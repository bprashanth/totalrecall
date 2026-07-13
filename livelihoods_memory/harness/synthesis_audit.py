#!/usr/bin/env python3
"""Fail-closed audit for the user-facing answer surface.

Compiler and execution scores are insufficient if faithful typed results are later contradicted
in prose.  This gate consumes ordinary trace JSONL and checks only deterministic invariants; it
does not call a model or a connector.  A saturation wall is eligible only when every row passes.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re


SOURCE_NAMES = {
    "osm": "OpenStreetMap",
    "worldbank": "World Bank",
    "ilostat": "ILOSTAT",
    "eurostat": "Eurostat",
}


def _flatten_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _flatten_strings(item)


def _unsafe_attr_strings(attrs):
    """Values from prose-like or provenance-like source fields, not categorical OSM tags."""
    risky={"source","description","note","instruction","comment","attribution"}
    if not isinstance(attrs,dict):
        return
    for key,value in attrs.items():
        if str(key).lower() in risky:
            yield from _flatten_strings(value)


def _walk(value):
    if isinstance(value,list):
        for item in value:yield from _walk(item)
    elif isinstance(value,dict):
        yield value
        for item in value.values():yield from _walk(item)


def _strip_time(value):
    if isinstance(value,list):return [_strip_time(item) for item in value]
    if isinstance(value,dict):
        return {key:_strip_time(item) for key,item in value.items() if key!="time"}
    return value


def _temporal_difference(ir):
    if not isinstance(ir,dict) or ir.get("op")!="COMPARE" or ir.get("how")!="difference":
        return False
    left,right=ir.get("left"),ir.get("right")
    lt=[x.get("time") for x in _walk(left) if x.get("op")=="SELECT" and x.get("time")]
    rt=[x.get("time") for x in _walk(right) if x.get("op")=="SELECT" and x.get("time")]
    return bool(lt and rt and lt!=rt and _strip_time(left)==_strip_time(right))


def _operand_label(node):
    selected=next((x for x in _walk(node) if x.get("op")=="SELECT"),{})
    region=selected.get("region")
    return str(region.get("place") if isinstance(region,dict) else region or
               selected.get("entity") or "")


def audit_trace(trace):
    """Return stable issue codes for one trace; an empty list is a pass."""
    issues=[]
    prose=trace.get("synthesis") or ""
    lower=prose.lower()
    execution=trace.get("execution") or {}
    status=execution.get("status")
    value=execution.get("value") or {}
    scores=trace.get("synthesis_scores") or {}
    if not prose:
        issues.append("empty_prose")
    if scores.get("overall") != 1.0:
        issues.append("mechanical_score_not_perfect")
    if status == "answer":
        if lower.startswith("i can't safely answer"):
            issues.append("answer_contract_failed_closed")
        scalar=value.get("value")
        if isinstance(scalar,bool):
            negative=bool(re.search(r"\b(?:no|none|zero|not present|false)\b",lower))
            positive=bool(re.search(r"\b(?:yes|present|true)\b",lower))
            if scalar and (negative or not positive):
                issues.append("boolean_polarity")
            if not scalar and not negative:
                issues.append("boolean_polarity")
        label=execution.get("label")
        if label == "modelled":
            if not re.search(r"model|estimat|approximat",lower):
                issues.append("modelled_label_missing")
            if not re.search(r"local\s+corroborat|corroborat\w*\s+locally",lower):
                issues.append("local_corroboration_missing")
            if value.get("kind") == "field" and "not an observed target count" not in lower:
                issues.append("modelled_field_count_unsafe")
        elif re.search(r"\b(?:modelled|modeled)\s+(?:estimate|field|result)\b",lower):
            issues.append("observed_called_modelled")
        routes=[]
        for item in execution.get("provenance",[]):
            route=item.get("route")
            if route in SOURCE_NAMES and route not in routes:
                routes.append(route)
        for route in routes:
            if SOURCE_NAMES[route].lower() not in lower:
                issues.append(f"source_label_missing:{route}")
        attrs=[]
        for row in value.get("rows") or []:
            safe={str(row.get(k)).strip().lower() for k in ("name","t","value","dist_km")
                  if row.get(k) is not None}
            attrs.extend(item for item in _unsafe_attr_strings(row.get("attrs") or {})
                         if item.strip().lower() not in safe)
        for attr in attrs:
            token=attr.strip().lower()
            if len(token)>=8 and token in lower:
                issues.append("arbitrary_attr_exposed")
                break
        ir=trace.get("ir") or {}
        if ir.get("op")=="COMPARE" and ir.get("how")=="difference" and isinstance(scalar,(int,float)):
            temporal=_temporal_difference(ir)
            if not temporal and re.search(r"\b(?:change|increase|decrease)\b",lower):
                issues.append("cross_section_called_temporal_change")
            ql=(trace.get("question") or "").lower()
            direct=bool(re.match(r"\s*(?:does|do|is|are|has|have|did|was|were)\b",ql))
            if direct and re.search(r"\b(?:more|higher|greater|larger|outnumber|less|lower|fewer|smaller)\b",ql) \
                    and not re.match(r"\s*(?:yes|no)\b",lower):
                issues.append("direct_compare_not_answered")
            if re.match(r"\s*which\b",ql) and scalar!=0:
                expected=_operand_label(ir.get("left") if scalar>0 else ir.get("right"))
                if expected and expected.lower() not in lower:
                    issues.append("compare_winner_not_named")
        if value.get("kind")=="scalar" and scalar is None:
            issues.append("null_scalar_answer")
        if ir.get("op")=="ANNOTATE" and str(ir.get("layer","")).lower() not in lower:
            issues.append("annotation_layer_omitted")
        if value.get("kind")=="records" and value.get("n_rows",len(value.get("rows") or []))>3:
            ql=(trace.get("question") or "").lower()
            if re.search(r"\b(?:list|show|every|all|which)\b",ql) and \
                    "examples:" not in lower and "display name" not in lower:
                issues.append("partial_list_not_disclosed")
        if ir.get("op") == "RANK":
            notes=[str(p.get("note") or "") for p in execution.get("provenance",[])
                   if p.get("op")=="RANK"]
            if ir.get("order")=="asc" and any(" > " in note for note in notes):
                issues.append("ascending_provenance_sign")
            if ir.get("order")=="desc" and any(" < " in note for note in notes):
                issues.append("descending_provenance_sign")
    elif status in ("error","data_request"):
        reason=execution.get("reason")
        if reason in ("no_ir","parse_invalid") and re.search(
                r"\b(?:no data|data (?:is|are) (?:missing|absent|unavailable)|none exist)\b",lower):
            issues.append("compiler_failure_called_data_gap")
        if reason == "no_connector" and "coverage gap" not in lower:
            issues.append("connector_gap_not_distinguished")
    else:
        issues.append("unknown_execution_status")
    return sorted(set(issues))


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("traces", nargs="+", type=Path)
    ap.add_argument("--out", required=True, type=Path)
    args=ap.parse_args()
    rows=[]
    files=[]
    for path in args.traces:
        count=0
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            trace=json.loads(line)
            count+=1
            issues=audit_trace(trace)
            if issues:
                rows.append({"trace":str(path),"id":trace.get("id"),"issues":issues})
        files.append({"trace":str(path),"rows":count})
    payload={"schema_version":"synthesis-faithfulness-v1","files":files,
             "rows_audited":sum(x["rows"] for x in files),"failures":len(rows),
             "passed":not rows,"rows":rows}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({k:payload[k] for k in
                      ("rows_audited","failures","passed")},indent=2))
    raise SystemExit(1 if rows else 0)


if __name__ == "__main__":
    main()
