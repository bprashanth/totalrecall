"""arms — the non-algebra baselines for the ROI curve.

A2 (algebra scaffold) is run_bench.py. This adds:
  A0  no-tools     : the model answers from parametric knowledge only. Measures memorized facts +
                     hallucination. No data access at all.
  A1  freeform     : the model gets the SAME connectors as freeform tools in an agentic loop, but
                     NO algebra/IR. Isolates the algebra's contribution from the data's.

Ground truth for scoring = the gold IR's EXECUTED result (a number / list-size / direction /
ranking / "data gap"). We compute it once per question, then judge each arm's prose answer against
it: factual agreement (numeric tolerance) + a hallucination flag + a refusal-appropriateness check.
The judge is a strong model (deepseekv4); for the algebra arm no judge is needed (structural score).
"""
import json
import re

from llm import chat, MODELS
from executor import execute
import connectors as C


# ---- ground truth from the gold tree -----------------------------------------
def gold_truth(gold_ir):
    """Execute the gold tree -> a compact ground-truth dict the judge/scorer can use."""
    try:
        res = execute(gold_ir)
    except Exception as e:
        return {"status": "error", "msg": str(e)[:120]}
    v = res.get("value") or {}
    gt = {"status": res.get("status"), "reason": res.get("reason"),
          "evidence_label": res.get("label"), "kind": v.get("kind")}
    if res.get("status") == "answer":
        if isinstance(v.get("value"), (int, float)):
            gt["number"] = v["value"]
        elif isinstance(v.get("value"), str):
            gt["direction"] = v["value"]          # trend answers: 'rising'/'falling' anchors the judge
        if v.get("kind") == "records":
            gt["count"] = len(v.get("rows", []))
        if v.get("kind") == "ranking":
            gt["ranking"] = [r.get("label") for r in v.get("rows", [])]
        if v.get("kind") == "series" and v.get("rows"):
            gt["series_endpoints"] = [v["rows"][0], v["rows"][-1]]
    return gt


# ---- A0: no tools ------------------------------------------------------------
A0_SYSTEM = """Answer the user's question about a place in ONE short paragraph (<=60 words). You have
no tools and no live data — answer from your own knowledge. If you genuinely do not know a specific
number, say so rather than inventing one. Lead with the direct answer."""


def run_a0(question, role):
    try:
        return chat(role, [{"role": "system", "content": A0_SYSTEM},
                           {"role": "user", "content": question}], max_tokens=6000).strip()
    except RuntimeError as e:
        return f"[a0-failed] {e}"


# ---- A1: freeform tools (no IR) ----------------------------------------------
TOOLS_DOC = """You can call these data tools. Emit ONE tool call as a JSON line:
{"tool": "<name>", "args": {...}} and wait for the result, then either call again or give your
FINAL answer as: {"final": "<one short paragraph>"}.
Tools:
- resolve_region(place)                      -> {bbox, lat, lon}    (call first for a place)
- osm_count(entity, place)                   -> number of that amenity (clinic, school, cafe, bus_stop, park, bank, hospital, pharmacy, restaurant, ...)
- osm_near(entity_a, entity_b, place, km)    -> how many entity_a are within km of an entity_b
- wb_series(indicator, place)                -> yearly [{t,value}] for a World Bank indicator (gdp per capita, internet users, unemployment, inflation, life expectancy, electricity access, ...)
Rules: use tools for every fact; never invent a number a tool can give; <=6 tool calls; if the data
isn't available, say exactly what's missing."""


def _tool_exec(call):
    t, a = call.get("tool"), call.get("args", {})
    try:
        if t == "resolve_region":
            r = C.resolve_region(a["place"])
            return {"bbox": r["bbox"], "lat": r["lat"], "lon": r["lon"], "name": r["name"]}
        if t == "osm_count":
            reg = C.resolve_region(a["place"])
            return {"count": len(C.osm_select(a["entity"], reg)["rows"])}
        if t == "osm_near":
            reg = C.resolve_region(a["place"])
            left = C.osm_select(a["entity_a"], reg)["rows"]
            right = C.osm_select(a["entity_b"], reg)["rows"]
            from executor import _relate
            return {"count": len(_relate(left, right, "within", a.get("km", 1.0)))}
        if t == "wb_series":
            reg = C.resolve_region(a["place"])
            s = C.wb_series(a["indicator"], reg)
            return {"series": s["rows"][-6:], "note": s["note"]}
    except Exception as e:
        return {"error": str(e)[:120]}
    return {"error": f"unknown tool {t}"}


def run_a1(question, role, max_steps=6):
    msgs = [{"role": "system", "content": TOOLS_DOC},
            {"role": "user", "content": question}]
    transcript = []
    for _ in range(max_steps):
        try:
            raw = chat(role, msgs, max_tokens=6000, use_cache=False).strip()
        except RuntimeError as e:
            return f"[a1-failed] {e}", transcript
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        if not m:
            return raw, transcript
        try:
            obj = json.loads(m.group(0))
        except json.JSONDecodeError:
            return raw, transcript
        if "final" in obj:
            return obj["final"], transcript
        if "tool" in obj:
            result = _tool_exec(obj)
            transcript.append({"call": obj, "result": result})
            msgs.append({"role": "assistant", "content": json.dumps(obj)})
            msgs.append({"role": "user", "content": "RESULT: " + json.dumps(result)})
        else:
            return raw, transcript
    return "[a1-no-final-after-max-steps]", transcript


# ---- prose scoring against ground truth (judge) ------------------------------
JUDGE_SYSTEM = """You grade an ANSWER against GROUND TRUTH (computed from real data). Return strict
JSON: {"factual": T/F, "hallucinated": T/F, "honest_unknown": T/F, "appropriate_refusal": T/F}.
Distinguish three response modes precisely — this is the whole point:
- factual: the answer STATES the correct key claim/number (numbers within ~10%, or right
  direction/ranking/list-size). A hedge with no figure is NOT factual. If ground truth is a
  "data_request", factual means the answer correctly asks for the missing info.
- hallucinated: the answer STATES A SPECIFIC figure/fact that ground truth does NOT support. An
  answer that gives NO specific number (says it doesn't know / can't say) is NEVER hallucinated.
  STRICTNESS: if ground truth carries only a direction (or no payload), any SPECIFIC number, count,
  distance or named-place claim in the answer counts as hallucinated — a thin ground truth is not a
  license. Fabricating specifics about an unspecified place ("the region has a tertiary center") is
  hallucination even with no digits.
- honest_unknown: the answer declines to give a specific figure and says it lacks the data. This is
  the honest-but-unhelpful mode; it is mutually exclusive with hallucinated.
- appropriate_refusal: ground truth is a data gap AND the answer declines; or ground truth is a
  real answer AND the answer does not wrongly refuse."""


def judge_prose_cursor(question, answer, gt, timeout=120):
    """Second, independent judge: the Cursor Agent CLI (different vendor, different model).
    Same rubric. Used in dual-judge mode; disagreements escalate to the supervisor."""
    import subprocess
    prompt = (JUDGE_SYSTEM + "\nReturn ONLY the JSON object, no prose.\n" +
              json.dumps({"question": question, "answer": answer, "ground_truth": gt}, default=str))
    try:
        out = subprocess.run(["agent", "-p", "--trust", "--mode", "ask", prompt],
                             capture_output=True, text=True, timeout=timeout,
                             cwd="/tmp").stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {"factual": None, "hallucinated": None, "honest_unknown": None,
                "appropriate_refusal": None}
    m = re.search(r"\{.*\}", out, re.DOTALL)
    if not m:
        return {"factual": None, "hallucinated": None, "honest_unknown": None,
                "appropriate_refusal": None}
    try:
        d = json.loads(m.group(0))
        return {k: bool(d.get(k)) for k in
                ("factual", "hallucinated", "honest_unknown", "appropriate_refusal")}
    except json.JSONDecodeError:
        return {"factual": None, "hallucinated": None, "honest_unknown": None,
                "appropriate_refusal": None}


def judge_prose(question, answer, gt, judge_role="deepseekv4"):
    payload = {"question": question, "answer": answer, "ground_truth": gt}
    try:
        raw = chat(judge_role, [{"role": "system", "content": JUDGE_SYSTEM},
                                {"role": "user", "content": json.dumps(payload, default=str)}],
                   max_tokens=4000)
    except RuntimeError:
        return {"factual": None, "hallucinated": None, "appropriate_refusal": None}
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if not m:
        return {"factual": None, "hallucinated": None, "appropriate_refusal": None}
    try:
        d = json.loads(m.group(0))
        return {k: bool(d.get(k)) for k in
                ("factual", "hallucinated", "honest_unknown", "appropriate_refusal")}
    except json.JSONDecodeError:
        return {"factual": None, "hallucinated": None, "honest_unknown": None,
                "appropriate_refusal": None}


if __name__ == "__main__":
    import argparse
    import os
    import time
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["a0", "a1"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--judge", default="deepseekv4")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    bank = json.load(open(a.questions))
    rows = []
    with open(os.path.join(a.out, "traces.jsonl"), "w") as tf:
        for q in bank["questions"]:
            gt = gold_truth(q["gold_ir"])
            t0 = time.time()
            if a.arm == "a0":
                ans, transcript = run_a0(q["q"], a.model), None
            else:
                ans, transcript = run_a1(q["q"], a.model)
            js = judge_prose(q["q"], ans, gt, a.judge)
            rec = {"id": q["id"], "sector": q["sector"], "type": q["type"], "question": q["q"],
                   "model": a.model, "arm": a.arm, "answer": ans, "ground_truth": gt,
                   "judge": js, "transcript": transcript, "latency_s": round(time.time() - t0, 2)}
            tf.write(json.dumps(rec, default=str) + "\n")
            rows.append(rec)
            print(f"{q['id']:12} factual={js['factual']} halluc={js['hallucinated']} {q['q'][:40]}")
    def rate(k):
        return round(sum(1 for r in rows if r["judge"].get(k)) / len(rows), 3)
    summ = {"model": a.model, "arm": a.arm, "n": len(rows), "factual": rate("factual"),
            "hallucinated": rate("hallucinated"), "honest_unknown": rate("honest_unknown"),
            "mean_latency_s": round(sum(r["latency_s"] for r in rows) / len(rows), 2)}
    json.dump(summ, open(os.path.join(a.out, "summary.json"), "w"), indent=2)
    print(f"\n== {a.model} {a.arm} == factual={summ['factual']} halluc={summ['hallucinated']} "
          f"honest_unknown={summ['honest_unknown']} n={len(rows)}")
