/* Shared browser/Node contract. executeTask is self-contained for MV3 injection. */
(function(root) {
  'use strict';
  function localUrl(value) {
    try { const u=new URL(value); return u.protocol==='http:' && ['localhost','127.0.0.1'].includes(u.hostname) && !u.username && !u.password && !u.hash ? u : null; } catch { return null; }
  }
  function allowedTaskUrl(value, platform) {
    if(platform==='mock') return !!localUrl(value);
    try { const u=new URL(value); return u.protocol==='https:' && !u.username && !u.password && !u.hash && !u.port && u.hostname===({wechat:'mp.weixin.qq.com',toutiao:'mp.toutiao.com',xiaohongshu:'creator.xiaohongshu.com'})[platform]; } catch { return false; }
  }
  function validateRequest(message,sender) {
    if(!message || message.type!=='MIDNIGHT_REQUEST' || typeof message.requestId!=='string' || !message.requestId || message.requestId.length>200 || typeof message.token!=='string' || !message.token || message.token.length>4096) return 'request_invalid';
    const origin=localUrl(sender && sender.url), base=localUrl(message.baseUrl);
    if(!origin || (sender.frameId!==undefined && sender.frameId!==0)) return 'sender_rejected';
    if(!base || base.origin!==origin.origin) return 'origin_mismatch';
    const t=message.task;
    const idValid=value=>typeof value==='string' && /^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$/.test(value);
    if(!t || !['fill','collect'].includes(t.kind) || !idValid(t.id) || !idValid(t.binding_id) || typeof t.expected_account!=='string' || !t.expected_account.trim() || t.expected_account.length>4096 || typeof t.url!=='string' || t.url.length>8192) return 'task_invalid';
    if(t.kind==='collect' && (typeof t.content_id!=='string' || !t.content_id.trim() || t.content_id.length>4096)) return 'task_invalid';
    if(!allowedTaskUrl(t.url,t.platform)) return 'url_rejected';
    if(t.platform==='mock' && new URL(t.url).origin!==origin.origin) return 'origin_mismatch';
    return null;
  }
  function validateBridgeEvent(event, ownWindow, loc) {
    return event.source===ownWindow && event.origin===loc.origin && !validateRequest(event.data,{url:loc.href,frameId:0});
  }
  function executeTask(task) {
    const source=task.platform==='mock'?'mock':'browser';
    const result=(status,extra={})=>({status,source,...extra});
    const normalize=v=>String(v ?? '').replace(/\r\n?/g,'\n').replace(/\u00a0/g,' ').trim();
    const read=el=>normalize('value' in el ? el.value : el.innerText ?? el.textContent);
    const fail=(status,field)=>{throw {status,field};};
    function one(selector,field,missingStatus='selector_missing') {
      if(typeof selector!=='string' || !selector.trim()) fail('capability_unverified',field);
      let found;
      try {found=document.querySelectorAll(selector);} catch {fail('selector_invalid',field);}
      if(!found.length) fail(missingStatus,field);
      if(found.length!==1) fail('selector_not_unique',field);
      return found[0];
    }
    try {
      let u, requested;
      try {u=new URL(location.href);requested=new URL(task.url);} catch {return result('url_rejected');}
      const host={wechat:'mp.weixin.qq.com',toutiao:'mp.toutiao.com',xiaohongshu:'creator.xiaohongshu.com'}[task.platform];
      const valid=task.platform==='mock' ? u.protocol==='http:' && ['localhost','127.0.0.1'].includes(u.hostname) && u.origin===requested.origin : u.protocol==='https:' && u.hostname===host && !u.port;
      if(!valid || u.username || u.password || u.hash) return result('url_rejected');
      const s=task.selectors || {};
      const account=one(s.account,'account','needs_login');
      if(!task.expected_account || read(account)!==normalize(task.expected_account)) return result('account_mismatch');
      if(task.kind==='collect') {
        if(!task.content_id || read(one(s.content_id,'content_id'))!==normalize(task.content_id)) return result('content_id_mismatch');
        const raw_status=read(one(s.status,'status'));
        const metrics={};
        for(const [key,selector] of Object.entries(s.metrics || {})) {
          if(!['impressions','clicks','reads','completions','saves','shares','comments','conversions','watch_seconds'].includes(key)) continue;
          const raw=read(one(selector,`metrics.${key}`));
          const value=(key==='watch_seconds'? /^(?:\d+(?:\.\d*)?|\.\d+)$/:/^\d+$/).test(raw)?Number(raw):NaN;
          metrics[key]=(key==='watch_seconds'? Number.isFinite(value) : Number.isSafeInteger(value)) && value>=0 ? value : null;
        }
        return result('collected',{platform_content_id:task.content_id,raw_status,metrics});
      }
      if(task.kind!=='fill') return result('task_invalid');
      const p=task.publication || {};
      if(task.platform==='xiaohongshu' && (!Array.isArray(p.media) || !p.media.length)) return result('needs_media');
      if(Array.isArray(p.media) && p.media.length) return result('media_upload_unsupported');
      if(typeof p.selected_title!=='string' || !normalize(p.selected_title) || typeof p.body!=='string' || !normalize(p.body)) return result('publication_invalid');
      const values={title:p.selected_title,body:p.body};
      if(p.summary || s.summary) values.summary=String(p.summary ?? '');
      if((Array.isArray(p.tags) && p.tags.length) || s.tags) values.tags=Array.isArray(p.tags)?p.tags.join(' '):'';
      const writes=[];
      for(const [field,value] of Object.entries(values)) {
        const el=one(s[field],field);
        if(!el.isContentEditable && !['INPUT','TEXTAREA'].includes(el.tagName)) fail('unsupported_field',field);
        if(el.disabled || el.readOnly) fail('field_not_editable',field);
        if(read(el) && task.overwrite!==true) fail('nonempty_draft',field);
        if(writes.some(w=>w.el===el)) fail('selector_overlap',field);
        writes.push({el,field,value});
      }
      const changed=[];
      for(const {el,field,value} of writes) {
        try {
          if(el.isContentEditable) el.textContent=value;
          else {
            let proto=Object.getPrototypeOf(el),setter;
            while(proto && !setter) {setter=Object.getOwnPropertyDescriptor(proto,'value')?.set;proto=Object.getPrototypeOf(proto);}
            if(setter) setter.call(el,value); else el.value=value;
          }
          changed.push(field);
          el.dispatchEvent(new Event('input',{bubbles:true}));
          el.dispatchEvent(new Event('change',{bubbles:true}));
        } catch {return result('write_failed',{field,changed_fields:changed});}
      }
      for(const {el,field,value} of writes) if(read(el)!==normalize(value)) return result('readback_mismatch',{field,changed_fields:changed});
      return result('filled',{changed_fields:changed});
    } catch(e) {return result(e.status || 'execution_failed',e.field?{field:e.field}:{});}
  }
  const api={executeTask,validateRequest,validateBridgeEvent,allowedTaskUrl};
  if(typeof module!=='undefined' && module.exports) module.exports=api;
  else root.MidnightHelper=api;
})(globalThis);
