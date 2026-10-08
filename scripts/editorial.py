"""Content context and publication feedback, without model-based claims."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def content_context(data: dict) -> dict:
    samples = data.get("author_samples", [])
    facts = data.get("facts", [])
    forbidden = data.get("forbidden_claims", [])
    if not isinstance(samples, list) or any(not isinstance(s, str) or not s.strip() for s in samples):
        raise ValueError("author_samples must contain nonempty strings")
    if not isinstance(forbidden, list) or any(not isinstance(s, str) for s in forbidden):
        raise ValueError("forbidden_claims must contain strings")
    if not isinstance(facts, list):
        raise ValueError("facts must be a list")
    ids = set()
    for fact in facts:
        if not isinstance(fact, dict) or not all(isinstance(fact.get(k), str) and fact[k].strip() for k in ("id", "claim", "source")):
            raise ValueError("Each fact requires id, claim, source")
        if fact["id"] in ids:
            raise ValueError("Duplicate fact id")
        ids.add(fact["id"])
    return {"author_samples": samples, "facts": facts, "forbidden_claims": forbidden,
            "source_note": "Supplied sources are not independently verified. Samples guide voice, not facts."}


def local_review(text: str, context: dict, scan: dict, viral: dict) -> dict:
    violations = [claim for claim in context["forbidden_claims"] if claim and claim in text]
    return {
        "facts": {"verdict": "needs_review", "score": None, "evidence": violations,
                  "reason": "Exact forbidden claims found." if violations else "Requires semantic review against sources."},
        "style": {"verdict": "not_evaluated", "score": None, "reason": "Author voice requires model or human comparison."},
        "expression": {"verdict": "heuristic_only", "score": scan["ai_slop_rule_score"], "scale": "lower_is_better"},
        "distribution": {"verdict": "heuristic_only", "score": viral["viral_score"], "scale": "higher_is_better"},
    }


def publication_record(data: dict) -> dict:
    for field in ("job_id", "platform", "variant_id", "published_at", "window_end"):
        if not isinstance(data.get(field), str) or not data[field].strip():
            raise ValueError(f"Missing {field}")
    from datetime import datetime
    start = datetime.fromisoformat(data["published_at"])
    end = datetime.fromisoformat(data["window_end"])
    if start.tzinfo is None or end.tzinfo is None or end <= start:
        raise ValueError("Use timezone-aware timestamps and a positive observation window")
    metrics = data.get("metrics", {})
    allowed = {"impressions", "clicks", "reads", "completions", "saves", "shares", "comments", "conversions", "watch_seconds"}
    if not isinstance(metrics, dict) or set(metrics) - allowed:
        raise ValueError("Unknown metric")
    for name, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(f"Invalid metric {name}")
        if name != "watch_seconds" and not float(value).is_integer():
            raise ValueError(f"Count metric {name} must be an integer")
    for numerator, denominator in (("clicks", "impressions"), ("completions", "reads")):
        if numerator in metrics and denominator in metrics and metrics[numerator] > metrics[denominator]:
            raise ValueError(f"{numerator} exceeds {denominator}")
    design = data.get("experiment_design", "observational")
    if design not in {"observational", "randomized"}:
        raise ValueError("Invalid experiment_design")
    if design == "randomized" and not data.get("experiment_id"):
        raise ValueError("Randomized records require experiment_id")
    rates = {}
    for name, numerator, denominator in (("ctr", "clicks", "impressions"), ("completion_rate", "completions", "reads")):
        rates[name] = metrics[numerator] / metrics[denominator] if numerator in metrics and metrics.get(denominator, 0) > 0 else None
    return {**data, "experiment_design": design, "rates": rates,
            "interpretation": "Observation only; no automatic winner or threshold update."}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    parser.add_argument("--log", default=str(Path(__file__).resolve().parents[1] / "feedback/publication_metrics.jsonl"))
    args = parser.parse_args()
    record = publication_record(json.loads(Path(args.input).read_text(encoding="utf-8")))
    path = Path(args.log)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    print(json.dumps(record, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
