"""mine — read a tick's traces.jsonl, cluster failures, classify each by layer.

Layers (FINDINGS.md convention):
  HARNESS   our code crashed / mis-built a request
  CONNECTOR data source returned nothing for a legitimate query (geocode, tag gap, indicator gap)
  PARSER    the model produced the wrong tree (shape/holes/estimate)
  SPEC      the model's tree is defensible but the spec/vocab couldn't express or accept it
  SCORING   execution succeeded and the tree is defensible but the gold marked it wrong

Heuristics keep this deterministic; the supervisor reads the output and decides the fix.
Usage: python3 mine.py ../runs/tick-003
"""
import json
import os
import sys
from collections import Counter


def classify(rec):
    s = rec["scores"]
    ex = rec.get("execution") or {}
    schema = rec.get("schema") or {}
    tags = []
    if not s["parse_valid"]:
        tags.append(("PARSER", "no JSON produced"))
        return tags
    if not s["schema_valid"]:
        errs = "; ".join(schema.get("errors", [])[:2])
        # unknown op / vocab miss = the model wanted a word we don't accept -> maybe SPEC
        if "not in" in errs or "unknown op" in errs:
            tags.append(("SPEC?", f"vocab/op rejection: {errs}"))
        else:
            tags.append(("PARSER", f"schema errors: {errs}"))
    if ex.get("status") == "error":
        tags.append(("HARNESS", f"{ex.get('reason')}: {json.dumps(ex.get('detail'))[:120]}"))
    if ex.get("status") == "data_request" and ex.get("reason") in ("empty_select", "no_connector"):
        tags.append(("CONNECTOR", f"{ex.get('reason')}: {json.dumps(ex.get('detail'))[:120]}"))
    if not s["shape_match"] and s["schema_valid"]:
        got = Counter(o for o in schema.get("ops", []) if o != "REGION")
        tags.append(("PARSER/SCORING", f"shape mismatch: got {dict(got)} want {rec.get('gold_shape')}"))
    if not s["holes_correct"]:
        tags.append(("PARSER", f"holes wrong: holes={schema.get('holes')} must_hole={rec.get('must_hole', False)}"))
    if not s["estimate_ok"]:
        tags.append(("PARSER", "transfer question but no ESTIMATE in tree"))
    if not tags:
        tags.append(("EXEC", f"exec_class miss: status={ex.get('status')} expected={rec.get('expect')}"))
    return tags


def mine(run_dir, threshold=0.85):
    path = os.path.join(run_dir, "traces.jsonl")
    rows = [json.loads(l) for l in open(path)]
    bad = [r for r in rows if r["scores"]["overall"] < threshold]
    print(f"{len(rows)} traces; {len(bad)} below {threshold}\n")
    layer_counts = Counter()
    for r in bad:
        tags = classify(r)
        print(f"--- {r['id']} ({r['sector']}/{r['type']}) overall={r['scores']['overall']}")
        print(f"    Q: {r['question']}")
        print(f"    IR: {json.dumps(r['ir'])[:180]}")
        for layer, why in tags:
            layer_counts[layer] += 1
            print(f"    [{layer}] {why}")
    print("\n== failure layers ==")
    for k, v in layer_counts.most_common():
        print(f"  {k:14} {v}")
    # per-dimension aggregate
    dims = ["parse_valid", "schema_valid", "shape_match", "holes_correct",
            "estimate_ok", "exec_class", "exec_grounded"]
    print("\n== dimension means ==")
    for d in dims:
        m = sum(1.0 if r["scores"][d] else 0.0 for r in rows) / len(rows)
        print(f"  {d:14} {m:.2f}")
    return bad


if __name__ == "__main__":
    mine(sys.argv[1] if len(sys.argv) > 1 else "../runs/tick-003",
         float(sys.argv[2]) if len(sys.argv) > 2 else 0.85)
