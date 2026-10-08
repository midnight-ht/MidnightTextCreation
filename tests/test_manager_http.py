import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from scripts.content_manager import ContentManager
from tests.test_content_manager import config

try:
    from scripts.manage_content import create_server
except ImportError:
    create_server=None


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(create_server,'Local management service is not implemented')
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve(); self.manager=ContentManager(self.root/'data')
        self.manager.save_config(config(self.root),self.root)
        self.server=create_server(self.manager,port=0)
        self.addCleanup(self.server.server_close); self.addCleanup(self.server.shutdown)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.base=f'http://127.0.0.1:{self.server.server_port}'
        self.token=self.get('/api/session')['token']

    def get(self,path,headers=None):
        try:
            with urlopen(Request(self.base+path,headers=headers or {})) as response: return json.load(response)
        except HTTPError as error:
            error.close()
            raise

    def post(self,path,data,headers=None):
        fields={'Content-Type':'application/json','X-Manager-Token':self.token,'Origin':self.base,**(headers or {})}
        try:
            with urlopen(Request(self.base+path,data=json.dumps(data).encode(),headers=fields)) as response: return json.load(response)['result']
        except HTTPError as error:
            error.close()
            raise

    def test_end_to_end_export_fill_association_and_mock_status(self):
        content=self.post('/api/generate',{'binding_id':'wa','input':{'title':'标题','raw_material':'正文'}})
        task=self.post('/api/task',{'version_id':content['id'],'kind':'fill'})
        done=self.post('/api/complete',{'task_id':task['id'],'result':{'status':'filled','source':'mock'}})
        self.assertEqual(done['state'],'filled')
        pub=self.post('/api/associate',{'version_id':content['id'],'platform_content_id':'post-1'})
        snap=self.post('/api/collect',{'publication_id':pub['id']})
        self.assertEqual(snap['source'],'mock')
        state=self.get('/api/state',{'X-Manager-Token':self.token})
        self.assertEqual(state['publications'][0]['status']['last_success']['status'],'processing')
        self.assertTrue(Path(content['directory'],'manifest.json').is_file())

    def test_foreign_origin_missing_token_and_rebinding_host_are_rejected(self):
        for headers in ({'Origin':'https://evil.example'}, {'X-Manager-Token':'wrong'}):
            with self.subTest(headers=headers),self.assertRaises(HTTPError) as error: self.post('/api/config',{'config':config(self.root)},headers)
            self.assertEqual(error.exception.code,403)
        for headers in ({'Host':'evil.example'}, {'Origin':'https://evil.example'}, {'Sec-Fetch-Site':'cross-site'}):
            with self.subTest(headers=headers),self.assertRaises(HTTPError) as error: self.get('/api/session',headers)
            self.assertEqual(error.exception.code,403)
        with self.assertRaises(HTTPError) as error: self.get('/api/state')
        self.assertEqual(error.exception.code,403)

    def test_config_export_and_polling_stop(self):
        exported=self.get('/api/config/export',{'X-Manager-Token':self.token})
        self.assertEqual(exported['accounts'][0]['id'],'a')
        record=self.manager.generate('wa',{'title':'标题','raw_material':'正文'})
        pub=self.manager.associate(record['id'],'p')
        result=self.post('/api/poll',{'publication_id':pub['id'],'enabled':True,'interval':60})
        self.assertTrue(result['polling'])
        self.assertFalse(self.post('/api/poll',{'publication_id':pub['id'],'enabled':False,'interval':60})['polling'])
        with self.assertRaises(HTTPError): self.post('/api/poll',{'publication_id':pub['id'],'enabled':True,'interval':1})


    def test_concurrent_browser_collection_reuses_one_pending_task(self):
        from concurrent.futures import ThreadPoolExecutor
        content=self.manager.generate('wa',{'title':'标题','raw_material':'正文'})
        pub=self.manager.associate(content['id'],'external-1')
        cfg=config(self.root)
        cfg['bindings'][0]['adapter']={'mode':'browser','collector_url':'https://mp.weixin.qq.com/',
                                      'selectors':{'account':'#a','content_id':'#id','status':'#state'}}
        self.manager.save_config(cfg,self.root)
        with ThreadPoolExecutor(max_workers=10) as pool:
            results=list(pool.map(lambda _:self.post('/api/collect',{'publication_id':pub['id']}),range(10)))
        self.assertEqual(len({r['task']['id'] for r in results}),1)

    def test_malformed_url_returns_validation_error_without_disconnecting(self):
        cfg=config(self.root);cfg['bindings'][0]['adapter']['editor_url']={'bad':'type'}
        with self.assertRaises(HTTPError) as error:self.post('/api/config',{'config':cfg})
        self.assertEqual(error.exception.code,400)
        error.exception.close()
        self.assertEqual(self.get('/api/state',{'X-Manager-Token':self.token})['config']['bindings'][0]['adapter']['mode'],'mock')

if __name__=='__main__': unittest.main()
