'use strict';
const query=new URLSearchParams(location.search);
document.getElementById('account').textContent=query.get('account')||'';
document.getElementById('content-id').textContent=query.get('content_id')||'';
