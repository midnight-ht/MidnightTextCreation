import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_skill import SUPPORTED_PLATFORMS, format_for_platform, normalize_input, platform_language_jobs, run_single
from scripts.platform_layout import PROFILES, layout_content


class PlatformLayoutTests(unittest.TestCase):
    def test_catalog_and_schema_agree(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / 'schemas/input.schema.json').read_text(encoding='utf-8'))
        self.assertEqual(set(PROFILES), SUPPORTED_PLATFORMS)
        self.assertEqual(set(PROFILES), set(schema['properties']['platform']['enum']))
        for profile in PROFILES.values():
            self.assertIn(profile['default_format'], profile['formats'])
            self.assertTrue(profile['content_order'])
            self.assertTrue(profile['publishing_steps'])

    def test_new_platforms_do_not_fall_back(self):
        for platform in ('weibo', 'wechat_channels', 'facebook', 'reddit', 'threads', 'youtube', 'youtube_shorts'):
            self.assertEqual(normalize_input({'platform': platform})['platform'], platform)
            result = format_for_platform('Topic', platform, 'en', 'One. Two.')
            self.assertEqual(result['layout_plan']['platform'], platform)

    def test_carousel_has_source_only_cards(self):
        result = layout_content('xiaohongshu', 'First point.\n\nSecond point.', 'carousel')
        self.assertEqual([b['text'] for b in result['blocks']], ['First point.', 'Second point.'])
        self.assertTrue(all(b['kind'] == 'card' for b in result['blocks']))
        self.assertEqual(result['semantic_adaptation'], 'not_evaluated')

    def test_code_and_urls_are_not_split(self):
        text = 'See https://example.com/a.b at version 3.14.\n\n```python\nprint("A. B.")\n```'
        result = layout_content('x_thread', text)
        self.assertIn('https://example.com/a.b', result['body'])
        self.assertIn('3.14', result['body'])
        self.assertIn('```python\nprint("A. B.")\n```', result['body'])
        self.assertTrue(result['warnings'])

    def test_unclosed_code_preserves_trailing_content(self):
        text = '```text\n    content   \n\n\n'
        for platform in ('x_thread', 'juejin'):
            self.assertEqual(layout_content(platform, text)['body'], text)

    def test_all_formats_preserve_last_content(self):
        for platform, profile in PROFILES.items():
            for mode in profile['formats']:
                result = layout_content(platform, 'First.\n\nLast detail 99.', mode)
                self.assertIn('Last detail 99.', result['body'])
                self.assertTrue(result['blocks'])

    def test_runner_format_and_layout_stay_consistent(self):
        data = normalize_input({'title': 'Test', 'raw_material': 'One. Two.', 'platform_configs': {'instagram': {'format': 'carousel'}}})
        with tempfile.TemporaryDirectory() as directory:
            result = run_single(data, 'instagram', 'en', Path(directory))
        output = result['platform_output']
        self.assertEqual(output['format'], 'carousel')
        self.assertEqual(output['layout_plan']['format'], 'carousel')
        self.assertEqual(output['body'], output['layout_plan']['body'])

    def test_unknown_format_is_rejected(self):
        with self.assertRaises(ValueError):
            layout_content('wechat', 'Text', 'unknown')

    def test_multi_platform_example_writes_all_outputs(self):
        root = Path(__file__).resolve().parents[1]
        data = normalize_input(json.loads((root / 'examples/input_platform_layouts.json').read_text(encoding='utf-8')))
        with tempfile.TemporaryDirectory() as directory:
            results = [run_single(data, platform, language, Path(directory))
                       for platform, language in platform_language_jobs(data)]
            self.assertEqual(len(results), 6)
            for result in results:
                output = result['platform_output']
                self.assertTrue(Path(output['files'][0]).is_file())
                self.assertEqual(output['format'], output['layout_plan']['format'])
                self.assertEqual(result['status'], 'needs_human_review')


if __name__ == '__main__':
    unittest.main()
