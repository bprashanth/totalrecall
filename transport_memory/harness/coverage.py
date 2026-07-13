#!/usr/bin/env python3
"""Round-2 coverage matrix for the transport banks (adaptation of the livelihoods reference).

Descriptive, not a scorer: every admitted gold tree becomes one machine-readable row, so that
question-count growth cannot masquerade as breadth — paraphrases add rows, not cells. The
summary section tallies every dimension; the CELLS section is the generation driver: empty and
singleton (source-family x question-type) and (type x skeleton) cells are what gen-003 and the
holdout prompts must fill, per ROUND2.md workstream B.

Run from anywhere: python3 harness/coverage.py [bank.json ...]
Default banks: questions/seed.json, gen-*.json (breakers/holdouts excluded unless flagged).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
from connectors import (gtfs_resolve, osm_resolve_tag, osm_routes_resolve,  # noqa: E402
                        ridership_resolve, wb_resolve_indicator)

GRAIN = {
    "gtfs-mobility-database": "city-feed/stop-point",
    "city-open-data-ridership": "city-system/annual-series",
    "osm-routes": "city-bbox/route-relation",
    "world-bank": "country/annual-series",
    "osm-points": "city-bbox/point-record",
    "hole": "unresolved",
    "none": "none",
}


def source_for(entity: str) -> str:
    """Mirror executor routing order EXACTLY — the matrix must not claim a source the
    executor would not pick (gtfs -> ridership -> osm-routes -> world-bank -> osm-points)."""
    if not isinstance(entity, str) or entity.startswith("?"):
        return "hole"
    if gtfs_resolve(entity)[0]:
        return "gtfs-mobility-database"
    if ridership_resolve(entity)[0]:
        return "city-open-data-ridership"
    if osm_routes_resolve(entity)[0]:
        return "osm-routes"
    if wb_resolve_indicator(entity)[0]:
        return "world-bank"
    if osm_resolve_tag(entity)[0]:
        return "osm-points"
    return "none"  # unmapped = honest DataRequest at runtime; a coverage finding, not OSM


def walk(node):
    if isinstance(node, dict):
        if isinstance(node.get("op"), str):
            yield node
        for v in node.values():
            yield from walk(v)
    elif isinstance(node, list):
        for v in node:
            yield from walk(v)


def scalars(node):
    if isinstance(node, dict):
        for v in node.values():
            yield from scalars(v)
    elif isinstance(node, list):
        for v in node:
            yield from scalars(v)
    else:
        yield node


def skeleton(node) -> str:
    if not isinstance(node, dict) or "op" not in node:
        return "?"
    kids = [skeleton(node[k]) for k in ("source", "left", "right", "target")
            if isinstance(node.get(k), dict) and "op" in node[k]]
    kids += [skeleton(i) for i in node.get("items", []) if isinstance(i, dict) and "op" in i]
    op = node["op"]
    return op if not kids else f"{op}({','.join(kids)})"


def time_form(v) -> str:
    if v is None:
        return "unspecified"
    if isinstance(v, str):
        return "hole" if v.startswith("?") else "other"
    if isinstance(v, dict):
        s, e = v.get("start"), v.get("end")
        return "point" if (s == e and s is not None) else "window"
    return "other"


def row_for(bank: str, q: dict) -> dict:
    ir = q.get("gold_ir") or q.get("gold_attempt") or {}
    nodes = list(walk(ir))
    selects = [n for n in nodes if n.get("op") == "SELECT"]
    entities = sorted({str(n.get("entity")) for n in selects})
    sources = q.get("source_family")
    sources = ([sources] if isinstance(sources, str) else sources) \
        or sorted({source_for(e) for e in entities}) or ["none"]
    ranks = [n for n in nodes if n.get("op") == "RANK"]
    holes = sorted({v for v in scalars(ir) if isinstance(v, str) and v.startswith("?")})
    return {
        "id": q.get("id"), "bank": bank, "type": q.get("type"),
        "expect": q.get("expect") or ("rejected" if "reject_reason" in q else None),
        "skeleton": skeleton(ir),
        "ops": dict(sorted(Counter(n["op"] for n in nodes).items())),
        "sources": sources,
        "grains": q.get("grain") or sorted({GRAIN.get(s, "unknown") for s in sources}),
        "entities": entities,
        "regions": sorted({str(n.get("place")) for n in nodes if n.get("op") == "REGION"}),
        "time_forms": sorted({time_form(n.get("time")) for n in selects}) or ["none"],
        "relations": sorted({str(n.get("relation")) for n in nodes if n.get("op") == "RELATE"}),
        "thresholds_km": sorted({n["threshold_km"] for n in nodes
                                 if n.get("op") == "RELATE" and "threshold_km" in n}),
        "agg_metrics": sorted({str(n.get("metric")) for n in nodes if n.get("op") == "AGGREGATE"}),
        "compare_hows": sorted({str(n.get("how")) for n in nodes if n.get("op") == "COMPARE"}),
        "estimate_methods": sorted({str(n.get("method")) for n in nodes
                                    if n.get("op") == "ESTIMATE"}),
        "rank_arities": sorted({len(n.get("items", [])) for n in ranks}),
        "holes": holes,
        "capability_family": q.get("capability_family"),
        "adversarial": bool(q.get("adversarial") or "reject_reason" in q),
    }


def cells(rows, a_field, b_field):
    c = Counter()
    for r in rows:
        avs = r[a_field] if isinstance(r[a_field], list) else [r[a_field]]
        bvs = r[b_field] if isinstance(r[b_field], list) else [r[b_field]]
        for a in avs:
            for b in bvs:
                c[f"{a} x {b}"] += 1
    return c


def summarize(rows):
    def tally(field):
        vals = []
        for r in rows:
            v = r[field]
            vals.extend(v if isinstance(v, list) else [v])
        return dict(sorted(Counter(str(x) for x in vals).items()))

    src_type = cells(rows, "sources", "type")
    type_skel = cells(rows, "type", "skeleton")
    return {
        "question_count": len(rows),
        "unique_skeletons": len({r["skeleton"] for r in rows}),
        "by_bank": tally("bank"), "by_type": tally("type"), "by_expect": tally("expect"),
        "by_source": tally("sources"), "by_grain": tally("grains"),
        "by_time_form": tally("time_forms"), "by_relation": tally("relations"),
        "by_agg_metric": tally("agg_metrics"), "by_compare_how": tally("compare_hows"),
        "by_estimate_method": tally("estimate_methods"),
        "by_capability_family": tally("capability_family"),
        "cells": {
            "source_x_type": dict(sorted(src_type.items())),
            "source_x_type_singletons": sorted(k for k, v in src_type.items() if v == 1),
            "type_x_skeleton_singletons": sorted(k for k, v in type_skel.items() if v == 1),
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=Path)
    ap.add_argument("--include-breakers", action="store_true")
    ap.add_argument("--include-holdouts", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "coverage" / "matrix.json")
    a = ap.parse_args()
    paths = a.paths or sorted((ROOT / "questions").glob("*.json"))
    paths = [p for p in paths if p.name != "fewshot.json"]
    if not a.include_breakers:
        paths = [p for p in paths if "breaker" not in p.name]
    if not a.include_holdouts:
        paths = [p for p in paths if "holdout" not in p.name]
    rows = []
    for p in paths:
        data = json.loads(p.read_text())
        qs = data if isinstance(data, list) else data.get("questions", [])
        rows.extend(row_for(p.name, q) for q in qs)
    payload = {"schema_version": "round2-coverage-transport-v1",
               "banks": [p.name for p in paths],
               "summary": summarize(rows), "rows": rows}
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
