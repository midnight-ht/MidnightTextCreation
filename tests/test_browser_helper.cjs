const test = require('node:test');
const assert = require('node:assert/strict');
const {executeTask, validateRequest, validateBridgeEvent, allowedTaskUrl} = require('../browser-helper/runner.js');

class Field {
  constructor(value = '') { this._value = value; this.events = []; this.tagName = 'INPUT'; }
  get value() { return this._value; }
  set value(v) { this._value = v; }
  dispatchEvent(e) { this.events.push(e.type); }
}
function fixture(overrides = {}) {
  const fields = { '#account': new Field('Alice'), '#title': new Field(), '#body': new Field(), '#id': new Field('post-1'), '#status': new Field('已发布'), '#reads': new Field('123'), ...overrides };
  global.document = {querySelectorAll(s) { if (s === 'INVALID[') throw new Error('bad selector'); return fields[s] === undefined ? [] : Array.isArray(fields[s]) ? fields[s] : [fields[s]]; }};
  global.location = {href:'http://127.0.0.1:8765/mock'};
  return fields;
}
function task(patch = {}) { return {id:'t1', binding_id:'binding-1', kind:'fill', platform:'mock', url:'http://127.0.0.1:8765/mock', expected_account:'Alice', content_id:'post-1', publication:{selected_title:'标题',body:'第一段\n第二段',summary:'',tags:[],media:[]}, selectors:{account:'#account',title:'#title',body:'#body',content_id:'#id',status:'#status',metrics:{reads:'#reads'}},overwrite:false,...patch}; }
test('fills exact fields, dispatches events and reports mock source', () => {
  const f = fixture(); const r = executeTask(task()); assert.equal(r.status,'filled'); assert.equal(r.source,'mock'); assert.equal(f['#title'].value,'标题'); assert.deepEqual(f['#body'].events,['input','change']);
});
test('account mismatch blocks every mutation', () => { const f = fixture({'#account':new Field('Bob')}); assert.equal(executeTask(task()).status,'account_mismatch'); assert.equal(f['#title'].value,''); });
test('missing account reports needs_login', () => { fixture({'#account':undefined}); assert.equal(executeTask(task()).status,'needs_login'); });
test('duplicate account blocks mutation', () => { const f = fixture({'#account':[new Field('Alice'),new Field('Alice')]}); assert.equal(executeTask(task()).status,'selector_not_unique'); assert.equal(f['#title'].value,''); });
test('existing draft is rejected and not appended', () => { const f = fixture({'#body':new Field('old')}); assert.equal(executeTask(task()).status,'nonempty_draft'); assert.equal(f['#title'].value,''); assert.equal(f['#body'].value,'old'); });
test('explicit overwrite replaces', () => { const f = fixture({'#body':new Field('old')}); assert.equal(executeTask(task({overwrite:true})).status,'filled'); assert.equal(f['#body'].value,'第一段\n第二段'); });
test('missing required field preflights before any write', () => { const f = fixture({'#body':undefined}); assert.equal(executeTask(task()).status,'selector_missing'); assert.equal(f['#title'].value,''); });
test('duplicate target blocks every write', () => { const f = fixture({'#body':[new Field(),new Field()]}); assert.equal(executeTask(task()).status,'selector_not_unique'); assert.equal(f['#title'].value,''); });
test('unsupported target blocks every write', () => { const f = fixture({'#body':{textContent:'',tagName:'DIV'}}); assert.equal(executeTask(task()).status,'unsupported_field'); assert.equal(f['#title'].value,''); });
test('configured optional field is preflighted', () => { const f = fixture(); const t = task(); t.publication.summary='摘要'; assert.equal(executeTask(t).status,'capability_unverified'); assert.equal(f['#title'].value,''); });
test('summary-only draft blocks all writes even with empty new summary',()=>{const f=fixture({'#summary':new Field('previous summary')});const t=task();t.selectors.summary='#summary';assert.equal(executeTask(t).status,'nonempty_draft');assert.equal(f['#title'].value,'');assert.equal(f['#body'].value,'');assert.equal(f['#summary'].value,'previous summary');});
test('tags-only draft blocks all writes even with empty new tags',()=>{const f=fixture({'#tags':new Field('old-tag')});const t=task();t.selectors.tags='#tags';assert.equal(executeTask(t).status,'nonempty_draft');assert.equal(f['#title'].value,'');assert.equal(f['#body'].value,'');assert.equal(f['#tags'].value,'old-tag');});
test('mapped blank optional fields are written and verified',()=>{const f=fixture({'#summary':new Field(),'#tags':new Field()});const t=task();t.selectors.summary='#summary';t.selectors.tags='#tags';const r=executeTask(t);assert.equal(r.status,'filled');assert.deepEqual(r.changed_fields,['title','body','summary','tags']);assert.deepEqual(f['#summary'].events,['input','change']);assert.deepEqual(f['#tags'].events,['input','change']);});
test('explicit overwrite clears stale mapped optional content',()=>{const f=fixture({'#summary':new Field('old'),'#tags':new Field('old')});const t=task({overwrite:true});t.selectors.summary='#summary';t.selectors.tags='#tags';assert.equal(executeTask(t).status,'filled');assert.equal(f['#summary'].value,'');assert.equal(f['#tags'].value,'');});
test('bad selector is a distinct error', () => { fixture(); const t = task(); t.selectors.body='INVALID['; assert.equal(executeTask(t).status,'selector_invalid'); });
test('readback failure never reports success', () => { class Locked extends Field { get value(){return '';} set value(v){} } fixture({'#body':new Locked()}); assert.equal(executeTask(task()).status,'readback_mismatch'); });
test('normalized line endings read back', () => { class CrLf extends Field { get value(){return this._value.replace(/\n/g,'\r\n');} set value(v){this._value=v;} } fixture({'#body':new CrLf()}); assert.equal(executeTask(task()).status,'filled'); });
test('contenteditable body is replaced and events dispatched', () => {const body={isContentEditable:true,textContent:'',events:[],dispatchEvent(e){this.events.push(e.type);}};fixture({'#body':body});assert.equal(executeTask(task()).status,'filled');assert.equal(body.textContent,'第一段\n第二段');assert.deepEqual(body.events,['input','change']);});
test('overlapping and readonly targets rejected before writes', () => {const f=fixture();const t=task();t.selectors.body='#title';assert.equal(executeTask(t).status,'selector_overlap');assert.equal(f['#title'].value,'');f['#body'].readOnly=true;assert.equal(executeTask(task()).status,'field_not_editable');assert.equal(f['#title'].value,'');});
test('collect checks ID and gets visible bounded metrics', () => { fixture(); const r = executeTask(task({kind:'collect'})); assert.equal(r.status,'collected'); assert.equal(r.platform_content_id,'post-1'); assert.equal(r.raw_status,'已发布'); assert.deepEqual(r.metrics,{reads:123}); assert.equal(r.source,'mock'); });
test('wrong collect ID blocks result', () => { fixture(); assert.equal(executeTask(task({kind:'collect',content_id:'other'})).status,'content_id_mismatch'); });
test('invalid metrics remain null', () => { fixture({'#reads':new Field('1.2万')}); assert.equal(executeTask(task({kind:'collect'})).metrics.reads,null); });
test('negative and unsafe integer metrics remain null', () => { for(const v of ['-1','9007199254740992','Infinity']) {fixture({'#reads':new Field(v)}); assert.equal(executeTask(task({kind:'collect'})).metrics.reads,null);} });
test('backend metric keys, fractional watch time, zero and blanks', () => {fixture({'#reads':new Field('0'),'#watch':new Field('12.5'),'#saves':new Field('')});const t=task({kind:'collect'});t.selectors.metrics={reads:'#reads',watch_seconds:'#watch',saves:'#saves',likes:'#reads'};const r=executeTask(t);assert.deepEqual(r.metrics,{reads:0,watch_seconds:12.5,saves:null});});
test('watch time must remain finite nonnegative numeric text', () => {for(const value of ['Infinity','-1','1.2万','1e999','']) {fixture({'#watch':new Field(value)});const t=task({kind:'collect'});t.selectors.metrics={watch_seconds:'#watch'};assert.equal(executeTask(t).metrics.watch_seconds,null);}});
test('real xiaohongshu requires media; media upload unsupported', () => { fixture(); global.location.href='https://creator.xiaohongshu.com/editor'; const t=task({platform:'xiaohongshu',url:global.location.href}); assert.equal(executeTask(t).status,'needs_media'); t.publication.media=['a.png']; assert.equal(executeTask(t).status,'media_upload_unsupported'); });
test('redirected document blocked before mutation', () => { const f=fixture(); global.location.href='https://evil.example/'; assert.equal(executeTask(task()).status,'url_rejected'); assert.equal(f['#title'].value,''); });
test('platform hosts are exact and credentials forbidden', () => { assert.equal(allowedTaskUrl('https://mp.weixin.qq.com/editor','wechat'),true); for(const u of ['https://mp.weixin.qq.com.evil.test/','http://mp.weixin.qq.com/','https://u:p@mp.weixin.qq.com/']) assert.equal(allowedTaskUrl(u,'wechat'),false); assert.equal(allowedTaskUrl('http://localhost:8765/mock','mock'),true); assert.equal(allowedTaskUrl('https://example.com','mock'),false); });
const request = () => ({type:'MIDNIGHT_REQUEST',requestId:'r1',task:task(),baseUrl:'http://127.0.0.1:8765',token:'session'});
test('trusted manager validates; external sender rejected', () => { assert.equal(validateRequest(request(),{url:'http://127.0.0.1:8765/',frameId:0}),null); assert.equal(validateRequest(request(),{url:'https://evil.test/',frameId:0}),'sender_rejected'); });
test('wrong manager origin and subframes rejected', () => { assert.equal(validateRequest(request(),{url:'http://localhost:8765/',frameId:0}),'origin_mismatch'); assert.equal(validateRequest(request(),{url:'http://127.0.0.1:8765/',frameId:1}),'sender_rejected'); });
test('mock task must use manager origin', () => { const r=request(); r.task.url='http://localhost:9999/mock'; assert.equal(validateRequest(r,{url:r.baseUrl,frameId:0}),'origin_mismatch'); });
test('bridge only accepts own window and same origin', () => { const w={}; const l={origin:'http://127.0.0.1:8765',href:'http://127.0.0.1:8765/'}; assert.equal(validateBridgeEvent({source:w,origin:l.origin,data:request()},w,l),true); assert.equal(validateBridgeEvent({source:{},origin:l.origin,data:request()},w,l),false); assert.equal(validateBridgeEvent({source:w,origin:'https://evil.test',data:request()},w,l),false); });
test('empty token and malformed requests rejected', () => {const r=request();r.token='';assert.equal(validateRequest(r,{url:r.baseUrl,frameId:0}),'request_invalid');assert.equal(validateRequest(null,{url:r.baseUrl}),'request_invalid');});
test('real URL rejects nondefault ports and fragments',()=>{assert.equal(allowedTaskUrl('https://mp.weixin.qq.com:443/edit','wechat'),true);assert.equal(allowedTaskUrl('https://mp.weixin.qq.com:444/edit','wechat'),false);assert.equal(allowedTaskUrl('https://mp.weixin.qq.com/edit#frag','wechat'),false);assert.equal(allowedTaskUrl('http://localhost:8765/mock#frag','mock'),false);});
test('task and binding identifiers obey backend bounds',()=>{for(const patch of [{id:'x'.repeat(81)},{id:'../bad'},{binding_id:''},{binding_id:'x'.repeat(81)},{binding_id:undefined}]) {const r=request();Object.assign(r.task,patch);assert.equal(validateRequest(r,{url:r.baseUrl,frameId:0}),'task_invalid');}});
function background(finalUrl) {
  const vm=require('node:vm'), fs=require('node:fs');
  let injected=0, created=0, listener;
  const event={addListener(){},removeListener(){}};
  const context={URL,setTimeout,clearTimeout,importScripts(){},MidnightHelper:{executeTask,validateRequest,allowedTaskUrl},chrome:{runtime:{onMessage:{addListener(fn){listener=fn;}}},tabs:{onUpdated:event,onRemoved:event,async create(){created++;return {id:4};},async get(){return {id:4,status:'complete',url:finalUrl};}},scripting:{async executeScript(args){injected++;assert.equal(args.func,executeTask);return [{result:{status:'filled',source:'mock'}}];}}}};
  vm.runInNewContext(fs.readFileSync(require('node:path').join(__dirname,'../browser-helper/background.js'),'utf8'),context);
  return {send(message,sender){return new Promise(resolve=>{assert.equal(listener(message,sender,resolve),true);});},counts(){return {injected,created};}};
}
test('background opens and injects with bounded load completion', async()=>{const b=background('http://127.0.0.1:8765/mock');const r=await b.send(request(),{url:'http://127.0.0.1:8765/',frameId:0});assert.equal(r.status,'filled');assert.deepEqual(b.counts(),{created:1,injected:1});});
test('background rejects redirects before scripting injection', async()=>{const b=background('https://evil.test/');const r=await b.send(request(),{url:'http://127.0.0.1:8765/',frameId:0});assert.equal(r.status,'url_rejected');assert.equal(r.source,'mock');assert.equal(b.counts().injected,0);});
test('background rejects external sender before opening tab', async()=>{const b=background('http://127.0.0.1:8765/mock');const r=await b.send(request(),{url:'https://evil.test/',frameId:0});assert.equal(r.status,'sender_rejected');assert.equal(b.counts().created,0);});
