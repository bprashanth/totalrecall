#!/usr/bin/env python3
"""Merge generated banks deterministically before blind evaluation."""
import argparse,json
from pathlib import Path
from executor import execute
from ir_schema import validate
ap=argparse.ArgumentParser();ap.add_argument("--out",type=Path,required=True);ap.add_argument("--n",type=int,required=True);ap.add_argument("inputs",nargs="+",type=Path);a=ap.parse_args()
rows=[]
for path in a.inputs:rows+=json.loads(path.read_text())["questions"]
seen=set();rows=[r for r in rows if not (r["q"] in seen or seen.add(r["q"]))][:a.n]
if len(rows)<a.n:raise SystemExit(f"only {len(rows)} unique rows")
for r in rows:
 rep=validate(r["gold_ir"]);assert rep["valid"],(r["id"],rep["errors"])
 result=execute(r["gold_ir"]);want=r["expect"]
 assert (result["status"] in ("answer","data_request") if want=="answer_or_data_request" else result["status"]==want),(r["id"],result,want)
out={"spec_version":"v2.1","note":"blind holdout merged and execution-checked before parser exposure; immutable after write","questions":rows}
a.out.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n");import hashlib;print(len(rows),hashlib.sha256(a.out.read_bytes()).hexdigest())
