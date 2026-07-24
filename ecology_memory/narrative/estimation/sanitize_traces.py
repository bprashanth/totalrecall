#!/usr/bin/env python3
"""Redact secret-shaped strings embedded in retained third-party web/tool payloads."""

from __future__ import annotations

import re
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOTS = (HERE / "runs", HERE / "judge-drafts", HERE / "transport-failures")
RULES = (
    (re.compile(r"AIza[0-9A-Za-z_-]{30,50}"), "[REDACTED_GOOGLE_API_KEY]"),
    (re.compile(r"(?i)sk-[a-z0-9_-]{12,}"), "[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(bearer\s+)[a-z0-9._-]{12,}"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(authorization[\"']?\s*[:=]\s*[\"']?)(?!\[REDACTED_TOKEN\])[^\s\"']{8,}"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*[\"']?)(?!\[REDACTED_)[^\s\"',&]{8,}"), r"\1[REDACTED_TOKEN]"),
    (re.compile(r"(?i)([?&](?:api[_-]?)?key=)(?!\[REDACTED_)[^&\s\"']{8,}"), r"\1[REDACTED_TOKEN]"),
)


def sanitize_value(value: object) -> tuple[object, int]:
    """Return a recursively redacted JSON value and its replacement count."""
    replacements = 0

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

    return clean(value), replacements


def main() -> None:
    files = replacements = 0
    for root in ROOTS:
        for path in root.rglob("*.json"):
            original = json.loads(path.read_text(errors="strict"))
            sanitized, count = sanitize_value(original)
            replacements += count
            if sanitized != original:
                path.write_text(json.dumps(sanitized, indent=2, ensure_ascii=False) + "\n")
                files += 1
    print(f"redacted {replacements} secret-shaped strings in {files} retained trace files")


if __name__ == "__main__":
    main()
