#!/usr/bin/env python3
"""Run identical multi-turn prompts through real Hermes sessions and save auditable traces."""
import argparse
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import time


HERE = pathlib.Path(__file__).resolve().parent
CHAT = HERE.parent / "chat.sh"
DEFAULT_CASES = HERE / "multiturn_cases.json"
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SESSION = re.compile(r"(?:Session:\s+|--resume\s+)([0-9]{8}_[0-9]{6}_[a-z0-9]+)")


def clean(text):
    return ANSI.sub("", text).replace("\r", "")


def run_case(case, runtime, model, max_turns):
    session = None
    turns = []
    source = f"mt-{case['id']}-{runtime}-{model}-{int(time.time())}"
    for index, prompt in enumerate(case["turns"], 1):
        command = [str(CHAT), "--runtime", runtime, "--context", case["context"],
                   "--model", model, prompt]
        env = dict(os.environ, HERMES_SOURCE=source, AUTO_APPROVE="1",
                   HERMES_MAXTURNS=str(max_turns))
        if session:
            env["HERMES_RESUME"] = session
        started = time.time()
        result = subprocess.run(command, text=True, capture_output=True, env=env)
        combined = clean(result.stdout + result.stderr)
        found = SESSION.findall(combined)
        if found:
            session = found[-1]
        turns.append({
            "turn": index,
            "prompt": prompt,
            "exit_code": result.returncode,
            "latency_s": round(time.time() - started, 3),
            "output": combined.strip(),
        })
        if result.returncode != 0 or not session:
            break
    return {
        "case": case["id"], "runtime": runtime, "model": model,
        "context": case["context"], "session": session, "source": source,
        "checks": case["checks"], "turns": turns,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", default=str(DEFAULT_CASES))
    parser.add_argument("--case", default="site_snake_inventory")
    parser.add_argument("--arm", action="append", required=True,
                        help="runtime:model, for example typed:qwen2b")
    parser.add_argument("--out")
    parser.add_argument("--max-turns", type=int, default=12,
                        help="maximum Hermes agent turns per user turn")
    args = parser.parse_args()
    bank = json.load(open(args.cases, encoding="utf-8"))
    case = next((x for x in bank["cases"] if x["id"] == args.case), None)
    if not case:
        raise SystemExit(f"unknown case: {args.case}")
    arms = []
    for arm in args.arm:
        runtime, sep, model = arm.partition(":")
        if not sep:
            raise SystemExit(f"bad --arm {arm!r}; expected runtime:model")
        arms.append(run_case(case, runtime, model, args.max_turns))
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    output = pathlib.Path(args.out or HERE / "runs" / f"{stamp}-{args.case}.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"schema": 1, "created_at": dt.datetime.now().isoformat(),
                                  "case": case, "arms": arms}, indent=2), encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
