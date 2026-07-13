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
from ir_schema import validate, is_hole
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


def _resolve_region(region):
    try:
        if isinstance(region, dict) and region.get("op") == "REGION":
            return C.resolve_region(region["place"])
        if isinstance(region, str) and not is_hole(region):
            return C.resolve_region(region)
    except (RuntimeError, ValueError, KeyError, TypeError) as exc:
        # Connector/geocoder failures are evidence gaps, not harness crashes.  Keep the original
        # requested scope in the DataRequest so a caller can clarify or add a region connector.
        raise DataRequest("unresolved_region", {"region": region, "error": str(exc)}) from exc
    raise DataRequest("unresolved_region", {"region": region})


# entity routing: try each source's resolver; first that matches wins. A World Bank indicator
# (economy/development series) takes priority; otherwise an OSM point entity (civic amenities).
def _route_select(entity, region, time, prov):
    # Curated ILOSTAT survey series. This precedes broad token resolvers because its subgroup
    # phrases are deliberately exact under frozen v2.1 (which has no FILTER operator).
    ilo_spec, ilo_canon, _ = C.ilo_resolve_indicator(entity)
    if ilo_spec:
        if not C.wb_resolve_iso(region):
            prov.append({"op":"SELECT", "route":"ilostat", "resolved":ilo_canon,
                         "note":"national indicator rejected for non-country scope"})
            raise DataRequest("national_scope_required",
                              {"entity":entity, "region":region.get("orig") or region.get("name"),
                               "source":"ilostat"})
        out = C.ilo_series(entity, region, time)
        prov.append({"op": "SELECT", "route": "ilostat", "resolved": ilo_canon,
                     "indicator": out.get("indicator"), "unit": out.get("unit"),
                     "source_code": out.get("source_code"), "note": out["note"]})
        return {"kind": "series", "rows": out["rows"], "label": "observed",
                "source": out["source"], "ambiguous": out.get("source_alternatives", [])}
    # Eurostat is intentionally scoped to curated NUTS-2 regions. This prevents its generic
    # "unemployment rate" phrase from stealing national World Bank questions.
    euro_spec, euro_canon, _ = C.eurostat_resolve_indicator(entity)
    euro_geo = C.eurostat_resolve_geo(region)
    if euro_spec and euro_geo:
        out = C.eurostat_series(entity, region, time)
        prov.append({"op": "SELECT", "route": "eurostat", "resolved": euro_canon,
                     "dataset": out.get("dataset"), "geo": out.get("geo"),
                     "unit": out.get("unit"), "note": out["note"]})
        return {"kind": "series", "rows": out["rows"], "label": "observed",
                "source": out["source"], "ambiguous": []}
    # world bank indicator?
    code, canon, ambig = C.wb_resolve_indicator(entity)
    if code:
        if not C.wb_resolve_iso(region):
            prov.append({"op":"SELECT", "route":"worldbank", "resolved":canon,
                         "note":"national indicator rejected for non-country scope"})
            raise DataRequest("national_scope_required",
                              {"entity":entity, "region":region.get("orig") or region.get("name"),
                               "source":"worldbank"})
        out = C.wb_series(entity, region, time)
        prov.append({"op": "SELECT", "route": "worldbank", "resolved": canon,
                     "ambiguous": ambig, "note": out["note"]})
        return {"kind": "series", "rows": out["rows"], "label": "observed",
                "source": out["source"], "ambiguous": ambig}
    # osm point entity?
    tag, ocanon, oambig = C.osm_resolve_tag(entity)
    if tag:
        out = C.osm_select(entity, region)
        prov.append({"op": "SELECT", "route": "osm", "resolved": ocanon,
                     "ambiguous": oambig, "note": out["note"]})
        if out.get("truncated"):
            raise DataRequest("source_truncated",
                              {"entity": entity, "region": region.get("name"),
                               "hint": out["note"]})
        return {"kind": "records", "rows": out["rows"], "label": "observed",
                "source": out["source"], "ambiguous": oambig}
    # no connector maps this entity -> honest data gap (never fabricate)
    prov.append({"op": "SELECT", "route": "none", "note": f"no connector for {entity!r}"})
    raise DataRequest("no_connector",
                      {"entity": entity,
                       "hint": "no data source maps this entity; add a connector or refine the term"})


def _ev(node, prov, region_ctx):
    op = node["op"]

    if op == "REGION":
        return {"kind": "region", "value": _resolve_region(node), "label": "observed"}

    if op == "SELECT":
        region = _resolve_region(node["region"])
        region_ctx["region"] = region
        val = _route_select(node["entity"], region, node.get("time"), prov)
        if not val["rows"]:
            raise DataRequest("empty_select",
                              {"entity": node["entity"], "region": region["name"],
                               "hint": "no records at this place; transfer or collect"})
        return val

    if op == "ANNOTATE":
        src = _ev(node["source"], prov, region_ctx)
        nonnull = 0
        for r in src.get("rows", []):
            value = (r.get("attrs") or {}).get(node["layer"])
            r[node["layer"]] = value
            nonnull += value is not None
        prov.append({"op": "ANNOTATE", "layer": node["layer"],
                     "note": (f"annotated {len(src.get('rows',[]))} rows from existing record "
                              f"attributes with {node['layer']}; {nonnull} non-null")})
        if src.get("rows") and nonnull == 0:
            raise DataRequest("annotation_unavailable",
                              {"layer": node["layer"],
                               "hint": "the requested field is absent from every source record"})
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
        out = _aggregate(src, node["by"], node["metric"], region_ctx.get("region"))
        prov.append({"op": "AGGREGATE", "by": node["by"], "metric": node["metric"],
                     "note": out["note"]})
        return {**out, "label": src["label"]}

    if op == "COMPARE":
        left = _ev(node["left"], prov, region_ctx)
        right = _ev(node["right"], prov, region_ctx) if "right" in node else None
        out = _compare(left, right, node["how"])
        prov.append({"op": "COMPARE", "how": node["how"], "note": out["note"]})
        labels = [left["label"]] + ([right["label"]] if right else [])
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
        rev = node.get("order", "desc") == "desc"
        scored.sort(key=lambda r: r["value"], reverse=rev)
        k = node.get("k")
        if isinstance(k, int) and k > 0:
            scored = scored[:k]
        prov.append({"op": "RANK", "order": node.get("order"),
                     "note": " > ".join(f"{r['label']}={r['value']}" for r in scored)})
        return {"kind": "ranking", "rows": scored,
                "label": _merge_label(*[v["label"] for v in vals]), "source": "rank"}

    if op == "ESTIMATE":
        src = _ev(node["source"], prov, region_ctx)
        target = _resolve_region(node["target"]) if not isinstance(node["target"], dict) or \
            node["target"].get("op") == "REGION" else node["target"]
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


def _aggregate(src, by, metric, region=None):
    rows = src.get("rows", [])
    if src["kind"] == "series":
        # The frozen canonical identity is ONLY mean-by-time over an already-series SELECT.
        # Passing count/density/space through unchanged made wrong statistical parses execute green.
        if by == "time" and metric == "mean":
            return {"kind": "series", "rows": rows,
                    "note": f"identity mean-by-time series ({len(rows)} pts)"}
        raise DataRequest("aggregate_type_mismatch",
                          {"kind": "series", "by": by, "metric": metric,
                           "hint": "only mean by time is an identity over an existing series"})
    if by == "time":
        bins = {}
        for r in rows:
            t = (r.get("time") or "")[:4]
            if not t:
                continue
            bins[t] = bins.get(t, 0) + 1
        series = [{"t": k, "value": v} for k, v in sorted(bins.items())]
        return {"kind": "series", "rows": series, "note": f"binned to {len(series)} years"}
    # by space
    if metric == "count":
        return {"kind": "scalar", "value": len(rows), "note": f"count={len(rows)}"}
    if metric == "presence":
        return {"kind": "scalar", "value": bool(rows),
                "note": f"presence={bool(rows)} from {len(rows)} records"}
    if metric == "density":
        # Density needs an area denominator. Tick-001 exposed the stock placeholder returning
        # a raw count while synthesis called it "per unit area". Use the resolved REGION bbox,
        # and state the bbox approximation explicitly in provenance.
        bb = region.get("bbox") if isinstance(region, dict) else None
        if not isinstance(bb, list) or len(bb) != 4:
            raise DataRequest("density_area_missing",
                              {"hint": "a resolved region bbox is required for density"})
        from math import cos, radians
        south, north, west, east = bb
        height_km = abs(north - south) * 111.32
        width_km = abs(east - west) * 111.32 * cos(radians((south + north) / 2))
        area_km2 = height_km * width_km
        if area_km2 <= 0:
            raise DataRequest("density_area_missing", {"hint": "region bbox has zero area"})
        value = len(rows) / area_km2
        return {"kind": "scalar", "value": value,
                "note": (f"density={value:.6g} records/km^2 from {len(rows)} records over "
                         f"{area_km2:.3f} km^2 bbox (bbox-area approximation)")}
    if metric == "mean":
        # RELATE(distance) declares its measured column as dist_km.  Do not average arbitrary
        # numeric record fields (ids/coordinates are numeric too), and never fall through to a
        # row count: that silently answered "mean distance" with N in H22.
        values = [r.get("dist_km") for r in rows if isinstance(r.get("dist_km"), (int, float))]
        if not values:
            raise DataRequest("mean_value_missing",
                              {"field": "dist_km",
                               "hint": "spatial mean requires a numeric distance relation"})
        value = statistics.mean(values)
        return {"kind": "scalar", "value": value,
                "note": f"mean dist_km={value:.6g} from {len(values)} records"}
    return {"kind": "scalar", "value": len(rows), "note": f"n={len(rows)}"}


def _compare(left, right, how):
    if how == "trend_direction":
        rows = left.get("rows", [])
        if len(rows) < 2:
            raise DataRequest("insufficient_series",
                              {"points": len(rows),
                               "hint": "trend direction requires at least two observations"})
        xs = list(range(len(rows)))
        ys = [r["value"] for r in rows]
        # simple least-squares slope sign
        n = len(xs)
        mx, my = sum(xs) / n, sum(ys) / n
        denom = sum((x - mx) ** 2 for x in xs) or 1
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / denom
        direction = "rising" if slope > 0 else "falling" if slope < 0 else "flat"
        pct = (ys[-1] - ys[0]) / (abs(ys[0]) or 1) * 100
        return {"kind": "scalar", "value": direction,
                "note": f"{direction} (slope={slope:.4g}, {pct:+.1f}% over {n} pts "
                        f"{rows[0]['t']}→{rows[-1]['t']})"}
    # difference / ratio between two scalars or two series endpoints
    def scal(v):
        if v is None:
            return None
        if v["kind"] == "scalar":
            return v["value"]
        if v["kind"] == "series" and v.get("rows"):
            return v["rows"][-1]["value"]
        if v["kind"] in ("records", "field"):
            return len(v.get("rows", []))
        return None
    a, b = scal(left), scal(right)
    if a is None or b is None or not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
        return {"kind": "scalar", "value": None, "note": f"cannot compare {a} {how} {b}"}
    # ORIENTATION (adopted from transport sector, spec v2->v2.1): "change t1->t2" compiles with
    # operands in QUESTION order — a defensible parse whose sign is opposite the gold's, silently
    # producing "decreased" for a series that grew. When both operands expose a time anchor and the
    # anchors differ, orient later-minus-earlier deterministically and stamp it in provenance.
    def end_year(v):
        if v and v.get("kind") == "series" and v.get("rows"):
            try:
                return int(str(v["rows"][-1]["t"])[:4])
            except (ValueError, TypeError):
                return None
        return None
    oriented = ""
    ya, yb = end_year(left), end_year(right)
    if ya is not None and yb is not None and ya < yb:
        a, b = b, a
        oriented = " (oriented later-minus-earlier)"
    val = (a - b) if how == "difference" else (a / b if b else None)
    return {"kind": "scalar", "value": val, "note": f"{a} {how} {b} = {val}{oriented}"}


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
def execute(ir):
    rep = validate(ir)
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
