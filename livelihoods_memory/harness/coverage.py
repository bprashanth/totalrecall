#!/usr/bin/env python3
"""Build the Round-2 question capability matrix.

This is intentionally descriptive, not a scorer.  It turns every admitted gold tree into one
machine-readable row so question-count growth cannot hide repeated templates or empty semantics.
The resulting snapshot is safe to diff at every checkpoint.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Any, Iterable

from connectors import (eurostat_resolve_indicator, ilo_resolve_indicator, osm_resolve_tag,
                        wb_resolve_indicator)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent


def walk(node: Any) -> Iterable[dict[str, Any]]:
    if isinstance(node, dict):
        if isinstance(node.get("op"), str):
            yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def skeleton(node: Any) -> str:
    if not isinstance(node, dict) or "op" not in node:
        return "?"
    op = node["op"]
    children = []
    for key in ("source", "left", "right", "target"):
        if isinstance(node.get(key), dict) and "op" in node[key]:
            children.append(skeleton(node[key]))
    children.extend(skeleton(item) for item in node.get("items", [])
                    if isinstance(item, dict) and "op" in item)
    return op if not children else f"{op}({','.join(children)})"


def source_for(entity: str) -> str:
    if entity.startswith("?"):
        return "hole"
    if ilo_resolve_indicator(entity)[0]:
        return "ilostat"
    if eurostat_resolve_indicator(entity)[0]:
        return "eurostat"
    if wb_resolve_indicator(entity)[0]:
        return "world-bank"
    if osm_resolve_tag(entity)[0]:
        return "osm-overpass"
    # Round-2 connectors can set an explicit source_family on the question until their local
    # resolver is available here. Unknown is a coverage finding, never silently called OSM.
    return "unknown"


def time_form(value: Any) -> str:
    if value is None:
        return "unspecified"
    if not isinstance(value, dict):
        return "hole" if isinstance(value, str) and value.startswith("?") else "other"
    start, end = value.get("start"), value.get("end")
    if start == end and start is not None:
        return "point"
    return "window"


def matrix_row(bank: str, q: dict[str, Any]) -> dict[str, Any]:
    ir = q.get("gold_ir") or q.get("gold_attempt") or {}
    nodes = list(walk(ir))
    selects = [n for n in nodes if n.get("op") == "SELECT"]
    entities = sorted({str(n.get("entity")) for n in selects})
    regions = sorted({str(n.get("place")) for n in nodes if n.get("op") == "REGION"})
    inferred_sources = sorted({source_for(e) for e in entities})
    explicit_sources = q.get("source_family")
    sources = ([explicit_sources] if isinstance(explicit_sources, str) else explicit_sources) \
        or inferred_sources
    rank_nodes = [n for n in nodes if n.get("op") == "RANK"]
    holes = sorted({v for n in nodes for v in n.values()
                    if isinstance(v, str) and v.startswith("?")})
    # Region holes can occur as scalar children and therefore do not appear in walk().
    holes.extend(sorted({v for v in scalar_values(ir)
                         if isinstance(v, str) and v.startswith("?") and v not in holes}))
    return {
        "id": q.get("id"),
        "bank": bank,
        "type": q.get("type"),
        "expect": q.get("expect", "rejected" if "reject_reason" in q else None),
        "skeleton": skeleton(ir),
        "ops": dict(sorted(Counter(n["op"] for n in nodes).items())),
        "sources": sources,
        "grain": q.get("grain") or infer_grains(sources, selects),
        "entities": entities,
        "regions": regions,
        "time_forms": sorted({time_form(n.get("time")) for n in selects}),
        "relations": sorted({str(n.get("relation")) for n in nodes if n.get("op") == "RELATE"}),
        "thresholds_km": sorted({n["threshold_km"] for n in nodes
                                  if n.get("op") == "RELATE" and "threshold_km" in n}),
        "aggregate_metrics": sorted({str(n.get("metric")) for n in nodes
                                     if n.get("op") == "AGGREGATE"}),
        "compare_modes": sorted({str(n.get("how")) for n in nodes
                                 if n.get("op") == "COMPARE"}),
        "estimate_methods": sorted({str(n.get("method")) for n in nodes
                                    if n.get("op") == "ESTIMATE"}),
        "rank_orders": sorted({str(n.get("order")) for n in rank_nodes}),
        "rank_sizes": sorted({len(n.get("items", [])) for n in rank_nodes}),
        "holes": holes,
        "capability_family": q.get("capability_family"),
        "adversarial": bool(q.get("adversarial") or "reject_reason" in q),
    }


def scalar_values(node: Any) -> Iterable[Any]:
    if isinstance(node, dict):
        for value in node.values():
            yield from scalar_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from scalar_values(value)
    else:
        yield node


def infer_grains(sources: list[str], selects: list[dict[str, Any]]) -> list[str]:
    grains = set()
    for source in sources:
        if source == "osm-overpass":
            grains.add("city-bbox/point-record")
        elif source == "world-bank":
            grains.add("country/annual-series")
        elif source == "ilostat":
            grains.add("country/annual-survey-series")
        elif source == "eurostat":
            grains.add("nuts2/annual-survey-series")
        elif source == "hole":
            grains.add("unresolved")
        else:
            grains.add("unknown")
    if not selects:
        grains.add("none")
    return sorted(grains)


def load_rows(paths: list[Path]) -> list[dict[str, Any]]:
    rows = []
    for path in paths:
        data = json.loads(path.read_text())
        questions = data if isinstance(data, list) else data.get("questions", [])
        rows.extend(matrix_row(path.name, q) for q in questions)
    return rows


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def tally(field: str) -> dict[str, int]:
        vals = []
        for row in rows:
            value = row[field]
            vals.extend(value if isinstance(value, list) else [value])
        return dict(sorted(Counter(str(v) for v in vals).items()))

    op_counts = Counter()
    for row in rows:
        op_counts.update(row["ops"])
    return {
        "question_count": len(rows),
        "by_bank": tally("bank"),
        "by_type": tally("type"),
        "by_expect": tally("expect"),
        "by_source": tally("sources"),
        "by_grain": tally("grain"),
        "by_time_form": tally("time_forms"),
        "by_relation": tally("relations"),
        "by_aggregate_metric": tally("aggregate_metrics"),
        "by_compare_mode": tally("compare_modes"),
        "by_estimate_method": tally("estimate_methods"),
        "by_rank_order": tally("rank_orders"),
        "by_capability_family": tally("capability_family"),
        "op_occurrences": dict(sorted(op_counts.items())),
        "unique_skeletons": len({row["skeleton"] for row in rows}),
        "adversarial_count": sum(row["adversarial"] for row in rows),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=Path,
                    help="question JSON files (default: admitted seed/gen banks)")
    ap.add_argument("--include-breakers", action="store_true")
    ap.add_argument("--out", type=Path, default=ROOT / "coverage" / "matrix.json")
    args = ap.parse_args()
    paths = args.paths or sorted((ROOT / "questions").glob("*.json"))
    if not args.include_breakers:
        paths = [p for p in paths if "breaker" not in p.name and "holdout" not in p.name]
    rows = load_rows(paths)
    payload = {"schema_version": "round2-coverage-v1", "summary": summarize(rows), "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(payload["summary"], indent=2))


if __name__ == "__main__":
    main()
