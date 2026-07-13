#!/usr/bin/env python3
"""Admit parser-blind H29 after qwen-free semantic and direct-evidence checks.

The raw author artifact stays byte-for-byte intact. Reviewed precontact exclusions and repairs are
applied only to this reproducible admitted copy before the parser under test sees any H29 surface.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from executor import execute
from ir_schema import validate


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "questions/round2-h29-raw.json"
OUT = ROOT / "questions/holdout-029.json"
EXCLUDED = {
    "h29-021": "inclusive distance boundary is not represented by frozen RELATE",
    "h29-033": "requested global temporal scalar mean is not represented by identity mean-by-time",
    "h29-034": "requested global temporal scalar mean is not represented by identity mean-by-time",
    "h29-035": "requested global temporal scalar mean is not represented by identity mean-by-time",
    "h29-040": "requested global annotated scalar mean is not represented by mean-by-space Field",
    "h29-060": "requested difference of global temporal means lacks a frozen scalar reduction",
}


def repair_tree(value):
    if isinstance(value, list):
        return [repair_tree(item) for item in value]
    if not isinstance(value, dict):
        return value
    value = {key: repair_tree(item) for key, item in value.items()}
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
    all_rows = copy.deepcopy(raw["questions"])
    ids = [f"h29-{number:03d}" for number in range(1, 101)]
    if len(all_rows) != 100 or [row.get("id") for row in all_rows] != ids:
        raise SystemExit("raw H29 must contain the exact 100-ID sequence")
    if len({row.get("q") for row in all_rows}) != 100:
        raise SystemExit("raw H29 questions must be unique")

    rows = [row for row in all_rows if row["id"] not in EXCLUDED]
    for row in rows:
        # Independent-audit repairs align an otherwise useful pressure row with a complete frozen
        # denotation. They add no parser mechanism and occur before any parser contact.
        if row["id"] == "h29-030":
            row["q"] = ("Return the presence of repair workshops in Addis Ababa, Ethiopia that "
                        "are within 0.6 km of a market, beyond 1 km from a bank, and co-occur "
                        "with spare-parts shops.")
            node = row["gold_ir"]["source"]["left"]["left"]["left"]
            node["entity"] = "repair workshop"
            row["notes"] += " Precontact audit made the workshop subtype explicit."
        if row["id"] == "h29-089":
            row["q"] = ("Rank Accra, Ghana, Nairobi, Kenya, and Kampala, Uganda from highest to "
                        "lowest by livelihood opportunities.")
            row["notes"] += " Precontact audit made the descending rank direction explicit."
        if row["id"] == "h29-100":
            row["q"] = ("Interpolate metro-station coverage for Mysuru, India from Bengaluru, "
                        "India records, compare it with Bengaluru's observed metro-station "
                        "density, and label which side is modelled.")
            row["notes"] += " Precontact audit made the observed comparison metric explicit."

        row["gold_ir"] = repair_tree(row["gold_ir"])
        row["gold_shape"] = shape(row["gold_ir"])

    failures = []
    outcomes = {}
    for row in rows:
        report = validate(row["gold_ir"])
        if bool(report["holes"]) != bool(row["must_hole"]):
            failures.append({"id": row["id"], "failure": "hole declaration mismatch"})
            continue
        if ("ESTIMATE" in report["ops"]) != bool(row["must_estimate"]):
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
        "epoch": "epoch-021",
        "note": ("post-freeze parser-blind H29 practical-saturation exam; independently audited, "
                 "representation-normalized, and directly executed before parser contact; "
                 "immutable after this checksum"),
        "source_generated": "questions/round2-h29-raw.json",
        "generator": raw["generator"],
        "generated_after": raw["generated_after"],
        "raw_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "precontact_repairs": [
            "excluded six independently disputed output/threshold rows rather than relying on debatable gold",
            "made h29-030's repair-workshop subtype explicit",
            "made h29-089's descending rank order explicit",
            "made h29-100's observed density metric explicit",
            "normalized the reviewed Warsaw capital region connector label without changing question scope",
            "recomputed every gold_shape mechanically as a preorder array with REGION excluded",
        ],
        "excluded": EXCLUDED,
        "direct_execution": "all 94 admitted golds matched their declared permitted outcome class",
        "questions": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "path": str(OUT.relative_to(ROOT)), "n": len(rows),
        "adversarial": sum(bool(row["adversarial"]) for row in rows),
        "raw_sha256": payload["raw_sha256"],
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
        "outcomes": outcomes,
    }, indent=2))


if __name__ == "__main__":
    main()
