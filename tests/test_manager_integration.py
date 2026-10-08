"""Integration regressions: failure snapshots, task dedupe and invalid config."""
import unittest
from tests.test_content_manager import config
from scripts.content_manager import ContentManager
from scripts.publication_status import latest, collect, poll_once, set_polling
from pathlib import Path
import tempfile

class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.m=ContentManager(self.root/'data');self.m.save_config(config(self.root),self.root)
        self.c=self.m.generate('wa',{'title':'标题','raw_material':'正文'});self.p=self.m.associate(self.c['id'],'p')

    def test_failure_browser_result_becomes_failed_snapshot_and_preserves_raw_error(self):
        good=collect(self.m,self.p['id'])
        task=self.m.create_task(self.c['id'],'collect','http://127.0.0.1:8765',self.p['id'])
        done=self.m.complete_task(task['id'],{'status':'content_id_mismatch','source':'mock'})
        self.assertEqual(done['state'],'failed')
        self.assertEqual(done['result']['status'],'content_id_mismatch')
        self.assertEqual(latest(self.m,self.p['id'])['latest']['query_state'],'failed')
        self.assertEqual(latest(self.m,self.p['id'])['last_success']['id'],good['id'])

    def test_duplicate_pending_click_reuses_task(self):
        a=self.m.create_task(self.c['id'],'fill','http://127.0.0.1:8765')
        b=self.m.create_task(self.c['id'],'fill','http://127.0.0.1:8765')
        self.assertEqual(a['id'],b['id'])

    def test_poll_due_stop_and_backoff(self):
        set_polling(self.m,self.p['id'],True,60)
        pub=self.m.get('publication',self.p['id']);pub['next_poll']=0;self.m.put('publication',pub)
        self.assertEqual(len(poll_once(self.m,'http://127.0.0.1:8765',100)),1)
        self.assertEqual(poll_once(self.m,'http://127.0.0.1:8765',101),[])
        set_polling(self.m,self.p['id'],False,60)
        self.assertEqual(poll_once(self.m,'http://127.0.0.1:8765',10000),[])

    def test_windows_reserved_ids_and_malformed_mappings_are_rejected(self):
        with self.assertRaises(ValueError): self.m.generate('wa',{'title':'x'},content_id='NUL')
        bad=config(self.root);bad['bindings'][0]['adapter']['status_mapping']=[]
        with self.assertRaises(ValueError):self.m.save_config(bad,self.root)

    def test_parallel_task_creation_in_one_manager_is_idempotent(self):
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=10) as pool:
            results=list(pool.map(lambda _:self.m.create_task(self.c['id'],'fill','http://127.0.0.1:8765'),range(10)))
        self.assertEqual(len({r['id'] for r in results}),1)

if __name__=='__main__':unittest.main()
