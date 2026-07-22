#!/usr/bin/env python3
"""Live chat/step viewer for the Codex CLI + native-skills bridge."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


RESET = "\033[0m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
DIM = "\033[2m"
RED = "\033[31m"


def _paint(text: str, colour: str, enabled: bool) -> str:
    return f"{colour}{text}{RESET}" if enabled else text


def _sse(request: urllib.request.Request):
    with urllib.request.urlopen(request, timeout=900) as response:
        event_name = "message"
        for raw in response:
            line = raw.decode(errors="replace").rstrip("\r\n")
            if not line:
                event_name = "message"
                continue
            if line.startswith("event:"):
                event_name = line[6:].strip()
                continue
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if data == "[DONE]":
                return
            try:
                yield event_name, json.loads(data)
            except json.JSONDecodeError:
                yield event_name, data


def _direct_events(url: str, token: str, session: str, question: str):
    payload = json.dumps({
        "session_id": session,
        "messages": [{"role": "user", "content": question}],
        "stream": True,
    }).encode()
    request = urllib.request.Request(
        url.rstrip("/") + "/v1/audit/chat", data=payload,
        headers={"Content-Type": "application/json", "Authorization": "Bearer " + token},
    )
    yield from _sse(request)


def _idlisseus_events(url: str, token: str, session: str, question: str):
    payload = urllib.parse.urlencode({
        "session": session, "message": question, "mode": "chat",
        "allow_bash": "false", "allow_web_search": "false",
    }).encode()
    request = urllib.request.Request(
        url.rstrip("/") + "/api/chat_stream", data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded",
                 "Authorization": "Bearer " + token},
    )
    yield from _sse(request)


def _show_direct(event: dict, colour: bool) -> None:
    kind = event.get("type")
    if kind == "turn_start":
        print(_paint(f"\n╭─ Codex CLI · {event.get('model')} · native skills", CYAN, colour))
        print(_paint(f"│ audit: {event.get('audit_path')}", DIM, colour))
    elif kind == "status":
        print(_paint("│ codex  ", MAGENTA, colour) + str(event.get("text") or ""))
    elif kind == "tool_start":
        tool = event.get("tool") or event.get("kind")
        print(_paint(f"│ start  {tool}", YELLOW, colour))
    elif kind == "tool_output":
        tool = event.get("tool") or event.get("kind")
        output = str(event.get("output") or "").strip()
        suffix = f" → {output}" if output else ""
        print(_paint(f"│ done   {tool}{suffix}", GREEN, colour))
    elif kind == "error":
        print(_paint(f"│ error  {event.get('error')}", RED, colour))
    elif kind == "final":
        print(_paint("╰─ answer", CYAN, colour))
        print(event.get("answer") or "")
        print(_paint(
            f"\n{event.get('latency_s')}s · thread={event.get('thread_id')} · "
            f"audit={event.get('session_id')}/{event.get('turn')}", DIM, colour
        ))


def _show_idlisseus(event: dict | str, colour: bool) -> None:
    if not isinstance(event, dict):
        print(event, end="", flush=True)
        return
    if "delta" in event:
        print(event.get("delta") or "", end="", flush=True)
    elif event.get("type") == "metrics":
        metrics = event.get("data") or {}
        print(_paint(
            f"\n\n{metrics.get('response_time', '?')}s · "
            f"in={metrics.get('input_tokens', '?')} · out={metrics.get('output_tokens', '?')}",
            DIM, colour,
        ))
    elif event.get("type") == "message_saved":
        print(_paint(f"\nsaved message {event.get('id')}", DIM, colour))
    elif event.get("error"):
        print(_paint(f"\nerror: {event.get('error')}", RED, colour))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct", action="store_true",
                        help="call the local structured bridge instead of Idlisseus")
    parser.add_argument("--url", help="bridge or Idlisseus base URL")
    parser.add_argument("--token", help="API token (or matching environment variable)")
    parser.add_argument("--session", default="")
    parser.add_argument("--question")
    parser.add_argument("--color", choices=("auto", "always", "never"), default="auto")
    args = parser.parse_args(argv)
    colour = args.color == "always" or (args.color == "auto" and sys.stdout.isatty()
                                        and not os.environ.get("NO_COLOR"))
    if args.direct:
        url = args.url or os.environ.get("CODEX_NATIVE_URL", "http://127.0.0.1:7011")
        token = args.token or os.environ.get("CODEX_NATIVE_API_TOKEN", "")
        event_source = _direct_events
    else:
        url = args.url or os.environ.get("ODYSSEUS_URL", "http://127.0.0.1:7000")
        token = args.token or os.environ.get("ODYSSEUS_API_TOKEN", "")
        event_source = _idlisseus_events
    if not token:
        parser.error("set --token or the matching API-token environment variable")
    session = args.session or os.environ.get("ODYSSEUS_SESSION") or "codex-" + uuid.uuid4().hex[:12]
    print(_paint(f"session: {session}", DIM, colour))

    questions = [args.question] if args.question else None
    while True:
        if questions is not None:
            if not questions:
                break
            question = questions.pop(0)
            print(_paint("\nYou: ", CYAN, colour) + question)
        else:
            try:
                question = input(_paint("\nYou: ", CYAN, colour)).strip()
            except EOFError:
                break
            if not question:
                continue
            if question in {"/quit", "/exit"}:
                break
        try:
            for _, event in event_source(url, token, session, question):
                if args.direct:
                    if isinstance(event, dict):
                        _show_direct(event, colour)
                else:
                    _show_idlisseus(event, colour)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            print(_paint(f"HTTP {exc.code}: {detail}", RED, colour), file=sys.stderr)
            return 1
        except urllib.error.URLError as exc:
            print(_paint(f"Connection failed: {exc}", RED, colour), file=sys.stderr)
            return 1
        if questions is not None:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
