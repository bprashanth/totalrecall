"""Executor — walk an IR tree, call connectors, return Answer or DataRequest.

This is the deterministic 'truth' layer. Zero model calls. It:
  - refuses to run an unbound tree (holes) -> DataRequest naming the holes (clarification)
  - auto-routes each SELECT to a connector by resolving the entity (the small model should NOT
    need to name the data source; the resolver's job)
  - propagates evidence labels (observed | modelled | proxy) as taint up the tree
  - enforces gate-as-admissibility on ESTIMATE; a failed gate -> DataRequest (not a number)
  - stamps per-node provenance so the tree IS the lineage

Return: {"status": "answer"|"data_request", "value": <typed>, "label", "provenance", ...}
A typed value = {"kind": records|series|scalar|field, "rows"/"value", "label", "source"}.
"""
import statistics
from ir_schema import RELEASED_ALGEBRA_VERSION, canonicalize, validate, is_hole
import connectors as C


class DataRequest(Exception):
    def __init__(self, reason, detail=None):
        self.reason = reason
        self.detail = detail or {}
        super().__init__(reason)


def _merge_label(*labels):
    if "modelled" in labels:
        return "modelled"
    if "proxy" in labels:
        return "proxy"
    return "observed"


META_FIELDS = ("measure", "unit", "grain", "lineage", "frequency", "vintage",
               "temporal_semantics", "coarsen", "grain_proxy", "fields")


def _meta(value):
    """Return total metadata: legacy values receive explicit, non-wildcard unknown tags."""
    return {
        "measure": value.get("measure", "unknown"),
        "unit": value.get("unit", "unknown"),
        "grain": value.get("grain", "unknown"),
        "lineage": value.get("lineage") or [],
        "frequency": value.get("frequency"),
        "vintage": value.get("vintage"),
        "temporal_semantics": value.get("temporal_semantics"),
        "coarsen": value.get("coarsen"),
        "grain_proxy": value.get("grain_proxy"),
        "fields": value.get("fields") or {},
    }


def _copy_meta(source):
    return {field: source[field] for field in META_FIELDS if field in source}


def _compatibility_tuple(value):
    metadata = _meta(value)
    return metadata["measure"], metadata["unit"], metadata["grain"]


def _resolve_region(region, prov=None):
    if isinstance(region, dict) and region.get("op") == "REGION":
        return C.resolve_region(region["place"])
    if isinstance(region, dict) and region.get("op") == "BUFFER":
        source = _resolve_region(region["source"], prov)
        try:
            out = C.buffer_region(source, region["radius_km"])
        except ValueError as exc:
            raise DataRequest("unsupported_region_geometry", {
                "method": "bbox-approx", "radius_km": region.get("radius_km"),
                "reason": str(exc), "ask": "use exact geometry or a bounded region away from the discontinuity"})
        if prov is not None:
            prov.append({"op": "BUFFER", "method": "bbox-approx", "approximate": True,
                         "radius_km": region["radius_km"],
                         "source_region": source.get("name"), "source_support": source,
                         "result_bbox": out.get("bbox"),
                         "note": ("approximate latitude-adjusted search bbox; not an exact "
                                  "geodesic polygon or surveyed boundary")})
        return out
    if isinstance(region, str) and not is_hole(region):
        return C.resolve_region(region)
    raise DataRequest("unresolved_region", {"region": region})


# entity routing: try each source's resolver; first that matches wins. A World Bank indicator
# (economy/development series) takes priority; otherwise an OSM point entity (civic amenities).
def _route_select(entity, region, time, prov):
    # world bank indicator?
    code, canon, ambig = C.wb_resolve_indicator(entity)
    if code:
        out = C.wb_series(entity, region, time)
        prov.append({"op": "SELECT", "route": "worldbank", "resolved": canon,
                     "ambiguous": ambig, "note": out["note"]})
        return {"kind": "series", "rows": out["rows"], "entity": canon,
                "label": out.get("label", "observed"),   # v2.2: connector-leaf evidence label
                "source": out["source"], "ambiguous": ambig, **_copy_meta(out)}
    # osm point entity?
    tag, ocanon, oambig = C.osm_resolve_tag(entity)
    if tag:
        out = C.osm_select(entity, region)
        prov.append({"op": "SELECT", "route": "osm", "resolved": ocanon,
                     "ambiguous": oambig, "note": out["note"]})
        return {"kind": "records", "rows": out["rows"], "entity": ocanon, "label": "observed",
                "source": out["source"], "ambiguous": oambig, **_copy_meta(out)}
    # no connector maps this entity -> honest data gap (never fabricate)
    prov.append({"op": "SELECT", "route": "none", "note": f"no connector for {entity!r}"})
    raise DataRequest("no_connector",
                      {"entity": entity,
                       "hint": "no data source maps this entity; add a connector or refine the term"})


def _ev(node, prov, region_ctx):
    op = node["op"]

    if op == "REGION":
        return {"kind": "region", "value": C.resolve_region(node["place"]), "label": "observed"}

    if op == "BUFFER":
        return {"kind": "region", "value": _resolve_region(node, prov), "label": "observed",
                "source": "derived-latitude-adjusted-bbox-expansion", "method": "bbox-approx",
                "approximate": True}

    if op == "SELECT":
        region = _resolve_region(node["region"], prov)
        region_ctx["region"] = region
        ent = node["entity"]
        if isinstance(ent, list):  # v2.2 entity UNION: run each, merge rows, weakest label wins
            parts = [_route_select(x, region, node.get("time"), prov) for x in ent]
            seen, rows = set(), []
            for p in parts:
                for r in p.get("rows", []):
                    k = r.get("id") or (r.get("lat"), r.get("lon"), r.get("name"))
                    if k not in seen:
                        seen.add(k)
                        rows.append(r)
            val = {"kind": parts[0]["kind"], "rows": rows, "entity": ent,
                   "label": _merge_label(*[p["label"] for p in parts]), "source": "union",
                   "measure": "union:" + "+".join(_meta(p)["measure"] for p in parts),
                   "unit": _meta(parts[0])["unit"] if all(
                       _meta(p)["unit"] == _meta(parts[0])["unit"] for p in parts) else "unknown",
                   "grain": _meta(parts[0])["grain"] if all(
                       _meta(p)["grain"] == _meta(parts[0])["grain"] for p in parts) else "unknown",
                   "lineage": [item for p in parts for item in _meta(p)["lineage"]]}
            prov.append({"op": "SELECT", "route": "union",
                         "note": f"union of {ent} -> {len(rows)} rows"})
        else:
            val = _route_select(ent, region, node.get("time"), prov)
        val["spatial_support"] = region
        if not val["rows"]:
            raise DataRequest("empty_select",
                              {"entity": node["entity"], "region": region["name"],
                               "hint": "no records at this place; transfer or collect"})
        return val

    if op == "ANNOTATE":
        src = _ev(node["source"], prov, region_ctx)
        prov.append({"op": "ANNOTATE", "layer": node["layer"],
                     "note": f"annotate {len(src.get('rows',[]))} rows with {node['layer']}"})
        # v0: annotation layer is itself a source lookup per row — approximated as a tag.
        for r in src.get("rows", []):
            r[node["layer"]] = None
        return src

    if op == "RELATE":
        left = _ev(node["left"], prov, region_ctx)
        right = _ev(node["right"], prov, region_ctx)
        rel = node["relation"]
        thresh = node.get("threshold_km")
        rows = _relate(left.get("rows", []), right.get("rows", []), rel, thresh)
        prov.append({"op": "RELATE", "relation": rel, "threshold_km": thresh,
                     "note": f"{len(left.get('rows',[]))} x {len(right.get('rows',[]))} -> {len(rows)}"})
        return {"kind": "records", "rows": rows,
                "label": _merge_label(left["label"], right["label"]), "source": "relate"}

    if op == "AGGREGATE":
        src = _ev(node["source"], prov, region_ctx)
        out = _aggregate(src, node["by"], node["metric"])
        prov.append({"op": "AGGREGATE", "by": node["by"], "metric": node["metric"],
                     "note": out["note"]})
        return {**out, "label": src["label"], "entity": src.get("entity")}

    if op == "COMPARE":
        left = _ev(node["left"], prov, region_ctx)
        right = _ev(node["right"], prov, region_ctx) if "right" in node else None
        out = _compare(left, right, node["how"])
        event = {"op": "COMPARE", "how": node["how"], "note": out["note"]}
        if out.get("alignment"):
            event["alignment"] = out["alignment"]
        if out.get("lineage"):
            event["lineage"] = out["lineage"]
        prov.append(event)
        labels = [left["label"]] + ([right["label"]] if right else []) + \
            ([out["label"]] if out.get("label") else [])
        return {**out, "label": _merge_label(*labels)}

    if op == "RANK":
        items = node["items"]
        vals, labels = [], []
        for it in items:
            v = _ev(it, prov, region_ctx)
            vals.append(v)
            labels.append(_item_label(it))
        # coerce each item to a scalar (same implicit coercion COMPARE uses)
        scored = []
        for lbl, v in zip(labels, vals):
            sv = _scalarize(v)
            scored.append({"label": lbl, "value": sv})
        if any(r["value"] is None for r in scored):
            raise DataRequest("rank_unscorable",
                              {"items": [r["label"] for r in scored if r["value"] is None],
                               "hint": "an item produced no comparable value"})
        signatures = {(_meta(v)["measure"], _meta(v)["unit"]) for v in vals}
        if len(signatures) != 1:
            raise DataRequest("rank_incompatible",
                              {"items": [{"label": label, "measure": _meta(value)["measure"],
                                          "unit": _meta(value)["unit"]}
                                         for label, value in zip(labels, vals)],
                               "hint": "RANK items must share measure and unit"})
        rev = node.get("order", "desc") == "desc"
        scored.sort(key=lambda r: r["value"], reverse=rev)
        k = node.get("k")
        if isinstance(k, int) and k > 0:
            scored = scored[:k]
        prov.append({"op": "RANK", "order": node.get("order"),
                     "note": " > ".join(f"{r['label']}={r['value']}" for r in scored)})
        return {"kind": "ranking", "rows": scored,
                "label": _merge_label(*[v["label"] for v in vals]), "source": "rank",
                "measure": _meta(vals[0])["measure"], "unit": _meta(vals[0])["unit"],
                "grain": "ranked-items", "lineage": [
                    {"label": label, "lineage": _meta(value)["lineage"]}
                    for label, value in zip(labels, vals)]}

    if op == "ESTIMATE":
        src = _ev(node["source"], prov, region_ctx)
        target = _resolve_region(node["target"], prov)
        gate = _gate(src, target, node["method"])
        prov.append({"op": "ESTIMATE", "method": node["method"], "gate": gate})
        if not gate["pass"]:
            raise DataRequest("gate_failed",
                              {"method": node["method"], "reason": gate["reason"],
                               "ask": gate["ask"]})
        # modelled field: v0 = the source distribution carried onto target, labelled modelled
        return {"kind": "field", "rows": src.get("rows", []), "label": "modelled",
                "source": f"estimate:{node['method']}", "gate": gate}

    raise DataRequest("unknown_op", {"op": op})


# ---- helpers -----------------------------------------------------------------
def _scalarize(v):
    """The implicit coercion: any typed value -> a comparable number."""
    if v["kind"] == "scalar":
        return v.get("value") if isinstance(v.get("value"), (int, float)) else None
    if v["kind"] == "series" and v.get("rows"):
        return v["rows"][-1]["value"]
    if v["kind"] in ("records", "field"):
        return len(v.get("rows", []))
    return None


def _item_label(node):
    """Human label for a RANK item: the place of its innermost REGION, else the entity."""
    place, entity = None, None

    def walk(n):
        nonlocal place, entity
        if not isinstance(n, dict):
            return
        if n.get("op") == "REGION" and place is None:
            place = n.get("place")
        if n.get("op") == "SELECT" and entity is None:
            entity = n.get("entity")
        for v in n.values():
            if isinstance(v, dict):
                walk(v)
            elif isinstance(v, list):
                for x in v:
                    walk(x)
    walk(node)
    return place or entity or "item"


def _haversine(a, b):
    from math import radians, sin, cos, asin, sqrt
    la1, lo1, la2, lo2 = map(radians, [a["lat"], a["lon"], b["lat"], b["lon"]])
    h = sin((la2 - la1) / 2) ** 2 + cos(la1) * cos(la2) * sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * asin(sqrt(h))


def _relate(left, right, rel, threshold_km=None):
    """within: keep left records with a right-neighbour <= threshold; beyond: the complement
    (no right-neighbour within threshold) — negation as a relation, not a new op (spec v2).
    An empty right set means within->nothing qualifies, beyond->everything does."""
    out = []
    for a in left:
        if "lat" not in a:
            continue
        dmin = min((_haversine(a, b) for b in right if "lat" in b), default=None)
        if rel == "distance":
            if dmin is not None:
                out.append({**a, "dist_km": round(dmin, 3)})
            continue
        thresh = threshold_km if isinstance(threshold_km, (int, float)) and threshold_km > 0 \
            else (5.0 if rel == "cooccur" else 1.0)
        if rel in ("within", "near", "cooccur"):
            if dmin is not None and dmin <= thresh:
                out.append({**a, "dist_km": round(dmin, 3)})
        elif rel == "beyond":
            if dmin is None or dmin > thresh:
                out.append({**a, "dist_km": (round(dmin, 3) if dmin is not None else None)})
    return out


def _aggregate(src, by, metric):
    rows = src.get("rows", [])
    if src["kind"] == "series":
        # already a series; count/mean summarise it
        return {"kind": "series", "rows": rows,
                "note": f"passthrough series ({len(rows)} pts)", **_copy_meta(src)}
    if by == "time":
        bins = {}
        for r in rows:
            t = (r.get("time") or "")[:4]
            if not t:
                continue
            bins[t] = bins.get(t, 0) + 1
        series = [{"t": k, "value": v} for k, v in sorted(bins.items())]
        return {"kind": "series", "rows": series, "note": f"binned to {len(series)} years",
                "measure": "record_count", "unit": "count", "grain": _meta(src)["grain"],
                "lineage": _meta(src)["lineage"], "frequency": "annual",
                "temporal_semantics": "flow", "coarsen": "sum"}
    # by space
    if metric in ("count", "presence"):
        return {"kind": "scalar", "value": len(rows), "note": f"count={len(rows)}",
                "measure": "record_count", "unit": "count", "grain": _meta(src)["grain"],
                "lineage": _meta(src)["lineage"]}
    if metric == "density":
        return {"kind": "scalar", "value": len(rows), "note": f"n={len(rows)} (density proxy)",
                "measure": "record_density_proxy", "unit": "count",
                "grain": _meta(src)["grain"], "lineage": _meta(src)["lineage"],
                "grain_proxy": {"declared": True, "reason": "bbox count used as density proxy"}}
    return {"kind": "scalar", "value": len(rows), "note": f"n={len(rows)}",
            "measure": "record_count", "unit": "count", "grain": _meta(src)["grain"],
            "lineage": _meta(src)["lineage"]}


FREQUENCY_ORDER = {"annual": 1, "quarterly": 2, "monthly": 3, "daily": 4}


def _infer_frequency(rows):
    periods = [str(row.get("t", "")) for row in rows if row.get("t") is not None]
    if not periods:
        return None
    if all(len(period) == 4 and period.isdigit() for period in periods):
        return "annual"
    if all("Q" in period.upper() for period in periods):
        return "quarterly"
    if all(len(period) >= 10 for period in periods):
        return "daily"
    if all(len(period) >= 7 for period in periods):
        return "monthly"
    return None


def _period_key(value, frequency):
    period = str(value)
    if frequency == "annual":
        return period[:4]
    if frequency == "monthly":
        return period[:7]
    if frequency == "daily":
        return period[:10]
    if frequency == "quarterly":
        compact = period.upper().replace("-", "")
        if "Q" in compact:
            year, quarter = compact.split("Q", 1)
            return f"{year[:4]}Q{quarter[:1]}"
    return period


def _coarsen_rows(rows, from_frequency, to_frequency, method):
    if to_frequency != "annual" or from_frequency not in {"daily", "monthly", "quarterly"}:
        raise DataRequest("temporal_frequency_mismatch", {
            "from": from_frequency, "to": to_frequency,
            "ask": "declare an implemented coarsening policy for these frequencies"})
    if method not in {"sum", "mean", "last"}:
        raise DataRequest("temporal_frequency_mismatch", {
            "from": from_frequency, "to": to_frequency, "coarsen": method,
            "ask": "connector must declare coarsen as sum, mean, or last"})
    buckets = {}
    for row in rows:
        buckets.setdefault(str(row.get("t", ""))[:4], []).append(row)
    out = []
    for period, items in sorted(buckets.items()):
        values = [item.get("value") for item in items
                  if isinstance(item.get("value"), (int, float))]
        if not values:
            continue
        if method == "sum":
            value = sum(values)
        elif method == "mean":
            value = sum(values) / len(values)
        else:
            value = sorted(items, key=lambda item: str(item.get("t", "")))[-1]["value"]
        out.append({"t": period, "value": value})
    return out


def _declared_coarsening(value, side, from_frequency, to_frequency):
    metadata = _meta(value)
    semantic, method = metadata["temporal_semantics"], metadata["coarsen"]
    valid = ((semantic == "flow" and method == "sum") or
             (semantic == "stock" and method in {"mean", "last"}))
    if not valid:
        raise DataRequest("temporal_frequency_mismatch", {
            "side": side, "from": from_frequency, "to": to_frequency,
            "temporal_semantics": semantic, "coarsen": method,
            "ask": "connector must declare flow+sum or stock+mean/last coarsening"})
    return method


def _aligned_series(left, right):
    """Exact-period inner join with an auditable certificate when support changes."""
    lrows, rrows = list(left.get("rows") or []), list(right.get("rows") or [])
    lf = _meta(left)["frequency"] or _infer_frequency(lrows)
    rf = _meta(right)["frequency"] or _infer_frequency(rrows)
    # Two one-point, intentionally disjoint windows are scalar CHANGE operands, not two
    # period-indexed series to align (v2.3 scoping clause).
    raw_overlap = {str(row.get("t")) for row in lrows} & {str(row.get("t")) for row in rrows}
    if len(lrows) == len(rrows) == 1 and not raw_overlap:
        return left, right, None

    coarsened = None
    if lf != rf:
        if lf not in FREQUENCY_ORDER or rf not in FREQUENCY_ORDER:
            raise DataRequest("temporal_frequency_mismatch", {
                "left_frequency": lf, "right_frequency": rf,
                "ask": "both connectors must declare compatible frequencies"})
        if FREQUENCY_ORDER[lf] > FREQUENCY_ORDER[rf]:
            method = _declared_coarsening(left, "left", lf, rf)
            lrows = _coarsen_rows(lrows, lf, rf, method)
            coarsened = {"side": "left", "from": lf, "to": rf, "method": method}
            lf = rf
        else:
            method = _declared_coarsening(right, "right", rf, lf)
            rrows = _coarsen_rows(rrows, rf, lf, method)
            coarsened = {"side": "right", "from": rf, "to": lf, "method": method}
            rf = lf

    def indexed(rows, frequency, side):
        out = {}
        duplicates = []
        for row in rows:
            key = _period_key(row.get("t"), frequency)
            if key in out:
                duplicates.append(key)
            out[key] = row
        if duplicates:
            raise DataRequest("duplicate_periods", {
                "side": side, "periods": sorted(set(duplicates)),
                "ask": "deduplicate the connector series before comparison"})
        return out

    li, ri = indexed(lrows, lf, "left"), indexed(rrows, rf, "right")
    common = sorted(set(li) & set(ri))
    if not common:
        raise DataRequest("temporal_no_overlap", {
            "left_window": [min(li) if li else None, max(li) if li else None],
            "right_window": [min(ri) if ri else None, max(ri) if ri else None],
            "ask": "choose a period covered by both series"})
    dropped_left = sorted(set(li) - set(common))
    dropped_right = sorted(set(ri) - set(common))
    left_aligned = {**left, "rows": [{**li[key], "t": key} for key in common],
                    "frequency": lf}
    right_aligned = {**right, "rows": [{**ri[key], "t": key} for key in common],
                     "frequency": rf}
    certificate = None
    if dropped_left or dropped_right or coarsened:
        certificate = {
            "join": "exact-period-inner", "frequency": lf,
            "used_periods": common,
            "used_window": [common[0], common[-1]],
            "dropped_left": dropped_left, "dropped_right": dropped_right,
            "coarsened": coarsened,
        }
    return left_aligned, right_aligned, certificate


def _compare(left, right, how):
    if how == "trend_direction":
        rows = left.get("rows", [])
        if len(rows) < 2:
            return {"kind": "scalar", "value": None, "note": "insufficient points for trend",
                    "measure": f"trend:{_meta(left)['measure']}",
                    "unit": f"{_meta(left)['unit']}/period", "grain": _meta(left)["grain"],
                    "lineage": _meta(left)["lineage"], "vintage": _meta(left)["vintage"]}
        xs = list(range(len(rows)))
        ys = [r["value"] for r in rows]
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        denom = sum((x - mx) ** 2 for x in xs) or 1
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
        direction = "rising" if slope > 0 else "falling" if slope < 0 else "flat"
        pct = (ys[-1] - ys[0]) / (abs(ys[0]) or 1) * 100
        return {"kind": "scalar", "value": direction,
                "measure": f"trend:{_meta(left)['measure']}",
                "unit": f"{_meta(left)['unit']}/period", "grain": _meta(left)["grain"],
                "lineage": _meta(left)["lineage"], "vintage": _meta(left)["vintage"],
                "note": f"{direction} (slope={slope:.4g}, {pct:+.1f}% over {n} pts "
                        f"{rows[0]['t']}→{rows[-1]['t']})"}

    alignment = None
    if left.get("kind") == right.get("kind") == "series":
        left, right, alignment = _aligned_series(left, right)

    def scal(value):
        if value is None:
            return None
        if value["kind"] == "scalar":
            return value["value"]
        if value["kind"] == "series" and value.get("rows"):
            return value["rows"][-1]["value"]
        if value["kind"] in ("records", "field"):
            return len(value.get("rows", []))
        return None

    left_meta, right_meta = _meta(left), _meta(right)
    if how == "difference" and _compatibility_tuple(left) != _compatibility_tuple(right):
        raise DataRequest("incompatible_arithmetic", {
            "how": how,
            "left": dict(zip(("measure", "unit", "grain"), _compatibility_tuple(left))),
            "right": dict(zip(("measure", "unit", "grain"), _compatibility_tuple(right))),
            "ask": "use operands with identical measure, unit, and grain"})
    proxy = None
    if how == "ratio" and left_meta["grain"] != right_meta["grain"]:
        proxy = left_meta["grain_proxy"] or right_meta["grain_proxy"]
        if not proxy:
            raise DataRequest("incompatible_arithmetic", {
                "how": how, "left_grain": left_meta["grain"],
                "right_grain": right_meta["grain"],
                "ask": "align grains or declare the specific proxy substitution"})

    a, b = scal(left), scal(right)
    if a is None or b is None or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return {"kind": "scalar", "value": None, "note": f"cannot compare {a} {how} {b}",
                "measure": "unknown", "unit": "unknown", "grain": "unknown"}

    def end_year(value):
        if value and value.get("kind") == "series" and value.get("rows"):
            try:
                return int(str(value["rows"][-1]["t"])[:4])
            except (ValueError, TypeError):
                return None
        return None

    oriented = ""
    ya, yb = end_year(left), end_year(right)
    same_entity = left.get("entity") is not None and left.get("entity") == right.get("entity")
    if same_entity and ya is not None and yb is not None and ya < yb:
        a, b = b, a
        left, right = right, left
        left_meta, right_meta = right_meta, left_meta
        oriented = " (oriented later-minus-earlier)"
    if how == "ratio" and b == 0:
        raise DataRequest("zero_denominator", {"how": how, "ask": "choose a non-zero denominator"})
    value = (a - b) if how == "difference" else (a / b)
    if how == "difference":
        measure, unit, grain = left_meta["measure"], left_meta["unit"], left_meta["grain"]
    else:
        measure = f"ratio:{left_meta['measure']}/{right_meta['measure']}"
        unit = f"{left_meta['unit']}/{right_meta['unit']}"
        grain = left_meta["grain"] if left_meta["grain"] == right_meta["grain"] else \
            f"proxy:{left_meta['grain']}/{right_meta['grain']}"
    lineage = {"operation": how,
               "left": {"measure": left_meta["measure"], "unit": left_meta["unit"],
                        "grain": left_meta["grain"], "lineage": left_meta["lineage"]},
               "right": {"measure": right_meta["measure"], "unit": right_meta["unit"],
                         "grain": right_meta["grain"], "lineage": right_meta["lineage"]}}
    vintage = {"left": left_meta["vintage"], "right": right_meta["vintage"]}
    alignment_note = (f"; exact common coverage {alignment['used_window'][0]}–"
                      f"{alignment['used_window'][1]}" if alignment else "")
    out = {"kind": "scalar", "value": value, "measure": measure, "unit": unit,
           "grain": grain, "lineage": lineage, "vintage": vintage,
           "note": f"{a} {how} {b} = {value}{oriented}{alignment_note}"}
    if left_meta["vintage"] != right_meta["vintage"] and (
            left_meta["vintage"] is not None or right_meta["vintage"] is not None):
        out["note"] += (f"; source vintages differ: left={left_meta['vintage']}, "
                        f"right={right_meta['vintage']}")
    if alignment:
        out["alignment"] = alignment
    if proxy:
        out["label"] = "proxy"
        out["grain_proxy"] = proxy
        out["note"] += "; declared grain proxy used"
    return out


def _gate(src, target, method):
    """Admissibility for ESTIMATE. v0: need enough source records; target near source extent."""
    rows = src.get("rows", [])
    n = len(rows)
    if n < 5:
        return {"pass": False, "reason": f"only {n} source records",
                "ask": "collect >=5 analog records before transferring"}
    # coverage: does target centroid fall within source bbox envelope?
    lats = [r["lat"] for r in rows if "lat" in r]
    lons = [r["lon"] for r in rows if "lon" in r]
    if lats and isinstance(target, dict) and "lat" in target:
        s, n2, w, e = min(lats), max(lats), min(lons), max(lons)
        inside = s - 1 <= target["lat"] <= n2 + 1 and w - 1 <= target["lon"] <= e + 1
        return {"pass": inside, "strength": "envelope",
                "reason": "target within source envelope" if inside else "target outside envelope",
                "ask": None if inside else "source records don't span the target; collect local data"}
    return {"pass": True, "strength": "count-only",
            "reason": f"{n} records, no geo check", "ask": None}


# ---- top level ---------------------------------------------------------------
def execute(ir, algebra_version=RELEASED_ALGEBRA_VERSION):
    ir = canonicalize(ir, algebra_version)
    rep = validate(ir, algebra_version)
    if not rep["valid"]:
        return {"status": "data_request", "reason": "parse_invalid",
                "detail": {"errors": rep["errors"]}, "provenance": []}
    if rep["unbound"]:
        return {"status": "data_request", "reason": "unbound_holes",
                "detail": {"holes": [h["name"] for h in rep["holes"]],
                           "ask": "clarify: " + ", ".join(sorted(set(h["name"] for h in rep["holes"])))},
                "provenance": []}
    prov, region_ctx = [], {}
    try:
        val = _ev(ir, prov, region_ctx)
    except DataRequest as dr:
        return {"status": "data_request", "reason": dr.reason, "detail": dr.detail,
                "provenance": prov}
    except (RuntimeError, KeyError, TypeError, ValueError) as e:
        return {"status": "error", "reason": type(e).__name__, "detail": {"msg": str(e)[:200]},
                "provenance": prov}
    return {"status": "answer", "value": val, "label": val.get("label", "observed"),
            "provenance": prov}


if __name__ == "__main__":
    import json
    import sys
    ir = json.load(sys.stdin)
    r = execute(ir)
    # trim rows for readability
    if r.get("value", {}).get("rows"):
        r["value"]["rows"] = r["value"]["rows"][:3]
    print(json.dumps(r, indent=2, default=str))
