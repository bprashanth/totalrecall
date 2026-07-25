#!/usr/bin/env python3
"""Multi-turn ecology bench against a live Valparai insight bridge.

One conversation is one chat session. The codex_native bridge keeps a resumable thread per
caller-supplied `session_id`, so continuity is bought by posting the same session id every turn and
sending only the current user message. Replaying the whole message array would double the context
and still not resume the thread.

Two things this harness does that the visual_conversation sibling does not:

* it reads the session's `audit.jsonl` after every turn and records which capability the bridge
  actually ran, so `right_tool` is graded on the tool trail rather than guessed from prose;
* it retries a turn when the bridge is restarting under it, and records that it did, because the
  bridge is being edited by someone else while this bench runs.

Usage:

    python bench.py --run-id round1
    python bench.py --only c3-lantana --run-id spot-check
    python bench.py --grade-only runs/round1/transcript.json --run-id round1
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime
import json
import pathlib
import re
import sys
import threading
import time
import urllib.error
import urllib.request

import grader

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_BASE = "http://172.17.0.1:7012"
DEFAULT_TOKEN = REPO / "runs" / "insight-valparai" / ".api-token"

PRINT_LOCK = threading.Lock()


def log(message: str) -> None:
    with PRINT_LOCK:
        print(message, file=sys.stderr, flush=True)


def post_turn(base_url: str, token: str, model: str, session_id: str, message: str,
              timeout: int) -> tuple[str, dict, float]:
    body = json.dumps({
        "model": model,
        "session_id": session_id,
        "messages": [{"role": "user", "content": message}],
    }).encode()
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:400]
        raise RuntimeError(f"HTTP {exc.code} from bridge: {detail}") from exc
    latency = time.time() - started
    answer = (payload.get("choices") or [{}])[0].get("message", {}).get("content") or ""
    return answer, payload.get("codex_audit") or {}, latency


def audit_events(audit: dict, turn_number: int | None) -> tuple[list[str], int]:
    """Read this turn's tool trail: which capabilities ran, and how many buttons were offered.

    The trail is the only honest record of routing: prose can describe a comparison while the
    orientation map is what actually ran. The button count matters because the bridge is told not
    to write a prose menu on the grounds that the interface renders one -- so whether a menu
    actually existed is a fact about the run, not about the wording.
    """
    path = audit.get("path")
    if not path:
        return [], 0
    audit_path = pathlib.Path(path)
    if not audit_path.is_absolute():
        audit_path = REPO / audit_path
    if not audit_path.exists():
        return [], 0
    turn = turn_number if turn_number is not None else audit.get("turn")
    used: list[str] = []
    buttons = 0
    try:
        lines = audit_path.read_text(errors="replace").splitlines()
    except OSError:
        return [], 0
    for line in lines:
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if turn is not None and event.get("turn") != turn:
            continue
        if event.get("type") == "skill_call":
            args = event.get("args") or {}
            capability = args.get("capability_id")
            if capability and capability not in used:
                used.append(capability)
            elif not capability:
                skill = event.get("skill")
                if skill and skill not in ("visual-result",) and skill not in used:
                    used.append(skill)
        elif event.get("type") == "tool_start" and event.get("kind") == "skill":
            command = str(event.get("command") or "")
            match = re.search(r'capability_id\\?":\\?"([a-z0-9-]+)', command)
            if match and match.group(1) not in used:
                used.append(match.group(1))
        elif event.get("type") == "insight_actions":
            buttons += len(event.get("options") or []) or 1
    return used, buttons


def run_conversation(conv: dict, args: argparse.Namespace, token: str,
                     limit: int | None) -> dict:
    session_id = f"ecoanr-{args.run_id}-{conv['id']}"
    record = {"id": conv["id"], "session_id": session_id, "turns": []}
    turns = conv["turns"][:limit] if limit else conv["turns"]
    for index, turn in enumerate(turns, start=1):
        log(f"[{conv['id']}/{turn['id']}] {turn['user'][:66]}")
        answer, audit, latency, error, retries = "", {}, None, None, 0
        for attempt in range(args.retries + 1):
            try:
                answer, audit, latency = post_turn(
                    args.base_url, token, args.model, session_id, turn["user"], args.timeout)
                error = None
                break
            except Exception as exc:  # a bridge restart mid-run is expected, not fatal
                error = f"{type(exc).__name__}: {exc}"
                retries = attempt + 1
                log(f"  !! {conv['id']}/{turn['id']} attempt {attempt + 1}: {error[:120]}")
                if attempt < args.retries:
                    time.sleep(args.retry_wait)
        entry = {"id": turn["id"], "user": turn["user"], "answer": answer,
                 "latency_s": round(latency, 2) if latency else None,
                 "retries": retries, "audit": audit}
        if error:
            entry["error"] = error
        else:
            entry["capabilities"], entry["action_buttons"] = audit_events(
                audit, audit.get("turn") or index)
            log(f"  <- {conv['id']}/{turn['id']} {latency:.0f}s, "
                f"{len(answer.split())} words, tools={entry['capabilities']}")
        record["turns"].append(entry)
        if args.pace:
            time.sleep(args.pace)
    return record


def run(spec: dict, args: argparse.Namespace, token: str) -> dict:
    conversations = spec["conversations"]
    if args.only:
        wanted = set(args.only)
        conversations = [c for c in conversations if c["id"] in wanted]
    limit = args.turns_per_conversation or None
    planned = sum(len(c["turns"][:limit] if limit else c["turns"]) for c in conversations)
    if planned > args.max_turns:
        raise SystemExit(f"planned {planned} turns exceeds the {args.max_turns}-turn guard")

    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    records: dict[str, dict] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_conversation, conv, args, token, limit): conv["id"]
                   for conv in conversations}
        for future in concurrent.futures.as_completed(futures):
            conv_id = futures[future]
            records[conv_id] = future.result()

    ordered = [records[c["id"]] for c in conversations if c["id"] in records]
    return {
        "run": {
            "run_id": args.run_id,
            "started": started,
            "finished": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
            "base_url": args.base_url,
            "model": args.model,
            "site": spec.get("site"),
            "workers": args.workers,
            "turns_planned": planned,
        },
        "conversations": ordered,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conversations", type=pathlib.Path, default=HERE / "conversations.json")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--token-file", type=pathlib.Path, default=DEFAULT_TOKEN)
    parser.add_argument("--model", default="idli-insight-valparai")
    parser.add_argument("--run-id", default=datetime.datetime.now().strftime("%Y%m%d-%H%M"))
    parser.add_argument("--only", nargs="*", default=None)
    parser.add_argument("--turns-per-conversation", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--workers", type=int, default=3)
    parser.add_argument("--pace", type=float, default=2.0,
                        help="seconds between turns inside one conversation")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--retry-wait", type=float, default=25.0)
    parser.add_argument("--max-turns", type=int, default=60)
    parser.add_argument("--grade-only", type=pathlib.Path, default=None)
    args = parser.parse_args(argv)

    spec = json.loads(args.conversations.read_text())
    out_dir = HERE / "runs" / args.run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.grade_only:
        transcript = json.loads(args.grade_only.read_text())
    else:
        token = args.token_file.read_text().strip()
        transcript = run(spec, args, token)
        (out_dir / "transcript.json").write_text(
            json.dumps(transcript, indent=2, ensure_ascii=False))

    graded = grader.grade_transcript(transcript, spec)
    (out_dir / "graded.json").write_text(json.dumps(graded, indent=2, ensure_ascii=False))
    results = grader.render_results(graded)
    (out_dir / "RESULTS.md").write_text(results)
    (HERE / "RESULTS.md").write_text(results)
    print(json.dumps(graded["summary"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
