#!/usr/bin/env python3
"""OpenAI-compatible bridge from Idlisseus to Codex CLI + native skills.

The bridge keeps one resumable Codex thread per caller-supplied session id.  Codex receives the
same progressive-disclosure skill bundle used by the winning benchmark arm.  Skill calls cross an
allowlisted in-process gateway; model-authored shell commands never choose connector code paths.

Two transports are exposed:

* POST /v1/chat/completions -- OpenAI-compatible, for an Idlisseus model endpoint.
* POST /v1/audit/chat       -- structured SSE, for the step/live audit client.

The OpenAI-compatible answer deliberately includes a compact live audit before the final answer,
so Idlisseus can display what Codex is doing without changes to its frontend.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import http.server
import json
import os
import pathlib
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
from typing import Any, Callable, Iterator


HERE = pathlib.Path(__file__).resolve().parent
MEMORY = HERE.parents[1]
REPO = MEMORY.parent
BENCH = MEMORY / "narrative" / "benchmarks" / "late-bound-skills"
HARNESS = MEMORY / "harness"
HERMES_BENCH = MEMORY / "hermes_bench"
sys.path[:0] = [str(HARNESS), str(HERMES_BENCH)]

import engine as E  # noqa: E402
import executor as X  # noqa: E402
import ir_schema as IR  # noqa: E402


MODEL = os.environ.get("CODEX_NATIVE_MODEL", "gpt-5.4")
REASONING = os.environ.get("CODEX_NATIVE_REASONING", "medium")
CODEX = pathlib.Path(os.environ.get("CODEX_NATIVE_CODEX", str(pathlib.Path.home() / ".local/bin/codex")))
AUTH_SOURCE = pathlib.Path(os.environ.get("CODEX_NATIVE_AUTH", str(pathlib.Path.home() / ".codex/auth.json")))
STATE_ROOT = pathlib.Path(os.environ.get("CODEX_NATIVE_STATE_DIR", str(HERE / "runs")))
SKILLS_PATH = pathlib.Path(os.environ.get("CODEX_NATIVE_SKILLS", str(BENCH / "skills.json")))
_TOKEN_FILE = os.environ.get("CODEX_NATIVE_API_TOKEN_FILE", "").strip()
API_TOKEN = os.environ.get("CODEX_NATIVE_API_TOKEN", "").strip()
if not API_TOKEN and _TOKEN_FILE:
    with contextlib.suppress(OSError):
        API_TOKEN = pathlib.Path(_TOKEN_FILE).read_text().strip()
SANDBOX = os.environ.get("CODEX_NATIVE_SANDBOX", "workspace-write").strip()
RUNNER = os.environ.get("CODEX_NATIVE_RUNNER", "hermes-exec").strip()
HERMES_CONTAINER = os.environ.get("CODEX_NATIVE_HERMES_CONTAINER", "hermes-live").strip()
CONTAINER_ROOT = pathlib.PurePosixPath("/tmp/codex-native")
MAX_REQUEST_BYTES = 128 * 1024
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")
SKILL_COMMAND = re.compile(r"skill_call\.py\s+([A-Za-z0-9_.-]+)")
READ_SKILL = re.compile(r"/skills/([A-Za-z0-9_.-]+)/SKILL\.md")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                      separators=(",", ":"))


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else (
        value.encode() if isinstance(value, str) else _stable_json(value).encode()
    )
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    os.replace(tmp, path)


def _safe_id(value: str | None) -> str:
    cleaned = SAFE_ID.sub("-", str(value or "").strip()).strip(".-")
    return (cleaned or secrets.token_hex(12))[:120]


def _load_skills() -> list[dict]:
    with SKILLS_PATH.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    return list(payload.get("skills") or [])


SKILLS = _load_skills()
SKILLS_BY_ID = {item["id"]: item for item in SKILLS}


def _bind_context(ir: dict | None) -> dict | None:
    return IR.canonicalize(E._bind_context(json.loads(json.dumps(ir)), "ebtl")) if ir else None


def _skill_ir(skill: dict, args: dict) -> dict:
    binding = skill.get("binding") or {}
    region_value = binding.get("region_place") or args.get("region") or "EBTL"
    region: dict = {"op": "REGION", "place": region_value}
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
        return {
            "op": "ANNOTATE", "layer": binding["layer"],
            "source": {"op": "SELECT", "entity": binding["source_entity"],
                       "region": region, "time": time_value},
        }
    if binding.get("mode") == "operator" and binding.get("op") == "ESTIMATE":
        entity = str(args.get("entity") or args.get("taxon") or "?taxon")
        for alias, canonical in (skill.get("aliases") or {}).items():
            if alias in entity.lower():
                entity = canonical
                break
        donor = {"op": "REGION", "place": args.get("donor_region") or "dry-Deccan donor belt"}
        return {
            "op": "ESTIMATE", "method": args.get("method") or "feature",
            "source": {"op": "SELECT", "entity": entity, "region": donor, "time": None},
            "target": {"op": "REGION", "place": args.get("target") or "EBTL"},
        }
    raise ValueError("skill has no executable binding")


def _execute_skill(skill_id: str, args: dict) -> dict:
    if skill_id not in SKILLS_BY_ID:
        raise KeyError(f"unknown skill: {skill_id}")
    ir = _bind_context(_skill_ir(SKILLS_BY_ID[skill_id], args))
    schema = IR.validate(ir)
    if not schema["valid"]:
        execution = {"status": "data_request", "reason": "invalid_ir",
                     "detail": {"errors": schema["errors"]}, "provenance": []}
    else:
        execution = X.execute(ir)
    return {"skill": skill_id, "ir": ir, "schema": schema, "execution": execution}


def _summary(result: dict) -> str:
    execution = result.get("execution") or {}
    status = execution.get("status") or "unknown"
    if status != "answer":
        reason = execution.get("reason") or "unspecified"
        return f"{status}: {reason}"
    value = execution.get("value") or {}
    rows = value.get("rows") if isinstance(value, dict) else None
    row_count = len(rows) if isinstance(rows, list) else None
    label = execution.get("label") or (value.get("label") if isinstance(value, dict) else None)
    source = value.get("source") if isinstance(value, dict) else None
    parts = ["answer"]
    if row_count is not None:
        parts.append(f"{row_count} rows")
    if label:
        parts.append(str(label))
    if source:
        parts.append(str(source))
    return " · ".join(parts)


class Session:
    def __init__(self, session_id: str):
        self.id = _safe_id(session_id)
        self.root = STATE_ROOT / self.id
        self.home = self.root / "home"
        self.work = self.root / "work"
        self.input = self.root / "input"
        self.output = self.root / "output"
        self.state_path = self.root / "state.json"
        self.audit_path = self.root / "audit.jsonl"
        self.raw_path = self.root / "codex-events.jsonl"
        self.lock = threading.Lock()
        self.gateway_token = secrets.token_urlsafe(24)
        self.thread_id: str | None = None
        self.turn = 0
        self._load()
        self._prepare()

    def _load(self) -> None:
        try:
            state = json.loads(self.state_path.read_text())
        except Exception:
            state = {}
        self.thread_id = state.get("thread_id")
        self.turn = int(state.get("turn") or 0)
        self.gateway_token = state.get("gateway_token") or self.gateway_token

    def _save(self) -> None:
        _atomic_json(self.state_path, {
            "schema": 1, "session_id": self.id, "thread_id": self.thread_id,
            "turn": self.turn, "gateway_token": self.gateway_token,
            "model": MODEL, "reasoning": REASONING,
            "skills_sha256": _sha256(SKILLS), "updated_at": dt.datetime.now().isoformat(),
        })

    def _prepare(self) -> None:
        for path in (self.home, self.work, self.input, self.output):
            path.mkdir(parents=True, exist_ok=True)
        auth_target = self.home / "auth.json"
        if not auth_target.exists():
            if not AUTH_SOURCE.exists():
                raise FileNotFoundError(f"Codex auth file not found: {AUTH_SOURCE}")
            shutil.copy2(AUTH_SOURCE, auth_target)
            os.chmod(auth_target, 0o600)
        invocation_root = (
            CONTAINER_ROOT / "sessions" / self.id / "input"
            if RUNNER == "hermes-exec" else self.input
        )
        index_lines = ["# Available conservation skills", "",
                       "Read the relevant SKILL.md, then invoke exactly as documented.", ""]
        for skill in SKILLS:
            index_lines.append(f"- `{skill['id']}` — {skill['description']}")
            skill_dir = self.input / "skills" / skill["id"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            md = (
                f"# {skill['id']}\n\n{skill['description']}\n\nUse for:\n" +
                "\n".join(f"- {x}" for x in skill.get("use_for") or []) +
                "\n\nDo not use for:\n" +
                "\n".join(f"- {x}" for x in skill.get("exclude") or []) +
                "\n\nInvoke:\n\n```bash\npython3 " + str(invocation_root / "skill_call.py") +
                " " + skill["id"] + " '{\"region\":\"EBTL\"}'\n```\n" +
                "For a named-taxon skill add `entity`; add `radius_km` only when the user "
                "explicitly asks to widen a search. Only include arguments the question supplies "
                "or the conversation has established. The command returns audited JSON.\n"
            )
            (skill_dir / "SKILL.md").write_text(md)
        (self.input / "SKILLS_INDEX.md").write_text("\n".join(index_lines) + "\n")
        wrapper = (
            "#!/usr/bin/env python3\nimport json,sys,urllib.request\n"
            f"URL='http://127.0.0.1:{SERVER_PORT}/internal/skill-call'\n"
            f"TOKEN={self.gateway_token!r}\nSESSION={self.id!r}\n"
            "payload={'session':SESSION,'skill':sys.argv[1],"
            "'args':json.loads(sys.argv[2]) if len(sys.argv)>2 else {}}\n"
            "req=urllib.request.Request(URL,data=json.dumps(payload).encode(),"
            "headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKEN})\n"
            "print(urllib.request.urlopen(req,timeout=300).read().decode())\n"
        )
        wrapper_path = self.input / "skill_call.py"
        wrapper_path.write_text(wrapper)
        os.chmod(wrapper_path, 0o700)
        self._save()

    def append_audit(self, event: dict) -> None:
        event = {"at": dt.datetime.now().isoformat(), "session_id": self.id,
                 "turn": self.turn, **event}
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


_SESSIONS: dict[str, Session] = {}
_SESSIONS_LOCK = threading.Lock()


def get_session(session_id: str) -> Session:
    key = _safe_id(session_id)
    with _SESSIONS_LOCK:
        if key not in _SESSIONS:
            _SESSIONS[key] = Session(key)
        return _SESSIONS[key]


def _native_prompt(message: str, session: Session) -> str:
    input_root = (
        CONTAINER_ROOT / "sessions" / session.id / "input"
        if RUNNER == "hermes-exec" else session.input
    )
    return (
        "You are helping staff at a conservation NGO. Answer the current message in short, simple "
        "English. You have an index at " + str(input_root / "SKILLS_INDEX.md") +
        " and executable skills under " + str(input_root / "skills") + ". Read and invoke "
        "relevant skills with the documented skill_call.py. Use data before making a factual "
        "local claim. You may use more than one skill and Python for transparent calculations. "
        "Keep observations, reports, proxies and estimates separate. If the skills cannot support "
        "a requested conclusion, give the useful partial result and say exactly what is missing. "
        "Do not inspect paths outside this session's input and work directories. Do not use the "
        "public web. Never read credentials or environment files.\n\nUSER:\n" + message
    )


def _command_kind(command: str) -> tuple[str, str]:
    match = SKILL_COMMAND.search(command)
    if match:
        return "skill", match.group(1)
    match = READ_SKILL.search(command)
    if match:
        return "read_skill", match.group(1)
    if "SKILLS_INDEX.md" in command or "/skills" in command and "find " in command:
        return "discover_skills", "skill index"
    if "python" in command:
        return "calculation", "transparent calculation"
    return "command", "inspection"


def _audit_from_codex(event: dict) -> list[dict]:
    item = event.get("item") or {}
    item_type = item.get("type")
    status = item.get("status")
    if event.get("type") == "thread.started":
        return [{"type": "thread", "thread_id": event.get("thread_id")}]
    if item_type == "command_execution":
        command = item.get("command") or ""
        kind, label = _command_kind(command)
        if event.get("type") == "item.started":
            return [{"type": "tool_start", "kind": kind, "tool": label,
                     "command": command}]
        if event.get("type") == "item.completed" or status in {"completed", "failed"}:
            output = item.get("aggregated_output") or ""
            compact = output.strip()
            if kind == "skill":
                with contextlib.suppress(Exception):
                    compact = _summary(json.loads(compact))
            if len(compact) > 800:
                compact = compact[:797] + "..."
            return [{"type": "tool_output", "kind": kind, "tool": label,
                     "command": command, "output": compact,
                     "exit_code": item.get("exit_code")}]
    if item_type == "agent_message" and event.get("type") == "item.completed":
        return [{"type": "agent_message", "text": item.get("text") or ""}]
    if event.get("type") == "turn.completed":
        return [{"type": "usage", "usage": event.get("usage") or {}}]
    if event.get("type") == "turn.failed":
        return [{"type": "error", "error": event.get("error") or "Codex turn failed"}]
    return []


def _prepare_hermes_session(session: Session) -> tuple[str, str, str, str]:
    """Copy one bounded session into the already-running Hermes container.

    Repository policy forbids starting or restarting containers, so this runner uses ``docker
    exec``. Codex runs as uid/gid 65534, which cannot traverse the Hermes data mount; its private
    state is confined to a uniquely named directory below /tmp.
    """
    root = CONTAINER_ROOT / "sessions" / session.id
    home = str(root / "home")
    work = str(root / "work")
    input_root = str(root / "input")
    output = str(root / "output")
    binary = str(CONTAINER_ROOT / "bin" / "codex")
    subprocess.run([
        "docker", "exec", "-u", "0:0", HERMES_CONTAINER, "sh", "-lc",
        "mkdir -p /tmp/codex-native/bin "
        f"{home} {work} {input_root} {output} && "
        f"rm -rf {input_root} && mkdir -p {input_root}",
    ], check=True, capture_output=True, text=True)
    subprocess.run(["docker", "cp", str(CODEX), f"{HERMES_CONTAINER}:{binary}"],
                   check=True, capture_output=True, text=True)
    subprocess.run(["docker", "cp", str(session.input) + "/.",
                    f"{HERMES_CONTAINER}:{input_root}"],
                   check=True, capture_output=True, text=True)
    subprocess.run(["docker", "cp", str(session.home / "auth.json"),
                    f"{HERMES_CONTAINER}:{home}/auth.json"],
                   check=True, capture_output=True, text=True)
    subprocess.run([
        "docker", "exec", "-u", "0:0", HERMES_CONTAINER, "sh", "-lc",
        f"chmod 755 {binary} && chown -R 65534:65534 {root} && chmod 700 {home}",
    ], check=True, capture_output=True, text=True)
    return home, work, output, binary


def run_turn(session: Session, message: str, emit: Callable[[dict], None]) -> dict:
    with session.lock:
        session.turn += 1
        turn = session.turn
        prompt = _native_prompt(message, session)
        final_path = session.output / f"{turn:04d}-final.txt"
        env = os.environ.copy()
        env.update({
            "HOME": str(session.home), "CODEX_HOME": str(session.home),
            "POINTS_CACHE": str(STATE_ROOT / "cache" / "points"),
            "DISCOVERY_CACHE": str(STATE_ROOT / "cache" / "discovery"),
        })
        corpus = os.environ.get("CODEX_NATIVE_CORPUS", "").strip()
        if corpus:
            env["CORPUS_CARDS"] = corpus
        container_final: str | None = None
        if RUNNER == "hermes-exec":
            home, work, output, binary = _prepare_hermes_session(session)
            container_final = f"{output}/{final_path.name}"
            base = [
                "docker", "exec", "-i", "-u", "65534:65534",
                "-e", f"HOME={home}", "-e", f"CODEX_HOME={home}",
                "-w", work, HERMES_CONTAINER, binary, "exec",
            ]
            requested_sandbox = "container-boundary"
        else:
            base = [str(CODEX), "exec"]
            requested_sandbox = SANDBOX
        common = ["--json", "-m", MODEL, "-c", f'model_reasoning_effort="{REASONING}"',
                  "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
                  "-o", container_final or str(final_path)]
        if RUNNER == "hermes-exec":
            common.append("--dangerously-bypass-approvals-and-sandbox")
        elif SANDBOX == "dangerously-bypass":
            common.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            common.extend(["-s", SANDBOX])
        if session.thread_id:
            # ``exec resume`` has a smaller option surface than ``exec``: the working directory is
            # inherited from docker exec / Popen, and options must precede the session id.
            command = base + ["resume"] + common + [session.thread_id, "-"]
        else:
            command = base + common + ["-C", work if RUNNER == "hermes-exec"
                                        else str(session.work), "-"]
        request = {
            "type": "request", "turn": turn, "message": message, "model": MODEL,
            "reasoning": REASONING, "prompt_sha256": _sha256(prompt),
            "skills_sha256": _sha256(SKILLS), "sandbox": requested_sandbox,
            "runner": RUNNER,
        }
        session.append_audit(request)
        emit({"type": "turn_start", "turn": turn, "model": MODEL,
              "reasoning": REASONING, "audit_path": str(session.audit_path)})
        started = time.time()
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env,
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(prompt)
        process.stdin.close()
        pending_message: str | None = None
        usage: dict = {}
        for raw_line in process.stdout:
            clean = ANSI.sub("", raw_line).replace("\r", "")
            with session.raw_path.open("a", encoding="utf-8") as raw_stream:
                raw_stream.write(clean)
            try:
                event = json.loads(clean)
            except json.JSONDecodeError:
                continue
            for audit in _audit_from_codex(event):
                if audit["type"] == "thread":
                    session.thread_id = audit.get("thread_id") or session.thread_id
                    session._save()
                    continue
                if audit["type"] == "agent_message":
                    if pending_message:
                        status_event = {"type": "status", "text": pending_message}
                        session.append_audit(status_event)
                        emit(status_event)
                    pending_message = audit.get("text") or ""
                    continue
                if pending_message:
                    status_event = {"type": "status", "text": pending_message}
                    session.append_audit(status_event)
                    emit(status_event)
                    pending_message = None
                if audit["type"] == "usage":
                    usage = audit.get("usage") or {}
                session.append_audit(audit)
                emit(audit)
        stderr = process.stderr.read() if process.stderr is not None else ""
        return_code = process.wait()
        if container_final:
            copied = subprocess.run([
                "docker", "cp", f"{HERMES_CONTAINER}:{container_final}", str(final_path)
            ], capture_output=True, text=True)
            if copied.returncode != 0 and return_code == 0:
                stderr += "\nCould not copy final answer: " + copied.stderr
        final = final_path.read_text().strip() if final_path.exists() else (pending_message or "")
        elapsed = round(time.time() - started, 3)
        if return_code != 0:
            error = {"type": "error", "error": stderr.strip()[-1000:] or
                     f"Codex exited {return_code}", "exit_code": return_code}
            session.append_audit(error)
            emit(error)
        result = {
            "type": "final", "answer": final, "thread_id": session.thread_id,
            "session_id": session.id, "turn": turn, "usage": usage,
            "latency_s": elapsed, "exit_code": return_code,
            "audit_path": str(session.audit_path),
        }
        session.append_audit(result)
        session._save()
        emit(result)
        return result


def _trace_markdown(event: dict) -> str:
    event_type = event.get("type")
    if event_type == "turn_start":
        return (
            "<details open><summary>Codex CLI · native skill trace</summary>\n\n"
            f"`{event.get('model')}` · reasoning `{event.get('reasoning')}`\n\n"
        )
    if event_type == "status":
        return f"- **Codex:** {event.get('text', '').strip()}\n"
    if event_type == "tool_start":
        kind = event.get("kind")
        if kind == "skill":
            return f"- **Invoke skill:** `{event.get('tool')}`\n"
        if kind == "read_skill":
            return f"- **Read skill:** `{event.get('tool')}`\n"
        if kind == "discover_skills":
            return "- **Discover skills:** inspect the frozen skill index\n"
        if kind == "calculation":
            return "- **Calculate:** transparent Python check\n"
        return "- **Inspect:** bounded session input\n"
    if event_type == "tool_output":
        output = str(event.get("output") or "").strip()
        if output:
            safe_output = output.replace("`", "'")
            return f"  - Result: `{safe_output}`\n"
    if event_type == "error":
        return f"- **Error:** {event.get('error')}\n"
    if event_type == "final":
        return (
            f"\nAudit id: `{event.get('session_id')}/{event.get('turn')}` · "
            f"{event.get('latency_s')}s\n\n</details>\n\n{event.get('answer', '')}"
        )
    return ""


SERVER_PORT = int(os.environ.get("CODEX_NATIVE_PORT", "7011"))


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CodexNativeSkills/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("invalid request size")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON object required")
        return payload

    def _authorized(self, internal_token: str | None = None) -> bool:
        expected = internal_token if internal_token is not None else API_TOKEN
        if not expected:
            return self.client_address[0] in {"127.0.0.1", "::1"}
        return self.headers.get("Authorization") == "Bearer " + expected

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, payload: Any) -> None:
        raw = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str)
        self.wfile.write(f"data: {raw}\n\n".encode())
        self.wfile.flush()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"/health", "/v1/models"}:
            if parsed.path == "/health":
                self._send_json(200, {"status": "ok", "model": MODEL,
                                      "skills": len(SKILLS), "codex": str(CODEX),
                                      "runner": RUNNER, "container": HERMES_CONTAINER})
            else:
                if not self._authorized():
                    self._send_json(401, {"error": {"message": "unauthorized"}})
                    return
                self._send_json(200, {"object": "list", "data": [{
                    "id": "gpt-5.4-codex-native-skills", "object": "model",
                    "owned_by": "codex-cli", "actual_model": MODEL,
                }]})
            return
        if parsed.path.startswith("/v1/audit/"):
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            session_id = _safe_id(parsed.path.rsplit("/", 1)[-1])
            session = get_session(session_id)
            rows = []
            if session.audit_path.exists():
                for line in session.audit_path.read_text().splitlines():
                    with contextlib.suppress(json.JSONDecodeError):
                        rows.append(json.loads(line))
            self._send_json(200, {"session_id": session_id, "events": rows,
                                  "audit_path": str(session.audit_path)})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self._json_body()
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})
            return
        if parsed.path == "/internal/skill-call":
            session = get_session(str(body.get("session") or ""))
            if not self._authorized(session.gateway_token):
                self._send_json(403, {"error": "unauthorized"})
                return
            try:
                skill_id = str(body.get("skill") or "")
                args = body.get("args") if isinstance(body.get("args"), dict) else {}
                result = _execute_skill(skill_id, args)
                session.append_audit({"type": "skill_call", "skill": skill_id,
                                      "args": args, "result": result})
                self._send_json(200, result)
            except Exception as exc:
                session.append_audit({"type": "skill_error", "skill": body.get("skill"),
                                      "error": f"{type(exc).__name__}: {exc}"})
                self._send_json(400, {"error": f"{type(exc).__name__}: {exc}"})
            return
        if parsed.path not in {"/v1/chat/completions", "/v1/audit/chat"}:
            self._send_json(404, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(401, {"error": {"message": "unauthorized"}})
            return
        messages = body.get("messages") if isinstance(body.get("messages"), list) else []
        message = ""
        for item in reversed(messages):
            if item.get("role") == "user":
                content = item.get("content")
                message = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                break
        message = str(body.get("message") or message).strip()
        if not message:
            self._send_json(400, {"error": {"message": "user message required"}})
            return
        session_id = _safe_id(str(body.get("session_id") or body.get("session") or ""))
        session = get_session(session_id)
        structured = parsed.path == "/v1/audit/chat"
        stream = bool(body.get("stream")) or structured
        events: list[dict] = []
        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            def emit(event: dict) -> None:
                events.append(event)
                if structured:
                    self._sse(event)
                    return
                delta = _trace_markdown(event)
                if not delta:
                    return
                chunk = {
                    "id": f"chatcmpl-{session.id}", "object": "chat.completion.chunk",
                    "model": "gpt-5.4-codex-native-skills",
                    "choices": [{"index": 0, "delta": {"content": delta},
                                 "finish_reason": None}],
                }
                self._sse(chunk)

            try:
                result = run_turn(session, message, emit)
                if structured:
                    self._sse("[DONE]")
                else:
                    self._sse({
                        "id": f"chatcmpl-{session.id}", "object": "chat.completion.chunk",
                        "model": "gpt-5.4-codex-native-skills",
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        "usage": result.get("usage") or {},
                    })
                    self._sse("[DONE]")
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:
                error = {"type": "error", "error": f"{type(exc).__name__}: {exc}"}
                with contextlib.suppress(Exception):
                    self._sse(error if structured else {
                        "error": {"message": error["error"], "type": "bridge_error"}
                    })
            return
        try:
            result = run_turn(session, message, events.append)
        except Exception as exc:
            self._send_json(500, {"error": {"message": f"{type(exc).__name__}: {exc}"}})
            return
        content = "".join(_trace_markdown(event) for event in events)
        self._send_json(200, {
            "id": f"chatcmpl-{session.id}", "object": "chat.completion",
            "model": "gpt-5.4-codex-native-skills",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content},
                         "finish_reason": "stop"}],
            "usage": result.get("usage") or {},
            "codex_audit": {"session_id": session.id, "turn": result.get("turn"),
                            "path": result.get("audit_path")},
        })


def main(argv: list[str] | None = None) -> int:
    global SERVER_PORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("CODEX_NATIVE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        missing = [str(path) for path in (CODEX, AUTH_SOURCE, SKILLS_PATH) if not path.exists()]
        payload = {"ok": not missing, "missing": missing, "model": MODEL,
                   "reasoning": REASONING, "sandbox": SANDBOX, "skills": len(SKILLS),
                   "runner": RUNNER, "container": HERMES_CONTAINER,
                   "state_root": str(STATE_ROOT)}
        print(json.dumps(payload, indent=2))
        return 0 if not missing else 1
    SERVER_PORT = args.port
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    print(json.dumps({"status": "listening", "host": args.host, "port": args.port,
                      "model": MODEL, "skills": len(SKILLS), "sandbox": SANDBOX,
                      "runner": RUNNER, "container": HERMES_CONTAINER}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
