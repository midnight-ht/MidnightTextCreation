from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_skill(input_path: Path) -> dict:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_skill.py"), str(input_path)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return json.loads(result.stdout)


def test_schema_files_are_valid_json() -> None:
    for path in (ROOT / "schemas").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))


def test_scoring_rules_are_used() -> None:
    from scripts.rule_scan import scan_text

    score = scan_text(
        "在当今时代，AI 正在赋能内容创作。",
        scoring_rules={
            "blacklist_hit_weight": 1,
            "meta_phrase_hit_weight": 1,
            "repeated_sentence_start_weight": 1,
            "paragraph_symmetry_penalty": 1,
            "list_overuse_penalty": 1,
            "generic_opening_penalty": 1,
            "generic_ending_penalty": 1,
            "max_score": 100,
        },
    )
    assert score["score_breakdown"]["blacklist_score"] == 2
    assert score["score_breakdown"]["generic_opening_penalty"] == 1


def test_runner_writes_markdown(tmp_path: Path) -> None:
    payload = {
        "title": "如何去掉 AI 写作味",
        "platform": "wechat",
        "language": "zh",
        "raw_material": "在当今时代，AI 正在全面赋能内容创作。本文将探讨如何降低 AI 写作味。总而言之，未来可期。",
        "output_dir": str(tmp_path),
        "max_rounds": 2,
        "pass_score": 25,
    }
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output = run_skill(input_path)

    assert output["ok"] is True
    assert output["execution_mode"] == "local_deterministic"
    assert output["platform_output"]["files"]
    assert Path(output["platform_output"]["files"][0]).exists()
    assert "赋能" in output["final_text"]
    assert "viral_judge_result" in output


def test_runner_handles_platform_configs(tmp_path: Path) -> None:
    payload = {
        "title": "Remove AI Slop",
        "platform": "generic",
        "language": "bilingual",
        "raw_material": "在当今时代，AI 正在赋能内容创作。",
        "output_dir": str(tmp_path),
        "platform_configs": {
            "wechat": {"language": "zh"},
            "linkedin": {"language": "en"},
        },
    }
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    output = run_skill(input_path)

    assert len(output["outputs"]) == 2
    assert {item["platform"] for item in output["outputs"]} == {"wechat", "linkedin"}
    assert len(output["platform_output"]["files"]) == 2
    assert all(len(item["platform_output"]["files"]) == 1 for item in output["outputs"])


def test_deep_slop_detects_vague_ending() -> None:
    from scripts.rule_scan import scan_text

    output = scan_text("这个方法可以提升效率。它会带来更多价值。未来它将在内容生产中发挥重要作用。")

    assert output["vague_claim_hits"]
    assert output["weak_ending"] is True
    assert output["deep_slop_score"] > 0


def test_specific_ending_is_not_penalized() -> None:
    from scripts.rule_scan import scan_text

    output = scan_text("未来的计划还没确定。最终先删掉第 3 段，再把来源补在表格下面。")
    assert output["weak_ending"] is False


def test_cleanup_preserves_quoted_terms() -> None:
    from scripts.run_skill import targeted_cleanup
    from scripts.rule_scan import scan_text

    text = "我不同意把‘重要’全部替换成‘值得认真处理’。例如，讨论赋能、闭环这些词时需要保留原词。"
    assert targeted_cleanup(text, scan_text(text)) == text


def test_english_scan_uses_explicit_language() -> None:
    from scripts.rule_scan import scan_text

    result = scan_text("This will deliver more value. It will unlock great potential.", language="en", blacklist=[])
    assert result["vague_claim_hits"]
    assert result["weak_ending"]


def test_thread_does_not_truncate_content() -> None:
    from scripts.run_skill import format_for_platform

    text = " ".join(f"Item {i}." for i in range(12))
    result = format_for_platform("Notes", "x_thread", "en", text)
    assert "Item 11." in result["body"]


def test_no_material_requires_review(tmp_path: Path) -> None:
    from scripts.run_skill import normalize_input, run_single

    result = run_single(normalize_input({"title": "New topic"}), "generic", "zh", tmp_path)
    assert result["status"] == "needs_human_review"


if __name__ == "__main__":
    import tempfile

    for name, test in list(globals().items()):
        if name.startswith("test_") and callable(test):
            if "tmp_path" in test.__code__.co_varnames[:test.__code__.co_argcount]:
                with tempfile.TemporaryDirectory() as directory:
                    test(Path(directory))
            else:
                test()
            print(f"PASS {name}")
