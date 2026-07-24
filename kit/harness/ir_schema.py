"""IR schema validator — structural checks + hole collection for the algebra IR.

Deliberately permissive on values, strict on structure: the loop's job is to find where the
spec is wrong, so we validate the *shape* (op known, required inputs present, children are
nodes) and report holes, rather than rejecting anything unfamiliar. Returns a report the
scorer and executor both consume.

See ../algebra/ir-spec.md for the spec this checks (v0).
"""

import json
import math

KERNEL_OPS = {"SELECT", "ANNOTATE", "RELATE", "AGGREGATE", "COMPARE", "ESTIMATE", "RANK"}
DRAFT_KERNEL_OPS = {"FILTER"}
RELEASED_SUPPORT_OPS = {"REGION"}
DRAFT_SUPPORT_OPS = {"BUFFER"}
RELEASED_ALGEBRA_VERSION = "v2.3.0"
BUFFER_ALGEBRA_VERSIONS = {"v2.4.0", "v2.4.0-draft"}


def buffer_enabled(algebra_version=None):
    return (algebra_version or RELEASED_ALGEBRA_VERSION) in BUFFER_ALGEBRA_VERSIONS


def allowed_ops(algebra_version=None):
    support = RELEASED_SUPPORT_OPS | (DRAFT_SUPPORT_OPS if buffer_enabled(algebra_version) else set())
    kernel = KERNEL_OPS | (DRAFT_KERNEL_OPS if buffer_enabled(algebra_version) else set())
    return kernel | support

# op -> (required scalar/leaf fields, required child-node fields)
REQUIRED = {
    "SELECT":    (["entity", "region", "time"], []),
    "ANNOTATE":  (["layer"], ["source"]),
    "RELATE":    (["relation"], ["left", "right"]),
    "AGGREGATE": (["by", "metric"], ["source"]),
    "COMPARE":   (["how"], ["left"]),  # 'right' required unless how==trend_direction (checked below)
    "ESTIMATE":  (["target", "method"], ["source"]),
    "RANK":      (["order"], []),  # items (a LIST of >=2 nodes) checked specially below
    "FILTER":    (["where"], ["source"]),
    "REGION":    (["place"], []),
    "BUFFER":    (["radius_km"], ["source"]),
}

# strict field sets: an unknown field on a known op is an ERROR, not noise — a parser that
# invents fields (e.g. AGGREGATE with a 'target') is composing the wrong op and must hear it.
ALLOWED_FIELDS = {
    "SELECT": {"op", "entity", "region", "time"},
    "ANNOTATE": {"op", "source", "layer"},
    "RELATE": {"op", "left", "right", "relation", "threshold_km"},
    "AGGREGATE": {"op", "source", "by", "metric"},
    "COMPARE": {"op", "left", "right", "how"},
    "ESTIMATE": {"op", "source", "target", "method"},
    "RANK": {"op", "items", "order", "k"},
    "FILTER": {"op", "source", "where"},
    "REGION": {"op", "place"},
    "BUFFER": {"op", "source", "radius_km"},
}

# Natural-language synonyms at the language boundary get NORMALIZED, not enumerated in the
# vocab (tick-003: the parser said "nearby" after we added "near" — alias whack-a-mole).
RELATION_SYNONYMS = {
    "near": "within", "nearby": "within", "close": "within", "close to": "within",
    "close_to": "within", "adjacent": "within", "next to": "within", "next_to": "within",
    "beside": "within", "around": "within", "in": "within", "inside": "within",
    "co-occur": "cooccur", "cooccurrence": "cooccur", "co_occur": "cooccur",
    "distance to": "distance", "distance_to": "distance", "how far": "distance",
    "not within": "beyond", "not_within": "beyond", "not near": "beyond",
    "away from": "beyond", "away_from": "beyond", "far from": "beyond", "without": "beyond",
    "outside": "beyond", "no": "beyond",
}


def canon_relation(v):
    if isinstance(v, str):
        return RELATION_SYNONYMS.get(v.lower().strip(), v)
    return v


VOCAB = {
    "order": {"desc", "asc"},
    "relation": {"distance", "within", "beyond", "cooccur"},  # beyond = complement of within (spec v2)
    "by": {"space", "time"},
    "metric": {"count", "density", "mean", "presence"},
    "how": {"difference", "ratio", "trend_direction"},
    "method": {"interpolate", "feature", "envelope"},
    "cmp": {"eq", "ne", "lt", "le", "gt", "ge", "contains"},
}


def is_hole(v):
    return isinstance(v, str) and v.startswith("?")


def _walk(node, path, errs, holes, ops, depth, active_ops):
    if depth > 12:
        errs.append(f"{path}: tree too deep (>12)")
        return
    if not isinstance(node, dict):
        errs.append(f"{path}: node is not an object ({type(node).__name__})")
        return
    op = node.get("op")
    if op is None:
        errs.append(f"{path}: missing 'op'")
        return
    if op not in active_ops:
        if op in {"BUFFER", "FILTER"}:
            errs.append(f"{path}: {op} requires algebra profile v2.4.0-draft or v2.4.0")
            return
        errs.append(f"{path}: unknown op {op!r}")
        return
    ops.append(op)
    unknown = set(node) - ALLOWED_FIELDS[op]
    if unknown:
        errs.append(f"{path}: {op} has unknown field(s) {sorted(unknown)} — wrong op composed?")
    req_leaf, req_child = REQUIRED[op]
    # normalize language-boundary synonyms in place before vocab check
    if op == "RELATE" and isinstance(node.get("relation"), str):
        node["relation"] = canon_relation(node["relation"])
    for f in req_leaf:
        # SELECT.region is handled below (it may be a REGION node, not a leaf)
        if (op == "SELECT" and f == "region") or (op == "ESTIMATE" and f == "target"):
            continue
        if f not in node:
            errs.append(f"{path}: {op} missing required field {f!r}")
        elif is_hole(node[f]):
            holes.append({"path": f"{path}.{f}", "op": op, "field": f, "name": node[f]})
        elif f == "entity" and isinstance(node[f], list):
            # v2.2 union: entity may be a list of names (holes allowed per element)
            if not node[f]:
                errs.append(f"{path}: entity list is empty")
            for i, x in enumerate(node[f]):
                if is_hole(x):
                    holes.append({"path": f"{path}.entity[{i}]", "op": op,
                                  "field": "entity", "name": x})
                elif not isinstance(x, str):
                    errs.append(f"{path}: entity[{i}] must be a string")
        elif isinstance(node[f], dict) and "op" not in node[f]:
            # holes NESTED in a plain value dict, e.g. time:{start:"?start_year"} — an
            # undetected nested hole once executed unbound and silently emptied the data
            for k, v in node[f].items():
                if is_hole(v):
                    holes.append({"path": f"{path}.{f}.{k}", "op": op,
                                  "field": f"{f}.{k}", "name": v})
        elif f in VOCAB and not isinstance(node[f], str):
            # a dict/list in an enum slot crashed the validator once (hard-bank, 2B) — a
            # validator REPORTS malformed input, it never raises on it
            errs.append(f"{path}: {op}.{f} must be a string, got {type(node[f]).__name__}")
        elif f in VOCAB and node[f] not in VOCAB[f] and not is_hole(node[f]):
            errs.append(f"{path}: {op}.{f}={node[f]!r} not in {sorted(VOCAB[f])}")
    for f in req_child:
        if f not in node:
            errs.append(f"{path}: {op} missing required child {f!r}")
        else:
            _walk(node[f], f"{path}.{f}", errs, holes, ops, depth + 1, active_ops)
    if op == "BUFFER":
        radius = node.get("radius_km")
        if (not is_hole(radius) and
                (not isinstance(radius, (int, float)) or isinstance(radius, bool) or
                 not math.isfinite(radius) or radius <= 0)):
            errs.append(f"{path}: BUFFER.radius_km must be a positive finite number")
        source = node.get("source")
        if isinstance(source, dict) and source.get("op") not in {"REGION", "BUFFER"}:
            errs.append(f"{path}: BUFFER.source must produce REGION support")
    if op == "FILTER":
        source = node.get("source")
        if isinstance(source, dict) and source.get("op") not in {
                "SELECT", "ANNOTATE", "RELATE", "FILTER"}:
            errs.append(f"{path}: FILTER.source must produce Records")
        where = node.get("where")
        if not isinstance(where, list) or not where:
            errs.append(f"{path}: FILTER.where must be a non-empty list")
        else:
            for index, predicate in enumerate(where):
                pred_path = f"{path}.where[{index}]"
                if not isinstance(predicate, dict):
                    errs.append(f"{pred_path}: predicate must be an object")
                    continue
                unknown_pred = set(predicate) - {"field", "cmp", "value"}
                if unknown_pred:
                    errs.append(f"{pred_path}: unknown predicate field(s) {sorted(unknown_pred)}")
                missing = {"field", "cmp", "value"} - set(predicate)
                if missing:
                    errs.append(f"{pred_path}: missing predicate field(s) {sorted(missing)}")
                    continue
                field, comparator, value = (predicate["field"], predicate["cmp"],
                                             predicate["value"])
                if is_hole(field):
                    holes.append({"path": f"{pred_path}.field", "op": op,
                                  "field": "where.field", "name": field})
                elif not isinstance(field, str) or not field:
                    errs.append(f"{pred_path}.field: must be a declared field name or typed hole")
                if not isinstance(comparator, str) or comparator not in VOCAB["cmp"]:
                    errs.append(f"{pred_path}.cmp: must be one of {sorted(VOCAB['cmp'])}")
                if isinstance(value, (dict, list)):
                    errs.append(f"{pred_path}.value: must be a literal or typed hole, never a subtree")
                elif is_hole(value):
                    holes.append({"path": f"{pred_path}.value", "op": op,
                                  "field": "where.value", "name": value})
    # RANK takes a LIST of >=2 item nodes (the n-ary op the binary COMPARE cannot express;
    # tick-008: both models degraded 3-way rankings by dropping cities or nesting COMPAREs).
    if op == "RANK":
        items = node.get("items")
        if not isinstance(items, list) or len(items) < 2:
            errs.append(f"{path}: RANK needs 'items' as a list of >=2 nodes")
        else:
            for i, it in enumerate(items):
                _walk(it, f"{path}.items[{i}]", errs, holes, ops, depth + 1, active_ops)
    # COMPARE needs a 'right' operand for binary hows; trend_direction is unary (one series).
    if op == "COMPARE" and node.get("how") != "trend_direction":
        if "right" not in node:
            errs.append(f"{path}: COMPARE how={node.get('how')!r} needs a 'right' operand")
        elif is_hole(node["right"]):
            holes.append({"path": f"{path}.right", "op": op, "field": "right",
                          "name": node["right"]})
        else:
            _walk(node["right"], f"{path}.right", errs, holes, ops, depth + 1, active_ops)
    # SELECT.region may be a REGION node or a leaf string/hole
    if op == "SELECT":
        reg = node.get("region")
        if isinstance(reg, dict):
            if reg.get("op") not in {"REGION", "BUFFER"}:
                errs.append(f"{path}: SELECT.region must be REGION or BUFFER support")
            _walk(reg, f"{path}.region", errs, holes, ops, depth + 1, active_ops)
        elif is_hole(reg):
            holes.append({"path": f"{path}.region", "op": op, "field": "region", "name": reg})
        elif reg is None:
            errs.append(f"{path}: SELECT missing required field 'region'")
    if op == "ESTIMATE":
        target = node.get("target")
        if isinstance(target, dict):
            if target.get("op") not in {"REGION", "BUFFER"}:
                errs.append(f"{path}: ESTIMATE.target must be REGION or BUFFER support")
            _walk(target, f"{path}.target", errs, holes, ops, depth + 1, active_ops)
        elif is_hole(target):
            holes.append({"path": f"{path}.target", "op": op, "field": "target",
                          "name": target})
        elif target is None:
            errs.append(f"{path}: ESTIMATE missing required field 'target'")


def canonicalize(ir, algebra_version=None):
    """Canonicalize IR without changing released-v2.3 behavior.

    Under the v2.4 draft, concrete nested BUFFER radii add, identical REGION/BUFFER values are
    interned, and nested FILTER predicates merge conjunctively in written order. These identities
    never invent support or predicates.
    """
    if not buffer_enabled(algebra_version):
        return ir
    interned = {}

    def walk(node):
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        out = {key: walk(value) for key, value in node.items()}
        if out.get("op") == "BUFFER":
            source = out.get("source")
            outer = out.get("radius_km")
            inner = source.get("radius_km") if isinstance(source, dict) else None
            if (isinstance(source, dict) and source.get("op") == "BUFFER" and
                    isinstance(outer, (int, float)) and not isinstance(outer, bool) and
                    math.isfinite(outer) and isinstance(inner, (int, float)) and
                    not isinstance(inner, bool) and math.isfinite(inner)):
                out = {"op": "BUFFER", "source": source["source"],
                       "radius_km": inner + outer}
        if out.get("op") == "FILTER":
            source = out.get("source")
            if isinstance(source, dict) and source.get("op") == "FILTER":
                out = {"op": "FILTER", "source": source.get("source"),
                       "where": list(source.get("where") or []) + list(out.get("where") or [])}
            out["where"] = sorted(out.get("where") or [],
                                  key=lambda item: json.dumps(item, sort_keys=True,
                                                              separators=(",", ":")))
        if out.get("op") in {"REGION", "BUFFER"}:
            key = json.dumps(out, sort_keys=True, separators=(",", ":"))
            if key in interned:
                return interned[key]
            interned[key] = out
        return out

    return walk(ir)


def validate(ir, algebra_version=None):
    """Return {valid, errors, holes, ops, has_estimate, unbound}."""
    errs, holes, ops = [], [], []
    if not isinstance(ir, dict):
        return {"valid": False, "errors": ["root is not an object"], "holes": [],
                "ops": [], "has_estimate": False, "unbound": True}
    _walk(ir, "root", errs, holes, ops, 0, allowed_ops(algebra_version))
    return {
        "valid": len(errs) == 0,
        "errors": errs,
        "holes": holes,
        "ops": ops,
        "has_estimate": "ESTIMATE" in ops,
        "unbound": len(holes) > 0,
    }


if __name__ == "__main__":
    import json
    import sys
    ir = json.load(sys.stdin)
    print(json.dumps(validate(ir), indent=2))
