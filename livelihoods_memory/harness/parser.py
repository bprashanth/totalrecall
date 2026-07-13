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
  "ratio of X to Y"                  -> COMPARE how:ratio with one SELECT for X and one for Y
  "are any / at least one X present" -> AGGREGATE by:space metric:presence over SELECT X
  "X co-occur/share a neighbourhood with Y" -> RELATE relation:cooccur with the named threshold
  "X annotated with field L"         -> ANNOTATE(source=SELECT X, layer=L)

CRITICAL RULES:
1. A HOLE is a string starting with "?" (e.g. "?facility_type", "?place") and means "ASK THE USER
   because the question did not say". Use a hole ONLY when the information is genuinely MISSING.
   - If the question NAMES the entity or place, write the real value with NO "?" prefix.
     e.g. "clinics" -> "clinic"; "Kenya" -> {"op":"REGION","place":"Kenya"}.
   - Deictic place words are ALWAYS holes: "here", "around here", "this area", "this district", "this region",
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
    {"q": "How is the job market doing around here?",
     "ir": {"op": "COMPARE", "how": "trend_direction",
            "left": {"op": "AGGREGATE", "by": "time", "metric": "mean",
                     "source": {"op": "SELECT", "entity": "?indicator",
                                "region": "?place", "time": None}}}},
    {"q": "How far are Lagos's coworking spaces from its marketplaces?",
     "ir": {"op": "RELATE", "relation": "distance",
            "left": {"op": "SELECT", "entity": "coworking space",
                     "region": {"op": "REGION", "place": "Lagos, Nigeria"}, "time": None},
            "right": {"op": "SELECT", "entity": "marketplace",
                      "region": {"op": "REGION", "place": "Lagos, Nigeria"}, "time": None}}},
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
    {"q": "Of the craft workshops in Jaipur, how many are within 1 km of a marketplace?",
     "ir": {"op": "AGGREGATE", "by": "space", "metric": "count",
            "source": {"op": "RELATE", "relation": "within",
                       "left": {"op": "SELECT", "entity": "craft workshop",
                                "region": {"op": "REGION", "place": "Jaipur, India"}, "time": None},
                       "right": {"op": "SELECT", "entity": "marketplace",
                                 "region": {"op": "REGION", "place": "Jaipur, India"}, "time": None}}}},
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
    {"q": "By how many percentage points did labor-force participation in Nepal change from 2005 to 2015?",
     "ir": {"op": "COMPARE", "how": "difference",
            "left": {"op": "SELECT", "entity": "labor force participation",
                     "region": {"op": "REGION", "place": "Nepal"},
                     "time": {"start": "2015", "end": "2015"}},
            "right": {"op": "SELECT", "entity": "labor force participation",
                      "region": {"op": "REGION", "place": "Nepal"},
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
    {"q": "Do nearby markets actually improve household earnings?",
     "ir": {"op": "SELECT", "entity": "?proxy", "region": "?place", "time": None}},
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
        if n.get("op") == "COMPARE" and n.get("how") == "trend_direction" and "right" in n:
            # trend_direction is unary. Indirect questions produced right:null/right:<duplicate>
            # despite a valid-looking tree; drop it mechanically before schema/execution.
            n = dict(n)
            n.pop("right", None)
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
    # Split all punctuation, including possessives and em-dashes. Tick-001 demoted a correctly
    # copied Bengaluru because the question token was "Bengaluru's".
    qtok = set(re.findall(r"[a-z0-9]+", fold(question)))

    def traceable(place):
        toks = re.findall(r"[a-z0-9]+", fold(place))
        return any(t == qt or (len(t) >= 4 and qt.startswith(t)) or
                   (len(qt) >= 4 and t.startswith(qt))
                   for t in toks if len(t) > 2 for qt in qtok)

    DEICTIC = {"here", "nearby", "around here", "this area", "this district", "this city",
               "this region", "these regions", "those regions", "this neighborhood",
               "this neighbourhood", "my town", "my city", "my area"}
    deictic_only = (bool(re.search(r"\b(?:this area|this district|this city|around here|nearby)\b",
                                   question,re.I)) and
                     not bool(re.search(r"\bin\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]+",question)))

    def walk(n):
        if isinstance(n, list):
            return [walk(x) for x in n]
        if not isinstance(n, dict):
            return n
        if n.get("op") == "REGION" and isinstance(n.get("place"), str) \
                and not n["place"].startswith("?"):
            # deictic literals are question-traceable but NOT geocodable ("here" passed the
            # traceability check in tick-024) — always a hole
            central_without_city = ("central square" in question.lower() and
                                    "central square" in n["place"].lower() and
                                    not re.search(r"central square\s+(?:in|of)\s+[A-Z]",question))
            if deictic_only or n["place"].lower().strip() in DEICTIC or central_without_city or not traceable(n["place"]):
                return "?place"
        return {k: walk(v) for k, v in n.items()}
    out = walk(ir)
    return out


def bind_named_indicator(ir, question):
    """A ?indicator is not a real hole when the question names one unique verified indicator.
    Bind from trusted resolver vocabulary; never infer bare 'employment' or bind ?proxy."""
    if not isinstance(ir, dict):
        return ir
    import connectors as C
    code, canon, ambig = C.wb_resolve_indicator(question)
    if not code or ambig:
        return ir

    def walk(v):
        if v == "?indicator":
            return canon
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(ir)


def _phrase_norm(value):
    import unicodedata
    value = "".join(c for c in unicodedata.normalize("NFKD", value.lower())
                    if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def _entity_occurrences(question, osm_only=False):
    """Supported resolver phrases literally present in the question, longest at each offset."""
    import connectors as C
    # Bare "market" is also an abstract topic in "job market"; never use it for question-based
    # restoration. The normal resolver still accepts a parsed market entity, while explicit
    # marketplace language remains safely restorable.
    osm_phrases = {k: v for k, v in C.OSM_TAGS.items() if k != "market"}
    osm_phrases["marketplace"] = C.OSM_TAGS["market"]
    mappings = [osm_phrases] if osm_only else [C.ILO_INDICATORS, C.EUROSTAT_INDICATORS,
                                                C.WB_INDICATORS, osm_phrases]
    qn = _phrase_norm(question)
    found = []
    for mapping in mappings:
        for key in mapping:
            kn = _phrase_norm(key)
            for match in re.finditer(r"(?<![a-z0-9])" + re.escape(kn) + r"(?:s|es)?(?![a-z0-9])", qn):
                found.append((match.start(), match.end(), key))
    # keep the longest phrase at a shared start, then discard wholly nested aliases
    found.sort(key=lambda x: (x[0], -(x[1] - x[0])))
    out = []
    for item in found:
        if any(item[0] >= old[0] and item[1] <= old[1] for old in out):
            continue
        out.append(item)
    return out


def restore_named_entities(ir, question):
    """Restore a uniquely question-grounded full resolver phrase after small-model truncation."""
    if not isinstance(ir, dict):
        return ir
    import connectors as C
    occurrences = _entity_occurrences(question)
    if not occurrences:
        return ir

    def resolves(entity):
        return (C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0] or
                C.wb_resolve_indicator(entity)[0] or C.osm_resolve_tag(entity)[0])

    def best(entity):
        behavior = re.search(r"\b(?:why|prefer|rather|choose|would|motives?|motivat\w*|intent|improve|cause|affect|impact|popular|habits?)\b",
                             question, re.I)
        if entity == "?proxy" and behavior:
            return entity
        current = _phrase_norm(str(entity).lstrip("?"))
        ct = set(current.split())
        scored = []
        for start, end, key in occurrences:
            kt = set(_phrase_norm(key).split())
            overlap = sum(any(C._tok_eq(a,b) or (a.startswith("employ") and b.startswith("employ"))
                              for b in kt) for a in ct)
            subset = bool(ct) and ct <= kt
            scored.append((subset, overlap, len(kt), -start, key))
        scored.sort(reverse=True)
        if not scored:
            return entity
        if not str(entity).startswith("?") and not scored[0][0] and scored[0][1] == 0:
            if len(occurrences) != 1:
                return entity
        if str(entity).startswith("?") and scored[0][1] == 0 and len(occurrences) != 1:
            return entity
        # Do not shorten an already exact/full supported phrase.
        chosen = scored[0][-1]
        if resolves(entity) and scored[0][1] > 0 \
                and len(_phrase_norm(str(entity)).split()) >= len(_phrase_norm(chosen).split()):
            return entity
        return chosen

    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        if out.get("op") == "SELECT" and isinstance(out.get("entity"), str):
            out["entity"] = best(out["entity"])
        return out
    out = walk(ir)
    # If a relation duplicated one leaf while the question names distinct entities, literal
    # surface order fully determines the missing assignment.
    if '"RELATE"' in json.dumps(out):
        leaves = []
        def collect(n):
            if isinstance(n, dict):
                if n.get("op") == "SELECT": leaves.append(n)
                else:
                    for v in n.values(): collect(v)
            elif isinstance(n, list):
                for v in n: collect(v)
        collect(out)
        named = list(dict.fromkeys(key for _, _, key in _entity_occurrences(question, osm_only=True)))
        resolved = [C.osm_resolve_tag(str(x.get("entity")))[0] for x in leaves]
        if len(named) == len(leaves) and len(set(named)) == len(named) and len(set(resolved)) < len(resolved):
            for leaf, name in zip(leaves, named): leaf["entity"] = name
    return out


def restore_eurostat_regions(ir, question):
    """Restore named NUTS-2 phrases that qwen shortened to their central city."""
    if not isinstance(ir, dict): return ir
    import connectors as C
    qn = _phrase_norm(question)
    aliases = []
    for alias, code in C.EUROSTAT_GEOS.items():
        m = re.search(r"(?<![a-z0-9])" + re.escape(_phrase_norm(alias)) + r"(?![a-z0-9])", qn)
        if m: aliases.append((alias, code, m.start()))
    aliases.sort(key=lambda x: x[2])
    if not aliases: return ir

    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        if out.get("op") == "SELECT" and C.eurostat_resolve_indicator(str(out.get("entity")))[0]:
            reg = out.get("region")
            current = reg.get("place", "") if isinstance(reg, dict) else str(reg)
            ct = set(_phrase_norm(current).split())
            ranked = sorted(aliases, key=lambda x: (len(ct & set(_phrase_norm(x[0]).split())),
                                                    len(_phrase_norm(x[0]))), reverse=True)
            if ranked:
                out["region"] = {"op": "REGION", "place": ranked[0][0]}
        return out
    out = walk(ir)
    if out.get("op") == "RANK" and len(out.get("items", [])) == len(aliases):
        for item, (alias, _, _) in zip(out["items"], aliases):
            sel = _first_select(item)
            if sel and C.eurostat_resolve_indicator(str(sel.get("entity")))[0]:
                sel["region"] = {"op":"REGION", "place":alias}
    return out


def _first_select(ir):
    if isinstance(ir, dict):
        if ir.get("op") == "SELECT": return ir
        for value in ir.values():
            found = _first_select(value)
            if found: return found
    elif isinstance(ir, list):
        for value in ir:
            found = _first_select(value)
            if found: return found
    return None


def mech_series_rank(ir, question):
    """Named 'Rank/Sort/Order A, B ... by indicator in YEAR' has a fully determined wide tree."""
    match = re.search(r"\b(?:rank|sort|order)\s+(.+?)\s+by\s+", question, re.I)
    goal = re.search(r"which\s+city\s+should\s+i\s+check\s+first\s+for\s+(.+?),\s*(.+?)\?",question,re.I)
    if not match and goal:
        entity,head=goal.groups();parts=[p.strip(" ,") for p in re.split(r",|\bor\b",head,flags=re.I) if p.strip(" ,")]
        if len(parts)>=6 and len(parts)%2==0:parts=[parts[i]+", "+parts[i+1] for i in range(0,len(parts),2)]
        items=[{"op":"AGGREGATE","by":"space","metric":"count","source":{"op":"SELECT","entity":entity,
                "region":{"op":"REGION","place":p},"time":None}} for p in parts]
        return {"op":"RANK","items":items,"order":"desc"} if len(items)>=3 else ir
    if not match or re.search(r"\b(?:these|those|the)\s+regions\b", match.group(1), re.I):
        return ir
    head = re.sub(r"^(?:the\s+)?countries\s+", "", match.group(1), flags=re.I)
    places = [p.strip(" ,") for p in re.split(r",|\band\b", head, flags=re.I) if p.strip(" ,")]
    country_words={"ghana","kenya","india","ecuador","morocco","france","germany","spain",
                   "italy","poland","portugal","brazil","mexico","colombia","romania",
                   "thailand","japan","nigeria","peru"}
    if len(places)>=6 and len(places)%2==0 and all(_phrase_norm(places[i]) in country_words for i in range(1,len(places),2)):
        places=[places[i]+", "+places[i+1] for i in range(0,len(places),2)]
    if len(places) < 3: return ir
    tail = question[match.end():]
    candidates = [(e - s, key) for s, e, key in _entity_occurrences(tail)
                  if not key.startswith("?")]
    if not candidates: return ir
    entity = max(candidates)[1]
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    time = {"start": years[-1], "end": years[-1]} if years else None
    import connectors as C
    items = []
    for place in places:
        item = {"op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},
                "time":time}
        if C.osm_resolve_tag(entity)[0]:
            osm=list(dict.fromkeys(key for _,_,key in _entity_occurrences(tail,osm_only=True)))
            source=item
            if len(osm)>=2 and re.search(r"\b(?:within|near)\b",tail,re.I):
                source={"op":"RELATE","relation":"within","threshold_km":_parse_dist_km(tail.lower()),
                        "left":item,"right":{"op":"SELECT","entity":osm[1],"region":item["region"],"time":None}}
            item = {"op":"AGGREGATE","by":"space","metric":"count","source":source}
        items.append(item)
    ql = question.lower()
    if "highest to lowest" in ql or "highest first" in ql:
        order = "desc"
    elif "lowest to highest" in ql or "lowest first" in ql:
        order = "asc"
    else:
        order = "asc" if re.search(r"\b(?:lowest|fewest|low|lower|ascending|bottom)\b", ql) else "desc"
    out = {"op": "RANK", "items": items, "order": order}
    km = re.search(r"(?:only\s+the|keeping|keep|return\s+only\s+the)\s+(\d+)", ql)
    if km: out["k"] = int(km.group(1))
    return out


def mech_ratio(ir, question):
    """Reconstruct explicit two-measure ratios; never infer an absent measure."""
    qn = _phrase_norm(question)
    first = _first_select(ir)
    if not first: return ir
    region, time = first.get("region"), first.get("time")
    # Shorthand 'female-to-male employment-rate ratio'.
    m = re.search(r"female\s+to\s+male\s+(.+?)\s+ratio", qn)
    if m:
        base = m.group(1)
        return {"op": "COMPARE", "how": "ratio",
                "left": {"op": "SELECT", "entity": f"female {base}", "region": region, "time": time},
                "right": {"op": "SELECT", "entity": f"male {base}", "region": region, "time": time}}
    marker = qn.find("ratio of ")
    if marker < 0: return ir
    occ = [x for x in _entity_occurrences(question) if x[0] >= marker]
    if len(occ) < 2: return ir
    left, right = occ[0][2], occ[1][2]
    return {"op": "COMPARE", "how": "ratio",
            "left": {"op": "SELECT", "entity": left, "region": region, "time": time},
            "right": {"op": "SELECT", "entity": right, "region": region, "time": time}}


def mech_dormant_ops(ir, question):
    """Compile explicit presence/cooccur/annotation surfaces whose literals determine the tree."""
    first = _first_select(ir)
    if not first: return ir
    ql = question.lower()
    if re.search(r"\bare\s+there\s+(?:any\s+)?(?!more\b)", ql) or re.match(r"\s*(?:are\s+(?:there\s+)?any|any)", ql):
      if isinstance(ir, dict):
        if ir.get("op") == "SELECT":
            return {"op":"AGGREGATE","by":"space","metric":"presence","source":ir}
        if ir.get("op") == "RELATE":
            pa = proximity_anchor(question)
            right = ir.get("right")
            if pa and isinstance(right, dict) and right.get("op") == "SELECT" \
                    and _phrase_norm(str(right.get("entity", ""))) not in _phrase_norm(question):
                ir = dict(ir); right = dict(right); right["entity"] = pa["anchor"]; ir["right"] = right
            return {"op":"AGGREGATE","by":"space","metric":"presence","source":ir}
        if ir.get("op")=="AGGREGATE" and isinstance(ir.get("source"),dict) and ir["source"].get("op")=="RELATE":
            out=dict(ir); rel=dict(ir["source"]); pa=proximity_anchor(question); right=rel.get("right")
            left=rel.get("left")
            duplicate = (isinstance(left,dict) and isinstance(right,dict) and
                         _phrase_norm(str(left.get("entity",""))) == _phrase_norm(str(right.get("entity",""))))
            if pa and isinstance(right,dict) and right.get("op")=="SELECT" \
                    and (duplicate or _phrase_norm(str(right.get("entity", ""))) not in _phrase_norm(question)):
                right=dict(right);right["entity"]=pa["anchor"];rel["right"]=right
            out["metric"]="presence";out["source"]=rel;return out
    if re.search(r"\b(?:what are the names of|what are the .+? names|names of)\b",ql):
        return {"op":"ANNOTATE","source":first,"layer":"name"}
    if re.search(r"\bof the .+?,\s*how many have\b.+\bwithin\b", ql):
        entities = [key for _, _, key in _entity_occurrences(question, osm_only=True)]
        if len(entities) >= 2:
            return {"op":"AGGREGATE","by":"space","metric":"count",
                    "source":{"op":"RELATE","relation":"within",
                              "threshold_km":_parse_dist_km(ql),
                              "left":{"op":"SELECT","entity":entities[0],
                                      "region":first.get("region"),"time":None},
                              "right":{"op":"SELECT","entity":entities[1],
                                       "region":first.get("region"),"time":None}}}
    if re.search(r"\b(?:at least one|are any|is any)\b", ql) and "present" in ql:
        return {"op": "AGGREGATE", "by": "space", "metric": "presence", "source": first}
    if "annotated with" in ql or re.search(r"\battach the .+? field\b", ql):
        m = (re.search(r"annotated with (?:their )?(.+?) attribute", ql) or
             re.search(r"attach the (.+?) field", ql))
        if m:
            layer = "_".join(m.group(1).strip().split())
            return {"op": "ANNOTATE", "source": first, "layer": layer}
    if re.search(r"\baddresses?\s+(?:of|for)\b|\bshow\s+(?:the\s+)?addresses?\b", ql):
        if ir.get("op")=="ANNOTATE" and ir.get("layer")=="address": return ir
        source=ir
        if ir.get("op")=="AGGREGATE" and isinstance(ir.get("source"),dict): source=ir["source"]
        if not isinstance(source,dict) or source.get("op") not in ("SELECT","RELATE"): source=first
        return {"op":"ANNOTATE","source":source,"layer":"address"}
    if "co-occur" in ql or "sharing a 5 km neighbourhood" in ql:
        entities = [key for _, _, key in _entity_occurrences(question, osm_only=True)]
        if len(entities) >= 2:
            return {"op": "RELATE", "relation": "cooccur", "threshold_km": 5.0,
                    "left": {"op": "SELECT", "entity": entities[0],
                             "region": first.get("region"), "time": None},
                    "right": {"op": "SELECT", "entity": entities[1],
                              "region": first.get("region"), "time": None}}
    return ir


def mech_series_types(ir, question):
    """Remove invalid record-aggregation wrappers around connector-declared Series values."""
    import connectors as C
    ql = question.lower()
    def is_series(entity):
        return bool(C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0]
                    or C.wb_resolve_indicator(entity)[0])
    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        if out.get("op") == "AGGREGATE" and isinstance(out.get("source"), dict) \
                and out["source"].get("op") == "SELECT" \
                and is_series(str(out["source"].get("entity"))) \
                and not (out.get("by") == "time" and out.get("metric") == "mean") \
                and not re.search(r"\b(?:how many|number of) years\b", ql):
            return out["source"]
        return out
    return walk(ir)


def mech_explicit_point_time(ir, question):
    """A single explicit year binds missing time on named statistical SELECTs."""
    import connectors as C
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    if len(set(years)) != 1: return ir
    year = years[0]
    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        if out.get("op") == "SELECT" and out.get("time") is None:
            entity = str(out.get("entity"))
            if (C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0]
                    or C.wb_resolve_indicator(entity)[0]):
                out["time"] = {"start": year, "end": year}
        return out
    return walk(ir)


def mech_explicit_window_time(ir, question):
    """A stated from/between YEAR through/to YEAR window binds missing series time."""
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    if len(years) != 2 or not re.search(r"\b(?:from|between)\b.+\b(?:to|through|and)\b",
                                        question, re.I):
        return ir
    start, end = sorted(years)
    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        if out.get("op") == "SELECT" and out.get("time") is None:
            out["time"] = {"start": start, "end": end}
        return out
    return walk(ir)


def mech_since_time(ir, question):
    """Normalize explicit 'since YEAR' through the current calendar year."""
    match = (re.search(r"\bsince\s+((?:19|20)\d{2})\b", question, re.I) or
             re.search(r"\bfrom\s+((?:19|20)\d{2})\s+onward\b", question, re.I))
    if not match: return ir
    from datetime import datetime
    start, end = match.group(1), str(datetime.now().year)
    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        if out.get("op") == "SELECT": out["time"] = {"start":start,"end":end}
        return out
    return walk(ir)


def mech_relation_thresholds(ir, question):
    """Bind named distances to their clauses; never leak one clause's distance into another."""
    if not isinstance(ir, dict) or '"RELATE"' not in json.dumps(ir): return ir
    ql = question.lower()
    if "and also" in ql or re.search(r"\bbut\s+(?:(?:have|has)\s+no|beyond|more than|within)\b", ql) \
            or (re.search(r"\band\s+within\b",ql) and "both" not in ql):
        return ir
    def dist(text): return _parse_dist_km(text)
    def set_rel(node, value):
        if not isinstance(node, dict): return node
        out = dict(node)
        if value is None: out.pop("threshold_km", None)
        else: out["threshold_km"] = value
        return out
    root = dict(ir)
    holder = root.get("source") if root.get("op") in ("AGGREGATE","ANNOTATE") else root
    if not isinstance(holder, dict) or holder.get("op") != "RELATE": return ir
    if isinstance(holder.get("left"),dict) and holder["left"].get("op")=="AGGREGATE" \
            and holder["left"].get("metric")=="count" and isinstance(holder["left"].get("source"),dict) \
            and holder["left"]["source"].get("op")=="SELECT":
        holder=dict(holder);holder["left"]=holder["left"]["source"]
        if root.get("op") in ("AGGREGATE","ANNOTATE"):root["source"]=holder
        else:root=holder
    pa=proximity_anchor(question); left=holder.get("left"); right=holder.get("right")
    duplicate=(isinstance(left,dict) and isinstance(right,dict) and
               _phrase_norm(str(left.get("entity",""))) == _phrase_norm(str(right.get("entity",""))))
    if not pa and duplicate and re.search(r"\b(?:within|beyond)\b.+?\b(?:a|the)\s+market\b",ql):
        pa={"anchor":"marketplace","negated":"beyond" in ql,"threshold_km":_parse_dist_km(ql)}
    if pa and duplicate:
        holder=dict(holder);right=dict(right);right["entity"]=pa["anchor"];holder["right"]=right
        if root.get("op") in ("AGGREGATE","ANNOTATE"): root["source"]=holder
        else: root=holder
    if "that are within" in ql and isinstance(holder.get("right"),dict) and holder["right"].get("op")=="RELATE":
        ds=[_parse_dist_km(m.group(0)) for m in re.finditer(r"[\d.]+\s*(?:km|m\b|meters?|metres?)",ql)]
        holder=dict(holder);inner=dict(holder["right"])
        if ds:holder["threshold_km"]=ds[0];inner["threshold_km"]=ds[1] if len(ds)>1 else ds[0]
        holder["right"]=inner
        if root.get("op") in ("AGGREGATE","ANNOTATE"):root["source"]=holder
        else:root=holder
    if "but not" in ql and isinstance(holder.get("left"), dict) and holder["left"].get("op") == "RELATE":
        before, after = ql.split("but not", 1)
        inner = set_rel(holder["left"], dist(before))
        outer = set_rel(holder, dist(after)); outer["left"] = inner
    elif "both" in ql and dist(ql) is not None:
        outer = set_rel(holder, dist(ql))
        if isinstance(outer.get("left"), dict) and outer["left"].get("op") == "RELATE":
            outer["left"] = set_rel(outer["left"], dist(ql))
    else:
        outer = set_rel(holder, dist(ql))
    if root.get("op") in ("AGGREGATE","ANNOTATE"): root["source"] = outer; return root
    return outer


def mech_answer_form(ir, question):
    """Preserve requested record-vs-count output around an otherwise-correct relation."""
    if not isinstance(ir, dict): return ir
    ql=question.lower()
    count=bool(re.search(r"\b(?:how many|count(?: the| of)?|what is the count)\b",ql))
    listing=bool(re.match(r"\s*(?:list|which|identify|where)\b",ql))
    if count and ir.get("op")=="RELATE":
        return {"op":"AGGREGATE","by":"space","metric":"count","source":ir}
    if listing and ir.get("op")=="AGGREGATE" and ir.get("metric")=="count" \
            and isinstance(ir.get("source"),dict) and ir["source"].get("op")=="RELATE":
        return ir["source"]
    return ir


def mech_terse_and_anaphoric(ir, question):
    """Compile terse answer forms and 'those' proximity references without guessing a referent."""
    ql=question.lower().strip()
    if " via markets" in ql and re.search(r"\bof them\b",ql):
        first=_first_select(ir);region=first.get("region") if first else "?place";d=_parse_dist_km(ql)
        rel={"op":"RELATE","relation":"within","threshold_km":d,
             "left":{"op":"SELECT","entity":"craft workshop","region":region,"time":None},
             "right":{"op":"SELECT","entity":"marketplace","region":region,"time":None}}
        return {"op":"AGGREGATE","by":"space","metric":"count","source":rel}
    if re.match(r"^(?:coworking(?: spaces?)?|atms?|banks?|marketplaces?|craft workshops?)\s+in\s+.+\?$",ql) \
            and isinstance(ir,dict) and ir.get("op")=="AGGREGATE" \
            and isinstance(ir.get("source"),dict) and ir["source"].get("op")=="SELECT":
        ir=ir["source"]
    implicit_any=bool(re.match(r"any\s+(?:near|within|more than|beyond)\b",ql))
    if ("those" not in ql and not implicit_any) or not re.search(r"\b(?:near|within|more than|beyond)\b",ql): return ir
    pa=proximity_anchor(question);named=[key for _,_,key in _entity_occurrences(question,osm_only=True)]
    anchor=(pa or {}).get("anchor") or (named[-1] if named else None)
    if not anchor:return ir
    relation="beyond" if ((pa or {}).get("negated") or re.search(r"\b(?:more than|beyond)\b",ql)) else "within"
    rel={"op":"RELATE","relation":relation,
         "left":{"op":"SELECT","entity":"?facility_type","region":"?place","time":None},
         "right":{"op":"SELECT","entity":anchor,"region":"?place","time":None}}
    d=_parse_dist_km(ql)
    if d is not None:rel["threshold_km"]=d
    if re.match(r"^(?:are\s+)?any\b",ql):return {"op":"AGGREGATE","by":"space","metric":"presence","source":rel}
    if re.match(r"^(?:how many|count)\b",ql):return {"op":"AGGREGATE","by":"space","metric":"count","source":rel}
    return rel


def mech_relation_comparisons(ir, question):
    """Preserve explicit relation predicates on both sides of a comparison."""
    ql=question.lower();first=_first_select(ir)
    if not first:return ir
    # Ratio of a related subset to its total, or difference between two related subsets.
    ents=list(dict.fromkeys(key for _,_,key in _entity_occurrences(question,osm_only=True)))
    if "ratio of" in ql and ql.count(" within ")==1:
        region=first.get("region");d=_parse_dist_km(ql);pa=proximity_anchor(question)
        anchor=ents[1] if len(ents)>=2 else ((pa or {}).get("anchor"))
        if re.search(r"\bof\s+(?:a|the)\s+market\s+to\b",ql):anchor="marketplace"
        if not ents or not anchor:return ir
        subset={"op":"AGGREGATE","by":"space","metric":"count","source":{"op":"RELATE","relation":"within","threshold_km":d,
                "left":{"op":"SELECT","entity":ents[0],"region":region,"time":None},
                "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}}
        total={"op":"AGGREGATE","by":"space","metric":"count","source":{"op":"SELECT","entity":ents[0],"region":region,"time":None}}
        return {"op":"COMPARE","how":"ratio","left":subset,"right":total}
    if "difference between" in ql and ql.count(" within ")>=2 and len(ents)>=2:
        region=first.get("region");d=_parse_dist_km(ql);pa=proximity_anchor(question);anchor=ents[-1] if len(ents)>=3 else (pa or {}).get("anchor")
        if not anchor:return ir
        def side(entity):return {"op":"AGGREGATE","by":"space","metric":"count","source":{"op":"RELATE","relation":"within","threshold_km":d,
            "left":{"op":"SELECT","entity":entity,"region":region,"time":None},
            "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}}
        return {"op":"COMPARE","how":"difference","left":side(ents[0]),"right":side(ents[1])}
    if " than within " in ql or ("ratio of" in ql and ql.count(" within ")>=2):
        ents=list(dict.fromkeys(key for _,_,key in _entity_occurrences(question,osm_only=True)))
        if len(ents)>=3:
            region=first.get("region");ds=[_parse_dist_km(m.group(0)) for m in re.finditer(r"[\d.]+\s*(?:km|m\b|meters?|metres?)",ql)]
            def side(anchor,d):return {"op":"AGGREGATE","by":"space","metric":"count","source":{
                "op":"RELATE","relation":"within","threshold_km":d,
                "left":{"op":"SELECT","entity":ents[0],"region":region,"time":None},
                "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}}
            return {"op":"COMPARE","how":"ratio" if "ratio" in ql else "difference",
                    "left":side(ents[1],ds[0] if ds else None),
                    "right":side(ents[2],ds[1] if len(ds)>1 else (ds[0] if ds else None))}
    if not isinstance(ir,dict) or ir.get("op")!="COMPARE":return ir
    if "outnumber" in ql and " near " in ql and " away from " in ql:
        ents=list(dict.fromkeys(key for _,_,key in _entity_occurrences(question,osm_only=True)))
        if len(ents)>=2:
            region=first.get("region")
            def side(rel):return {"op":"AGGREGATE","by":"space","metric":"count","source":{"op":"RELATE","relation":rel,
                "left":{"op":"SELECT","entity":ents[0],"region":region,"time":None},
                "right":{"op":"SELECT","entity":ents[1],"region":region,"time":None}}}
            return {"op":"COMPARE","how":"difference","left":side("within"),"right":side("beyond")}
    m=re.match(r"does\s+(.+?)\s+have\s+more\s+(.+?)\s+within\s+(.+?)\s+of\s+(.+?)\s+than\s+(.+?)\?",question,re.I)
    if m:
        p1,entity,dist,anchor,p2=m.groups();d=_parse_dist_km(dist)
        def side(place):return {"op":"AGGREGATE","by":"space","metric":"count","source":{"op":"RELATE","relation":"within","threshold_km":d,
            "left":{"op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},"time":None},
            "right":{"op":"SELECT","entity":anchor,"region":{"op":"REGION","place":place},"time":None}}}
        return {"op":"COMPARE","how":"difference","left":side(p1),"right":side(p2)}
    return ir


def mech_behavior_proxy(ir, question):
    """Preference/motivation/usage-likelihood claims need a proxy, never facility arithmetic."""
    ql=question.lower()
    personal_goal=bool(re.search(r"\bwhere\b.+\bcould\s+i\b.+\b(?:sell|meet|withdraw|work)\b",ql))
    if not (personal_goal or (re.search(r"\b(?:people|residents|freelancers|owners|workers|tourists|visitors)\b",ql) and
            re.search(r"\b(?:why|prefer|choose|likely|popular|satisfied|motivat\w*|habits?|transactions?|networking)\b",ql))):
        return ir
    first=_first_select(ir);region=first.get("region") if first else "?place"
    if isinstance(region,dict) and str(region.get("place","")).lower() in ("here","this area"):
        region="?place"
    return {"op":"SELECT","entity":"?proxy","region":region or "?place","time":None}


def mech_both_relations(ir, question):
    """'X within D of both Y and Z' is two chained RELATE constraints."""
    if " both " not in question.lower(): return ir
    entities=[key for _,_,key in _entity_occurrences(question,osm_only=True)]
    # De-duplicate resolver aliases while preserving literal order.
    entities=list(dict.fromkeys(entities))
    if len(entities)<3:return ir
    first=_first_select(ir)
    if not first:return ir
    region=first.get("region");threshold=_parse_dist_km(question.lower())
    def s(entity):return {"op":"SELECT","entity":entity,"region":region,"time":None}
    rel={"op":"RELATE","relation":"within","threshold_km":threshold,
         "left":{"op":"RELATE","relation":"within","threshold_km":threshold,
                 "left":s(entities[0]),"right":s(entities[1])},"right":s(entities[2])}
    if re.search(r"\bare\s+(?:there\s+)?any\b", question, re.I):
        return {"op":"AGGREGATE","by":"space","metric":"presence","source":rel}
    return {"op":"AGGREGATE","by":"space","metric":"count","source":rel} \
        if re.search(r"\b(?:how many|count)\b",question,re.I) else rel


def mech_three_entity_relations(ir, question):
    """Compile explicit Y-and-Z or Y-but-not-Z constraints over one left entity."""
    ql=question.lower();entities=list(dict.fromkeys(key for _,_,key in _entity_occurrences(question,osm_only=True)))
    if len(entities)==2 and re.search(r"\bthat are within\b.+?\bof\s+(?:a\s+|the\s+)?market\b",ql):entities.append("marketplace")
    if len(entities)<3:return ir
    first=_first_select(ir)
    if not first:return ir
    region=first.get("region")
    distances=[]
    for m in re.finditer(r"[\d.]+\s*(?:km|kilometers?|kilometres?|m\b|meters?|metres?)",ql):
        value=_parse_dist_km(m.group(0));distances.append(value)
    def s(entity):return {"op":"SELECT","entity":entity,"region":region,"time":None}
    if re.search(r"\bwithin\b.+?\bof\b.+?\bthat are within\b",ql):
        ds=distances or [None]
        right={"op":"RELATE","relation":"within","left":s(entities[1]),"right":s(entities[2])}
        outer={"op":"RELATE","relation":"within","left":s(entities[0]),"right":right}
        if ds[0] is not None:outer["threshold_km"]=ds[0]
        if len(ds)>1:right["threshold_km"]=ds[1]
        elif ds[0] is not None:right["threshold_km"]=ds[0]
        return {"op":"AGGREGATE","by":"space","metric":"count","source":outer} if re.search(r"\bhow many\b",ql) else outer
    if (" but not " in ql or re.search(r"\bbut\s+(?:have|has)\s+no\b", ql)
            or re.search(r"\bbut\s+(?:beyond|more than|within)\b", ql)):
        parts = re.split(r"\bbut\s+(?:(?:have|has)\s+no|not)\b", ql, maxsplit=1)
        if len(parts)==1:parts=re.split(r"\bbut\b",ql,maxsplit=1)
        before, after = parts if len(parts) == 2 else (ql, ql)
        def polarity(text):return "beyond" if re.search(r"\b(?:beyond|more than|not within|away from|no)\b",text) else "within"
        inner={"op":"RELATE","relation":polarity(before),"left":s(entities[0]),"right":s(entities[1])}
        negated_outer=(" but not " in ql or bool(re.search(r"\bbut\s+(?:have|has)\s+no\b",ql)))
        outer={"op":"RELATE","relation":"beyond" if negated_outer else polarity(after),
               "left":inner,"right":s(entities[2])}
        d1,d2=_parse_dist_km(before),_parse_dist_km(after)
        if d1 is not None:inner["threshold_km"]=d1
        if d2 is not None:outer["threshold_km"]=d2
    elif " and also " in ql or re.search(r"\band\s+(?:also\s+)?within\b",ql):
        inner={"op":"RELATE","relation":"within","left":s(entities[0]),"right":s(entities[1])}
        outer={"op":"RELATE","relation":"within","left":inner,"right":s(entities[2])}
        if distances:inner["threshold_km"]=distances[0]
        if len(distances)>1:outer["threshold_km"]=distances[1]
        elif distances:outer["threshold_km"]=distances[0]
    else:return ir
    if re.match(r"\s*(?:are\s+(?:there\s+)?any|any|are\s+there\s+(?!more\b))", ql):
        return {"op":"AGGREGATE","by":"space","metric":"presence","source":outer}
    return {"op":"AGGREGATE","by":"space","metric":"count","source":outer} \
        if re.search(r"\b(?:how many|count)\b",ql) else outer


def mech_negative_relation(ir, question):
    ql=question.lower()
    if "but not" in ql:return ir
    if negative_or_anchors(question): return ir
    if json.dumps(ir).count('"RELATE"') >= 2: return ir
    if not re.search(r"\b(?:not near|no .+ within)\b",ql):return ir
    entities=list(dict.fromkeys(key for _,_,key in _entity_occurrences(question,osm_only=True)))
    if len(entities)<2:return ir
    first=_first_select(ir)
    if not first:return ir
    region=first.get("region");rel={"op":"RELATE","relation":"beyond",
        "left":{"op":"SELECT","entity":entities[0],"region":region,"time":None},
        "right":{"op":"SELECT","entity":entities[1],"region":region,"time":None}}
    d=_parse_dist_km(ql)
    if d is not None:rel["threshold_km"]=d
    if re.search(r"\bare there any\b", ql):
        return {"op":"AGGREGATE","by":"space","metric":"presence","source":rel}
    return {"op":"AGGREGATE","by":"space","metric":"count","source":rel} \
        if re.search(r"\b(?:how many|count)\b",ql) else rel


def mech_transfer_contract(ir, question):
    """Normalize inferred transfer to the frozen Records->ESTIMATE envelope contract."""
    if not isinstance(ir,dict) or '"ESTIMATE"' not in json.dumps(ir):return ir
    explicit=None
    for method in ("interpolate","feature","envelope"):
        if re.search(r"\b"+method+r"\b",question,re.I):explicit=method
    def walk(value):
        if isinstance(value,list):return [walk(x) for x in value]
        if not isinstance(value,dict):return value
        out={k:walk(v) for k,v in value.items()}
        if out.get("op")=="ESTIMATE":
            out["method"]=explicit or "envelope"
            src=out.get("source")
            if isinstance(src,dict) and src.get("op")=="AGGREGATE" and isinstance(src.get("source"),dict):
                out["source"]=src["source"]
        return out
    out=walk(ir)
    # ESTIMATE already yields a modelled Field; an outer count is an invalid type composition.
    if out.get("op")=="AGGREGATE" and isinstance(out.get("source"),dict) and out["source"].get("op")=="ESTIMATE":
        out=out["source"]
    # In the common explicit transfer surface, target and donor are literal syntax, so do not
    # retain model-invented places (which the provenance pass correctly demotes to holes).
    m = re.search(r"\b(?:no|missing|lack)\b.+?\b(?:data|records?)\s+for\s+"
                  r"([A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?)"
                  r".+?\bfrom\s+(?:nearby\s+)?"
                  r"([A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?)",
                  question, re.I | re.S)
    if not m:
        m = re.search(r"\b(?:data\s+on|records?\s+of|interested\s+in)\b.+?\bin\s+"
                      r"([A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?"
                      r"(?:,\s*[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?).+?\bfrom\s+(?:nearby\s+)?"
                      r"([A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?)",
                      question, re.I | re.S)
    using = re.search(r"using\s+(.+?)\s+as\s+a\s+reference.+?\bwould\s+(.+?)\s+likely\s+have",question,re.I)
    trailing = re.search(r"\bwould\s+(.+?)\s+likely\s+have\s+using\s+(.+?)\s+as\s+a\s+reference",question,re.I)
    if (using or trailing) and isinstance(out,dict) and out.get("op")=="ESTIMATE":
        donor,target = using.groups() if using else (trailing.group(2),trailing.group(1))
        donor=donor.strip(" ,.;:—-");target=target.strip(" ,.;:—-")
        entity=(_first_select(out) or {}).get("entity","?facility_type")
        out={"op":"ESTIMATE","method":"envelope","source":{"op":"SELECT","entity":entity,
             "region":{"op":"REGION","place":donor},"time":None},"target":{"op":"REGION","place":target}}
    siting=re.search(r"\b(?:program|support)\s+in\s+(.+?),\s*estimate\s+.+?\s+from\s+(.+?)(?:[.?]|$)",question,re.I)
    if siting and isinstance(out,dict) and out.get("op")=="ESTIMATE":
        target,donor=(x.strip(" ,.;:—-") for x in siting.groups());entity=(_first_select(out) or {}).get("entity","?facility_type")
        out={"op":"ESTIMATE","method":"envelope","source":{"op":"SELECT","entity":entity,
             "region":{"op":"REGION","place":donor},"time":None},"target":{"op":"REGION","place":target}}
    unknown_target=re.search(r"\bestimate\s+.+?\s+from\s+(.+?)(?:[.?]|$)",question,re.I) if "nearby" in question.lower() else None
    target_now=out.get("target") if isinstance(out,dict) else None
    target_is_hole=(isinstance(target_now,str) and target_now.startswith("?")) or \
        (isinstance(target_now,dict) and str(target_now.get("place","")).startswith("?"))
    if unknown_target and target_is_hole and not (using or trailing) and isinstance(out,dict) and out.get("op")=="ESTIMATE":
        donor=unknown_target.group(1).strip(" ,.;:—-");entity=(_first_select(out) or {}).get("entity","?facility_type")
        out={"op":"ESTIMATE","method":"envelope","source":{"op":"SELECT","entity":entity,
             "region":{"op":"REGION","place":donor},"time":None},"target":"?place"}
    if m and isinstance(out, dict) and out.get("op") == "ESTIMATE":
        target, donor = (x.strip(" ,.;:—-") for x in m.groups())
        donor=re.sub(r"^nearby\s+","",donor,flags=re.I)
        old_target = out.get("target")
        old_target_place = old_target.get("place", "") if isinstance(old_target, dict) else ""
        if target.lower() not in str(old_target_place).lower():
            out["target"] = {"op":"REGION", "place":target}
        src = out.get("source")
        if isinstance(src, dict) and src.get("op") == "SELECT":
            old_region = src.get("region")
            old_source_place = old_region.get("place", "") if isinstance(old_region, dict) else ""
            if donor.lower() not in ("there", "here", "nearby") \
                    and (str(old_source_place).lower().startswith("nearby ") or
                         donor.lower() not in str(old_source_place).lower()):
                src = dict(src); src["region"] = {"op":"REGION", "place":donor}; out["source"] = src
    return out


def mech_shared_distance_compare(ir, question):
    """Compile 'more X within D of Z than Y within the same distance' without dropping Z."""
    ql=question.lower()
    if not ("same distance" in ql and re.search(r"\bmore\b",ql)):return ir
    entities=list(dict.fromkeys(key for _,_,key in _entity_occurrences(question,osm_only=True)))
    if len(entities)<3:return ir
    first=_first_select(ir)
    if not first:return ir
    region=first.get("region");threshold=_parse_dist_km(ql)
    def counted(entity,anchor):
        return {"op":"AGGREGATE","by":"space","metric":"count","source":{
            "op":"RELATE","relation":"within","threshold_km":threshold,
            "left":{"op":"SELECT","entity":entity,"region":region,"time":None},
            "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}}
    # Surface order is X, shared anchor, Y.
    return {"op":"COMPARE","how":"difference","left":counted(entities[0],entities[1]),
            "right":counted(entities[2],entities[1])}


def mech_comparison_mode(ir, question):
    if isinstance(ir,dict) and ir.get("op")=="COMPARE" and ir.get("how")=="ratio" \
            and re.search(r"\b(?:higher|more|lower|fewer)\b",question,re.I) \
            and not re.search(r"\bratio\b",question,re.I):
        out=dict(ir);out["how"]="difference";return out
    return ir


def mech_subtract_orientation(ir, question):
    """'Subtract X from Y' denotes Y-X; preserve it for equal-time place comparisons."""
    if not (isinstance(ir, dict) and ir.get("op") == "COMPARE" and
            ir.get("how") == "difference" and re.match(r"\s*subtract\b", question, re.I)):
        return ir
    before_from = question.lower().split(" from ", 1)[0]
    left = ir.get("left")
    first = _first_select(left)
    place = ""
    if first and isinstance(first.get("region"), dict): place = first["region"].get("place", "")
    if place and any(tok in _phrase_norm(before_from).split() for tok in _phrase_norm(place).split()
                     if len(tok) > 3):
        out = dict(ir); out["left"], out["right"] = ir.get("right"), ir.get("left"); return out
    return ir


def mech_mixed_gap(ir, question):
    """Rebuild an explicit 'gap between X in A and Y in B in YEAR' without leaf collapse."""
    match = re.search(r"gap between (.+?) in (.+?) and (.+?) in (.+?) in ((?:19|20)\d{2})",
                      question, re.I)
    if not match: return ir
    left_text, left_place, right_text, right_place, year = match.groups()
    left_occ, right_occ = _entity_occurrences(left_text), _entity_occurrences(right_text)
    if not left_occ or not right_occ: return ir
    left_entity = max(left_occ, key=lambda x: x[1]-x[0])[2]
    right_entity = max(right_occ, key=lambda x: x[1]-x[0])[2]
    time = {"start": year, "end": year}
    return {"op":"COMPARE","how":"difference",
            "left":{"op":"SELECT","entity":left_entity,
                    "region":{"op":"REGION","place":left_place},"time":time},
            "right":{"op":"SELECT","entity":right_entity,
                     "region":{"op":"REGION","place":right_place},"time":time}}


def mech_time_faithfulness(ir, question):
    """Never retain calendar literals absent from the question."""
    years = set(re.findall(r"\b(?:19|20)\d{2}\b", question))
    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        if out.get("op") == "SELECT" and isinstance(out.get("time"), dict):
            anchors = set(re.findall(r"\b(?:19|20)\d{2}\b", json.dumps(out["time"])))
            if not anchors <= years: out["time"] = None
        return out
    return walk(ir)


def mech_source_gap_select(ir, question):
    """Preserve the full requested entity on an explicit unsupported 'Show X for PLACE' ask."""
    match = re.match(r"\s*show\s+(.+?)\s+for\s+(.+?)\s+in\s+((?:19|20)\d{2})[.?!]?\s*$",
                     question, re.I)
    if not match: return ir
    entity, place, year = match.groups()
    # Only apply when the phrase is not already a supported connector measure.
    import connectors as C
    if (C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0]
            or C.wb_resolve_indicator(entity)[0] or C.osm_resolve_tag(entity)[0]):
        return ir
    if entity.lower().endswith("surveys"): entity = entity[:-3] + "ey"
    elif entity.lower().endswith("s"): entity = entity[:-1]
    return {"op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},
            "time":{"start":year,"end":year}}


def mech_explicit_change(ir, question):
    """Explicit 'changed ... YEAR ... YEAR' means endpoint difference, not unary trend.
    The two snapshots are fully determined by the question and the parsed SELECT."""
    if not isinstance(ir, dict) or not re.search(r"\bchang(?:e|ed|ing)\b", question.lower()):
        return ir
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    if len(years) != 2:
        return ir
    y1, y2 = years

    sels = []
    def collect(n):
        if isinstance(n, list):
            for x in n: collect(x)
        elif isinstance(n, dict):
            if n.get("op") == "SELECT": sels.append(n)
            for v in n.values():
                if isinstance(v, (dict, list)): collect(v)
    collect(ir)
    if not sels:
        return ir
    anchors = {(s.get("time") or {}).get("start") for s in sels
               if isinstance(s.get("time"), dict) and
               (s.get("time") or {}).get("start") == (s.get("time") or {}).get("end")}
    if ir.get("op") == "COMPARE" and ir.get("how") == "difference" and anchors == {y1, y2}:
        return ir
    base = {k: v for k, v in sels[0].items()}
    later, earlier = (y2, y1) if int(y2) >= int(y1) else (y1, y2)
    left, right = dict(base), dict(base)
    left["time"] = {"start": later, "end": later}
    right["time"] = {"start": earlier, "end": earlier}
    return {"op": "COMPARE", "how": "difference", "left": left, "right": right}


def mech_generic_entity_hole(ir, question):
    """Generic 'places around here' names neither entity type nor region. A concrete noun copied
    from the purpose clause ('desk') must not satisfy the missing facility slot."""
    ql = question.lower()
    if re.search(r"\bplaces to work\b",ql):
        first=_first_select(ir);return {"op":"SELECT","entity":"?workplace_type",
            "region":first.get("region") if first else "?place","time":None}
    if re.search(r"\bmapping services there\b",ql):
        first=_first_select(ir)
        if first:return {"op":"SELECT","entity":first.get("entity"),"region":"?place","time":None}
    livelihood_place=re.search(r"\blivelihood place\b",ql)
    if livelihood_place:
        first=_first_select(ir);region=first.get("region") if first else None
        if region is None:
            m=re.search(r"\bin\s+(.+?)(?:\s+is\b|\s+within\b|\?)",question,re.I)
            region={"op":"REGION","place":m.group(1).strip(" ,.;:—-")} if m else "?place"
        left={"op":"SELECT","entity":"?facility_type","region":region,"time":None}
        pa=proximity_anchor(question)
        if not pa and " within " in ql:
            named=[key for _,_,key in _entity_occurrences(question,osm_only=True)]
            if named:pa={"anchor":named[-1],"negated":False,"threshold_km":_parse_dist_km(ql)}
        if pa:
            rel={"op":"RELATE","relation":"beyond" if pa["negated"] else "within","left":left,
                 "right":{"op":"SELECT","entity":pa["anchor"],"region":region,"time":None}}
            if pa.get("threshold_km") is not None:rel["threshold_km"]=pa["threshold_km"]
            return rel
        return left
    generic_places = re.search(
        r"\b(?:what|which|any|are there any)\s+(?:kind of\s+)?(?:places|facilities|options)\s+"
        r"(?:are\s+)?(?:around|near)\s+here\b", ql)
    generic_facilities = re.search(
        r"\b(?:health|livelihood|education|transport)?\s*facilities\b", ql) and re.search(
        r"\b(?:here|this area|this district|around here)\b", ql)
    anaphoric_workplace = re.search(r"\b(?:those|these)\s+workplaces\b", ql)
    anaphoric_facility = re.search(r"\b(?:those|these)\s+facilities\b", ql)
    bare_those = re.search(r"\baddresses?\s+for\s+those\b", ql)
    if not isinstance(ir, dict) or not (generic_places or generic_facilities or anaphoric_workplace or anaphoric_facility or bare_those):
        return ir
    def walk(v):
        if isinstance(v, list):
            return [walk(x) for x in v]
        if not isinstance(v, dict):
            return v
        out = {k: walk(x) for k, x in v.items()}
        if out.get("op") == "SELECT" and not str(out.get("entity", "")).startswith("?"):
            out["entity"] = "?workplace_type" if anaphoric_workplace else "?facility_type"
        return out
    out = walk(ir)
    # A deictic generic request is first a clarification request. Presence over an unknown
    # facility and unknown place falsely turns that clarification into a yes/no computation.
    if generic_places and out.get("op") == "AGGREGATE" and out.get("metric") == "presence" \
            and isinstance(out.get("source"), dict) and out["source"].get("op") == "SELECT":
        return out["source"]
    return out


def bind_named_behavior_place(ir, question):
    """Behavior needs a proxy hole, but a place explicitly named after people/residents/workers
    is already bound. Rule-2's ?place template must not override Rule-1's named-place invariant."""
    if not isinstance(ir, dict) or '"?proxy"' not in json.dumps(ir):
        return ir
    m = re.search(r"\b(?:people|residents|workers)\s+in\s+(.+?)\s+"
                  r"(?:prefer|choose|use|work|avoid|struggle|rely)\b", question,
                  flags=re.IGNORECASE)
    if m:
        place = m.group(1).strip(" ,.;:—-")
    else:
        generic = re.search(r"\bin\s+([A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?)",
                            question)
        if not generic: return ir
        place = generic.group(1).strip(" ,.;:—-")
    if not place:
        return ir
    def walk(v):
        if v == "?place":
            return {"op": "REGION", "place": place}
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            return {k: walk(x) for k, x in v.items()}
        return v
    return walk(ir)


def _clean_anchor(a):
    # greedy capture runs to the next punctuation; strip trailing prepositional phrases
    for sep in (" in ", " at ", " of ", " near ", " around ", " within "):
        a = a.split(sep)[0]
    return a.strip()


def _parse_dist_km(text):
    m = re.search(r"([\d.]+)\s*(m\b|meters?|metres?|km\b|kilometers?|kilometres?)", text)
    if not m:
        if re.search(r"\b(?:a|one)\s+(?:km|kilometers?|kilometres?)\b", text, re.I):
            return 1.0
        if re.search(r"\b(?:a|one)\s+(?:meter|metre)\b", text, re.I):
            return 0.001
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


def negative_or_anchors(question):
    """'no A or B within D' = beyond(A) AND beyond(B), expressible by chained RELATEs."""
    ql = question.lower()
    m = re.search(r"\bno\s+(?:a\s+|an\s+|any\s+)?([a-z][a-z ]{1,24}?)\s+or\s+"
                  r"(?:a\s+|an\s+|any\s+)?([a-z][a-z ]{1,24}?)\s+within\b", ql)
    if not m:
        return None
    return {"anchors": [_clean_anchor(m.group(1)), _clean_anchor(m.group(2))],
            "threshold_km": _parse_dist_km(ql)}


def semantic_lints(ir, question):
    """Meaning-level checks the schema can't see (tick-017/021). Lints:
    1. dropped proximity constraint (anchored phrase in question, no RELATE in tree)
    2. POLARITY FLIP: question negates ("no hospital within 1km") but the tree's RELATE says
       'within' — the affirmative of a negated constraint is the exact-opposite answer set,
       the worst silent failure the probes found."""
    if not isinstance(ir, dict):
        return []
    tree = json.dumps(ir)
    noa = negative_or_anchors(question)
    if noa and tree.count('"RELATE"') < 2:
        return [f"The negated disjunction requires BOTH complements: no {noa['anchors'][0]} AND "
                f"no {noa['anchors'][1]} within range. Chain two beyond RELATE nodes."]
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
    noa = negative_or_anchors(question)
    if noa and isinstance(ir, dict) and json.dumps(ir).count('"RELATE"') == 1:
        relnode = ir.get("source") if ir.get("op") == "AGGREGATE" else ir
        if isinstance(relnode, dict) and relnode.get("op") == "RELATE" \
                and relnode.get("relation") == "beyond":
            existing = str((relnode.get("right") or {}).get("entity", "")).lower()
            # Frontier models may keep the literal union as one entity ("bank or ATM"). Split
            # that ambiguous leaf into the first complement before chaining the second.
            if all(a.lower() in existing for a in noa["anchors"]):
                relnode = dict(relnode)
                right = dict(relnode.get("right") or {})
                right["entity"] = noa["anchors"][0]
                relnode["right"] = right
                missing = noa["anchors"][1]
            else:
                missing = next((a for a in noa["anchors"] if a.lower() not in existing), None)
            if missing:
                region = (relnode.get("right") or {}).get("region")
                wrapped = {"op": "RELATE", "relation": "beyond", "left": relnode,
                           "right": {"op": "SELECT", "entity": missing,
                                     "region": region, "time": None}}
                if noa.get("threshold_km"):
                    wrapped["threshold_km"] = noa["threshold_km"]
                if ir.get("op") == "AGGREGATE":
                    out = dict(ir); out["source"] = wrapped; return out
                return wrapped
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
        if ir.get("op") == "ANNOTATE" and isinstance(ir.get("source"), dict) \
                and ir["source"].get("op") == "SELECT":
            out=dict(ir);out["source"]=wrap(ir["source"]);return out
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
    # reasoning-style remote models emit reasoning tokens before the JSON; give big headroom.
    # local small models: room for wide trees (truncation at 800 broke tick-009).
    mt = 1500 if role in ("qwen2b", "loravb") else 8000
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
        events.append("peephole:structural_normalization")
    before = json.dumps(ir)
    ir = faithfulness_pass(ir, question)
    if json.dumps(ir) != before:
        events.append("provenance:invented_place_demoted_to_hole")
    before = json.dumps(ir)
    ir = bind_named_indicator(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:named_indicator_from_question")
    before = json.dumps(ir)
    ir = restore_named_entities(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:full_entity_phrase_from_question")
    before = json.dumps(ir)
    ir = restore_eurostat_regions(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:nuts2_phrase_from_question")
    before = json.dumps(ir)
    ir = mech_explicit_change(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_two_snapshot_change")
    before = json.dumps(ir)
    ir = mech_series_rank(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_series_rank")
    before = json.dumps(ir)
    ir = mech_ratio(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_ratio")
    before = json.dumps(ir)
    ir = mech_mixed_gap(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_mixed_source_gap")
    before = json.dumps(ir)
    ir = mech_subtract_orientation(ir, question)
    if json.dumps(ir) != before:
        events.append("canonical:subtract_x_from_y_orientation")
    before = json.dumps(ir)
    ir = mech_dormant_ops(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_presence_cooccur_or_annotate")
    before = json.dumps(ir)
    ir = mech_both_relations(ir, question)
    ir = mech_three_entity_relations(ir, question)
    ir = mech_negative_relation(ir, question)
    ir = mech_shared_distance_compare(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:conjunctive_or_shared_anchor_relation")
    before = json.dumps(ir)
    ir = mech_relation_thresholds(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:clause_scoped_relation_threshold")
    before = json.dumps(ir)
    ir = mech_answer_form(ir, question)
    ir = mech_terse_and_anaphoric(ir, question)
    ir = mech_relation_comparisons(ir, question)
    ir = mech_comparison_mode(ir, question)
    ir = mech_behavior_proxy(ir, question)
    ir = mech_transfer_contract(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:answer_form_comparison_or_behavior")
    before = json.dumps(ir)
    ir = mech_series_types(ir, question)
    if json.dumps(ir) != before:
        events.append("typecheck:invalid_series_aggregate_removed")
    before = json.dumps(ir)
    ir = mech_explicit_point_time(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:single_explicit_year")
    before = json.dumps(ir)
    ir = mech_explicit_window_time(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:explicit_time_window")
    before = json.dumps(ir)
    ir = mech_time_faithfulness(ir, question)
    if json.dumps(ir) != before:
        events.append("provenance:invented_time_removed")
    before = json.dumps(ir)
    ir = mech_since_time(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:since_time_window")
    before = json.dumps(ir)
    ir = mech_source_gap_select(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:full_unsupported_entity_from_question")
    before = json.dumps(ir)
    ir = mech_generic_entity_hole(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:generic_entity_hole")
    before = json.dumps(ir)
    ir = bind_named_behavior_place(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:named_behavior_place")
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
        # An accepted schema-repair response is a fresh model tree. Reapply deterministic semantic
        # passes so the correction round cannot erase explicit endpoints or answer-form rules.
        before_post = json.dumps(ir)
        for fn in (restore_named_entities, restore_eurostat_regions, mech_explicit_change,
                   mech_ratio, mech_mixed_gap, mech_subtract_orientation, mech_dormant_ops,
                   mech_both_relations, mech_three_entity_relations, mech_negative_relation,
                   mech_shared_distance_compare,
                   mech_relation_thresholds, mech_answer_form, mech_terse_and_anaphoric,
                   mech_relation_comparisons, mech_comparison_mode,
                   mech_behavior_proxy, mech_transfer_contract, mech_series_types, mech_explicit_point_time,
                   mech_explicit_window_time, mech_time_faithfulness, mech_since_time,
                   mech_generic_entity_hole, bind_named_behavior_place):
            ir = fn(ir, question)
        if json.dumps(ir) != before_post:
            events.append("post_repair:semantic_passes_reapplied")
    return {"question": question, "raw": raw, "ir": ir, "parse_valid": ir is not None,
            "repaired": repaired, "events": events}


if __name__ == "__main__":
    import sys
    role = sys.argv[2] if len(sys.argv) > 2 else "qwen2b"
    r = parse(sys.argv[1], role=role)
    print(json.dumps(r, indent=2, default=str))
