#!/usr/bin/env python3
"""Pre-run mechanical repair: add the required null time to SELECT leaves when omitted."""
import argparse,json
from pathlib import Path
ap=argparse.ArgumentParser();ap.add_argument("bank",type=Path);a=ap.parse_args()
data=json.loads(a.bank.read_text());changed=0
def walk(v):
    global changed
    if isinstance(v,list):
        for x in v:walk(x)
    elif isinstance(v,dict):
        if v.get("op")=="SELECT" and "time" not in v:v["time"]=None;changed+=1
        for x in v.values():walk(x)
for row in data["questions"]:walk(row["gold_ir"])
a.bank.write_text(json.dumps(data,indent=1,ensure_ascii=False)+"\n")
print(json.dumps({"bank":str(a.bank),"select_time_null_added":changed}))
