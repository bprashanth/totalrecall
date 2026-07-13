#!/usr/bin/env python3
"""Admit parser-blind H28 after qwen-free semantic and direct-evidence checks.

The generated bank is preserved byte-for-byte.  Any precontact normalization is applied to a
deep copy here, recorded in the admitted artifact, and exercised through the frozen executor
before the parser under test is allowed to see a question.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from executor import execute
from ir_schema import validate


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "questions/holdout-h28-generated.json"
OUT = ROOT / "questions/holdout-028.json"


def repair_tree(value):
    if isinstance(value, list):
        return [repair_tree(item) for item in value]
    if not isinstance(value, dict):
        return value
    value = {key: repair_tree(item) for key, item in value.items()}
    # The census and connector registry use this reviewed NUTS label without a country suffix.
    # Question wording retains "Poland"; this is a resolver label normalization, not a scope edit.
    if value.get("op") == "REGION" and value.get("place") == \
            "Warsaw capital region, Poland":
        value["place"] = "Warsaw capital region"
    return value


def shape(tree):
    report = validate(tree)
    if not report["valid"]:
        raise ValueError(report["errors"])
    return [op for op in report["ops"] if op != "REGION"]


def outcome_matches(want, status):
    if want == "answer_or_data_request":
        return status in ("answer", "data_request")
    return status == want


def main():
    raw_bytes = RAW.read_bytes()
    raw = json.loads(raw_bytes)
    rows = copy.deepcopy(raw["questions"])
    ids = [f"h28-{number:03d}" for number in range(1, 101)]
    if len(rows) != 100 or [row.get("id") for row in rows] != ids:
        raise SystemExit("raw H28 must contain the exact 100-ID sequence")
    if len({row.get("q") for row in rows}) != 100:
        raise SystemExit("raw H28 questions must be unique")

    failures = []
    outcomes = {}
    for row in rows:
        # Qwen-free semantic repairs from the independent gold audit.  They align the question
        # surface with the already-frozen v2.1 denotation; they do not add parser mechanisms.
        if row["id"] == "h28-011":
            row["q"] = "For coworking spaces in Nairobi, Kenya, attach bank distance."
            row["notes"] += " Removed unsupported nearest/minimum semantics."
        temporal_ratio_repairs = {
            "h28-035": ("For 2023, what is Catalonia, Spain employed persons divided by its own "
                         "2022 employed persons?"),
            "h28-036": ("Numerator: Kenya gini coefficient in 2022. Denominator: Kenya gini "
                         "coefficient in 1992. Ratio?"),
            "h28-046": ("Madrid region, Spain unemployment rate in 2024 divided by Spain labour "
                         "underutilization rate in 2022."),
        }
        if row["id"] in temporal_ratio_repairs:
            row["q"] = temporal_ratio_repairs[row["id"]]
            row["gold_ir"]["left"], row["gold_ir"]["right"] = \
                row["gold_ir"]["right"], row["gold_ir"]["left"]
            row["notes"] += " Aligned the written ratio with v2.1 later-over-earlier execution."
        if row["id"] == "h28-076":
            row["q"] = ("Envelope Dakar, Senegal bank records into a field for another, "
                        "unspecified place.")
            row["notes"] += " Replaced a resolvable deictic with a genuinely unspecified target."

        row["gold_ir"] = repair_tree(row["gold_ir"])
        row["gold_shape"] = shape(row["gold_ir"])
        report = validate(row["gold_ir"])
        if bool(report["holes"]) != bool(row["must_hole"]):
            failures.append({"id": row["id"], "failure": "hole declaration mismatch"})
            continue
        if (row["gold_ir"].get("op") == "ESTIMATE") != bool(row["must_estimate"]):
            failures.append({"id": row["id"], "failure": "estimate declaration mismatch"})
            continue
        result = execute(row["gold_ir"])
        outcomes[result["status"]] = outcomes.get(result["status"], 0) + 1
        if not outcome_matches(row["expect"], result["status"]):
            failures.append({
                "id": row["id"], "expect": row["expect"],
                "status": result["status"], "reason": result.get("reason"),
                "detail": result.get("detail"),
            })
    if failures:
        print(json.dumps({"outcomes": outcomes, "failures": failures}, indent=2,
                         ensure_ascii=False))
        raise SystemExit(1)

    payload = {
        "spec_version": "v2.1",
        "epoch": "epoch-020",
        "note": ("post-freeze parser-blind H28 practical-saturation exam; independently "
                 "audited, representation-normalized, and directly executed before parser "
                 "contact; immutable after this checksum"),
        "source_generated": "questions/holdout-h28-generated.json",
        "generator": raw["generator"],
        "generated_after": raw["generated_after"],
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "precontact_repairs": [
            "normalized the reviewed Warsaw capital region connector label without changing question scope",
            "removed unsupported nearest/minimum semantics from h28-011",
            "aligned h28-035, h28-036, and h28-046 wording and operand order with v2.1 later-over-earlier temporal ratios",
            "made h28-076's intended unknown transfer target genuinely unspecified",
            "recomputed every gold_shape mechanically with REGION nodes excluded",
        ],
        "excluded": {},
        "direct_execution": "all 100 admitted golds matched their declared permitted outcome class",
        "questions": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "path": str(OUT.relative_to(ROOT)), "n": len(rows),
        "raw_sha256": payload["raw_sha256"],
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "outcomes": outcomes,
    }, indent=2))


if __name__ == "__main__":
    main()
