#!/usr/bin/env python3
"""Start the Codex-native bridge and register it as an Idlisseus model endpoint."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import secrets
import signal
import subprocess
import sys
import time
import urllib.request
import uuid


HERE = pathlib.Path(__file__).resolve().parent
DEFAULT_IDLISSEUS = pathlib.Path("/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus")


def _paths(state: pathlib.Path) -> dict[str, pathlib.Path]:
    return {
        "token": state / ".api-token",
        "pid": state / "server.pid",
        "stdout": state / "server.stdout.log",
        "stderr": state / "server.stderr.log",
    }


def _token(path: pathlib.Path) -> str:
    if path.exists():
        return path.read_text().strip()
    value = secrets.token_urlsafe(36)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value + "\n")
    os.chmod(path, 0o600)
    return value


def _alive(pid_path: pathlib.Path) -> bool:
    try:
        pid = int(pid_path.read_text())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _start(state: pathlib.Path, host: str, port: int, python: str, sandbox: str,
           corpus: pathlib.Path, runner: str, container: str) -> None:
    paths = _paths(state)
    if _alive(paths["pid"]):
        return
    token = _token(paths["token"])
    env = os.environ.copy()
    env.update({
        "CODEX_NATIVE_API_TOKEN": token,
        "CODEX_NATIVE_STATE_DIR": str(state / "sessions"),
        "CODEX_NATIVE_HOST": host,
        "CODEX_NATIVE_PORT": str(port),
        "CODEX_NATIVE_SANDBOX": sandbox,
        "CODEX_NATIVE_RUNNER": runner,
        "CODEX_NATIVE_HERMES_CONTAINER": container,
        "CODEX_NATIVE_CORPUS": str(corpus),
    })
    paths["stdout"].parent.mkdir(parents=True, exist_ok=True)
    stdout = paths["stdout"].open("ab")
    stderr = paths["stderr"].open("ab")
    process = subprocess.Popen(
        [python, str(HERE / "server.py"), "--host", host, "--port", str(port)],
        stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
        start_new_session=True, env=env,
    )
    paths["pid"].write_text(str(process.pid) + "\n")
    for _ in range(50):
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.2)
    raise RuntimeError(f"bridge failed to become healthy; see {paths['stderr']}")


def _stop(state: pathlib.Path) -> None:
    pid_path = _paths(state)["pid"]
    if not _alive(pid_path):
        pid_path.unlink(missing_ok=True)
        return
    pid = int(pid_path.read_text())
    os.killpg(pid, signal.SIGTERM)
    pid_path.unlink(missing_ok=True)


def _register(idlisseus: pathlib.Path, token: str, port: int) -> str:
    os.chdir(idlisseus)
    sys.path[:0] = [str(idlisseus)]
    from core.database import ModelEndpoint, SessionLocal

    base_url = f"http://host.docker.internal:{port}/v1"
    model_id = "gpt-5.4-codex-native-skills"
    db = SessionLocal()
    try:
        endpoint = db.query(ModelEndpoint).filter(ModelEndpoint.base_url == base_url).first()
        if endpoint is None:
            endpoint = ModelEndpoint(id=str(uuid.uuid4())[:8], base_url=base_url)
            db.add(endpoint)
        endpoint.name = "Codex CLI · Native Skills"
        endpoint.api_key = token
        endpoint.is_enabled = True
        endpoint.cached_models = json.dumps([model_id])
        endpoint.pinned_models = json.dumps([model_id])
        endpoint.model_type = "llm"
        endpoint.endpoint_kind = "api"
        endpoint.model_refresh_mode = "manual"
        endpoint.supports_tools = False
        endpoint.owner = None
        db.commit()
        return endpoint.id
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "stop", "status"), nargs="?", default="start")
    parser.add_argument("--idlisseus", type=pathlib.Path, default=DEFAULT_IDLISSEUS)
    parser.add_argument("--state", type=pathlib.Path, default=HERE / "runs" / "service")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=7011)
    parser.add_argument("--sandbox", choices=("read-only", "workspace-write", "danger-full-access",
                                               "dangerously-bypass"), default="workspace-write")
    parser.add_argument("--runner", choices=("hermes-exec", "host"), default="hermes-exec",
                        help="default reuses the already-running Hermes container")
    parser.add_argument("--container", default="hermes-live")
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--corpus", type=pathlib.Path,
                        default=DEFAULT_IDLISSEUS.parents[1] / "dss" / "corpus" / "cards.jsonl")
    parser.add_argument("--no-register", action="store_true")
    args = parser.parse_args(argv)
    paths = _paths(args.state)
    if args.action == "stop":
        _stop(args.state)
        print(json.dumps({"status": "stopped", "state": str(args.state)}, indent=2))
        return 0
    if args.action == "status":
        print(json.dumps({"running": _alive(paths["pid"]), "pid_file": str(paths["pid"]),
                          "token_file": str(paths["token"]), "port": args.port}, indent=2))
        return 0
    _start(args.state, args.host, args.port, args.python, args.sandbox, args.corpus,
           args.runner, args.container)
    token = _token(paths["token"])
    endpoint_id = None if args.no_register else _register(args.idlisseus, token, args.port)
    print(json.dumps({
        "status": "ready", "endpoint_id": endpoint_id,
        "endpoint_name": "Codex CLI · Native Skills",
        "model": "gpt-5.4-codex-native-skills",
        "health": f"http://127.0.0.1:{args.port}/health",
        "token_file": str(paths["token"]),
        "pid_file": str(paths["pid"]),
        "note": "Refresh Idlisseus, create a chat using this model, and keep Idlisseus in chat mode.",
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
