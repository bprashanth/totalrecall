#!/usr/bin/env python3
"""Produce the disclosed H28 development bank without mutating immutable first contact."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from ir_schema import validate


ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT / "questions/holdout-028.json"
OUT=ROOT / "questions/round2-h28-dev.json"


def main():
    source=json.loads(SOURCE.read_text())
    rows=copy.deepcopy(source["questions"])
    for row in rows:
        report=validate(row["gold_ir"])
        if not report["valid"]:
            raise SystemExit(f"invalid gold {row['id']}: {report['errors']}")
    payload={
        "spec_version":"v2.1",
        "epoch":"epoch-021-dev",
        "note":"H28 disclosed development bank; immutable H28 first contact retained",
        "source":"questions/holdout-028.json",
        "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "disclosed_repairs":[],
        "questions":rows,
    }
    OUT.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"path":str(OUT.relative_to(ROOT)),"n":len(rows),
                      "sha256":hashlib.sha256(OUT.read_bytes()).hexdigest()},indent=2))


if __name__ == "__main__":
    main()
