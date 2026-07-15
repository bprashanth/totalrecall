"""Parser — English question -> IR JSON tree, via a (small) LLM.

This is the ONE step under test: can a laptop-sized model compile language to the algebra?
The prompt is the product. It carries: the op table, the question-type->tree mapping, the
hole rule, and few-shot exemplars. Few-shots are loaded from questions/fewshot.json so the
loop can improve them without touching code.

Output contract: strict JSON, one tree. We strip code fences and extract the first {...}.
Invalid JSON is a scored failure (parse_valid=false), not an exception.
"""
import json
import os
import re
from llm import chat

HERE = os.path.dirname(os.path.abspath(__file__))
FEWSHOT_PATH = os.path.join(HERE, "questions", "fewshot.json")

SYSTEM = """You translate a user's question about a PLACE into a JSON expression tree (an "IR").
You do NOT answer the question. You only emit the tree. Deterministic tools execute it.

The tree uses these operations (ops). Each node is a JSON object with an "op" field:

  SELECT    {op, entity, region, time}            get records of `entity` at `region` in `time`
  ANNOTATE  {op, source, layer}                   add a column from `layer` to records
  RELATE    {op, left, right, relation [, threshold_km]}
                                                  relate two record sets; relation: distance|within|beyond|cooccur
                                                  beyond = the COMPLEMENT (left records with NO right within range)
                                                  threshold_km: use when the question names a distance ("500 m" -> 0.5)
  AGGREGATE {op, source, by, metric}              by: space|time ; metric: count|density|mean|presence
  COMPARE   {op, left, how [, right]}             how: difference|ratio|trend_direction
                                                  (trend_direction is UNARY: no `right`)
  ESTIMATE  {op, source, target, method}          model records from ELSEWHERE onto `target`;
                                                  method: interpolate|feature|envelope  (use for TRANSFER)
  RANK      {op, items:[node,...], order, k?}     order 3+ things; order: desc|asc; items is a LIST
                                                  of subtrees, ONE PER thing being ranked
  REGION    {op:"REGION", place:"<name>"}         a place; use as a `region` or `target` value

region/time values: region is usually a REGION node. time is {"start":"YYYY","end":"YYYY"} or null.

HOW QUESTION TYPES MAP TO TREES:
  "how many / where is X here"      -> SELECT  (wrap in AGGREGATE by:space metric:count for a count)
  "X near/within Y"                 -> RELATE(SELECT X, SELECT Y, relation: within)
  "X with NO Y nearby / X not near Y / X without Y within D"
                                    -> RELATE(SELECT X, SELECT Y, relation: beyond [, threshold_km])
                                       NEVER use relation "within" for a negated constraint.
  "X near Y but not near Z"         -> RELATE(beyond, RELATE(within, SELECT X, SELECT Y), SELECT Z)
                                       (chain RELATEs for and/and-not conjunctions)
  "is X rising/falling/declining"   -> COMPARE how:trend_direction over AGGREGATE(by:time) of SELECT
  "how much did X change t1->t2"    -> COMPARE how:difference of SELECT@t2 and SELECT@t1
  "compare X in A vs B"             -> COMPARE how:difference of SELECT@A and SELECT@B
  "estimate X here from data over there / no data here" -> ESTIMATE(source=SELECT elsewhere, target=here)
  "which of A, B and C has the most/fewest X" (3+ places) -> RANK{items:[AGGREGATE(SELECT@A),
      AGGREGATE(SELECT@B), AGGREGATE(SELECT@C)], order: desc for most / asc for fewest}
      NEVER drop a place; NEVER nest COMPARE inside COMPARE for ranking — one item per place.
  "compare X in A vs B" (exactly 2)  -> COMPARE how:difference (two things = COMPARE, 3+ = RANK)

CRITICAL RULES:
1. A HOLE is a string starting with "?" (e.g. "?facility_type", "?place") and means "ASK THE USER
   because the question did not say". Use a hole ONLY when the information is genuinely MISSING.
   - If the question NAMES the entity or place, write the real value with NO "?" prefix.
     e.g. "clinics" -> "clinic"; "Kenya" -> {"op":"REGION","place":"Kenya"}.
   - Deictic place words are ALWAYS holes: "here", "around here", "this area", "this district",
     "nearby", "my town" -> region "?place". NEVER write {"op":"REGION","place":"here"} — "here"
     is not a geocodable name. Entity types with no subtype ("the facilities", "the shops")
     -> "?facility_type"/"?shop_type". Abstract topics that are not measurable entities
     ("the economy", "quality of life", "safety") -> "?indicator" (which measure? ask).
   Emitting a "?" on a value you actually know is a mistake.
   - TIME is never a hole for trend/state questions: if no period is stated, use null (= all
     available data). Never put a "?" inside {"start":...,"end":...}.
2. A question about people's motives/intent/behaviour ("why do people...", "do residents prefer...")
   cannot be measured directly: emit a SELECT on a "?proxy" entity with a "?place" hole (the tool
   will turn it into a survey request). Never fabricate a distribution for intent.
3. Copy entity phrases FROM THE QUESTION, whole: "internet use" stays "internet use" (never
   shorten to "internet"); "school enrollment" stays "school enrollment". The tools resolve
   phrases better than fragments.
4. Output ONLY the JSON tree. No prose, no markdown fences, no explanation.
"""

DEFAULT_FEWSHOT = [
    {"q": "How many clinics are in Kisumu, Kenya?",
     "ir": {"op": "AGGREGATE", "by": "space", "metric": "count",
            "source": {"op": "SELECT", "entity": "clinic",
                       "region": {"op": "REGION", "place": "Kisumu, Kenya"}, "time": None}}},
    {"q": "Is GDP per capita rising in Vietnam?",
     "ir": {"op": "COMPARE", "how": "trend_direction",
            "left": {"op": "AGGREGATE", "by": "time", "metric": "mean",
                     "source": {"op": "SELECT", "entity": "gdp per capita",
                                "region": {"op": "REGION", "place": "Vietnam"},
                                "time": {"start": "2000", "end": "2023"}}}}},
    {"q": "Which pharmacies in Nairobi are within a kilometer of a hospital?",
     "ir": {"op": "RELATE", "relation": "within",
            "left": {"op": "SELECT", "entity": "pharmacy",
                     "region": {"op": "REGION", "place": "Nairobi, Kenya"}, "time": None},
            "right": {"op": "SELECT", "entity": "hospital",
                      "region": {"op": "REGION", "place": "Nairobi, Kenya"}, "time": None}}},
    {"q": "We have no data for Kisii town — estimate pharmacy access there from nearby Kisumu.",
     "ir": {"op": "ESTIMATE", "method": "envelope",
            "target": {"op": "REGION", "place": "Kisii, Kenya"},
            "source": {"op": "SELECT", "entity": "pharmacy",
                       "region": {"op": "REGION", "place": "Kisumu, Kenya"}, "time": None}}},
    {"q": "Tell me about the health facilities here.",
     "ir": {"op": "SELECT", "entity": "?facility_type", "region": "?place", "time": None}},
    {"q": "Which city has more hotels, Vienna or Prague?",
     "ir": {"op": "COMPARE", "how": "difference",
            "left": {"op": "AGGREGATE", "by": "space", "metric": "count",
                     "source": {"op": "SELECT", "entity": "hotel",
                                "region": {"op": "REGION", "place": "Vienna, Austria"}, "time": None}},
            "right": {"op": "AGGREGATE", "by": "space", "metric": "count",
                      "source": {"op": "SELECT", "entity": "hotel",
                                 "region": {"op": "REGION", "place": "Prague, Czechia"}, "time": None}}}},
    {"q": "How many fuel stations are there around here?",
     "ir": {"op": "AGGREGATE", "by": "space", "metric": "count",
            "source": {"op": "SELECT", "entity": "fuel", "region": "?place", "time": None}}},
    {"q": "Of the schools in Windhoek, how many are within 1 km of a clinic?",
     "ir": {"op": "AGGREGATE", "by": "space", "metric": "count",
            "source": {"op": "RELATE", "relation": "within",
                       "left": {"op": "SELECT", "entity": "school",
                                "region": {"op": "REGION", "place": "Windhoek, Namibia"}, "time": None},
                       "right": {"op": "SELECT", "entity": "clinic",
                                 "region": {"op": "REGION", "place": "Windhoek, Namibia"}, "time": None}}}},
    {"q": "I just moved to Tartu and I'm hunting for a gym buddy — any fitness options close to the university campus?",
     "ir": {"op": "RELATE", "relation": "within",
            "left": {"op": "SELECT", "entity": "?amenity_type",
                     "region": {"op": "REGION", "place": "Tartu, Estonia"}, "time": None},
            "right": {"op": "SELECT", "entity": "university",
                      "region": {"op": "REGION", "place": "Tartu, Estonia"}, "time": None}}},
    {"q": "Thinking about my kids' future in Peru — people say fewer children were finishing school a decade ago; has enrollment picked up?",
     "ir": {"op": "COMPARE", "how": "trend_direction",
            "left": {"op": "AGGREGATE", "by": "time", "metric": "mean",
                     "source": {"op": "SELECT", "entity": "school enrollment",
                                "region": {"op": "REGION", "place": "Peru"},
                                "time": {"start": "2010", "end": "2023"}}}}},
    {"q": "Which hotels in Zagreb are within 1 km of a park but not within 300 meters of a bar?",
     "ir": {"op": "RELATE", "relation": "beyond", "threshold_km": 0.3,
            "left": {"op": "RELATE", "relation": "within", "threshold_km": 1.0,
                     "left": {"op": "SELECT", "entity": "hotel",
                              "region": {"op": "REGION", "place": "Zagreb, Croatia"}, "time": None},
                     "right": {"op": "SELECT", "entity": "park",
                               "region": {"op": "REGION", "place": "Zagreb, Croatia"}, "time": None}},
            "right": {"op": "SELECT", "entity": "bar",
                      "region": {"op": "REGION", "place": "Zagreb, Croatia"}, "time": None}}},
    {"q": "Which hotels in Vilnius have no restaurant within 300 meters?",
     "ir": {"op": "RELATE", "relation": "beyond", "threshold_km": 0.3,
            "left": {"op": "SELECT", "entity": "hotel",
                     "region": {"op": "REGION", "place": "Vilnius, Lithuania"}, "time": None},
            "right": {"op": "SELECT", "entity": "restaurant",
                      "region": {"op": "REGION", "place": "Vilnius, Lithuania"}, "time": None}}},
    {"q": "Of Accra, Kumasi and Tamale, which has the most marketplaces?",
     "ir": {"op": "RANK", "order": "desc", "items": [
         {"op": "AGGREGATE", "by": "space", "metric": "count",
          "source": {"op": "SELECT", "entity": "market",
                     "region": {"op": "REGION", "place": "Accra, Ghana"}, "time": None}},
         {"op": "AGGREGATE", "by": "space", "metric": "count",
          "source": {"op": "SELECT", "entity": "market",
                     "region": {"op": "REGION", "place": "Kumasi, Ghana"}, "time": None}},
         {"op": "AGGREGATE", "by": "space", "metric": "count",
          "source": {"op": "SELECT", "entity": "market",
                     "region": {"op": "REGION", "place": "Tamale, Ghana"}, "time": None}}]}},
]


def load_fewshot():
    if os.path.exists(FEWSHOT_PATH):
        with open(FEWSHOT_PATH) as f:
            return json.load(f)
    return DEFAULT_FEWSHOT


def build_messages(question, fewshot=None):
    fewshot = fewshot if fewshot is not None else load_fewshot()
    msgs = [{"role": "system", "content": SYSTEM}]
    for ex in fewshot:
        msgs.append({"role": "user", "content": ex["q"]})
        msgs.append({"role": "assistant", "content": json.dumps(ex["ir"])})
    msgs.append({"role": "user", "content": question})
    return msgs


def extract_json(text, events=None):
    if not text:
        return None
    text = text.strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    # find first balanced {...}
    start = text.find("{")
    if start < 0:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    return None
    # brace-completion: small models sometimes stop one '}' short of a valid tree (tick-011:
    # a 451-char output missing exactly one closing brace). Complete and validate mechanically.
    frag = text[start:]
    opens = frag.count("{") - frag.count("}")
    opens_sq = frag.count("[") - frag.count("]")
    if 0 < opens <= 6 and 0 <= opens_sq <= 3:
        try:
            out = json.loads(frag + "]" * opens_sq + "}" * opens)
            if events is not None:
                events.append(f"brace_completion:+{opens}}}")
            return out
        except json.JSONDecodeError:
            pass
    return None


def mech_repair(ir):
    """Deterministic peephole repairs for known small-model op-merge patterns (tick-010/011).
    AGGREGATE that grew a 'right' (+optional 'relation') absorbed a RELATE: unmerge it —
    the count-over-related-set composition is unambiguous."""
    if not isinstance(ir, dict):
        return ir
    def walk(n):
        if not isinstance(n, dict):
            return n
        if n.get("op") == "AGGREGATE" and "right" in n and "source" in n:
            n = dict(n)
            right = n.pop("right")
            relation = n.pop("relation", "within")
            n["source"] = {"op": "RELATE", "relation": relation,
                           "left": n["source"], "right": right}
        return {k: (walk(v) if isinstance(v, dict) else
                    [walk(x) for x in v] if isinstance(v, list) else v)
                for k, v in n.items()}
    return walk(ir)


def faithfulness_pass(ir, question):
    """Literal provenance (tick-014): every REGION place in the tree must be traceable to the
    question text. A small model can copy a place from a few-shot exemplar into an unrelated
    parse (observed: 'Tartu, Estonia' invented for a question naming no place). An invented
    place is worse than a hole — so demote it to '?place' and let the dialogue layer ask."""
    if not isinstance(ir, dict):
        return ir
    import unicodedata

    def fold(w):
        # diacritic-fold: the model writes "Medellin" for a question saying "Medellín" —
        # that is the SAME literal, not an invented one (tick-015 false positives)
        return "".join(c for c in unicodedata.normalize("NFKD", w.lower())
                       if not unicodedata.combining(c))
    # Split on ALL punctuation, incl. possessives/em-dashes (backported from the livelihoods
    # sector fork 2026-07-13: "France's"/"Bengaluru's" demoted a correctly copied place —
    # their tick-001 finding; bit our cross-sector A2 runs identically).
    qtok = set(re.findall(r"[a-z0-9]+", fold(question)))

    def traceable(place):
        toks = re.findall(r"[a-z0-9]+", fold(place))
        return any(t == qt or (len(t) >= 4 and qt.startswith(t)) or
                   (len(qt) >= 4 and t.startswith(qt))
                   for t in toks if len(t) > 2 for qt in qtok)

    DEICTIC = {"here", "nearby", "around here", "this area", "this district", "this city",
               "this neighborhood", "this neighbourhood", "my town", "my city", "my area"}

    def walk(n):
        if isinstance(n, list):
            return [walk(x) for x in n]
        if not isinstance(n, dict):
            return n
        if n.get("op") == "REGION" and isinstance(n.get("place"), str) \
                and not n["place"].startswith("?"):
            # deictic literals are question-traceable but NOT geocodable ("here" passed the
            # traceability check in tick-024) — always a hole
            if n["place"].lower().strip() in DEICTIC or not traceable(n["place"]):
                return "?place"
        return {k: walk(v) for k, v in n.items()}
    out = walk(ir)
    return out


def _clean_anchor(a):
    # greedy capture runs to the next punctuation; strip trailing prepositional phrases
    for sep in (" in ", " at ", " of ", " near ", " around ", " within "):
        a = a.split(sep)[0]
    return a.strip()


def _parse_dist_km(text):
    m = re.search(r"([\d.]+)\s*(m\b|meters?|metres?|km\b|kilometers?|kilometres?)", text)
    if not m:
        return None
    val = float(m.group(1))
    return val if m.group(2).startswith("k") else val / 1000.0


def proximity_anchor(question):
    """Detect a proximity constraint anchored to a NAMED entity (deictic 'nearby'/'around
    here' is NOT an anchor). Returns {anchor, negated, threshold_km} or None."""
    ql = question.lower() + " ."
    # negated: "no X within D", "without a/any X within/nearby"
    m = re.search(r"(?:have|has|with)?\s*(?:no|without a|without any)\s+([a-z][a-z ]{2,40}?)\s+"
                  r"(?:within|nearby|near|closer)", ql)
    if m:
        return {"anchor": _clean_anchor(m.group(1)), "negated": True,
                "threshold_km": _parse_dist_km(ql)}
    m = re.search(r"not\s+(?:within|near)\s+(?:[\d.a-z ]{0,20}?)(?:of|from)?\s*(?:the|a|an)\s+"
                  r"([a-z][a-z ]{2,40})[^a-z ]", ql)
    if m:
        return {"anchor": _clean_anchor(m.group(1)), "negated": True,
                "threshold_km": _parse_dist_km(ql)}
    m = re.search(r"(?:near|close to|next to|beside)\s+(?:the|a|an)\s+([a-z][a-z ]{2,40})[^a-z ]",
                  ql) or \
        re.search(r"within\s+(?:walking distance|[\d.]+\s*(?:m|km|meters?|metres?|kilometers?|minutes?))\s+"
                  r"(?:of|from)\s+(?:the|a|an)\s+([a-z][a-z ]{2,40})[^a-z ]", ql)
    if m:
        return {"anchor": _clean_anchor(m.group(1)), "negated": False,
                "threshold_km": _parse_dist_km(ql)}
    return None


def semantic_lints(ir, question):
    """Meaning-level checks the schema can't see (tick-017/021). Lints:
    1. dropped proximity constraint (anchored phrase in question, no RELATE in tree)
    2. POLARITY FLIP: question negates ("no hospital within 1km") but the tree's RELATE says
       'within' — the affirmative of a negated constraint is the exact-opposite answer set,
       the worst silent failure the probes found."""
    if not isinstance(ir, dict):
        return []
    tree = json.dumps(ir)
    pa = proximity_anchor(question)
    if not pa:
        return []
    if '"RELATE"' not in tree:
        want = "beyond" if pa["negated"] else "within"
        return [f"The question constrains results by proximity to '{pa['anchor']}' "
                f"({'NEGATED — records with NO such neighbour' if pa['negated'] else 'affirmative'}), "
                f"but your tree has no RELATE. Use relation \"{want}\"."]
    if pa["negated"] and '"beyond"' not in tree and '"within"' in tree:
        return [f"The question NEGATES the proximity ('no {pa['anchor']} within range') but the "
                f"tree uses relation \"within\" — that selects the OPPOSITE set. Use \"beyond\"."]
    return []


def mech_add_relate(ir, question):
    """Deterministic fixes for proximity lints — the fix is fully determined, no model needed:
    - no RELATE: wrap the main SELECT in RELATE(anchor, within|beyond, threshold).
    - polarity flip on a single RELATE: swap within -> beyond."""
    pa = proximity_anchor(question)
    if not pa:
        return ir
    tree = json.dumps(ir)
    rel = "beyond" if pa["negated"] else "within"

    if '"RELATE"' not in tree:
        def wrap(sel):
            node = {"op": "RELATE", "relation": rel, "left": sel,
                    "right": {"op": "SELECT", "entity": pa["anchor"],
                              "region": sel.get("region"), "time": None}}
            if pa["threshold_km"]:
                node["threshold_km"] = pa["threshold_km"]
            return node
        if ir.get("op") == "SELECT":
            return wrap(ir)
        if ir.get("op") == "AGGREGATE" and isinstance(ir.get("source"), dict) \
                and ir["source"].get("op") == "SELECT":
            out = dict(ir)
            out["source"] = wrap(ir["source"])
            return out
        return ir

    # polarity flip — only when exactly one RELATE (conjunctions are left to gold/corpus)
    if pa["negated"] and tree.count('"RELATE"') == 1 and '"within"' in tree:
        def flip(n):
            if isinstance(n, list):
                return [flip(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: flip(v) for k, v in n.items()}
            if out.get("op") == "RELATE" and out.get("relation") == "within":
                out["relation"] = "beyond"
                if pa["threshold_km"] and "threshold_km" not in out:
                    out["threshold_km"] = pa["threshold_km"]
            return out
        return flip(ir)
    return ir


MINIMAL_SYSTEM = ("Translate the user's question about a place into the JSON query tree (ops: "
                  "SELECT, ANNOTATE, RELATE, AGGREGATE, COMPARE, RANK, ESTIMATE, REGION; holes "
                  "start with '?'). Output only JSON.")


def parse(question, role="qwen2b", fewshot=None, temperature=0.0, repair=True, minimal=False):
    from ir_schema import validate  # local import to avoid cycles
    if minimal:
        msgs = [{"role": "system", "content": MINIMAL_SYSTEM},
                {"role": "user", "content": question}]
    else:
        msgs = build_messages(question, fewshot)
    # reasoning-style remote models emit reasoning tokens before the JSON; give big headroom.
    # local small models: room for wide trees (truncation at 800 broke tick-009).
    mt = 1500 if role in ("qwen2b", "loravb", "qwen2bbase", "hammer7b", "lora9b") else 8000
    events = []  # interpretability: every mechanical/LLM intervention on the raw parse is logged
    try:
        raw = chat(role, msgs, temperature=temperature, max_tokens=mt)
    except RuntimeError as e:
        return {"question": question, "raw": f"[llm-error] {e}", "ir": None, "parse_valid": False,
                "events": ["llm_error"]}
    ir = extract_json(raw, events)
    repaired = False
    before = json.dumps(ir)
    ir = mech_repair(ir)
    if json.dumps(ir) != before:
        events.append("peephole:aggregate_relate_unmerge")
    before = json.dumps(ir)
    ir = faithfulness_pass(ir, question)
    if json.dumps(ir) != before:
        events.append("provenance:invented_place_demoted_to_hole")
    # repair-with-feedback (tick-010): a schema-invalid tree gets ONE correction round with the
    # validator's exact errors — compiler-style error recovery, generic across failure patterns.
    if repair and ir is not None:
        rep = validate(ir)
        if not rep["valid"]:
            # schema errors -> one LLM correction round with the exact errors
            fix_msgs = msgs + [
                {"role": "assistant", "content": json.dumps(ir)},
                {"role": "user", "content":
                    "That tree failed validation:\n- " + "\n- ".join(rep["errors"][:4]) +
                    "\nRemember: RELATE joins two record sets; to COUNT a related set, wrap it: "
                    'AGGREGATE{source: RELATE{left, right, relation}, by:"space", metric:"count"}. '
                    "Output ONLY the corrected JSON tree."}]
            events.append("schema_errors:" + "; ".join(rep["errors"][:2]))
            try:
                raw2 = chat(role, fix_msgs, temperature=temperature, max_tokens=mt)
                ir2 = extract_json(raw2, events)
                ir2 = faithfulness_pass(mech_repair(ir2), question)
                if ir2 is not None and validate(ir2)["valid"]:
                    ir, raw, repaired = ir2, raw2, True
                    events.append("llm_repair:accepted")
                else:
                    events.append("llm_repair:rejected")
            except RuntimeError:
                events.append("llm_repair:call_failed")
        # semantic lints -> DIRECT mechanical synthesis (the fix is fully determined; asking the
        # model re-rolls the dice — tick-019: it wrapped the wrong node and used a bad anchor)
        lints = semantic_lints(ir, question)
        if lints:
            events.append("lint:" + lints[0][:90])
            ir3 = mech_add_relate(ir, question)
            if ir3 is not ir and validate(ir3)["valid"]:
                ir, repaired = ir3, True
                events.append("mech_synthesis:relate_wrap_or_polarity_flip")
    return {"question": question, "raw": raw, "ir": ir, "parse_valid": ir is not None,
            "repaired": repaired, "events": events}


if __name__ == "__main__":
    import sys
    role = sys.argv[2] if len(sys.argv) > 2 else "qwen2b"
    r = parse(sys.argv[1], role=role)
    print(json.dumps(r, indent=2, default=str))
