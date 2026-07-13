#!/usr/bin/env python3
"""Round-2 breaker runner — evidence collection for the >=30 out-of-op-set probes.

For every probe in questions/breakers-round2.json:
  - the 2B parser (NEVER the supervisor) compiles the question;
  - the tree is validated and executed;
  - probes with a gold (judgement expressible / executor-gap) are scored normally;
  - inexpressible probes record WHAT THE PARSER DID under pressure (the evidence a
    spec proposal cites: does the model hallucinate an op, weaken the question, hole it,
    or produce a defensible partial tree?).

Output: runs/<out>/traces.jsonl + summary.json (same trace fields as run_bench where they
apply; extra fields judgement/capability_family/parser_behavior are additive).
"""
import argparse
import json
import os
import time

import parser as P
import scorer as S
from executor import execute
from ir_schema import validate

HERE = os.path.dirname(os.path.abspath(__file__))


def parser_behavior(rec):
    """Deterministic classification of what the parse did with an inexpressible ask."""
    ir, rep, ex = rec["ir"], rec["schema"], rec["execution"]
    if ir is None:
        return "no_parse"
    if rep and not rep["valid"]:
        errs = " ".join(rep["errors"])
        return "invented_op_or_field" if ("unknown op" in errs or "unknown field" in errs) \
            else "invalid_tree"
    if rep and rep["holes"]:
        return "holed_the_gap"  # asked instead of guessing — the honest degradation
    if ex.get("status") == "data_request":
        return "honest_data_request"
    return "weakened_to_expressible"  # executed something narrower than the question


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen2b")
    ap.add_argument("--questions", default=os.path.join(HERE, "..", "questions",
                                                        "breakers-round2.json"))
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bank = json.load(open(a.questions))
    rows = []
    with open(os.path.join(a.out, "traces.jsonl"), "w") as tf:
        for q in bank["questions"]:
            t0 = time.time()
            pr = P.parse(q["q"], role=a.model)
            ir = pr["ir"]
            rep = validate(ir) if ir else None
            try:
                ex = execute(ir) if ir else {"status": "error", "reason": "no_ir"}
            except Exception as e:
                ex = {"status": "error", "reason": "executor_crash",
                      "detail": {"msg": str(e)[:200]}}
            rec = {
                "id": q["id"], "sector": q["sector"], "type": "BREAKER",
                "capability_family": q["capability_family"], "judgement": q["judgement"],
                "question": q["q"], "model": a.model, "reason": q["reason"],
                "repair_events": pr.get("events", []),
                "ir": ir, "gold_ir": q.get("gold_ir"), "gold_shape": q.get("gold_shape"),
                "expect": q.get("expect"),
                "schema": {"valid": rep["valid"], "errors": rep["errors"],
                           "holes": [h["name"] for h in rep["holes"]],
                           "ops": rep["ops"]} if rep else None,
                "execution": {k: v for k, v in ex.items() if k != "value"} | (
                    {"value_kind": (ex.get("value") or {}).get("kind"),
                     "value_scalar": (ex.get("value") or {}).get("value"),
                     "n_rows": len((ex.get("value") or {}).get("rows", []) or [])}
                    if ex.get("status") == "answer" else {}),
                "latency_s": round(time.time() - t0, 2),
            }
            rec["parser_behavior"] = parser_behavior(rec)
            if q.get("gold_ir"):
                qrow = {"gold_shape": q.get("gold_shape"), "expect": q.get("expect", "answer")}
                rec["scores"] = S.score(qrow, ir, ex)
                # gold-side check: does the GOLD itself execute to the expected class?
                gex = execute(q["gold_ir"])
                rec["gold_execution_status"] = gex["status"]
                gv = gex.get("value") or {}
                rec["gold_value"] = {"kind": gv.get("kind"), "value": gv.get("value"),
                                     "n_rows": len(gv.get("rows", []) or [])}
                rec["gold_note"] = "; ".join(p.get("note", "") for p in gex.get("provenance", [])
                                             if p.get("op") in ("COMPARE", "AGGREGATE", "RELATE"))[:300]
            rows.append(rec)
            tf.write(json.dumps(rec, default=str) + "\n")
            beh = rec["parser_behavior"]
            sc = rec.get("scores", {}).get("overall")
            print(f"{q['id']} [{q['capability_family']:18}] {q['judgement']:13} "
                  f"parser={beh:24} score={sc if sc is not None else '-'}")
    summary = {
        "model": a.model, "n": len(rows), "ts": time.time(),
        "by_judgement": {},
        "by_parser_behavior": {},
        "scored": {r["id"]: r["scores"]["overall"] for r in rows if "scores" in r},
    }
    for r in rows:
        summary["by_judgement"][r["judgement"]] = summary["by_judgement"].get(r["judgement"], 0) + 1
        summary["by_parser_behavior"][r["parser_behavior"]] = \
            summary["by_parser_behavior"].get(r["parser_behavior"], 0) + 1
    with open(os.path.join(a.out, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
