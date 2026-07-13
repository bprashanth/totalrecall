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


def _answer_contract(ir):
    """Meaning-bearing fields that an op multiset cannot see.

    This remains lighter than strict canonical audit, but prevents a missing density/mean head,
    wrong arithmetic mode, lost RANK cardinality, or wrong annotation field from scoring as a
    perfect structural parse.  Count inside COMPARE/RANK stays optional because the frozen
    executor scalarizes records there.
    """
    contract = []
    def walk(node, parent=None):
        if isinstance(node,list):
            for value in node: walk(value,parent)
            return
        if not isinstance(node,dict): return
        op=node.get("op")
        if op == "COMPARE":
            contract.append(("compare",node.get("how")))
        elif op == "RANK":
            contract.append(("rank",node.get("order"),node.get("k"),len(node.get("items",[]))))
        elif op == "ANNOTATE":
            # Layer labels are literals. Separator punctuation and underscores do not change
            # their denotation (``population-density`` == ``population density``), matching the
            # strict semantic audit rather than manufacturing a coarse-score disagreement.
            import re
            layer=" ".join(re.findall(r"[a-z0-9]+",str(node.get("layer","")).lower()))
            contract.append(("annotate",layer))
        elif op == "AGGREGATE":
            by,metric=node.get("by"),node.get("metric")
            required = metric in ("density","presence") or (metric == "mean" and by == "space")
            required = required or (metric == "count" and parent not in ("COMPARE","RANK"))
            if metric == "mean" and by == "time":
                # Only a known connector Series has the documented identity denotation.
                source=node.get("source")
                entity=source.get("entity") if isinstance(source,dict) and source.get("op")=="SELECT" else None
                if entity:
                    import connectors as C
                    required = not bool(C.ilo_resolve_indicator(entity)[0] or
                        C.eurostat_resolve_indicator(entity)[0] or C.wb_resolve_indicator(entity)[0])
            if required: contract.append(("aggregate",by,metric))
        for value in node.values():
            if isinstance(value,(dict,list)): walk(value,op)
    walk(ir)
    return Counter(contract)


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
        skeleton_ok = (got in accepted) if got is not None else False
        contract_ok = (_answer_contract(ir) == _answer_contract(g.get("gold_ir")))
        s["shape_match"] = skeleton_ok and contract_ok

    has_holes = bool(rep["holes"]) if ir is not None else False
    if g.get("must_hole"):
        # Compare unbound FIELDS, not just "at least one hole". Tick-010 corpus audit found
        # ?place-only accepted against gold requiring both entity+region; hole names may vary
        # (?facility_type vs ?amenity_type), but the missing slots may not.
        grep = validate(g.get("gold_ir")) if isinstance(g.get("gold_ir"), dict) else None
        if grep and grep.get("holes"):
            # REGION{place:"?place"} and SELECT{region:"?place"} are the two schema-valid
            # encodings of the same missing region slot.
            def slot(h):
                if h.get("op")=="REGION" and h.get("field")=="place":
                    return "target" if str(h.get("path","")).startswith("root.target") else "region"
                return h["field"]
            s["holes_correct"] = (Counter(slot(h) for h in rep["holes"]) ==
                                  Counter(slot(h) for h in grep["holes"]))
        else:
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
               "holes_correct": 2.0, "estimate_ok": 1.5, "exec_class": 2.0,
               "exec_grounded": 1.5}
    num = sum(weights[k] * (1.0 if s[k] else 0.0) for k in weights)
    s["overall"] = round(num / sum(weights.values()), 4)
    return s


def aggregate(scored_rows):
    """Mean of each dimension across a run + overall."""
    if not scored_rows:
        return {}
    keys = ["parse_valid", "schema_valid", "shape_match", "holes_correct",
            "estimate_ok", "exec_class", "exec_grounded", "overall"]
    agg = {}
    for k in keys:
        vals = [(1.0 if r["scores"][k] else 0.0) if k != "overall" else r["scores"][k]
                for r in scored_rows]
        agg[k] = round(sum(vals) / len(vals), 4)
    agg["n"] = len(scored_rows)
    return agg
