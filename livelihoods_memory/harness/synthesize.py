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
- If status is data_request: do NOT invent an answer. Say exactly what is missing or ambiguous and
  ask the ONE most useful question (or name the data to collect).
- Never invent numbers not present in the result. Mention the data source in passing."""

NUMBER_WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10}


def _first_number(text):
    hits = []
    for m in re.finditer(r"\b\d[\d,]*(?:\.\d+)?\b", text.lower()):
        try: hits.append((m.start(), float(m.group().replace(",", ""))))
        except ValueError: pass
    for word, value in NUMBER_WORDS.items():
        m = re.search(rf"\b{word}\b", text.lower())
        if m: hits.append((m.start(), float(value)))
    return min(hits)[1] if hits else None


def _context(exec_result):
    v = exec_result.get("value") or {}
    ctx = {"status": exec_result.get("status"), "evidence_label": exec_result.get("label"),
           "reason": exec_result.get("reason"), "detail": exec_result.get("detail"),
           "kind": v.get("kind"), "scalar": v.get("value"),
           "n_rows": v.get("n_rows", len(v.get("rows", []) or [])),
           "sample_rows": (v.get("rows") or [])[:3],
           "provenance_notes": [p.get("note") for p in exec_result.get("provenance", [])
                                if p.get("note")][:4],
           "sources": list({p.get("route") for p in exec_result.get("provenance", [])
                            if p.get("route")})}
    return ctx


def synthesize(question, exec_result, role="qwen2b"):
    ctx = _context(exec_result)
    # Deterministic honesty surfaces for source gaps. A small model turned no_connector into
    # "no pottery studios exist" (tick-006), conflating tool coverage with real-world absence.
    reason = exec_result.get("reason")
    detail = exec_result.get("detail") or {}
    if exec_result.get("status") == "data_request" and reason == "no_connector":
        entity = detail.get("entity", "that entity")
        return (f"No configured data source maps {entity!r}; this is a source-coverage gap, not "
                "evidence that none exist. Please refine the entity or add a suitable connector.")
    if exec_result.get("status") == "data_request" and reason == "empty_select":
        entity = detail.get("entity", "the requested records")
        return (f"No mapped records were returned for {entity!r}. Treat this as missing coverage, "
                "not evidence that none exist; local data collection or source verification is needed.")
    if exec_result.get("status") == "data_request" and reason == "source_truncated":
        return ("The source exceeded the safe retrieval cap, so an exact or spatially complete "
                "answer would be misleading. Narrow the region or use a complete bulk source.")
    msgs = [{"role": "system", "content": SYNTH_SYSTEM},
            {"role": "user", "content": f"Question: {question}\n\nResult:\n{json.dumps(ctx, default=str)}"}]
    try:
        prose = chat(role, msgs, temperature=0.0, max_tokens=220).strip()
        # A ranking is already sorted by deterministic execution. Tick-004-gen001 found fluent
        # prose that copied every value but reordered Canada from first to last and called the US
        # highest. Preserve the model at the synthesis edge, but reject a reordered surface and
        # fall back to a deterministic rendering of the trusted rows.
        rows = (exec_result.get("value") or {}).get("rows") or []
        if (exec_result.get("value") or {}).get("kind") == "ranking" and rows:
            positions = [prose.lower().find(str(r.get("label", "")).lower()) for r in rows]
            mentioned = [(i, p) for i, p in enumerate(positions) if p >= 0]
            order_ok = bool(mentioned and mentioned[0][0] == 0 and
                            all(a[1] < b[1] for a, b in zip(mentioned, mentioned[1:])))
            if not order_ok:
                def fmt(v):
                    return f"{v:.4g}" if isinstance(v, float) else str(v)
                ranked = ", ".join(f"{r.get('label')} ({fmt(r.get('value'))})" for r in rows)
                sources = {p.get("route") for p in exec_result.get("provenance", [])}
                source = "World Bank" if "worldbank" in sources else \
                    "OpenStreetMap" if "osm" in sources else "the resolved data source"
                caveat = " This is a modelled estimate needing local corroboration." \
                    if exec_result.get("label") == "modelled" else ""
                return f"Ranking: {ranked}. Source: {source}.{caveat}"
        if (exec_result.get("value") or {}).get("kind") == "records":
            n = (exec_result.get("value") or {}).get("n_rows", len(rows))
            first = _first_number(prose)
            if first is None or first != n:
                names = [str(r.get("name")) for r in rows[:3] if r.get("name")]
                examples = f" Examples: {'; '.join(names)}." if names else ""
                sources = {p.get("route") for p in exec_result.get("provenance", [])}
                source = "World Bank" if "worldbank" in sources else \
                    "OpenStreetMap" if "osm" in sources else "the resolved data source"
                return f"Found {n} matching records.{examples} Source: {source}."
        return prose
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
        found = num_in(headline, prose) or num_in(abs(headline), prose)
        if v.get("kind") == "records":
            found = _first_number(prose) == headline
        if not found:
            nums = [int(m.replace(",", "")) for m in
                    re.findall(r"\d[\d,]*", prose) if m.replace(",", "").isdigit()]
            found = any(abs(x - y) == round(abs(headline))
                        for i, x in enumerate(nums) for y in nums[i + 1:])
        s["states_finding"] = found
    elif status == "answer" and isinstance(v.get("value"), str) and s["not_empty"]:
        s["states_finding"] = v["value"].lower() in prose.lower()
    else:
        # direction / ranking / list answers: at least echo a value or label from the result
        rows = (v.get("rows") or [])[:3]
        if status == "answer" and v.get("kind") == "ranking" and rows:
            positions = [prose.lower().find(str(r.get("label", "")).lower()) for r in rows]
            mentioned = [(i, p) for i, p in enumerate(positions) if p >= 0]
            s["states_finding"] = bool(mentioned and mentioned[0][0] == 0 and
                                       all(a[1] < b[1] for a, b in zip(mentioned, mentioned[1:])))
        else:
            s["states_finding"] = True if status != "answer" else (
                any(str(r.get("label", r.get("value", ""))).split(",")[0] in prose
                    for r in rows) or v.get("kind") == "series")
    if exec_result.get("label") == "modelled":
        s["modelled_flagged"] = bool(re.search(r"model|estimat|approximat", prose.lower()))
    else:
        s["modelled_flagged"] = True
    if status == "data_request":
        s["gap_stated"] = bool(re.search(r"missing|no data|source-coverage gap|no configured data source|need|required?|collect|clarif|which |couldn|unable|specify"
                                         r"|cannot|can't|not (?:locate|find|available)|no available",
                                         prose.lower()))
        s["no_fabrication"] = not re.search(r"\b\d{2,}\b", prose)  # no invented big numbers
    else:
        s["gap_stated"] = True
        s["no_fabrication"] = True
    dims = [k for k in s]
    s["overall"] = round(sum(1.0 if s[k] else 0.0 for k in dims) / len(dims), 3)
    return s
