#!/usr/bin/env python3
"""Summarise deterministic dialogue scores and latency milestones."""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics


BENCH = pathlib.Path(__file__).resolve().parent.parent


def median(values):
    return round(statistics.median(values), 3) if values else None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args()
    root = BENCH / "runs" / args.run
    scores = json.loads((root / "scores.json").read_text(encoding="utf-8"))
    fractions = [float(row.get("fraction") or 0) for row in scores]
    critical = [
        {"conversation": row["conversation"], "turn": row["turn"], "errors": errors}
        for row in scores if (errors := row.get("critical_errors"))
    ]
    milestones = {}
    for row in scores:
        for name, value in (row.get("milestones") or {}).items():
            if isinstance(value, (int, float)):
                milestones.setdefault(name, []).append(value)
    summary = {
        "turns": len(scores),
        "mean_score": round(statistics.mean(fractions), 3) if fractions else 0,
        "critical_failure_count": len(critical),
        "critical_failures": critical,
        "median_latency_s": {name: median(values) for name, values in milestones.items()},
    }
    (root / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
