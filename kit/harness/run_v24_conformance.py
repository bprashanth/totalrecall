#!/usr/bin/env python3
"""Gold-execute and parser-probe the coordinated ALG-002/ALG-015 v2.4 surface."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os

import parser as P
from ir_schema import canonicalize, validate
from run_buffer_conformance import execute_fixture


HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = "v2.4.0-draft"
DEFAULT_BANKS = [
    os.path.join(HERE, "..", "conformance", "buffer_questions_v2.4.json"),
    os.path.join(HERE, "..", "conformance", "filter_questions_v2.4.json"),
]


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--model", default="qwen2b")
    cli.add_argument("--questions", action="append",
                     help="question bank; repeat to replace the two default banks")
    cli.add_argument("--out", required=True)
    cli.add_argument("--corpus-out")
    cli.add_argument("--require-parser-perfect", action="store_true")
    args = cli.parse_args()
    banks = args.questions or DEFAULT_BANKS

    items = []
    for path in banks:
        with open(path, encoding="utf-8") as stream:
            bank = json.load(stream)
        if bank.get("algebra_version") != PROFILE:
            raise SystemExit(f"wrong algebra profile in {path}")
        items.extend((path, question) for question in bank["questions"])

    rows, gold_failures = [], 0
    parser_matches = parser_required = 0
    for path, item in items:
        gold = canonicalize(item["gold_ir"], PROFILE)
        schema = validate(gold, PROFILE)
        execution = execute_fixture(gold) if schema["valid"] else {
            "status": "error", "reason": "invalid_gold"}
        expect = item["expect"]
        status_ok = (execution["status"] in {"answer", "data_request"}
                     if expect == "answer_or_data_request" else execution["status"] == expect)
        gold_failures += int(not schema["valid"] or not status_ok)

        parsed = P.parse(item["q"], role=args.model, algebra_version=PROFILE)
        compiled = canonicalize(parsed.get("ir"), PROFILE)
        compiled_schema = validate(compiled, PROFILE) if compiled else {
            "valid": False, "errors": ["no IR"], "holes": [], "ops": []}
        exact = compiled == gold
        required = item.get("parser_required", True)
        parser_required += int(required)
        parser_matches += int(required and exact and compiled_schema["valid"])
        rows.append({
            "id": item["id"], "question": item["q"], "expect": expect,
            "proposal": "ALG-015" if item["id"].startswith("buf-") else "ALG-002",
            "source_bank": os.path.basename(path), "gold_ir": gold,
            "gold_schema": schema, "gold_execution": execution,
            "compiled_ir": compiled, "compiled_schema": compiled_schema,
            "parser_exact_canonical_match": exact, "parser_required": required,
            "repair_events": parsed.get("events") or [],
            "raw_parse": parsed.get("raw") if not compiled_schema["valid"] else None,
        })
        print(f"{item['id']}: gold={'ok' if status_ok else 'FAIL'} "
              f"parser={'match' if exact else 'different'}", flush=True)

    artifact = {
        "schema_version": "v24-conformance-evidence-v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "algebra_version": PROFILE, "model": args.model,
        "question_banks": [os.path.relpath(path, os.getcwd()) for path in banks],
        "summary": {"n": len(rows), "gold_execution_failures": gold_failures,
                    "parser_required": parser_required,
                    "parser_exact_canonical_matches": parser_matches,
                    "parser_exact_canonical_rate": round(parser_matches / parser_required, 4),
                    "parser_promotion_pass": parser_matches == parser_required},
        "rows": rows,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as stream:
        json.dump(artifact, stream, indent=2, default=str)
    if args.corpus_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.corpus_out)), exist_ok=True)
        system = P.build_messages("placeholder", algebra_version=PROFILE)[0]["content"]
        with open(args.corpus_out, "w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps({"messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": row["question"]},
                    {"role": "assistant", "content": json.dumps(row["gold_ir"])}],
                    "meta": {"proposal": row["proposal"], "algebra_version": PROFILE,
                             "source": row["source_bank"],
                             "gold_execution_status": row["gold_execution"]["status"]}
                }) + "\n")
    print(args.out)
    if gold_failures:
        raise SystemExit(2)
    if args.require_parser_perfect and parser_matches != parser_required:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
