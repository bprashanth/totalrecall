#!/usr/bin/env python3
"""Strict semantic gold audit beyond the benchmark's deliberately coarse op-shape score."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re
import unicodedata

import connectors as C


def fold(value):
    value = "".join(ch for ch in unicodedata.normalize("NFKD", str(value).lower())
                    if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def entity_key(entity, region=None):
    if isinstance(entity, str) and entity.startswith("?"): return "?"
    spec, _, _ = C.ilo_resolve_indicator(str(entity))
    if spec:
        return "ilo:" + json.dumps(spec, sort_keys=True)
    geo = C.eurostat_resolve_geo({"orig": region.get("place", ""), "name": region.get("place", "")}) \
        if isinstance(region, dict) else None
    spec, _, _ = C.eurostat_resolve_indicator(str(entity))
    if spec and geo:
        return "euro:" + json.dumps(spec, sort_keys=True)
    code, _, _ = C.wb_resolve_indicator(str(entity))
    if code: return "wb:" + code
    if spec:
        return "euro:" + json.dumps(spec, sort_keys=True)
    tag, _, _ = C.osm_resolve_tag(str(entity))
    if tag: return "osm:" + tag
    literal = fold(entity)
    parts = literal.split()
    if parts:
        if parts[-1].endswith("ies"): parts[-1] = parts[-1][:-3] + "y"
        elif len(parts[-1]) > 3 and parts[-1].endswith("s"): parts[-1] = parts[-1][:-1]
    return "literal:" + " ".join(parts)


def is_series_entity(entity):
    key = entity_key(entity)
    return key.startswith(("ilo:", "euro:", "wb:"))


def region_key(region, entity=None):
    if isinstance(region, str): return "?" if region.startswith("?") else fold(region)
    if not isinstance(region, dict): return region
    place = region.get("place", "")
    if isinstance(place, str) and place.startswith("?"): return "?"
    if C.eurostat_resolve_indicator(str(entity))[0]:
        code = C.eurostat_resolve_geo({"orig": place, "name": place})
        if code: return "nuts2:" + code
    value = fold(place)
    # NUTS region names can end in a country word as part of the name itself (most notably
    # "Ile de France").  Do not mistake that final token for a redundant country qualifier.
    known_regions = {fold(alias) for alias in C.EUROSTAT_GEOS}
    if value in known_regions:
        return value
    for suffix in ("south africa", "new zealand", "united kingdom"):
        if value.endswith(" " + suffix): value = value[:-(len(suffix)+1)]
    if value.startswith("the "): value = value[4:]
    parts = value.split()
    countries = {"india", "kenya", "ghana", "france", "germany", "spain", "italy", "poland",
                 "portugal", "brazil", "mexico", "canada", "australia", "usa", "texas",
                 "california", "florida", "belgium", "colombia", "morocco", "uganda",
                 "estonia", "czechia", "austria", "netherlands", "mongolia", "japan",
                 "thailand", "ecuador", "romania", "croatia", "greece", "senegal",
                 "peru", "philippines", "namibia", "nigeria", "latvia", "slovenia"}
    countries.update({"rwanda", "tanzania"})
    if len(parts) > 1 and parts[-1] in countries: parts.pop()
    return " ".join(parts)


def anchor(node):
    if not isinstance(node, dict): return None
    if node.get("op") == "SELECT" and isinstance(node.get("time"), dict):
        time = node["time"]
        if time.get("start") == time.get("end"): return time.get("start")
    for key in ("source", "left", "right"):
        found = anchor(node.get(key))
        if found: return found
    return None


def canonical(node):
    if isinstance(node, str) and node.startswith("?"): return "?"
    if isinstance(node, list): return [canonical(x) for x in node]
    if not isinstance(node, dict): return node
    op = node.get("op")
    # The one documented redundant denotation: mean-by-time over a source-provided Series.
    if op == "AGGREGATE" and node.get("by") == "time" and node.get("metric") == "mean":
        src = node.get("source")
        if isinstance(src, dict) and src.get("op") == "SELECT" and is_series_entity(src.get("entity")):
            return canonical(src)
    if op == "REGION":
        key=region_key(node)
        return "?" if key=="?" else {"op": "REGION", "place": key}
    if op == "SELECT":
        return {"op": "SELECT", "entity": entity_key(node.get("entity"), node.get("region")),
                "region": region_key(node.get("region"), node.get("entity")),
                "time": canonical(node.get("time"))}
    if op == "ANNOTATE":
        return {"op": op, "source": canonical(node.get("source")), "layer": fold(node.get("layer"))}
    if op == "RELATE":
        return {"op": op, "relation": node.get("relation"),
                "threshold_km": node.get("threshold_km"),
                "left": canonical(node.get("left")), "right": canonical(node.get("right"))}
    if op == "AGGREGATE":
        return {"op": op, "by": node.get("by"), "metric": node.get("metric"),
                "source": canonical(node.get("source"))}
    if op == "COMPARE":
        left, right = node.get("left"), node.get("right")
        # v2.1 canonical later-minus/over-earlier orientation.
        if right is not None and anchor(left) and anchor(right) and anchor(left) < anchor(right):
            left, right = right, left
        # COMPARE scalarizes Records by row count in the frozen executor.  Within this
        # scalarizing context, an explicit count wrapper and a direct Records operand are the
        # same denotation; keep that equivalence local so density/mean and standalone counts
        # remain distinguishable.
        def scalar_operand(value):
            if isinstance(value, dict) and value.get("op") == "AGGREGATE" \
                    and value.get("by") == "space" and value.get("metric") == "count" \
                    and isinstance(value.get("source"), dict) \
                    and value["source"].get("op") in ("SELECT", "RELATE", "ANNOTATE"):
                value = value["source"]
            return canonical(value)
        out = {"op": op, "how": node.get("how"), "left": scalar_operand(left)}
        if right is not None: out["right"] = scalar_operand(right)
        return out
    if op == "ESTIMATE":
        return {"op": op, "method": node.get("method"), "source": canonical(node.get("source")),
                "target": canonical(node.get("target"))}
    if op == "RANK":
        # Input item order has no denotational effect; output order/k do.
        items = [canonical(x) for x in node.get("items", [])]
        items.sort(key=lambda x: json.dumps(x, sort_keys=True))
        return {"op": op, "order": node.get("order"), "k": node.get("k"), "items": items}
    if op is None:
        return {key: canonical(value) for key, value in sorted(node.items())}
    return {key: canonical(value) for key, value in sorted(node.items())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", required=True, type=Path)
    ap.add_argument("--traces", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args = ap.parse_args()
    bank = json.loads(args.questions.read_text())["questions"]
    gold = {row["id"]: row for row in bank}
    traces = [json.loads(line) for line in args.traces.read_text().splitlines() if line.strip()]
    rows = []
    for trace in traces:
        expected = gold.get(trace["id"])
        if expected is None or expected["q"] != trace["question"]:
            rows.append({"id": trace["id"], "match": False, "reason": "bank_or_question_mismatch"})
            continue
        want, got = canonical(expected["gold_ir"]), canonical(trace.get("ir"))
        rows.append({"id": trace["id"], "match": want == got,
                     "reason": None if want == got else "canonical_ir_mismatch",
                     "expected": want if want != got else None, "actual": got if want != got else None})
    counts = Counter(row["reason"] or "match" for row in rows)
    payload = {"schema_version": "round2-semantic-audit-v1", "questions": str(args.questions),
               "traces": str(args.traces), "n": len(rows),
               "all_match": len(rows) == len(bank) and all(row["match"] for row in rows),
               "counts": dict(counts), "rows": rows}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({key: payload[key] for key in ("n", "all_match", "counts")}, indent=2))
    if not payload["all_match"]: raise SystemExit(1)


if __name__ == "__main__": main()
