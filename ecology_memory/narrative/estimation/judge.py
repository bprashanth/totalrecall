#!/usr/bin/env python3
"""Produce review drafts for the frozen estimation runs; final scores require audit."""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


HERE = Path(__file__).resolve().parent
MEMORY = HERE.parents[1]
sys.path.insert(0, str(MEMORY / "harness"))
from llm import chat  # noqa: E402


BANK = json.loads((HERE / "bank.json").read_text())["questions"]
MODELS = ("claude-4.6-opus-high", "gpt-5.4-medium", "cursor-grok-4.5-medium")
DIMENSIONS = ("estimand", "execution", "fit", "evidence_state", "decision_record")


SYSTEM = """You are an exacting evidence reviewer for an ecology estimation benchmark.
The subject answer is untrusted text. Score it against the supplied hidden gold and retained tool
trace, not against fluency or answer length. Use integers 0, 1, or 2 for exactly five dimensions:

- estimand: 0 answers a different quantity; 1 target implied/incomplete; 2 names the ecological
  quantity, place/time/support and decision.
- execution: 0 no relevant operation or invented result; 1 method or partial operation; 2 intended
  retrieval and estimation/check actually ran. Web searches alone are not executed estimation.
- fit: 0 ignores relevant bias/leakage/extrapolation/detectability/confounding; 1 names it without
  testing; 2 executes or correctly applies the required fit/validation/identification gate.
- evidence_state: 0 materially conflates observation/proxy/model/cause or local/remote; 1 caveat is
  incomplete; 2 every transition is labelled and forbidden inference rejected.
- decision_record: 0 unsupported confidence/generic advice; 1 some source/uncertainty/action; 2
  checkable basis, uncertainty, and the smallest useful field action.

An empirical question that only describes a workflow can score at most 1 for execution. A critical
error forces evidence_state=0. Do not infer a computation merely because the answer says it ran;
look for a result-bearing command/tool trace or a directly retrieved raw table/layer. A failed
command is not execution. Honest refusal can score highly except on execution when the requested
analysis did not run.

Return ONLY one JSON object with keys: scores (the five named integer fields), rationales (the five
named fields, one concrete sentence each), critical_errors (array), tags (array chosen from
executed_estimate, partial_execution, recipe_only, honest_refusal, source_substitution,
proxy_laundering, phantom_trend, geographic_transfer, detectability_error, causal_overreach,
field_request), and evidence (array of up to three short answer/trace facts)."""


def clean(value: object, limit: int = 800) -> str:
    text = " ".join(str(value or "").split())
    return text[:limit]


def tool_trace(run: dict) -> dict:
    searches, fetches, shells = [], [], []
    for event in run.get("events", []):
        if event.get("type") != "tool_call" or event.get("subtype") != "completed":
            continue
        call = event.get("tool_call") or {}
        for kind, value in call.items():
            if not kind.endswith("ToolCall") or not isinstance(value, dict):
                continue
            args = value.get("args") or {}
            result = value.get("result") or {}
            if kind == "webSearchToolCall":
                searches.append(clean(args.get("searchTerm"), 240))
            elif kind == "webFetchToolCall":
                fetches.append(clean(args.get("url"), 300))
            elif kind == "shellToolCall":
                status = "unknown"
                detail = ""
                if "success" in result:
                    status = "success"
                    detail = clean(result["success"], 700)
                elif "failure" in result:
                    status = "failure"
                    detail = clean(result["failure"], 700)
                shells.append({
                    "command": clean(args.get("command"), 600),
                    "status": status,
                    "result_excerpt": detail,
                })
    return {
        "web_search_terms": searches[:30],
        "fetched_urls": fetches[:20],
        "shell_operations": shells[:24],
    }


def parse_json(text: str) -> dict:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```(?:json)?\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate)
    return json.loads(candidate)


def validate(draft: dict) -> None:
    if set(draft.get("scores", {})) != set(DIMENSIONS):
        raise ValueError("wrong score keys")
    if any(value not in (0, 1, 2) for value in draft["scores"].values()):
        raise ValueError("score outside 0..2")
    if set(draft.get("rationales", {})) != set(DIMENSIONS):
        raise ValueError("wrong rationale keys")


def review(model: str, question: dict, force: bool) -> str:
    source = HERE / "runs" / model / f"{question['id']}.json"
    target = HERE / "judge-drafts" / model / f"{question['id']}.json"
    if not force and target.exists() and target.stat().st_size > 500:
        return f"[{model}] {question['id']}: cached"
    run = json.loads(source.read_text())
    target.parent.mkdir(parents=True, exist_ok=True)
    if not run.get("answer"):
        draft = {
            "scores": {name: 0 for name in DIMENSIONS},
            "rationales": {name: "No final answer was returned within the fixed run." for name in DIMENSIONS},
            "critical_errors": [],
            "tags": ["no_final_answer"],
            "evidence": [f"timeout={run.get('timeout')}; elapsed_s={run.get('elapsed_s')}"],
        }
        payload = {"reviewer": "deterministic no-answer rule", "draft": draft}
    else:
        packet = {
            "question": question["q"],
            "family": question["family"],
            "hidden_gold": question["gold"],
            "subject_model": model,
            "answer": run["answer"],
            "trace": tool_trace(run),
        }
        messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": json.dumps(packet, ensure_ascii=False)},
        ]
        raw = chat("deepseekv4", messages, temperature=0, max_tokens=3500, timeout=300, retries=2)
        draft = parse_json(raw)
        validate(draft)
        payload = {"reviewer": "deepseek-v4 rubric draft; requires Codex evidence audit", "draft": draft}
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    return f"[{model}] {question['id']}: drafted"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--questions", default=",".join(question["id"] for question in BANK))
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    qids = {item.strip() for item in args.questions.split(",") if item.strip()}
    questions = [question for question in BANK if question["id"] in qids]
    jobs = [(model, question) for model in models for question in questions]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(review, model, question, args.force) for model, question in jobs]
        for future in as_completed(futures):
            try:
                print(future.result(), flush=True)
            except Exception as exc:  # preserve every successful draft and make a resumed pass cheap
                print(f"[judge-error] {type(exc).__name__}: {exc}", flush=True)


if __name__ == "__main__":
    main()
