import unittest
import tests.test_manager_integration as fixture_module
from scripts.publication_status import snapshot_from_result,latest,poll_once,set_polling
from datetime import datetime,timezone,timedelta
from scripts.manage_content import expire_tasks

class ReviewRegressions(unittest.TestCase):
    setUp=fixture_module.IntegrationTests.setUp

    def test_daily_poll_does_not_run_hourly(self):
        set_polling(self.m,self.p['id'],True,86400)
        pub=self.m.get('publication',self.p['id']);pub['next_poll']=0;self.m.put('publication',pub)
        poll_once(self.m,'http://127.0.0.1:8765',100)
        self.assertEqual(self.m.get('publication',self.p['id'])['next_poll'],86500)

    def test_oversized_metric_is_validation_error(self):
        with self.assertRaises(ValueError): snapshot_from_result(self.p,{'platform_content_id':'p','raw_status':'published','metrics':{'reads':10**400}},'api',{})

    def test_task_timeout_updates_latest_collection_error(self):
        task=self.m.create_task(self.c['id'],'collect','http://127.0.0.1:8765',self.p['id'])
        task['created_at']=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat();self.m.put('task',task)
        expire_tasks(self.m)
        self.assertEqual(latest(self.m,self.p['id'])['latest']['query_state'],'failed')

    def test_old_upstream_snapshot_is_stale_even_if_fetched_now(self):
        old=(datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        snap=snapshot_from_result(self.p,{'platform_content_id':'p','raw_status':'published','observed_at':old},'api',{})
        self.m.put('snapshot',snap)
        self.assertEqual(latest(self.m,self.p['id'])['freshness'],'stale')

    def test_offset_upstream_time_is_compared_as_instant(self):
        old=(datetime.now(timezone.utc)-timedelta(hours=2)).astimezone(timezone(timedelta(hours=8))).isoformat()
        snap=snapshot_from_result(self.p,{'platform_content_id':'p','raw_status':'published','observed_at':old},'api',{})
        self.m.put('snapshot',snap)
        self.assertEqual(latest(self.m,self.p['id'])['freshness'],'stale')
        self.assertGreater(latest(self.m,self.p['id'])['age_seconds'],7000)

if __name__=='__main__': unittest.main()

