#!/usr/bin/env python3
"""Meena-style turn-by-turn conversational bench for the Idlisseus visual data assistant.

One conversation is one chat session. The codex_native bridge keeps a resumable Codex thread per
caller-supplied session id, so continuity is bought by sending the same `session_id` on every POST
to `/v1/chat/completions` and sending only the current user turn -- the bridge holds the history,
not the client. Sending a replayed message array would double the context and still not resume the
thread, which is why this harness deliberately sends one message per request.

Usage:

    python bench.py --run-id before-skill-change
    python bench.py --only c4-estimate --run-id spot-check

Each run writes `runs/<run-id>/transcript.json`, `graded.json` and a RESULTS.md, and refreshes the
top-level RESULTS.md with the newest run.
"""

from __future__ import annotations

import argparse
import datetime
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

import grader

HERE = pathlib.Path(__file__).resolve().parent
REPO = HERE.parent.parent
DEFAULT_BASE = "http://172.17.0.1:7013"
DEFAULT_TOKEN = REPO / "runs" / "insight-valparai-livelihoods" / ".api-token"


def post_turn(base_url: str, token: str, model: str, session_id: str, message: str,
              timeout: int) -> tuple[str, dict, float]:
    """Send one user turn into an existing session and return (answer, audit, latency)."""
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


def run(spec: dict, args: argparse.Namespace, token: str) -> dict:
    conversations = spec["conversations"]
    if args.only:
        wanted = set(args.only)
        conversations = [c for c in conversations if c["id"] in wanted]
    budget = args.max_turns
    planned = sum(min(len(c["turns"]), args.turns_per_conversation or len(c["turns"]))
                  for c in conversations)
    if planned > budget:
        raise SystemExit(f"planned {planned} turns exceeds the {budget}-turn guard; "
                         "narrow with --only or raise --max-turns deliberately")

    started = datetime.datetime.now().astimezone().isoformat(timespec="seconds")
    out: dict = {
        "run": {
            "run_id": args.run_id,
            "started": started,
            "base_url": args.base_url,
            "model": args.model,
            "site": spec.get("site"),
            "turns_planned": planned,
        },
        "conversations": [],
    }
    spent = 0
    for conv in conversations:
        session_id = f"vcbench-{args.run_id}-{conv['id']}"
        record = {"id": conv["id"], "session_id": session_id, "turns": []}
        turns = conv["turns"]
        if args.turns_per_conversation:
            turns = turns[: args.turns_per_conversation]
        for turn in turns:
            if spent >= budget:
                break
            print(f"[{conv['id']}/{turn['id']}] {turn['user'][:70]}", file=sys.stderr, flush=True)
            try:
                answer, audit, latency = post_turn(
                    args.base_url, token, args.model, session_id, turn["user"], args.timeout)
            except Exception as exc:  # a bridge failure is a bench result, not a crash
                print(f"  !! {type(exc).__name__}: {exc}", file=sys.stderr)
                record["turns"].append({
                    "id": turn["id"], "user": turn["user"], "answer": "",
                    "error": f"{type(exc).__name__}: {exc}", "latency_s": None,
                })
                spent += 1
                continue
            spent += 1
            print(f"  <- {latency:.0f}s, {len(answer.split())} words", file=sys.stderr, flush=True)
            record["turns"].append({
                "id": turn["id"], "user": turn["user"], "answer": answer,
                "latency_s": round(latency, 2), "audit": audit,
            })
        out["conversations"].append(record)
    out["run"]["turns_spent"] = spent
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--conversations", type=pathlib.Path, default=HERE / "conversations.json")
    parser.add_argument("--base-url", default=DEFAULT_BASE)
    parser.add_argument("--token-file", type=pathlib.Path, default=DEFAULT_TOKEN)
    parser.add_argument("--model", default="idli-insight")
    parser.add_argument("--run-id", default=datetime.datetime.now().strftime("%Y%m%d-%H%M"))
    parser.add_argument("--only", nargs="*", default=None, help="conversation ids to run")
    parser.add_argument("--turns-per-conversation", type=int, default=0)
    parser.add_argument("--timeout", type=int, default=900)
    parser.add_argument("--max-turns", type=int, default=40,
                        help="cost guard: one full run must stay inside this many Codex turns")
    parser.add_argument("--grade-only", type=pathlib.Path, default=None,
                        help="skip the endpoint and grade an existing transcript")
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
