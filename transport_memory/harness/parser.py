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
    # entity swap (Round 2, tick-014): "scheduled transit stops" is this sector's 3-token
    # phrase the 2B truncated to bare "transit" — same shape as the original clinic count,
    # demonstrating whole-phrase copying exactly where it failed (place disjoint from banks)
    {"q": "How many scheduled transit stops are in Bergen, Norway?",
     "ir": {"op": "AGGREGATE", "by": "space", "metric": "count",
            "source": {"op": "SELECT", "entity": "scheduled transit stop",
                       "region": {"op": "REGION", "place": "Bergen, Norway"}, "time": None}}},
    {"q": "Is GDP per capita rising in Vietnam?",
     "ir": {"op": "COMPARE", "how": "trend_direction",
            "left": {"op": "AGGREGATE", "by": "time", "metric": "mean",
                     "source": {"op": "SELECT", "entity": "gdp per capita",
                                "region": {"op": "REGION", "place": "Vietnam"},
                                "time": {"start": "2000", "end": "2023"}}}}},
    {"q": "Which railway stations in Kigali are within a kilometer of a bus station?",
     "ir": {"op": "RELATE", "relation": "within",
            "left": {"op": "SELECT", "entity": "railway station",
                     "region": {"op": "REGION", "place": "Kigali, Rwanda"}, "time": None},
            "right": {"op": "SELECT", "entity": "bus station",
                      "region": {"op": "REGION", "place": "Kigali, Rwanda"}, "time": None}}},
    {"q": "We have no data for Kisii town — estimate pharmacy access there from nearby Kisumu.",
     "ir": {"op": "ESTIMATE", "method": "envelope",
            "target": {"op": "REGION", "place": "Kisii, Kenya"},
            "source": {"op": "SELECT", "entity": "pharmacy",
                       "region": {"op": "REGION", "place": "Kisumu, Kenya"}, "time": None}}},
    {"q": "Tell me about the stations here.",
     "ir": {"op": "SELECT", "entity": "?station_type", "region": "?place", "time": None}},
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
    {"q": "How much did air passengers carried change between 2005 and 2015 in Brazil?",
     "ir": {"op": "COMPARE", "how": "difference",
            "left": {"op": "SELECT", "entity": "air passengers carried",
                     "region": {"op": "REGION", "place": "Brazil"},
                     "time": {"start": "2015", "end": "2015"}},
            "right": {"op": "SELECT", "entity": "air passengers carried",
                      "region": {"op": "REGION", "place": "Brazil"},
                      "time": {"start": "2005", "end": "2005"}}}},
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
    {"q": "How many cafes are within 500 meters of this railway station?",
     "ir": {"op": "AGGREGATE", "by": "space", "metric": "count",
            "source": {"op": "RELATE", "relation": "within", "threshold_km": 0.5,
                       "left": {"op": "SELECT", "entity": "cafe", "region": "?place", "time": None},
                       "right": {"op": "SELECT", "entity": "railway station",
                                 "region": "?place", "time": None}}}},
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
        if n.get("op") == "ESTIMATE":
            # SELF-TRANSFER unwrap (transport tick-010): hedged indirect phrasings ("will there
            # be...", "is X enough...") seduce the 2B into wrapping a plain SELECT in ESTIMATE
            # with source region == target — a degenerate transfer (ESTIMATE means records from
            # ELSEWHERE). Unwrap to the source; deterministic and meaning-preserving.
            src, tgt = n.get("source"), n.get("target")
            src_place = (src or {}).get("region", {}).get("place") if isinstance(src, dict) \
                and isinstance(src.get("region"), dict) else None
            tgt_place = tgt.get("place") if isinstance(tgt, dict) else None
            def _np(p):
                return "".join(ch for ch in p.lower() if ch.isalnum()) if isinstance(p, str) else None
            if src_place and tgt_place and (_np(src_place) == _np(tgt_place)
                                            or _np(tgt_place) in _np(src_place)
                                            or _np(src_place) in _np(tgt_place)):
                n = src
        if n.get("op") == "SELECT":
            n = dict(n)
            # time misfiled INSIDE the REGION node (transport tick-006, gen-tran-12): hoist it
            reg = n.get("region")
            if isinstance(reg, dict) and reg.get("op") == "REGION" and "time" in reg:
                reg = dict(reg)
                t = reg.pop("time")
                n["region"] = reg
                if n.get("time") is None:
                    n["time"] = t
            # SELECT missing 'time' entirely: absent time = null = all data IS the spec default
            # (ir-spec "Time is never a hole") — fill it rather than fail schema (tick-006)
            if "time" not in n:
                n["time"] = None
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
    # split on ALL non-alphanumerics, not whitespace: "countries—Germany, France, Italy—had"
    # glued "countries—germany"/"italy—had" and DEMOTED two correctly-copied places to holes
    # (transport tick-006, gen-tran-12 — em-dash literal-provenance false positive)
    qtok = set(re.findall(r"[a-z0-9]+", fold(question)))

    def traceable(place):
        # prefix-tolerant: "India" must trace to a question saying "Indian railways", "Norway"
        # to "Norwegian" would not (different stem) — tolerance is prefix-only, len>=4 guard
        # against short-word false hits (transport tick-010, gen-tran-05 false demotion)
        toks = re.findall(r"[a-z0-9]+", fold(place))
        return any(t == qt or (len(t) >= 4 and qt.startswith(t)) or (len(qt) >= 4 and t.startswith(qt))
                   for t in toks if len(t) > 2 for qt in qtok)

    def walk(n):
        if isinstance(n, list):
            return [walk(x) for x in n]
        if not isinstance(n, dict):
            return n
        if n.get("op") == "REGION" and isinstance(n.get("place"), str) \
                and not n["place"].startswith("?") and not traceable(n["place"]):
            return "?place"
        return {k: walk(v) for k, v in n.items()}
    out = walk(ir)
    return out


def entities_faithful(ir, question):
    """Repair-acceptance guard (transport tick-001 finding): the one-round LLM repair can return
    an unrelated-but-VALID tree — it echoed the repair message's inline example with few-shot
    entities ('hotel', 'park') for a rail-lines question, and validity-only acceptance let it in.
    Guard: every non-hole SELECT entity in a REPAIRED tree must share at least one word-token
    (prefix-tolerant, diacritic-folded) with the question. Applied ONLY to repair candidates —
    first parses are already covered by the prompt's copy-phrases-whole rule + scoring."""
    if not isinstance(ir, dict):
        return False
    import unicodedata

    def fold(w):
        return "".join(c for c in unicodedata.normalize("NFKD", w.lower())
                       if not unicodedata.combining(c))
    qtok = set(re.findall(r"[a-z0-9]+", fold(question)))  # non-alnum split (em-dash bug)

    def tok_in_q(t):
        return any(t == qt or (len(t) >= 3 and qt.startswith(t)) or
                   (len(qt) >= 3 and t.startswith(qt)) for qt in qtok)

    ok = True

    def walk(n):
        nonlocal ok
        if isinstance(n, list):
            for x in n:
                walk(x)
            return
        if not isinstance(n, dict):
            return
        if n.get("op") == "SELECT":
            e = n.get("entity")
            if isinstance(e, str) and not e.startswith("?"):
                toks = [fold(t) for t in e.replace("_", " ").split() if len(t) > 2]
                if toks and not any(tok_in_q(t) for t in toks):
                    ok = False
        for v in n.values():
            if isinstance(v, (dict, list)):
                walk(v)
    walk(ir)
    return ok


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
        re.search(r"within\s+(?:walking distance|a short (?:walk|stroll|drive)|easy walking distance"
                  r"|[\d.]+\s*(?:m|km|meters?|metres?|kilometers?|minutes?))\s+"
                  r"(?:of|from)\s+(?:the|a|an)\s+([a-z][a-z ]{2,40})[^a-z ]", ql)
    if m:
        return {"anchor": _clean_anchor(m.group(1)), "negated": False,
                "threshold_km": _parse_dist_km(ql)}
    # DISTANCE anchor (Round 2, tick-014): "how far is (the nearest) X from (the) Y" — a
    # distance question, not a within/beyond filter; the tree needs RELATE relation:"distance"
    m = re.search(r"how far\s+(?:is|are)\s+(?:the\s+)?(?:nearest\s+)?[a-z][a-z ]{2,40}?\s+"
                  r"from\s+(?:the|a|an)\s+([a-z][a-z ]{2,40})[^a-z ]", ql)
    if m:
        return {"anchor": _clean_anchor(m.group(1)), "negated": False,
                "threshold_km": None, "distance": True}
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
        want = "distance" if pa.get("distance") else ("beyond" if pa["negated"] else "within")
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
    rel = "distance" if pa.get("distance") else ("beyond" if pa["negated"] else "within")

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


def parse(question, role="qwen2b", fewshot=None, temperature=0.0, repair=True):
    from ir_schema import validate  # local import to avoid cycles
    msgs = build_messages(question, fewshot)
    # reasoning-style remote models need headroom beyond the tree itself; the local 2B needs
    # room for wide trees (a two-sided COMPARE with REGION nodes truncated at 800 — tick-009)
    mt = 1500 if role == "qwen2b" else 4000
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
                if ir2 is not None and validate(ir2)["valid"] and entities_faithful(ir2, question):
                    ir, raw, repaired = ir2, raw2, True
                    events.append("llm_repair:accepted")
                elif ir2 is not None and validate(ir2)["valid"]:
                    events.append("llm_repair:rejected_unfaithful_entities")
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
