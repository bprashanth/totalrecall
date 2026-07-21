#!/usr/bin/env python3
"""Redact secret-shaped strings embedded in retained third-party web/tool payloads."""

from __future__ import annotations

import re
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOTS = (HERE / "runs", HERE / "transport-failures")
RULES = (
    (re.compile(r"(?i)sk-[a-z0-9_-]{12,}"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(bearer\s+)[a-z0-9._-]{12,}"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(authorization[\"']?\s*[:=]\s*[\"']?)(?!\[REDACTED_TOKEN\])[^\s\"']{8,}"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*[\"']?)(?!\[REDACTED_TOKEN\])[^\s\"',&]{8,}"), r"\1[REDACTED_TOKEN]"),
)


def main() -> None:
    files = replacements = 0

    def clean(value: object) -> object:
        nonlocal replacements
        if isinstance(value, dict):
            return {key: clean(item) for key, item in value.items()}
        if isinstance(value, list):
            return [clean(item) for item in value]
        if not isinstance(value, str):
            return value
        text = value
        for pattern, replacement in RULES:
            text, count = pattern.subn(replacement, text)
            replacements += count
        return text

    for root in ROOTS:
        for path in root.rglob("*.json"):
            original = json.loads(path.read_text(errors="strict"))
            sanitized = clean(original)
            if sanitized != original:
                path.write_text(json.dumps(sanitized, indent=2, ensure_ascii=False) + "\n")
                files += 1
    print(f"redacted {replacements} secret-shaped strings in {files} retained trace files")


if __name__ == "__main__":
    main()
