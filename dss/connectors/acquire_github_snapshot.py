#!/usr/bin/env python3
"""Acquire selected files from one immutable GitHub commit archive."""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import io
import json
import os
import pathlib
import re
import tarfile
import urllib.request
from datetime import datetime, timezone
from typing import Any


GITHUB_REPOSITORY = re.compile(
    r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$"
)
COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _download(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "totalrecall-site-pack-connector/0.1"}
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return response.read()


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _selected(relative: pathlib.PurePosixPath, patterns: list[str]) -> bool:
    name = relative.as_posix()
    return any(fnmatch.fnmatchcase(name, pattern) for pattern in patterns)


def acquire(
    repository_url: str,
    commit: str,
    patterns: list[str],
    output_dir: pathlib.Path,
) -> dict[str, Any]:
    match = GITHUB_REPOSITORY.fullmatch(repository_url)
    if not match:
        raise ValueError("repository must be an https://github.com/OWNER/REPO URL")
    if not COMMIT.fullmatch(commit):
        raise ValueError("commit must be a full lowercase SHA-1")
    if not patterns or any(
        pathlib.PurePosixPath(pattern).is_absolute() or ".." in pathlib.PurePosixPath(pattern).parts
        for pattern in patterns
    ):
        raise ValueError("one or more safe relative include patterns are required")
    owner, repository = match.groups()
    archive_url = (
        f"https://codeload.github.com/{owner}/{repository}/tar.gz/{commit}"
    )
    archive = _download(archive_url)
    output_dir.mkdir(parents=True, exist_ok=True)
    selected_files: list[dict[str, Any]] = []
    matched_patterns: set[str] = set()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
        members = bundle.getmembers()
        roots = {
            pathlib.PurePosixPath(member.name).parts[0]
            for member in members if pathlib.PurePosixPath(member.name).parts
        }
        if len(roots) != 1:
            raise ValueError("GitHub archive does not have one root directory")
        root = next(iter(roots))
        for member in members:
            path = pathlib.PurePosixPath(member.name)
            if not path.parts or path.parts[0] != root or len(path.parts) == 1:
                continue
            relative = pathlib.PurePosixPath(*path.parts[1:])
            matching = [
                pattern for pattern in patterns
                if fnmatch.fnmatchcase(relative.as_posix(), pattern)
            ]
            if not matching:
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(f"selected archive member is not a regular file: {relative}")
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"unsafe archive member: {relative}")
            extracted = bundle.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"could not read archive member: {relative}")
            content = extracted.read()
            destination = output_dir.joinpath(*relative.parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            temporary = destination.with_suffix(destination.suffix + ".part")
            temporary.write_bytes(content)
            os.replace(temporary, destination)
            selected_files.append({
                "path": relative.as_posix(),
                "bytes": len(content),
                "sha256": _sha256(content),
            })
            matched_patterns.update(matching)
    unmatched = sorted(set(patterns) - matched_patterns)
    if unmatched:
        raise RuntimeError("include patterns matched no files: " + ", ".join(unmatched))
    manifest = {
        "schema_version": "github-snapshot-acquisition/0.1",
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "repository_url": repository_url,
        "commit": commit,
        "archive_url": archive_url,
        "archive_sha256": _sha256(archive),
        "include_patterns": patterns,
        "files": sorted(selected_files, key=lambda item: item["path"]),
        "integrity": "verified",
    }
    (output_dir / "ACQUISITION.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--include", action="append", required=True)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    manifest = acquire(
        args.repository, args.commit, args.include, args.output_dir
    )
    print(json.dumps({
        "repository_url": manifest["repository_url"],
        "commit": manifest["commit"],
        "files": len(manifest["files"]),
        "bytes": sum(item["bytes"] for item in manifest["files"]),
        "integrity": manifest["integrity"],
    }, indent=2))


if __name__ == "__main__":
    main()
