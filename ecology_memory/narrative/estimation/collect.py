#!/usr/bin/env python3
"""Collect the frozen ecology-estimation bank through isolated Cursor agents."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


HERE = Path(__file__).resolve().parent
BANK = json.loads((HERE / "bank.json").read_text())["questions"]
RUNS = HERE / "runs"
MODELS = (
    "claude-4.6-opus-high",
    "gpt-5.4-medium",
    "cursor-grok-4.5-medium",
)
STAGE_LOCK = threading.Lock()


def save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")


def stage_runtime(isolation: Path) -> tuple[Path, Path, str]:
    source_agent = Path(os.path.realpath(shutil.which("agent") or ""))
    if not source_agent.exists():
        raise RuntimeError("Cursor agent CLI is unavailable")
    source_version = source_agent.parent
    agent_copy = isolation / "cursor-agent"
    staged_version = agent_copy / source_version.name
    auth_copy = isolation / "auth-config"
    with STAGE_LOCK:
        if not staged_version.exists():
            agent_copy.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_version, staged_version)
        if not (auth_copy / "auth.json").exists():
            auth_copy.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path.home() / ".config/cursor/auth.json", auth_copy / "auth.json")
    # Bubblewrap is launched through sudo and traverses the staged paths before constructing the
    # private namespace. These copies contain only the runtime and Cursor auth; the benchmark
    # repository remains unmounted. Match the already validated ecology-pilot transport.
    agent_copy.chmod(0o755)
    auth_copy.chmod(0o755)
    (auth_copy / "auth.json").chmod(0o644)
    return agent_copy, auth_copy, source_version.name


def run_one(model: str, question: dict, force: bool) -> str:
    qid = question["id"]
    path = RUNS / model / f"{qid}.json"
    if not force and path.exists() and path.stat().st_size > 500:
        return f"[{model}] {qid}: cached"

    isolation = Path("/tmp/ecology-estimation-v1")
    work = isolation / "work" / model / qid
    cursor_home = isolation / "cursor-home" / model / qid
    work.mkdir(parents=True, exist_ok=True)
    cursor_home.mkdir(parents=True, exist_ok=True)
    agent_copy, auth_copy, version = stage_runtime(isolation)
    for directory in (isolation, isolation / "work", isolation / "cursor-home", work, cursor_home):
        directory.chmod(0o777)

    prompt = (
        question["q"]
        + "\n\nPlease give your best answer now. Use tools and data where needed, and include "
          "citations and enough method detail for me to check it."
    )
    command = [
        "sudo", "bwrap", "--unshare-all", "--share-net", "--die-with-parent",
        "--ro-bind", "/usr", "/usr", "--ro-bind", "/lib", "/lib",
        "--ro-bind", "/etc", "/etc", "--symlink", "usr/bin", "/bin",
        "--dir", "/run", "--dir", "/run/systemd", "--ro-bind",
        "/run/systemd/resolve", "/run/systemd/resolve", "--proc", "/proc",
        "--dev", "/dev", "--dir", "/opt", "--ro-bind", str(agent_copy), "/opt/ca",
        "--dir", "/root", "--dir", "/root/.config", "--ro-bind", str(auth_copy),
        "/root/.config/cursor", "--bind", str(cursor_home), "/root/.cursor",
        "--bind", str(work), "/work", "--tmpfs", "/tmp", "--chdir", "/work",
        "--setenv", "HOME", "/root", "--setenv", "PATH", "/usr/bin:/bin",
        f"/opt/ca/{version}/cursor-agent", "-p", prompt, "--model", model,
        "--trust", "-f", "--approve-mcps", "--output-format", "stream-json",
    ]
    started = time.time()
    try:
        proc = subprocess.run(command, cwd=work, capture_output=True, text=True, timeout=900)
        events = []
        for line in (proc.stdout or "").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"type": "unparsed", "text": line})
        results = [event for event in events if event.get("type") == "result"]
        answer = str(results[-1].get("result") or "") if results else ""
        payload = {
            "benchmark": "ecology-estimation-benchmark-1",
            "model": model,
            "cursor_agent_version": version,
            "protocol": "Cursor Agent CLI in Bubblewrap filesystem isolation",
            "question_id": qid,
            "family": question["family"],
            "mode": question["mode"],
            "question": question["q"],
            "elapsed_s": round(time.time() - started, 3),
            "returncode": proc.returncode,
            "answer": answer,
            "events": events,
            "stderr_tail": (proc.stderr or "")[-1200:],
            "workspace_inside_isolation": "/work",
        }
    except subprocess.TimeoutExpired as exc:
        payload = {
            "benchmark": "ecology-estimation-benchmark-1",
            "model": model,
            "cursor_agent_version": version,
            "protocol": "Cursor Agent CLI in Bubblewrap filesystem isolation",
            "question_id": qid,
            "family": question["family"],
            "mode": question["mode"],
            "question": question["q"],
            "elapsed_s": round(time.time() - started, 3),
            "timeout": 900,
            "answer": "",
            "partial_stdout": exc.stdout.decode(errors="replace")[-4000:] if isinstance(exc.stdout, bytes) else (exc.stdout or "")[-4000:],
            "stderr_tail": exc.stderr.decode(errors="replace")[-1200:] if isinstance(exc.stderr, bytes) else (exc.stderr or "")[-1200:],
            "workspace_inside_isolation": "/work",
        }
    save(path, payload)
    return f"[{model}] {qid}: {payload['elapsed_s']}s len={len(payload.get('answer', ''))}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", default=",".join(MODELS))
    parser.add_argument("--questions", default=",".join(q["id"] for q in BANK))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    models = [item.strip() for item in args.models.split(",") if item.strip()]
    unknown = sorted(set(models) - set(MODELS))
    if unknown:
        raise SystemExit(f"unknown models: {unknown}")
    qids = {item.strip() for item in args.questions.split(",") if item.strip()}
    questions = [question for question in BANK if question["id"] in qids]
    jobs = [(model, question) for model in models for question in questions]
    print(f"collecting {len(jobs)} frozen cells", flush=True)
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(run_one, model, question, args.force) for model, question in jobs]
        for future in as_completed(futures):
            print(future.result(), flush=True)
    print("ECOLOGY-ESTIMATION-COLLECT-DONE", flush=True)


if __name__ == "__main__":
    main()
