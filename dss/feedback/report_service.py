#!/usr/bin/env python3
"""Draft and explicitly submit public issue reports without leaking private model context.

The browser may provide the visible user/assistant transcript. The bridge can also reconstruct
that same surface from its audit log. Raw prompts, tool output, hidden context and credentials are
never included. Drafting is always local and immutable; submission requires a separate call with
``confirmed=true``.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import tempfile
import urllib.parse
import urllib.request
from typing import Any


SCHEMA_VERSION = "idli-problem-report/1"
MAX_DESCRIPTION_CHARS = 8_000
MAX_TRANSCRIPT_CHARS = 80_000
SECRET = re.compile(
    r"(?i)(bearer\s+|(?:api[_ -]?key|token|secret|password)\s*[:=]\s*)"
    r"([A-Za-z0-9._~+/-]{12,})"
)
IDLISSEUS_MARKER = re.compile(
    r"<!--\s*idli-(?:result|progress|activity|answer-check):.*?-->",
    flags=re.IGNORECASE | re.DOTALL,
)


def _clean(value: Any, limit: int) -> str:
    text = " ".join(str(value or "").split())
    return SECRET.sub(r"\1[redacted]", text)[:limit]


def _multiline(value: Any, limit: int) -> str:
    text = IDLISSEUS_MARKER.sub("", str(value or "").replace("\x00", ""))
    return SECRET.sub(r"\1[redacted]", text).strip()[:limit]


def _atomic_write_once(path: pathlib.Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def visible_transcript_from_audit(path: pathlib.Path) -> list[dict[str, str]]:
    """Read only the messages a person sent and the final answers they were shown."""
    transcript: list[dict[str, str]] = []
    if not path.is_file():
        return transcript
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "request":
            content = _multiline(event.get("message"), MAX_TRANSCRIPT_CHARS)
            role = "user"
        elif event.get("type") == "final":
            content = _multiline(event.get("answer"), MAX_TRANSCRIPT_CHARS)
            role = "assistant"
        else:
            continue
        if content:
            transcript.append({"role": role, "content": content})
    return transcript


def normalise_transcript(value: Any) -> list[dict[str, str]]:
    """Accept only the visible roles and bounded string content supplied by the consumer."""
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("transcript must be a list of visible user/assistant messages")
    result: list[dict[str, str]] = []
    remaining = MAX_TRANSCRIPT_CHARS
    for item in value:
        if not isinstance(item, dict) or item.get("role") not in {"user", "assistant"}:
            raise ValueError("transcript entries must have role user or assistant")
        content = _multiline(item.get("content"), remaining)
        if content:
            result.append({"role": item["role"], "content": content})
            remaining -= len(content)
        if remaining <= 0:
            break
    return result


def _transcript_markdown(transcript: list[dict[str, str]]) -> str:
    sections = []
    for item in transcript:
        speaker = "User" if item["role"] == "user" else "Assistant"
        sections.append(f"#### {speaker}\n\n{item['content']}")
    return "\n\n".join(sections)


class ReportService:
    """Local drafts plus a configurable GitHub issue submission boundary."""

    def __init__(
        self, state_root: pathlib.Path, config: dict[str, Any] | None = None,
    ):
        self.state_root = pathlib.Path(state_root).resolve()
        self.config = dict(config or {})
        self.repository = _clean(
            self.config.get("repository") or "bprashanth/totalrecall", 200
        )
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", self.repository):
            raise ValueError("feedback repository must be owner/name")
        self.web_url = str(
            self.config.get("web_url") or "https://github.com"
        ).rstrip("/")
        self.api_url = str(
            self.config.get("api_url") or "https://api.github.com"
        ).rstrip("/")
        self.token_file = pathlib.Path(str(self.config.get("token_file"))).expanduser() \
            if self.config.get("token_file") else None
        self.labels = [
            _clean(item, 100) for item in (self.config.get("labels") or ["user-report"])
            if _clean(item, 100)
        ][:10]

    def _path(self, report_id: str) -> pathlib.Path:
        if not re.fullmatch(r"report-[a-f0-9]{24}", report_id):
            raise ValueError("invalid report id")
        return self.state_root / "feedback" / "drafts" / f"{report_id}.json"

    def draft(
        self, *, session_id: str, turn: int | None, description: Any,
        include_conversation: bool, transcript: Any = None,
        audit_path: pathlib.Path | None = None, diagnostics: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        description = _multiline(description, MAX_DESCRIPTION_CHARS)
        if not description:
            raise ValueError("a problem description is required")
        messages = normalise_transcript(transcript)
        if include_conversation and not messages and audit_path is not None:
            messages = visible_transcript_from_audit(audit_path)
        if not include_conversation:
            messages = []
        safe_diagnostics = {
            str(key): _clean(value, 500)
            for key, value in (diagnostics or {}).items()
            if value not in (None, "", [], {})
        }
        created_at = dt.datetime.now(dt.timezone.utc).isoformat()
        identity = {
            "repository": self.repository, "session_id": _clean(session_id, 120),
            "turn": int(turn) if turn is not None else None,
            "description": description, "include_conversation": include_conversation,
            "transcript": messages, "diagnostics": safe_diagnostics,
            "created_at": created_at,
        }
        report_id = "report-" + hashlib.sha256(
            json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()[:24]
        title_line = next(
            (line.strip() for line in description.splitlines() if line.strip()),
            "Problem report",
        )
        title = f"User report: {title_line}"[:180]
        body = (
            "## What happened\n\n" + description
            + "\n\n## Context\n\n"
            + f"- Audit id: `{identity['session_id']}/{identity['turn']}`\n"
            + "- Submitted from the visual assistant\n"
        )
        if safe_diagnostics:
            body += "\n## Diagnostics\n\n" + "\n".join(
                f"- {key}: `{value}`" for key, value in safe_diagnostics.items()
            ) + "\n"
        if messages:
            body += (
                "\n## Conversation included by the reporter\n\n"
                + _transcript_markdown(messages)
                + "\n"
            )
        draft = {
            "schema_version": SCHEMA_VERSION,
            "report_id": report_id,
            "status": "draft",
            "repository": self.repository,
            "public_warning": (
                f"This will create a public issue in {self.repository}. "
                "Review the preview and remove sensitive information before submitting."
            ),
            "include_conversation": bool(include_conversation),
            "conversation_messages": len(messages),
            "title": title,
            "body": body,
            "labels": self.labels,
            "created_at": created_at,
            "requires_confirmation": True,
        }
        _atomic_write_once(self._path(report_id), draft)
        return draft

    def load(self, report_id: str) -> dict[str, Any]:
        try:
            value = json.loads(self._path(report_id).read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise LookupError("report draft not found") from exc
        return value

    def submit(self, report_id: str, *, confirmed: bool) -> dict[str, Any]:
        if confirmed is not True:
            raise PermissionError("explicit confirmed=true is required before public submission")
        draft = self.load(report_id)
        token = ""
        if self.token_file:
            try:
                token = self.token_file.read_text(encoding="utf-8").strip()
            except OSError:
                token = ""
        if not token:
            query = urllib.parse.urlencode({
                "title": draft["title"], "body": draft["body"],
            })
            return {
                "schema_version": SCHEMA_VERSION,
                "report_id": report_id,
                "status": "ready_for_browser_confirmation",
                "url": f"{self.web_url}/{self.repository}/issues/new?{query}",
                "submitted": False,
                "reason": "No issue API token is configured; open the prefilled public issue.",
            }
        request = urllib.request.Request(
            f"{self.api_url}/repos/{self.repository}/issues",
            data=json.dumps({
                "title": draft["title"], "body": draft["body"],
                "labels": draft["labels"],
            }).encode(),
            headers={
                "Accept": "application/vnd.github+json",
                "Authorization": "Bearer " + token,
                "Content-Type": "application/json",
                "User-Agent": "totalrecall-problem-report/1",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            created = json.loads(response.read().decode("utf-8"))
        submitted = {
            "schema_version": SCHEMA_VERSION,
            "report_id": report_id,
            "status": "submitted",
            "submitted": True,
            "url": created.get("html_url"),
            "issue_number": created.get("number"),
            "repository": self.repository,
        }
        submitted_path = (
            self.state_root / "feedback" / "submitted" / f"{report_id}.json"
        )
        _atomic_write_once(submitted_path, submitted)
        return submitted
