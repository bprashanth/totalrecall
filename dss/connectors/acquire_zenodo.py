#!/usr/bin/env python3
"""Acquire and verify all files from one immutable Zenodo record."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import urllib.request
from datetime import datetime, timezone
from typing import Any


def _json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "totalrecall-site-pack-connector/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _download(url: str, destination: pathlib.Path) -> tuple[int, str, str]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "totalrecall-site-pack-connector/0.1"}
    )
    temporary = destination.with_suffix(destination.suffix + ".part")
    sha256 = hashlib.sha256()
    md5 = hashlib.md5(usedforsecurity=False)
    size = 0
    with urllib.request.urlopen(request, timeout=180) as response:
        with temporary.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                sha256.update(chunk)
                md5.update(chunk)
                size += len(chunk)
    os.replace(temporary, destination)
    return size, sha256.hexdigest(), md5.hexdigest()


def acquire(record_id: int, output_dir: pathlib.Path) -> dict[str, Any]:
    record = _json(f"https://zenodo.org/api/records/{record_id}")
    output_dir.mkdir(parents=True, exist_ok=True)
    files = []
    failures = []
    for item in record.get("files", []):
        relative = pathlib.PurePosixPath(item["key"])
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
            raise ValueError(f"unsafe Zenodo file path: {item['key']!r}")
        destination = output_dir / relative.name
        size, sha256, md5 = _download(item["links"]["self"], destination)
        advertised_checksum = str(item.get("checksum") or "")
        checksum_matches = advertised_checksum == f"md5:{md5}"
        size_matches = size == int(item["size"])
        if not checksum_matches or not size_matches:
            failures.append(relative.name)
        files.append({
            "path": relative.name,
            "file_id": item["id"],
            "advertised_size": int(item["size"]),
            "actual_size": size,
            "size_matches": size_matches,
            "advertised_checksum": advertised_checksum,
            "actual_md5": md5,
            "checksum_matches": checksum_matches,
            "actual_sha256": sha256,
        })
    metadata = record["metadata"]
    manifest = {
        "schema_version": "zenodo-acquisition/0.1",
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "record_id": record["id"],
        "concept_record_id": record.get("conceptrecid"),
        "doi": record.get("doi"),
        "title": metadata.get("title"),
        "publication_date": metadata.get("publication_date"),
        "license": (metadata.get("license") or {}).get("id"),
        "resource_type": (metadata.get("resource_type") or {}).get("type"),
        "related_identifiers": metadata.get("related_identifiers", []),
        "files": files,
        "integrity": "verified" if not failures else "failed",
    }
    (output_dir / "ACQUISITION.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if failures:
        raise RuntimeError("download integrity failed for: " + ", ".join(failures))
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--record-id", required=True, type=int)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    args = parser.parse_args()
    manifest = acquire(args.record_id, args.output_dir)
    print(json.dumps({
        "record_id": manifest["record_id"],
        "doi": manifest["doi"],
        "files": len(manifest["files"]),
        "integrity": manifest["integrity"],
    }, indent=2))


if __name__ == "__main__":
    main()
