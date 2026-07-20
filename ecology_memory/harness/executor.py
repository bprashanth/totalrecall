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
import math
import statistics
from ir_schema import canonicalize, validate, is_hole
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


def _route_select(entity, region, time, prov):
    resolution = C.resolve_ecology_entity(entity)
    route = "unresolved"
    if resolution and resolution.get("kind") == "unsupported_measure":
        raise DataRequest("unsupported_measure", {"entity": entity, "hint": resolution["note"]})
    if resolution and resolution.get("kind") in {"ambiguous", "unverified_taxon"}:
        raise DataRequest("ambiguous_entity", {"entity": entity, **resolution})
    try:
        if resolution and resolution.get("kind") == "taxon":
            route = "origin-points"
            out = C.taxon_occurrences(entity, region, time)
        elif resolution and resolution.get("kind") == "taxon_group":
            route = "gbif+inaturalist-higher-taxon"
            out = C.taxon_group_occurrences(resolution, region, time)
        elif resolution and resolution.get("kind") == "taxon_group_transfer":
            route = "dynamic-higher-taxon-transfer-audit"
            out = C.arachnid_transfer_evidence(region)
        elif resolution and resolution.get("kind") == "taxon_inventory":
            route = "published-taxon-inventory"
            out = C.published_taxon_inventory(resolution, region, time)
        elif resolution and resolution.get("kind") == "published_site_evidence":
            route = "published-site-evidence"
            out = C.published_site_evidence(resolution, region, time)
        elif resolution and resolution.get("kind") == "soil_wetness_proxy":
            route = "nasa-power-merra2"
            out = C.nasa_power_soil_wetness(region, 2024)
        elif resolution and resolution.get("kind") == "ebird":
            route = "ebird"
            out = C.ebird_recent(region, time)
        elif resolution and resolution.get("kind") == "survey_sites":
            route = "zenodo-survey-sites"
            out = C.anamalai_survey_sites(region)
        elif resolution and resolution.get("kind") == "site_point":
            route = "site-metadata"
            out = C.site_center(region)
        elif resolution and resolution.get("kind") == "series" \
                and resolution.get("canonical") == "ndvi":
            route = "earth-engine-ndvi"
            out = C.ee_ndvi_series(region, time)
        else:
            out = None
            route = "none"
    except Exception as e:
        prov.append({"op": "SELECT", "route": "source-error", "entity": entity,
                     "note": f"{type(e).__name__}: {str(e)[:160]}"})
        raise DataRequest("source_unavailable", {"entity": entity, "source": route,
                                                  "error": str(e)[:160]})
    if out is not None:
        if out.get("unavailable"):
            raise DataRequest("source_unavailable", {"entity": entity, "source": out["source"],
                                                      "error": out["unavailable"]})
        if out.get("unsupported_time"):
            raise DataRequest("unsupported_time", {"entity": entity, "source": out["source"],
                                                    "hint": out["note"]})
        for event in out.get("connector_events") or []:
            prov.append({"op": "CONNECTOR", **event})
        prov.append({"op": "SELECT", "route": route,
                     "resolved": resolution.get("canonical"), "note": out["note"]})
        return {**out, "entity": resolution.get("canonical"), "input_entity": entity}
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
            if len({p["kind"] for p in parts}) != 1:
                raise DataRequest("incompatible_union",
                                  {"entities": ent, "kinds": [p["kind"] for p in parts]})
            seen, rows = set(), []
            for p in parts:
                for r in p.get("rows", []):
                    k = r.get("id") or (r.get("lat"), r.get("lon"), r.get("name"))
                    if k not in seen:
                        seen.add(k)
                        rows.append(r)
            val = {"kind": parts[0]["kind"], "rows": rows, "entity": ent,
                   "label": _merge_label(*[p["label"] for p in parts]), "source": "union",
                   "grain": parts[0].get("grain"),
                   "count_admissible": all(p.get("count_admissible", False) for p in parts),
                   "region": region, "query_time": node.get("time")}
            prov.append({"op": "SELECT", "route": "union",
                         "note": f"union of {ent} -> {len(rows)} rows"})
        else:
            val = _route_select(ent, region, node.get("time"), prov)
        if not val["rows"]:
            raise DataRequest("empty_select",
                              {"entity": node["entity"], "region": region["name"],
                               "hint": "no records at this place; transfer or collect",
                               "evidence_discovery": val.get("evidence_discovery") or [],
                               "connector_events": val.get("connector_events") or []})
        return val

    if op == "ANNOTATE":
        src = _ev(node["source"], prov, region_ctx)
        if src.get("kind") != "records":
            raise DataRequest("incompatible_grain",
                              {"op": "ANNOTATE", "kind": src.get("kind"),
                               "hint": "ANNOTATE currently requires point records"})
        try:
            out = C.annotate_records(src.get("rows", []), node["layer"], src.get("query_time"),
                                     src.get("region"))
        except Exception as e:
            prov.append({"op": "ANNOTATE", "layer": node["layer"],
                         "note": f"{type(e).__name__}: {str(e)[:160]}"})
            raise DataRequest("source_unavailable", {"layer": node["layer"],
                                                      "error": str(e)[:160]})
        if out.get("unsupported_layer"):
            raise DataRequest("no_connector", {"layer": node["layer"], "hint": out["note"]})
        prov.append({"op": "ANNOTATE", "layer": out.get("layer") or node["layer"],
                     "source": out["source"], "note": out["note"]})
        return {**src, **out, "label": _merge_label(src["label"], out["label"]),
                "source": f"{src['source']} + {out['source']}"}

    if op == "RELATE":
        left = _ev(node["left"], prov, region_ctx)
        right = _ev(node["right"], prov, region_ctx)
        if left.get("kind") != "records" or right.get("kind") != "records":
            raise DataRequest("incompatible_grain", {
                "op": "RELATE", "left_kind": left.get("kind"),
                "right_kind": right.get("kind"),
                "hint": "RELATE requires two georeferenced record sets"})
        rel = node["relation"]
        thresh = node.get("threshold_km")
        rows = _relate(left.get("rows", []), right.get("rows", []), rel, thresh)
        reverse_rows = _relate(right.get("rows", []), left.get("rows", []), rel, thresh)
        effective_threshold = (thresh if isinstance(thresh, (int, float)) and thresh > 0 else
                               (5.0 if rel == "cooccur" else
                                1.0 if rel in {"within", "beyond"} else None))
        prov.append({"op": "RELATE", "relation": rel, "threshold_km": thresh,
                     "note": (f"{len(left.get('rows',[]))} left x "
                              f"{len(right.get('rows',[]))} right -> {len(rows)} matched left and "
                              f"{len(reverse_rows)} matched right; "
                              "occurrence proximity is not interaction or simultaneous observation")})
        return {"kind": "records", "rows": rows,
                "label": "proxy", "source": "deterministic occurrence-point relation",
                "grain": "occurrence-proximity-relation", "relation": rel,
                "threshold_km": effective_threshold,
                "left_entity": left.get("input_entity") or left.get("entity"),
                "right_entity": right.get("input_entity") or right.get("entity"),
                "left_record_count": len(left.get("rows", [])),
                "right_record_count": len(right.get("rows", [])),
                "matched_left_count": len(rows),
                "matched_right_count": len(reverse_rows),
                "matched_left_fraction": round(len(rows) / len(left.get("rows", [])), 4)
                if left.get("rows") else None,
                "matched_right_fraction": round(len(reverse_rows) / len(right.get("rows", [])), 4)
                if right.get("rows") else None,
                "matched_left_percent": round(100 * len(rows) / len(left.get("rows", [])), 1)
                if left.get("rows") else None,
                "matched_right_percent": round(100 * len(reverse_rows) / len(right.get("rows", [])), 1)
                if right.get("rows") else None,
                "left_region": left.get("region"), "right_region": right.get("region"),
                "temporal_alignment": "not established",
                "note": ("spatial proximity among occurrence records; not evidence of ecological "
                         "interaction, same-time co-observation, abundance, or site presence")}

    if op == "AGGREGATE":
        src = _ev(node["source"], prov, region_ctx)
        out = _aggregate(src, node["by"], node["metric"])
        prov.append({"op": "AGGREGATE", "by": node["by"], "metric": node["metric"],
                     "note": out["note"]})
        return {**out, "label": out.get("label", src["label"]),
                "entity": src.get("entity"), "source": src.get("source")}

    if op == "COMPARE":
        left = _ev(node["left"], prov, region_ctx)
        right = _ev(node["right"], prov, region_ctx) if "right" in node else None
        out = _compare(left, right, node["how"])
        if right is not None:
            out["left_label"] = _item_label(node["left"])
            out["right_label"] = _item_label(node["right"])
            out["left_value"] = _scalarize(left)
            out["right_value"] = _scalarize(right)
            if (node["how"] == "difference" and
                    isinstance(out["left_value"], (int, float)) and
                    isinstance(out["right_value"], (int, float)) and
                    out["left_label"] != out["right_label"]):
                out["winner"] = (out["left_label"] if out["left_value"] > out["right_value"] else
                                 out["right_label"] if out["right_value"] > out["left_value"] else
                                 "tie")
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
        if src.get("grain") == "occurrence-proximity-relation":
            raise DataRequest("unsupported_relational_transfer", {
                "method": node["method"],
                "reason": "joint relation transfer has no admitted sampling or gate contract",
                "ask": ("estimate each taxon independently with declared donor occurrence data, "
                        "or collect aligned interaction/co-observation data at the target")})
        target = _resolve_region(node["target"], prov)
        try:
            out = C.estimate_transfer(src, target, node["method"])
        except Exception as e:
            prov.append({"op": "ESTIMATE", "method": node["method"],
                         "note": f"{type(e).__name__}: {str(e)[:160]}"})
            raise DataRequest("source_unavailable", {"method": node["method"],
                                                       "error": str(e)[:160]})
        gate = out["gate"]
        prov.append({"op": "ESTIMATE", "method": node["method"], "gate": gate})
        if not gate["pass"]:
            raise DataRequest("gate_failed",
                              {"method": node["method"], "reason": gate["reason"],
                               "ask": gate["ask"]})
        prov.append({"op": "ESTIMATE", "method": node["method"], "source": out["source"],
                     "note": out["note"]})
        return {**out,
                "donor_entity": src.get("input_entity") or src.get("entity"),
                "donor_region": src.get("region"),
                "donor_record_count": len(src.get("rows", [])),
                "target_region": target}

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
        if by == "space" and metric == "mean" and len(rows) == 1:
            return {"kind": "scalar", "value": rows[0].get("value"), "unit": src.get("unit"),
                    "note": "single aligned place-time value"}
        if by != "time":
            raise DataRequest("incompatible_grain", {"kind": "series", "by": by})
        # SELECT series already has one aligned quantity per time bin.
        return {"kind": "series", "rows": rows, "unit": src.get("unit"),
                "note": f"passthrough aligned series ({len(rows)} points)"}
    if by == "time":
        if metric == "count" and src.get("grain") == "occurrence" \
                and not src.get("count_admissible"):
            raise DataRequest("unsupported_measure",
                              {"entity": src.get("input_entity") or src.get("entity"),
                               "hint": "ask for occurrence records/sightings explicitly; record "
                                       "counts are not organism abundance"})
        bins = {}
        for r in rows:
            t = (r.get("time") or "")[:4]
            if not t:
                continue
            if metric == "mean":
                field = src.get("measure_field")
                value = r.get(field) if field else None
                if isinstance(value, (int, float)):
                    bins.setdefault(t, []).append(value)
            else:
                bins[t] = bins.get(t, 0) + 1
        if metric == "mean":
            series = [{"t": k, "value": statistics.fmean(v)} for k, v in sorted(bins.items())]
        elif metric == "presence":
            series = [{"t": k, "value": bool(v)} for k, v in sorted(bins.items())]
        else:
            series = [{"t": k, "value": v} for k, v in sorted(bins.items())]
        label = "proxy" if src.get("grain") in {"occurrence", "checklist-observation"} else src["label"]
        return {"kind": "series", "rows": series, "label": label,
                "note": f"binned to {len(series)} years"
                        + ("; record-count trend is sampling-effort biased" if label == "proxy" else "")}
    # by space
    if metric == "count":
        if src.get("grain") == "occurrence" and not src.get("count_admissible"):
            raise DataRequest("unsupported_measure",
                              {"entity": src.get("input_entity") or src.get("entity"),
                               "hint": "occurrence records establish presence, not the number of organisms; "
                                       "ask for record count explicitly or provide a designed survey"})
        return {"kind": "scalar", "value": len(rows), "note": f"count={len(rows)}"}
    if metric == "presence":
        return {"kind": "scalar", "value": bool(rows), "note": f"presence={bool(rows)}"}
    if metric == "density":
        if src.get("grain") == "occurrence" and not src.get("count_admissible"):
            raise DataRequest("unsupported_measure",
                              {"entity": src.get("input_entity") or src.get("entity"),
                               "hint": "organism density needs survey effort/area, not occurrence records"})
        region = src.get("region") or {}
        bbox = region.get("bbox")
        if not bbox:
            raise DataRequest("missing_area", {"hint": "density needs a bounded region"})
        s, n, w, e = bbox
        mid = (s + n) / 2
        area = max(1e-9, 111.32 * (n - s) * 111.32 * math.cos(math.radians(mid)) * (e - w))
        value = len(rows) / area
        return {"kind": "scalar", "value": value, "unit": "records/km2", "label": "proxy",
                "note": f"{len(rows)}/{area:.2f} bbox km2={value:.4g}; bbox-area proxy"}
    if metric == "mean":
        field = src.get("measure_field")
        if not field:
            raise DataRequest("missing_measure",
                              {"hint": "mean requires a numeric annotation or measurement series"})
        values = [r.get(field) for r in rows if isinstance(r.get(field), (int, float))]
        if not values:
            raise DataRequest("empty_measure", {"field": field})
        return {"kind": "scalar", "value": statistics.fmean(values), "unit": src.get("unit"),
                "note": f"mean {field} over {len(values)} records"}
    raise DataRequest("unsupported_metric", {"metric": metric})


def _compare(left, right, how):
    if how == "trend_direction":
        rows = left.get("rows", [])
        if len(rows) < 2:
            return {"kind": "scalar", "value": None, "note": "insufficient points for trend"}
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
    # anchors differ AND both values resolve to the same entity, orient later-minus-earlier
    # deterministically and stamp it in provenance. Cross-entity ratios preserve operand order;
    # differing source end-years must never silently invert the requested denominator.
    def end_year(v):
        if v and v.get("kind") == "series" and v.get("rows"):
            try:
                return int(str(v["rows"][-1]["t"])[:4])
            except (ValueError, TypeError):
                return None
        return None
    oriented = ""
    ya, yb = end_year(left), end_year(right)
    same_entity = left.get("entity") is not None and left.get("entity") == right.get("entity")
    if same_entity and ya is not None and yb is not None and ya < yb:
        a, b = b, a
        oriented = " (oriented later-minus-earlier)"
    val = (a - b) if how == "difference" else (a / b if b else None)
    return {"kind": "scalar", "value": val, "note": f"{a} {how} {b} = {val}{oriented}"}


def _gate(src, target, method):
    """Compatibility wrapper; the admitted gate lives with the ecology connectors."""
    return C.transfer_gate(src, target, method)


# ---- top level ---------------------------------------------------------------
def execute(ir):
    ir = canonicalize(ir)
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
    except RuntimeError as e:
        return {"status": "data_request", "reason": "source_unavailable",
                "detail": {"error": str(e)[:200]}, "provenance": prov}
    except (KeyError, TypeError, ValueError) as e:
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
