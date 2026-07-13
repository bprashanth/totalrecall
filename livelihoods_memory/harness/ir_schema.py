"""IR schema validator — structural checks + hole collection for the algebra IR.

Deliberately permissive on values, strict on structure: the loop's job is to find where the
spec is wrong, so we validate the *shape* (op known, required inputs present, children are
nodes) and report holes, rather than rejecting anything unfamiliar. Returns a report the
scorer and executor both consume.

See ../algebra/ir-spec.md for the spec this checks (v0).
"""

KERNEL_OPS = {"SELECT", "ANNOTATE", "RELATE", "AGGREGATE", "COMPARE", "ESTIMATE", "RANK"}
SUPPORT_OPS = {"REGION"}
ALL_OPS = KERNEL_OPS | SUPPORT_OPS

# op -> (required scalar/leaf fields, required child-node fields)
REQUIRED = {
    "SELECT":    (["entity", "region", "time"], []),
    "ANNOTATE":  (["layer"], ["source"]),
    "RELATE":    (["relation"], ["left", "right"]),
    "AGGREGATE": (["by", "metric"], ["source"]),
    "COMPARE":   (["how"], ["left"]),  # 'right' required unless how==trend_direction (checked below)
    "ESTIMATE":  (["target", "method"], ["source"]),
    "RANK":      (["order"], []),  # items (a LIST of >=2 nodes) checked specially below
    "REGION":    (["place"], []),
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
    "REGION": {"op", "place"},
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
}


def is_hole(v):
    return isinstance(v, str) and v.startswith("?")


def _walk(node, path, errs, holes, ops, depth):
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
    if op not in ALL_OPS:
        errs.append(f"{path}: unknown op {op!r}")
        return
    ops.append(op)
    unknown = set(node) - ALLOWED_FIELDS[op]
    if unknown:
        errs.append(f"{path}: {op} has unknown field(s) {sorted(unknown)} — wrong op composed?")
    # Required leaf fields are not all enums, but they still have types. A dict in ANNOTATE.layer
    # passed the old validator and crashed the executor with "unhashable dict" in Round 2.
    string_fields = {("SELECT", "entity"), ("ANNOTATE", "layer"), ("REGION", "place")}
    for owner, field in string_fields:
        if op == owner and field in node and not is_hole(node[field]) \
                and not isinstance(node[field], str):
            errs.append(f"{path}: {op}.{field} must be a string, got {type(node[field]).__name__}")
    if op == "RELATE" and "threshold_km" in node and not isinstance(node["threshold_km"], (int, float)):
        errs.append(f"{path}: RELATE.threshold_km must be numeric")
    if op == "RANK" and "k" in node and (not isinstance(node["k"], int) or node["k"] <= 0):
        errs.append(f"{path}: RANK.k must be a positive integer")
    req_leaf, req_child = REQUIRED[op]
    # normalize language-boundary synonyms in place before vocab check
    if op == "RELATE" and isinstance(node.get("relation"), str):
        node["relation"] = canon_relation(node["relation"])
    for f in req_leaf:
        # SELECT.region is handled below (it may be a REGION node, not a leaf)
        if op == "SELECT" and f == "region":
            continue
        if f not in node:
            errs.append(f"{path}: {op} missing required field {f!r}")
        elif is_hole(node[f]):
            holes.append({"path": f"{path}.{f}", "op": op, "field": f, "name": node[f]})
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
            _walk(node[f], f"{path}.{f}", errs, holes, ops, depth + 1)
    # Frozen v2.1 declares these inputs as Records. Shape-only validation let scalar
    # AGGREGATE results enter RELATE and ESTIMATE, producing meaningless but executable trees.
    record_ops = {"SELECT", "ANNOTATE", "RELATE"}
    record_children = {
        "ANNOTATE": ("source",), "RELATE": ("left", "right"),
        "AGGREGATE": ("source",), "ESTIMATE": ("source",),
    }
    for field in record_children.get(op, ()):
        child = node.get(field)
        if isinstance(child, dict) and child.get("op") not in record_ops:
            errs.append(f"{path}: {op}.{field} requires Records, got {child.get('op')!r}")
    # RANK takes a LIST of >=2 item nodes (the n-ary op the binary COMPARE cannot express;
    # tick-008: both models degraded 3-way rankings by dropping cities or nesting COMPAREs).
    if op == "RANK":
        items = node.get("items")
        if not isinstance(items, list) or len(items) < 2:
            errs.append(f"{path}: RANK needs 'items' as a list of >=2 nodes")
        else:
            for i, it in enumerate(items):
                _walk(it, f"{path}.items[{i}]", errs, holes, ops, depth + 1)
    # COMPARE needs a 'right' operand for binary hows; trend_direction is unary (one series).
    if op == "COMPARE" and node.get("how") != "trend_direction":
        if "right" not in node:
            errs.append(f"{path}: COMPARE how={node.get('how')!r} needs a 'right' operand")
        elif is_hole(node["right"]):
            holes.append({"path": f"{path}.right", "op": op, "field": "right",
                          "name": node["right"]})
        else:
            _walk(node["right"], f"{path}.right", errs, holes, ops, depth + 1)
    elif op == "COMPARE" and "right" in node:
        errs.append(f"{path}: COMPARE how='trend_direction' is unary and must not have 'right'")
    # SELECT.region may be a REGION node or a leaf string/hole
    if op == "SELECT":
        reg = node.get("region")
        if isinstance(reg, dict):
            _walk(reg, f"{path}.region", errs, holes, ops, depth + 1)
        elif is_hole(reg):
            holes.append({"path": f"{path}.region", "op": op, "field": "region", "name": reg})
        elif reg is None:
            errs.append(f"{path}: SELECT missing required field 'region'")
    # ESTIMATE.target is a value-or-REGION slot, just like SELECT.region.  Merely checking the
    # required leaf above is insufficient: REGION{place:"?place"} otherwise looks like a bound
    # dict and can reach the geocoder.  Every nested hole must stop execution (spec v2.1).
    if op == "ESTIMATE":
        target = node.get("target")
        if isinstance(target, dict):
            if target.get("op") != "REGION":
                errs.append(f"{path}: ESTIMATE.target node must be REGION, got "
                            f"{target.get('op')!r}")
            _walk(target, f"{path}.target", errs, holes, ops, depth + 1)
        elif target is not None and not isinstance(target, str):
            errs.append(f"{path}: ESTIMATE.target must be a string or REGION node, got "
                        f"{type(target).__name__}")


def validate(ir):
    """Return {valid, errors, holes, ops, has_estimate, unbound}."""
    errs, holes, ops = [], [], []
    if not isinstance(ir, dict):
        return {"valid": False, "errors": ["root is not an object"], "holes": [],
                "ops": [], "has_estimate": False, "unbound": True}
    _walk(ir, "root", errs, holes, ops, 0)
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
