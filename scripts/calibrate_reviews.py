"""Compare paired human/model dimension labels without changing thresholds."""
import argparse
import json
from pathlib import Path

DIMENSIONS = ("facts", "style", "expression", "distribution")
LABELS = ("pass", "needs_review", "unknown")


def calibration_report(records):
    report = {d: {"count": 0, "agreement_count": 0, "false_passes": 0, "false_rejections": 0, "unknown_disagreements": 0, "agreement_rate": None} for d in DIMENSIONS}
    ids = set()
    for record in records:
        for key in ("id", "model_version", "prompt_version", "human_reviewer", "split"):
            if not isinstance(record.get(key), str) or not record[key].strip():
                raise ValueError(f"Missing {key}")
        if record["id"] in ids or record["split"] not in {"calibration", "holdout"}:
            raise ValueError("Duplicate id or invalid split")
        ids.add(record["id"])
        for key in ("human", "model"):
            if set(record.get(key, {})) != set(DIMENSIONS) or any(record[key][d] not in LABELS for d in DIMENSIONS):
                raise ValueError("Each label set requires four valid dimensions")
        if record["split"] != "holdout":
            continue
        for dimension in DIMENSIONS:
            human, model = record["human"][dimension], record["model"][dimension]
            row = report[dimension]
            row["count"] += 1
            row["agreement_count"] += human == model
            row["false_passes"] += human == "needs_review" and model == "pass"
            row["false_rejections"] += human == "pass" and model == "needs_review"
            row["unknown_disagreements"] += human != model and "unknown" in (human, model)
    for row in report.values():
        if row["count"]:
            row["agreement_rate"] = row["agreement_count"] / row["count"]
    versions = sorted({(r["model_version"], r["prompt_version"]) for r in records})
    groups = []
    if len(versions) > 1:
        for model, prompt in versions:
            subset = [r for r in records if (r["model_version"], r["prompt_version"]) == (model, prompt)]
            groups.append({"model_version": model, "prompt_version": prompt, "heldout_dimensions": calibration_report(subset)["heldout_dimensions"]})
    return {"heldout_dimensions": report, "record_count": len(ids), "versions": versions, "version_groups": groups, "note": "Held-out label comparison only. Compare version groups when versions differ. No automatic threshold changes or causal publication claims."}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="JSONL human/model paired labels")
    args = parser.parse_args()
    records = [json.loads(line) for line in Path(args.input).read_text(encoding="utf-8").splitlines() if line.strip()]
    print(json.dumps(calibration_report(records), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
