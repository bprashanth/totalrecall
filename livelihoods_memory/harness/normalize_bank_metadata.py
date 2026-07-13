#!/usr/bin/env python3
"""Recompute non-semantic benchmark metadata from gold IR without changing questions/golds."""
import argparse,json
from pathlib import Path
from ir_schema import validate

ap=argparse.ArgumentParser();ap.add_argument("bank",type=Path);a=ap.parse_args()
data=json.loads(a.bank.read_text())
for row in data["questions"]:
    rep=validate(row["gold_ir"])
    if not rep["valid"]:raise SystemExit(f"invalid gold {row['id']}: {rep['errors']}")
    row["gold_shape"]=[op for op in rep["ops"] if op!="REGION"]
    if row.get("expect")=="data_request":row["must_hole"]=True
    if row.get("type")=="TRANSFER":row["must_estimate"]=True
a.bank.write_text(json.dumps(data,indent=1,ensure_ascii=False)+"\n")
print(json.dumps({"bank":str(a.bank),"n":len(data["questions"])}))
