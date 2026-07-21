#!/usr/bin/env python3
"""Validate and package the execution-admitted ecology corpus for Fable."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
ECOLOGY = ROOT / "ecology_memory"
KIT = ROOT / "kit"
sys.path.insert(0, str(ECOLOGY / "harness"))
from ir_schema import validate as validate_ecology  # noqa: E402


def load_kit_validator():
    path = KIT / "harness" / "ir_schema.py"
    spec = importlib.util.spec_from_file_location("handoff_kit_ir_schema", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.validate


validate_kit = load_kit_validator()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def dump_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))


def walk_ops(node: object, out: Counter) -> None:
    if isinstance(node, dict):
        if isinstance(node.get("op"), str):
            out[node["op"]] += 1
        for value in node.values():
            walk_ops(value, out)
    elif isinstance(node, list):
        for value in node:
            walk_ops(value, out)


def validate_parse(rows: list[dict], verified: set[str]) -> Counter:
    questions, ops = set(), Counter()
    for index, row in enumerate(rows, 1):
        messages = row.get("messages")
        if not isinstance(messages, list) or [m.get("role") for m in messages] != [
                "system", "user", "assistant"]:
            raise ValueError(f"parse row {index}: bad message contract")
        question = messages[1].get("content", "").strip()
        if not question or question in questions:
            raise ValueError(f"parse row {index}: empty or duplicate question")
        questions.add(question)
        meta = row.get("meta") or {}
        if meta.get("sector") != "ecology" or meta.get("source_run") not in verified:
            raise ValueError(f"parse row {index}: not admitted by ecology verified-run manifest")
        ir = json.loads(messages[2]["content"])
        report = validate_ecology(ir)
        if not report["valid"]:
            raise ValueError(f"parse row {index}: invalid IR: {report['errors']}")
        if {"BUFFER", "FILTER"} & set(report["ops"]):
            raise ValueError(f"parse row {index}: v2.4 operation leaked into v2.3 corpus")
        walk_ops(ir, ops)
    return ops


def validate_clarify(rows: list[dict]) -> None:
    for index, row in enumerate(rows, 1):
        holed = validate_ecology(row.get("ir_holed"))
        bound = validate_ecology(row.get("ir_bound"))
        if not holed["valid"] or not holed["unbound"]:
            raise ValueError(f"clarify row {index}: first tree is not a valid unbound tree")
        if not bound["valid"] or bound["unbound"]:
            raise ValueError(f"clarify row {index}: bound tree is invalid or still unbound")
        if not row.get("clarify") or not row.get("reply"):
            raise ValueError(f"clarify row {index}: missing dialogue text")


def validate_v24(rows: list[dict], evidence: dict) -> Counter:
    summary = evidence.get("summary") or {}
    evidence_rows = evidence.get("rows") or []
    if (evidence.get("algebra_version") != "v2.4.0-draft" or
            summary.get("gold_execution_failures") != 0 or
            summary.get("n") != len(rows) or len(evidence_rows) != len(rows)):
        raise ValueError("v2.4 execution evidence is incomplete or does not cover the corpus")
    ops = Counter()
    for index, (row, proved) in enumerate(zip(rows, evidence_rows), 1):
        messages = row.get("messages") or []
        if len(messages) != 3 or [message.get("role") for message in messages] != [
                "system", "user", "assistant"]:
            raise ValueError(f"v2.4 row {index}: bad message contract")
        meta = row.get("meta") or {}
        if meta.get("algebra_version") != "v2.4.0-draft":
            raise ValueError(f"v2.4 row {index}: wrong profile")
        ir = json.loads(messages[2]["content"])
        report = validate_kit(ir, "v2.4.0-draft")
        if not report["valid"]:
            raise ValueError(f"v2.4 row {index}: invalid draft IR: {report['errors']}")
        if (messages[1]["content"] != proved.get("question") or
                ir != proved.get("gold_ir") or
                meta.get("gold_execution_status") !=
                (proved.get("gold_execution") or {}).get("status")):
            raise ValueError(f"v2.4 row {index}: does not match execution evidence")
        walk_ops(ir, ops)
        if meta.get("gold_execution_status") not in {"answer", "data_request"}:
            raise ValueError(f"v2.4 row {index}: gold did not execute to an admitted status")
    if not {"BUFFER", "FILTER"} <= set(ops):
        raise ValueError("v2.4 curriculum does not cover both BUFFER and FILTER")
    return ops


def main() -> None:
    manifest_path = ECOLOGY / "corpus" / "verified-runs.json"
    source_parse = ECOLOGY / "corpus" / "parse.jsonl"
    source_clarify = ECOLOGY / "corpus" / "clarify.jsonl"
    source_v24 = KIT / "conformance" / "v24_parse_v2.4.jsonl"
    source_v24_evidence = ROOT / "governance" / "evidence" / "v24-qwen2b-pretrain.json"
    verified = set(json.loads(manifest_path.read_text())["verified_runs"])
    parse_rows, clarify_rows, v24_rows = (jsonl(source_parse), jsonl(source_clarify),
                                           jsonl(source_v24))
    v24_evidence = json.loads(source_v24_evidence.read_text())
    parse_ops = validate_parse(parse_rows, verified)
    validate_clarify(clarify_rows)
    v24_ops = validate_v24(v24_rows, v24_evidence)

    out_parse = HERE / "parse-v2.3.jsonl"
    out_clarify = HERE / "clarify-v2.3.jsonl"
    out_v24 = HERE / "v24-surface.jsonl"
    dump_jsonl(out_parse, parse_rows)
    dump_jsonl(out_clarify, clarify_rows)
    dump_jsonl(out_v24, v24_rows)
    manifest = {
        "schema_version": "ecology-origin-corpus-handoff-v1",
        "status": "ready",
        "sector": "ecology",
        "source_verified_runs": sorted(verified),
        "admission": "execution-verified allowlisted development rows; no holdouts or expressiveness probes",
        "profiles": {
            "parse-v2.3.jsonl": "v2.3.0",
            "clarify-v2.3.jsonl": "v2.3.0",
            "v24-surface.jsonl": "v2.4.0-draft"
        },
        "counts": {"parse": len(parse_rows), "clarify": len(clarify_rows),
                   "v24_surface": len(v24_rows)},
        "ops": {"parse_v23": dict(sorted(parse_ops.items())),
                "v24_surface": dict(sorted(v24_ops.items()))},
        "source_sha256": {
            str(path.relative_to(ROOT)): sha(path) for path in
            (manifest_path, source_parse, source_clarify, source_v24, source_v24_evidence)
        },
        "output_sha256": {
            path.name: sha(path) for path in (out_parse, out_clarify, out_v24)
        },
        "exclusions": ["holdouts", "exams", "expressiveness probes", "narrative frontier runs",
                       "raw Hermes transcripts", "GROUP pending RFC"]
    }
    (HERE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest["counts"], sort_keys=True))


if __name__ == "__main__":
    main()
