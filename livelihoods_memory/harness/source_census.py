#!/usr/bin/env python3
"""Live/cache-backed integrity census for Round-2 connector additions."""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

import connectors as C

ROOT = Path(__file__).resolve().parent.parent


def check_series(result):
    rows = result.get("rows", [])
    times = [r.get("t") for r in rows]
    values = [r.get("value") for r in rows]
    checks = {
        "nonempty": bool(rows),
        "unique_time": len(times) == len(set(times)),
        "ordered_time": times == sorted(times),
        "numeric": all(isinstance(v, (int, float)) for v in values),
        "bounded_query": len(rows) <= 5,
    }
    return {
        "passed": all(checks.values()), "checks": checks, "row_count": len(rows),
        "time_min": min(times) if times else None, "time_max": max(times) if times else None,
        "sample": rows[:2], "source": result.get("source"), "unit": result.get("unit"),
        "indicator": result.get("indicator") or result.get("dataset"),
        "source_code": result.get("source_code"), "geo": result.get("iso") or result.get("geo"),
        "note": result.get("note"),
    }


def main():
    tests = []
    ilo_cases = [
        ("France", "informal employment rate"),
        ("Germany", "female average weekly hours worked"),
        ("Spain", "labour underutilization rate"),
        ("Kenya", "average weekly hours worked"),
    ]
    for place, entity in ilo_cases:
        out = C.ilo_series(entity, {"orig": place, "name": place},
                           {"start": "2019", "end": "2023"})
        tests.append({"family": "ilostat", "place": place, "entity": entity,
                      **check_series(out)})

    euro_cases = [
        ("Ile de France", "employment rate"),
        ("Berlin, Germany", "female employment rate"),
        ("Madrid region, Spain", "unemployment rate"),
        ("Catalonia, Spain", "employed persons"),
        ("Lombardy, Italy", "employment rate"),
        ("Warsaw capital region, Poland", "employment rate"),
    ]
    for place, entity in euro_cases:
        out = C.eurostat_series(entity, {"orig": place, "name": place},
                                {"start": "2022", "end": "2024"})
        tests.append({"family": "eurostat", "place": place, "entity": entity,
                      **check_series(out)})

    payload = {
        "schema_version": "round2-source-census-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "all_passed": all(test["passed"] for test in tests),
        "families": sorted({test["family"] for test in tests}),
        "tests": tests,
    }
    target = ROOT / "coverage" / "source-census.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"all_passed": payload["all_passed"], "tests": len(tests),
                      "families": payload["families"]}, indent=2))
    if not payload["all_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
