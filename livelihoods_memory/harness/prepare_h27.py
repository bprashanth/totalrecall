#!/usr/bin/env python3
"""Admit parser-blind H27 after qwen-free representation, semantic, and evidence checks."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from executor import execute
from ir_schema import validate


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "questions/holdout-h27-generated.json"
OUT = ROOT / "questions/holdout-027.json"


def repair_tree(value):
    if isinstance(value, list):
        return [repair_tree(item) for item in value]
    if not isinstance(value, dict):
        return value
    value = {key: repair_tree(item) for key, item in value.items()}
    if value.get("op") == "REGION" and value.get("place") == "Warsaw capital region, Poland":
        value["place"] = "Warsaw capital region"
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
    rows = copy.deepcopy(raw["questions"])
    ids = [f"h27-{number:03d}" for number in range(1, 101)]
    if len(rows) != 100 or [row.get("id") for row in rows] != ids:
        raise SystemExit("raw H27 must contain the exact 100-ID sequence")
    if len({row.get("q") for row in rows}) != 100:
        raise SystemExit("raw H27 questions must be unique")

    failures = []
    outcomes = {}
    for row in rows:
        # Precontact semantic repairs. These change only benchmark representation/source metadata,
        # never the parser-under-test or the frozen algebra.
        if row["id"] == "h27-054":
            row["expect"] = "answer_or_data_request"
            row["notes"] += " Direct evidence found an empty exact leaf, so either grounded data or a typed data request is admitted."
        if row["id"] == "h27-081":
            row["gold_ir"]["entity"] = "current firm-posted job vacancies"
            row["notes"] += " Preserved every fixed modifier in the unsupported literal leaf."
        precise_proxy_holes = {
            "h27-084": "?proxy_for_trader_preference_for_markets_near_bus_stations",
            "h27-085": "?proxy_for_worker_motive_for_coworking_space_choice",
            "h27-086": "?proxy_for_new_metro_station_shop_income_rise_causality",
        }
        if row["id"] in precise_proxy_holes:
            row["gold_ir"]["entity"] = precise_proxy_holes[row["id"]]
            row["notes"] += " Proxy hole retains the fixed object and direction of the behaviour claim."
        if row["id"] == "h27-087":
            row["q"] = ("In Guayaquil, what is the ratio of coworking spaces near metro stations "
                        "to metro stations near coworking spaces, using 1 km for both relations?")
            row["notes"] += (" Removed a prose instruction that conflicted with the frozen typed "
                             "undefined-ratio answer and made the shared threshold explicit.")

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
            failures.append({"id": row["id"], "expect": row["expect"],
                             "status": result["status"], "reason": result.get("reason"),
                             "detail": result.get("detail")})
    if failures:
        print(json.dumps({"outcomes": outcomes, "failures": failures}, indent=2,
                         ensure_ascii=False))
        raise SystemExit(1)

    payload = {
        "spec_version": "v2.1",
        "epoch": "epoch-019",
        "note": ("post-freeze parser-blind H27; independently audited, representation-normalized, "
                 "and directly executed before parser contact; immutable after this checksum"),
        "source_generated": "questions/holdout-h27-generated.json",
        "generator": raw["generator"],
        "generated_after": raw["generated_after"],
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "precontact_repairs": [
            "converted generator skeleton strings to exact preorder gold_shape arrays",
            "normalized the already reviewed Warsaw capital region connector label",
            "changed h27-054 to answer_or_data_request after direct evidence found an empty exact leaf",
            "preserved the complete unsupported entity in h27-081 and the fixed proxy roles in h27-084 through h27-086",
            "removed h27-087's zero-denominator DataRequest instruction and made its shared 1 km threshold explicit"
        ],
        "excluded": {},
        "direct_execution": "all 100 admitted golds matched their declared permitted outcome class",
        "questions": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"path": str(OUT.relative_to(ROOT)), "n": len(rows),
                      "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
                      "outcomes": outcomes}, indent=2))


if __name__ == "__main__":
    main()
