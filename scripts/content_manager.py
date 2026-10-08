"""Account-scoped configuration, immutable content exports and browser tasks."""
from __future__ import annotations
import hashlib
import json
import re
import sqlite3
import uuid
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, quote

from scripts.run_skill import normalize_input, run_single, load_or_create_style_template
from scripts.platform_layout import PROFILES


def now():
    return datetime.now(timezone.utc).isoformat()


def identifier(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', value):
        raise ValueError('ID must contain 1-80 letters, digits, underscores or hyphens')
    if value.upper() in {'CON','PRN','AUX','NUL',*(f'COM{i}' for i in range(1,10)),*(f'LPT{i}' for i in range(1,10))}:
        raise ValueError('ID is a reserved Windows device name')
    return value


def required_text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{name} must be nonempty text')
    return value.strip()


def output_path(value, base):
    required_text(value, 'output_dir')
    path = Path(value).expanduser()
    if '..' in path.parts:
        raise ValueError('Output path must not contain parent traversal')
    return (path if path.is_absolute() else Path(base) / path).resolve()


HOSTS = {'wechat': 'mp.weixin.qq.com', 'toutiao': 'mp.toutiao.com', 'xiaohongshu': 'creator.xiaohongshu.com'}
FILL_STATES = {'filled', 'partial', 'failed', 'needs_login', 'account_mismatch', 'needs_media', 'draft_not_empty', 'unsupported'}
HELPER_ERRORS = {'request_invalid','sender_rejected','origin_mismatch','task_invalid','url_rejected','selector_missing',
                 'selector_invalid','selector_not_unique','capability_unverified','content_id_mismatch','media_upload_unsupported',
                 'publication_invalid','unsupported_field','field_not_editable','nonempty_draft','selector_overlap',
                 'write_failed','readback_mismatch','execution_failed','extension_unavailable','page_timeout','tab_closed'}


def validate_browser_url(url, platform):
    parsed = urlparse(url)
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError('Browser URL must not contain credentials or fragments')
    if platform == 'mock':
        if parsed.scheme != 'http' or parsed.hostname not in {'127.0.0.1', 'localhost'}:
            raise ValueError('Mock browser tasks require a local HTTP URL')
    elif parsed.scheme != 'https' or parsed.hostname != HOSTS.get(platform) or parsed.port not in {None, 443}:
        raise ValueError('Browser URL does not match selected platform')
    return url


def validate_config(config):
    if not isinstance(config, dict): raise ValueError('Configuration must be an object')
    maps = {}
    for group in ('accounts', 'styles', 'bindings'):
        records = config.get(group, [])
        if not isinstance(records, list): raise ValueError(f'{group} must be an array')
        maps[group] = {}
        for record in records:
            if not isinstance(record, dict): raise ValueError('Configuration records must be objects')
            rid = identifier(record.get('id'))
            if rid in maps[group]: raise ValueError(f'Duplicate {group} ID')
            maps[group][rid] = record
    def no_secrets(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower() in {'password','cookie','token','access_token','authorization','secret','api_key'}:
                    raise ValueError('Use environment credential references, not stored secrets')
                no_secrets(item)
        elif isinstance(value, list):
            for item in value: no_secrets(item)
    no_secrets(config)
    for account in maps['accounts'].values():
        required_text(account.get('name'), 'account name')
        if 'enabled' in account and not isinstance(account['enabled'],bool): raise ValueError('Account enabled must be boolean')
    for style in maps['styles'].values():
        required_text(style.get('name'), 'style name')
        for field in ('tone','style_guidance','target_reader','forbidden_style','style_template'):
            if field in style and not isinstance(style[field], str): raise ValueError(f'Invalid style {field}')
        if 'facts' in style: raise ValueError('Task facts cannot be stored in a style preset')
        normalize_input({**style, 'platform': 'generic', 'format': 'text'})
    for binding in maps['bindings'].values():
        if binding.get('account_id') not in maps['accounts']: raise ValueError('Unknown account binding')
        if binding.get('style_id') not in maps['styles']: raise ValueError('Unknown style binding')
        platform = binding.get('platform')
        if platform not in PROFILES: raise ValueError('Unknown platform binding')
        required_text(binding.get('expected_account'), 'expected_account')
        if 'output_dir' in binding: required_text(binding['output_dir'], 'output_dir')
        style = maps['styles'][binding['style_id']]
        normalize_input({**style, 'platform': platform})
        adapter = binding.get('adapter', {'mode':'mock'})
        if not isinstance(adapter, dict) or adapter.get('mode') not in {'mock','api','browser'}: raise ValueError('Invalid adapter mode')
        mapping = adapter.get('status_mapping',{})
        if not isinstance(mapping,dict) or any(not isinstance(k,str) or not isinstance(v,str) or v not in {'unknown','draft','scheduled','processing','published','rejected','removed'} for k,v in mapping.items()):
            raise ValueError('Invalid status mapping')
        for key in ('editor_url','collector_url'):
            if key in adapter and not isinstance(adapter[key],str): raise ValueError(f'{key} must be text')
            if adapter.get(key): validate_browser_url(adapter[key].replace('{content_id}', 'id'), platform)
        for key in ('endpoint','token_env','mock_status'):
            if key in adapter and not isinstance(adapter[key],str): raise ValueError(f'{key} must be text')
        if 'selectors' in adapter:
            selectors = adapter['selectors']
            if not isinstance(selectors, dict): raise ValueError('selectors must be an object')
            for key, value in selectors.items():
                if key == 'metrics':
                    if not isinstance(value, dict) or any(not isinstance(v,str) for v in value.values()): raise ValueError('Invalid metric selectors')
                elif not isinstance(value, str): raise ValueError('Invalid field selector')
        if 'poll_interval' in adapter and (isinstance(adapter['poll_interval'],bool) or not isinstance(adapter['poll_interval'],int) or not 10 <= adapter['poll_interval'] <= 86400): raise ValueError('poll_interval must be 10-86400 seconds')
    for account in maps['accounts'].values():
        if 'output_dir' in account: required_text(account['output_dir'], 'output_dir')
    return maps


class ContentManager:
    def __init__(self, data_dir):
        self.task_lock = threading.RLock()
        self.data_dir = Path(data_dir).resolve()
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.data_dir / 'manager.sqlite3'
        with self.connect() as db:
            db.execute('CREATE TABLE IF NOT EXISTS records(kind TEXT, id TEXT, data TEXT, PRIMARY KEY(kind,id))')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.db_path, timeout=10)
        try:
            with db:
                yield db
        finally:
            db.close()

    def put(self, kind, data):
        with self.connect() as db:
            db.execute('INSERT INTO records VALUES(?,?,?) ON CONFLICT(kind,id) DO UPDATE SET data=excluded.data',
                       (kind, data['id'], json.dumps(data, ensure_ascii=False, allow_nan=False)))
        return data

    def get(self, kind, rid):
        with self.connect() as db:
            row = db.execute('SELECT data FROM records WHERE kind=? AND id=?', (kind, rid)).fetchone()
        if not row: raise ValueError(f'Unknown {kind}: {rid}')
        return json.loads(row[0])

    def list(self, kind):
        with self.connect() as db:
            rows = db.execute('SELECT data FROM records WHERE kind=? ORDER BY rowid DESC', (kind,)).fetchall()
        return [json.loads(r[0]) for r in rows]

    def save_config(self, config, base_dir=None):
        validate_config(config)
        # Existing version records are immutable; retained bindings cannot change identity.
        old = self.get_config()
        old_bindings = {b['id']:b for b in old['bindings']}
        used = {c['binding_id'] for c in self.contents()}
        new_bindings = {b['id']:b for b in config.get('bindings',[])}
        for bid in used:
            previous = old_bindings.get(bid)
            current = new_bindings.get(bid)
            if previous and (not current or any(current.get(k) != previous.get(k) for k in ('account_id','platform','expected_account'))):
                raise ValueError('A binding with content cannot be deleted or reassigned; create a new binding')
        self.put('settings', {'id':'config', 'config':config, 'base_dir':str(Path(base_dir or self.data_dir).resolve())})
        return self.get_config()

    def get_config(self):
        try: return self.get('settings','config')['config']
        except ValueError: return {'accounts':[], 'styles':[], 'bindings':[]}

    def binding(self, bid):
        maps = validate_config(self.get_config())
        if bid not in maps['bindings']: raise ValueError('Unknown binding')
        return maps['bindings'][bid], maps

    def resolve(self, bid, overrides):
        if not isinstance(overrides,dict): raise ValueError('Content input must be an object')
        binding, maps = self.binding(bid)
        if 'platform_configs' in overrides: raise ValueError('Managed content is one binding per request')
        if 'platform' in overrides and overrides['platform'] != binding['platform']: raise ValueError('Task platform does not match binding')
        style_id = overrides.get('style_id', binding['style_id'])
        if style_id not in maps['styles']: raise ValueError('Unknown style')
        style = maps['styles'][style_id]
        account = maps['accounts'][binding['account_id']]
        if not account.get('enabled',True): raise ValueError('Account is disabled')
        base = self.get('settings','config')['base_dir']
        directory = overrides.get('output_dir', binding.get('output_dir', account.get('output_dir', str(self.data_dir / 'exports'))))
        merged = {**style, **overrides, 'platform':binding['platform'], 'output_dir':str(output_path(directory,base)), 'style_id':style_id}
        return normalize_input(merged)

    def generate(self, bid, payload, content_id=None):
        resolved = self.resolve(bid, payload)
        if resolved['language']=='bilingual': raise ValueError('Managed versions require one language; create a separate version for each language')
        binding, _ = self.binding(bid)
        cid = identifier(content_id or uuid.uuid4().hex)
        version = uuid.uuid4().hex
        directory = Path(resolved['output_dir']) / binding['account_id'] / binding['platform'] / cid / version
        root = Path(resolved['output_dir'])
        if not directory.resolve().is_relative_to(root): raise ValueError('Export escapes output root')
        directory.mkdir(parents=True, exist_ok=False)
        resolved['output_dir'] = str(directory)
        if not resolved.get('style_guidance'):
            _, guidance = load_or_create_style_template(resolved)
            resolved['style_guidance'] = guidance
        result = run_single(resolved, binding['platform'], resolved['language'], directory)
        publication = {**result['platform_output'], 'selected_title':result['platform_output'].get('selected_title',resolved['title'])}
        return self._record(binding, resolved, cid, version, directory, publication, result['status'], result)

    def import_content(self, bid, publication, review_status='needs_human_review', content_id=None, overrides=None):
        if not isinstance(publication,dict): raise ValueError('Publication must be an object')
        required_text(publication.get('selected_title'), 'selected_title')
        required_text(publication.get('body'), 'body')
        for field in ('summary','cover_text'):
            if field in publication and not isinstance(publication[field],str): raise ValueError(f'{field} must be text')
        for field in ('tags','media'):
            if field in publication and (not isinstance(publication[field],list) or any(not isinstance(x,str) for x in publication[field])): raise ValueError(f'{field} must contain strings')
        if review_status not in {'needs_human_review','ready_for_human_review'}: raise ValueError('Import cannot approve or publish content')
        binding, _ = self.binding(bid)
        resolved = self.resolve(bid, overrides or {})
        cid, version = identifier(content_id or uuid.uuid4().hex), uuid.uuid4().hex
        directory = Path(resolved['output_dir']) / binding['account_id'] / binding['platform'] / cid / version
        if not directory.resolve().is_relative_to(Path(resolved['output_dir'])): raise ValueError('Export escapes output root')
        directory.mkdir(parents=True, exist_ok=False)
        publication = {'summary':'','tags':[],'media':[],**publication}
        (directory / 'body.md').write_text(f"# {publication['selected_title']}\n\n{publication['body']}\n",encoding='utf-8')
        return self._record(binding,resolved,cid,version,directory,publication,review_status, {'execution_mode':'imported'})

    def _record(self,binding,resolved,cid,version,directory,publication,status,result):
        media = publication.get('media',[])
        for path in media:
            if not isinstance(path,str) or not Path(path).is_file(): raise ValueError('Imported media must exist as a local file')
        publication.setdefault('media',[])
        serialized = json.dumps(publication,ensure_ascii=False,allow_nan=False,indent=2)
        (directory/'publication.json').write_text(serialized,encoding='utf-8')
        (directory/'review.json').write_text(json.dumps(result,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf-8')
        record = {'id':version,'content_id':cid,'version_id':version,'binding_id':binding['id'],'account_id':binding['account_id'],
                  'platform':binding['platform'],'expected_account':binding['expected_account'],'style_id':resolved['style_id'],
                  'style_snapshot':{k:v for k,v in resolved.items() if k in ('tone','author_samples','style_guidance','review_thresholds','forbidden_claims')},
                  'style_version':hashlib.sha256(json.dumps(self.binding(binding['id'])[1]['styles'][resolved['style_id']],sort_keys=True,ensure_ascii=False).encode()).hexdigest(),
                  'resolved_input':resolved,
                  'directory':str(directory),'publication':publication,'review_status':status,'created_at':now(),
                  'digest':hashlib.sha256(serialized.encode()).hexdigest()}
        (directory/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
        return self.put('content',record)

    def contents(self): return self.list('content')
    def publications(self): return self.list('publication')
    def tasks(self): return self.list('task')

    def associate(self, version_id, platform_content_id, url='', published_at=None):
        content = self.get('content',version_id)
        required_text(platform_content_id,'platform_content_id')
        if len(platform_content_id)>300: raise ValueError('Content ID is too long')
        if url:
            parsed = urlparse(url)
            if parsed.scheme not in {'https','http'} or parsed.username or parsed.password: raise ValueError('Invalid publication URL')
        if published_at:
            stamp = datetime.fromisoformat(published_at)
            if not stamp.tzinfo: raise ValueError('Published time requires timezone')
        existing = next((p for p in self.publications() if p['binding_id']==content['binding_id'] and p['platform_content_id']==platform_content_id),None)
        if existing:
            if existing['version_id'] != version_id: raise ValueError('Publication ID is already associated with another version')
            return existing
        return self.put('publication',{'id':uuid.uuid4().hex,'version_id':version_id,'binding_id':content['binding_id'],
                        'platform':content['platform'],'platform_content_id':platform_content_id,'url':url,'published_at':published_at,
                        'association_source':'manual','created_at':now(),'polling':False,'poll_interval':60,'next_poll':0,'failures':0})

    def create_task(self, version_id, kind, base_url, publication_id=None):
        with self.task_lock:
            return self._create_task(version_id,kind,base_url,publication_id)

    def _create_task(self, version_id, kind, base_url, publication_id=None):
        if kind not in {'fill','collect'}: raise ValueError('Invalid browser task kind')
        content = self.get('content',version_id)
        for existing in self.tasks():
            if existing['state']=='pending' and existing['version_id']==version_id and existing['kind']==kind and existing.get('publication_id')==publication_id:
                if (datetime.now(timezone.utc)-datetime.fromisoformat(existing['created_at'])).total_seconds()<90:
                    return existing
        binding,_ = self.binding(content['binding_id'])
        adapter = binding.get('adapter',{'mode':'mock'})
        mock = adapter['mode']=='mock'
        expected = content['expected_account']
        publication = self.get('publication',publication_id) if publication_id else None
        if kind == 'collect' and (not publication or publication['version_id']!=version_id): raise ValueError('Collection requires matching publication association')
        cid = publication['platform_content_id'] if publication else content['content_id']
        if mock:
            validate_browser_url(base_url,'mock')
            url = base_url + '/mock-editor.html?account=' + quote(expected) + '&content_id=' + quote(cid)
            selectors = {'account':'#account','title':'#title','body':'#body','summary':'#summary','tags':'#tags','status':'#status','content_id':'#content-id','metrics':{'reads':'#reads'}}
        else:
            key = 'editor_url' if kind=='fill' else 'collector_url'
            url = adapter.get(key,'').replace('{content_id}',quote(cid,safe=''))
            validate_browser_url(url,binding['platform'])
            selectors = adapter.get('selectors',{})
            required = ('account','title','body') if kind=='fill' else ('account','content_id','status')
            if any(not selectors.get(k) for k in required): raise ValueError('Configure and verify account/page field selectors first')
        return self.put('task',{'id':uuid.uuid4().hex,'kind':kind,'state':'pending','platform':'mock' if mock else binding['platform'],
                        'binding_platform':binding['platform'],'binding_id':binding['id'],'url':url,'expected_account':expected,
                        'content_id':cid,'version_id':version_id,'publication_id':publication_id,'publication':content['publication'],
                        'selectors':selectors,'overwrite':False,'created_at':now(),'digest':content['digest']})

    def complete_task(self, tid, result):
        with self.task_lock:
            return self._complete_task(tid,result)

    def _complete_task(self, tid, result):
        task = self.get('task',tid)
        if task['state'] != 'pending': return task
        if not isinstance(result,dict): raise ValueError('Task result must be an object')
        state = result.get('status')
        if state in HELPER_ERRORS: state='failed'
        allowed = FILL_STATES if task['kind']=='fill' else {'collected','failed','needs_login','account_mismatch','unsupported'}
        if state not in allowed: raise ValueError('Unexpected browser result status')
        expected_source = 'mock' if task['platform']=='mock' else 'browser'
        if state in {'filled','collected'} and result.get('source') != expected_source: raise ValueError('Incorrect browser result source')
        if state=='collected':
            from scripts.publication_status import snapshot_from_result
            publication = self.get('publication',task['publication_id'])
            binding,_ = self.binding(task['binding_id'])
            snap = snapshot_from_result(publication,result,expected_source,binding.get('adapter',{}).get('status_mapping',{}))
            self.put('snapshot',snap)
        elif task['kind']=='collect':
            from scripts.publication_status import failed_snapshot
            failed_snapshot(self,self.get('publication',task['publication_id']),expected_source,result.get('status','failed'))
        task.update(state=state,result=result,completed_at=now())
        return self.put('task',task)

