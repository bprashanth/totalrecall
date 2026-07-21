#!/usr/bin/env python3
"""Aggregate the audited estimation scores into narrative-ready JSON."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
DIMS = ("estimand", "execution", "fit", "evidence_state", "decision_record")


def summarize(rows: list[dict]) -> dict:
    scores = {dim: sum(row["review"]["scores"][dim] for row in rows) for dim in DIMS}
    max_score = len(rows) * 2
    return {
        "n": len(rows),
        "score": sum(scores.values()),
        "max_score": max_score * len(DIMS),
        "percent": round(100 * sum(scores.values()) / (max_score * len(DIMS)), 1),
        "dimensions": {
            dim: {"score": value, "max": max_score, "percent": round(100 * value / max_score, 1)}
            for dim, value in scores.items()
        },
        "executed_estimates": sum(row["review"]["scores"]["execution"] == 2 for row in rows),
        "partial_execution": sum(row["review"]["scores"]["execution"] == 1 for row in rows),
        "fit_gates_executed": sum(row["review"]["scores"]["fit"] == 2 for row in rows),
        "boundaries_preserved": sum(row["review"]["scores"]["evidence_state"] == 2 for row in rows),
        "critical_error_answers": sum(bool(row["review"].get("critical_errors")) for row in rows),
        "no_final_answer": sum("no_final_answer" in row["review"].get("tags", []) for row in rows),
        "tags": dict(Counter(tag for row in rows for tag in row["review"].get("tags", []))),
    }


def main() -> None:
    rows = json.loads((HERE / "scoring.json").read_text())["rows"]
    by_model = defaultdict(list)
    by_family = defaultdict(list)
    matrix = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_model[row["model"]].append(row)
        by_family[row["family"]].append(row)
        matrix[row["model"]][row["family"]].append(row)
    output = {
        "overall": summarize(rows),
        "by_model": {key: summarize(value) for key, value in sorted(by_model.items())},
        "by_family": {key: summarize(value) for key, value in sorted(by_family.items())},
        "model_family": {
            model: {family: summarize(items) for family, items in sorted(families.items())}
            for model, families in sorted(matrix.items())
        },
    }
    (HERE / "summary.json").write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
