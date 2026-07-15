"""indic_autopsy — split Indic-eval misses into LEXICON/RESOLVER vs REGISTER/PHRASING vs OTHER.

The decision gate for the INDIAN-DIALECT experiment needs the miss mix, not just the score:
  LEXICON   the tree is right-shaped but an entity/place failed to resolve or routed wrong
            (no_connector, empty_select on an aliased entity, wrong-source route)
  REGISTER  the tree itself is wrong on dialect phrasing: shape mismatch, spurious/missing
            holes, dropped constraints — the model misread the register, not the words
  OTHER     invalid JSON, infra errors, gold disputes

Usage: python3 indic_autopsy.py ../runs/indic-base-<model> [...more run dirs]
"""
import json
import os
import sys
from collections import Counter


def classify(rec):
    s = rec["scores"]
    ex = rec.get("execution") or {}
    schema = rec.get("schema") or {}
    if not s["parse_valid"] or not s["schema_valid"]:
        return ("OTHER", "invalid parse/schema")
    if ex.get("status") == "error":
        return ("OTHER", f"exec error: {ex.get('reason')}")
    shape_ok = bool(s["shape_match"])
    holes_ok = bool(s["holes_correct"])
    if shape_ok and holes_ok and ex.get("status") == "data_request" \
            and ex.get("reason") in ("no_connector", "empty_select"):
        det = json.dumps(ex.get("detail", {}))[:100]
        return ("LEXICON", f"{ex.get('reason')}: {det}")
    if not shape_ok or not holes_ok:
        why = []
        if not shape_ok:
            got = Counter(o for o in (schema.get("ops") or []) if o not in ("REGION", "AGGREGATE"))
            why.append(f"shape got {dict(got)} want {rec.get('gold_shape')}")
        if not holes_ok:
            why.append(f"holes {schema.get('holes')} (must_hole={rec.get('must_hole')})")
        return ("REGISTER", "; ".join(why))
    if ex.get("status") != "answer" and rec.get("expect", "answer") == "answer":
        return ("LEXICON", f"exec {ex.get('status')}:{ex.get('reason')}")
    return ("OTHER", "grounding/exec-class residual")


def main(run_dirs, thresh=0.85):
    for rd in run_dirs:
        tp = os.path.join(rd, "traces.jsonl")
        if not os.path.exists(tp):
            print(f"{rd}: no traces")
            continue
        rows = [json.loads(l) for l in open(tp)]
        misses = [r for r in rows if r["scores"]["overall"] < thresh]
        cats = Counter()
        print(f"\n== {os.path.basename(rd)}  n={len(rows)} misses={len(misses)}")
        for r in misses:
            cat, why = classify(r)
            cats[cat] += 1
            meta = r.get("expect"), (r.get("id") or "")
            style = ""
            print(f"  {cat:8} {r['scores']['overall']:.2f} [{r.get('id','')}] {why[:90]}")
            print(f"           q: {r['question'][:90]}")
        tot = sum(cats.values()) or 1
        print("  MIX: " + ", ".join(f"{k}={v} ({v/tot:.0%})" for k, v in cats.most_common()))


if __name__ == "__main__":
    main(sys.argv[1:])
