#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Local runner for midnight-advertorial.

This runner is deterministic. It does not call an LLM, but it completes the
local parts of the skill contract: input normalization, rule scanning, a simple
targeted cleanup pass, platform formatting, and Markdown file output.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from platform_layout import PROFILES, layout_content
    from editorial import content_context, local_review
    from normalize_text import normalize_text, split_sentences, transform_prose
    from rule_scan import ROOT, scan_text
except ImportError:
    from scripts.platform_layout import PROFILES, layout_content
    from scripts.editorial import content_context, local_review
    from scripts.normalize_text import normalize_text, split_sentences, transform_prose
    from scripts.rule_scan import ROOT, scan_text


SUPPORTED_PLATFORMS = set(PROFILES)

DOMESTIC_PLATFORMS = {key for key, profile in PROFILES.items() if profile["region"] == "domestic"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_rules(name: str) -> list[str]:
    return load_json(ROOT / "rules" / name)


def load_rule_object(name: str) -> dict[str, Any]:
    return load_json(ROOT / "rules" / name)


def normalize_input(data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError("Input must be an object")
    for key in ("title", "topic", "platform", "language", "raw_material", "text", "content", "tone", "format", "core_opinion", "cover_text"):
        if key in data and not isinstance(data[key], str):
            raise ValueError(f"{key} must be a string")
    title = data.get("title") or data.get("topic") or "未命名文章"
    platform = data.get("platform", "generic")
    if platform not in SUPPORTED_PLATFORMS:
        raise ValueError("Unsupported platform")

    language = data.get("language", "zh")
    if language not in {"zh", "en", "bilingual"}:
        raise ValueError("Invalid language")
    for key, fallback, upper in (("max_rounds", 2, 10), ("pass_score", 25, 100)):
        value = data.get(key, fallback)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or not 0 <= value <= upper:
            raise ValueError(f"{key} must be an integer between 0 and {upper}")
    configs = data.get("platform_configs", {})
    if not isinstance(configs, dict):
        raise ValueError("platform_configs must be an object")
    for target, config in configs.items():
        if target not in SUPPORTED_PLATFORMS or not isinstance(config, dict):
            raise ValueError("Invalid platform configuration")
        if config.get("language", language) not in {"zh", "en", "bilingual"}:
            raise ValueError("Invalid platform language")
        if "tone" in config and not isinstance(config["tone"], str):
            raise ValueError("Platform tone must be a string")
        mode = config.get("format", data.get("format", PROFILES[target]["default_format"]))
        if not isinstance(mode, str) or mode not in PROFILES[target]["formats"]:
            raise ValueError(f"Unsupported format for {target}")
    if not configs and "format" in data and data["format"] not in PROFILES[platform]["formats"]:
        raise ValueError("Unsupported platform format")

    normalized = {
        **data,
        "title": title,
        "platform": platform,
        "language": language,
        "target_reader": data.get("target_reader") or ("中文内容读者" if language != "en" else "English-speaking readers"),
        "content_goal": data.get("content_goal") or "输出一篇低 AI 味、可发布的文章",
        "raw_material": data.get("raw_material") or data.get("text") or data.get("content") or "",
        "core_opinion": data.get("core_opinion") or "",
        "tone": data.get("tone") or ("直接、清晰、有经验感，不要营销腔" if language != "en" else "clear, practical, experienced"),
        "forbidden_style": data.get("forbidden_style") or "不要宏大开头，不要结尾升华，不要过度列表化，不要 AI 套话",
        "personal_examples": data.get("personal_examples") or "",
        "output_dir": data.get("output_dir") or str(ROOT),
        "max_rounds": int(data.get("max_rounds", 2)),
        "pass_score": int(data.get("pass_score", 25)),
    }
    if not 0 <= normalized["max_rounds"] <= 10:
        raise ValueError("max_rounds must be between 0 and 10")
    if not 0 <= normalized["pass_score"] <= 100:
        raise ValueError("pass_score must be between 0 and 100")
    normalized["content_context"] = content_context(data)
    return normalized


def load_or_create_style_template(data: dict[str, Any]) -> tuple[str, str]:
    requested = data.get("style_template")
    if requested:
        for path in (Path(requested), ROOT / "styles" / f"{requested}.md"):
            if path.is_file():
                return str(path.resolve()), path.read_text(encoding="utf-8")
    search_dirs = [Path(data["output_dir"]), ROOT]
    filenames = ["风格模板.md", "style-template.md", "style-templates.md", "writing-style.md"]
    for directory in search_dirs:
        for filename in filenames:
            path = directory / filename
            if path.exists():
                return str(path), path.read_text(encoding="utf-8")

    if not data.get("style_template"):
        return "", ""

    path = Path(data["output_dir"]) / "风格模板.md"
    content = """# 风格模板

## 纪实克制
少形容，多现场。把判断落在具体人、具体事和具体代价上。

## 评论随笔
允许有立场，但每个判断后面要有理由，不靠情绪推进。

## 实用拆解
先指出问题，再给判断标准，最后给可操作步骤。

## 口语短文
短句、少术语，像作者对一个具体读者解释问题。

## 深度长文
保留复杂性，不急着下结论，用案例和限制条件推进。

## Practical Essay
Clear thesis, concrete constraints, and practical advice without corporate filler.

## Personal Commentary
A visible point of view with lived context and restrained polish.

## Founder/Operator Note
Direct, specific, tradeoff-aware, and grounded in decisions.
"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return str(path), content


def choose_structure_template(platform: str) -> str:
    if platform in {"toutiao", "zhihu", "blog", "wechat"}:
        return "conflict_breakdown"
    if platform in {"xiaohongshu", "douyin_long_text", "kuaishou"}:
        return "identity_mirror"
    if platform in {"x_thread", "linkedin"}:
        return "opinion_reversal"
    if platform in {"substack", "medium"}:
        return "experience_review"
    return "conflict_breakdown"


def make_topic_tension(data: dict[str, Any], text: str) -> dict[str, Any]:
    title = data["title"]
    reader = data["target_reader"]
    template = choose_structure_template(data["platform"])
    topic_strength = "usable" if data.get("core_opinion") or len(split_sentences(text)) >= 3 else "weak"
    return {
        "topic_strength": topic_strength,
        "core_tension": data.get("core_opinion") or f"{title} 的通用说法和读者真实处境之间的落差",
        "reader_mirror": f"{reader} 在具体写作、发布或修改时遇到的卡点。",
        "counter_position": "常见做法是先修词句，但更大的问题通常在结构、判断和例子。",
        "recommended_structure": template,
    }


def safe_filename(title: str, platform: str, language: str) -> str:
    if language == "en":
        base = re.sub(r"[^a-zA-Z0-9]+", "-", title.lower()).strip("-") or "article"
    else:
        base = re.sub(r'[\\/:*?"<>|\s]+', "", title).strip() or "未命名文章"
    return f"{base}-{platform}-{language}.md"


def strip_patterns(text: str, patterns: list[str]) -> str:
    cleaned = text
    for pattern in patterns:
        try:
            cleaned = re.sub(pattern, "", cleaned)
        except re.error:
            cleaned = cleaned.replace(pattern, "")
    return cleaned


def targeted_cleanup(text: str, scan: dict[str, Any]) -> str:
    if not text:
        return text
    # Only remove standalone transition prefixes; content words need an editor.
    return normalize_text(transform_prose(text, lambda prose: re.sub(r"(^|\n)(总而言之|综上所述)[，,：:]?", r"\1", prose)))


def make_structure_plan(data: dict[str, Any], text: str) -> dict[str, Any]:
    thesis = data["core_opinion"] or f"围绕“{data['title']}”给出一个更具体、可负责的判断"
    topic_tension = make_topic_tension(data, text)
    return {
        "topic_tension": topic_tension,
        "opening_strategy": "直接从读者遇到的具体问题进入，不写时代背景。",
        "main_thesis": thesis,
        "structure": [
            {
                "section_title": "先指出真正的问题",
                "section_goal": "把问题从词语替换推进到结构、判断和例子。",
                "key_points": ["识别泛泛开头", "检查作者判断", "确认例子是否真实"],
                "evidence_needed": ["原文中最像模板的句子"],
                "length_weight": "medium",
            },
            {
                "section_title": "再做局部修改",
                "section_goal": "只修影响可信度的地方，避免越改越顺滑。",
                "key_points": ["删元叙述", "减少空泛形容", "结尾停在具体建议"],
                "evidence_needed": ["规则扫描命中的片段"],
                "length_weight": "medium",
            },
        ],
        "ending_strategy": "以一个具体判断或下一步动作结束，不升华。",
        "do_not_write": ["宏大时代开头", "综上所述式结尾", "虚构案例和数据"],
        "evidence_to_collect": ["读者真实场景", "作者自己的判断依据", "能说明限制条件的例子"],
        "source_sentence_count": len(split_sentences(text)),
    }


def judge_from_scan(scan: dict[str, Any], pass_score: int) -> dict[str, Any]:
    score = scan["ai_slop_rule_score"]
    issues: list[dict[str, str]] = []
    for hit in scan.get("blacklist_hits", [])[:5]:
        issues.append({
            "type": "banned_phrase",
            "severity": "medium",
            "evidence": hit["pattern"],
            "why_it_feels_ai": "高频模板词会让判断显得可替换。",
            "fix": "换成具体动作、场景或代价。",
        })
    for hit in scan.get("meta_hits", [])[:3]:
        issues.append({
            "type": "meta_phrase",
            "severity": "medium",
            "evidence": hit["pattern"],
            "why_it_feels_ai": "元叙述在解释文章要做什么，而不是直接推进内容。",
            "fix": "删除这类提示语，直接进入判断。",
        })
    if scan.get("generic_opening"):
        issues.append({
            "type": "generic_opening",
            "severity": "high",
            "evidence": "开头使用泛背景句",
            "why_it_feels_ai": "任何主题都能套用，缺少具体问题。",
            "fix": "用读者的具体困境或原文问题开头。",
        })
    if scan.get("generic_ending"):
        issues.append({
            "type": "generic_ending",
            "severity": "high",
            "evidence": "结尾使用泛总结或未来展望",
            "why_it_feels_ai": "结尾没有落到作者判断或行动建议。",
            "fix": "停在具体判断、限制条件或下一步动作。",
        })
    for hit in scan.get("vague_claim_hits", [])[:5]:
        issues.append({
            "type": "vague_claim",
            "severity": "medium",
            "evidence": hit["pattern"],
            "why_it_feels_ai": "这类句子看起来完整，但不需要作者承担具体判断。",
            "fix": "改成场景、动作、代价或边界条件。",
        })
    if scan.get("weak_ending"):
        issues.append({
            "type": "weak_ending",
            "severity": "high",
            "evidence": "结尾停在泛化价值、未来趋势或抽象提醒",
            "why_it_feels_ai": "结尾像通用收束，不像真实作者做出的最后判断。",
            "fix": "删掉泛化升华，停在一个可执行动作或适用边界。",
        })
    if scan.get("specificity_marker_count") == 0 and scan.get("sentence_count", 0) >= 3:
        issues.append({
            "type": "low_specificity",
            "severity": "medium",
            "evidence": "缺少例子、数字、限制、代价或具体动作",
            "why_it_feels_ai": "文本可迁移到很多主题，缺少不可替换的信息。",
            "fix": "补入真实场景或明确标记需要作者补素材。",
        })
    return {
        "ai_slop_score": score,
        "verdict": "pass" if score <= pass_score else "rewrite",
        "main_problem": "规则扫描命中较多模板表达。" if score > pass_score else "未发现明显规则层面的 AI 模板问题。",
        "issues": issues,
        "keep": ["保留原文中可验证的信息和作者真实判断。"],
        "rewrite_brief": "删除元叙述和泛背景句，把空泛词改成具体判断；不要补不存在的事实。",
    }


def local_viral_judge(data: dict[str, Any], platform: str, text: str, platform_output: dict[str, Any]) -> dict[str, Any]:
    sentences = split_sentences(text)
    first_sentence = sentences[0] if sentences else ""
    title_text = platform_output.get("selected_title", data["title"])
    has_tension = any(word in text for word in ["不是", "但", "误区", "问题", "代价", "限制", "取舍", "but", "tradeoff"])
    has_reader_mirror = bool(data.get("target_reader")) and any(word in text for word in ["你", "创作者", "读者", "用户", "团队", "作者"])
    has_specificity = any(word in text for word in ["比如", "例如", "一次", "当时", "后来", "因为", "具体", "限制", "代价", "取舍"]) or bool(re.search(r"\d+", text))
    has_comment_trigger = platform in {"toutiao", "zhihu", "bilibili", "youtube_community"} and any(word in text for word in ["争议", "不同意", "你会", "问题"])

    title_score = 70 if any(word in title_text for word in ["问题", "别", "不是", "如何", "为什么"]) else 45
    hook_score = 70 if first_sentence and not re.match(r"^(在当今|随着|近年来|如今|当前|现在)", first_sentence) else 40
    reader_score = 75 if has_reader_mirror else 45
    tension_score = 75 if has_tension else 40
    specificity_score = 75 if has_specificity else 35
    viral_score = round((title_score + hook_score + reader_score + tension_score + specificity_score) / 5)

    gaps = []
    if title_score < 60:
        gaps.append("标题缺少具体问题、冲突或反向判断。")
    if hook_score < 60:
        gaps.append("开头没有快速进入读者现场。")
    if reader_score < 60:
        gaps.append("读者镜像不够具体。")
    if specificity_score < 60:
        gaps.append("缺少真实例子、动作、限制或代价。")

    return {
        "viral_score": viral_score,
        "hook_score": hook_score,
        "title_score": title_score,
        "reader_mirror_score": reader_score,
        "tension_score": tension_score,
        "specificity_score": specificity_score,
        "share_reason": "none",
        "comment_trigger": "none",
        "main_viral_gap": gaps[0] if gaps else "传播基础可用，但仍需人工确认标题和开头是否足够贴近平台。",
        "fix_brief": "优先强化标题和前三行：写出读者正在经历的卡点、一个反常识判断，以及一个具体代价。",
        "mode": "local_heuristic",
    }


def format_for_platform(title: str, platform: str, language: str, text: str, mode: str | None = None) -> dict[str, Any]:
    layout = layout_content(platform, text, mode)
    body = layout["body"]
    tags: list[str] = []
    image_style = "none"
    image_usage = "none"
    image_reason = "none"
    if language == "en":
        title_options = [title]
        summary = "A cleaner, more specific draft with generic phrasing reduced."
        cover_prompt = "none"
        hook_lines = split_sentences(body)[:3] or [summary]
        share_trigger = "none"
        comment_trigger = "none"
    else:
        title_options = [title]
        summary = "已按规则扫描结果减少套话、元叙述和泛泛结尾。"
        cover_prompt = "none"
        hook_lines = split_sentences(body)[:3] or [summary]
        share_trigger = "none"
        comment_trigger = "none"

    return {
        "title_options": title_options,
        "summary": summary,
        "body": body,
        "tags": tags,
        "cover_prompt": cover_prompt,
        "image_style": image_style,
        "image_usage": image_usage,
        "image_reason": image_reason,
        "hook_lines": hook_lines,
        "share_trigger": share_trigger,
        "comment_trigger": comment_trigger,
        "publish_notes": "本地 runner 未调用大模型，发布前仍需人工确认事实、语气和例子。 " + layout["native_note"],
        "layout_plan": layout,
        "files": [],
    }


def write_markdown(output_dir: Path, title: str, platform: str, language: str, body: str) -> str:
    filename = safe_filename(title, platform, language)
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {title}\n\n{body}\n", encoding="utf-8")
    return str(path)


def run_single(data: dict[str, Any], platform: str, language: str, output_dir: Path) -> dict[str, Any]:
    config = (data.get("platform_configs") or {}).get(platform, {})
    data = {**data, **{key: config[key] for key in ("tone", "format") if key in config}, "platform": platform, "language": language}
    text = normalize_text(data["raw_material"])
    has_material = bool(text)
    if not text:
        text = normalize_text(data["core_opinion"] or data["title"])

    blacklist = load_rules("en_blacklist.json") if language == "en" else None
    meta_phrases = load_rules("en_meta_phrases.json") if language == "en" else None
    versions: dict[str, str] = {"draft_v0": text}
    rounds = 0
    scan = scan_text(text, blacklist=blacklist, meta_phrases=meta_phrases, language=language)
    pass_score = data["pass_score"]
    max_rounds = data["max_rounds"]

    while scan["ai_slop_rule_score"] > pass_score and rounds < max_rounds:
        cleaned = targeted_cleanup(text, scan)
        if cleaned == text:
            break
        text = cleaned
        rounds += 1
        versions[f"draft_v{rounds}"] = text
        scan = scan_text(text, blacklist=blacklist, meta_phrases=meta_phrases, language=language)

    score = scan["ai_slop_rule_score"]
    judge = judge_from_scan(scan, pass_score)
    requested_format = data.get("format")
    platform_output = format_for_platform(data["title"], platform, language, text, requested_format)
    platform_output["selected_title"] = data["title"]
    platform_output["cover_text"] = data.get("cover_text", "")
    platform_output["tone"] = data["tone"]
    platform_output["format"] = platform_output["layout_plan"]["format"]
    platform_output["style_guidance"] = data.get("style_guidance", "")
    final_body = platform_output["body"]
    reviewed_text = "\n".join([platform_output["selected_title"], platform_output["cover_text"], platform_output["summary"], final_body, *platform_output["hook_lines"], *platform_output["tags"]])
    scan = scan_text(reviewed_text, blacklist=blacklist, meta_phrases=meta_phrases, language=language)
    score = scan["ai_slop_rule_score"]
    judge = judge_from_scan(scan, pass_score)
    viral_judge = local_viral_judge(data, platform, final_body, platform_output)
    context = data.get("content_context") or content_context(data)
    review = local_review(reviewed_text, context, scan, viral_judge)
    file_path = write_markdown(output_dir, data["title"], platform, language, platform_output["body"])
    platform_output["files"].append(file_path)

    return {
        "language": language,
        "platform": platform,
        "status": "needs_human_review",
        "review_reasons": ["Local mode requires semantic facts and author-style review."],
        "final_text": final_body,
        "ai_slop_score": score,
        "round": rounds,
        "judge_result": judge,
        "viral_judge_result": viral_judge,
        "editorial_review": review,
        "content_context": context,
        "candidate_comparison": {"mode": "not_evaluated", "reason": "Local mode preserves supplied title; model comparison required."},
        "rule_scan": scan,
        "versions": versions,
        "structure_json": make_structure_plan(data, text),
        "platform_output": platform_output,
    }


def platform_language_jobs(data: dict[str, Any]) -> list[tuple[str, str]]:
    configs = data.get("platform_configs") or {}
    if isinstance(configs, dict) and configs:
        jobs = []
        for platform, config in configs.items():
            if platform not in SUPPORTED_PLATFORMS:
                raise ValueError("Unsupported configured platform")
            if not isinstance(config, dict):
                raise ValueError("Invalid platform configuration")
            language = config.get("language", data["language"]) if isinstance(config, dict) else data["language"]
            if language not in {"zh", "en", "bilingual"}:
                raise ValueError("Invalid platform language")
            jobs.extend((platform, lang) for lang in (["zh", "en"] if language == "bilingual" else [language]))
        if jobs:
            return jobs

    if data["language"] == "bilingual":
        return [(data["platform"], "zh"), (data["platform"], "en")]
    return [(data["platform"], data["language"])]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Path to JSON input file")
    parser.add_argument("--json-out", help="Optional path for the structured JSON result")
    parser.add_argument("--account-config", help="Import account configuration for a managed run")
    parser.add_argument("--binding", help="Account/platform binding ID for an isolated managed export")
    parser.add_argument("--data-dir", help="Managed record storage directory")
    args = parser.parse_args()

    if args.account_config and not args.binding:
        parser.error("--account-config requires --binding")
    if args.binding:
        from scripts.content_manager import ContentManager
        manager = ContentManager(args.data_dir or ROOT / 'feedback' / 'manager-data')
        if args.account_config:
            config_path = Path(args.account_config).resolve()
            manager.save_config(json.loads(config_path.read_text(encoding='utf-8-sig')), config_path.parent)
        content = manager.generate(args.binding, load_json(Path(args.input)))
        result = json.loads((Path(content['directory']) / 'review.json').read_text(encoding='utf-8'))
        output = {**result, 'ok': True, 'execution_mode': 'local_deterministic', 'managed_content': content}
        if args.json_out:
            write_json(Path(args.json_out), output)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return

    data = normalize_input(load_json(Path(args.input)))
    output_dir = Path(data["output_dir"])
    style_path, _style_content = load_or_create_style_template(data)
    data["style_guidance"] = _style_content
    jobs = platform_language_jobs(data)
    results = [run_single(data, platform, language, output_dir) for platform, language in jobs]

    first = results[0]
    files = [file for result in results for file in result["platform_output"].get("files", [])]
    output = {
        "ok": True,
        "execution_mode": "local_deterministic",
        "execution_note": "Local runner does not call LLM Judge/Rewriter; use n8n or a model service for strict full-mode execution.",
        "job_id": data.get("job_id") or f"local_{int(time.time())}",
        "title": data["title"],
        "platform": data["platform"],
        "language": data["language"],
        "status": "ready_for_human_review" if all(r["status"] == "ready_for_human_review" for r in results) else "needs_human_review",
        "ai_slop_score": max(r["ai_slop_score"] for r in results),
        "pass_score": data["pass_score"],
        "round": max(r["round"] for r in results),
        "main_problem": first["judge_result"]["main_problem"],
        "issues": first["judge_result"]["issues"],
        "rewrite_brief": first["judge_result"]["rewrite_brief"],
        "final_text": first["final_text"],
        "rule_scan": first["rule_scan"],
        "judge_result": first["judge_result"],
        "viral_judge_result": first["viral_judge_result"],
        "editorial_review": first["editorial_review"],
        "content_context": first["content_context"],
        "candidate_comparison": first["candidate_comparison"],
        "versions": first["versions"],
        "structure_json": first["structure_json"],
        "platform_output": {**first["platform_output"], "files": files},
        "outputs": results,
        "style_template_path": style_path,
        "style_guidance": _style_content,
        "human_review_checklist": [
            "确认事实、数据和案例是否真实",
            "确认观点是否代表作者本人立场",
            "确认选题张力是否清楚，不只是顺滑表达",
            "确认读者镜像是否具体到场景、动作或限制",
            "删除仍然可替换到任何文章里的废话",
            "检查结尾是否过度升华",
            "检查是否需要加入个人经验或真实案例",
            "确认平台标题、标签、配图需求和封面提示词是否适合发布场景",
        ],
    }
    output["platform_output"]["files"] = files

    if args.json_out:
        write_json(Path(args.json_out), output)

    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"ok": False, "status": "failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise
