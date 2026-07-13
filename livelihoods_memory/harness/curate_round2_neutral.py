#!/usr/bin/env python3
"""Manual-judge corrections to the independently generated Round-2 neutral bank."""
from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from executor import execute
from ir_schema import validate

ROOT=Path(__file__).resolve().parent.parent
src=ROOT/"coverage"/"raw"/"round2-neutral-generated.json"
dst=ROOT/"questions"/"round2-neutral.json"


def main():
    data=json.loads(src.read_text()); rows=[]
    excluded={
        "r2-neutral-006":"address is not one OSM attribute; admitted ANNOTATE returned nulls",
        "r2-neutral-019":"relative 'past five years' gold was stale 2019–2023 and requires an explicit relative-time policy",
    }
    corrections={}
    for row in data["questions"]:
        rid=row["id"]
        if rid in excluded: continue
        ir=row["gold_ir"]
        if rid=="r2-neutral-012":
            relation=dict(ir);relation.pop("threshold_km",None)
            ir={"op":"AGGREGATE","by":"space","metric":"presence","source":relation}
            corrections[rid]="'are there any' is presence; 1 km modifies marketplace clause, not unquantified 'near a bank'"
        elif rid=="r2-neutral-020":
            ir["left"]["source"]["time"]={"start":"2018","end":str(datetime.now().year)}
            corrections[rid]="since 2018 normalized through current calendar year"
        elif rid=="r2-neutral-021":
            ir["left"]["source"]["time"]=None
            corrections[rid]="vague 'recently' follows frozen trend default: all available data"
        elif rid=="r2-neutral-027":
            ir["method"]="envelope"
            corrections[rid]="question does not select feature method; standard transfer exemplar is envelope"
        elif rid=="r2-neutral-031":
            ir["left"]["source"]["entity"]="?indicator"
            corrections[rid]="bare employment is not a declared measure and requires indicator clarification"
        elif rid=="r2-neutral-034":
            ir["entity"]="?proxy";ir["region"]={"op":"REGION","place":"Leipzig"}
            corrections[rid]="motivation requires proxy but Leipzig is explicitly named"
        elif rid=="r2-neutral-036":
            ir["entity"]="?proxy";ir["region"]={"op":"REGION","place":"Durban"}
            corrections[rid]="behavior requires proxy but Durban is explicitly named"
        row["gold_ir"]=ir
        rep=validate(ir)
        if not rep["valid"]: raise SystemExit(f"{rid} invalid: {rep['errors']}")
        result=execute(ir)
        expected=row["expect"]
        ok=(result["status"] in ("answer","data_request")) if expected=="answer_or_data_request" else result["status"]==expected
        if not ok: raise SystemExit(f"{rid} executes {result['status']} not {expected}: {result}")
        row["gold_shape"]=[op for op in rep["ops"] if op!="REGION"]
        rows.append(row)
    assert len(rows)==40,(len(rows),excluded)
    out={"spec_version":"v2.1",
         "note":"DeepSeek-neutral generated bank; execution-admitted then manually judged. Two unsafe golds excluded and seven corrected; see manual_curation.",
         "manual_curation":{"excluded":excluded,"corrected":corrections},"questions":rows}
    dst.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"admitted":len(rows),"excluded":excluded,"corrected":corrections},indent=2))


if __name__=="__main__":main()
