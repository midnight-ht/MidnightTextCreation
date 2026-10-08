'use strict';
importScripts('runner.js');
const active=new Map();
function waitComplete(tabId,timeout=20000) {
  return new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>finish(new Error('page_timeout')),timeout);
    function finish(error,tab) {clearTimeout(timer);chrome.tabs.onUpdated.removeListener(updated);chrome.tabs.onRemoved.removeListener(removed);error?reject(error):resolve(tab);}
    function updated(id,change,tab) {if(id===tabId && change.status==='complete') finish(null,tab);}
    function removed(id) {if(id===tabId) finish(new Error('tab_closed'));}
    chrome.tabs.onUpdated.addListener(updated);
    chrome.tabs.onRemoved.addListener(removed);
    chrome.tabs.get(tabId).then(tab=>{if(tab.status==='complete') finish(null,tab);},()=>finish(new Error('tab_closed')));
  });
}
async function run(message,sender) {
  const source=message?.task?.platform==='mock'?'mock':'browser';
  const error=MidnightHelper.validateRequest(message,sender);
  if(error) return {status:error,source};
  const key=new URL(sender.url).origin+'|'+message.task.id;
  if(active.has(key)) return active.get(key);
  const operation=(async()=>{
    try {
      const tab=await chrome.tabs.create({url:message.task.url,active:true});
      await waitComplete(tab.id);
      const current=await chrome.tabs.get(tab.id);
      if(!MidnightHelper.allowedTaskUrl(current.url,message.task.platform) || (message.task.platform==='mock' && new URL(current.url).origin!==new URL(message.task.url).origin)) return {status:'url_rejected',source};
      const results=await chrome.scripting.executeScript({target:{tabId:tab.id},func:MidnightHelper.executeTask,args:[message.task]});
      return results[0]?.result || {status:'execution_failed',source};
    } catch(e) {return {status:['page_timeout','tab_closed'].includes(e.message)?e.message:'execution_failed',source};}
  })();
  active.set(key,operation);
  try {return await operation;} finally {active.delete(key);}
}
chrome.runtime.onMessage.addListener((message,sender,sendResponse)=>{
  if(message?.type!=='MIDNIGHT_REQUEST') return;
  run(message,sender).then(sendResponse,()=>sendResponse({status:'execution_failed'}));
  return true;
});
