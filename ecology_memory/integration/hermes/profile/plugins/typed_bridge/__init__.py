"""Minimal Hermes boundary for the general typed compiler/executor/responder runtime.

This plugin deliberately contains no topic aliases, regex intent routes, or canned ecology
answers. The semantic selector and compiler operate in the runtime; Python executes the selected
algebra and this bridge records the real audited call for Hermes `/why` and session resume.
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from openai.types.chat import ChatCompletion
from openai.types.chat.chat_completion import Choice
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.completion_usage import CompletionUsage


RUNTIME = "/opt/data/work/dss_typed/ecology_memory/integration/runtime"
BRIDGE = os.path.join(RUNTIME, "chat.py")
WHY_LEDGER = "/opt/data/work/.why_ledger.json"
_STATE = {"typed_answer": None, "audited_history": []}
_PLUGIN_CONTEXT = None

EVALUATE_SCHEMA = {
    "name": "typed_evaluate",
    "description": (
        "Compile one scoped data question to the pinned typed algebra, execute governed "
        "connectors, and return an audited answer or precise DataRequest."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "question": {"type": "string"},
            "model": {"type": "string"},
            "context": {"type": "string", "enum": ["general", "ebtl"]},
        },
        "required": ["question", "model", "context"],
    },
}


def _message_value(item, key, default=None):
    return item.get(key, default) if isinstance(item, dict) else getattr(item, key, default)


def _restore_audited_history(conversation_history):
    """Recover only code-owned evidence summaries from persisted typed tool results."""
    recovered = []
    seen = set()
    for item in conversation_history or []:
        role = _message_value(item, "role")
        name = _message_value(item, "name") or _message_value(item, "tool_name")
        if role != "tool" and name != "typed_evaluate":
            continue
        content = _message_value(item, "content", "") or ""
        try:
            trace = json.loads(content) if isinstance(content, str) else content
        except (json.JSONDecodeError, TypeError):
            continue
        record = trace.get("history_record") if isinstance(trace, dict) else None
        if not isinstance(record, list):
            continue
        for message in record:
            marker = (message.get("role"), message.get("content"))
            if marker not in seen:
                seen.add(marker)
                recovered.append(message)
    if recovered:
        _STATE["audited_history"] = recovered


def _evaluate_tool(args, **kwargs):
    command = [
        "python", BRIDGE,
        "--model", args["model"],
        "--context", args["context"],
        "--selector", os.environ.get("DSS_TYPED_SELECTOR", "qwen9b>deepseekv4"),
        "--compiler", os.environ.get("DSS_TYPED_COMPILER", args["model"]),
        "--responder", os.environ.get("DSS_TYPED_RESPONDER", "qwen9b"),
        "--history-json", json.dumps(_STATE["audited_history"], ensure_ascii=False),
        "--json", args["question"],
    ]
    completed = subprocess.run(command, text=True, capture_output=True, timeout=300)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-1200:]
        return json.dumps({"error": f"typed bridge failed closed: {detail}"})
    try:
        trace = json.loads(completed.stdout.strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return json.dumps({"error": "typed bridge returned an invalid trace"})

    _STATE["typed_answer"] = trace.get("answer")
    record = trace.get("history_record")
    if isinstance(record, list):
        _STATE["audited_history"].extend(record)
    _write_why_ledger(trace)
    print(f"  ┊ 🧮 typed_evaluate  {trace.get('status', 'unknown')}", flush=True)
    value = (trace.get("execution") or {}).get("value") or {}
    events = value.get("connector_events") or (trace.get("execution") or {}).get("provenance") or []
    for event in events:
        route = event.get("tool") or event.get("route") or event.get("source")
        if route:
            suffix = (f"  {event.get('output_rows')} rows"
                      if event.get("output_rows") is not None else "")
            print(f"  ┊ 🔌 {route}{suffix}", flush=True)
    return json.dumps(trace, ensure_ascii=False, default=str)


def _write_why_ledger(trace):
    """Expose audited typed provenance to the existing origin `/why` renderer.

    The renderer owns a small, process-external ledger because slash commands are not transcript
    messages. Translate only executed routes and counts; never infer a data step from answer prose.
    """
    try:
        execution = trace.get("execution") or {}
        value = execution.get("value") or {}
        events = value.get("connector_events") or execution.get("provenance") or []
        entries = []
        route_map = {
            "points": "occurrence", "occurrence": "occurrence",
            "discovery": "paper_data", "paper": "paper_data",
            "fire": "fire", "landcover": "landcover", "greenness": "greenness",
            "alphaearth": "embedding", "embedding": "embedding",
            "worldclim": "predict", "transfer": "predict",
        }
        for event in events:
            raw_route = str(event.get("tool") or event.get("route") or
                            event.get("source") or "").lower()
            connector = next((mapped for marker, mapped in route_map.items()
                              if marker in raw_route), None)
            if not connector and raw_route.startswith("published-"):
                connector = "site evidence"
            if not connector:
                continue
            parameters = event.get("parameters") or {}
            entry = {
                "connector": connector,
                "sub": raw_route,
                "species": parameters.get("species"),
                "bbox": parameters.get("bbox"),
                "points_file": None,
                "loc": parameters.get("place"),
                "json": event.get("gate") or {},
                "n": (event.get("output_rows") if event.get("output_rows") is not None
                      else len(value.get("rows") or [])),
                "raw": "audited typed connector event",
            }
            entries.append(entry)
        if not entries and execution.get("status") == "answer":
            rows = value.get("rows") if isinstance(value.get("rows"), list) else []
            entries.append({
                "connector": "site evidence", "sub": str(value.get("source") or "typed evidence"),
                "species": None, "bbox": None, "points_file": None, "loc": None,
                "json": {}, "n": len(rows), "raw": "audited typed evidence record",
            })
        with open(WHY_LEDGER, "w", encoding="utf-8") as handle:
            json.dump(entries, handle, ensure_ascii=False)
    except Exception as exc:
        print(f"  ┊ ⚠ /why provenance export failed: {type(exc).__name__}", flush=True)


def _record_tool_audit(args, raw_result, session_id=None):
    owned_db = False
    try:
        cli = _PLUGIN_CONTEXT._manager._cli_ref if _PLUGIN_CONTEXT else None
        db = getattr(cli, "_session_db", None)
        sid = (session_id or os.environ.get("HERMES_SESSION_ID") or
               os.environ.get("DSS_TYPED_RESUME_SESSION") or
               getattr(cli, "session_id", None) or
               getattr(getattr(cli, "agent", None), "session_id", None))
        if not sid:
            return
        if not db:
            # Resume/non-interactive Hermes paths do not always expose the CLI's
            # SessionDB through the plugin manager. Use Hermes' own storage API,
            # pointed at the active profile, rather than silently dropping audit
            # records or writing SQLite directly.
            from hermes_state import SessionDB
            db = SessionDB(Path(os.environ["HERMES_HOME"]) / "state.db")
            owned_db = True
        call_id = f"typed_{int(time.time() * 1000000)}"
        db.append_message(
            session_id=sid, role="assistant", content=None,
            tool_calls=[{"id": call_id, "type": "function", "function": {
                "name": "typed_evaluate", "arguments": json.dumps(args, ensure_ascii=False)}}],
        )
        db.append_message(session_id=sid, role="tool", content=raw_result,
                          tool_name="typed_evaluate", tool_call_id=call_id)
    except Exception as exc:
        print(f"  ┊ ⚠ tool audit persistence failed: {type(exc).__name__}", flush=True)
    finally:
        if owned_db:
            db.close()


def _pre_llm(user_message=None, conversation_history=None, session_id=None, **kwargs):
    if os.environ.get("DSS_EVAL_RUNTIME") != "typed":
        return None
    message = (user_message or "").strip()
    if not message:
        return None
    _restore_audited_history(conversation_history)
    args = {
        "question": message,
        "model": os.environ.get("DSS_TYPED_MODEL", "qwen2b"),
        "context": os.environ.get("DSS_TYPED_CONTEXT", "general"),
    }
    try:
        raw_result = (_evaluate_tool(args) if _PLUGIN_CONTEXT is None else
                      _PLUGIN_CONTEXT.dispatch_tool("typed_evaluate", args))
        result = json.loads(raw_result)
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError, TypeError) as exc:
        _STATE["typed_answer"] = f"The typed runtime failed closed: {type(exc).__name__}."
        return {"context": "The typed runtime is unavailable; do not invent an answer."}
    if result.get("error"):
        _STATE["typed_answer"] = result["error"]
        return {"context": "The typed runtime failed closed; do not invent an answer."}
    _record_tool_audit(args, raw_result, session_id)
    return {"context": "The audited typed runtime already produced the final answer."}


def _llm_execution(request=None, next_call=None, model=None, **kwargs):
    answer = _STATE.get("typed_answer")
    if not answer:
        return next_call(request)
    _STATE["typed_answer"] = None
    return ChatCompletion(
        id=f"typed-{int(time.time() * 1000)}",
        choices=[Choice(index=0, finish_reason="stop",
                        message=ChatCompletionMessage(role="assistant", content=answer))],
        created=int(time.time()), model=model or "typed", object="chat.completion",
        usage=CompletionUsage(completion_tokens=0, prompt_tokens=0, total_tokens=0),
    )


def _transform(response_text=None, **kwargs):
    answer = _STATE.get("typed_answer")
    if answer:
        _STATE["typed_answer"] = None
        return answer
    return None


def register(ctx):
    global _PLUGIN_CONTEXT
    _PLUGIN_CONTEXT = ctx
    ctx.register_tool(name="typed_evaluate", toolset="typed-evaluation",
                      schema=EVALUATE_SCHEMA, handler=_evaluate_tool, emoji="🧮")
    ctx.register_hook("pre_llm_call", _pre_llm)
    ctx.register_hook("transform_llm_output", _transform)
    ctx.register_middleware("llm_execution", _llm_execution)
