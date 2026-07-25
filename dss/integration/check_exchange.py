#!/usr/bin/env python3
"""List producer proposals beside Idlisseus-owned responses."""

from __future__ import annotations

import argparse
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_RESPONSES = ROOT.parent / "idlisseus" / "dss" / "integration" / "responses"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--responses", type=pathlib.Path, default=DEFAULT_RESPONSES)
    args = parser.parse_args()
    index_path = ROOT / "dss" / "integration" / "proposals" / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    exchange = []
    invalid = False
    for proposal in index["proposals"]:
        proposal_id = proposal["proposal_id"]
        response_path = args.responses / proposal_id / "response.json"
        response = None
        if response_path.is_file():
            response = json.loads(response_path.read_text(encoding="utf-8"))
            if response.get("proposal_id") != proposal_id:
                invalid = True
                response = {
                    "invalid": True,
                    "reason": "response proposal_id does not match its directory",
                    "path": str(response_path),
                }
        exchange.append({
            "proposal_id": proposal_id,
            "title": proposal["title"],
            "proposal_status": proposal["status"],
            "response": response,
        })
    print(json.dumps({
        "schema_version": "producer-consumer-exchange-status/1",
        "responses_root": str(args.responses),
        "proposals": exchange,
    }, indent=2, ensure_ascii=False))
    return 1 if invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
