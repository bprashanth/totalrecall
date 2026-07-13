"""synthesize — the fourth stage: typed result -> short prose answer, plus its scoring.

Until now only compile/execute/dialogue were tested; this adds the answer surface where the
constitution's behavioral rules (short, honest, observed-vs-modelled labelled, gap -> specific
ask) actually face the user. Scoring is MECHANICAL where possible (length, number-presence,
modelled-flag, gap-stated); an LLM judge is deliberately not required for the core dims.
"""
import json
import re

from llm import chat

SYNTH_SYSTEM = """You write the FINAL one-paragraph answer to a user's question about a place,
from a structured result computed by deterministic tools. Rules:
- <= 60 words. Lead with the finding (the number / the list size / the direction / the ranking).
- If evidence_label is "modelled": say clearly it is a modelled estimate needing local corroboration.
- If status is data_request: do NOT invent an answer. Say exactly what is missing or ambiguous and
  ask the ONE most useful question (or name the data to collect).
- Never invent numbers not present in the result. Mention the data source in passing."""

NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _first_number(text):
    hits = []
    for m in re.finditer(r"\b\d[\d,]*(?:\.\d+)?\b", text.lower()):
        try: hits.append((m.start(), float(m.group().replace(",", ""))))
        except ValueError: pass
    for word, value in NUMBER_WORDS.items():
        m = re.search(rf"\b{word}\b", text.lower())
        if m: hits.append((m.start(), float(value)))
    return min(hits)[1] if hits else None


def _context(exec_result):
    v = exec_result.get("value") or {}
    ctx = {"status": exec_result.get("status"), "evidence_label": exec_result.get("label"),
           "reason": exec_result.get("reason"), "detail": exec_result.get("detail"),
           "kind": v.get("kind"), "scalar": v.get("value"),
           "n_rows": v.get("n_rows", len(v.get("rows", []) or [])),
           # Never expose arbitrary OSM attrs to an answer model. In H25 an attrs.source tag on
           # one row was promoted into the source for the whole result. Only typed answer fields
           # are safe at this boundary.
           "sample_rows": [{k: row.get(k) for k in ("name", "t", "value", "dist_km")
                            if row.get(k) is not None}
                           for row in (v.get("rows") or [])[:3]],
           "provenance_notes": [p.get("note") for p in exec_result.get("provenance", [])
                                if p.get("note")][:4],
           "sources": list({p.get("route") for p in exec_result.get("provenance", [])
                            if p.get("route")})}
    return ctx


def _fmt(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.6g}"
    return str(value)


def _fmt_coord(value):
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _source_label(exec_result):
    names = {"osm": "OpenStreetMap", "worldbank": "World Bank",
             "ilostat": "ILOSTAT", "eurostat": "Eurostat"}
    routes=[]
    for item in exec_result.get("provenance", []):
        route=item.get("route")
        if route in names and names[route] not in routes:
            routes.append(names[route])
    return ", ".join(routes) if routes else "the resolved data source"


def _source_suffix(exec_result):
    return f" Source: {_source_label(exec_result)}."


def _walk_ir(value):
    if isinstance(value, list):
        for item in value:
            yield from _walk_ir(item)
    elif isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_ir(child)


def _without_time(value):
    if isinstance(value,list):
        return [_without_time(item) for item in value]
    if isinstance(value,dict):
        return {key:_without_time(item) for key,item in value.items() if key!="time"}
    return value


def _times(value):
    return [node.get("time") for node in _walk_ir(value)
            if node.get("op")=="SELECT" and node.get("time") is not None]


def _temporal_difference(ir):
    if not isinstance(ir,dict) or ir.get("op")!="COMPARE" or ir.get("how")!="difference":
        return False
    left,right=ir.get("left"),ir.get("right")
    return (_without_time(left)==_without_time(right) and _times(left) and _times(right)
            and _times(left)!=_times(right))


def _operand_label(node):
    selects=[item for item in _walk_ir(node) if item.get("op")=="SELECT"]
    if not selects:return "the operand"
    first=selects[0]
    region=first.get("region")
    place=region.get("place") if isinstance(region,dict) else region
    return str(place or first.get("entity") or "the operand")


def _contrast_label(left,right,choose_left):
    """Name the distinguishing side of a two-operand choice, preferring geography."""
    def parts(node):
        selected=[item for item in _walk_ir(node) if item.get("op")=="SELECT"]
        places=[];entities=[]
        for item in selected:
            region=item.get("region")
            place=region.get("place") if isinstance(region,dict) else region
            if place is not None:places.append(str(place))
            if item.get("entity") is not None:entities.append(str(item.get("entity")))
        return places,entities
    lp,le=parts(left);rp,re_=parts(right)
    for a,b in zip(lp,rp):
        if a.lower()!=b.lower():return a if choose_left else b
    for a,b in zip(le,re_):
        if a.lower()!=b.lower():return f"the {a if choose_left else b}-based side"
    return "the left-hand side" if choose_left else "the right-hand side"


def _difference_finding(question, scalar, ir):
    magnitude=_fmt(abs(scalar))
    if _temporal_difference(ir):
        direction="decrease" if scalar<0 else "increase" if scalar>0 else "no change"
        return f"The change is {_fmt(scalar)} ({direction} of {magnitude})."
    ql=question.lower()
    direct=bool(re.match(r"\s*(?:does|do|is|are|has|have|did|was|were)\b",ql))
    choice=bool(re.search(r"\bwhich\b.+?\b(?:more|higher|greater|larger|fewer|lower)\b",ql)
                or re.search(r"\bmore\b.+?\bor\b",ql))
    if choice:
        if scalar==0:return "The two operands are tied (difference 0)."
        wants_smaller=bool(re.search(r"\b(?:fewer|lower|less|smaller|smallest)\b",ql))
        choose_left=(scalar<0) if wants_smaller else (scalar>0)
        winner=_contrast_label(ir.get("left"),ir.get("right"),choose_left)
        winner=winner[:1].upper()+winner[1:]
        adjective="smaller" if wants_smaller else "larger"
        return f"{winner} has the {adjective} value; the left-minus-right difference is {_fmt(scalar)}."
    if direct and re.search(r"\b(?:more|higher|greater|larger|outnumber)\b",ql):
        yes=scalar>0
        relation="higher" if scalar>0 else "lower" if scalar<0 else "equal"
        return f"{'Yes' if yes else 'No'}; the left-hand value is {relation} (difference {_fmt(scalar)})."
    if direct and re.search(r"\b(?:less|lower|fewer|smaller)\b",ql):
        yes=scalar<0
        relation="lower" if scalar<0 else "higher" if scalar>0 else "equal"
        return f"{'Yes' if yes else 'No'}; the left-hand value is {relation} (difference {_fmt(scalar)})."
    if re.search(r"^\s*which\b|\bwhich\s+(?:city|region|country|one)\b",ql):
        if scalar==0:return f"The two operands are tied (difference 0)."
        winner=_operand_label(ir["left"] if scalar>0 else ir["right"])
        return f"{winner} has the larger value; the left-minus-right difference is {_fmt(scalar)}."
    left=_contrast_label(ir.get("left"),ir.get("right"),True)
    right=_contrast_label(ir.get("left"),ir.get("right"),False)
    return f"{left} minus {right} is {_fmt(scalar)}."


def _contract_issue(question, exec_result, ir):
    """Fail closed when the compiled result cannot answer an explicit surface contract."""
    if exec_result.get("status") != "answer" or not isinstance(ir, dict):
        return None
    value=exec_result.get("value") or {}
    ql=question.lower()
    rank_intent=bool(re.search(
        r"\b(?:rank|order)\b|\bwhich\b.+?\b(?:highest|lowest|most|fewest|largest|smallest)\b",
        ql))
    if rank_intent and (":" in question or re.search(r"\bamong\b|\bwhich\s+of\b",ql)) \
            and value.get("kind") != "ranking":
        return "the compiled result is not the requested complete ranking"
    if ir.get("op") == "RANK":
        requested=None
        if re.search(r"\b(?:highest|largest|most)\s+to\s+(?:lowest|smallest|fewest)\b"
                     r"|\bdescending\b|\bhighest\s+first\b",ql): requested="desc"
        elif re.search(r"\b(?:lowest|smallest|fewest)\s+to\s+(?:highest|largest|most)\b"
                       r"|\bascending\b|\blowest\s+first\b",ql): requested="asc"
        if requested and ir.get("order") != requested:
            return "the compiled ranking direction conflicts with the requested direction"
    existential=bool(re.match(r"\s*(?:is|are)\s+(?:there\s+)?any\b",ql) or
                     re.match(r"\s*is\s+at\s+least\s+one\b",ql))
    if existential and not (value.get("kind") == "scalar" and
                            isinstance(value.get("value"), bool)):
        return "the compiled result is not the requested yes-or-no presence answer"
    relations=[node for node in _walk_ir(ir) if node.get("op")=="RELATE" and
               isinstance(node.get("threshold_km"),(int,float))]
    # A single-threshold question can be checked exactly. Multi-clause thresholds are already
    # protected by strict compiler guards and are intentionally not collapsed here.
    if len(relations)==1:
        from parser import _parse_dist_km
        requested=_parse_dist_km(ql)
        if requested is not None and abs(relations[0]["threshold_km"]-requested)>1e-9:
            return "the executed distance threshold conflicts with the requested threshold"
    return None


def _render_nonanswer(exec_result):
    status=exec_result.get("status")
    reason = exec_result.get("reason")
    detail = exec_result.get("detail") or {}
    if status == "error":
        if reason == "no_ir":
            return ("I couldn't compile this request into a valid query, so no factual answer "
                    "or data-availability conclusion is safe. Please rephrase the request.")
        return ("The query failed during deterministic execution; no factual answer or "
                "data-availability conclusion is safe.")
    if reason == "no_connector":
        entity = detail.get("entity", "that entity")
        return (f"No configured data source maps {entity!r}; this is a source-coverage gap, not "
                "evidence that none exist. Please refine the entity or add a suitable connector.")
    if reason == "empty_select":
        entity = detail.get("entity", "the requested records")
        return (f"No mapped records were returned for {entity!r}. Treat this as missing coverage, "
                "not evidence that none exist; local data collection or source verification is needed.")
    if reason == "source_truncated":
        return ("The source exceeded the safe retrieval cap, so an exact or spatially complete "
                "answer would be misleading. Narrow the region or use a complete bulk source.")
    if reason == "source_unavailable":
        return ("The configured source is temporarily unavailable after bounded retries. This is "
                "an upstream availability gap, not evidence that no matching records exist; retry "
                "the source or provide a verified alternate connector.")
    if reason == "parse_invalid":
        return ("I couldn't compile this request into a valid typed query. This is a compiler "
                "failure and establishes nothing about source coverage.")
    if reason == "unbound_holes":
        holes=detail.get("holes") or []
        names=[str(item.get("name",item)) if isinstance(item,dict) else str(item) for item in holes]
        suffix=f" Missing: {', '.join(names)}." if names else ""
        return "I need clarification before running this query." + suffix
    if reason == "gate_failed":
        ask=detail.get("ask") or "collect local target-area observations"
        return f"The transfer gate did not pass: {detail.get('reason','insufficient support')}. Please {ask}."
    if reason == "national_scope_required":
        return ("The configured indicator source is country-level and cannot support this "
                "subnational request. A verified regional source is required.")
    if reason == "regional_scope_unavailable":
        region=detail.get("region","the requested region")
        return (f"The indicator is mapped, but {region} is outside the connector's verified "
                "regional geography. Add a verified regional source or geography mapping.")
    if reason == "unresolved_region":
        return "The named region could not be resolved reliably. Please clarify the place."
    if reason == "annotation_unavailable":
        return "The requested annotation is not present in the source records; collect that field first."
    if reason == "insufficient_series":
        points=detail.get("points",0)
        word="observation" if points==1 else "observations"
        return (f"Only {points} dated {word} is available; at least two are needed to determine "
                "whether the series is rising or falling.")
    return f"I can't answer safely because required data or bindings are missing ({reason or 'data_request'})."


def synthesize(question, exec_result, role="qwen2b", ir=None):
    """Render typed results deterministically; freeform generation is not a truth boundary."""
    if exec_result.get("status") != "answer":
        return _render_nonanswer(exec_result)
    issue=_contract_issue(question,exec_result,ir)
    if issue:
        return f"I can't safely answer: {issue}."
    value=exec_result.get("value") or {}
    kind=value.get("kind")
    label=exec_result.get("label")
    source=_source_suffix(exec_result)
    caveat=(" This is a modelled estimate requiring local corroboration."
            if label=="modelled" else "")
    if kind=="scalar":
        scalar=value.get("value")
        if isinstance(scalar,bool):
            return ("Yes, the requested condition is present." if scalar else
                    "No, the requested condition is not present.") + source + caveat
        if isinstance(scalar,str):
            return f"The computed result is {scalar}." + source + caveat
        mode=next((p.get("how") for p in reversed(exec_result.get("provenance",[]))
                   if p.get("op")=="COMPARE"),None)
        if mode=="difference" and isinstance(scalar,(int,float)):
            finding=_difference_finding(question,scalar,ir)
        elif mode=="ratio":
            finding=f"The ratio is {_fmt(scalar)}."
        else:
            finding=f"The computed value is {_fmt(scalar)}."
        return finding+source+caveat
    rows=value.get("rows") or []
    n=value.get("n_rows",len(rows))
    if kind=="ranking":
        ranked=", ".join(f"{row.get('label')} ({_fmt(row.get('value'))})" for row in rows)
        return f"Ranking: {ranked}."+source+caveat
    if kind=="records":
        if isinstance(ir,dict) and ir.get("op")=="ANNOTATE":
            layer=ir.get("layer")
            annotated=[row for row in rows if row.get(layer) is not None]
            samples="; ".join(f"{row.get('name') or 'unnamed'} — {_fmt(row.get(layer))}"
                             for row in annotated[:3])
            detail=(f" Examples: {samples}." if samples else "")
            count=(value.get("annotation") or {}).get("n_nonnull",len(annotated))
            if layer=="name":
                detail=(f" Examples: {'; '.join(str(row.get('name')) for row in annotated[:3])}."
                        if annotated else "")
                noun="record" if n==1 else "records";verb="has" if count==1 else "have"
                return f"Found {n} mapped {noun}; {count} {verb} a name."+detail+source+caveat
            return (f"Found {n} mapped records; {layer} is present for {count}."
                    +detail+source+caveat)
        examples=[]
        for row in rows:
            name=row.get("name")
            if name:
                distance=f" ({_fmt(row['dist_km'])} km)" if isinstance(row.get("dist_km"),(int,float)) else ""
                examples.append(str(name)+distance)
            elif isinstance(row.get("lat"),(int,float)) and isinstance(row.get("lon"),(int,float)):
                examples.append(f"({_fmt_coord(row['lat'])}, {_fmt_coord(row['lon'])})")
            if len(examples)==3:break
        sample=f" Examples: {'; '.join(examples)}." if examples else ""
        if n and not examples:
            noun="record" if n==1 else "records"
            return (f"Found {n} matching mapped {noun}, but no displayable identifier is available."
                    +source+caveat)
        noun="record" if n==1 else "records"
        qualifier="mapped matching" if n==0 else "matching"
        return f"Found {n} {qualifier} {noun}."+sample+source+caveat
    if kind=="series":
        if len(rows)==1:
            row=rows[0]
            return f"The recorded value is {_fmt(row.get('value'))} for {row.get('t')}."+source+caveat
        if rows:
            return (f"The series contains {n} observations, from {_fmt(rows[0].get('value'))} "
                    f"at {rows[0].get('t')} to {_fmt(rows[-1].get('value'))} at {rows[-1].get('t')}.")+source+caveat
    if kind=="field":
        return (f"A modelled field was generated from {n} source records; {n} is not an observed "
                "target count and local corroboration is required."+source)
    return "A typed answer was produced, but its result kind has no safe renderer."+source+caveat


def score_synthesis(question, exec_result, prose):
    """Mechanical behavioral dims; each True/False, overall = mean."""
    s = {}
    words = len(prose.split())
    s["not_empty"] = bool(prose) and not prose.startswith("[synthesis-failed]")
    s["short"] = 0 < words <= 80
    v = exec_result.get("value") or {}
    status = exec_result.get("status")
    # number-presence: if the result carries a headline number, the prose must contain it
    headline = None
    if isinstance(v.get("value"), (int, float)):
        headline = v["value"]
    elif v.get("kind") == "records":
        headline = v.get("n_rows",len(v.get("rows") or []))
    if status == "answer" and isinstance(v.get("value"), bool) and s["not_empty"]:
        negative=bool(re.search(r"\b(?:no|none|zero|not present|false)\b",prose.lower()))
        positive=bool(re.search(r"\b(?:yes|present|true)\b",prose.lower()))
        s["states_finding"] = (positive and not negative) if v["value"] else negative
    elif status == "answer" and headline is not None and s["not_empty"]:
        def num_in(x, text):
            if isinstance(x, float):
                cands = {f"{x:.0f}", f"{x:.1f}", f"{x:.2f}", f"{x:,.0f}"}
            else:
                cands = {str(x), f"{x:,}"}
            return any(c in text for c in cands)
        found = num_in(headline, prose) or num_in(abs(headline), prose)
        found = found or _fmt(headline) in prose or _fmt(abs(headline)) in prose
        if v.get("kind") == "records":
            found = _first_number(prose) == headline
        if not found:
            nums = [int(m.replace(",", "")) for m in
                    re.findall(r"\d[\d,]*", prose) if m.replace(",", "").isdigit()]
            found = any(abs(x - y) == round(abs(headline))
                        for i, x in enumerate(nums) for y in nums[i + 1:])
        s["states_finding"] = found
    elif status == "answer" and isinstance(v.get("value"), str) and s["not_empty"]:
        s["states_finding"] = v["value"].lower() in prose.lower()
    else:
        # direction / ranking / list answers: at least echo a value or label from the result
        rows = (v.get("rows") or [])[:3]
        if status == "answer" and v.get("kind") == "ranking" and rows:
            positions = [prose.lower().find(
                f"{r.get('label')} ({_fmt(r.get('value'))})".lower()) for r in rows]
            mentioned = [(i, p) for i, p in enumerate(positions) if p >= 0]
            s["states_finding"] = bool(mentioned and mentioned[0][0] == 0 and
                                       all(a[1] < b[1] for a, b in zip(mentioned, mentioned[1:])))
        else:
            s["states_finding"] = True if status != "answer" else (
                any(str(r.get("label", r.get("value", ""))).split(",")[0] in prose
                    for r in rows) or v.get("kind") == "series")
    if exec_result.get("label") == "modelled":
        s["modelled_flagged"] = bool(re.search(r"model|estimat|approximat", prose.lower())) \
            and bool(re.search(r"local\s+corroborat|corroborat\w*\s+locally",prose.lower()))
    elif status == "answer":
        s["modelled_flagged"] = not bool(re.search(
            r"\b(?:modelled|modeled)\s+(?:estimate|field|result)|\ba\s+modelled\s+estimate\b",
            prose.lower()))
    else:
        s["modelled_flagged"] = True
    if status == "data_request":
        s["gap_stated"] = bool(re.search(r"missing|no data|source-coverage gap|no configured data source|need|required?|collect|clarif|which |couldn|unable|specify"
                                         r"|cannot|can't|not (?:locate|find|available)|no available"
                                         r"|exceeded|incomplete|misleading|narrow|complete bulk|outside|add a verified",
                                         prose.lower()))
        # A DataRequest may repeat numbers supplied by the user or grounded in its structured
        # failure detail (for example, "2 source records; collect >=5").  It must not introduce
        # numbers from free text outside those two typed inputs.
        allowed=[float(x.replace(",","")) for x in re.findall(
            r"\b\d[\d,]*(?:\.\d+)?\b",question)]
        def collect_detail(value):
            if isinstance(value, bool) or value is None:
                return
            if isinstance(value, (int, float)):
                allowed.append(float(value))
            elif isinstance(value, str):
                for hit in re.findall(r"\b\d[\d,]*(?:\.\d+)?\b", value):
                    allowed.append(float(hit.replace(",", "")))
            elif isinstance(value, list):
                for item in value:
                    collect_detail(item)
            elif isinstance(value, dict):
                for item in value.values():
                    collect_detail(item)
        collect_detail(exec_result.get("detail"))
        found=[float(x.replace(",","")) for x in re.findall(
            r"\b\d[\d,]*(?:\.\d+)?\b",prose)]
        s["no_fabrication"] = all(any(abs(x-y)<1e-6 for y in allowed) for x in found)
    else:
        s["gap_stated"] = True
        allowed=[]
        def collect(value):
            if isinstance(value,bool) or value is None:return
            if isinstance(value,(int,float)):allowed.append(float(value));return
            if isinstance(value,str):
                for hit in re.findall(r"\b\d[\d,]*(?:\.\d+)?\b",value):
                    allowed.append(float(hit.replace(",","")))
                return
            if isinstance(value,list):
                for item in value:collect(item)
            elif isinstance(value,dict):
                for key,item in value.items():
                    if key in ("attrs","id"):continue
                    collect(item)
        if isinstance(v.get("rows"),list):
            allowed.append(float(v.get("n_rows",len(v["rows"]))))
        collect(v)
        collect({"question_numbers":re.findall(r"\b\d[\d,]*(?:\.\d+)?\b",question)})
        found=[]
        for hit in re.findall(r"(?<![a-z])[-+]?\d[\d,]*(?:\.\d+)?(?![a-z])",prose.lower()):
            try:found.append(float(hit.replace(",","")))
            except ValueError:pass
        s["no_fabrication"] = all(any(abs(x-y)<1e-4 or abs(abs(x)-abs(y))<1e-4
                                       for y in allowed) for x in found)
    dims = [k for k in s]
    s["overall"] = round(sum(1.0 if s[k] else 0.0 for k in dims) / len(dims), 3)
    return s
