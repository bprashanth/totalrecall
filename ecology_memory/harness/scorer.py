"""Scorer — grade a produced IR + its execution against gold.

Scores are BEHAVIORAL and STRUCTURAL, matching the algebra's claim that correctness lives in
the tree, not the prose:
  parse_valid    produced parseable JSON
  schema_valid   passes the IR schema
  shape_match    the multiset of ops equals gold_shape (the core: did it pick the right algebra?)
  holes_correct  produced holes iff the question is ambiguous (must_hole)
  estimate_ok    used ESTIMATE iff the question is a transfer (must_estimate)
  exec_class     executor outcome class == expected (answer | data_request)
  exec_grounded  an 'answer' actually carried rows/value (not empty)

overall = weighted mean in [0,1]. The trap we avoid (improvement-loop.md): scoring only content.
Here structure + behavior dominate, and an optional LLM judge is a tiebreaker, not the score.
"""
from collections import Counter
import json
import re
from ir_schema import validate


def _shape(ir):
    """multiset of SKELETON ops in the tree, NORMALIZED (tick-005/006 spec finding):
    - REGION excluded (plumbing)
    - AGGREGATE excluded entirely: it is implicit type coercion. Over a series it's an
      identity; before a COMPARE of record sets the count is demanded by the output type
      (COMPARE(recs,recs) ≡ COMPARE(AGG count, AGG count)). The skeleton that carries the
      question's meaning is SELECT/RELATE/COMPARE/ESTIMATE/ANNOTATE; wrong metrics surface
      via execution, not shape."""
    if not isinstance(ir, dict):
        return Counter()
    ops = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
            return
        if not isinstance(n, dict):
            return
        op = n.get("op")
        if op and op not in ("REGION", "AGGREGATE"):
            ops.append(op)
        for v in n.values():
            if isinstance(v, (dict, list)):
                walk(v)
    walk(ir)
    return Counter(ops)


def _walk(ir):
    if isinstance(ir, dict):
        yield ir
        for value in ir.values():
            yield from _walk(value)
    elif isinstance(ir, list):
        for value in ir:
            yield from _walk(value)


def _normal_entity(value):
    """Normalize connector-grain decoration without erasing the requested measure.

    `documented Lantana occurrences` and `Lantana records` route to the same occurrence
    connector, but `elephants` and `elephant population` do not. This deliberately keeps
    ecological measures such as population, abundance, NDVI and density.
    """
    text = re.sub(r"[^a-z0-9 ]+", " ", str(value).lower())
    words = [w for w in text.split() if w not in {
        "all", "both", "carried", "data", "documented", "for", "locations", "of", "out",
        "published", "occurrence", "occurrences",
        "observation", "observations", "record", "records", "sighting", "sightings",
    }]
    words = [{"elephants": "elephant", "frogs": "frog", "sites": "site",
              "surveys": "survey"}.get(w, w)
             for w in words]
    return " ".join(words)


def _entities(ir):
    out = []
    for node in _walk(ir):
        if node.get("op") != "SELECT":
            continue
        value = node.get("entity")
        for item in value if isinstance(value, list) else [value]:
            if item is not None and not str(item).startswith("?"):
                out.append(_normal_entity(item))
    return [x for x in out if x]


def _entity_contains(required, produced):
    """One-to-one token containment allows connector qualifiers without losing union members."""
    remaining = list(produced)
    for wanted in required:
        want_tokens = set(wanted.split())
        found = None
        for index, got in enumerate(remaining):
            if want_tokens.issubset(set(got.split())):
                found = index
                break
        if found is None:
            return False
        remaining.pop(found)
    return True


def _places(ir):
    return [
        re.sub(r"\s+", " ", str(node.get("place")).strip(" .").lower())
        for node in _walk(ir)
        if node.get("op") == "REGION" and node.get("place") and
        not str(node.get("place")).startswith("?")
    ]


def _place_contains(required, produced):
    """Allow a missing geocoder-added qualifier, but never accept conflicting qualifiers."""
    remaining = list(produced)
    for wanted in required:
        wp = [x.strip() for x in wanted.split(",") if x.strip()]
        found = None
        for index, got in enumerate(remaining):
            gp = [x.strip() for x in got.split(",") if x.strip()]
            if not wp or not gp or wp[0] != gp[0]:
                continue
            if len(wp) > 1 and len(gp) > 1 and wp[1:] != gp[1:]:
                continue
            found = index
            break
        if found is None:
            return False
        remaining.pop(found)
    return True


def _relations(ir):
    return [
        (node.get("relation"), None if node.get("threshold_km") is None else
         round(float(node["threshold_km"]), 6))
        for node in _walk(ir) if node.get("op") == "RELATE"
    ]


def _aggregates(ir):
    return Counter(
        (node.get("by"), node.get("metric"))
        for node in _walk(ir) if node.get("op") == "AGGREGATE"
    )


def _params(ir, op, *fields):
    def normal(field, value):
        if op == "ANNOTATE" and field == "layer" and isinstance(value, str):
            layer = re.sub(r"[-_\s]+", " ", value.strip().lower())
            return {"terrain slope": "slope", "landcover": "land cover"}.get(layer, layer)
        return value
    return Counter(
        tuple(json.dumps(normal(field, node.get(field)), sort_keys=True) for field in fields)
        for node in _walk(ir) if node.get("op") == op
    )


def _contains(required, produced):
    return all(produced[item] >= count for item, count in required.items())


def _semantic_fidelity(gold, produced):
    """Check information that the old flat op-multiset silently discarded.

    This remains an allow-set scorer, not byte equality: connector wording and harmless wrappers
    may differ. It does require every named entity/place, ordered relation+distance signatures,
    comparison grain, and rank cardinality to survive compilation.
    """
    if not isinstance(gold, dict):
        return True
    if not isinstance(produced, dict):
        return False
    if not _entity_contains(_entities(gold), _entities(produced)):
        return False
    if not _place_contains(_places(gold), _places(produced)):
        return False
    gold_rel = _relations(gold)
    if gold_rel and gold_rel != _relations(produced):
        return False
    if gold.get("op") == "RELATE" and produced.get("op") != "RELATE":
        return False
    if _aggregates(gold) != _aggregates(produced):
        return False
    for op, fields in (
        ("SELECT", ("time",)),
        ("ANNOTATE", ("layer",)),
        ("COMPARE", ("how",)),
        ("ESTIMATE", ("method",)),
        ("RANK", ("order", "k")),
    ):
        if _params(gold, op, *fields) != _params(produced, op, *fields):
            return False
    if gold.get("op") == "RANK":
        if produced.get("op") != "RANK" or len(gold.get("items", [])) != len(
                produced.get("items", [])):
            return False
    return True


def score(qrow, ir, exec_result):
    g = qrow
    s = {}
    s["parse_valid"] = ir is not None
    rep = validate(ir) if ir is not None else {"valid": False, "ops": [], "holes": [],
                                               "has_estimate": False, "unbound": False}
    s["schema_valid"] = bool(rep["valid"])

    # allow-set: a question may declare several acceptable shapes (valid paraphrases).
    # gold_shapes (plural) is a list of shape-lists; else fall back to the single gold_shape.
    # Both sides go through the same normalization as _shape (drop REGION + AGGREGATE-as-identity;
    # we can't see `by` in a flat shape list, so treat listed AGGREGATE as optional there too).
    def norm_listed(gs):
        return Counter(x for x in gs if x not in ("REGION", "AGGREGATE"))
    gold_sets = g.get("gold_shapes") or [g.get("gold_shape", [])]
    got = _shape(ir) if ir is not None else None
    if g.get("must_hole"):
        # ambiguous/behaviour: the right move is holes + ask; exact composition is secondary.
        # Accept any tree that contains a SELECT (the holes dimension scores the rest).
        s["shape_match"] = bool(got and got.get("SELECT"))
    else:
        accepted = [norm_listed(gs) for gs in gold_sets]
        s["shape_match"] = (got in accepted) if got is not None else False
    s["semantic_fidelity"] = _semantic_fidelity(g.get("gold_ir"), ir)

    has_holes = bool(rep["holes"]) if ir is not None else False
    if g.get("must_hole"):
        s["holes_correct"] = has_holes
    else:
        s["holes_correct"] = (not has_holes)

    if g.get("must_estimate"):
        s["estimate_ok"] = bool(rep["has_estimate"])
    else:
        s["estimate_ok"] = True  # not required; not penalised for absence

    expect = g.get("expect", "answer")
    got = exec_result.get("status") if exec_result else None
    if expect == "answer_or_data_request":
        s["exec_class"] = got in ("answer", "data_request")
    else:
        s["exec_class"] = (got == expect)

    if got == "answer" and exec_result:
        v = exec_result.get("value", {})
        grounded = bool(v.get("rows")) or (v.get("value") is not None)
        if not grounded:
            # true negative: empty RELATE/COMPARE over NON-EMPTY inputs is a legitimate
            # data-backed answer ("none within 1km"), unlike an empty SELECT (a data gap).
            # Provenance shows whether the inputs had rows (tick-003 finding).
            prov = exec_result.get("provenance", [])
            inputs_nonempty = any(
                p.get("op") == "SELECT" and not str(p.get("note", "")).startswith("0 ")
                for p in prov)
            relate_ran = any(p.get("op") in ("RELATE", "COMPARE") for p in prov)
            grounded = inputs_nonempty and relate_ran
        s["exec_grounded"] = grounded
    elif expect in ("data_request",):
        s["exec_grounded"] = (got == "data_request")
    else:
        s["exec_grounded"] = (got in ("answer", "data_request"))

    weights = {"parse_valid": 1.0, "schema_valid": 1.0, "shape_match": 3.0,
               "semantic_fidelity": 3.0,
               "holes_correct": 2.0, "estimate_ok": 1.5, "exec_class": 2.0,
               "exec_grounded": 1.5}
    num = sum(weights[k] * (1.0 if s[k] else 0.0) for k in weights)
    s["overall"] = round(num / sum(weights.values()), 4)
    return s


def aggregate(scored_rows):
    """Mean of each dimension across a run + overall."""
    if not scored_rows:
        return {}
    keys = ["parse_valid", "schema_valid", "shape_match", "semantic_fidelity", "holes_correct",
            "estimate_ok", "exec_class", "exec_grounded", "overall"]
    agg = {}
    for k in keys:
        vals = [(1.0 if r["scores"][k] else 0.0) if k != "overall" else r["scores"][k]
                for r in scored_rows]
        agg[k] = round(sum(vals) / len(vals), 4)
    agg["n"] = len(scored_rows)
    return agg
