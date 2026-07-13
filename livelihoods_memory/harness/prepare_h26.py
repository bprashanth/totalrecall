#!/usr/bin/env python3
"""Admit the parser-blind H26 pool after a qwen-free semantic and evidence audit.

The raw question surfaces remain independent of the parser.  This script records the evaluator's
pre-contact gold repairs, directly executes every admitted tree, and refuses to write the immutable
bank if any declared outcome is not supported by the current connector evidence.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from executor import execute
from ir_schema import validate


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "questions/holdout-h26-generated.json"
OUT = ROOT / "questions/holdout-026.json"

# Source-constrained h26-060 cannot encode its explicit provider in frozen v2.1.  In h26-087,
# "there" resolves to Guadalajara, so a target hole would be false ambiguity.  Both are rejected
# rather than weakened.  Further exclusions, if evidence execution requires them, are explicit here.
EXCLUDED = {
    "h26-006": "direct evidence returned no metro-station records for the resolved Nairobi scope",
    "h26-012": "Warsaw bus-stop retrieval exceeded the completeness cap",
    "h26-016": "the shelter annotation was absent from every retrieved Bangkok station record",
    "h26-018": "direct evidence returned no metro-station records for the resolved Accra scope",
    "h26-019": "direct evidence returned no metro-station records for the resolved Johannesburg scope",
    "h26-021": "Istanbul bank retrieval exceeded the completeness cap",
    "h26-022": "Manila bus-stop retrieval exceeded the completeness cap",
    "h26-023": "Mexico City cafe retrieval exceeded the completeness cap",
    "h26-060": "explicit World Bank constraint is not representable by SELECT",
    "h26-087": "deictic target is resolved by the immediately preceding Guadalajara antecedent",
}
SELECTED = [f"h26-{number:03d}" for number in range(1, 97)
            if f"h26-{number:03d}" not in EXCLUDED]

PLACE_ALIASES = {
    "Warsaw capital region, Poland": "Warsaw capital region",
}


def repair_tree(value):
    """Apply only frozen-semantics gold normalization; return the possibly replaced node."""
    if isinstance(value, list):
        return [repair_tree(item) for item in value]
    if not isinstance(value, dict):
        return value

    value = {key: repair_tree(item) for key, item in value.items()}
    if value.get("op") == "REGION" and value.get("place") in PLACE_ALIASES:
        value["place"] = PLACE_ALIASES[value["place"]]

    # A one-year statistical SELECT already returns a Series.  Mean-by-space is not the frozen
    # identity and fails the type contract; the canonical level tree is the SELECT itself.
    if value.get("op") == "AGGREGATE" and value.get("by") == "space" \
            and value.get("metric") == "mean":
        source = value.get("source")
        if isinstance(source, dict) and source.get("op") == "SELECT" \
                and source.get("time") is not None:
            return source
    return value


def shape(tree):
    report = validate(tree)
    if not report["valid"]:
        raise ValueError(report["errors"])
    return [op for op in report["ops"] if op != "REGION"]


def outcome_matches(want, status):
    return status in ("answer", "data_request") if want == "answer_or_data_request" \
        else status == want


def main():
    raw = json.loads(RAW.read_text())
    by_id = {row["id"]: row for row in raw["questions"]}
    if len(by_id) != 96 or len(by_id) != len(raw["questions"]):
        raise SystemExit("raw H26 must contain 96 unique IDs")

    rows = [copy.deepcopy(by_id[row_id]) for row_id in SELECTED]
    wording_repairs = {
        "h26-020": "Flag Lagos marketplaces that are more than 2,000 metres from every metro station.",
        "h26-049": "What is the ratio of Catalonia's 2024 employed-person level to its 2022 level?",
        "h26-070": "Rank Madrid region, Catalonia, and Andalusia from lowest to highest unemployment rate in 2023.",
        "h26-075": ("Using signed 2022-minus-1992 Gini changes, rank Brazil, India, and Kenya "
                     "from the lowest signed change to the highest."),
    }
    failures = []
    outcome_counts = {}
    for row in rows:
        if row["id"] in wording_repairs:
            row["q"] = wording_repairs[row["id"]]
            row["notes"] += " Wording clarified during the qwen-free admission audit."
        row["gold_ir"] = repair_tree(row["gold_ir"])
        row["gold_shape"] = shape(row["gold_ir"])
        report = validate(row["gold_ir"])
        if bool(report["holes"]) != bool(row["must_hole"]):
            failures.append({"id": row["id"], "failure": "hole declaration mismatch"})
            continue
        result = execute(row["gold_ir"])
        outcome_counts[result["status"]] = outcome_counts.get(result["status"], 0) + 1
        if not outcome_matches(row["expect"], result["status"]):
            failures.append({
                "id": row["id"], "expect": row["expect"], "status": result["status"],
                "reason": result.get("reason"), "detail": result.get("detail"),
            })

    if failures:
        print(json.dumps({"rows": len(rows), "outcomes": outcome_counts,
                          "failures": failures}, indent=2, ensure_ascii=False))
        raise SystemExit(1)

    payload = {
        "spec_version": "v2.1",
        "epoch": "epoch-018",
        "note": ("post-freeze parser-blind H26; independently audited, gold-normalized, and "
                 "directly executed before parser contact; immutable after this checksum"),
        "source_generated": "questions/holdout-h26-generated.json",
        "generator": raw["generator"],
        "generated_after": raw["generated_after"],
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "precontact_repairs": [
            "removed invalid mean-by-space wrappers from one-year statistical SELECT levels",
            "normalized the Warsaw capital region connector alias without changing question scope",
            "clarified h26-020 strict beyond, h26-049 later/earlier ratio, h26-070 regional scope, and h26-075 signed-change order",
            "recomputed every gold_shape mechanically with REGION nodes excluded",
        ],
        "excluded": EXCLUDED,
        "selection": SELECTED,
        "direct_execution": "all admitted golds matched their declared permitted outcome class",
        "questions": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "path": str(OUT.relative_to(ROOT)), "n": len(rows),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "outcomes": outcome_counts,
    }, indent=2))


if __name__ == "__main__":
    main()
