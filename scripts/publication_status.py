"""Explicit-source publication snapshots; failed queries preserve the last success."""
from __future__ import annotations
import json
import math
import os
import re
import time
import uuid
from datetime import datetime, timezone, timedelta
from contextlib import nullcontext
from urllib.parse import quote, urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler
from scripts.content_manager import now, required_text

STATES = {'unknown','draft','scheduled','processing','published','rejected','removed'}
METRICS = {'impressions','clicks','reads','completions','saves','shares','comments','conversions','watch_seconds'}


def snapshot_from_result(publication, result, source, mapping):
    if source not in {'mock','api','browser'}: raise ValueError('Invalid snapshot source')
    if not isinstance(result,dict) or result.get('platform_content_id') != publication['platform_content_id']:
        raise ValueError('Publication identity mismatch')
    if result.get('ok') is False or result.get('error') or result.get('errcode',0) not in {0,'0',None}: raise ValueError('Upstream business error')
    raw = required_text(result.get('raw_status'),'raw_status')
    status = mapping.get(raw, raw if raw in STATES else 'unknown')
    if status not in STATES: raise ValueError('Invalid mapped publication state')
    values = result.get('metrics',{})
    if not isinstance(values,dict) or set(values)-METRICS: raise ValueError('Unknown metric')
    metrics = {k:None for k in METRICS}
    for key,value in values.items():
        if value is not None and (isinstance(value,bool) or not isinstance(value,(float,int)) or not 0 <= value <= 2**53-1 or not math.isfinite(value) or (key!='watch_seconds' and int(value)!=value)):
            raise ValueError('Invalid metric value')
        metrics[key]=value
    upstream_time = result.get('observed_at')
    if upstream_time:
        stamp = datetime.fromisoformat(upstream_time)
        if stamp.tzinfo is None or stamp > datetime.now(timezone.utc)+timedelta(minutes=5): raise ValueError('Invalid upstream observation time')
    return {'id':uuid.uuid4().hex,'publication_id':publication['id'],'platform_content_id':publication['platform_content_id'],
            'source':source,'observed_at':now(),'upstream_observed_at':upstream_time,'query_state':'succeeded',
            'status':status,'raw_status':raw,'metrics':metrics}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):
        raise ValueError('Status endpoint redirect refused')


def api_result(adapter, publication, expected_account):
    endpoint = required_text(adapter.get('endpoint'),'API endpoint').replace('{content_id}',quote(publication['platform_content_id'],safe=''))
    parsed = urlparse(endpoint)
    if parsed.username or parsed.password or parsed.fragment or not parsed.hostname:
        raise ValueError('Invalid status endpoint')
    if parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in {'localhost','127.0.0.1'}):
        raise ValueError('Status endpoint must be HTTPS or loopback HTTP')
    headers={'Accept':'application/json'}
    if adapter.get('token_env'):
        name=adapter['token_env']
        if not isinstance(name,str) or not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',name): raise ValueError('Invalid credential environment reference')
        token=os.environ.get(name)
        if not token: raise ValueError('Status credential is unavailable')
        headers['Authorization']='Bearer '+token
    # Disable proxy inheritance and redirects so configured credentials stay at this endpoint.
    opener=build_opener(ProxyHandler({}),NoRedirect())
    with opener.open(Request(endpoint,headers=headers),timeout=5) as response:
        payload=response.read(1024*1024+1)
    if len(payload)>1024*1024: raise ValueError('Status response exceeds size limit')
    result=json.loads(payload.decode('utf-8'))
    if not isinstance(result,dict) or result.get('account')!=expected_account: raise ValueError('Status account mismatch')
    return result


def failed_snapshot(manager,publication,source,error):
    return manager.put('snapshot',{'id':uuid.uuid4().hex,'publication_id':publication['id'],'source':source,
                      'observed_at':now(),'query_state':'failed','status':'unknown','metrics':{},'error':error})


def collect(manager, publication_id, base_url='http://127.0.0.1:8765',lock=None):
    with lock or nullcontext():
        publication=manager.get('publication',publication_id)
        binding,_=manager.binding(publication['binding_id'])
        adapter=binding.get('adapter',{'mode':'mock'}); source=adapter['mode']
        if source=='browser':
            return {'task':manager.create_task(publication['version_id'],'collect',base_url,publication_id)}
    try:
        if source=='mock':
            result={'platform_content_id':publication['platform_content_id'],'raw_status':adapter.get('mock_status','processing'),
                    'metrics':adapter.get('mock_metrics',{})}
        else:
            result=api_result(adapter,publication,binding['expected_account'])
        snap=snapshot_from_result(publication,result,source,adapter.get('status_mapping',{}))
        return manager.put('snapshot',snap)
    except (ValueError,TypeError,OSError,TimeoutError) as exc:
        # Avoid retaining endpoint URLs, headers or remote messages which may contain credentials.
        return failed_snapshot(manager,publication,source,type(exc).__name__)


def latest(manager,publication_id):
    manager.get('publication',publication_id)
    snapshots=[s for s in manager.list('snapshot') if s['publication_id']==publication_id]
    snapshots.sort(key=lambda s:s['observed_at'],reverse=True)
    recent=snapshots[0] if snapshots else None
    good=next((s for s in snapshots if s['query_state']=='succeeded'),None)
    observed=min(datetime.fromisoformat(good['observed_at']),datetime.fromisoformat(good.get('upstream_observed_at') or good['observed_at'])) if good else None
    age=(datetime.now(timezone.utc)-observed).total_seconds() if observed else None
    interval=manager.get('publication',publication_id).get('poll_interval',60)
    return {'latest':recent,'last_success':good,'age_seconds':round(age,1) if age is not None else None,
            'freshness':'unknown' if age is None else ('fresh' if age<=interval*2 else 'stale')}


def set_polling(manager, publication_id, enabled, interval=60):
    if not isinstance(enabled,bool) or isinstance(interval,bool) or not isinstance(interval,int) or not 10<=interval<=86400:
        raise ValueError('Polling requires a boolean and an integer interval of 10-86400 seconds')
    pub=manager.get('publication',publication_id)
    binding,_=manager.binding(pub['binding_id'])
    # Browser worker operates in a visible management tab, never silently launches background tabs.
    pub.update(polling=enabled,poll_interval=interval,next_poll=time.time(),failures=0)
    return manager.put('publication',pub)


def poll_once(manager,base_url,clock=None,lock=None):
    clock=time.time() if clock is None else clock
    results=[]
    for pub in manager.publications():
        if not pub.get('polling') or pub.get('next_poll',0)>clock: continue
        binding,_=manager.binding(pub['binding_id'])
        if binding.get('adapter',{}).get('mode')=='browser': continue
        with lock or nullcontext():
            current=manager.get('publication',pub['id'])
            if not current.get('polling') or current.get('next_poll',0)>clock: continue
            current['next_poll']=clock+current['poll_interval']
            manager.put('publication',current)
        result=collect(manager,pub['id'],base_url,lock=lock)
        # Re-read to avoid overwriting an explicit stop/interval change during a request.
        with lock or nullcontext():
            current=manager.get('publication',pub['id'])
            failures=current.get('failures',0)+1 if result.get('query_state')=='failed' else 0
            delay=max(current['poll_interval'],min(current['poll_interval']*2**min(failures,6),3600))
            current.update(failures=failures,next_poll=clock+delay)
            manager.put('publication',current)
        results.append(result)
    return results
