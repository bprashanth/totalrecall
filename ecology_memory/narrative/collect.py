#!/usr/bin/env python3
"""Collect the frozen ecology narrative pilot.

Generated transcripts are intentionally written by this runner. Authored benchmark files are
edited separately. Existing non-trivial outputs are never overwritten unless --force is supplied.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


HERE = Path(__file__).resolve().parent
MEMORY = HERE.parent
BANK = json.loads((HERE / "bank.json").read_text())["questions"]
RUNS = HERE / "runs"

ARMS = ("gemini-flash-agent", "deepseek-v4-web", "ecology-stack-best",
        "ecology-mech-bind-lora9", "ecology-stack-lora9")
STAGE_LOCK = threading.Lock()


def output_path(arm: str, qid: str) -> Path:
    return RUNS / arm / f"{qid}.json"


def cached(path: Path, force: bool) -> bool:
    return not force and path.exists() and path.stat().st_size > 400


def save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n")


def gemini(qq: dict, force: bool) -> str:
    arm = "gemini-flash-agent"
    path = output_path(arm, qq["id"])
    if cached(path, force):
        return f"[{arm}] {qq['id']}: cached"
    isolation = Path("/tmp/ecology-narrative/isolation")
    work = isolation / "work" / qq["id"]
    cursor_home = isolation / "cursor-home" / qq["id"]
    agent_copy = isolation / "cursor-agent"
    auth_copy = isolation / "auth-config"
    work.mkdir(parents=True, exist_ok=True)
    cursor_home.mkdir(parents=True, exist_ok=True)
    # Bubblewrap cannot traverse the user's private home while building its namespace, so stage
    # only the agent runtime and auth file in a private temporary root. These are never recorded.
    source_agent = Path(os.path.realpath(shutil.which("agent") or ""))
    source_version = source_agent.parent
    staged_version = agent_copy / source_version.name
    with STAGE_LOCK:
        if not staged_version.exists():
            agent_copy.mkdir(parents=True, exist_ok=True)
            shutil.copytree(source_version, staged_version)
        if not (auth_copy / "auth.json").exists():
            auth_copy.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path.home() / ".config/cursor/auth.json", auth_copy / "auth.json")
    for directory in (isolation, work, cursor_home):
        directory.chmod(0o777)
    (auth_copy / "auth.json").chmod(0o644)
    prompt = qq["q"] + "\n\nPlease give your best answer now and include citations I can check."
    started = time.time()
    bwrap = [
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
        f"/opt/ca/{source_version.name}/cursor-agent",
    ]
    try:
        proc = subprocess.run(
            bwrap + ["-p", prompt, "--model", "gemini-3.5-flash", "--trust", "-f",
                     "--approve-mcps", "--output-format", "stream-json"],
            cwd=work, capture_output=True, text=True, timeout=900,
        )
        events = []
        for line in (proc.stdout or "").splitlines():
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"type": "unparsed", "text": line})
        result_events = [event for event in events if event.get("type") == "result"]
        answer = str(result_events[-1].get("result") or "") if result_events else ""
        payload = {
            "arm": arm, "model": "gemini-3.5-flash",
            "protocol": "Cursor Agent CLI in Bubblewrap filesystem isolation",
            "question_id": qq["id"], "question": qq["q"],
            "elapsed_s": round(time.time() - started, 3), "returncode": proc.returncode,
            "answer": answer, "events": events, "stderr_tail": (proc.stderr or "")[-1000:],
            "workspace_inside_isolation": "/work",
        }
    except subprocess.TimeoutExpired as exc:
        payload = {
            "arm": arm, "model": "gemini-3.5-flash",
            "protocol": "Cursor Agent CLI in Bubblewrap filesystem isolation",
            "question_id": qq["id"], "question": qq["q"],
            "elapsed_s": round(time.time() - started, 3), "timeout": 900,
            "answer": (exc.stdout or "") if isinstance(exc.stdout, str) else "",
            "stderr_tail": (exc.stderr or "")[-1000:] if isinstance(exc.stderr, str) else "",
            "workspace": str(work),
        }
    save(path, payload)
    return f"[{arm}] {qq['id']}: {payload['elapsed_s']}s len={len(payload.get('answer',''))}"


def openrouter_key() -> str:
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    config = Path.home() / ".config/idlisseus/openrouter.json"
    return json.loads(config.read_text())["api_key"]


def deepseek_web(qq: dict, force: bool) -> str:
    arm = "deepseek-v4-web"
    path = output_path(arm, qq["id"])
    if cached(path, force):
        return f"[{arm}] {qq['id']}: cached"
    started = time.time()
    body = json.dumps({
        "model": "deepseek/deepseek-v4-flash",
        "messages": [{"role": "user", "content": qq["q"] +
                      "\n\nPlease give your best answer now and include citations I can check."}],
        "temperature": 0,
        "max_tokens": 3000,
        "reasoning": {"effort": "low"},
        "plugins": [{"id": "web", "engine": "exa", "max_results": 10}],
    }).encode()
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions", data=body,
        headers={"Authorization": f"Bearer {openrouter_key()}",
                 "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            raw = json.loads(response.read())
        message = raw["choices"][0]["message"]
        payload = {
            "arm": arm, "model": "deepseek/deepseek-v4-flash",
            "protocol": "OpenRouter Chat Completions + one-shot web plugin (Exa, max 10)",
            "question_id": qq["id"], "question": qq["q"],
            "elapsed_s": round(time.time() - started, 3),
            "answer": message.get("content") or "", "annotations": message.get("annotations", []),
            "tool_calls": message.get("tool_calls", []), "usage": raw.get("usage", {}),
            "finish_reason": raw["choices"][0].get("finish_reason"),
        }
    except Exception as exc:
        payload = {
            "arm": arm, "model": "deepseek/deepseek-v4-flash",
            "protocol": "OpenRouter Chat Completions + one-shot web plugin (Exa, max 10)",
            "question_id": qq["id"], "question": qq["q"],
            "elapsed_s": round(time.time() - started, 3), "error": repr(exc), "answer": "",
        }
    save(path, payload)
    return f"[{arm}] {qq['id']}: {payload['elapsed_s']}s len={len(payload.get('answer',''))}"


def stack(qq: dict, force: bool, lora: bool = False) -> str:
    arm = "ecology-stack-lora9" if lora else "ecology-stack-best"
    path = output_path(arm, qq["id"])
    if cached(path, force):
        return f"[{arm}] {qq['id']}: cached"
    for import_path in (MEMORY / "integration/runtime", MEMORY / "hermes_bench",
                        MEMORY / "harness"):
        if str(import_path) not in sys.path:
            sys.path.insert(0, str(import_path))
    from pipeline import run_question
    started = time.time()
    compiler = "lora9b" if lora else "qwen2b"
    responder = "lora9b" if lora else "qwen9b"
    try:
        result = run_question(qq["q"], model=compiler, context="ebtl", history=[],
                              selector="qwen9b>deepseekv4", compiler=compiler,
                              responder=responder)
        payload = {
            "arm": arm,
            "model": ("merged-9b-002 last-mile compiler/responder" if lora else
                      "accepted ecology stack (Q9 selector > DS verifier @ Q2 compiler -> Q9 responder)"),
            "protocol": "typed algebra + deterministic connectors/executor + audited responder",
            "question_id": qq["id"], "elapsed_wall_s": round(time.time() - started, 3),
            **result,
        }
    except Exception as exc:
        payload = {"arm": arm, "question_id": qq["id"], "question": qq["q"],
                   "elapsed_wall_s": round(time.time() - started, 3),
                   "error": repr(exc), "answer": ""}
    save(path, payload)
    return f"[{arm}] {qq['id']}: {payload['elapsed_wall_s']}s len={len(payload.get('answer',''))}"


def mech_bind_lora9(qq: dict, force: bool) -> str:
    """Execute the frozen plan, then allow LoRA-9B to explain only the audited result."""
    arm = "ecology-mech-bind-lora9"
    path = output_path(arm, qq["id"])
    if cached(path, force):
        return f"[{arm}] {qq['id']}: cached"
    for import_path in (MEMORY / "integration/runtime", MEMORY / "hermes_bench",
                        MEMORY / "harness"):
        if str(import_path) not in sys.path:
            sys.path.insert(0, str(import_path))
    from engine import render_turn
    from executor import execute
    plan = json.loads((HERE / "plans.json").read_text())[qq["id"]]
    started = time.time()
    try:
        execution = execute(plan)
        compiled = {
            "compiler": "benchmark-bound-plan", "base_compiler": None, "selector": None,
            "critic": None, "dialogue_mode": "execute", "question": qq["q"], "ir": plan,
            "raw_compiler": None, "raw_selector": None, "raw_critic": None,
            "parse_valid": True, "repair_events": ["benchmark:frozen_plan_bound"],
            "schema": {"valid": True, "errors": [], "holes": [], "ops": []},
            "execution": execution, "compile_execute_latency_s": round(time.time() - started, 3),
        }
        rendered = render_turn(qq["q"], compiled, "lora9b", [])
        payload = {
            "arm": arm, "model": "merged-9b-002 audited responder",
            "protocol": "frozen benchmark plan -> deterministic connectors/executor -> LoRA-9B",
            "diagnostic_ceiling_not_end_to_end": True, "question_id": qq["id"],
            "question": qq["q"], "elapsed_wall_s": round(time.time() - started, 3),
            "status": execution.get("status"), "answer": rendered["answer"], "ir": plan,
            "execution": execution, "audit": rendered.get("audit"),
            "fallback": rendered.get("fallback"),
            "render_latency_s": rendered.get("render_latency_s"),
        }
    except Exception as exc:
        payload = {"arm": arm, "question_id": qq["id"], "question": qq["q"],
                   "elapsed_wall_s": round(time.time() - started, 3),
                   "error": repr(exc), "answer": ""}
    save(path, payload)
    return f"[{arm}] {qq['id']}: {payload['elapsed_wall_s']}s len={len(payload.get('answer',''))}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arms", default=",".join(ARMS[:3]))
    parser.add_argument("--questions", default="Q1,Q2,Q3,Q4,Q5")
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    arms = [x.strip() for x in args.arms.split(",") if x.strip()]
    unknown = sorted(set(arms) - set(ARMS))
    if unknown:
        raise SystemExit(f"unknown arms: {unknown}")
    wanted = {x.strip() for x in args.questions.split(",") if x.strip()}
    questions = [q for q in BANK if q["id"] in wanted]
    jobs = [(arm, q) for arm in arms for q in questions]

    def run(job: tuple[str, dict]) -> str:
        arm, qq = job
        if arm == "gemini-flash-agent":
            return gemini(qq, args.force)
        if arm == "deepseek-v4-web":
            return deepseek_web(qq, args.force)
        if arm == "ecology-mech-bind-lora9":
            return mech_bind_lora9(qq, args.force)
        return stack(qq, args.force, lora=(arm == "ecology-stack-lora9"))

    # Local stack calls share model servers; keep those sequential. Web/agent arms can overlap.
    remote = [job for job in jobs if not job[0].startswith("ecology-")]
    local = [job for job in jobs if job[0].startswith("ecology-")]
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
        futures = [pool.submit(run, job) for job in remote]
        for future in as_completed(futures):
            print(future.result(), flush=True)
    for job in local:
        print(run(job), flush=True)


if __name__ == "__main__":
    main()
