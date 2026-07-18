"""Capture parser/executor traces for deliberately blocked expressiveness probes.

These rows are proposal evidence, never training examples and never part of the saturation score.
"""
import argparse
import json
import os

import parser as P
from executor import execute
from ir_schema import validate


def run(bank_path, out_dir, model="qwen2b"):
    os.makedirs(out_dir, exist_ok=True)
    bank = json.load(open(bank_path))
    out_path = os.path.join(out_dir, "traces.jsonl")
    with open(out_path, "w") as f:
        for row in bank["questions"]:
            parsed = P.parse(row["q"], role=model)
            ir = parsed.get("ir")
            schema = validate(ir) if ir else None
            execution = execute(ir) if ir and schema["valid"] else {"status": "error", "reason": "no_valid_ir"}
            rec = {**row, "model": model, "ir": ir, "repair_events": parsed.get("events", []),
                   "schema": schema, "execution": execution,
                   "admission": "blocked-expressiveness-evidence"}
            f.write(json.dumps(rec, default=str) + "\n")
            print(row["id"], row["family"], execution.get("status"), execution.get("reason"))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--bank", default="questions/expressiveness.json")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="qwen2b")
    a = ap.parse_args()
    run(a.bank, a.out, a.model)
