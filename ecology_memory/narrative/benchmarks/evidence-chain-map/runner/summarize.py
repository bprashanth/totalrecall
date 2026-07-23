#!/usr/bin/env python3
"""Summarise a completed evidence-chain benchmark run from its recorded turns."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


BENCHMARK_ROOT = Path(__file__).resolve().parents[1]


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def latency_summary(values: list[float]) -> dict[str, float | int | None]:
    return {
        "count": len(values),
        "mean": round(statistics.fmean(values), 3) if values else None,
        "median": round(statistics.median(values), 3) if values else None,
        "p95": round(percentile(values, 0.95), 3) if values else None,
        "max": round(max(values), 3) if values else None,
    }


def replay_summary(rows: list[dict]) -> dict[str, float | int | None]:
    pairs: dict[tuple[str, int], list[float]] = defaultdict(list)
    for row in rows:
        pairs[(row["conversation"], row["turn"])].append(
            float(row["score"]["fraction"])
        )
    complete = [scores for scores in pairs.values() if len(scores) == 2]
    deltas = [abs(scores[0] - scores[1]) for scores in complete]
    exact = sum(delta < 1e-12 for delta in deltas)
    return {
        "pairs": len(complete),
        "exact_pairs": exact,
        "exact_rate": round(exact / len(complete), 6) if complete else None,
        "mean_absolute_delta": round(statistics.fmean(deltas), 6) if deltas else None,
        "max_absolute_delta": round(max(deltas), 6) if deltas else None,
    }


def summarise_arm(rows: list[dict]) -> dict:
    fractions = [float(row["score"]["fraction"]) for row in rows]
    passed = sum(int(row["score"]["passed"]) for row in rows)
    total = sum(int(row["score"]["total"]) for row in rows)
    native_latency = [float(row["native"]["latency_s"]) for row in rows]
    verifier_latency = [
        float(row["verifier"]["latency_s"])
        for row in rows
        if row.get("verifier") is not None
    ]
    total_latency = [
        float(row["native"]["latency_s"])
        + (float(row["verifier"]["latency_s"]) if row.get("verifier") else 0.0)
        for row in rows
    ]
    decisions = Counter(
        row["verifier"]["decision"]
        for row in rows
        if row.get("verifier") is not None
    )
    skills = Counter(
        skill for row in rows for skill in row["score"].get("skills", [])
    )
    conversations: dict[str, dict] = {}
    for conversation in sorted({row["conversation"] for row in rows}):
        selected = [row for row in rows if row["conversation"] == conversation]
        scores = [float(row["score"]["fraction"]) for row in selected]
        conversations[conversation] = {
            "turns": len(selected),
            "mean_score": round(statistics.fmean(scores), 6),
            "replay": replay_summary(selected),
        }
    pass_scores = {
        str(pass_number): round(statistics.fmean(
            float(row["score"]["fraction"])
            for row in rows if int(row["pass"]) == pass_number
        ), 6)
        for pass_number in sorted({int(row["pass"]) for row in rows})
    }
    pass_values = list(pass_scores.values())
    return {
        "turns": len(rows),
        "mean_turn_score": round(statistics.fmean(fractions), 6),
        "weighted_requirement_score": round(passed / total, 6) if total else None,
        "passed_requirements": passed,
        "total_requirements": total,
        "perfect_turns": sum(score == 1.0 for score in fractions),
        "zero_turns": sum(score == 0.0 for score in fractions),
        "critical_failures": sum(
            len(row["score"].get("critical_errors", [])) for row in rows
        ),
        "mean_score_by_pass": pass_scores,
        "absolute_pass_mean_change": (
            round(abs(pass_values[-1] - pass_values[-2]), 6)
            if len(pass_values) >= 2 else None
        ),
        "latency_s": {
            "native": latency_summary(native_latency),
            "verifier": latency_summary(verifier_latency),
            "end_to_end": latency_summary(total_latency),
        },
        "verifier_decisions": dict(sorted(decisions.items())),
        "skill_mentions": dict(sorted(skills.items())),
        "replay": replay_summary(rows),
        "conversations": conversations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="run directory name under runs/")
    args = parser.parse_args()
    run_dir = BENCHMARK_ROOT / "runs" / args.run
    turns_path = run_dir / "turns.jsonl"
    rows = [json.loads(line) for line in turns_path.read_text().splitlines() if line]
    by_arm: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_arm[row["arm"]].append(row)
    passes = sorted({int(row["pass"]) for row in rows})
    conversations = sorted({row["conversation"] for row in rows})
    turns_per_pass = sum(
        1
        for row in rows
        if int(row["pass"]) == passes[0] and row["arm"] == sorted(by_arm)[0]
    ) if passes and by_arm else 0
    output = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "run": args.run,
        "method": {
            "score": "mean per-turn rubric fraction; weighted score is passed/required",
            "latency": "linear-interpolated p95; end-to-end is native plus verifier",
            "replay": "absolute score difference for identical arm/conversation/turn pairs",
        },
        "coverage": {
            "rows": len(rows),
            "passes": passes,
            "arms": sorted(by_arm),
            "conversations": conversations,
            "turns_per_arm_per_pass": turns_per_pass,
            "expected_rows": len(passes) * len(by_arm) * turns_per_pass,
        },
        "arms": {
            arm: summarise_arm(sorted(arm_rows, key=lambda row: (
                int(row["pass"]), row["conversation"], int(row["turn"])
            )))
            for arm, arm_rows in sorted(by_arm.items())
        },
    }
    (run_dir / "summary.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
