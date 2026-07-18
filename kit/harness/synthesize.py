"""synthesize — the fourth stage: typed result -> short prose answer, plus its scoring.

Until now only compile/execute/dialogue were tested; this adds the answer surface where the
constitution's behavioral rules (short, honest, observed-vs-modelled labelled, gap -> specific
ask) actually face the user. Scoring is MECHANICAL where possible (length, number-presence,
modelled-flag, gap-stated); an LLM judge is deliberately not required for the core dims.
"""
import json
import re

from llm import chat

SYNTH_SYSTEM = """You write the FINAL one-paragraph answer to a user's question about a place,
from a structured result computed by deterministic tools. Rules:
- <= 60 words. Lead with the finding (the number / the list size / the direction / the ranking).
- If evidence_label is "modelled": say clearly it is a modelled estimate needing local corroboration.
- If alignment is present, name the exact common coverage window and that unmatched periods were
  dropped; never imply interpolation. If source vintages differ, name both vintages.
- If status is data_request: do NOT invent an answer. Say exactly what is missing or ambiguous and
  ask the ONE most useful question (or name the data to collect).
- Never invent numbers not present in the result. Mention the data source in passing."""


def _context(exec_result):
    v = exec_result.get("value") or {}
    alignments = [p.get("alignment") for p in exec_result.get("provenance", [])
                  if p.get("alignment")]
    ctx = {"status": exec_result.get("status"), "evidence_label": exec_result.get("label"),
           "reason": exec_result.get("reason"), "detail": exec_result.get("detail"),
           "kind": v.get("kind"), "scalar": v.get("value"),
           "n_rows": v.get("n_rows", len(v.get("rows", []) or [])),
           "sample_rows": (v.get("rows") or [])[:3],
           "measure": v.get("measure"), "unit": v.get("unit"), "grain": v.get("grain"),
           "alignment": alignments[-1] if alignments else v.get("alignment"),
           "vintage": v.get("vintage"),
           "provenance_notes": [p.get("note") for p in exec_result.get("provenance", [])
                                if p.get("note")][:4],
           "sources": list({p.get("route") for p in exec_result.get("provenance", [])
                            if p.get("route")})}
    return ctx


def synthesize(question, exec_result, role="qwen2b"):
    ctx = _context(exec_result)
    msgs = [{"role": "system", "content": SYNTH_SYSTEM},
            {"role": "user", "content": f"Question: {question}\n\nResult:\n{json.dumps(ctx, default=str)}"}]
    try:
        return chat(role, msgs, temperature=0.0, max_tokens=220).strip()
    except RuntimeError as e:
        return f"[synthesis-failed] {e}"


def score_synthesis(question, exec_result, prose):
    """Mechanical behavioral dims; each True/False, overall = mean."""
    s = {}
    words = len(prose.split())
    s["not_empty"] = bool(prose) and not prose.startswith("[synthesis-failed]")
    s["short"] = 0 < words <= 80
    v = exec_result.get("value") or {}
    status = exec_result.get("status")
    # number-presence: if the result carries a headline number, the prose must contain it
    headline = None
    if isinstance(v.get("value"), (int, float)):
        headline = v["value"]
    elif v.get("kind") == "records" and v.get("n_rows") is not None:
        headline = v.get("n_rows")
    if status == "answer" and headline is not None and s["not_empty"]:
        def num_in(x, text):
            if isinstance(x, float):
                cands = {f"{x:.0f}", f"{x:.1f}", f"{x:.2f}", f"{x:,.0f}"}
            else:
                cands = {str(x), f"{x:,}"}
            return any(c in text for c in cands)
        s["states_finding"] = num_in(headline, prose)
    else:
        # direction / ranking / list answers: at least echo a value or label from the result
        s["states_finding"] = True if status != "answer" else (
            any(str(r.get("label", r.get("value", ""))).split(",")[0] in prose
                for r in (v.get("rows") or [])[:3]) or v.get("kind") == "series")
    if exec_result.get("label") == "modelled":
        s["modelled_flagged"] = bool(re.search(r"model|estimat|approximat", prose.lower()))
    else:
        s["modelled_flagged"] = True
    alignment = next((p.get("alignment") for p in exec_result.get("provenance", [])
                      if p.get("alignment")), None)
    if alignment and alignment.get("used_window"):
        start, end = alignment["used_window"]
        s["alignment_surfaced"] = str(start) in prose and str(end) in prose and bool(
            re.search(r"common|overlap|align|drop|unmatched", prose.lower()))
    else:
        s["alignment_surfaced"] = True
    if status == "data_request":
        s["gap_stated"] = bool(re.search(r"missing|no data|need|collect|clarif|which |couldn|unable|specify",
                                         prose.lower()))
        s["no_fabrication"] = not re.search(r"\b\d{2,}\b", prose)  # no invented big numbers
    else:
        s["gap_stated"] = True
        s["no_fabrication"] = True
    dims = [k for k in s]
    s["overall"] = round(sum(1.0 if s[k] else 0.0 for k in dims) / len(dims), 3)
    return s
