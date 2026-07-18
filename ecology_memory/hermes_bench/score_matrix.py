#!/usr/bin/env python3
"""Blind-score every turn of a matrix against its own audited execution result."""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from engine import response_pack, strip_reasoning  # noqa: E402
from llm import chat  # noqa: E402


RUBRIC = (HERE / "judge" / "RUBRIC.md").read_text()


def extract_object(text: str) -> dict:
    text = strip_reasoning(text)
    start = text.find("{")
    if start < 0:
        raise ValueError("judge returned no JSON object")
    depth = 0
    quoted = False
    escaped = False
    for index, char in enumerate(text[start:], start=start):
        if escaped:
            escaped = False
            continue
        if char == "\\" and quoted:
            escaped = True
            continue
        if char == '"':
            quoted = not quoted
        elif not quoted and char == "{":
            depth += 1
        elif not quoted and char == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:index + 1])
    raise ValueError("judge returned incomplete JSON")


def judge_turn(turn: dict, arm_ids: dict[str, str]) -> dict:
    candidates = {}
    for arm, opaque in arm_ids.items():
        rendered = turn["arms"][arm]
        compiler = rendered["_compiler"]
        candidates[opaque] = {
            "audited_result": response_pack(turn["compiled"][compiler]),
            "prior_audited_results": rendered.get("_prior_audited", []),
            "answer": rendered["answer"],
            "mechanical_audit": rendered.get("audit"),
        }
    prompt = (
        "You are a strict conservation-data benchmark judge. Score each blinded candidate only "
        "against its own audited result and the current question. Do not reward facts that are "
        "plausible but absent from that result. Apply critical errors exactly as written. Return "
        "ONLY JSON with shape {\"candidates\": {\"A\": {\"grounding\":0, ... six rubric "
        "keys grounding, honesty, place_usefulness, prose, coherence, actionability, then "
        "\"critical_errors\":[], \"reason\":\"brief\"}}}. Scores are integers 0,1,2.\n\n"
        + RUBRIC + "\n\nQUESTION:\n" + turn["question"] + "\n\nCANDIDATES:\n" +
        json.dumps(candidates, ensure_ascii=False, default=str)
    )
    raw = chat("deepseekv4", [{"role": "user", "content": prompt}], temperature=0.0,
               max_tokens=5000, use_cache=True)
    result = extract_object(raw)
    result["raw_judge"] = raw
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("matrix")
    args = parser.parse_args()
    matrix_path = Path(args.matrix).resolve()
    matrix = json.loads(matrix_path.read_text())
    arms = matrix["arms"]
    # Preserve a secret-to-the-judge mapping; alphabetical opaque IDs are not quality labels.
    opaque = {arm: chr(ord("A") + index) for index, arm in enumerate(arms)}
    scores_path = matrix_path.with_name("scores.json")
    scores = json.loads(scores_path.read_text()) if scores_path.exists() else {
        "matrix": str(matrix_path), "opaque_map": opaque, "turns": []
    }
    arm_defs = matrix.get("arm_defs", {})
    while len(scores["turns"]) < len(matrix["turns"]):
        turn_index = len(scores["turns"])
        turn = json.loads(json.dumps(matrix["turns"][turn_index]))
        for arm in arms:
            compiler = arm_defs.get(arm, {}).get("compiler")
            if compiler is None:
                # Backward-compatible inference for the original fixed arm names.
                compiler = ("qwen2b" if arm.startswith("C2-") else
                            "lora9b" if arm.startswith("C9-") else "deepseekv4")
            turn["arms"][arm]["_compiler"] = compiler
            turn["arms"][arm]["_prior_audited"] = [
                response_pack(prior["compiled"][compiler])
                for prior in matrix["turns"][max(0, turn_index - 4):turn_index]
                if compiler in prior.get("compiled", {})
            ]
        judged = judge_turn(turn, opaque)
        scores["turns"].append({"number": turn["number"], "question": turn["question"],
                                "judgment": judged})
        scores_path.write_text(json.dumps(scores, indent=2, ensure_ascii=False) + "\n")
        print(f"judged turn {turn['number']}/{len(matrix['turns'])}", flush=True)

    dimensions = ["grounding", "honesty", "place_usefulness", "prose", "coherence",
                  "actionability"]
    totals = {arm: defaultdict(float) for arm in arms}
    counts = defaultdict(int)
    critical = defaultdict(int)
    for turn in scores["turns"]:
        rows = turn["judgment"].get("candidates", {})
        for arm, code in opaque.items():
            row = rows.get(code, {})
            for dim in dimensions:
                totals[arm][dim] += float(row.get(dim, 0))
            counts[arm] += 1
            critical[arm] += len(row.get("critical_errors") or [])
    scores["summary"] = {
        arm: {**{dim: round(totals[arm][dim] / max(counts[arm], 1), 3)
                  for dim in dimensions},
              "mean": round(sum(totals[arm][dim] for dim in dimensions) /
                            max(counts[arm] * len(dimensions), 1), 3),
              "critical_errors": critical[arm]}
        for arm in arms
    }
    scores_path.write_text(json.dumps(scores, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(scores["summary"], indent=2))


if __name__ == "__main__":
    main()
