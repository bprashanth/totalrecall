"""run_bench — one pass over a question bank: parse -> validate -> execute -> score -> trace.

The trace JSONL it writes is the primary DELIVERABLE (the training data for the eventual small
model): each line is a full record of {question, model, ir, execution, provenance, scores}.

Usage:
  python3 run_bench.py --model qwen2b --questions questions/seed.json --out ../runs/tick-001
  (add --judge deepseekv4 to also record an LLM equivalence judgment; off by default = cheap)
"""
import argparse
import json
import os
import time

import parser as P
import scorer as S
from executor import execute
from ir_schema import validate


def trim_exec(res):
    """Shrink execution result for the trace (rows can be large)."""
    r = dict(res)
    v = r.get("value")
    if isinstance(v, dict) and isinstance(v.get("rows"), list):
        v = dict(v)
        v["n_rows"] = len(v["rows"])
        rows=v["rows"]
        # Keep annotation evidence auditable in a compact trace.  Source order can put all
        # non-null requested fields after the first three rows even when many values exist.
        layers=[p.get("layer") for p in r.get("provenance",[]) if p.get("op")=="ANNOTATE"]
        if v.get("kind")=="series" and len(rows)>3:
            # Synthesis reports the first and final endpoints.  Persist both so an independent
            # reviewer can replay the prose claim from the compact trace (v6 evidence finding).
            rows=rows[:2]+rows[-1:]
        elif layers:
            layer=layers[-1]
            rows=sorted(rows,key=lambda row: row.get(layer) is None)
        v["rows"] = rows[:3]
        r["value"] = v
    return r


def run(model, questions_path, out_dir, fewshot_path=None, judge=None, limit=None, synth=False):
    os.makedirs(out_dir, exist_ok=True)
    with open(questions_path) as f:
        bank = json.load(f)
    qs = bank["questions"][:limit] if limit else bank["questions"]
    fewshot = None
    if fewshot_path and os.path.exists(fewshot_path):
        with open(fewshot_path) as f:
            fewshot = json.load(f)

    trace_path = os.path.join(out_dir, "traces.jsonl")
    scored = []
    with open(trace_path, "w") as tf:
        for q in qs:
            t0 = time.time()
            pr = P.parse(q["q"], role=model, fewshot=fewshot)
            ir = pr["ir"]
            rep = validate(ir) if ir else None
            try:
                exec_res = execute(ir) if ir else {"status": "error", "reason": "no_ir"}
            except Exception as e:  # executor must never crash the loop
                exec_res = {"status": "error", "reason": "executor_crash",
                            "detail": {"msg": str(e)[:200]}}
            sc = S.score(q, ir, exec_res)
            syn, syn_scores = None, None
            if synth:
                import synthesize as SYN
                syn = SYN.synthesize(q["q"], exec_res, role=model, ir=ir)
                syn_scores = SYN.score_synthesis(q["q"], exec_res, syn)
            rec = {
                "id": q["id"], "sector": q["sector"], "type": q["type"],
                "question": q["q"], "model": model,
                "expect": q.get("expect"), "must_hole": q.get("must_hole", False),
                "repair_events": pr.get("events", []),
                "synthesis": syn, "synthesis_scores": syn_scores,
                "ir": ir, "gold_ir": q.get("gold_ir"), "gold_shape": q.get("gold_shape"),
                "raw_parse": pr["raw"][:500] if not pr["parse_valid"] else None,
                "schema": {"valid": rep["valid"], "errors": rep["errors"],
                           "holes": [h["name"] for h in rep["holes"]],
                           "ops": rep["ops"]} if rep else None,
                "execution": trim_exec(exec_res),
                "scores": sc, "latency_s": round(time.time() - t0, 2),
            }
            tf.write(json.dumps(rec, default=str) + "\n")
            scored.append(rec)
            flag = "OK " if sc["overall"] >= 0.85 else ("~~ " if sc["overall"] >= 0.6 else "XX ")
            print(f"{flag}{q['id']:12} {sc['overall']:.2f} "
                  f"shape={int(sc['shape_match'])} holes={int(sc['holes_correct'])} "
                  f"exec={exec_res.get('status'):12} {q['q'][:44]}")

    agg = S.aggregate(scored)
    summary = {"model": model, "questions": questions_path, "n": agg.get("n"),
               "aggregate": agg, "ts": time.time(), "fewshot": fewshot_path}
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\n== {model} on {os.path.basename(questions_path)} =="
          f"  overall={agg['overall']:.3f}  shape={agg['shape_match']:.2f}"
          f"  holes={agg['holes_correct']:.2f}  exec_class={agg['exec_class']:.2f}  n={agg['n']}")
    return summary, scored


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2b")
    ap.add_argument("--questions", default=os.path.join(os.path.dirname(__file__), "questions", "seed.json"))
    ap.add_argument("--out", required=True)
    ap.add_argument("--fewshot", default=None)
    ap.add_argument("--judge", default=None)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--synth", action="store_true")
    a = ap.parse_args()
    run(a.model, a.questions, a.out, a.fewshot, a.judge, a.limit, a.synth)
