"""arms — the non-algebra baselines for the ROI curve.

A2 (algebra scaffold) is normally run_bench.py. This file can also render A2 prose for an
answer-surface head-to-head. It adds:
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
import parser as P
import synthesize as SYN


# ---- ground truth from the gold tree -----------------------------------------
def gold_truth(gold_ir):
    """Execute the gold tree -> a compact ground-truth dict the judge/scorer can use."""
    try:
        res = execute(gold_ir)
    except Exception as e:
        return {"status": "error", "msg": str(e)[:120]}
    v = res.get("value") or {}
    gt = {"status": res.get("status"), "reason": res.get("reason"),
          "detail": res.get("detail"), "evidence_label": res.get("label"),
          "kind": v.get("kind"), "source": v.get("source"), "note": v.get("note"),
          "unit": v.get("unit"), "provenance": res.get("provenance", [])}
    if res.get("status") == "answer":
        if isinstance(v.get("value"), (int, float)):
            gt["number"] = v["value"]
        elif isinstance(v.get("value"), str):
            gt["direction"] = v["value"]          # trend answers: 'rising'/'falling' anchors the judge
        if v.get("kind") in {"records", "field"}:
            gt["count"] = len(v.get("rows", []))
            # The answer may truthfully name returned species/sites. Give the judge enough executed
            # evidence to distinguish that from parametric invention without sending full payloads.
            gt["sample_rows"] = v.get("rows", [])[:5]
        if v.get("kind") == "ranking":
            gt["ranking"] = [r.get("label") for r in v.get("rows", [])]
            gt["ranking_rows"] = v.get("rows", [])
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
TOOLS_DOC = """You can call these ecology data tools. Emit ONE tool call as a JSON line:
{"tool": "<name>", "args": {...}} and wait for the result, then either call again or give your
FINAL answer as: {"final": "<one short paragraph>"}.
Tools:
- resolve_region(place) -> bbox and centroid.
- occurrence_records(entity, place, start?, end?) -> licensed GBIF+iNaturalist presence records.
- recent_birds(place, start?, end?) -> recent bbox-filtered eBird observation rows.
- ndvi_series(place, start?, end?) -> annual QA-masked MODIS bbox-mean NDVI.
- survey_sites(place) -> published Anamalai vegetation survey sites (not interventions).
- annotate_sites(place, layer, start?, end?) -> survey sites annotated with elevation, slope,
  land cover, NDVI, surface-water occurrence, or ecoregion.
- relate_records(entity_a, entity_b, place, relation, km) -> occurrence records of A within/beyond
  the threshold of B; entity_b may be "survey sites".
Rules: use tools for every data claim; occurrence counts are observation records, NEVER organism
abundance/population. NDVI is a geocoder-bbox proxy. Preserve OBSERVED/MODELLED/PROXY labels in the
answer. Use at most 8 calls. If the tool or requested measurement is unavailable, state exactly
what data is missing; do not substitute another quantity."""


def _time_args(a):
    if not a.get("start") and not a.get("end"):
        return None
    return {"start": a.get("start"), "end": a.get("end")}


def _compact(out, limit=8):
    rows = out.get("rows") or []
    return {"kind": out.get("kind"), "n_rows": len(rows), "rows": rows[:limit],
            "source": out.get("source"), "label": out.get("label"), "note": out.get("note"),
            "unit": out.get("unit"), "measure_field": out.get("measure_field")}


def _occurrence(entity, place, time_value=None):
    reg = C.resolve_region(place)
    resolution = C.resolve_ecology_entity(entity)
    if not resolution:
        raise ValueError(f"taxon not safely resolved: {entity}")
    if resolution.get("kind") in {"ambiguous", "unverified_taxon", "unsupported_measure"}:
        raise ValueError(resolution.get("note") or f"unsafe entity: {resolution.get('kind')}")
    if resolution.get("kind") != "taxon":
        raise ValueError(f"{entity!r} is not a taxon occurrence query")
    return C.taxon_occurrences(entity, reg, time_value)


def _tool_exec(call):
    t, a = call.get("tool"), call.get("args", {})
    try:
        if t == "resolve_region":
            r = C.resolve_region(a["place"])
            return {"bbox": r["bbox"], "lat": r["lat"], "lon": r["lon"], "name": r["name"]}
        if t == "occurrence_records":
            return _compact(_occurrence(a["entity"], a["place"], _time_args(a)))
        if t == "recent_birds":
            reg = C.resolve_region(a["place"])
            return _compact(C.ebird_recent(reg, _time_args(a)))
        if t == "ndvi_series":
            reg = C.resolve_region(a["place"])
            return _compact(C.ee_ndvi_series(reg, _time_args(a)), limit=40)
        if t == "survey_sites":
            reg = C.resolve_region(a["place"])
            return _compact(C.anamalai_survey_sites(reg))
        if t == "annotate_sites":
            reg = C.resolve_region(a["place"])
            sites = C.anamalai_survey_sites(reg)
            out = C.annotate_records(sites["rows"], a["layer"], _time_args(a))
            return _compact(out, limit=30)
        if t == "relate_records":
            left_out = _occurrence(a["entity_a"], a["place"], _time_args(a))
            if str(a["entity_b"]).lower() in {"survey site", "survey sites",
                                                     "vegetation survey sites"}:
                right_out = C.anamalai_survey_sites(C.resolve_region(a["place"]))
            else:
                right_out = _occurrence(a["entity_b"], a["place"], _time_args(a))
            from executor import _relate
            rows = _relate(left_out["rows"], right_out["rows"],
                           a.get("relation", "within"), a.get("km", 1.0))
            return {"kind": "records", "n_rows": len(rows), "rows": rows[:8],
                    "source": f"{left_out['source']} related to {right_out['source']}",
                    "label": "observed", "note": "record relation; not organism abundance"}
    except Exception as e:
        return {"error": str(e)[:120]}
    return {"error": f"unknown tool {t}"}


def run_a1(question, role, max_steps=8):
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


def run_a2(question, role):
    """Algebra arm: local parse, deterministic execution, audited concise synthesis."""
    parsed = P.parse(question, role=role)
    result = execute(parsed["ir"]) if parsed.get("ir") else {
        "status": "error", "reason": "no_ir"}
    answer = SYN.synthesize(question, result, role=role)
    transcript = {"ir": parsed.get("ir"), "repair_events": parsed.get("events", []),
                  "execution_status": result.get("status"), "execution_reason": result.get("reason"),
                  "evidence_label": result.get("label"),
                  "synthesis_audit": SYN.score_synthesis(question, result, answer)}
    return answer, transcript


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


def judge_prose_cursor(question, answer, gt, timeout=120,
                       model="gpt-5.4-mini-low"):
    """Second, independent judge: the Cursor Agent CLI (different vendor, different model).
    Same rubric. Used in dual-judge mode; disagreements escalate to the supervisor."""
    import subprocess
    prompt = (JUDGE_SYSTEM + "\nReturn ONLY the JSON object, no prose.\n" +
              json.dumps({"question": question, "answer": answer, "ground_truth": gt}, default=str))
    try:
        out = subprocess.run(["agent", "-p", "--trust", "--mode", "ask", "--model", model,
                              prompt],
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
    ap.add_argument("--arm", choices=["a0", "a1", "a2"], required=True)
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
            elif a.arm == "a1":
                ans, transcript = run_a1(q["q"], a.model)
            else:
                ans, transcript = run_a2(q["q"], a.model)
            js = (judge_prose_cursor(q["q"], ans, gt) if a.judge == "cursor"
                  else judge_prose(q["q"], ans, gt, a.judge))
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
