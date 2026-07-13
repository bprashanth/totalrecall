#!/usr/bin/env python3
"""Materialize externally authored raw candidate groups for normal holdout curation."""
import argparse, json
from pathlib import Path

ap=argparse.ArgumentParser()
ap.add_argument("raw",type=Path);ap.add_argument("group");ap.add_argument("out",type=Path)
a=ap.parse_args()
rows=json.loads(a.raw.read_text())[a.group]
for row in rows:
    if row.get("expect")=="data_request": row["must_hole"]=True
    if row.get("type")=="TRANSFER": row["must_estimate"]=True
payload={"spec_version":"v2.1","note":"post-freeze Cursor-authored candidates; unexposed to qwen",
         "source_generated":str(a.raw),"questions":rows}
a.out.write_text(json.dumps(payload,indent=1,ensure_ascii=False)+"\n")
print(json.dumps({"group":a.group,"n":len(rows),"out":str(a.out)}))
