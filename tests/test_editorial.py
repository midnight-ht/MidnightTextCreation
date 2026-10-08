import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.editorial import content_context, publication_record
from scripts.run_skill import normalize_input, run_single
from scripts.run_skill import platform_language_jobs, load_or_create_style_template
from scripts.calibrate_reviews import calibration_report


class EditorialTests(unittest.TestCase):
    def test_invalid_input_is_rejected(self):
        for payload in ({"platform": "wecaht"}, {"language": "fr"}, {"max_rounds": 1.9},
                        {"max_rounds": True}, {"pass_score": "25"},
                        {"platform_configs": {"wecaht": {}}},
                        {"platform_configs": {"wechat": []}},
                        {"platform_configs": {"wechat": {"format": "carousel"}}}):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                normalize_input(payload)

    def test_runner_preserves_code_and_checks_final_bundle(self):
        code = '```python\nif True:\n    print("first")\n    if True:\n        print("nested")\n```'
        with tempfile.TemporaryDirectory() as directory:
            result = run_single(normalize_input({"title": "Code", "raw_material": code}), "juejin", "en", Path(directory))
            self.assertEqual(result["final_text"], code)
            result = run_single(normalize_input({"title": "Forbidden title", "raw_material": "One. Two.", "forbidden_claims": ["Forbidden title"]}), "x_thread", "en", Path(directory))
            self.assertEqual(result["final_text"], result["platform_output"]["body"])
            self.assertIn("Forbidden title", result["editorial_review"]["facts"]["evidence"])

    def test_cleanup_preserves_code_transitions(self):
        from scripts.run_skill import targeted_cleanup
        text = '总而言之，先检查。\n\n```text\n总而言之，保留这段代码。\n    缩进\n```'
        result = targeted_cleanup(text, {})
        self.assertTrue(result.startswith("先检查。"))
        self.assertIn('```text\n总而言之，保留这段代码。\n    缩进\n```', result)

    def test_normalizer_preserves_multiple_and_unclosed_fences(self):
        from scripts.normalize_text import normalize_text
        text = 'Intro\n\n~~~python\nif True:\n\tprint(1)\n~~~\n\n```text\n    unclosed   \n\n\n'
        self.assertEqual(normalize_text(text), text)

    def test_context_preserves_sources(self):
        data = {"author_samples": ["Voice sample"], "facts": [{"id": "F1", "claim": "Supplied claim", "source": "Author interview"}]}
        self.assertEqual(content_context(data)["facts"], data["facts"])
        with self.assertRaises(ValueError):
            content_context({"facts": data["facts"] * 2})

    def test_local_review_does_not_invent_scores(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_single(normalize_input({"title": "Test", "raw_material": "A concrete opinion.", "author_samples": ["Example"]}), "generic", "en", Path(directory))
        self.assertIsNone(result["editorial_review"]["style"]["score"])
        self.assertEqual(result["candidate_comparison"]["mode"], "not_evaluated")

    def test_forbidden_claim_requires_review(self):
        with tempfile.TemporaryDirectory() as directory:
            result = run_single(normalize_input({"title": "Test", "raw_material": "Guaranteed success.", "forbidden_claims": ["Guaranteed success"]}), "generic", "en", Path(directory))
        self.assertEqual(result["status"], "needs_human_review")

    def feedback(self):
        return {"job_id": "job1", "platform": "wechat", "variant_id": "A", "published_at": "2026-10-04T10:00:00+08:00", "window_end": "2026-10-05T10:00:00+08:00", "metrics": {"impressions": 100, "clicks": 10}}

    def test_feedback_rates_and_missing_data(self):
        record = publication_record(self.feedback())
        self.assertEqual(record["rates"]["ctr"], 0.1)
        self.assertIsNone(record["rates"]["completion_rate"])
        self.assertEqual(record["experiment_design"], "observational")

    def test_invalid_metrics_and_experiment(self):
        for metrics in ({"clicks": -1}, {"impressions": 1, "clicks": 2}, {"clicks": float("nan")}, {"impressions": 1.5}):
            with self.assertRaises(ValueError):
                publication_record({**self.feedback(), "metrics": metrics})
        with self.assertRaises(ValueError):
            publication_record({**self.feedback(), "experiment_design": "randomized"})

    def test_cli_appends_feedback(self):
        with tempfile.TemporaryDirectory() as directory:
            input_path = Path(directory) / "input.json"
            log_path = Path(directory) / "log.jsonl"
            input_path.write_text(json.dumps(self.feedback()), encoding="utf-8")
            for _ in range(2):
                subprocess.run([sys.executable, "-m", "scripts.editorial", str(input_path), "--log", str(log_path)], check=True, capture_output=True)
            records = [json.loads(line) for line in log_path.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(len(records), 2)

    def test_bilingual_platform_defaults_and_format(self):
        data = normalize_input({"title": "Test", "raw_material": "One. Two.", "language": "bilingual", "platform_configs": {"wechat": {"tone": "Restrained", "format": "thread"}}})
        self.assertEqual(platform_language_jobs(data), [("wechat", "zh"), ("wechat", "en")])
        with tempfile.TemporaryDirectory() as directory:
            result = run_single(data, "wechat", "en", Path(directory))
        self.assertIn("2. Two.", result["platform_output"]["body"])
        self.assertEqual(result["platform_output"]["tone"], "Restrained")
        self.assertEqual(result["status"], "needs_human_review")

    def test_named_template_is_loaded(self):
        path, content = load_or_create_style_template({"style_template": "practical-essay", "output_dir": "."})
        self.assertTrue(path.endswith("practical-essay.md"))
        self.assertTrue(content)

    def test_calibration_counts_heldout_disagreements(self):
        record = {"id": "r1", "model_version": "test-model", "prompt_version": "v1", "human_reviewer": "editor", "split": "holdout", "human": {d: "needs_review" for d in ("facts", "style", "expression", "distribution")}, "model": {d: "pass" for d in ("facts", "style", "expression", "distribution")}}
        report = calibration_report([record])
        self.assertEqual(report["heldout_dimensions"]["facts"]["false_passes"], 1)
        self.assertEqual(report["heldout_dimensions"]["facts"]["agreement_rate"], 0)
        report = calibration_report([{**record, "split": "calibration"}])
        self.assertIsNone(report["heldout_dimensions"]["facts"]["agreement_rate"])


if __name__ == "__main__":
    unittest.main()
