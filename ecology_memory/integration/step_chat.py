#!/usr/bin/env python3
"""Human-stepped view of the real typed selector/compiler/executor/responder pipeline."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
import textwrap
import time
import uuid
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BENCH = ROOT / "hermes_bench"
HARNESS = ROOT / "harness"
for path in (str(BENCH), str(HARNESS)):
    if path not in sys.path:
        sys.path.insert(0, path)

from engine import audited_history_entry, compile_turn, render_turn  # noqa: E402


class StopTurn(Exception):
    """The operator declined the next stage; no later work should run."""


class Paint:
    CODES = {
        "reset": "\033[0m", "bold": "\033[1m", "dim": "\033[2m",
        "cyan": "\033[36m", "blue": "\033[34m", "green": "\033[32m",
        "yellow": "\033[33m", "red": "\033[31m", "magenta": "\033[35m",
    }

    def __init__(self, enabled: bool):
        self.enabled = enabled

    def __call__(self, value: str, *styles: str) -> str:
        if not self.enabled:
            return value
        return "".join(self.CODES[item] for item in styles) + value + self.CODES["reset"]


STAGE_META = {
    "capability_selected": (
        "1", "CAPABILITY SELECTED", "Selector",
        "The selector chooses measurement contracts, not facts or connector output.",
        "The verifier will check whether those measurements really answer the question.",
    ),
    "capability_verified": (
        "2", "SELECTION VERIFIED", "Verifier",
        "The verifier may retain, narrow, replace, or reject the proposed capabilities.",
        "The compiler will translate the question and admitted capabilities into algebra.",
    ),
    "algebra_compiled": (
        "3", "ALGEBRA COMPILED", "Compiler",
        "This JSON is a proposed data plan. No dataset has been queried yet.",
        "The algebra verifier will check that the plan still answers the original question.",
    ),
    "algebra_verified": (
        "4", "ALGEBRA VERIFIED", "Verifier",
        "The verifier checks meaning and tree shape; Python still owns schema enforcement.",
        "Python will validate the tree and preview execution. No model is used for that.",
    ),
    "execution_preview": (
        "5", "EXECUTION PREVIEW", "Python",
        "This is the validated plan. Actual connector events appear only after execution.",
        "Python will route the algebra to governed connectors and execute them.",
    ),
    "execution_complete": (
        "6", "DATA RETURNED", "Python",
        "These values, labels, units, sources, and limits came from deterministic execution.",
        "The responder will receive a bounded evidence pack and write the answer.",
    ),
    "response_preview": (
        "7", "RESPONSE PREVIEW", "Responder",
        "The responder receives this audited pack, not unrestricted connector output.",
        "The responder model will turn the pack into plain language.",
    ),
    "response_complete": (
        "8", "FINAL ANSWER AND AUDIT", "Audit",
        "The prose is checked mechanically; unsafe prose falls back to deterministic rendering.",
        "This turn is complete and can now become audited multi-turn history.",
    ),
}


def _jsonable(value):
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _pretty(value) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _row_count(value: dict) -> int | None:
    if not isinstance(value, dict):
        return None
    if isinstance(value.get("n_rows"), int):
        return value["n_rows"]
    if isinstance(value.get("rows"), list):
        return len(value["rows"])
    return None


def _walk_ir(node, depth=0):
    if not isinstance(node, dict):
        return []
    op = node.get("op", "?")
    if op == "SELECT":
        region = node.get("region") or {}
        place = region.get("place") if isinstance(region, dict) else region
        line = f"SELECT {node.get('entity')} in {place or '?place'}"
    elif op == "ANNOTATE":
        line = f"ANNOTATE with {node.get('layer')}"
    elif op == "REGION":
        line = f"REGION {node.get('place')}"
    elif op == "BUFFER":
        line = f"BUFFER {node.get('radius_km')} km"
    elif op == "RELATE":
        threshold = node.get("threshold_km")
        suffix = f" at {threshold} km" if threshold is not None else ""
        line = f"RELATE {node.get('relation')}{suffix}"
    elif op == "ESTIMATE":
        line = f"ESTIMATE using {node.get('method')}"
    else:
        line = op
    lines = [(depth, line)]
    for key in ("source", "left", "right", "target", "region"):
        if isinstance(node.get(key), dict):
            lines.extend(_walk_ir(node[key], depth + 1))
    for item in node.get("items", []) if isinstance(node.get("items"), list) else []:
        lines.extend(_walk_ir(item, depth + 1))
    return lines


class TraceStore:
    def __init__(self, config: dict, trace_root: Path):
        stamp = time.strftime("%Y%m%d-%H%M%S")
        self.trace_root = trace_root
        self.path = trace_root / f"{stamp}-{uuid.uuid4().hex[:8]}.json"
        self.latest = trace_root / "latest.json"
        self.data = {
            "schema_version": 1,
            "session_id": self.path.stem,
            "started_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "status": "running",
            "config": config,
            "turns": [],
        }
        self.save()

    def new_turn(self, question: str) -> dict:
        turn = {"question": question, "status": "running", "stages": []}
        self.data["turns"].append(turn)
        self.save()
        return turn

    def save(self) -> None:
        self.trace_root.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.data, ensure_ascii=False, indent=2, default=str) + "\n"
        for destination in (self.path, self.latest):
            fd, temporary = tempfile.mkstemp(prefix=".step-chat-", dir=self.trace_root)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                os.replace(temporary, destination)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)


class StepDisplay:
    def __init__(self, store: TraceStore, turn: dict, paint: Paint, auto_yes: bool,
                 input_stream=sys.stdin, output_stream=sys.stdout):
        self.store = store
        self.turn = turn
        self.paint = paint
        self.auto_yes = auto_yes
        self.input = input_stream
        self.output = output_stream

    def write(self, value=""):
        print(value, file=self.output, flush=True)

    def rule(self, color="blue"):
        width = min(max(shutil.get_terminal_size((88, 24)).columns, 60), 110)
        self.write(self.paint("─" * width, color, "dim"))

    def __call__(self, stage: str, payload: dict) -> None:
        record = {"stage": stage, "at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                  "payload": _jsonable(payload)}
        self.turn["stages"].append(record)
        self.turn["current_stage"] = stage
        self.store.save()
        self.show(stage, payload)
        if stage != "response_complete":
            self.confirm(stage, payload)

    def show(self, stage: str, payload: dict) -> None:
        number, title, owner, explanation, next_step = STAGE_META[stage]
        self.write()
        self.rule("cyan")
        self.write(self.paint(f" STEP {number}  {title} ", "bold", "cyan"))
        model = payload.get("model")
        uses_model = bool(model and model != "deterministic")
        owner_value = owner + (f" · model={model}" if uses_model else " · deterministic Python")
        self.write(self.paint(owner_value, "magenta" if uses_model else "green"))
        self.write(textwrap.fill(explanation, width=100))
        self.write()

        if stage in {"capability_selected", "capability_verified"}:
            if payload.get("parsed"):
                self.write(self.paint(f"Mode: {payload['parsed'].get('mode')}", "bold"))
            selected = payload.get("selected") or []
            if selected:
                self.write(self.paint("Selected capabilities:", "bold"))
                for item in selected:
                    self.write(self.paint(f"  • {item.get('entity')}", "green", "bold"))
                    detail = item.get("description") or item.get("grain")
                    if detail:
                        self.write("    " + textwrap.fill(str(detail), width=94,
                                                         subsequent_indent="    "))
                    tags = [str(item[key]) for key in ("evidence", "grain", "binding")
                            if item.get(key) is not None]
                    if tags:
                        self.write(self.paint("    " + " · ".join(tags), "dim"))
            else:
                self.write(self.paint("Selected capabilities: none (the system should fail closed)",
                                      "yellow"))
            events = payload.get("events") or []
            for event in events:
                if "verifier:" in event:
                    self.write(self.paint("Decision: " + event.split("capability_verifier:", 1)[-1],
                                          "yellow"))

        elif stage in {"algebra_compiled", "algebra_verified"}:
            self.write(self.paint("Proposed algebra:", "bold"))
            self.write(self.paint(_pretty(payload.get("ir")), "yellow"))
            events = payload.get("events") or payload.get("parser_events") or []
            if events:
                self.write(self.paint("Events: " + ", ".join(events), "dim"))

        elif stage == "execution_preview":
            schema = payload.get("schema") or {}
            color = "green" if schema.get("valid") else "red"
            self.write(self.paint(
                f"Schema valid: {schema.get('valid')} · ops={schema.get('ops') or []} · "
                f"holes={schema.get('holes') or []}", color, "bold"))
            ir = payload.get("ir")
            if ir:
                self.write(self.paint("Plan:", "bold"))
                for depth, line in _walk_ir(ir):
                    self.write("  " + "  " * depth + self.paint("• " + line, "cyan"))
            capabilities = payload.get("selected_capabilities") or []
            if capabilities:
                self.write(self.paint("Declared data contracts:", "bold"))
                for item in capabilities:
                    self.write(f"  • {item.get('entity')} — {item.get('description', 'no description')}")
            self.write(self.paint(
                "The exact Python connector and returned row count will be recorded after execution.",
                "dim"))

        elif stage == "execution_complete":
            execution = payload.get("execution") or {}
            status = execution.get("status")
            color = "green" if status == "answer" else "yellow" if status == "data_request" else "red"
            self.write(self.paint(
                f"Status: {status} · evidence={execution.get('label') or 'n/a'}",
                color, "bold"))
            if execution.get("reason"):
                self.write(f"Reason: {execution['reason']}")
            value = execution.get("value") or {}
            if value:
                self.write(f"Source: {value.get('source') or 'not declared'}")
                self.write(f"Grain: {value.get('grain') or value.get('kind') or 'not declared'}")
                count = _row_count(value)
                if count is not None:
                    self.write(f"Rows: {count}")
                if value.get("note"):
                    self.write(self.paint("Limit: " + str(value["note"]), "yellow"))
            events = value.get("connector_events") or execution.get("provenance") or []
            self.write(self.paint("Actual connector events:", "bold"))
            if not events:
                self.write("  • none")
            for event in events:
                route = event.get("tool") or event.get("route") or event.get("source") or "unknown"
                rows = event.get("output_rows")
                suffix = f" → {rows} rows" if rows is not None else ""
                self.write(self.paint(f"  • {route}{suffix}", "green"))
                if event.get("implementation"):
                    self.write(self.paint(f"    {event['implementation']}", "dim"))
                if event.get("parameters"):
                    self.write("    parameters=" + json.dumps(event["parameters"], ensure_ascii=False))

        elif stage == "response_preview":
            pack = payload.get("evidence_pack") or {}
            value = pack.get("value") or {}
            self.write(f"Status: {pack.get('status')} · evidence={pack.get('evidence_label')}")
            self.write(f"Source: {value.get('source') or 'none'}")
            count = _row_count(value)
            if count is not None:
                self.write(f"Rows exposed to responder: {count}")
            if value.get("note"):
                self.write(self.paint("Required limitation: " + str(value["note"]), "yellow"))
            if model == "deterministic":
                next_step = "Python will render the evidence pack without calling a model."

        elif stage == "response_complete":
            self.write(self.paint("Answer:", "bold", "green"))
            self.write(textwrap.fill(str(payload.get("answer") or ""), width=100))
            audit = payload.get("audit") or {}
            passed = audit.get("passed")
            self.write()
            self.write(self.paint(
                f"Mechanical audit: {'PASS' if passed else 'FAIL'}"
                f" · fallback={payload.get('fallback', False)}",
                "green" if passed else "red", "bold"))
            failed = [key for key, value in audit.items()
                      if key not in {"passed", "new_numbers"} and value is False]
            if failed:
                self.write(self.paint("Failed checks: " + ", ".join(failed), "red"))

        self.write()
        self.write(self.paint("Next: ", "bold") + next_step)
        self.write(self.paint(f"Trace: {self.store.path}", "dim"))

    def explain(self, stage: str) -> None:
        explanation = STAGE_META[stage][3]
        self.write(self.paint("Why this stage exists:", "bold", "cyan"))
        self.write(textwrap.fill(explanation, width=100))
        self.write("It can constrain or reject a plan, but it cannot create evidence that a connector did not return.")

    def confirm(self, stage: str, payload: dict) -> None:
        if self.auto_yes:
            self.write(self.paint("Proceeding automatically (--yes).", "dim"))
            return
        while True:
            self.write(self.paint("Proceed? [y/n/?/raw/catalog/trace] ", "bold", "cyan"))
            answer = self.input.readline()
            if answer == "":
                raise StopTurn("input closed")
            command = answer.strip().lower()
            if command in {"y", "yes"}:
                return
            if command in {"n", "no", "q", "quit"}:
                raise StopTurn(f"stopped after {stage}")
            if command in {"?", "why", "help"}:
                self.explain(stage)
            elif command == "raw":
                self.write(_pretty(payload))
            elif command == "catalog":
                selected = payload.get("selected") or payload.get("selected_capabilities") or []
                self.write(_pretty(selected))
            elif command == "trace":
                self.write(str(self.store.path))
            else:
                self.write("Use y, n, ?, raw, catalog, or trace.")


def color_enabled(mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "never" or os.environ.get("NO_COLOR") is not None:
        return False
    return sys.stdout.isatty()


def run_turn(question: str, args, history: list[dict], store: TraceStore) -> bool:
    turn = store.new_turn(question)
    display = StepDisplay(store, turn, Paint(color_enabled(args.color)), args.yes)
    compiler_role = f"{args.selector}@{args.compiler}" if args.selector else args.compiler
    try:
        compiled = compile_turn(
            question, compiler_role, history, context=args.context, observer=display)
        rendered = render_turn(
            question, compiled, args.responder, history, observer=display)
    except StopTurn as exc:
        turn["status"] = "stopped"
        turn["stop_reason"] = str(exc)
        store.save()
        print(Paint(color_enabled(args.color))(f"Turn stopped safely: {exc}", "yellow"))
        return False
    except KeyboardInterrupt:
        turn["status"] = "interrupted"
        store.save()
        print("\nTurn interrupted safely.")
        return False
    except Exception as exc:
        turn["status"] = "error"
        turn["error"] = f"{type(exc).__name__}: {exc}"
        store.save()
        raise

    turn["status"] = "complete"
    turn["compiled"] = _jsonable(compiled)
    turn["rendered"] = _jsonable(rendered)
    turn["history_record"] = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": "AUDITED EVIDENCE: " + json.dumps(
            audited_history_entry(question, compiled), ensure_ascii=False)},
    ]
    history.extend(turn["history_record"])
    store.save()
    return True


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Pause after each real typed-pipeline stage and inspect what happened.")
    ap.add_argument("--context", choices=("general", "ebtl"), default="ebtl")
    ap.add_argument("--selector", default="qwen9b>deepseekv4",
                    help="capability selector and optional verifier chain")
    ap.add_argument("--compiler", default="qwen2b",
                    help="last-mile algebra compiler (tested default: qwen2b)")
    ap.add_argument("--responder", default="lora9b",
                    help="answer writer (default: local merged-9b-003 role)")
    ap.add_argument("--question", "-q", help="run one question instead of opening a prompt")
    ap.add_argument("--yes", "-y", action="store_true",
                    help="show all stages without pausing (useful for smoke tests)")
    ap.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    ap.add_argument("--trace-dir", type=Path, default=HERE / "runs" / "step-repl")
    return ap


def main() -> int:
    args = parser().parse_args()
    config = {"context": args.context, "selector": args.selector,
              "compiler": args.compiler, "responder": args.responder,
              "algebra": "ecology snapshot v2.2.1"}
    store = TraceStore(config, args.trace_dir)
    paint = Paint(color_enabled(args.color))
    print(paint("\nTyped Pipeline Step REPL", "bold", "cyan"))
    print("Four core jobs: select data → compile a plan → execute Python → write the answer.")
    print("Safety checks appear as separate stages so you can inspect them.")
    print(f"selector={args.selector} · compiler={args.compiler} · responder={args.responder}")
    print(paint(f"live trace: {store.path}\n", "dim"))

    history: list[dict] = []
    if args.question:
        completed = run_turn(args.question, args, history, store)
        store.data["status"] = "complete" if completed else "stopped"
        store.save()
        return 0 if completed else 2

    while True:
        try:
            question = input(paint("Question> ", "bold", "green")).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not question:
            continue
        if question.lower() in {"quit", "exit", "/quit", "/exit"}:
            break
        run_turn(question, args, history, store)
        print()
    store.data["status"] = "complete"
    store.save()
    print(paint(f"Session trace saved to {store.path}", "dim"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
