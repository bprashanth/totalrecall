#!/usr/bin/env python3
"""Acquire one immutable Dryad dataset version with an auditable manifest.

Credentials are read from a user-owned JSON file and are never copied to the
output. The connector checks path safety, advertised byte size and SHA-256.
Dryad occasionally advertises the empty-file digest for a non-empty object; the
caller must explicitly acknowledge that anomaly and the local manifest records
it rather than silently accepting the mismatch.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any


API_ROOT = "https://datadryad.org"
EMPTY_SHA256 = hashlib.sha256(b"").hexdigest()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, file_pointer, code, message, headers, new_url):
        return None


def _request_json(path: str, token: str) -> dict[str, Any]:
    request = urllib.request.Request(
        urllib.parse.urljoin(API_ROOT, path),
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "totalrecall-site-pack-connector/0.1",
        },
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return json.load(response)


def _download(path: str, destination: pathlib.Path, token: str) -> tuple[int, str]:
    request = urllib.request.Request(
        urllib.parse.urljoin(API_ROOT, path),
        headers={
            "Accept": "application/octet-stream",
            "Authorization": f"Bearer {token}",
            "User-Agent": "totalrecall-site-pack-connector/0.1",
        },
    )
    try:
        response = urllib.request.build_opener(_NoRedirect).open(request, timeout=60)
    except urllib.error.HTTPError as error:
        if error.code not in {301, 302, 303, 307, 308}:
            raise
        redirect = error.headers.get("Location")
        error.close()
        if not redirect or urllib.parse.urlparse(redirect).scheme != "https":
            raise RuntimeError("Dryad returned an unsafe or missing download redirect")
        # The redirect is a pre-signed object URL. Forwarding Dryad's bearer
        # header changes the signed request and can produce a 400 response.
        response = urllib.request.urlopen(
            urllib.request.Request(
                redirect,
                headers={"User-Agent": "totalrecall-site-pack-connector/0.1"},
            ),
            timeout=180,
        )
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    size = 0
    with response:
        with temporary.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
    os.replace(temporary, destination)
    return size, digest.hexdigest()


def acquire(
    doi: str,
    output_dir: pathlib.Path,
    token_file: pathlib.Path,
    *,
    allow_known_digest_anomaly: bool,
) -> dict[str, Any]:
    credentials = json.loads(token_file.expanduser().read_text(encoding="utf-8"))
    token = str(credentials.get("token") or "").strip()
    if not token:
        raise ValueError(f"Dryad token missing from {token_file}")
    identifier = doi if doi.startswith("doi:") else f"doi:{doi}"
    encoded = urllib.parse.quote(identifier, safe="")
    dataset = _request_json(f"/api/v2/datasets/{encoded}", token)
    version_path = dataset["_links"]["stash:version"]["href"]
    version = _request_json(version_path, token)
    files_path = version["_links"]["stash:files"]["href"]
    files_response = _request_json(files_path, token)
    files = files_response["_embedded"]["stash:files"]
    output_dir.mkdir(parents=True, exist_ok=True)
    report_files = []
    fatal_mismatches = []
    for item in files:
        relative = pathlib.PurePosixPath(item["path"])
        if relative.is_absolute() or ".." in relative.parts or len(relative.parts) != 1:
            raise ValueError(f"unsafe Dryad file path: {item['path']!r}")
        destination = output_dir / relative.name
        actual_size, actual_sha256 = _download(
            item["_links"]["stash:download"]["href"], destination, token
        )
        advertised_size = int(item["size"])
        advertised_sha256 = str(item.get("digest") or "")
        size_matches = actual_size == advertised_size
        digest_matches = actual_sha256 == advertised_sha256
        known_anomaly = (
            advertised_size > 0
            and advertised_sha256 == EMPTY_SHA256
            and actual_size == advertised_size
        )
        if not size_matches or (
            not digest_matches
            and not (known_anomaly and allow_known_digest_anomaly)
        ):
            fatal_mismatches.append(relative.name)
        report_files.append({
            "path": relative.name,
            "api_file_id": item["_links"]["self"]["href"].rsplit("/", 1)[-1],
            "media_type": item.get("mimeType"),
            "advertised_size": advertised_size,
            "actual_size": actual_size,
            "size_matches": size_matches,
            "advertised_sha256": advertised_sha256,
            "actual_sha256": actual_sha256,
            "digest_matches": digest_matches,
            "known_nonempty_empty_digest_anomaly": known_anomaly,
        })
    manifest = {
        "schema_version": "dryad-acquisition/0.1",
        "acquired_at": datetime.now(timezone.utc).isoformat(),
        "identifier": dataset["identifier"],
        "title": dataset["title"],
        "dataset_id": dataset["id"],
        "version_id": int(version_path.rstrip("/").rsplit("/", 1)[-1]),
        "version_number": dataset.get("versionNumber"),
        "publication_date": dataset.get("publicationDate"),
        "license": dataset.get("license"),
        "related_works": dataset.get("relatedWorks", []),
        "files": report_files,
        "integrity": "accepted_with_documented_api_anomaly" if any(
            item["known_nonempty_empty_digest_anomaly"] and not item["digest_matches"]
            for item in report_files
        ) else "verified",
        "credential_material_in_output": False,
    }
    manifest_path = output_dir / "ACQUISITION.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    if fatal_mismatches:
        raise RuntimeError(
            "download integrity failed for: " + ", ".join(fatal_mismatches)
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--doi", required=True)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument(
        "--token-file",
        type=pathlib.Path,
        default=pathlib.Path("~/.config/idlisseus/dryad_token.json"),
    )
    parser.add_argument("--allow-known-digest-anomaly", action="store_true")
    args = parser.parse_args()
    manifest = acquire(
        args.doi,
        args.output_dir,
        args.token_file,
        allow_known_digest_anomaly=args.allow_known_digest_anomaly,
    )
    print(json.dumps({
        "identifier": manifest["identifier"],
        "version_id": manifest["version_id"],
        "files": len(manifest["files"]),
        "integrity": manifest["integrity"],
    }, indent=2))


if __name__ == "__main__":
    main()
