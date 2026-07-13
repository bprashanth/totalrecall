#!/usr/bin/env python3
"""Freeze a manually pre-audited generated holdout before the parser sees it."""
from __future__ import annotations
import argparse,hashlib,json
from pathlib import Path
from executor import execute
from ir_schema import validate

def main():
 ap=argparse.ArgumentParser();ap.add_argument("src",type=Path);ap.add_argument("dst",type=Path)
 ap.add_argument("--exclude",nargs="*",default=[]);ap.add_argument("--n",type=int,default=40);a=ap.parse_args()
 data=json.loads(a.src.read_text());rows=[q for q in data["questions"] if q["id"] not in set(a.exclude)]
 if len(rows)<a.n:raise SystemExit(f"only {len(rows)} after exclusions, need {a.n}")
 rows=rows[:a.n]
 for q in rows:
  rep=validate(q["gold_ir"])
  if not rep["valid"]:raise SystemExit(f"{q['id']} invalid {rep['errors']}")
  result=execute(q["gold_ir"]);want=q["expect"]
  ok=result["status"] in ("answer","data_request") if want=="answer_or_data_request" else result["status"]==want
  if not ok:raise SystemExit(f"{q['id']} {result['status']} != {want}")
 out={"spec_version":"v2.1","note":"blind holdout selected and execution-audited before parser run; no post-run edits permitted",
      "source_generated":str(a.src),"pre_run_exclusions":a.exclude,"questions":rows}
 a.dst.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
 print(json.dumps({"n":len(rows),"sha256":hashlib.sha256(a.dst.read_bytes()).hexdigest(),"path":str(a.dst)},indent=2))
if __name__=="__main__":main()
