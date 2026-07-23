#!/usr/bin/env python3
"""Run the site-ecology dialogue bank through the live structured bridge."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import subprocess
import time
import urllib.request
import uuid
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parent
MEMORY = BENCH.parents[2]
REPO = MEMORY.parent
BRIDGE = os.environ.get("IDLI_INSIGHT_URL", "http://127.0.0.1:7011").rstrip("/")
TOKEN_PATH = pathlib.Path(os.environ.get(
    "IDLI_INSIGHT_TOKEN_FILE",
    str(MEMORY / "integration/codex_native/runs/service/.api-token"),
))


def stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                      separators=(",", ":"))


def digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else stable_json(value).encode()
    return hashlib.sha256(raw).hexdigest()


def write_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")


def append_jsonl(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, default=str) + "\n")


def request_json(url: str, token: str | None = None) -> dict:
    headers = {"Authorization": "Bearer " + token} if token else {}
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.load(response)


def bridge_turn(session_id: str, question: str, faults: list[str] | None = None) -> dict:
    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    payload = {
        "model": "idli-insight",
        "stream": True,
        "session_id": session_id,
        "message": question,
        "idlisseus_context": {
            "session_id": session_id,
            "owner": "benchmark",
            "benchmark_faults": faults or [],
        },
    }
    request = urllib.request.Request(
        BRIDGE + "/v1/audit/chat",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    started = time.monotonic()
    events = []
    milestones = {}
    with urllib.request.urlopen(request, timeout=1200) as response:
        for raw in response:
            line = raw.decode(errors="replace").strip()
            if not line.startswith("data: "):
                continue
            text = line[6:]
            if text == "[DONE]":
                break
            try:
                event = json.loads(text)
            except json.JSONDecodeError:
                continue
            elapsed = round(time.monotonic() - started, 3)
            events.append({"elapsed_s": elapsed, **event})
            event_type = event.get("type")
            if event_type in {"turn_start", "insight_progress"}:
                milestones.setdefault("first_progress_s", elapsed)
            if event_type == "tool_output" and event.get("kind") == "skill":
                milestones.setdefault("first_skill_result_s", elapsed)
            if event_type == "insight_evidence":
                milestones.setdefault("evidence_badges_s", elapsed)
            if event_type == "final":
                milestones["answer_s"] = elapsed
    final = next((event for event in reversed(events) if event.get("type") == "final"), {})
    return {
        "answer": str(final.get("answer") or ""),
        "events": events,
        "milestones": milestones,
        "latency_s": round(time.monotonic() - started, 3),
        "turn": final.get("turn"),
    }


def audit_for(session_id: str, turn: int | None = None) -> list[dict]:
    token = TOKEN_PATH.read_text(encoding="utf-8").strip()
    suffix = f"/{turn}" if turn is not None else ""
    return request_json(f"{BRIDGE}/v1/audit/{session_id}{suffix}", token).get("events") or []


def skill_calls(audit: list[dict]) -> list[dict]:
    return [event for event in audit if event.get("type") == "skill_call"]


def _execution(call: dict) -> dict:
    result = call.get("result") if isinstance(call.get("result"), dict) else {}
    return result.get("execution") if isinstance(result.get("execution"), dict) else {}


def _value(call: dict) -> dict:
    execution = _execution(call)
    return execution.get("value") if isinstance(execution.get("value"), dict) else {}


def _badge_kinds(audit: list[dict]) -> set[str]:
    event = next((item for item in reversed(audit)
                  if item.get("type") == "insight_evidence"), {})
    return {
        str(item.get("kind")) for item in event.get("items") or [] if isinstance(item, dict)
    }


def _has_map(calls: list[dict], answer: str) -> bool:
    return "build-ecology-field-map" in [call.get("skill") for call in calls] and (
        "#map-" in answer or any((_value(call).get("artifact") or {}).get("url")
                                for call in calls))


def _result_blob(calls: list[dict]) -> str:
    return stable_json([call.get("result") for call in calls]).casefold()


def score_turn(turn: dict, audit: list[dict], answer: str, live: dict) -> dict:
    required = turn.get("requires") or []
    calls = skill_calls(audit)
    skills = [str(call.get("skill") or "") for call in calls]
    blob = _result_blob(calls)
    lower = re.sub(r"\s+", " ", re.sub(r"[`*_~]", "", answer.casefold()))
    badges = _badge_kinds(audit)
    map_calls = [call for call in calls if call.get("skill") == "build-ecology-field-map"]
    map_values = [_value(call) for call in map_calls]
    map_labels = {str(value.get("label") or "") for value in map_values}
    result_ids = [str(_value(call).get("result_id") or "") for call in calls]
    has_map = _has_map(calls, answer)
    has_dashboard = "publish-evidence-dashboard" in skills and (
        "#dashboard-" in answer or "dashboard" in blob)
    has_report = any(event.get("type") == "report_published" for event in audit)
    order = {skill: min(index for index, name in enumerate(skills) if name == skill)
             for skill in set(skills)}
    evidence_before_9b = (
        "compile-scientific-algebra-9b" not in order
        or any(order.get(skill, 10**6) < order["compile-scientific-algebra-9b"]
               for skill in (
                   "merged-taxon-occurrence-search", "discover-ecology-evidence",
                   "local-site-evidence-search"))
    )
    signals = {
        "site_inventory": "site-overview" in skills,
        "site_name_taxon_search": (
            "merged-taxon-occurrence-search" in skills and
            any("elephants by the lake" in stable_json(call.get("args") or {}).casefold()
                for call in calls)),
        "local_evidence": any(name.startswith("local-") for name in skills)
                          or "site-overview" in skills,
        "local_first": bool(skills) and (
            skills[0].startswith("local-") or skills[0] == "site-overview"),
        "local_badge": "local_asset" in badges,
        "proxy_badge": "proxy" in badges,
        "designed_badge": "designed" in badges,
        "data_gap_badge": "data_gap" in badges,
        "evidence_badges": bool(badges),
        "result_handle": any(result_ids),
        "audit_lineage": bool(result_ids) and any(
            token in lower for token in ("audit", "result", "#map-", "#dashboard-", "report")),
        "one_follow_up": "?" in answer and len(answer.split()) <= 260,
        "guided_choice": any(event.get("type") == "insight_actions" for event in audit),
        "concise": len(answer.split()) <= 220,
        "clarify_entity": "?" in answer and not any(
            node in blob for node in ('"op":"estimate"', '"op": "estimate"')),
        "no_bulk_ungated_model": skills.count("compile-scientific-algebra-9b") <= 1,
        "entity_resolution": "resolution" in blob or "scientific_name" in blob,
        "no_local_absence_claim": not any(
            phrase in lower for phrase in ("is not at the site", "does not occur at the site",
                                           "is absent from the site")),
        "offer_wider_search": "wider" in lower or any(
            (event.get("operation") == "search_wider_occurrences")
            for event in audit if isinstance(event, dict)),
        "occurrence_connector": "merged-taxon-occurrence-search" in skills,
        "taxon_resolution": "resolution" in blob or "canonical" in blob,
        "source_identifiers": bool(re.search(
            r"10\.\d{4,9}/|gbif|inaturalist|openalex|zenodo|dryad", answer, re.I)) or
            "source_connector" in blob,
        "raw_map_choice": any(
            option.get("operation") == "show_observed_map"
            for event in audit if event.get("type") == "insight_actions"
            for option in event.get("options") or []),
        "evidence_before_9b": evidence_before_9b,
        "algebra9b": "compile-scientific-algebra-9b" in skills,
        "gate": "gate" in blob,
        "map": has_map,
        "map_or_designed_fallback": has_map,
        "map_label": bool(map_labels & {"observed", "modelled", "designed"}),
        "stable_point_ids": "point_ids" in blob and bool(
            re.search(r"(?:FIELD|OBS)-\d+", blob, re.I)),
        "datasheet": "csv" in blob or "datasheet" in lower or "field sheet" in lower,
        "point_specific_request": bool(re.search(r"(?:FIELD|OBS)-\d+", blob)),
        "query_bound_discovery": any(
            skill in skills for skill in (
                "discover-ecology-evidence", "discover-biotic-interactions")),
        "inspect_before_protocol": (
            "build-source-backed-field-protocol" not in order or (
                "inspect-evidence-dataset" in order and
                order["inspect-evidence-dataset"] <
                order["build-source-backed-field-protocol"])),
        "source_backed_protocol": "build-source-backed-field-protocol" in skills,
        "adaptation_boundary": "adapt" in lower or "programme-added" in blob,
        "dashboard": has_dashboard,
        "report": has_report,
        "visual_link": "#map-" in answer or "#dashboard-" in answer or "/report/" in answer,
        "no_phantom_outcomes": not re.search(
            r"\b(?:survival|growth|effect)\s+(?:was|is|increased|decreased)\b", lower),
        "knowledge_boundary": (
            "general ecological context" in lower or "model_background" in badges
            or "from the onboarded" in lower),
        "reported_not_present": "reported" in lower or "local_asset" in badges,
        "reported_not_trend": not re.search(r"\b(?:increased|decreased|improved|declined)\b", lower),
        "comparable_time_gate": (
            "compare" in blob or "time" in blob or "comparable" in lower or "need" in lower),
        "no_phantom_trend": not re.search(
            r"\b(?:trend|condition)\s+(?:shows?|is)\s+(?:up|down|improving|declining)\b", lower),
        "specific_data_request": "data_gap" in badges or "need" in lower or "missing" in lower,
        "no_effect_claim": not re.search(
            r"\b(?:anr|restoration|clearing|planting)\s+(?:worked|caused|improved)\b", lower),
        "local_or_wired_measurement": any(
            skill in skills for skill in ("historical-fire-exposure", "site-overview")),
        "site_geometry_boundary": "boundary" in lower or "centre point" in lower or "bbox" in lower,
        "no_proxy_as_probability": not re.search(
            r"(?:historical|active.fire).{0,80}(?:chance|probability)\s+(?:is|of)", lower),
        "specific_missing_model": "model" in lower and ("missing" in lower or "cannot" in lower),
        "live_dataset_discovery": "discover-ecology-evidence" in skills,
        "wired_vs_discovered": "wired" in lower and "discover" in lower,
        "t4gc_request": "request-model-from-t4gc" in skills,
        "estimand_clarification": "?" in answer or "outcome" in lower or "measure" in lower,
        "explicit_estimand": "12 month" in lower or "survival" in lower,
        "gate_or_fallback": "gate" in blob or "designed" in map_labels,
        "knowledge_as_query_seed": any(
            skill in skills for skill in (
                "discover-ecology-evidence", "discover-biotic-interactions")),
        "no_unsupported_interaction": not any(
            phrase in lower for phrase in ("birds spread eucalyptus at", "proves dispersal")),
        "candidate_lineage": (
            any(skill in skills for skill in (
                "discover-ecology-evidence", "discover-biotic-interactions"))
            and "merged-taxon-occurrence-search" in skills),
        "independent_estimates": "build-ecology-field-map" in skills or
                                 skills.count("compile-scientific-algebra-9b") >= 2,
        "overlap_not_interaction": any(
            phrase in lower for phrase in
            ("not proof", "does not establish", "does not prove", "not interaction")),
        "protocol_or_specific_request": (
            "build-source-backed-field-protocol" in skills or
            any(token in lower for token in ("observe", "record", "collect", "survey"))),
        "non_detection_not_absence": any(
            phrase in lower for phrase in ("not evidence of absence", "does not mean", "non-detection")),
        "effort_boundary": "effort" in lower or "survey" in lower,
        "repeat_visits": "repeat" in lower or "visit" in lower,
        "no_occupancy_from_density": not re.search(
            r"occurrence (?:density|records?).{0,30}(?:occupancy|occupied)", lower),
        "proxy_boundary": "proxy" in badges or "proxy" in lower,
        "intervention_date_request": "date" in lower or "when" in lower,
        "no_phantom_causality": not re.search(
            r"\brestoration\s+(?:caused|made|improved)\b", lower),
        "source_failure_visible": "data_gap" in badges or "unavailable" in lower or "failed" in lower,
        "estimand_invariance": not any(
            phrase in lower for phrase in ("instead i measured", "as a substitute")),
        "no_source_lottery": not any(
            phrase in lower for phrase in ("another source proves", "using a different measure")),
        "cache_lineage": "cache" in blob or "retriev" in blob or "designed" in map_labels,
    }
    checks = {name: bool(signals.get(name, False)) for name in required}
    forbidden = {
        name: bool(signals.get(name, False)) for name in turn.get("forbids") or []
    }
    critical = []
    if not evidence_before_9b and "compile-scientific-algebra-9b" in skills:
        critical.append("Algebra 9B ran before evidence admission")
    if "modelled" in badges:
        estimates = [
            call for call in calls if call.get("skill") == "compile-scientific-algebra-9b"
            and '"op":"estimate"' in stable_json(call.get("result") or {}).casefold()
            and ((_value(call).get("execution") or {}).get("status") == "answer")
        ]
        modelled_maps = [value for value in map_values if value.get("label") == "modelled"]
        if not estimates and not modelled_maps:
            critical.append("Modelled badge has no answered ESTIMATE")
    if "modelled" in map_labels and "gate" not in blob:
        critical.append("modelled map has no recorded gate")
    if any(forbidden.values()):
        critical.extend(f"forbidden behaviour: {name}" for name, value in forbidden.items() if value)
    passed = sum(checks.values())
    return {
        "required": checks,
        "forbidden": forbidden,
        "passed": passed,
        "total": len(checks),
        "fraction": round(passed / len(checks), 3) if checks else 1.0,
        "critical_errors": critical,
        "skills": skills,
        "badges": sorted(badges),
        "milestones": live.get("milestones") or {},
    }


def manifest(bank: dict, arms: dict) -> dict:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO,
        text=True, capture_output=True).stdout.strip()
    dirty = bool(subprocess.run(
        ["git", "status", "--porcelain"], cwd=REPO,
        text=True, capture_output=True).stdout.strip())
    return {
        "created_at": dt.datetime.now().isoformat(),
        "git_commit": commit,
        "dirty": dirty,
        "bank_sha256": digest(bank),
        "arms": arms,
        "bridge": BRIDGE,
        "bridge_health": request_json(BRIDGE + "/health"),
        "note": "Runner observes the existing service; it never starts or restarts a model.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", default="smoke-001")
    parser.add_argument("--conversation", action="append")
    parser.add_argument("--max-turns", type=int)
    parser.add_argument("--passes", type=int, default=1)
    args = parser.parse_args()
    bank = json.loads((BENCH / "questions.json").read_text(encoding="utf-8"))
    arms = json.loads((BENCH / "arms.json").read_text(encoding="utf-8"))
    wanted = set(args.conversation or [])
    conversations = [
        item for item in bank["conversations"] if not wanted or item["id"] in wanted
    ]
    root = BENCH / "runs" / args.run
    root.mkdir(parents=True, exist_ok=True)
    write_json(root / "manifest.json", manifest(bank, arms))
    write_json(root / "bank.json", bank)
    score_rows = []
    for pass_number in range(1, args.passes + 1):
        for conversation in conversations:
            session_id = (
                f"site-dialogue-{args.run}-p{pass_number}-{conversation['id']}-"
                f"{uuid.uuid4().hex[:8]}"
            )[:118]
            for index, turn in enumerate(
                    conversation["turns"][:args.max_turns], 1):
                faults = (
                    conversation.get("faults") if index >= 2
                    and conversation.get("faults") else [])
                started_at = dt.datetime.now().isoformat()
                try:
                    live = bridge_turn(session_id, turn["question"], faults)
                    audit = audit_for(session_id, index)
                    history_audit = audit_for(session_id)
                    score = score_turn(turn, history_audit, live["answer"], live)
                    record = {
                        "pass": pass_number,
                        "conversation": conversation["id"],
                        "arm": "codex-outer-algebra9b",
                        "session_id": session_id,
                        "turn": index,
                        "question": turn["question"],
                        "started_at": started_at,
                        "answer": live["answer"],
                        "latency_s": live["latency_s"],
                        "milestones": live["milestones"],
                        "score": score,
                    }
                except Exception as exc:
                    audit = []
                    record = {
                        "pass": pass_number,
                        "conversation": conversation["id"],
                        "arm": "codex-outer-algebra9b",
                        "session_id": session_id,
                        "turn": index,
                        "question": turn["question"],
                        "started_at": started_at,
                        "error": f"{type(exc).__name__}: {str(exc)[:800]}",
                        "score": {
                            "fraction": 0,
                            "critical_errors": ["runtime failure"],
                        },
                    }
                append_jsonl(root / "turns.jsonl", record)
                for event in audit:
                    append_jsonl(root / "audit.jsonl", {
                        "pass": pass_number,
                        "conversation": conversation["id"],
                        "arm": "codex-outer-algebra9b",
                        "benchmark_turn": index,
                        **event,
                    })
                score_rows.append({
                    "pass": pass_number,
                    "conversation": conversation["id"],
                    "turn": index,
                    **record["score"],
                })
                write_json(root / "scores.json", score_rows)
                print(
                    f"p{pass_number} {conversation['id']} t{index}: "
                    f"{record['score'].get('fraction', 0):.3f}",
                    flush=True,
                )


if __name__ == "__main__":
    main()
