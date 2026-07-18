#!/usr/bin/env python3
"""Normalize pre-semantic-scorer population/abundance golds to the released fail-closed policy.

Historical generated banks sometimes encoded explicit population/abundance as AGGREGATE count of
occurrence-backed organisms. That contradicts the active bank, connector contract, and executor
boundary: occurrence rows are not abundance. This one-way migration is intentionally limited to
explicit elephant population/abundance wording with no user-named record grain.
"""
import glob
import json
import re


def select_region(ir):
    if isinstance(ir, dict):
        if ir.get("op") == "REGION":
            return ir
        for value in ir.values():
            found = select_region(value)
            if found:
                return found
    elif isinstance(ir, list):
        for value in ir:
            found = select_region(value)
            if found:
                return found
    return None


changed_total = 0
for path in sorted(glob.glob("questions/final-*.json")):
    bank = json.load(open(path))
    changed = 0
    for row in bank.get("questions", []):
        q = row.get("q", "")
        ql = q.lower()
        explicit = (re.search(r"\belephants?\s+(?:population|abundance)\b", ql) or
                    re.search(r"\b(?:population(?:\s+size)?|abundance)\s+of\s+elephants?\b", ql))
        named_records = re.search(r"\b(?:records?|observations?|occurrences?|sightings?)\b", ql)
        if not explicit or named_records:
            continue
        measure = "abundance" if "abundance" in ql else "population"
        region = select_region(row.get("gold_ir")) or "?place"
        wanted = {"op": "SELECT", "entity": f"elephant {measure}",
                  "region": region, "time": None}
        if row.get("gold_ir") != wanted or row.get("gold_shape") != ["SELECT"]:
            row["gold_ir"] = wanted
            row["gold_shape"] = ["SELECT"]
            row["expect"] = "data_request"
            changed += 1
    if changed:
        bank["gold_policy_normalization"] = (
            "Explicit population/abundance migrated to fail-closed SELECT under IR v2.2.1; "
            "occurrence rows are never organism abundance.")
        with open(path, "w") as handle:
            json.dump(bank, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        print(path, changed)
        changed_total += changed
print("changed", changed_total)
