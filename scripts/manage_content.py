"""Loopback-only content manager service. No third-party Python dependencies."""
from __future__ import annotations
import argparse
import hmac
import json
import mimetypes
import os
import secrets
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from scripts.content_manager import ContentManager, now
from scripts.platform_layout import PROFILES
from scripts.publication_status import collect, latest, set_polling, poll_once, failed_snapshot

ROOT=Path(__file__).resolve().parents[1]
STATIC=ROOT/'manager'


def create_server(manager,port=8765):
    lock=threading.RLock()
    token=secrets.token_urlsafe(32)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,payload,content_type='application/json; charset=utf-8',extra=None):
            body=payload if isinstance(payload,bytes) else json.dumps(payload,ensure_ascii=False,allow_nan=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Referrer-Policy','no-referrer')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")
            for key,value in (extra or {}).items(): self.send_header(key,value)
            self.end_headers(); self.wfile.write(body)
        def guard(self,authenticated=False):
            port=self.server.server_port
            hosts={f'127.0.0.1:{port}',f'localhost:{port}'}
            host=self.headers.get('Host','')
            if host not in hosts: return False
            origin=self.headers.get('Origin')
            if origin and origin!='http://'+host: return False
            if self.headers.get('Sec-Fetch-Site') not in {None,'same-origin','none'}: return False
            if authenticated and not hmac.compare_digest(self.headers.get('X-Manager-Token',''),token): return False
            return True
        def do_GET(self):
            path=urlparse(self.path).path
            if not self.guard(path.startswith('/api/') and path!='/api/session'):
                self.send(403,{'ok':False,'error':'Local origin and session token required'}); return
            try:
                with lock:
                    if path=='/api/session': self.send(200,{'token':token}); return
                    if path=='/api/state':
                        expire_tasks(manager)
                        pubs=[{**p,'status':latest(manager,p['id'])} for p in manager.publications()]
                        self.send(200,{'config':manager.get_config(),'contents':manager.contents(),'publications':pubs,'tasks':manager.tasks(),
                                      'platforms':[{'id':key,'label':value['label'],'formats':value['formats']} for key,value in PROFILES.items()]}); return
                    if path=='/api/config/export':
                        self.send(200,manager.get_config(),extra={'Content-Disposition':'attachment; filename="account-config.json"'}); return
                routes={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/style.css':'style.css',
                        '/mock-editor.html':'mock-editor.html','/mock-editor.js':'mock-editor.js'}
                routes.update({'/manager/'+name:name for name in ('app.js','style.css','mock-editor.js','mock-editor.html')})
                if path not in routes or not (STATIC/routes[path]).is_file(): self.send(404,{'ok':False,'error':'Not found'}); return
                target=STATIC/routes[path]
                mime=mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
                self.send(200,target.read_bytes(),mime+'; charset=utf-8')
            except (ValueError,TypeError,OSError) as exc: self.send(400,{'ok':False,'error':str(exc)})
        def do_POST(self):
            if not self.guard(True): self.send(403,{'ok':False,'error':'Local origin and session token required'}); return
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<=2*1024*1024: raise ValueError('Request size must be 1 byte to 2 MiB')
                if self.headers.get_content_type()!='application/json': raise ValueError('Use application/json')
                self.connection.settimeout(10)
                raw=self.rfile.read(length)
                if len(raw)!=length: raise ValueError('Incomplete request')
                data=json.loads(raw)
                if not isinstance(data,dict): raise ValueError('Request must be an object')
                path=urlparse(self.path).path
                if path=='/api/collect':
                    result=collect(manager,data['publication_id'],'http://'+self.headers['Host'],lock=lock)
                    self.send(200,{'ok':True,'result':result}); return
                with lock:
                    base='http://'+self.headers['Host']
                    if path=='/api/config':
                        try: config_base=manager.get('settings','config')['base_dir']
                        except ValueError: config_base=manager.data_dir
                        result=manager.save_config(data['config'],config_base)
                    elif path=='/api/generate': result=manager.generate(data['binding_id'],data.get('input',{}),data.get('content_id'))
                    elif path=='/api/import-content': result=manager.import_content(data['binding_id'],data['publication'],data.get('review_status','needs_human_review'),data.get('content_id'),data.get('overrides'))
                    elif path=='/api/task': result=manager.create_task(data['version_id'],data['kind'],base,data.get('publication_id'))
                    elif path=='/api/complete': result=manager.complete_task(data['task_id'],data['result'])
                    elif path=='/api/associate': result=manager.associate(data['version_id'],data['platform_content_id'],data.get('url',''),data.get('published_at'))
                    elif path=='/api/collect': result=collect(manager,data['publication_id'],base)
                    elif path=='/api/poll': result=set_polling(manager,data['publication_id'],data['enabled'],data.get('interval',60))
                    elif path=='/api/open-directory':
                        folder=Path(manager.get('content',data['version_id'])['directory'])
                        if not folder.is_dir(): raise ValueError('Export folder no longer exists')
                        if os.name!='nt': raise ValueError('Open-directory button currently supports Windows; copy the displayed path')
                        subprocess.Popen(['explorer.exe',str(folder)])
                        result={'opened':True,'directory':str(folder)}
                    else: self.send(404,{'ok':False,'error':'Not found'}); return
                self.send(200,{'ok':True,'result':result})
            except (ValueError,TypeError,KeyError,OSError) as exc: self.send(400,{'ok':False,'error':str(exc)})
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.manager=manager; server.manager_lock=lock
    return server


def expire_tasks(manager):
    from datetime import datetime,timezone
    for task in manager.tasks():
        if task['state']=='pending' and (datetime.now(timezone.utc)-datetime.fromisoformat(task['created_at'])).total_seconds()>90:
            if task['kind']=='collect':
                failed_snapshot(manager,manager.get('publication',task['publication_id']),'mock' if task['platform']=='mock' else 'browser','task_timeout')
            task.update(state='failed',result={'status':'failed','error':'task_timeout'},completed_at=now())
            manager.put('task',task)


def polling_loop(server,stop):
    base=f'http://127.0.0.1:{server.server_port}'
    while not stop.wait(1):
        try:
            with server.manager_lock:
                expire_tasks(server.manager)
            poll_once(server.manager,base,lock=server.manager_lock)
        except (ValueError,TypeError,OSError):
            # Broken individual config is shown through immediate collection; loop remains available.
            continue


def main():
    parser=argparse.ArgumentParser(description='Local account content manager (loopback only)')
    parser.add_argument('--data-dir',default=str(ROOT/'feedback'/'manager-data'))
    parser.add_argument('--config',help='Import account configuration JSON; relative output paths use its directory')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true',help='Open local manager in the default browser')
    args=parser.parse_args()
    manager=ContentManager(args.data_dir)
    if args.config:
        config_path=Path(args.config).resolve()
        manager.save_config(json.loads(config_path.read_text(encoding='utf-8-sig')),config_path.parent)
    server=create_server(manager,args.port); stop=threading.Event()
    threading.Thread(target=polling_loop,args=(server,stop),daemon=True).start()
    url=f'http://127.0.0.1:{server.server_port}'
    print(f'Content manager: {url}',flush=True)
    if args.open: webbrowser.open(url)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: stop.set(); server.server_close()


if __name__=='__main__': main()
