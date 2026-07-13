#!/usr/bin/env python3
"""Produce the disclosed H27 development bank without mutating its immutable first contact."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ir_schema import validate


ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT / "questions/holdout-027.json"
OUT=ROOT / "questions/round2-h27-dev.json"

DISCLOSED_QUESTION_REPAIRS={
    "h27-010": "In Córdoba, Argentina, show coworking offices co-located with cafés.",
    "h27-017": "Use 0.5 km for both: which Cebu City, Philippines food vendors are near a bank and a bus stop?",
    "h27-024": "Bremen minus Hanover: difference in counts of banks within 900 m of a train station.",
    "h27-059": "Order Durban, Gqeberha and Johannesburg by count of markets beyond 1.2 km from a train station; low to high.",
}


def main():
    source=json.loads(SOURCE.read_text())
    rows=copy.deepcopy(source["questions"])
    seen=set()
    for row in rows:
        replacement=DISCLOSED_QUESTION_REPAIRS.get(row["id"])
        if replacement:
            original=row["q"]
            row["q"]=replacement
            row["notes"] += " Post-contact dev repair discloses the gold's formerly implicit place or station subtype."
            row["dev_repair"]={"original_question":original,"reason":"declared gold ambiguity"}
            seen.add(row["id"])
        report=validate(row["gold_ir"])
        if not report["valid"]:
            raise SystemExit(f"invalid gold {row['id']}: {report['errors']}")
    if seen != set(DISCLOSED_QUESTION_REPAIRS):
        raise SystemExit(f"repair IDs missing from source: {set(DISCLOSED_QUESTION_REPAIRS)-seen}")
    payload={
        "spec_version":"v2.1",
        "epoch":"epoch-020-dev",
        "note":"H27 development bank; four post-contact ambiguities disclosed in question text; immutable H27 retained",
        "source":"questions/holdout-027.json",
        "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "disclosed_repairs":sorted(DISCLOSED_QUESTION_REPAIRS),
        "questions":rows,
    }
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"path":str(OUT.relative_to(ROOT)),"n":len(rows),
                      "sha256":hashlib.sha256(OUT.read_bytes()).hexdigest()},indent=2))


if __name__ == "__main__":
    main()
