"""multiturn — test the DIALOGUE layer: hole -> clarifying question -> merge answer -> execute.

The algebra's Layer-3 claim: a hole IS the clarifying question, and the user's reply should BIND
the hole, not restart the parse. Protocol per case:

  turn 1: parse(question)            -> tree with holes (else FAIL asked_when_needed)
  turn 2: the harness renders the clarifying question from the holes; a scripted user reply
          (the case's hidden goal) is given; the parser BINDS: parse_bind(prev_ir, reply) -> tree
  check : no holes remain, skeleton unchanged (binding must not rewrite the question),
          executes to the expected class.

Two binding strategies are measured head-to-head:
  - model-bind: the small model merges the reply into the tree (a second LLM call)
  - mech-bind: pure code — substitute the reply's values into the holes by slot type
The spec question this answers: does hole-binding even NEED a model? (If mech-bind wins, the
dialogue layer is code, and the model is only ever a question->tree compiler.)

Trace: every case appends {question, ir1, holes, reply, bound_ir(model), bound_ir(mech), scores}
to the run's traces.jsonl — multi-turn training data for the small model.
"""
import json
import os
import time

import parser as P
from ir_schema import validate, is_hole
from executor import execute
from scorer import _shape
from llm import chat

BIND_SYSTEM = """You previously translated a user's question into a JSON expression tree that
contains HOLES — strings starting with "?" marking missing information. The user has now answered
the clarifying question. Fill the holes with the user's values and output the SAME tree with holes
replaced. Do NOT restructure the tree, do NOT add or remove operations, do NOT change any other
field. Output ONLY the JSON tree."""


def clarifying_question(holes):
    """Render the ask from the holes — deterministic, no model."""
    slots = sorted({h["name"].lstrip("?").replace("_", " ") for h in holes})
    return "Could you tell me: " + " and ".join(f"which {s}" for s in slots) + "?"


def model_bind(ir, reply, role="qwen2b"):
    msgs = [{"role": "system", "content": BIND_SYSTEM},
            {"role": "user", "content": f"Tree:\n{json.dumps(ir)}\n\nUser's answer: {reply}"}]
    try:
        raw = chat(role, msgs, temperature=0.0, max_tokens=800)
    except RuntimeError:
        return None
    return P.extract_json(raw)


def mech_bind(ir, slot_values):
    """Pure-code binding: walk the tree, replace each hole with the scripted slot value.
    slot_values maps hole-name (with or without '?') -> value. A region hole gets a REGION node."""
    def sub(v, field):
        if is_hole(v):
            key = v.lstrip("?")
            val = slot_values.get(v) or slot_values.get(key) or slot_values.get(field)
            if val is None:
                return v
            if field == "region":
                return {"op": "REGION", "place": val}
            return val
        return v

    def walk(n):
        if not isinstance(n, dict):
            return n
        out = {}
        for k, v in n.items():
            if isinstance(v, dict) and "op" in v:
                out[k] = walk(v)
            elif isinstance(v, dict):
                out[k] = {kk: sub(vv, f"{k}.{kk}") for kk, vv in v.items()}
            else:
                out[k] = sub(v, k)
        return out
    return walk(ir)


def run_case(case, role="qwen2b"):
    q, reply, slots = case["q"], case["reply"], case.get("slots", {})
    rec = {"id": case["id"], "question": q, "reply": reply, "ts": time.time()}
    pr = P.parse(q, role=role)
    ir1 = pr["ir"]
    rec["ir_turn1"] = ir1
    rep1 = validate(ir1) if ir1 else None
    rec["holes"] = [h["name"] for h in rep1["holes"]] if rep1 else []
    s = {"asked_when_needed": bool(rep1 and rep1["holes"])}
    if not s["asked_when_needed"]:
        rec["scores"] = {**s, "overall": 0.0}
        return rec
    rec["clarify_rendered"] = clarifying_question(rep1["holes"])

    for name, bind in (("model", lambda: model_bind(ir1, reply, role)),
                       ("mech", lambda: mech_bind(ir1, slots))):
        b = bind()
        rep2 = validate(b) if b else None
        ok_bound = bool(rep2 and rep2["valid"] and not rep2["holes"])
        same_skeleton = (_shape(b) == _shape(ir1)) if b else False
        ex = execute(b) if ok_bound else {"status": "not_run"}
        s[f"{name}_bound"] = ok_bound
        s[f"{name}_skeleton_kept"] = same_skeleton
        s[f"{name}_exec_ok"] = ex.get("status") == case.get("expect", "answer")
        rec[f"ir_bound_{name}"] = b
        rec[f"exec_{name}"] = {"status": ex.get("status"), "reason": ex.get("reason")}
    dims = [v for k, v in s.items()]
    s["overall"] = round(sum(1.0 if v else 0.0 for v in dims) / len(dims), 3)
    rec["scores"] = s
    return rec


CASES = [
    {"id": "mt-01", "q": "Tell me about the transport options here.",
     "reply": "I mean bus stops, in Rosario, Argentina.",
     "slots": {"transport_type": "bus stop", "transport_option": "bus stop",
               "facility_type": "bus stop", "amenity_type": "bus stop",
               "place": "Rosario, Argentina"}, "expect": "answer"},
    {"id": "mt-02", "q": "Map the stations here.",
     "reply": "Railway stations, around Brno, Czechia.",
     "slots": {"station_type": "railway station", "facility_type": "railway station",
               "entity": "railway station", "place": "Brno, Czechia"}, "expect": "answer"},
    {"id": "mt-03", "q": "Are there many fuel stations around here?",
     "reply": "I'm asking about Mombasa, Kenya.",
     "slots": {"place": "Mombasa, Kenya"}, "expect": "answer"},
    {"id": "mt-04", "q": "How is air travel doing around here?",
     "reply": "Vietnam — say air passengers carried.",
     "slots": {"place": "Vietnam", "indicator": "air passengers carried",
               "travel_indicator": "air passengers carried",
               "air_travel_indicator": "air passengers carried",
               "transport_indicator": "air passengers carried"}, "expect": "answer"},
    {"id": "mt-05", "q": "Map the parking around here.",
     "reply": "In Da Nang, Vietnam.",
     "slots": {"place": "Da Nang, Vietnam", "amenity_type": "parking",
               "facility_type": "parking"}, "expect": "answer"},
]


def main(out_dir, role="qwen2b"):
    os.makedirs(out_dir, exist_ok=True)
    rows = []
    with open(os.path.join(out_dir, "traces.jsonl"), "w") as tf:
        for c in CASES:
            r = run_case(c, role)
            rows.append(r)
            tf.write(json.dumps(r, default=str) + "\n")
            s = r["scores"]
            print(f"{c['id']}: overall={s['overall']} asked={int(s['asked_when_needed'])} "
                  f"model[bound={int(s.get('model_bound', 0))} skel={int(s.get('model_skeleton_kept', 0))} "
                  f"exec={int(s.get('model_exec_ok', 0))}] "
                  f"mech[bound={int(s.get('mech_bound', 0))} skel={int(s.get('mech_skeleton_kept', 0))} "
                  f"exec={int(s.get('mech_exec_ok', 0))}]")
    agg = sum(r["scores"]["overall"] for r in rows) / len(rows)
    print(f"\n== multiturn ({role}) == overall={agg:.3f} n={len(rows)}")
    with open(os.path.join(out_dir, "summary.json"), "w") as f:
        json.dump({"overall": agg, "n": len(rows)}, f, indent=2)


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "../runs/tick-008-mt",
         sys.argv[2] if len(sys.argv) > 2 else "qwen2b")
