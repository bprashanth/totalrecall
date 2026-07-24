#!/usr/bin/env python3
"""Re-cut the frozen ecology pilot through its estimation subset; no model calls."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
DIMENSION = {"task_completion": 0, "executed_analysis": 2, "evidence_boundary": 3}


def main() -> None:
    lens = json.loads((HERE / "estimation_lens.json").read_text())
    scoring = json.loads((HERE / "scoring.json").read_text())
    qids = [row["question_id"] for row in lens["ladder"] if row["estimate_subset"]]
    out = {}
    for arm, arm_data in scoring["arms"].items():
        rows = [arm_data["questions"][qid]["scores"] for qid in qids]
        total = sum(sum(row) for row in rows)
        executed = sum(row[DIMENSION["executed_analysis"]] for row in rows)
        boundary = sum(row[DIMENSION["evidence_boundary"]] for row in rows)
        complete = sum(
            row[DIMENSION["task_completion"]] == 2
            and row[DIMENSION["executed_analysis"]] == 2
            and row[DIMENSION["evidence_boundary"]] == 2
            for row in rows
        )
        out[arm] = {
            "role": arm_data["role"],
            "workflow_score": [total, 10 * len(qids)],
            "workflow_percent": round(100 * total / (10 * len(qids)), 1),
            "executed_analysis": [executed, 2 * len(qids)],
            "evidence_boundary": [boundary, 2 * len(qids)],
            "complete_workflows": [complete, len(qids)],
        }
    print(json.dumps({
        "lens_version": lens["version"],
        "questions": qids,
        "note": lens["status"],
        "arms": out,
    }, indent=2))


if __name__ == "__main__":
    main()
