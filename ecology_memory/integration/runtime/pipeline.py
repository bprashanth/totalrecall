"""Production entrypoint for semantic selection → typed execution → audited response."""
import os
import sys
import time


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
BENCH = os.path.join(ROOT, "hermes_bench")
HARNESS = os.path.join(ROOT, "harness")
for path in (BENCH, HARNESS):
    if path not in sys.path:
        sys.path.insert(0, path)

from engine import audited_history_entry, compile_turn, render_turn  # noqa: E402


MODEL_ALIASES = {
    "qwen2b": "qwen2b", "2b": "qwen2b",
    "qwen2b-lora": "loravb", "2b-lora": "loravb", "loravb": "loravb",
    "lora9b": "lora9b", "merged-9b-002": "lora9b", "9b-lora": "lora9b",
    "deepseekv4": "deepseekv4", "deepseek-v4": "deepseekv4", "deepseek": "deepseekv4",
    "qwen9b": "qwen9b", "qwen27b": "qwen27b", "qwen122b": "qwen122b",
    "qwen397b": "qwen397b", "coder30b": "coder30b", "glm": "glm",
}


def _trim_execution(result):
    out = dict(result)
    value = out.get("value")
    if isinstance(value, dict) and isinstance(value.get("rows"), list):
        value = dict(value)
        value["n_rows"] = len(value["rows"])
        value["rows"] = value["rows"][:20]
        out["value"] = value
    return out


def run_question(question, model="qwen2b", context="general", history=None,
                 selector="qwen9b>deepseekv4", compiler=None, responder="qwen9b"):
    started = time.time()
    history = history or []
    compiler = compiler or model
    compiler_role = f"{selector}@{compiler}" if selector else compiler
    compiled = compile_turn(question, compiler_role, history, context=context)
    rendered = render_turn(question, compiled, responder, history)
    evidence = audited_history_entry(question, compiled)
    history_record = [
        {"role": "user", "content": question},
        {"role": "assistant", "content": "AUDITED EVIDENCE: " +
         __import__("json").dumps(evidence, ensure_ascii=False)},
    ]
    return {
        "runtime": "typed", "model": model, "selector": selector,
        "compiler": compiler, "responder": responder, "context": context,
        "question": question, "status": compiled["execution"].get("status"),
        "answer": rendered["answer"], "ir": compiled.get("ir"),
        "dialogue_mode": compiled.get("dialogue_mode"),
        "schema": compiled.get("schema"), "execution": _trim_execution(compiled["execution"]),
        "repair_events": compiled.get("repair_events", []),
        "parse_valid": compiled.get("parse_valid", False), "audit": rendered.get("audit"),
        "fallback": rendered.get("fallback"), "history_record": history_record,
        "latency_s": round(time.time() - started, 3),
    }
