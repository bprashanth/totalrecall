#!/usr/bin/env python3
"""Verify the frozen repaired-showcase manifest without rerunning model calls."""

from __future__ import annotations

import hashlib
import json
import statistics
from pathlib import Path


RUNS = Path(__file__).resolve().parent / "runs"
EPOCH = RUNS / "20260717-showcase-epoch.json"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    epoch = json.loads(EPOCH.read_text())
    scores = {"candidate": 0, "baseline": 0}
    latencies = {"candidate": [], "baseline": []}
    critical = {"candidate": 0, "baseline": 0}

    for case in epoch["cases"]:
        for arm in ("candidate", "baseline"):
            declared = case[arm]
            path = RUNS / declared["file"]
            assert digest(path) == declared["sha256"], path
            trace = json.loads(path.read_text())
            turns = trace["arms"][0]["turns"]
            assert all(turn["exit_code"] == 0 for turn in turns), path
            actual_latency = sum(turn["latency_s"] for turn in turns)
            assert abs(actual_latency - declared["latency_s"]) < 1e-6, path
            scores[arm] += declared["score"]
            latencies[arm].append(actual_latency)
            critical[arm] += len(declared["critical_errors"])

    for arm in ("candidate", "baseline"):
        declared = epoch["arms"][arm]
        assert scores[arm] == declared["score"]
        assert critical[arm] == declared["critical_error_count"]
        assert abs(sum(latencies[arm]) - declared["total_latency_s"]) < 1e-6
        assert abs(statistics.median(latencies[arm]) - declared["median_case_latency_s"]) < 1e-6

    relative = (scores["candidate"] - scores["baseline"]) / scores["baseline"]
    stop = epoch["stop_condition"]
    assert relative >= stop["quality_relative_improvement_minimum"]
    assert critical["candidate"] <= stop["candidate_critical_errors_maximum"]
    assert statistics.median(latencies["candidate"]) < statistics.median(latencies["baseline"])
    print(
        "showcase epoch valid: "
        f"quality={scores['candidate']}/{scores['baseline']} "
        f"relative={relative:.3%} critical={critical['candidate']}/{critical['baseline']} "
        f"median_s={statistics.median(latencies['candidate']):.3f}/"
        f"{statistics.median(latencies['baseline']):.3f}"
    )


if __name__ == "__main__":
    main()
