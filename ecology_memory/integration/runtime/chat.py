#!/usr/bin/env python3
"""Interactive/one-shot entrypoint for the typed runtime."""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
INTEGRATION = os.path.dirname(HERE)
ROOT = os.path.dirname(INTEGRATION)
HARNESS = os.path.join(ROOT, "harness")
sys.path.insert(0, HARNESS)

from pipeline import MODEL_ALIASES, run_question  # noqa: E402


def emit(question, model, context, as_json, history, selector, compiler, responder):
    result = run_question(question, model, context=context, history=history,
                          selector=selector, compiler=compiler, responder=responder)
    if as_json:
        print(json.dumps(result, ensure_ascii=False, default=str))
    else:
        print(result["answer"])
    return 0 if result["status"] in {"answer", "data_request"} else 1


def main():
    ap = argparse.ArgumentParser(description="Typed planner/executor/synthesizer chat")
    ap.add_argument("--model", default="qwen2b")
    ap.add_argument("--context", choices=("general", "ebtl"), default="general")
    ap.add_argument("--selector", default=os.environ.get("DSS_TYPED_SELECTOR", "qwen9b>deepseekv4"))
    ap.add_argument("--compiler", default=os.environ.get("DSS_TYPED_COMPILER"))
    ap.add_argument("--responder", default=os.environ.get("DSS_TYPED_RESPONDER", "qwen9b"))
    ap.add_argument("--history-json", default="[]")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("question", nargs="*")
    args = ap.parse_args()
    if args.model not in MODEL_ALIASES:
        ap.error(f"unknown typed model {args.model!r}; have {', '.join(sorted(MODEL_ALIASES))}")
    model = MODEL_ALIASES[args.model]
    try:
        history = json.loads(args.history_json)
        if not isinstance(history, list):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        ap.error("--history-json must be a JSON list")
    compiler = MODEL_ALIASES.get(args.compiler, args.compiler) if args.compiler else model
    responder = ("deterministic" if args.responder == "deterministic" else
                 MODEL_ALIASES.get(args.responder, args.responder))
    if args.question:
        raise SystemExit(emit(" ".join(args.question), model, args.context, args.json,
                              history, args.selector, compiler, responder))
    if args.json:
        ap.error("interactive mode does not support --json")
    print(f"typed diagnostic · model={model} · context={args.context} · Ctrl-D to exit",
          file=sys.stderr)
    while True:
        try:
            question = input("> ").strip()
        except EOFError:
            print()
            return
        if not question:
            continue
        emit(question, model, args.context, False, history, args.selector, compiler, responder)


if __name__ == "__main__":
    main()
