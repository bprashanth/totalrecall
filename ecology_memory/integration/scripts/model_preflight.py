#!/usr/bin/env python3
"""Fail before Hermes starts when a requested local model is not actually served."""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request


LOCAL_IDS = {
    "qwen2b": "qwen3.5-2b",
    "2b": "qwen3.5-2b",
    "qwen2b-lora": "qwen3.5-2b-lora",
    "2b-lora": "qwen3.5-2b-lora",
    "loravb": "qwen3.5-2b-lora",
    "lora9b": "m",
    "9b-lora": "m",
    "merged-9b-002": "m",
}

LOCAL_BASES = {
    "lora9b": "http://172.17.0.1:8007/v1",
    "9b-lora": "http://172.17.0.1:8007/v1",
    "merged-9b-002": "http://172.17.0.1:8007/v1",
}


def served_models(base_url):
    request = urllib.request.Request(base_url.rstrip("/") + "/models")
    with urllib.request.urlopen(request, timeout=5) as response:
        payload = json.load(response)
    return sorted(item.get("id") for item in payload.get("data", []) if item.get("id"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--base-url")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    wanted = LOCAL_IDS.get(args.model)
    if not wanted:
        return 0
    try:
        base_url = args.base_url or os.environ.get("DSS_LOCAL_OPENAI_BASE") or \
            LOCAL_BASES.get(args.model, "http://172.17.0.1:8001/v1")
        available = served_models(base_url)
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError) as exc:
        print(f"chat.sh: local model preflight failed before chat: {exc}", file=sys.stderr)
        return 2
    if wanted not in available:
        have = ", ".join(available) if available else "none"
        print(
            f"chat.sh: model {wanted!r} is not deployed; available local models: {have}. "
            "No Hermes session was started.",
            file=sys.stderr,
        )
        return 2
    if not args.quiet:
        print(f"local model ready: {wanted}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
