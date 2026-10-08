import json
import tempfile
import unittest
from pathlib import Path

try:
    from scripts.content_manager import ContentManager
except ImportError:
    ContentManager = None


def config(root):
    return {'accounts': [{'id': 'a', 'name': '账号甲'}, {'id': 'b', 'name': '账号乙'}],
            'styles': [{'id': 'plain', 'name': '实用', 'tone': '直接', 'language': 'zh', 'format': 'long_form', 'style_guidance': '先写判断'}],
            'bindings': [{'id': 'wa', 'account_id': 'a', 'platform': 'wechat', 'expected_account': '账号甲', 'style_id': 'plain', 'output_dir': str(root / '中文 空格'), 'adapter': {'mode': 'mock'}},
                         {'id': 'wb', 'account_id': 'b', 'platform': 'wechat', 'expected_account': '账号乙', 'style_id': 'plain', 'output_dir': str(root / '另一个目录'), 'adapter': {'mode': 'mock'}}]}


class ManagerTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(ContentManager, 'Account content management is not implemented')
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.manager = ContentManager(self.root / 'data')
        self.manager.save_config(config(self.root), self.root)

    def test_config_survives_restart_and_invalid_references_do_not_replace_it(self):
        other = ContentManager(self.root / 'data')
        self.assertEqual(other.get_config()['accounts'][0]['name'], '账号甲')
        bad = config(self.root)
        bad['bindings'][0]['account_id'] = 'missing'
        with self.assertRaises(ValueError): self.manager.save_config(bad, self.root)
        self.assertEqual(other.get_config()['bindings'][0]['account_id'], 'a')

    def test_output_is_account_isolated_and_new_versions_never_overwrite(self):
        payload = {'title': '同名', 'raw_material': '先核对证据，再检查实际标题。'}
        a = self.manager.generate('wa', payload, content_id='post')
        b = self.manager.generate('wb', payload, content_id='post')
        again = self.manager.generate('wa', payload, content_id='post')
        self.assertNotEqual(a['version_id'], again['version_id'])
        self.assertNotEqual(a['directory'], b['directory'])
        self.assertTrue(Path(a['directory']).is_relative_to(self.root / '中文 空格' / 'a' / 'wechat' / 'post'))
        self.assertEqual(json.loads((Path(a['directory']) / 'publication.json').read_text(encoding='utf-8'))['body'], '先核对证据，再检查实际标题。')
        self.assertEqual(a['review_status'], 'needs_human_review')
        self.assertEqual(len(ContentManager(self.root / 'data').contents()), 3)

    def test_resolution_preserves_task_facts_and_task_override(self):
        data = self.manager.resolve('wa', {'tone': '任务语气', 'output_dir': '任务输出', 'facts': []})
        self.assertEqual(data['tone'], '任务语气')
        self.assertEqual(data['style_guidance'], '先写判断')
        self.assertEqual(data['facts'], [])
        self.assertEqual(data['output_dir'], str(self.root / '任务输出'))

    def test_bad_ids_empty_paths_and_platform_override_fail(self):
        for payload in ({'output_dir': ''}, {'platform': 'toutiao'}, {'platform_configs': {'toutiao': {}}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError): self.manager.resolve('wa', payload)
        with self.assertRaises(ValueError): self.manager.generate('wa', {'title': 'x'}, content_id='../escape')
        bad = config(self.root); bad['accounts'].append(bad['accounts'][0])
        with self.assertRaises(ValueError): self.manager.save_config(bad, self.root)

    def test_task_binds_version_and_fill_completion_is_not_publication(self):
        content = self.manager.generate('wa', {'title': '标题', 'raw_material': '实际正文'})
        task = self.manager.create_task(content['id'], 'fill', 'http://127.0.0.1:8765')
        self.assertEqual(task['publication']['body'], '实际正文')
        self.assertEqual(task['expected_account'], '账号甲')
        with self.assertRaises(ValueError): self.manager.complete_task(task['id'], {'status': 'published'})
        done = self.manager.complete_task(task['id'], {'status': 'filled', 'source': 'mock', 'fields': ['title','body']})
        self.assertEqual(done['state'], 'filled')
        self.assertEqual(self.manager.publications(), [])

    def test_imported_model_output_retains_metadata_and_version(self):
        bundle = {'selected_title': '模型标题', 'body': '真实稿件', 'summary': '摘要', 'tags': ['编辑'], 'cover_text': '封面'}
        record = self.manager.import_content('wa', bundle, review_status='ready_for_human_review')
        self.assertEqual(record['publication']['summary'], '摘要')
        self.assertEqual(record['publication']['cover_text'], '封面')
        self.assertEqual(record['review_status'], 'ready_for_human_review')


if __name__ == '__main__': unittest.main()

