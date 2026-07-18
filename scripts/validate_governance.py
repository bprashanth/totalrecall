#!/usr/bin/env python3
"""Validate framework proposal and release registries without third-party dependencies."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ALLOWED_STATES = {
    "proposed", "deferred", "rejected", "accepted", "accepted-conditional",
    "rfc-required", "implemented", "validated",
}


def load(relative: str):
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    registry = load("governance/proposals.json")
    manifest = load("governance/framework-manifest.json")
    proposals = registry.get("proposals", [])
    ids = [item.get("id") for item in proposals]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate proposal ID")
    by_id = {item["id"]: item for item in proposals}
    for item in proposals:
        missing = {"id", "title", "scope", "status", "source", "required_tests"} - item.keys()
        if missing:
            raise SystemExit(f"{item.get('id', '<unknown>')}: missing {sorted(missing)}")
        if item["status"] not in ALLOWED_STATES:
            raise SystemExit(f"{item['id']}: invalid state {item['status']}")
        if not item["required_tests"]:
            raise SystemExit(f"{item['id']}: no required tests")
    for proposal_id in manifest.get("released_proposals", []):
        item = by_id.get(proposal_id)
        if item is None:
            raise SystemExit(f"manifest references unknown proposal {proposal_id}")
        if item["status"] != "validated":
            raise SystemExit(f"manifest releases non-validated proposal {proposal_id}")
    required_artifacts = [
        "governance/reviews/codex-round2.md",
        "governance/reviews/fable-import-20260713.md",
        "governance/decisions/20260713-round2.md",
        "kit/SATURATION.md",
    ]
    for relative in required_artifacts:
        if not (ROOT / relative).is_file():
            raise SystemExit(f"missing governance artifact {relative}")
    print(f"governance valid: {len(proposals)} proposals, {len(manifest['released_proposals'])} released")


if __name__ == "__main__":
    main()
