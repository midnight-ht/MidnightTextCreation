#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rule scanner for Chinese AI Slop detection.

Usage:
    python scripts/rule_scan.py examples/input_wechat.json
    python scripts/rule_scan.py --text "在当今时代，AI 正在赋能内容创作。"
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

try:
    from normalize_text import normalize_text, split_sentences, split_paragraphs
    from score_calculator import ScoreBreakdown, level_for_score, action_for_score
except ImportError:
    from scripts.normalize_text import normalize_text, split_sentences, split_paragraphs
    from scripts.score_calculator import ScoreBreakdown, level_for_score, action_for_score

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def count_hits(patterns: list[str], text: str) -> list[dict[str, Any]]:
    hits: list[dict[str, Any]] = []
    for pattern in patterns:
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            regex = re.compile(re.escape(pattern))
        matches = regex.findall(text)
        if matches:
            hits.append({"pattern": pattern, "count": len(matches)})
    return hits


def repeated_sentence_starts(sentences: list[str], prefix_len: int = 8, threshold: int = 3) -> list[dict[str, Any]]:
    starts: dict[str, int] = {}
    for sentence in sentences:
        start = sentence[:prefix_len]
        if start:
            starts[start] = starts.get(start, 0) + 1
    return [
        {"start": start, "count": count}
        for start, count in starts.items()
        if count >= threshold
    ]


def paragraph_symmetry_ratio(paragraphs: list[str]) -> float:
    if not paragraphs:
        return 0.0
    lengths = [len(p) for p in paragraphs]
    avg = sum(lengths) / max(len(lengths), 1)
    if avg <= 0:
        return 0.0
    similar = [length for length in lengths if abs(length - avg) / avg < 0.15]
    return round(len(similar) / len(paragraphs), 2)


def list_ratio(text: str, paragraph_count: int) -> float:
    lines = text.split("\n")
    list_like = [line for line in lines if re.match(r"^\s*(\d+[\.、]|[-*•]|[一二三四五六七八九十]+[、.])", line)]
    if paragraph_count <= 0:
        return 0.0
    return round(len(list_like) / paragraph_count, 2)


def vague_claim_hits(text: str, language: str) -> list[dict[str, Any]]:
    zh_patterns = [
        "越来越重要",
        "发挥.*作用",
        "带来.*价值",
        "提升.*效率",
        "提高.*质量",
        "实现.*优化",
        "值得.*关注",
        "具有.*意义",
        "产生.*影响",
        "推动.*发展",
    ]
    en_patterns = [
        r"increasingly important",
        r"play(s)? a .* role",
        r"drive .* growth",
        r"deliver .* value",
        r"improve .* efficiency",
        r"enhance .* quality",
        r"unlock .* potential",
        r"make a .* impact",
    ]
    patterns = en_patterns if language == "en" else zh_patterns
    patterns = [p.replace(".*", "[^。！？.!?\\n]{0,60}") for p in patterns]
    return count_hits(patterns, text)


def abstract_noun_density(text: str, language: str) -> float:
    terms = (
        [
            "能力",
            "价值",
            "效率",
            "质量",
            "体系",
            "系统",
            "方法",
            "路径",
            "机制",
            "模型",
            "场景",
            "生态",
            "趋势",
            "影响",
            "意义",
        ]
        if language != "en"
        else [
            "value",
            "efficiency",
            "quality",
            "system",
            "framework",
            "approach",
            "model",
            "impact",
            "potential",
            "strategy",
            "solution",
            "innovation",
        ]
    )
    sentences = split_sentences(text)
    if not sentences:
        return 0.0
    total_hits = sum(len(re.findall(re.escape(term), text, flags=re.IGNORECASE)) for term in terms)
    return round(total_hits / len(sentences), 2)


def weak_ending(text: str, language: str) -> bool:
    sentences = split_sentences(text)
    tail = sentences[-1] if sentences else ""
    if not tail:
        return False
    if language == "en":
        return bool(
            re.search(
                r"(increasingly important|unlock .* potential|drive .* value|play.*role)",
                tail,
                flags=re.IGNORECASE,
            )
        )
    return bool(re.search(r"(越来越重要|未来可期|发挥[^。！？]{0,40}作用|带来[^。！？]{0,40}价值|值得[^。！？]{0,40}关注)", tail))


def specificity_markers(text: str, language: str) -> int:
    if language == "en":
        patterns = [r"\b\d+(\.\d+)?\b", r"\bwhen\b", r"\bbefore\b", r"\bafter\b", r"\bfor example\b", r"\bbecause\b"]
    else:
        patterns = [r"\d+", "比如", "例如", "一次", "当时", "后来", "因为", "具体", "限制", "代价", "取舍"]
    return sum(len(re.findall(pattern, text, flags=re.IGNORECASE)) for pattern in patterns)


def load_scoring_rules() -> dict[str, Any]:
    rules_path = ROOT / "rules" / "scoring_rules.json"
    if not rules_path.exists():
        return {}
    return load_json(rules_path)


def scan_text(
    text: str,
    blacklist: list[str] | None = None,
    meta_phrases: list[str] | None = None,
    scoring_rules: dict[str, Any] | None = None,
    language: str = "zh",
) -> dict[str, Any]:
    text = normalize_text(text)
    if language not in {"zh", "en"}:
        raise ValueError("language must be zh or en")
    blacklist = blacklist if blacklist is not None else load_json(ROOT / "rules" / f"{language}_blacklist.json")
    meta_phrases = meta_phrases if meta_phrases is not None else load_json(ROOT / "rules" / f"{language}_meta_phrases.json")
    scoring_rules = scoring_rules if scoring_rules is not None else load_scoring_rules()

    blacklist_weight = int(scoring_rules.get("blacklist_hit_weight", 6))
    meta_weight = int(scoring_rules.get("meta_phrase_hit_weight", 8))
    repeated_weight = int(scoring_rules.get("repeated_sentence_start_weight", 5))
    symmetry_penalty = int(scoring_rules.get("paragraph_symmetry_penalty", 15))
    list_penalty = int(scoring_rules.get("list_overuse_penalty", 12))
    opening_penalty = int(scoring_rules.get("generic_opening_penalty", 12))
    ending_penalty = int(scoring_rules.get("generic_ending_penalty", 12))
    vague_claim_weight = int(scoring_rules.get("vague_claim_hit_weight", 7))
    abstract_density_penalty = int(scoring_rules.get("abstract_noun_density_penalty", 10))
    weak_ending_penalty = int(scoring_rules.get("weak_ending_penalty", 14))
    low_specificity_penalty = int(scoring_rules.get("low_specificity_penalty", 10))
    max_score = int(scoring_rules.get("max_score", 100))

    sentences = split_sentences(text)
    paragraphs = split_paragraphs(text)

    blacklist_hits = count_hits(blacklist, text)
    meta_hits = count_hits(meta_phrases, text)
    repeated_starts = repeated_sentence_starts(sentences)
    symmetry_ratio = paragraph_symmetry_ratio(paragraphs)
    lr = list_ratio(text, len(paragraphs))
    vague_hits = vague_claim_hits(text, language)
    abstract_density = abstract_noun_density(text, language)
    weak_tail = weak_ending(text, language)
    specificity_count = specificity_markers(text, language)

    generic_opening = bool(re.match(r"^(在当今|随着|近年来|如今|当前|现在)" if language == "zh" else r"^(in today's|in today’s|as technology continues)", text.strip(), re.IGNORECASE))
    generic_ending = bool(re.search(r"(总而言之|综上所述|未来.*越来越重要|未来可期|让我们.*未来)", text[-300:]))

    breakdown = ScoreBreakdown()
    breakdown.blacklist_score = sum(item["count"] * blacklist_weight for item in blacklist_hits)
    breakdown.meta_score = sum(item["count"] * meta_weight for item in meta_hits)
    breakdown.repeated_start_score = sum(item["count"] * repeated_weight for item in repeated_starts)
    breakdown.paragraph_symmetry_penalty = symmetry_penalty if symmetry_ratio > 0.7 and len(paragraphs) >= 5 else 0
    breakdown.list_overuse_penalty = list_penalty if lr > 0.5 and len(paragraphs) >= 6 else 0
    breakdown.generic_opening_penalty = opening_penalty if generic_opening else 0
    breakdown.generic_ending_penalty = ending_penalty if generic_ending else 0
    deep_slop_score = 0
    deep_slop_score += sum(item["count"] * vague_claim_weight for item in vague_hits)
    deep_slop_score += abstract_density_penalty if abstract_density >= 2.0 and len(sentences) >= 3 else 0
    deep_slop_score += weak_ending_penalty if weak_tail else 0
    deep_slop_score += low_specificity_penalty if specificity_count == 0 and len(sentences) >= 3 else 0
    breakdown.total_score = min(
        max_score,
        breakdown.blacklist_score
        + breakdown.meta_score
        + breakdown.repeated_start_score
        + breakdown.paragraph_symmetry_penalty
        + breakdown.list_overuse_penalty
        + breakdown.generic_opening_penalty
        + breakdown.generic_ending_penalty
        + deep_slop_score,
    )

    return {
        "ai_slop_rule_score": breakdown.total_score,
        "level": level_for_score(breakdown.total_score),
        "action": action_for_score(breakdown.total_score),
        "blacklist_hits": blacklist_hits,
        "meta_hits": meta_hits,
        "repeated_starts": repeated_starts,
        "paragraph_count": len(paragraphs),
        "sentence_count": len(sentences),
        "symmetry_ratio": symmetry_ratio,
        "list_ratio": lr,
        "generic_opening": generic_opening,
        "generic_ending": generic_ending,
        "vague_claim_hits": vague_hits,
        "abstract_noun_density": abstract_density,
        "weak_ending": weak_tail,
        "specificity_marker_count": specificity_count,
        "deep_slop_score": deep_slop_score,
        "score_breakdown": breakdown.to_dict(),
    }


def text_from_input_file(path: Path) -> str:
    data = load_json(path)
    return data.get("raw_material") or data.get("text") or data.get("content") or ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?", help="Path to JSON input file")
    parser.add_argument("--text", help="Raw text to scan")
    parser.add_argument("--language", choices=["zh", "en"], default="zh")
    args = parser.parse_args()

    if args.text:
        text = args.text
    elif args.input:
        text = text_from_input_file(Path(args.input))
    else:
        raise SystemExit("Provide an input JSON file or --text.")

    print(json.dumps(scan_text(text, language=args.language), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
