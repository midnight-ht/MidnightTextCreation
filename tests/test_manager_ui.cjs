'use strict';
const test=require('node:test');
const assert=require('node:assert/strict');
const ui=require('../manager/app.js');
test('simple binding edits preserve advanced adapter configuration',()=>{
 const config={accounts:[],styles:[],bindings:[{binding_id:'b',adapter:{mode:'browser',selectors:{title:'#title'}},style_ids:['s'],output_dir:'old'}]};
 const next=ui.mergeRecord(config,'bindings','binding_id',{binding_id:'b',output_dir:'new'});
 assert.equal(next.bindings[0].adapter.selectors.title,'#title'); assert.equal(config.bindings[0].output_dir,'old');
});
test('failed query clearly distinguishes retained successful status',()=>{
 const text=ui.statusText({latest:{query_status:'failed',error:'timeout',observed_at:'now'},last_success:{normalized_status:'published',observed_at:'old'},freshness:'stale',age_seconds:90});
 assert.match(text,/failed|失败/);assert.match(text,/published/);assert.match(text,/old/);assert.match(text,/stale|过期/);
});
test('import preserves publication media and explicit overrides',()=>{
 const p={selected_title:'T',body:'B',media:[{path:'a.png'}],custom:{proof:true}};
 const payload=ui.importPayload('b',p,'approved','c',{output_dir:'D:/中文'});
 assert.deepEqual(payload.publication,p);assert.equal(payload.overrides.output_dir,'D:/中文');
});
test('messages must originate from same window and origin and match pending request',()=>{
 const own={}; const pending=new Map([['r',{}]]);
 assert.equal(ui.acceptResponse({source:own,origin:'http://127.0.0.1:8765',data:{type:'MIDNIGHT_RESPONSE',requestId:'r',result:{status:'filled'}}},own,'http://127.0.0.1:8765',pending),true);
 assert.equal(ui.acceptResponse({source:own,origin:'https://evil.test',data:{type:'MIDNIGHT_RESPONSE',requestId:'r',result:{status:'filled'}}},own,'http://127.0.0.1:8765',pending),false);
});
test('blank output override restores inheritance and preserves adapter',()=>{
 const c={bindings:[{id:'b',output_dir:'old',adapter:{mode:'api',token_env:'REF'}}]};
 const next=ui.mergeRecord(c,'bindings','id',{id:'b',output_dir:''});
 assert.equal('output_dir' in next.bindings[0],false);assert.equal(next.bindings[0].adapter.token_env,'REF');assert.equal(c.bindings[0].output_dir,'old');
});
test('semantic generation payload and managed languages are valid',()=>{
 assert.equal(ui.validLanguage('zh'),true);assert.equal(ui.validLanguage('en'),true);assert.equal(ui.validLanguage('zh-CN'),false);
 const p=ui.generationPayload('b',{title:'标题',raw_material:'已核验素材',style_id:'s',output_dir:'D:/中文'});
 assert.equal(p.input.title,'标题');assert.equal(p.input.style_id,'s');assert.equal(p.input.output_dir,'D:/中文');
 assert.throws(()=>ui.generationPayload('b',{title:'T',raw_material:''}),/素材|正文/);
});
test('backend query_state failure stays visible while retaining old success',()=>{
 assert.match(ui.statusText({latest:{query_state:'failed',status:'unknown',observed_at:'new'},last_success:{status:'published',observed_at:'old'},freshness:'stale'}),/最近查询：failed/);
 assert.match(ui.statusText({latest:null,last_success:null,freshness:'unknown'}),/上次成功：无/);
});
test('browser polling honors visibility, interval, stop and pending',()=>{
 const b=[{id:'b',adapter:{mode:'browser'}},{id:'m',adapter:{mode:'mock'}}];
 const p=[{id:'p',binding_id:'b',polling:true},{id:'stopped',binding_id:'b',polling:false},{id:'mock',binding_id:'m',polling:true}];
 assert.deepEqual(ui.dueBrowserPolls(p,b,{},1000,false).map(p=>p.id),['p']);
 assert.deepEqual(ui.dueBrowserPolls(p,b,{},1000,true),[]);
 assert.deepEqual(ui.dueBrowserPolls(p,b,{p:{next:2000}},1000,false),[]);
 assert.deepEqual(ui.dueBrowserPolls(p,b,{p:{next:0,pending:true}},1000,false),[]);
 assert.equal(ui.pollDelay(60,0),60000);assert.equal(ui.pollDelay(60,1),120000);assert.equal(ui.pollDelay(60,12),3600000);assert.equal(ui.pollDelay(7200,2),7200000);
});
test('automatic refresh preserves open association form and recent interaction',()=>{
 assert.equal(ui.isInteractionActive({focusedTag:'SUMMARY',focusedInForm:false,openForm:true,lastInteraction:0,now:100000}),true);
 assert.equal(ui.isInteractionActive({focusedTag:'INPUT',focusedInForm:true,openForm:false,lastInteraction:0,now:100000}),true);
 assert.equal(ui.isInteractionActive({focusedTag:'BUTTON',focusedInForm:false,openForm:false,lastInteraction:95000,now:100000}),true);
 assert.equal(ui.isInteractionActive({focusedTag:'BODY',focusedInForm:false,openForm:false,lastInteraction:0,now:100000}),false);
});
test('Chinese timestamps display Beijing time and association stores explicit offset',()=>{
 const shown=ui.displayTime('2026-10-04T02:42:50+00:00');assert.match(shown,/10:42:50/);assert.match(shown,/北京时间/);
 assert.equal(ui.beijingTimestamp('2026-10-04T10:42'),'2026-10-04T10:42+08:00');
 assert.throws(()=>ui.beijingTimestamp('bad'),/时间/);
});
