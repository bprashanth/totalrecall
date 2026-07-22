#!/usr/bin/env python3
"""Run the frozen five-arm late-binding first-contact benchmark."""

from __future__ import annotations

import argparse
import contextlib
import copy
import datetime as dt
import hashlib
import http.server
import json
import os
import pathlib
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from typing import Any


HERE = pathlib.Path(__file__).resolve().parent
BENCH = HERE.parent
MEMORY = BENCH.parents[2]
HARNESS = MEMORY / "harness"
HERMES_BENCH = MEMORY / "hermes_bench"
sys.path[:0] = [str(HARNESS), str(HERMES_BENCH), str(HERE)]

import connectors as C  # noqa: E402
import engine as E  # noqa: E402
import executor as X  # noqa: E402
import ir_schema as IR  # noqa: E402
import parser as P  # noqa: E402
from semantic import SemanticIndex, card_text  # noqa: E402


CODEX = pathlib.Path("/home/beeps/.local/bin/codex")
IMAGE = "hermes-agent-local"
MODEL = "gpt-5.4"
REASONING = "medium"
LORA_URL = "http://172.17.0.1:8004/v1/chat/completions"
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


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


def extract_object(text: str) -> dict | None:
    obj = P.extract_json(text or "")
    return obj if isinstance(obj, dict) else None


def general_compiler_prompt(question: str, history_note: str = "") -> str:
    examples = P.load_fewshot()
    rendered = "\n\n".join(
        f"USER: {item['q']}\nASSISTANT: {json.dumps(item['ir'], ensure_ascii=False)}"
        for item in examples
    )
    return (
        "COMPILER CONTRACT\n" + P.SYSTEM +
        "\nThe current runtime also accepts BUFFER as documented in the ecology v2.2.1 profile: "
        '{"op":"BUFFER","source":<REGION>,"radius_km":<positive number>}. BUFFER controls '
        "the retrieval extent; RELATE.threshold_km controls distance among returned records. "
        "If the current message only asks what a previous audited result means or what data is "
        "missing, return JSON {\"mode\":\"history\",\"ir\":null}. Otherwise return "
        "{\"mode\":\"execute\",\"ir\":<one algebra tree>}. Do not answer the question.\n\n"
        + ("AUDITED CONVERSATION NOTE:\n" + history_note + "\n\n" if history_note else "")
        + "EXAMPLES:\n" + rendered + "\n\nCURRENT USER MESSAGE:\n" + question
    )


def capability_selector_prompt(question: str, catalog: list[dict]) -> str:
    compact = [{key: item.get(key) for key in
                ("entity", "kind", "description", "grain", "evidence", "binding", "ops",
                 "requires", "includes", "excludes", "scope", "place")
                if item.get(key) is not None} for item in catalog]
    return (
        "Select current executable capability cards for this user message. Capabilities describe "
        "measurements, not facts. Return only JSON "
        '{"mode":"execute"|"clarify"|"history","entities":[exact catalog names]}. '
        "Use history only when the message asks to interpret or qualify evidence already returned "
        "in this conversation. For execute, choose the smallest sufficient set of at most four. "
        "Relations and estimates need their operator ingredient and data leaves. If a required "
        "measurement is unavailable, return an empty list.\n\nCATALOG:\n" +
        json.dumps(compact, ensure_ascii=False) + "\n\nUSER MESSAGE:\n" + question
    )


def capability_compiler_prompt(question: str, selected: list[dict]) -> str:
    messages = P.build_messages(
        question,
        fewshot=E.GENERIC_FEWSHOT + E._selected_examples(selected),
        capabilities=selected,
    )
    return (
        "Compile the current message using the exact selected capability contracts below. "
        "Return only one JSON algebra tree, never an answer.\n\n" +
        "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
    )


def response_prompt(question: str, execution: dict, ir: dict | None,
                    architecture: str) -> str:
    pack = E.response_pack({"execution": execution, "ir": ir, "schema": IR.validate(ir)
                            if isinstance(ir, dict) else {"valid": True}})
    return (
        "Answer the current NGO staff question in short, simple English using only the audited "
        "result below and earlier audited results in this conversation. Lead with the useful "
        "answer. Keep local, regional, observed, reported, proxy and modelled evidence separate. "
        "Do not turn record proximity into same-time presence, an estimate into an observation, "
        "or change into causality. If data is missing, say exactly what is missing and what the "
        "field team can collect. Do not mention the benchmark architecture.\n\nQUESTION:\n" +
        question + "\n\nAUDITED RESULT:\n" + json.dumps(pack, ensure_ascii=False, default=str)
    )


def bind_context(ir: dict | None) -> dict | None:
    return IR.canonicalize(E._bind_context(copy.deepcopy(ir), "ebtl")) if ir else None


def execute_ir(ir: dict | None) -> tuple[dict, dict]:
    if not isinstance(ir, dict):
        schema = {"valid": False, "errors": ["no IR"], "holes": [], "ops": []}
        return schema, {"status": "data_request", "reason": "no_ir", "detail": {}}
    schema = IR.validate(ir)
    if not schema["valid"]:
        return schema, {"status": "data_request", "reason": "invalid_ir",
                        "detail": {"errors": schema["errors"]}, "provenance": []}
    return schema, X.execute(ir)


class CodexSession:
    def __init__(self, root: pathlib.Path, arm: str, conversation: str,
                 input_files: dict[str, str] | None = None, native: bool = False,
                 web: bool = False):
        self.root = root / "isolation" / conversation / arm
        # Keep credentials and resumable Codex state outside the repository.  The benchmark
        # directory contains only prompts, events and results that are safe to inspect/commit.
        private_key = sha(f"{root.resolve()}:{conversation}:{arm}")[:20]
        self.private_home = pathlib.Path("/tmp/late-bound-skills") / private_key
        self.arm = arm
        self.conversation = conversation
        self.native = native
        self.web = web
        self.session_id: str | None = None
        for name in ("work", "input", "output"):
            (self.root / name).mkdir(parents=True, exist_ok=True)
        self.private_home.mkdir(parents=True, exist_ok=True)
        shutil.copy2(os.path.expanduser("~/.codex/auth.json"), self.private_home / "auth.json")
        os.chmod(self.private_home / "auth.json", 0o600)
        for name, content in (input_files or {}).items():
            path = self.root / "input" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)

    def call(self, prompt: str, stage: str, schema: dict | None = None) -> dict:
        number = len(list((self.root / "output").glob("*-request.json"))) + 1
        stem = f"{number:03d}-{stage}"
        out = self.root / "output"
        request = {
            "arm": self.arm, "conversation": self.conversation, "stage": stage,
            "model": MODEL, "reasoning": REASONING, "prompt_sha256": sha(prompt),
            "prompt": prompt,
        }
        write_json(out / f"{stem}-request.json", request)
        schema_container = None
        if schema is not None:
            schema_path = self.root / "input" / f"{stem}-schema.json"
            write_json(schema_path, schema)
            schema_container = f"/bench/arm/input/{stem}-schema.json"
        final_container = f"/bench/arm/output/{stem}-final.txt"
        base = [
            "docker", "run", "--rm", "-i", "--network", "host", "--entrypoint", "/bench/codex",
            "-u", f"{os.getuid()}:{os.getgid()}",
            "-e", "HOME=/bench/home", "-e", "CODEX_HOME=/bench/home",
            "-v", f"{CODEX}:/bench/codex:ro", "-v", f"{self.root}:/bench/arm",
            "-v", f"{self.private_home}:/bench/home",
            "-w", "/bench/arm/work", IMAGE,
        ]
        if self.web:
            base.append("--search")
        base.append("exec")
        if self.session_id:
            args = ["resume", self.session_id, "--json", "-m", MODEL,
                    "-c", f'model_reasoning_effort="{REASONING}"',
                    "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
                    "-o", final_container]
        else:
            args = ["--json", "-m", MODEL, "-c", f'model_reasoning_effort="{REASONING}"',
                    "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
                    "-o", final_container]
            if self.native:
                args.append("--dangerously-bypass-approvals-and-sandbox")
            else:
                args.extend(["-s", "read-only"])
        if schema_container:
            args.extend(["--output-schema", schema_container])
        args.append("-")
        started = time.time()
        completed = subprocess.run(base + args, input=prompt, text=True, capture_output=True,
                                   timeout=900)
        elapsed = round(time.time() - started, 3)
        events_path = out / f"{stem}-events.jsonl"
        events_path.write_text(ANSI.sub("", completed.stdout).replace("\r", ""))
        (out / f"{stem}-stderr.txt").write_text(completed.stderr)
        events = []
        for line in completed.stdout.splitlines():
            with contextlib.suppress(json.JSONDecodeError):
                events.append(json.loads(line))
        if not self.session_id:
            thread = next((event.get("thread_id") for event in events
                           if event.get("type") == "thread.started"), None)
            self.session_id = thread
        final_path = self.root / "output" / f"{stem}-final.txt"
        final = final_path.read_text() if final_path.exists() else ""
        result = {
            "stage": stage, "exit_code": completed.returncode, "latency_s": elapsed,
            "session_id": self.session_id, "prompt_sha256": request["prompt_sha256"],
            "final": final.strip(), "parsed": extract_object(final),
            "usage": next((event.get("usage") for event in reversed(events)
                           if event.get("type") == "turn.completed"), None),
        }
        write_json(out / f"{stem}-result.json", result)
        if completed.returncode != 0:
            raise RuntimeError(f"Codex {self.arm}/{stage} failed: {completed.stderr[-500:]}")
        return result

    def close(self) -> None:
        shutil.rmtree(self.private_home, ignore_errors=True)


def lora_call(messages: list[dict], prompt: str, stage: str,
              logdir: pathlib.Path, max_tokens: int = 2400) -> dict:
    messages.append({"role": "user", "content": prompt})
    payload = {"model": "lora9b", "messages": messages, "temperature": 0,
               "max_tokens": max_tokens}
    request_path = logdir / f"{len(list(logdir.glob('*-request.json'))) + 1:03d}-{stage}-request.json"
    write_json(request_path, {"endpoint": LORA_URL, "payload": payload,
                              "prompt_sha256": sha(prompt)})
    started = time.time()
    req = urllib.request.Request(LORA_URL, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as response:
            raw = json.loads(response.read())
        text = raw["choices"][0]["message"].get("content") or ""
        code, error = 0, None
    except Exception as exc:
        raw, text, code, error = {}, "", 1, f"{type(exc).__name__}: {exc}"
    elapsed = round(time.time() - started, 3)
    messages.append({"role": "assistant", "content": text})
    result = {"stage": stage, "exit_code": code, "latency_s": elapsed,
              "final": text, "parsed": extract_object(text), "raw": raw, "error": error}
    write_json(logdir / request_path.name.replace("-request", "-result"), result)
    return result


def capability_turn(question: str, session: CodexSession) -> dict:
    catalog = C.capability_catalog()
    selected_call = session.call(capability_selector_prompt(question, catalog), "select")
    choice = selected_call.get("parsed") or {}
    mode = choice.get("mode", "execute")
    by_name = {item["entity"]: item for item in catalog}
    selected = [{**by_name[name], "selected": True} for name in choice.get("entities", [])
                if name in by_name][:4]
    # Dependencies and containment are catalog contracts, not model judgment.  Apply the same
    # deterministic completion used by the frozen capability-first harness.
    required = {name for item in selected for name in item.get("requires", [])}
    present = {item["entity"] for item in selected}
    selected.extend({**by_name[name], "selected": True}
                    for name in sorted(required - present) if name in by_name)
    covered = {name for item in selected for name in item.get("includes", [])}
    selected = [item for item in selected if item["entity"] not in covered]
    if mode != "execute":
        execution = {"status": "data_request" if mode == "clarify" else "history",
                     "reason": "ambiguous_request" if mode == "clarify" else "history",
                     "detail": {"candidate_capabilities": [x["entity"] for x in selected]}}
        ir, schema, compile_call = None, {"valid": True, "errors": []}, None
    else:
        compile_call = session.call(capability_compiler_prompt(question, selected), "compile")
        draft = compile_call.get("parsed")
        if not isinstance(draft, dict):
            draft = None
        if not selected:
            draft = {"op": "SELECT", "entity": "?proxy", "region": "?place", "time": None}
        draft = E._bind_single_capability(draft, selected)
        ir = bind_context(draft)
        schema, execution = execute_ir(ir)
    answer_call = session.call(response_prompt(question, execution, ir, "capability-first"),
                               "answer")
    return {"question": question, "mode": mode, "selected_capabilities": selected,
            "selector": selected_call, "compiler": compile_call, "ir": ir,
            "schema": schema, "execution": execution, "answer": answer_call["final"],
            "answer_call": answer_call}


def walk_link_targets(node: Any, path: str = "root", parent: str | None = None) -> list[dict]:
    if not isinstance(node, dict):
        return []
    op = node.get("op")
    targets = []
    if op in {"SELECT", "ANNOTATE", "ESTIMATE"}:
        subject = node.get("entity") if op == "SELECT" else node.get("layer") or node.get("method")
        targets.append({"path": path, "op": op, "subject": subject, "node": copy.deepcopy(node),
                        "parent_op": parent,
                        "require_georef": parent == "RELATE" or op == "ANNOTATE"})
    for key, value in node.items():
        if isinstance(value, dict) and "op" in value:
            targets.extend(walk_link_targets(value, f"{path}.{key}", op))
        elif isinstance(value, list):
            for index, item in enumerate(value):
                if isinstance(item, dict):
                    targets.extend(walk_link_targets(item, f"{path}.{key}[{index}]", op))
    return targets


def target_query(target: dict) -> str:
    return (
        f"Algebra operation: {target['op']}\nRequested subject or layer: {target['subject']}\n"
        f"Parent operation: {target.get('parent_op')}\nRequired output: "
        f"{'georeferenced ' if target.get('require_georef') else ''}Records or declared operator result\n"
        f"Complete algebra leaf: {json.dumps(target['node'], ensure_ascii=False)}"
    )


def apply_at_path(root: dict, path: str, fn) -> dict:
    parts = re.findall(r"\.([A-Za-z_]+)|\[([0-9]+)\]", path[len("root"):])
    node: Any = root
    for index, (key, array_index) in enumerate(parts):
        token: Any = int(array_index) if array_index else key
        if index == len(parts) - 1:
            node[token] = fn(node[token])
        else:
            node = node[token]
    if not parts:
        root = fn(root)
    return root


def bind_node(node: dict, skill: dict) -> dict:
    out = copy.deepcopy(node)
    binding = skill.get("binding") or {}
    mode = binding.get("mode")
    if mode == "exact_select" and out.get("op") == "SELECT":
        out["entity"] = binding["entity"]
        if binding.get("region_place"):
            out["region"] = {"op": "REGION", "place": binding["region_place"]}
    elif mode == "compiler_entity" and out.get("op") == "SELECT":
        entity = str(out.get("entity") or "")
        for alias, canonical in (skill.get("aliases") or {}).items():
            if alias in entity.lower():
                out["entity"] = canonical
                break
    elif mode == "annotate" and out.get("op") == "ANNOTATE":
        out["layer"] = binding["layer"]
        if isinstance(out.get("source"), dict) and out["source"].get("op") == "SELECT":
            out["source"]["entity"] = binding["source_entity"]
    return out


def linker_prompt(question: str, ir: dict, retrieval: list[dict]) -> str:
    return (
        "The algebra below was frozen before skill discovery. For every listed leaf, choose one "
        "exact candidate skill ID or NONE. A skill must provide the requested measurement, not "
        "merely mention the subject. Respect every exclusion, output shape and evidence boundary. "
        "Do not rewrite the algebra and do not answer the user. Return only JSON "
        '{"bindings":[{"path":"root...","skill":"exact-id-or-NONE"},...]}.\n\n'
        f"QUESTION:\n{question}\n\nFROZEN ALGEBRA:\n{json.dumps(ir, ensure_ascii=False)}\n\n"
        "RETRIEVED CANDIDATES:\n" + json.dumps(retrieval, ensure_ascii=False)
    )


def compile_plan(result: dict) -> tuple[str, dict | None]:
    parsed = result.get("parsed") or {}
    if parsed.get("mode") in {"execute", "history"}:
        return parsed["mode"], parsed.get("ir")
    if parsed.get("op"):
        return "execute", parsed
    return "execute", None


def late_bound_codex_turn(question: str, session: CodexSession,
                          index: SemanticIndex, skills: list[dict]) -> dict:
    compile_call = session.call(general_compiler_prompt(question), "compile")
    mode, draft = compile_plan(compile_call)
    raw_ir = bind_context(draft) if draft else None
    retrieval, link_call, bindings = [], None, []
    if mode == "history":
        ir, schema = None, {"valid": True, "errors": []}
        execution = {"status": "history", "reason": "interpret_prior_audit", "detail": {}}
    elif not raw_ir:
        ir, schema = None, {"valid": False, "errors": ["no IR"]}
        execution = {"status": "data_request", "reason": "no_ir", "detail": {}}
    else:
        for target in walk_link_targets(raw_ir):
            candidates = index.search(target_query(target), target["op"],
                                      target.get("require_georef", False))
            retrieval.append({
                "path": target["path"], "op": target["op"], "query": target_query(target),
                "candidates": [{"id": c.skill["id"], "score": c.score,
                                "card": card_text(c.skill)} for c in candidates],
            })
        link_call = session.call(linker_prompt(question, raw_ir, retrieval), "link")
        requested = (link_call.get("parsed") or {}).get("bindings") or []
        by_id = {skill["id"]: skill for skill in skills}
        allowed = {row["path"]: {c["id"] for c in row["candidates"]} for row in retrieval}
        ir = copy.deepcopy(raw_ir)
        for item in requested:
            path, skill_id = item.get("path"), item.get("skill")
            accepted = bool(path in allowed and skill_id in allowed[path] and skill_id in by_id)
            bindings.append({"path": path, "skill": skill_id, "accepted": accepted})
            if accepted:
                ir = apply_at_path(ir, path, lambda node, s=by_id[skill_id]: bind_node(node, s))
        accepted_paths = {item["path"] for item in bindings if item["accepted"]}
        required_paths = {row["path"] for row in retrieval}
        if required_paths - accepted_paths:
            schema = IR.validate(ir)
            execution = {"status": "data_request", "reason": "skill_unbound",
                         "detail": {"unbound_paths": sorted(required_paths - accepted_paths)},
                         "provenance": []}
        else:
            schema, execution = execute_ir(ir)
    answer_call = session.call(response_prompt(question, execution, ir, "late-bound"), "answer")
    return {"question": question, "mode": mode, "compiler": compile_call,
            "raw_ir": raw_ir, "raw_ir_sha256": sha(raw_ir) if raw_ir else None,
            "retrieval": retrieval, "linker": link_call, "bindings": bindings,
            "ir": ir, "schema": schema, "execution": execution,
            "answer": answer_call["final"], "answer_call": answer_call}


def late_bound_lora_turn(question: str, messages: list[dict], logdir: pathlib.Path,
                         index: SemanticIndex, skills: list[dict]) -> dict:
    compile_call = lora_call(messages, general_compiler_prompt(question), "compile", logdir)
    mode, draft = compile_plan(compile_call)
    raw_ir = bind_context(draft) if draft else None
    retrieval, link_call, bindings = [], None, []
    if mode == "history":
        ir, schema = None, {"valid": True, "errors": []}
        execution = {"status": "history", "reason": "interpret_prior_audit", "detail": {}}
    elif not raw_ir:
        ir, schema = None, {"valid": False, "errors": ["no IR"]}
        execution = {"status": "data_request", "reason": "no_ir", "detail": {}}
    else:
        for target in walk_link_targets(raw_ir):
            candidates = index.search(target_query(target), target["op"],
                                      target.get("require_georef", False))
            retrieval.append({"path": target["path"], "op": target["op"],
                              "query": target_query(target),
                              "candidates": [{"id": c.skill["id"], "score": c.score,
                                              "card": card_text(c.skill)} for c in candidates]})
        link_call = lora_call(messages, linker_prompt(question, raw_ir, retrieval), "link", logdir)
        requested = (link_call.get("parsed") or {}).get("bindings") or []
        by_id = {skill["id"]: skill for skill in skills}
        allowed = {row["path"]: {c["id"] for c in row["candidates"]} for row in retrieval}
        ir = copy.deepcopy(raw_ir)
        for item in requested:
            path, skill_id = item.get("path"), item.get("skill")
            accepted = bool(path in allowed and skill_id in allowed[path] and skill_id in by_id)
            bindings.append({"path": path, "skill": skill_id, "accepted": accepted})
            if accepted:
                ir = apply_at_path(ir, path, lambda node, s=by_id[skill_id]: bind_node(node, s))
        accepted_paths = {item["path"] for item in bindings if item["accepted"]}
        required_paths = {row["path"] for row in retrieval}
        if required_paths - accepted_paths:
            schema = IR.validate(ir)
            execution = {"status": "data_request", "reason": "skill_unbound",
                         "detail": {"unbound_paths": sorted(required_paths - accepted_paths)},
                         "provenance": []}
        else:
            schema, execution = execute_ir(ir)
    answer_call = lora_call(messages, response_prompt(question, execution, ir, "late-bound"),
                            "answer", logdir)
    return {"question": question, "mode": mode, "compiler": compile_call,
            "raw_ir": raw_ir, "raw_ir_sha256": sha(raw_ir) if raw_ir else None,
            "retrieval": retrieval, "linker": link_call, "bindings": bindings,
            "ir": ir, "schema": schema, "execution": execution,
            "answer": answer_call["final"], "answer_call": answer_call}


def skill_ir(skill: dict, args: dict) -> dict:
    binding = skill.get("binding") or {}
    region_value = binding.get("region_place") or args.get("region") or "EBTL"
    region: dict = {"op": "REGION", "place": region_value}
    # Only the generic occurrence skill advertises a widened-region contract. A model cannot
    # accidentally widen a site-locked survey card by copying an argument from an example.
    if args.get("radius_km") and binding.get("mode") == "compiler_entity":
        region = {"op": "BUFFER", "radius_km": float(args["radius_km"]), "source": region}
    time_value = args.get("time")
    if binding.get("mode") == "exact_select":
        return {"op": "SELECT", "entity": binding["entity"], "region": region,
                "time": time_value}
    if binding.get("mode") == "compiler_entity":
        entity = str(args.get("entity") or args.get("taxon") or "?taxon")
        for alias, canonical in (skill.get("aliases") or {}).items():
            if alias in entity.lower():
                entity = canonical
                break
        return {"op": "SELECT", "entity": entity, "region": region, "time": time_value}
    if binding.get("mode") == "annotate":
        return {"op": "ANNOTATE", "layer": binding["layer"],
                "source": {"op": "SELECT", "entity": binding["source_entity"],
                           "region": region, "time": time_value}}
    if binding.get("mode") == "operator" and binding.get("op") == "ESTIMATE":
        entity = str(args.get("entity") or args.get("taxon") or "?taxon")
        for alias, canonical in (skill.get("aliases") or {}).items():
            if alias in entity.lower():
                entity = canonical
                break
        donor = {"op": "REGION", "place": args.get("donor_region") or "dry-Deccan donor belt"}
        return {"op": "ESTIMATE", "method": args.get("method") or "feature",
                "source": {"op": "SELECT", "entity": entity, "region": donor, "time": None},
                "target": {"op": "REGION", "place": args.get("target") or "EBTL"}}
    raise ValueError("skill has no executable binding")


class Gateway:
    def __init__(self, skills: list[dict], log_path: pathlib.Path):
        self.skills = {skill["id"]: skill for skill in skills}
        self.log_path = log_path
        self.token = secrets.token_hex(24)
        gateway = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):  # noqa: N802
                if self.headers.get("Authorization") != "Bearer " + gateway.token:
                    self.send_error(403); return
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    request = json.loads(self.rfile.read(length))
                    skill = gateway.skills[request["skill"]]
                    ir = bind_context(skill_ir(skill, request.get("args") or {}))
                    schema, execution = execute_ir(ir)
                    result = {"skill": skill["id"], "ir": ir, "schema": schema,
                              "execution": execution}
                    with gateway.log_path.open("a") as stream:
                        stream.write(json.dumps({"at": dt.datetime.now().isoformat(),
                                                 "request": request, "result": result},
                                                ensure_ascii=False, default=str) + "\n")
                    body, status = json.dumps(result, default=str).encode(), 200
                except Exception as exc:
                    body = json.dumps({"error": f"{type(exc).__name__}: {exc}"}).encode()
                    status = 400
                self.send_response(status); self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body))); self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_):
                return

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self.server.server_port}/call"

    def close(self):
        self.server.shutdown(); self.thread.join(timeout=5); self.server.server_close()


def native_files(skills: list[dict], gateway: Gateway) -> dict[str, str]:
    files = {}
    index_lines = ["# Available conservation skills", "",
                   "Read the relevant SKILL.md, then invoke exactly as documented.", ""]
    for skill in skills:
        index_lines.append(f"- `{skill['id']}` — {skill['description']}")
        files[f"skills/{skill['id']}/SKILL.md"] = (
            f"# {skill['id']}\n\n{skill['description']}\n\n"
            "Use for:\n" + "\n".join(f"- {x}" for x in skill.get("use_for") or []) +
            "\n\nDo not use for:\n" + "\n".join(f"- {x}" for x in skill.get("exclude") or []) +
            "\n\nInvoke:\n\n```bash\npython3 /bench/arm/input/skill_call.py " + skill["id"] +
            " '{\"region\":\"EBTL\"}'\n```\n"
            "For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly "
            "asks to widen a search. Only include arguments the question supplies or the "
            "conversation has established. "
            "The command returns audited JSON.\n"
        )
    files["SKILLS_INDEX.md"] = "\n".join(index_lines) + "\n"
    files["skill_call.py"] = (
        "#!/usr/bin/env python3\nimport json,sys,urllib.request\n"
        f"URL={gateway.url!r}; TOKEN={gateway.token!r}\n"
        "payload={'skill':sys.argv[1],'args':json.loads(sys.argv[2]) if len(sys.argv)>2 else {}}\n"
        "req=urllib.request.Request(URL,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKEN})\n"
        "print(urllib.request.urlopen(req,timeout=300).read().decode())\n"
    )
    return files


def native_turn(question: str, session: CodexSession) -> dict:
    prompt = (
        "You are helping staff at a conservation NGO. Answer the current message in short, simple "
        "English. You have an index at /bench/arm/input/SKILLS_INDEX.md and executable skills under "
        "/bench/arm/input/skills. Read and invoke relevant skills with the documented skill_call.py. "
        "Use data before making a factual local claim. You may use more than one skill and Python "
        "for transparent calculations. Keep observations, reports, proxies and estimates separate. "
        "If the skills cannot support a requested conclusion, give the useful partial result and "
        "say exactly what is missing. Do not inspect paths outside /bench/arm.\n\nUSER:\n" + question
    )
    call = session.call(prompt, "user-turn")
    return {"question": question, "answer": call["final"], "agent_call": call}


def naked_turn(question: str, session: CodexSession) -> dict:
    prompt = (
        "Answer this conservation NGO staff question in short, simple English. Use your normal web "
        "research when useful. Do not assume access to private project data. Distinguish what you "
        "found from what you estimate, cite public sources you rely on, and say what is missing.\n\n"
        "USER:\n" + question
    )
    call = session.call(prompt, "user-turn")
    return {"question": question, "answer": call["final"], "agent_call": call}


def environment_manifest() -> dict:
    paths = [BENCH / "questions.json", BENCH / "arms.json", BENCH / "protocol.md",
             BENCH / "scoring.md", BENCH / "skills.json", MEMORY / "algebra" / "ir-spec.md",
             HARNESS / "parser.py", HARNESS / "executor.py", HARNESS / "connectors.py"]
    files = {str(path.relative_to(MEMORY.parent)): sha(path.read_bytes()) for path in paths}
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=MEMORY.parent,
                            text=True, capture_output=True).stdout.strip()
    return {"created_at": dt.datetime.now().isoformat(), "git_commit": commit,
            "dirty": bool(subprocess.run(["git", "status", "--porcelain"], cwd=MEMORY.parent,
                                         text=True, capture_output=True).stdout.strip()),
            "files": files, "codex_cli": subprocess.run([str(CODEX), "--version"], text=True,
                                                         capture_output=True).stdout.strip(),
            "codex_model": MODEL, "codex_reasoning": REASONING,
            "lora_endpoint": LORA_URL, "embedding": "BAAI/bge-small-en-v1.5"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--round", default="round-001")
    ap.add_argument("--conversation", action="append")
    ap.add_argument("--arm", action="append")
    ap.add_argument("--max-turns", type=int,
                    help="run only the first N turns of each selected conversation (smoke tests)")
    args = ap.parse_args()
    bank = json.loads((BENCH / "questions.json").read_text())
    skills = json.loads((BENCH / "skills.json").read_text())["skills"]
    wanted_conversations = set(args.conversation or [])
    conversations = [c for c in bank["conversations"]
                     if not wanted_conversations or c["id"] in wanted_conversations]
    arms = args.arm or ["codex-capability-first", "codex-late-bound", "codex-native-skills",
                        "lora9b-late-bound", "codex-naked"]
    run_root = BENCH / "runs" / args.round
    run_root.mkdir(parents=True, exist_ok=True)
    write_json(run_root / "manifest.json", environment_manifest())
    write_json(run_root / "bank.json", bank)
    write_json(run_root / "arms.json", json.loads((BENCH / "arms.json").read_text()))
    index = SemanticIndex(skills)
    gateway = Gateway(skills, run_root / "native-skill-calls.jsonl")
    state = {"round": args.round, "started_at": dt.datetime.now().isoformat(), "arms": arms,
             "conversations": []}
    try:
        for conversation in conversations:
            conv_state = {"id": conversation["id"], "checks": conversation["checks"], "arms": {}}
            print(f"conversation {conversation['id']}", flush=True)
            for arm in arms:
                print(f"  arm {arm}", flush=True)
                arm_state = {"turns": []}
                if arm.startswith("codex-"):
                    files = native_files(skills, gateway) if arm == "codex-native-skills" else {}
                    session = CodexSession(run_root, arm, conversation["id"], files,
                                           native=arm == "codex-native-skills",
                                           web=arm == "codex-naked")
                    try:
                        for question in conversation["turns"][:args.max_turns]:
                            if arm == "codex-capability-first":
                                turn = capability_turn(question, session)
                            elif arm == "codex-late-bound":
                                turn = late_bound_codex_turn(question, session, index, skills)
                            elif arm == "codex-native-skills":
                                turn = native_turn(question, session)
                            else:
                                turn = naked_turn(question, session)
                            arm_state["turns"].append(turn)
                            write_json(run_root / "progress" / conversation["id"] / f"{arm}.json",
                                       arm_state)
                    finally:
                        session.close()
                elif arm == "lora9b-late-bound":
                    messages: list[dict] = []
                    logdir = run_root / "isolation" / conversation["id"] / arm / "output"
                    logdir.mkdir(parents=True, exist_ok=True)
                    for question in conversation["turns"][:args.max_turns]:
                        turn = late_bound_lora_turn(question, messages, logdir, index, skills)
                        arm_state["turns"].append(turn)
                        write_json(run_root / "progress" / conversation["id"] / f"{arm}.json",
                                   arm_state)
                conv_state["arms"][arm] = arm_state
            state["conversations"].append(conv_state)
            write_json(run_root / "matrix.json", state)
        state["finished_at"] = dt.datetime.now().isoformat()
        write_json(run_root / "matrix.json", state)
        print(run_root / "matrix.json")
    finally:
        gateway.close(); index.close()


if __name__ == "__main__":
    main()
