"""propose — widen the question bank with NEUTRALLY-generated questions (improvement-loop.md).

The generator (a remote model, not the parser under test) sees only the sector list, the
question TYPES, and the coverage counts — never the parser's outputs — so the bank can't
flatter the system. Gold IR is authored by the same strong model, then STRUCTURALLY validated
(schema) and EXECUTED; a candidate is admitted only if its gold actually runs to the expected
outcome class. That keeps 'gold' honest without hand-authoring every tree.

Usage: python3 propose.py --n 10 --out questions/gen-001.json
"""
import argparse
import json
import os
import sys

from llm import chat
from ir_schema import validate
from executor import execute
import parser as P

SECTORS = ["livelihoods"]
TYPES = ["STATE", "RELATION", "CHANGE", "TREND", "TRANSFER", "AMBIGUOUS", "BEHAVIOUR",
         "COMPOSITE", "RANKING"]
# COMPOSITE questions are BREAKER PROBES (reference loop method): multi-step compositions that
# may exceed the current op set (ranking over 3+ regions, nested relations, conditional filters).
# A composite whose gold can't be expressed/validated is logged to breakers.json — recurring
# breaker clusters are exactly how a missing primitive announces itself.

GEN_PROMPT = """You are generating benchmark questions a real user might ask about a PLACE, for a
system that answers from verified data (present-day livelihood-infrastructure records from
OpenStreetMap; yearly country indicators from the World Bank; country labor-survey series from
ILOSTAT; and NUTS-2 regional labor series from Eurostat).

Generate {n} questions as a JSON array. Each item:
  {{"sector": one of {sectors},
    "type": one of {types},
    "q": "the question, natural phrasing, one sentence"}}

Rules:
- STATE: how many / where are <livelihood facility> in <named city>. Verified OSM entities:
  marketplaces, coworking spaces, craft workshops, banks, and ATMs. Use real, mid-sized world
  cities (vary continents). A facility is NOT proof of a job, income, or behavior.
- RELATION: which <facility A> in <city> are near/within 1km of <facility B>; also probe explicit
  distances and negation ("no B within D") where natural.
- CHANGE: by how much did <indicator> change between <year1> and <year2> in <country>. Verified
  indicators: unemployment, total labor force, self-employment, vulnerable employment,
  labor-force participation, youth unemployment, wage and salaried workers, employment in
  services, employment in agriculture.
- ILOSTAT verified exact measures: informal employment rate, female/male informal employment
  rate, informal employment rate in agriculture, average weekly hours worked, female/male average
  weekly hours worked, labour/labor underutilization rate, time related underemployment rate.
  Prefer France/Germany/Spain during 2015–2023; Kenya weekly hours has only 2019 and 2021.
- Eurostat verified NUTS-2 regions: Ile de France, Berlin, Madrid region, Catalonia, Lombardy,
  Warsaw capital region. Measures: employment rate, female/male employment rate, employed persons,
  unemployment rate. Use 2021–2024.
- TREND: is <indicator> rising/falling in <country>.
- TRANSFER: we have no <amenity> data for <small town> — estimate from <nearby big city>.
- AMBIGUOUS: a question that does NOT name the place or the entity type ("around here", "the
  facilities") — the right behavior is to ask a clarifying question.
- BEHAVIOUR: asks about people's motives/preferences/intent (not measurable from these sources).
- COMPOSITE: a harder SINGLE-CLAUSE question that combines operations — e.g. "does <city A> have
  more marketplaces than <city B>?", "of the craft workshops in <city>, how many are near a
  marketplace?", or a within-X-but-not-near-Y conjunction. Push complexity here.
- RANKING: requires ordering MORE THAN TWO things — "which of <city A>, <city B> and <city C>
  has the most <amenity>?", "rank <country A>/<country B>/<country C> by <indicator>", "which
  of these three cities has the fewest <amenity>?". Always name 3+ places explicitly.
- Exercise ascending and top-k ranks, explicit time windows, same-unit ratios, source-compatible
  comparisons, presence, co-occurrence, and annotations where natural. Never compare incompatible
  units or rank different measures.
- Mix difficulty; vary phrasing (don't reuse sentence templates); no two questions about the same
  city+entity pair.
- Every item must ask ONE answerable clause. Do not join two questions with "and". Do not ask for
  unions such as "markets and banks"; the frozen algebra has no record-set union.
- INDIRECT MODE (when asked for "indirect" style): phrase questions the way real users talk —
  goal-first and implicit, never naming the operation: "I'm opening a bakery in <city>; how
  saturated is the market?" (= count bakeries/cafes), "my daughter starts school next year in
  <city> — what are my options near the center?" (= where are schools), "is <country> getting
  richer?" (= GDP trend). The DATA need must still be inferable and answerable from the sources.
Coverage gaps to fill (prefer these): {gaps}
Output ONLY the JSON array."""

GOLD_PROMPT_SUFFIX = """\n\nIMPORTANT: this is for GOLD data. Produce the single best tree. If the
question type is AMBIGUOUS or BEHAVIOUR, holes are REQUIRED for the unspecified parts."""


def coverage_gaps(bank_paths):
    from collections import Counter
    seen = Counter()
    for p in bank_paths:
        if os.path.exists(p):
            d = json.load(open(p))
            if not isinstance(d, dict) or "questions" not in d:
                continue  # e.g. breakers.json swept in by a glob — not a bank
            for q in d["questions"]:
                seen[(q["sector"], q["type"])] += 1
    gaps = [f"{s}/{t}" for s in SECTORS for t in TYPES if seen[(s, t)] == 0]
    return gaps[:12] or ["none — just vary cities/countries"]


def generate(n, gaps, role="deepseekv4"):
    msg = GEN_PROMPT.format(n=n, sectors=SECTORS, types=TYPES, gaps=", ".join(gaps))
    # Cache the neutral generator draw so interrupted overnight admission can resume exactly the
    # same candidate distribution; novelty comes from a new prompt/epoch, not accidental retries.
    raw = chat(role, [{"role": "user", "content": msg}], temperature=0.8, max_tokens=12000,
               use_cache=True)
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end <= start:
        raise RuntimeError(f"generator returned no JSON array: {raw[:200]!r}")
    return json.loads(raw[start:end + 1])


def author_gold(q, role="deepseekv4"):
    """Strong model writes the gold IR using the SAME parser prompt (plus gold suffix)."""
    msgs = P.build_messages(q["q"])
    msgs[0]["content"] += GOLD_PROMPT_SUFFIX
    try:
        raw = chat(role, msgs, temperature=0.0, max_tokens=4000)
    except RuntimeError:
        return None
    return P.extract_json(raw)


def expected_outcome(qtype):
    if qtype in ("AMBIGUOUS", "BEHAVIOUR"):
        return "data_request"
    if qtype == "TRANSFER":
        return "answer_or_data_request"
    return "answer"


def log_breaker(q, gold, why, path="questions/breakers.json"):
    """A candidate whose gold can't be expressed/executed in the current algebra. Recurring
    clusters here are the discovery signal for a missing primitive."""
    rows = []
    if os.path.exists(path):
        rows = json.load(open(path))
    rows.append({"sector": q.get("sector"), "type": q.get("type"), "q": q.get("q"),
                 "gold_attempt": gold, "reject_reason": why})
    with open(path, "w") as f:
        json.dump(rows, f, indent=1)


def admit(q, gold):
    """Validate + execute the gold; admit only if it behaves as the type demands."""
    if gold is None:
        return False, "gold: no JSON"
    rep = validate(gold)
    if not rep["valid"]:
        return False, f"gold schema: {rep['errors'][:2]}"
    if q["type"] in ("AMBIGUOUS", "BEHAVIOUR") and not rep["holes"]:
        return False, "gold must have holes"
    if q["type"] == "TRANSFER" and not rep["has_estimate"]:
        return False, "gold must ESTIMATE"
    if q["type"] == "RANKING" and "RANK" not in rep["ops"]:
        # tick-008: execution-only admission let in semantically-wrong rankings (nested
        # COMPAREs / dropped cities that still "ran"). Structure is part of gold quality.
        return False, "gold must use RANK (n-ary), not nested/partial COMPARE"
    res = execute(gold)
    exp = expected_outcome(q["type"])
    ok = (res["status"] in ("answer", "data_request")) if exp == "answer_or_data_request" \
        else (res["status"] == exp)
    if not ok:
        return False, f"gold exec: {res['status']} ({res.get('reason')}) want {exp}"
    return True, res["status"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--out", required=True)
    ap.add_argument("--banks", nargs="*", default=[os.path.join("questions", "seed.json")])
    ap.add_argument("--style", default=None, help="e.g. 'indirect' — passed into the generator")
    ap.add_argument("--prefix", default="gen-live", help="stable ID prefix for this bank")
    a = ap.parse_args()
    gaps = coverage_gaps(a.banks)
    if a.style:
        gaps = [f"STYLE={a.style}: phrase ALL questions in {a.style} mode"] + gaps
    print("coverage gaps:", gaps)
    # Generators sometimes ignore the requested cardinality (Round 2 returned a much larger
    # valid array). Enforce the experiment budget mechanically before per-candidate gold calls.
    cands = generate(a.n, gaps)[:a.n]
    admitted, idx = [], 1
    for q in cands:
        if q.get("type") not in TYPES or q.get("sector") not in SECTORS:
            print(f"XX skip (bad meta): {q}")
            continue
        try:
            gold = author_gold(q)
            ok, why = admit(q, gold)
        except Exception as e:  # one bad candidate must not kill the batch (overnight loop)
            gold, ok, why = None, False, f"exception: {type(e).__name__}: {str(e)[:120]}"
        rep = validate(gold) if gold else None
        print(f"{'OK' if ok else 'XX'} [{q['sector']}/{q['type']}] {q['q'][:60]} -> {why}")
        if not ok:
            log_breaker(q, gold, why)
        if ok:
            admitted.append({
                "id": f"{a.prefix}-{idx:03d}", "sector": q["sector"], "type": q["type"],
                "q": q["q"], "expect": expected_outcome(q["type"]),
                "must_hole": q["type"] in ("AMBIGUOUS", "BEHAVIOUR") or None,
                "must_estimate": q["type"] == "TRANSFER" or None,
                "behaviour": q["type"] == "BEHAVIOUR" or None,
                "gold_ir": gold,
                "gold_shape": [o for o in rep["ops"] if o != "REGION"],
            })
            idx += 1
    admitted = [{k: v for k, v in row.items() if v is not None} for row in admitted]
    out = {"spec_version": "v2.1", "note": "neutrally generated (deepseekv4), gold validated by execution",
           "questions": admitted}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    print(f"\nadmitted {len(admitted)}/{len(cands)} -> {a.out}")


if __name__ == "__main__":
    main()
