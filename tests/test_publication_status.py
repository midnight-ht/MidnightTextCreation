import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from tests.test_content_manager import config
from scripts.content_manager import ContentManager
from pathlib import Path
import tempfile

try:
    from scripts.publication_status import collect, latest, snapshot_from_result
except ImportError:
    collect = latest = snapshot_from_result = None


class StatusTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manager = ContentManager(self.root / 'data')
        self.manager.save_config(config(self.root),self.root)
        self.assertIsNotNone(collect, 'Publication status collection is not implemented')
        self.content = self.manager.generate('wa', {'title':'标题','raw_material':'正文'})
        self.pub = self.manager.associate(self.content['id'], 'external-1')

    def test_mock_cannot_be_treated_as_real_and_missing_metrics_are_null(self):
        snap = collect(self.manager, self.pub['id'])
        self.assertEqual(snap['source'],'mock')
        self.assertEqual(snap['status'],'processing')
        self.assertIsNone(snap['metrics']['reads'])
        self.assertEqual(latest(self.manager,self.pub['id'])['last_success']['id'],snap['id'])

    def test_browser_identity_mismatch_and_invalid_metric_are_rejected(self):
        for result in ({'platform_content_id':'wrong','raw_status':'published'},
                       {'platform_content_id':'external-1','raw_status':'published','metrics':{'reads':-1}},
                       {'platform_content_id':'external-1','raw_status':'published','metrics':{'reads':True}}):
            with self.subTest(result=result), self.assertRaises(ValueError): snapshot_from_result(self.pub,result,'browser',{})

    def test_failed_collection_preserves_last_success(self):
        good = collect(self.manager,self.pub['id'])
        cfg = config(self.root); cfg['bindings'][0]['adapter'] = {'mode':'api','endpoint':'http://127.0.0.1:1/status/{content_id}'}
        self.manager.save_config(cfg,self.root)
        failed = collect(self.manager,self.pub['id'])
        state = latest(self.manager,self.pub['id'])
        self.assertEqual(failed['query_state'],'failed')
        self.assertEqual(state['last_success']['id'],good['id'])
        self.assertEqual(state['latest']['id'],failed['id'])
        self.assertEqual(state['last_success']['source'],'mock')

    def test_real_http_adapter_validates_business_response_and_identity(self):
        responses = [{'platform_content_id':'external-1','account':'账号甲','raw_status':'online','metrics':{'reads':7}},
                     {'platform_content_id':'other','account':'账号甲','raw_status':'online'},
                     {'ok':False,'error':'failure','platform_content_id':'external-1','account':'账号甲','raw_status':'online'}]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                payload = json.dumps(responses.pop(0)).encode()
                self.send_response(200); self.end_headers(); self.wfile.write(payload)
            def log_message(self,*args): pass
        server = ThreadingHTTPServer(('127.0.0.1',0),Handler)
        thread = threading.Thread(target=server.serve_forever,daemon=True); thread.start()
        self.addCleanup(server.server_close); self.addCleanup(server.shutdown)
        cfg=config(self.root)
        cfg['bindings'][0]['adapter']={'mode':'api','endpoint':f'http://127.0.0.1:{server.server_port}/status/{{content_id}}','status_mapping':{'online':'published'}}
        self.manager.save_config(cfg,self.root)
        good=collect(self.manager,self.pub['id'])
        self.assertEqual(good['source'],'api'); self.assertEqual(good['status'],'published'); self.assertEqual(good['metrics']['reads'],7)
        self.assertEqual(collect(self.manager,self.pub['id'])['query_state'],'failed')
        self.assertEqual(collect(self.manager,self.pub['id'])['query_state'],'failed')
        self.assertEqual(latest(self.manager,self.pub['id'])['last_success']['metrics']['reads'],7)

    def test_mock_browser_collect_is_stored_with_mock_source(self):
        task=self.manager.create_task(self.content['id'],'collect','http://127.0.0.1:8765',self.pub['id'])
        done=self.manager.complete_task(task['id'],{'status':'collected','source':'mock','platform_content_id':'external-1','raw_status':'published','metrics':{'reads':2}})
        self.assertEqual(done['state'],'collected')
        self.assertEqual(latest(self.manager,self.pub['id'])['last_success']['source'],'mock')


if __name__=='__main__': unittest.main()

