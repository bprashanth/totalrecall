#!/usr/bin/env python3
"""Validate, fixture-execute, and parser-probe the neutral ALG-015 question corpus."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from unittest import mock

import executor as E
import parser as P
from ir_schema import canonicalize, validate


HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_BANK = os.path.join(HERE, "..", "conformance", "buffer_questions_v2.4.json")
PROFILE = "v2.4.0-draft"


PLACE_CENTRES = {
    "Erode town": (11.34, 77.72), "Pune": (18.52, 73.86),
    "Mysuru, India": (12.30, 76.64), "Surat, India": (21.17, 72.83),
    "Coimbatore, India": (11.02, 76.96), "Tiruppur, India": (11.11, 77.34),
    "Kisumu, Kenya": (-0.10, 34.75), "Jaipur": (26.91, 75.79),
}


def fixture_region(place):
    if place == "Dateline Station":
        return {"name": place, "bbox": [-0.1, 0.1, 179.5, 179.9],
                "lat": 0.0, "lon": 179.7, "orig": place}
    lat, lon = PLACE_CENTRES.get(place, (10.0, 77.0))
    return {"name": place, "bbox": [lat - 0.08, lat + 0.08, lon - 0.08, lon + 0.08],
            "lat": lat, "lon": lon, "orig": place}


def fixture_select(entity, region, time_value, provenance):
    lat, lon = region["lat"], region["lon"]
    offsets = (-0.02, -0.01, 0.0, 0.004, 0.01, 0.02)
    rows = [{"id": f"{entity}:{i}", "lat": lat + offset, "lon": lon + offset,
             "name": (None if i == 1 else f"{entity} fixture {i}"), "time": None}
            for i, offset in enumerate(offsets)]
    provenance.append({"op": "SELECT", "route": "fixture", "resolved": entity,
                       "note": f"{len(rows)} neutral conformance rows"})
    return {"kind": "records", "rows": rows, "entity": entity, "label": "observed",
            "source": "neutral-conformance-fixture", "measure": f"records:{entity}",
            "unit": "record", "grain": "point", "lineage": [{"source": "fixture"}],
            "fields": {"id": "identifier", "lat": "number", "lon": "number",
                       "name": "string|null", "time": "period|null"}}


def execute_fixture(ir):
    with mock.patch.object(E.C, "resolve_region", side_effect=fixture_region), \
            mock.patch.object(E, "_route_select", side_effect=fixture_select):
        return E.execute(ir, algebra_version=PROFILE)


def main():
    cli = argparse.ArgumentParser()
    cli.add_argument("--model", default="qwen2b")
    cli.add_argument("--questions", default=DEFAULT_BANK)
    cli.add_argument("--out", required=True)
    cli.add_argument("--corpus-out")
    cli.add_argument("--require-parser-perfect", action="store_true",
                     help="fail unless every parser-required row exactly matches canonical gold")
    args = cli.parse_args()
    with open(args.questions, encoding="utf-8") as stream:
        bank = json.load(stream)

    rows = []
    gold_failures = 0
    parser_matches = 0
    parser_required = 0
    for item in bank["questions"]:
        gold = canonicalize(item["gold_ir"], PROFILE)
        gold_schema = validate(gold, PROFILE)
        gold_execution = execute_fixture(gold) if gold_schema["valid"] else {
            "status": "error", "reason": "invalid_gold"}
        expected = item["expect"]
        gold_status_ok = (gold_execution["status"] in {"answer", "data_request"}
                          if expected == "answer_or_data_request" else
                          gold_execution["status"] == expected)
        if not gold_schema["valid"] or not gold_status_ok:
            gold_failures += 1

        parsed = P.parse(item["q"], role=args.model, algebra_version=PROFILE)
        compiled = canonicalize(parsed.get("ir"), PROFILE)
        compiled_schema = validate(compiled, PROFILE) if compiled else {
            "valid": False, "errors": ["no IR"], "holes": [], "ops": []}
        exact = compiled == gold
        required = item.get("parser_required", True)
        parser_required += int(required)
        parser_matches += int(required and exact and compiled_schema["valid"])
        rows.append({
            "id": item["id"], "question": item["q"], "expect": expected,
            "gold_ir": gold, "gold_schema": gold_schema,
            "gold_execution": gold_execution,
            "compiled_ir": compiled, "compiled_schema": compiled_schema,
            "parser_exact_canonical_match": exact,
            "parser_required": required,
            "repair_events": parsed.get("events") or [],
            "raw_parse": parsed.get("raw") if not compiled_schema["valid"] else None,
        })
        print(f"{item['id']}: gold={'ok' if gold_status_ok else 'FAIL'} "
              f"parser={'match' if exact else 'different'}")

    artifact = {
        "schema_version": "buffer-conformance-evidence-v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "algebra_version": PROFILE, "model": args.model,
        "questions": os.path.relpath(args.questions, os.getcwd()),
        "summary": {"n": len(rows), "gold_execution_failures": gold_failures,
                    "parser_required": parser_required,
                    "parser_exact_canonical_matches": parser_matches,
                    "parser_exact_canonical_rate": round(parser_matches / parser_required, 4),
                    "parser_promotion_pass": parser_matches == parser_required},
        "rows": rows,
    }
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as stream:
        json.dump(artifact, stream, indent=2, default=str)
    if args.corpus_out:
        os.makedirs(os.path.dirname(os.path.abspath(args.corpus_out)), exist_ok=True)
        system = P.build_messages("placeholder", algebra_version=PROFILE)[0]["content"]
        with open(args.corpus_out, "w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps({"messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": row["question"]},
                    {"role": "assistant", "content": json.dumps(row["gold_ir"])}],
                    "meta": {"proposal": "ALG-015", "algebra_version": PROFILE,
                             "source": os.path.basename(args.questions),
                             "gold_execution_status": row["gold_execution"]["status"]}
                }) + "\n")
    print(args.out)
    if gold_failures:
        raise SystemExit(2)
    if args.require_parser_perfect and parser_matches != parser_required:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
