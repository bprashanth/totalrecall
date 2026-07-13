#!/usr/bin/env python3
"""Record exact Round-2 freeze-epoch checksums before blind holdouts."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = [
    "harness/parser.py", "harness/ir_schema.py", "harness/executor.py",
    "harness/connectors.py", "harness/scorer.py", "harness/synthesize.py",
    "harness/semantic_audit.py", "harness/synthesis_audit.py", "harness/multiturn.py",
    "harness/test_parser_regressions.py", "harness/coverage.py",
    "harness/compile_corpus.py", "harness/release_holdout.py", "harness/freeze.py",
]
BANKS = [
    "questions/seed.json", "questions/gen-001.json", "questions/gen-002-indirect.json",
    "questions/round2-dev.json", "questions/round2-neutral.json",
    "questions/round2-h1-dev.json", "questions/round2-h2-dev.json",
    "questions/round2-h3-dev.json", "questions/round2-h4-dev.json",
    "questions/round2-h5-dev.json",
    "questions/round2-h8-dev.json", "questions/round2-h9-dev.json",
    "questions/round2-h10-dev.json",
    "questions/round2-h11-dev.json", "questions/round2-h12-dev.json",
    "questions/round2-h13-dev.json", "questions/round2-h14-dev.json",
    "questions/round2-h15-dev.json", "questions/round2-h16-dev.json",
    "questions/round2-h17-dev.json", "questions/round2-h18-dev.json",
    "questions/round2-h19-dev.json", "questions/round2-h20-dev.json",
    "questions/round2-h21-dev.json", "questions/round2-h22-dev.json",
    "questions/round2-h23-dev.json", "questions/round2-h24-dev.json",
    "questions/round2-h25-dev.json",
    "questions/round2-breakers.json",
]
EVIDENCE = ["coverage/matrix.json", "coverage/source-census.json",
            "coverage/gold-defects.json",
            "coverage/epoch-011-certification.json", "coverage/epoch-012-certification.json",
            "coverage/epoch-013-certification.json", "coverage/epoch-014-certification.json"]
EVIDENCE.append("coverage/epoch-015-certification.json")
EVIDENCE.append("coverage/epoch-016-certification.json")
EVIDENCE.append("coverage/epoch-017-certification.json")
EVIDENCE.append("coverage/epoch-018-certification.json")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("epoch")
    ap.add_argument("--note", required=True)
    args = ap.parse_args()
    files = {}
    for rel in CORE + BANKS + EVIDENCE:
        path = ROOT / rel
        if not path.exists(): raise SystemExit(f"freeze input missing: {rel}")
        files[rel] = {"sha256": digest(path), "bytes": path.stat().st_size}
    payload = {"schema_version":"round2-freeze-v1", "epoch":args.epoch,
               "created_at":datetime.now(timezone.utc).isoformat(), "note":args.note,
               "holdout_policy":"Any core/prompt/repair/scorer/connector change invalidates all holdouts in this epoch.",
               "files":files}
    target=ROOT/"freezes"/f"{args.epoch}.json"; target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(payload,indent=2)+"\n")
    print(json.dumps({"epoch":args.epoch,"files":len(files),"manifest":str(target)},indent=2))


if __name__=="__main__": main()
