#!/usr/bin/env python3
"""Run the evidence-chain benchmark turn by turn through the live Idli Insight bridge."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parent
MEMORY = BENCH.parents[2]
REPO = MEMORY.parent
HARNESS = MEMORY / "harness"
sys.path.insert(0, str(HARNESS))
import llm  # noqa: E402
import parser as algebra_parser  # noqa: E402


BRIDGE = os.environ.get("IDLI_INSIGHT_URL", "http://127.0.0.1:7011").rstrip("/")
TOKEN_PATH = pathlib.Path(os.environ.get(
    "IDLI_INSIGHT_TOKEN_FILE",
    str(MEMORY / "integration/codex_native/runs/service/.api-token"),
))
LORA004D_URL = os.environ.get(
    "LORA9B004D_URL", "http://172.17.0.1:8012/v1/chat/completions")
RUNTIME_FILES = [
    MEMORY / "harness" / "connectors.py",
    MEMORY / "harness" / "origin_adapters.py",
    MEMORY / "integration" / "codex_native" / "server.py",
    MEMORY / "integration" / "codex_native" / "ecology_artifacts.py",
    BENCH / "arms.json",
    BENCH / "questions.json",
    BENCH / "scoring.md",
    pathlib.Path(__file__).resolve(),
]


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                      separators=(",", ":"))


def sha(value: Any) -> str:
    raw = value if isinstance(value, bytes) else (
        value.encode() if isinstance(value, str) else stable_json(value).encode())
    return hashlib.sha256(raw).hexdigest()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def append_jsonl(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def _request(url: str, payload: dict | None = None, token: str | None = None,
             timeout: int = 900) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(
        url, data=json.dumps(payload).encode() if payload is not None else None,
        headers=headers)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def bridge_turn(session_id: str, question: str, owner: str = "benchmark") -> dict:
    token = TOKEN_PATH.read_text().strip()
    payload = {
        "model": "idli-insight", "stream": False, "session_id": session_id,
        "messages": [{"role": "user", "content": question}],
        "idlisseus_context": {"session_id": session_id, "owner": owner},
    }
    started = time.monotonic()
    response = _request(BRIDGE + "/v1/chat/completions", payload, token, timeout=1200)
    elapsed = round(time.monotonic() - started, 3)
    return {"answer": response["choices"][0]["message"]["content"],
            "usage": response.get("usage") or {}, "latency_s": elapsed,
            "response_id": response.get("id")}


def bridge_audit(session_id: str, turn: int) -> list[dict]:
    token = TOKEN_PATH.read_text().strip()
    return _request(f"{BRIDGE}/v1/audit/{session_id}/{turn}", token=token)["events"]


def _extract_json(text: str) -> dict | None:
    value = algebra_parser.extract_json(text or "")
    return value if isinstance(value, dict) else None


def verifier_prompt(question: str, answer: str, audit: list[dict]) -> str:
    evidence = []
    for event in audit:
        if event.get("type") == "skill_call":
            result = event.get("result") or {}
            execution = result.get("execution") or {}
            value = execution.get("value") or {}
            compact_rows = [{key: row.get(key) for key in (
                "id", "title", "doi", "source_connector", "evidence_kind", "scientific_name",
                "lat", "lon", "point_id", "score", "evidence_label") if row.get(key) is not None}
                for row in (value.get("rows") or [])[:10] if isinstance(row, dict)]
            evidence.append({
                "skill": event.get("skill"), "args": event.get("args"),
                "status": execution.get("status"), "reason": execution.get("reason"),
                "source": value.get("source"), "label": value.get("label"),
                "note": str(value.get("note") or "")[:500], "rows": compact_rows,
                "artifact": value.get("artifact"), "result_id": value.get("result_id"),
            })
    return (
        "You are a strict evidence verifier for an Indian conservation NGO. Check the candidate "
        "answer only against the audited skill material. Model memory is not evidence. Do not add "
        "a taxon, paper, coordinate or estimate absent from the audit. Preserve useful map and "
        "audit links. Spatial overlap is not interaction. Keep the answer under 180 words. Return "
        "only complete JSON with keys decision "
        "('accept' or 'revise'), answer, and critical_errors (array). Use direct Indian English, "
        "not ornate British phrasing.\n\nQUESTION:\n" + question +
        "\n\nCANDIDATE ANSWER:\n" + answer +
        "\n\nAUDITED MATERIAL:\n" + json.dumps(evidence, ensure_ascii=False, default=str)
    )


def deepseek_verify(question: str, answer: str, audit: list[dict]) -> dict:
    prompt = verifier_prompt(question, answer, audit)
    started = time.monotonic()
    text = llm.chat("deepseekv4", [{"role": "user", "content": prompt}],
                    max_tokens=2400, use_cache=True, timeout=240)
    parsed = _extract_json(text) or {}
    return {"latency_s": round(time.monotonic() - started, 3), "raw": text,
            "decision": parsed.get("decision") or "parse_failed",
            "answer": parsed.get("answer") or answer,
            "critical_errors": parsed.get("critical_errors") or []}


def lora_verify(question: str, answer: str, audit: list[dict]) -> dict:
    prompt = verifier_prompt(question, answer, audit)
    payload = {"model": "lora9b", "temperature": 0, "max_tokens": 1800,
               "messages": [{"role": "user", "content": prompt}]}
    started = time.monotonic()
    raw = _request(LORA004D_URL, payload, timeout=420)
    text = raw["choices"][0]["message"].get("content") or ""
    parsed = _extract_json(text) or {}
    return {"latency_s": round(time.monotonic() - started, 3), "raw": text,
            "decision": parsed.get("decision") or "parse_failed",
            "answer": parsed.get("answer") or answer,
            "critical_errors": parsed.get("critical_errors") or [],
            "usage": raw.get("usage") or {}}


def skill_calls(audit: list[dict]) -> list[dict]:
    return [event for event in audit if event.get("type") == "skill_call"]


def score_turn(turn: dict, audit: list[dict], answer: str) -> dict:
    required = turn.get("requires") or []
    calls = skill_calls(audit)
    skills = [event.get("skill") for event in calls]
    args = [event.get("args") or {} for event in calls]
    lower = answer.lower()
    # Formatting must not change semantic scoring (for example, ``does **not** prove``).
    semantic = re.sub(r"[`*_~]", "", lower)
    semantic = re.sub(r"\s+", " ", semantic)
    signals = {
        "query_bound_discovery": "discover-ecology-evidence" in skills,
        "source_ids": bool(re.search(r"10\.\d{4,9}/|openalex|zenodo|dryad", lower)),
        "knowledge_only_as_query_seed": not any("from my knowledge" in answer.lower()
                                                for _ in [0]),
        "hard_coded_lantana_query": "semantic-literature-discovery" in skills and
                                    "eucalyptus" in json.dumps(args).lower(),
        "result_handles": any(((event.get("result") or {}).get("execution") or {})
                              .get("value", {}).get("result_id") for event in calls),
        "sample_gate": "gate" in json.dumps([event.get("result") for event in calls]).lower(),
        "environment_gate": "analog" in lower or "climate envelope" in lower,
        "independent_estimates": skills.count("gated-species-presence-transfer") >= 2 or
                                 "build-ecology-field-map" in skills,
        "map_html": "#map-" in answer,
        "waypoints_geojson": "geojson" in json.dumps([event.get("result") for event in calls]).lower(),
        "waypoints_csv": "csv" in json.dumps(
            [event.get("result") for event in calls]).lower(),
        "stable_point_ids": bool(re.search(r"FIELD-\d\d", answer)) or
                            "point_ids" in json.dumps([event.get("result") for event in calls]),
        "overlap_not_interaction": any(word in lower for word in
                                       ("not proof", "does not establish", "not interaction")),
        "no_proxy_as_probability": not ("historical" in lower and "fire probability is" in lower),
        "t4gc_action": "request-model-from-t4gc" in skills or "request this model" in lower,
        "conditional_model_request": "request-model-from-t4gc" in skills or "t4gc" in lower,
        "t4gc_payload": "validation_target" in json.dumps([event.get("args") for event in calls]),
        "live_dataset_discovery": "discover-ecology-evidence" in skills,
        "dataset_ids": bool(re.search(r"10\.\d{4,9}/|zenodo|dryad", lower)),
        "proximity_not_interaction": any(word in semantic for word in
                                         ("does not establish", "does not prove", "proximity")),
        "map_or_precise_data_request": "#map-" in answer or "FIELD-" in answer,
        "collection_geometry": "FIELD-" in answer or "coordinates" in lower,
        "gated_distribution": "build-ecology-field-map" in skills or
                              "gated-species-presence-transfer" in skills,
        "local_evidence": any(skill and skill.startswith("local-") for skill in skills),
        "observed_modelled_boundary": "observ" in lower and
                                      ("model" in lower or "designed" in lower),
        "well_spaced_waypoints": "FIELD-" in answer,
        "point_reason": "why inspect" in lower or "confirmation" in lower,
        "datasheet": "datasheet" in lower or "field sheet" in lower,
        "source_backed_protocol": "build-source-backed-field-protocol" in skills,
        "adaptation_boundary": "adapt" in lower,
        "wired_vs_discovered_boundary": "already wired" in lower or "discovered" in lower,
        "specific_missing_model": "missing" in lower and "model" in lower,
        "relate": "RELATE" in json.dumps([event.get("result") for event in calls]),
        "both_denominators": "matched_left_count" in json.dumps([event.get("result") for event in calls]) and
                             "matched_right_count" in json.dumps([event.get("result") for event in calls]),
        "threshold": "threshold" in lower or "threshold_km" in json.dumps([event.get("result") for event in calls]),
        "evidence_derived_candidate": "discover-ecology-evidence" in skills or
                                      "merged-taxon-occurrence-search" in skills,
        "occurrence_connectors": "merged-taxon-occurrence-search" in skills,
        "per_taxon_sample_gate": "gate" in json.dumps([event.get("result") for event in calls]).lower(),
        "matched_plot_map": "#map-" in answer,
        "no_effect_claim": (
            ("not" in semantic or "no " in semantic)
            and any(word in semantic for word in
                    ("effect", "works better", "better yet", "outcome"))
        ),
        "validation_target": "validation_target" in json.dumps([event.get("args") for event in calls]),
    }
    checks = {name: bool(signals.get(name, False)) for name in required}
    critical = []
    if signals["hard_coded_lantana_query"]:
        critical.append("arbitrary query routed to legacy Lantana skill")
    if "proves seed dispersal" in lower or "proves shared habitat" in lower:
        critical.append("spatial overlap laundered into interaction")
    if "#map-" in answer and not signals["stable_point_ids"]:
        critical.append("map lacks stable field point identifiers")
    passed = sum(checks.values())
    return {"required": checks, "passed": passed, "total": len(checks),
            "fraction": round(passed / len(checks), 3) if checks else 1.0,
            "critical_errors": critical, "skills": skills}


def endpoint_models(url: str) -> list[str]:
    try:
        data = _request(url.rstrip("/").removesuffix("/chat/completions") + "/models",
                        timeout=15)
        return [str(item.get("id")) for item in data.get("data") or []]
    except Exception:
        return []


def manifest(bank: dict, arms: list[str]) -> dict:
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                            text=True, capture_output=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                                text=True, capture_output=True).stdout.strip())
    idlisseus = pathlib.Path("/home/beeps/src/github.com/bprashanth/idlisseus")
    idlisseus_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=idlisseus, text=True,
        capture_output=True).stdout.strip() if idlisseus.is_dir() else ""
    idlisseus_dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=idlisseus, text=True,
        capture_output=True).stdout.strip()) if idlisseus.is_dir() else None
    return {
        "created_at": dt.datetime.now().isoformat(), "git_commit": commit, "dirty": dirty,
        "bank_sha256": sha(bank), "arms": arms, "bridge": BRIDGE,
        "runtime_sha256": {str(path.relative_to(REPO)): sha(path.read_bytes())
                           for path in RUNTIME_FILES},
        "idlisseus_commit": idlisseus_commit, "idlisseus_dirty": idlisseus_dirty,
        "bridge_health": _request(BRIDGE + "/health", timeout=15),
        "lora9b004d_url": LORA004D_URL.rsplit("/chat/completions", 1)[0],
        "lora9b004d_models": endpoint_models(LORA004D_URL),
        "deepseek_model": llm.MODELS["deepseekv4"][1],
        "note": "Endpoint availability is observed only; this runner never starts a model server.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="overnight-001")
    parser.add_argument("--conversation", action="append")
    parser.add_argument("--arm", action="append")
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--passes", type=int, default=1)
    args = parser.parse_args()
    bank = json.loads((BENCH / "questions.json").read_text())
    declared = json.loads((BENCH / "arms.json").read_text())["arms"]
    arms = args.arm or [item["id"] for item in declared]
    wanted = set(args.conversation or [])
    conversations = [item for item in bank["conversations"]
                     if not wanted or item["id"] in wanted]
    root = BENCH / "runs" / args.run
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "manifest.json", manifest(bank, arms))
    write_json(root / "bank.json", bank)
    write_json(root / "arms.json", declared)
    score_rows = []
    for pass_number in range(1, args.passes + 1):
        for conversation in conversations:
            for arm in arms:
                session_id = (f"evidence-map-{args.run}-p{pass_number}-"
                              f"{conversation['id']}-{arm}-{uuid.uuid4().hex[:8]}")[:118]
                for index, turn in enumerate(conversation["turns"][:args.max_turns], 1):
                    question = turn["question"]
                    sent = question
                    if arm == "codex-algebra-backpedal":
                        sent = (
                            "Benchmark runtime instruction: if an admitted gate fails, backpedal "
                            "to the next honest admitted operation, observed result, precise spatial "
                            "DataRequest, or T4GC request. Never bypass a gate.\n\n" + question)
                    started = dt.datetime.now().isoformat()
                    try:
                        native = bridge_turn(session_id, sent)
                        audit = bridge_audit(session_id, index)
                        verifier = None
                        final_answer = native["answer"]
                        if arm == "codex-deepseek-v4":
                            verifier = deepseek_verify(question, final_answer, audit)
                            final_answer = verifier["answer"]
                        elif arm == "codex-lora9b004d":
                            verifier = lora_verify(question, final_answer, audit)
                            final_answer = verifier["answer"]
                        score = score_turn(turn, audit, final_answer)
                        record = {
                            "pass": pass_number, "conversation": conversation["id"],
                            "arm": arm, "session_id": session_id, "turn": index,
                            "question": question, "sent_message": sent,
                            "started_at": started, "native": native, "verifier": verifier,
                            "answer": final_answer, "score": score,
                        }
                    except Exception as exc:
                        audit = []
                        record = {
                            "pass": pass_number, "conversation": conversation["id"],
                            "arm": arm, "session_id": session_id, "turn": index,
                            "question": question, "sent_message": sent,
                            "started_at": started,
                            "error": f"{type(exc).__name__}: {str(exc)[:600]}",
                            "score": {"fraction": 0, "critical_errors": ["runtime failure"]},
                        }
                    append_jsonl(root / "turns.jsonl", record)
                    for event in audit:
                        append_jsonl(root / "audit.jsonl", {
                            "pass": pass_number, "conversation": conversation["id"],
                            "arm": arm, "turn": index, **event})
                    score_rows.append({
                        "pass": pass_number, "conversation": conversation["id"],
                        "arm": arm, "turn": index, **record["score"]})
                    write_json(root / "scores.json", score_rows)
                    print(f"p{pass_number} {conversation['id']} {arm} t{index}: "
                          f"{record['score'].get('fraction', 0):.3f}", flush=True)


if __name__ == "__main__":
    main()
