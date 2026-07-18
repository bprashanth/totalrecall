#!/usr/bin/env python3
"""Run the Kavya multi-turn compiler/responder factorial.

The benchmark asks one shared question per turn.  Compilers emit the frozen IR; Python validates
and executes it; responders see only the audited execution pack.  The grinder phrases follow-ups
but never supplies domain facts.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from engine import (audited_history_entry, compile_turn, deterministic_render, render_turn, response_pack,
                    strip_reasoning)  # noqa: E402
from llm import chat  # noqa: E402


ARMS = {
    "C2-D": ("qwen2b", "deterministic"),
    "C9-D": ("lora9b", "deterministic"),
    "C2-R9": ("qwen2b", "lora9b"),
    "C9-R9": ("lora9b", "lora9b"),
    "CDS-RDS": ("deepseekv4", "deepseekv4"),
    "CDS-D": ("deepseekv4", "deterministic"),
    "C2-RDS": ("qwen2b", "deepseekv4"),
    # Infrastructure control: same Qwen scale without adapter, served remotely. This never counts
    # as the LoRA result; it keeps the compiler/responder experiment moving if the shared HF shim
    # is occupied by another job.
    "CQ9-D": ("qwen9b", "deterministic"),
    "C2-RQ9": ("qwen2b", "qwen9b"),
    "CQ9-RQ9": ("qwen9b", "qwen9b"),
    "C2Q9-D": ("qwen2b+qwen9b", "deterministic"),
    "C9Q9-D": ("lora9b+qwen9b", "deterministic"),
    "CQ9Q9-D": ("qwen9b+qwen9b", "deterministic"),
    "CQ9Q9-RQ9": ("qwen9b+qwen9b", "qwen9b"),
    "C2DS-D": ("qwen2b+deepseekv4", "deterministic"),
    "C9DS-D": ("lora9b+deepseekv4", "deterministic"),
    "CQ9DS-D": ("qwen9b+deepseekv4", "deterministic"),
    "CQ9DS-RQ9": ("qwen9b+deepseekv4", "qwen9b"),
    "CQ9GLM-D": ("qwen9b+glm", "deterministic"),
    "CQ9GLM-RQ9": ("qwen9b+glm", "qwen9b"),
    "SQ9C2-D": ("qwen9b@qwen2b", "deterministic"),
    "SQ9C2-RQ9": ("qwen9b@qwen2b", "qwen9b"),
    "SQ9C9-D": ("qwen9b@lora9b", "deterministic"),
    "SQ9CQ9-D": ("qwen9b@qwen9b", "deterministic"),
    "SQ9CQ9-RQ9": ("qwen9b@qwen9b", "qwen9b"),
    "SQ9DSC2-D": ("qwen9b>deepseekv4@qwen2b", "deterministic"),
    "SQ9DSC2-RQ9": ("qwen9b>deepseekv4@qwen2b", "qwen9b"),
    "SQ9DSC9-D": ("qwen9b>deepseekv4@lora9b", "deterministic"),
    "SQ9DSC9-RQ9": ("qwen9b>deepseekv4@lora9b", "qwen9b"),
}

TURN1 = (
    "I work with a conservation NGO around Elephants by the Lake. Map EBTL for a new field "
    "colleague: what are the strongest facts we actually have, and what are the important gaps?"
)


def load_arc() -> list[str]:
    goals = []
    for line in (HERE / "persona" / "arc.md").read_text().splitlines():
        match = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
        if match:
            goals.append(match.group(2))
    return goals


def phrase_followup(goal: str, previous: dict[str, str]) -> str:
    answers = "\n\n".join(f"[{arm}]\n{text[-1800:]}" for arm, text in previous.items())
    prompt = (
        "You are Kavya, 32, a conservation NGO programme manager in Krishnagiri. Write ONLY "
        "her next chat message, 1-2 natural sentences in direct Indian English. All systems just "
        "answered the previous question; their answers are below. Refer only to a point supported "
        "in common, then drill into the GOAL. Do not add an ecological fact, species, number, "
        "answer, route, connector name, or data source. It is fine to challenge uncertainty.\n\n"
        f"GOAL: {goal}\n\nPREVIOUS ANSWERS:\n{answers}"
    )
    raw = chat("deepseekv4", [{"role": "user", "content": prompt}], temperature=0.4,
               max_tokens=900, use_cache=True)
    phrased = strip_reasoning(raw).strip().strip('"')
    if not phrased:
        raise RuntimeError("follow-up grinder returned no visible question")
    return phrased


def compiler_history(state: dict, compiler: str) -> list[dict]:
    """Same evidence lineage for arms sharing a compiler; no responder prose enters compilation."""
    history: list[dict] = []
    for turn in state.get("turns", []):
        history.append({"role": "user", "content": turn["question"]})
        compiled = turn.get("compiled", {}).get(compiler)
        if compiled:
            summary = audited_history_entry(turn["question"], compiled)
            history.append({"role": "assistant", "content": "AUDITED EVIDENCE: " +
                            json.dumps(summary, ensure_ascii=False)})
    return history


def arm_history(state: dict, arm: str) -> list[dict]:
    history: list[dict] = []
    for turn in state.get("turns", [])[-4:]:
        history.append({"role": "user", "content": turn["question"]})
        compiler = ARMS[arm][0]
        compiled = turn.get("compiled", {}).get(compiler)
        if compiled:
            history.append({"role": "assistant", "content":
                            "PRIOR AUDITED RESULT: " + json.dumps(
                                response_pack(compiled), ensure_ascii=False, default=str)})
    return history


def write_transcripts(state: dict, outdir: Path, arms: list[str]) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    for arm in arms:
        compiler, responder = ARMS[arm]
        lines = [
            f"# EBTL Kavya drill-down — {arm}", "",
            f"compiler={compiler} responder={responder} round={state['round']}", "",
        ]
        for turn in state.get("turns", []):
            if arm not in turn.get("arms", {}):
                continue
            compiled = turn["compiled"][compiler]
            rendered = turn["arms"][arm]
            lines.extend([
                f"## Turn {turn['number']} — {turn['goal']}", "",
                "### Kavya", "", turn["question"], "", "### Algebra", "",
                "```json", json.dumps(compiled.get("ir"), indent=2, ensure_ascii=False), "```", "",
                f"schema_valid={compiled['schema']['valid']} status={compiled['execution'].get('status')} "
                f"label={compiled['execution'].get('label')} compile_execute_s="
                f"{compiled['compile_execute_latency_s']}", "", "### Answer", "",
                rendered["answer"], "",
                f"audit_passed={rendered['audit']['passed']} fallback={rendered['fallback']} "
                f"render_s={rendered['render_latency_s']}", "",
            ])
        (outdir / f"{arm}.md").write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", default="pilot")
    parser.add_argument("--turns", type=int, default=4)
    parser.add_argument("--arms", default="C2-D,C9-D,C2-R9,C9-R9")
    parser.add_argument("--include-frontier", action="store_true")
    parser.add_argument("--questions-file",
                        help="JSON matrix/list supplying frozen questions instead of the grinder")
    args = parser.parse_args()

    arms = [item.strip() for item in args.arms.split(",") if item.strip()]
    if args.include_frontier and "CDS-RDS" not in arms:
        arms.append("CDS-RDS")
    unknown = sorted(set(arms) - set(ARMS))
    if unknown:
        raise SystemExit(f"unknown arms: {unknown}")

    arc = load_arc()
    frozen_questions = None
    if args.questions_file:
        supplied = json.loads(Path(args.questions_file).read_text())
        if isinstance(supplied, dict):
            supplied = supplied.get("turns", supplied.get("questions", []))
        frozen_questions = [item["question"] if isinstance(item, dict) else str(item)
                            for item in supplied]
    limit = min(args.turns, len(arc))
    if frozen_questions is not None:
        limit = min(limit, len(frozen_questions))
    outdir = HERE / "transcripts" / args.round
    state_path = outdir / "matrix.json"
    if state_path.exists():
        state = json.loads(state_path.read_text())
        if state.get("arms") != arms:
            raise SystemExit(f"existing round has arms={state.get('arms')}; requested {arms}")
    else:
        state = {"round": args.round, "arms": arms,
                 "arm_defs": {arm: {"compiler": ARMS[arm][0], "responder": ARMS[arm][1]}
                              for arm in arms},
                 "started": time.strftime("%FT%T%z"), "turns": []}

    while len(state["turns"]) < limit:
        index = len(state["turns"])
        if frozen_questions is not None:
            question = frozen_questions[index]
        elif index == 0:
            question = TURN1
        else:
            previous = {arm: state["turns"][-1]["arms"][arm]["answer"] for arm in arms}
            question = phrase_followup(arc[index], previous)
        compilers = sorted({ARMS[arm][0] for arm in arms})
        compiled: dict[str, dict] = {}
        with ThreadPoolExecutor(max_workers=len(compilers)) as pool:
            futures = {
                pool.submit(compile_turn, question, compiler,
                            compiler_history(state, compiler)): compiler
                for compiler in compilers
            }
            for future in as_completed(futures):
                compiler = futures[future]
                compiled[compiler] = future.result()

        # The tracked :8007 SSE proxy accepts overlapping sockets but its single HF shim can stall
        # both generations indefinitely. Keep responder calls sequential; deterministic arms are
        # instantaneous, and every arm still sees the exact same frozen execution object.
        rendered: dict[str, dict] = {}
        for arm in arms:
            compiler, responder = ARMS[arm]
            rendered[arm] = render_turn(
                question, compiled[compiler], responder, arm_history(state, arm)
            )

        turn = {"number": index + 1, "goal": arc[index], "question": question,
                "compiled": compiled, "arms": rendered}
        state["turns"].append(turn)
        outdir.mkdir(parents=True, exist_ok=True)
        state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False, default=str) + "\n")
        write_transcripts(state, outdir, arms)
        statuses = ", ".join(
            f"{arm}:{compiled[ARMS[arm][0]]['execution'].get('status')}/"
            f"audit={rendered[arm]['audit']['passed']}" for arm in arms
        )
        print(f"turn {index + 1}/{limit}: {statuses}", flush=True)

    print(f"matrix -> {state_path}")


if __name__ == "__main__":
    main()
