#!/usr/bin/env python3
"""Write a hash inventory for the read-only origin assets admitted to integration review."""
import datetime as dt
import glob
import hashlib
import json
import os
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
INTEGRATION = os.path.dirname(HERE)
ORIGIN = os.environ.get(
    "IDLISSEUS_ROOT", "/home/beeps/src/github.com/bprashanth/idlisseus")
OUT = os.path.join(INTEGRATION, "manifests", "origin-lock.json")

EXACT = [
    "agents/hermes/chat.sh",
    "agents/hermes/SOUL.md",
    "agents/hermes/config.yaml.reference",
    "dss/ARCHITECTURE.md",
    "dss/DATA_STRATEGIES.md",
    "dss/connectors/PLAYBOOK.md",
    "dss/connectors/PHILOSOPHY.md",
]
PATTERNS = [
    "dss/connectors/*.py",
    "dss/connectors/*.md",
    "dss/connectors/*.json",
    "dss/corpus/*.jsonl",
    "dss/corpus/README.md",
    "dss/queries/data/**/*",
]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args):
    return subprocess.check_output(["git", "-C", ORIGIN, *args], text=True).strip()


def main():
    rels = set(EXACT)
    for pattern in PATTERNS:
        for path in glob.glob(os.path.join(ORIGIN, pattern), recursive=True):
            if os.path.isfile(path):
                rels.add(os.path.relpath(path, ORIGIN))
    files = {}
    missing = []
    for rel in sorted(rels):
        path = os.path.join(ORIGIN, rel)
        if not os.path.isfile(path):
            missing.append(rel)
            continue
        files[rel] = {"sha256": digest(path), "bytes": os.path.getsize(path)}
    manifest = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "origin_root": ORIGIN,
        "origin_commit": git("rev-parse", "HEAD"),
        "origin_dirty": bool(git("status", "--porcelain")),
        "policy": "reference-only allowlist; no secrets, caches, mutable ledgers, or commercial artifacts",
        "files": files,
        "missing": missing,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as stream:
        json.dump(manifest, stream, indent=2)
        stream.write("\n")
    print(f"locked {len(files)} origin assets at {manifest['origin_commit'][:12]} -> {OUT}")


if __name__ == "__main__":
    main()
