#!/usr/bin/env python3
"""Validate the hand-scored rubric and print reproducible aggregates."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
PRIMARY = ("gemini-flash-agent", "deepseek-v4-web", "ecology-stack-best")


def main() -> None:
    bank = json.loads((HERE / "bank.json").read_text())
    scoring = json.loads((HERE / "scoring.json").read_text())
    qids = [question["id"] for question in bank["questions"]]
    summary: dict[str, dict] = {}

    for arm, arm_data in scoring["arms"].items():
        if set(arm_data["questions"]) != set(qids):
            raise SystemExit(f"{arm}: score keys do not match bank")
        per_question = {}
        critical = 0
        for qid in qids:
            row = arm_data["questions"][qid]
            scores = row["scores"]
            if len(scores) != 5 or any(not isinstance(value, int) or value not in (0, 1, 2)
                                       for value in scores):
                raise SystemExit(f"{arm}/{qid}: invalid scores {scores!r}")
            if set(row["rationale"]) != set(scoring["dimensions"]):
                raise SystemExit(f"{arm}/{qid}: rationale keys do not match dimensions")
            per_question[qid] = sum(scores)
            critical += len(row["critical_errors"])
        total = sum(per_question.values())
        summary[arm] = {
            "role": arm_data["role"],
            "per_question": per_question,
            "total": total,
            "maximum": 10 * len(qids),
            "percent": round(100 * total / (10 * len(qids)), 1),
            "critical_errors": critical,
        }

    print(json.dumps({
        "bank_version": bank["version"],
        "primary_arms": list(PRIMARY),
        "summary": summary,
    }, indent=2))


if __name__ == "__main__":
    main()
