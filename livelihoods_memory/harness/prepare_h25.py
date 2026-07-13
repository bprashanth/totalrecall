#!/usr/bin/env python3
"""Curate and freeze the parser-blind H25 raw pool before qwen contact."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from executor import execute
from ir_schema import validate


ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "questions/holdout-h25-generated.json"
OUT = ROOT / "questions/holdout-025.json"

# Eight state/source controls, eight spatial/relational compositions, eight temporal/arithmetic
# rows, eight ranks, four transfer rows, and four ambiguity/behaviour/source-gap rows. Selection
# happened before qwen contact.  Raw rows with unavailable computed annotations, truncated OSM
# leaves, or unstable region resolution are deliberately absent.
SELECTED = [
    "h25-001", "h25-003", "h25-005", "h25-006",
    "h25-007", "h25-008", "h25-009", "h25-010",
    "h25-017", "h25-019", "h25-020", "h25-021",
    "h25-022", "h25-024", "h25-028", "h25-034",
    "h25-011", "h25-012", "h25-046", "h25-047",
    "h25-049", "h25-050", "h25-051", "h25-056",
    "h25-061", "h25-062", "h25-064", "h25-065",
    "h25-067", "h25-068", "h25-070", "h25-073",
    "h25-077", "h25-078", "h25-079", "h25-080",
    "h25-085", "h25-088", "h25-090", "h25-095",
]


def walk(value):
    """Normalize exact-year shorthand to an executable one-year TimeWindow."""
    if isinstance(value, dict):
        if value.get("op") == "SELECT" and isinstance(value.get("time"), str):
            year = value["time"]
            value["time"] = {"start": year, "end": year}
        for child in value.values():
            walk(child)
    elif isinstance(value, list):
        for child in value:
            walk(child)


def shape(tree):
    report = validate(tree)
    if not report["valid"]:
        raise ValueError(report["errors"])
    return [op for op in report["ops"] if op != "REGION"]


def main():
    raw = json.loads(RAW.read_text())
    by_id = {row["id"]: row for row in raw["questions"]}
    if len(by_id) != len(raw["questions"]):
        raise SystemExit("duplicate raw IDs")
    rows = [copy.deepcopy(by_id[row_id]) for row_id in SELECTED]
    if len(rows) != 40:
        raise SystemExit(f"selected {len(rows)}, expected 40")
    for row in rows:
        walk(row["gold_ir"])
        row["gold_shape"] = shape(row["gold_ir"])
        if row["id"] in {"h25-077", "h25-078", "h25-079", "h25-080"}:
            row["notes"] = ("The requested method receives a Records-typed source if available "
                            "and a REGION target; unavailable observations or a failed gate "
                            "truthfully produce a DataRequest.")
        result = execute(row["gold_ir"])
        want = row["expect"]
        ok = result["status"] in ("answer", "data_request") \
            if want == "answer_or_data_request" else result["status"] == want
        if not ok:
            raise SystemExit(f"{row['id']}: {result['status']} != {want}: "
                             f"{result.get('reason')}")
    payload = {
        "spec_version": "v2.1",
        "note": ("epoch-017 post-freeze blind H25; selected, semantically audited, and directly "
                 "executed before parser contact; no post-contact edits permitted"),
        "source_generated": "questions/holdout-h25-generated.json",
        "generator": raw["generator"],
        "generated_after": raw["generated_after"],
        "precontact_repairs": [
            "exact-year SELECT.time strings normalized to one-year {start,end} windows",
            "transfer notes made conditional on source availability and the estimate gate",
            "gold_shape recomputed mechanically with REGION nodes excluded",
        ],
        "selection": SELECTED,
        "questions": rows,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({
        "path": str(OUT.relative_to(ROOT)),
        "n": len(rows),
        "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest(),
    }, indent=2))


if __name__ == "__main__":
    main()
