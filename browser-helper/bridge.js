'use strict';
window.addEventListener('message', async event => {
  if(!MidnightHelper.validateBridgeEvent(event,window,location)) return;
  const message=event.data;
  let result;
  try {result=await chrome.runtime.sendMessage(message);} catch {result={status:'extension_unavailable'};}
  window.postMessage({type:'MIDNIGHT_RESPONSE',requestId:message.requestId,result},location.origin);
});
