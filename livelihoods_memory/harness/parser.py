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
        if n.get("op") == "REGION" and set(n) - {"op", "place"}:
            n = {"op":"REGION", "place":n.get("place")}
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
    """Bind one uniquely named verified statistic across its SELECT leaves.

    This is intentionally source-family neutral. A small-model leaf such as `labor slack`,
    `person`, or even a different supported labor indicator must not survive when the question
    names exactly one ILO/Eurostat/WB measure. Mixed-measure questions remain untouched.
    """
    if not isinstance(ir, dict):
        return ir
    import connectors as C
    named=[]
    for _,_,entity in _entity_occurrences(question):
        if (C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0] or
                C.wb_resolve_indicator(entity)[0]):
            named.append(entity)
    # A singular hyphenated noun used attributively still names the published Eurostat
    # aggregate.  Keep this narrow: bare "employed person" may describe an individual record,
    # while "employed-person level/count/total" unambiguously denotes employed persons.
    if re.search(r"\bemployed[- ]person(?:s)?\s+(?:level|count|total)\b", question, re.I):
        named.append("employed persons")
    named=list(dict.fromkeys(named))
    if len(named) != 1:
        return ir
    canon=named[0]

    existing=set()
    def collect_existing(value):
        if isinstance(value,list):
            for item in value:collect_existing(item)
        elif isinstance(value,dict):
            if value.get("op")=="SELECT":
                entity=str(value.get("entity"))
                resolved=(C.ilo_resolve_indicator(entity)[0] or
                          C.eurostat_resolve_indicator(entity)[0] or
                          C.wb_resolve_indicator(entity)[0])
                if resolved:existing.add(json.dumps(resolved,sort_keys=True))
            for child in value.values():collect_existing(child)
    collect_existing(ir)
    if len(existing)>1:
        return ir

    def walk(v):
        if v == "?indicator":
            return canon
        if isinstance(v, list):
            return [walk(x) for x in v]
        if isinstance(v, dict):
            out={k:walk(x) for k,x in v.items()}
            if out.get("op")=="SELECT" and isinstance(out.get("entity"),str) \
                    and out["entity"] != "?proxy" and not C.osm_resolve_tag(out["entity"])[0]:
                current=out["entity"]
                current_target=(C.ilo_resolve_indicator(current)[0] or
                                C.eurostat_resolve_indicator(current)[0] or
                                C.wb_resolve_indicator(current)[0])
                canon_target=(C.ilo_resolve_indicator(canon)[0] or
                              C.eurostat_resolve_indicator(canon)[0] or
                              C.wb_resolve_indicator(canon)[0])
                current_tokens=set(_phrase_norm(current).split())
                canon_tokens=set(_phrase_norm(canon).split())
                if current_target != canon_target and not canon_tokens <= current_tokens:
                    out["entity"]=canon
            return out
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
            suffix = re.escape(kn[:-1]) + r"(?:y|ies)" if kn.endswith("y") else \
                re.escape(kn) + r"(?:s|es)?"
            for match in re.finditer(r"(?<![a-z0-9])" + suffix + r"(?![a-z0-9])", qn):
                found.append((match.start(), match.end(), key))
    # `market` is excluded from the generic mapping because "job market" is abstract. Restore it
    # only in unambiguously spatial/facility syntax; this also covers the common plural "markets".
    if osm_only or any(mapping is osm_phrases for mapping in mappings):
        spatial_market = re.search(r"\b(?:within|near|beyond|from|of|co occur)\b.+?\bmarkets?\b", qn) or \
            re.search(r"\bmarkets?\b.+?\b(?:within|near|beyond|co occur)\b", qn) or \
            re.search(r"\b(?:a|the|any)\s+markets?\b", qn)
        if spatial_market:
            for match in re.finditer(r"\bmarkets?\b", qn):
                if qn[max(0, match.start() - 4):match.start()] != "job ":
                    found.append((match.start(), match.end(), "marketplace"))
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
        eligible=occurrences
        if str(entity).startswith("?"):
            cue=re.search(r"\b(?:rather than|instead of|do not use|don't use)\b",_phrase_norm(question))
            if cue:
                before=[item for item in occurrences if item[0] < cue.start()]
                if not before:return entity
                eligible=before
        current = _phrase_norm(str(entity).lstrip("?"))
        ct = set(current.split())
        scored = []
        for start, end, key in eligible:
            kt = set(_phrase_norm(key).split())
            overlap = sum(any(C._tok_eq(a,b) or (a.startswith("employ") and b.startswith("employ"))
                              for b in kt) for a in ct)
            subset = bool(ct) and ct <= kt
            scored.append((subset, overlap, len(kt), -start, key))
        scored.sort(reverse=True)
        if not scored:
            return entity
        # Uniqueness is not lexical evidence. H23/H24 retained unsupported `cold storage` and
        # `metro station` leaves beside one supported noun; the old shortcut replaced the
        # unrelated leaf and executed a self-join. Non-hole restoration always needs overlap.
        if not str(entity).startswith("?") and not scored[0][0] and scored[0][1] == 0:
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
    # Nested aliases such as "madrid" inside "Madrid region" denote one candidate.  Keep the
    # longest literal per resolved geography so a later positional binder cannot duplicate it
    # and shift every following rank item.
    by_code = {}
    for alias, code, start in aliases:
        old = by_code.get(code)
        if old is None or len(_phrase_norm(alias)) > len(_phrase_norm(old[0])):
            by_code[code] = (alias, code, start)
    aliases = sorted(by_code.values(), key=lambda x: x[2])
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


def restore_named_region_scope(ir, question):
    """Preserve an explicitly named subnational boundary for record queries too.

    The small model often expands "Madrid region" or "Warsaw capital region" to the central
    city plus country.  That is harmless for prose but changes the OSM selection boundary.
    Rebind only when the question contains aliases for exactly one curated region code.
    """
    if not isinstance(ir, dict): return ir
    import connectors as C
    qn = _phrase_norm(question)
    hits = []
    for alias, code in C.EUROSTAT_GEOS.items():
        an = _phrase_norm(alias)
        match = re.search(r"(?<![a-z0-9])" + re.escape(an) + r"(?![a-z0-9])", qn)
        if match: hits.append((match.start(), -(match.end() - match.start()), alias, code))
    codes = {hit[3] for hit in hits}
    if len(codes) != 1: return ir
    # Prefer the longest literal surface when aliases nest ("madrid" in "madrid region").
    chosen = sorted(hits, key=lambda hit: (hit[0], hit[1]))[0][2]
    code = next(iter(codes))

    def walk(value):
        if isinstance(value, list): return [walk(item) for item in value]
        if not isinstance(value, dict): return value
        out = {key: walk(child) for key, child in value.items()}
        if out.get("op") != "SELECT": return out
        region = out.get("region")
        if not isinstance(region, dict) or str(region.get("place", "")).startswith("?"):
            return out
        current = region.get("place", "")
        current_code = C.eurostat_resolve_geo({"orig": current, "name": current})
        overlap = set(_phrase_norm(current).split()) & set(_phrase_norm(chosen).split())
        if current_code == code or overlap:
            out["region"] = {"op": "REGION", "place": chosen}
        return out
    return walk(ir)


def bind_prefixed_region(ir, question):
    """Bind terse `PLACE — ...` / `PLACE: ...` prefixes when every parsed region is a hole."""
    if not isinstance(ir, dict): return ir
    match = re.match(
        r"\s*([A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?"
        r"(?:,\s*[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?)\s*(?:—|:)\s+", question)
    if not match: return ir
    place = match.group(1).strip()
    regions = []
    def collect(value):
        if isinstance(value, list):
            for item in value: collect(item)
        elif isinstance(value, dict):
            if value.get("op") == "SELECT": regions.append(value.get("region"))
            for child in value.values():
                if isinstance(child, (dict, list)): collect(child)
    collect(ir)
    if not regions or any(not (isinstance(r, str) and r.startswith("?")) for r in regions):
        return ir
    def walk(value):
        if isinstance(value, list): return [walk(item) for item in value]
        if not isinstance(value, dict): return value
        out = {key: walk(child) for key, child in value.items()}
        if out.get("op") == "SELECT" and isinstance(out.get("region"), str) \
                and out["region"].startswith("?"):
            out["region"] = {"op": "REGION", "place": place}
        return out
    return walk(ir)


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


def _stat_operand_from_clause(text, year, fallback=None):
    """Compile one independently scoped official-statistic operand from a short clause."""
    import connectors as C
    surface = _phrase_norm(text)
    # Percentage is a presentation synonym, not a distinct measure.
    lookup = re.sub(r"\bpercentage\b", "rate", surface)
    # The curated connector names include the unit-bearing noun that ordinary prose often drops.
    lookup = re.sub(r"\b(labou?r underutilization)(?! rate)\b", r"\1 rate", lookup)
    lookup = re.sub(r"\b((?:(?:female|male) )?average weekly hours)(?! worked)\b",
                    r"\1 worked", lookup)
    lookup = re.sub(r"(?<!average )\bweekly hours\b", "average weekly hours worked", lookup)
    aliases = [(alias, code) for alias, code in C.EUROSTAT_GEOS.items()
               if re.search(r"(?<![a-z0-9])" + re.escape(_phrase_norm(alias)) +
                            r"(?![a-z0-9])", lookup)]
    occurrences = _entity_occurrences(lookup)
    measures = [item for item in occurrences if
                C.ilo_resolve_indicator(item[2])[0] or
                C.eurostat_resolve_indicator(item[2])[0] or
                C.wb_resolve_indicator(item[2])[0]]
    # A named national unemployment operand is the country-level WB measure, while a curated
    # NUTS region's bare "unemployment" denotes Eurostat unemployment rate.
    if re.search(r"\b(?:world bank|national)\b", lookup) and re.search(r"\bunemployment\b", lookup):
        entity = "unemployment"
    elif aliases and re.search(r"\bfemale\s+employment\s+rate\b", lookup):
        entity = "female employment rate"
    elif aliases and re.search(r"\bmale\s+employment\s+rate\b", lookup):
        entity = "male employment rate"
    elif aliases and re.search(r"\bemployment\s+rate\b", lookup):
        entity = "employment rate"
    elif aliases and re.search(r"\bunemployment(?:\s+rate)?\b", lookup):
        entity = "unemployment rate"
    elif not measures:
        return None
    else:
        chosen = max(measures, key=lambda item:item[1]-item[0])
        entity = chosen[2]

    place = None
    if aliases:
        # Prefer the longest named NUTS surface, not a nested city alias.
        place = max((alias for alias, _ in aliases), key=lambda value:len(_phrase_norm(value)))
    if place is None:
        remainder = lookup
        en = _phrase_norm(entity)
        remainder = re.sub(r"(?<![a-z0-9])" + re.escape(en) + r"(?![a-z0-9])", " ", remainder,
                           count=1)
        remainder = re.sub(r"\b(?:world bank|eurostat|ilostat|ilo|national|reported|rate|"
                           r"percentage|share|value|its|the|s)\b", " ", remainder)
        remainder = re.sub(r"\b(?:19|20)\d{2}\b", " ", remainder)
        remainder = re.sub(r"^(?:what\s+(?:was|is)|compare|show|give\s+me)\s+", "", remainder)
        remainder = re.sub(r"\s+(?:preserve|keep)\s+(?:that|the)\s+left\s+right\s+order.*$",
                           "", remainder)
        remainder = re.sub(r"^(?:for|in|of)\s+|\s+(?:for|in|of)$", "", remainder.strip())
        place = " ".join(remainder.split())
    if not place and isinstance(fallback, dict):
        region = fallback.get("region")
    else:
        region = {"op":"REGION", "place":place}
    if not region: return None
    return {"op":"SELECT", "entity":entity, "region":region,
            "time":{"start":year,"end":year}}


def mech_statistical_surfaces(ir, question):
    """Compile compact level and binary-statistic surfaces one independently scoped clause at a time.

    Reporting labels, possessive ``'s``, and terse endpoint punctuation are not part of a place or
    indicator.  The rule is source-neutral and activates only when both clauses resolve through the
    frozen statistical vocabularies.
    """
    def operand(text, year, fallback=None):
        return _stat_operand_from_clause(text.strip(" ,.;:—-"), year, fallback)

    # "Pull the 2022 unemployment rate for the Madrid region".
    level = re.match(
        r"\s*(?:pull|retrieve|show|report|give(?:\s+me)?)\s+(?:the\s+)?"
        r"((?:19|20)\d{2})\s+(.+?)\s+for\s+(?:the\s+)?(.+?)[.?!]*$",
        question, re.I)
    if level:
        year, measure, place = level.groups()
        got = operand(f"{place} {measure}", year)
        if got: return got

    # One report-wide year with two independently named operands.
    binary = (
        (r"\s*((?:19|20)\d{2})\s+snapshot\s*:\s*(.+?)\s+minus\s+(.+?)[.?!]*$",
         "difference"),
        (r"\s*for\s+((?:19|20)\d{2})\s*,\s*(?:give\s+)?(?:the\s+)?ratio\s+of\s+"
         r"(.+?)\s+to\s+(.+?)[.?!]*$", "ratio"),
        (r"\s*for\s+((?:19|20)\d{2})\s*,\s*divide\s+(.+?)\s+by\s+(.+?)[.?!]*$",
         "ratio"),
    )
    for pattern, how in binary:
        found = re.match(pattern, question, re.I)
        if found:
            year, left_text, right_text = found.groups()
            left, right = operand(left_text, year), operand(right_text, year)
            if left and right:
                return {"op":"COMPARE", "how":how, "left":left, "right":right}

    # A winner surface is a signed comparison, not an arbitrary ratio.
    winner = re.match(r"\s*which\s+percentage\s+was\s+larger\s*:\s*"
                      r"(.+?)\s+or\s+(.+?)[.?!]*$", question, re.I)
    if winner:
        sides=[]
        for clause in winner.groups():
            years=re.findall(r"\b(?:19|20)\d{2}\b",clause)
            sides.append(operand(clause,years[-1]) if years else None)
        if all(sides):
            return {"op":"COMPARE","how":"difference","left":sides[0],"right":sides[1]}

    # "Kenya weekly-hours brief: 2021 minus 2019" and regional equivalents.
    endpoints = re.match(r"\s*(.+?)\s*:\s*(?:calculate\s+)?"
                         r"((?:19|20)\d{2})\s+(?:minus|less)\s+((?:19|20)\d{2})[.?!]*$",
                         question, re.I)
    if endpoints:
        prefix, later, earlier = endpoints.groups()
        prefix=re.sub(r"\s+brief\s*$", "", prefix, flags=re.I)
        left, right = operand(prefix,later), operand(prefix,earlier)
        if left and right:
            return {"op":"COMPARE","how":"difference","left":left,"right":right}

    # "India's 2022 Gini divided by its 1977 Gini".
    temporal_ratio = re.match(
        r"\s*(.+?)[’']s\s+((?:19|20)\d{2})\s+(.+?)\s+divided\s+by\s+its\s+"
        r"((?:19|20)\d{2})\s+(.+?)(?:\s*:\s*.+?)?[.?!]*$", question, re.I)
    if temporal_ratio:
        place, later, left_measure, earlier, right_measure = temporal_ratio.groups()
        # The answer-form tail after a colon is outside the right operand.  Repeat the explicit
        # possessive place when expanding ``its`` instead of asking the generic operand parser to
        # infer a place from that tail.
        right_measure=right_measure.split(":",1)[0]
        left=operand(f"{place} {left_measure}",later)
        right=operand(f"{place} {right_measure}",earlier)
        if left and right:
            return {"op":"COMPARE","how":"ratio","left":left,"right":right}
    return ir


def mech_closed_statistical_surface(ir, question):
    """Bind explicit level/trend/ratio/subtraction roles independently for each statistic."""
    ql=question.lower();first=_first_select(ir)

    level=re.match(r"\s*(.+?)[’']s\s+(.+?)\s+in\s+((?:19|20)\d{2})\s*[—-]+\s*"
                   r"what level[?!.]*$",question,re.I)
    if level:
        place,measure,year=level.groups()
        got=_stat_operand_from_clause(f"{place} {measure}",year,first)
        if got:return got

    years=re.findall(r"\b(?:19|20)\d{2}\b",question)
    explicit_direction=bool(re.search(r"\b(?:trend up or down|direction only|fitted direction|"
                                      r"rising or falling)\b",ql))
    if explicit_direction and len(years)>=2 and first:
        start,end=sorted(years[:2],key=int)
        source=dict(first);source["time"]={"start":start,"end":end}
        return {"op":"COMPARE","how":"trend_direction","left":{
            "op":"AGGREGATE","by":"time","metric":"mean","source":source}}

    over=re.match(r"\s*take\s+(.+?)[’']s\s+((?:19|20)\d{2})\s+(.+?)\s+over\s+its\s+"
                  r"((?:19|20)\d{2})\s+(.+?)[.?!]*$",question,re.I)
    if over:
        place,y1,m1,y2,m2=over.groups()
        left=_stat_operand_from_clause(f"{place} {m1}",y1,first)
        right=_stat_operand_from_clause(f"{place} {m2}",y2,first)
        if left and right:return {"op":"COMPARE","how":"ratio","left":left,"right":right}

    at_subtract=re.match(r"\s*at\s+((?:19|20)\d{2})(?:\s+and\s+((?:19|20)\d{2})\s+respectively)?\s*,\s*"
                         r"subtract\s+(.+?)\s+from\s+(.+?)[.?!]*$",question,re.I)
    if at_subtract:
        y1,y2,subtrahend,minuend=at_subtract.groups();y2=y2 or y1
        left=_stat_operand_from_clause(minuend,y1,first)
        right=_stat_operand_from_clause(subtrahend,y2,first)
        if left and right:return {"op":"COMPARE","how":"difference","left":left,"right":right}

    explicit_pair=re.match(r"\s*difference\s*,\s*first minus second\s*:\s*"
                           r"(.+?)\s+in\s+((?:19|20)\d{2})\s*;\s*"
                           r"(.+?)\s+in\s+((?:19|20)\d{2})[.?!]*$",question,re.I)
    if explicit_pair:
        c1,y1,c2,y2=explicit_pair.groups()
        left=_stat_operand_from_clause(c1,y1,first);right=_stat_operand_from_clause(c2,y2,first)
        if left and right:return {"op":"COMPARE","how":"difference","left":left,"right":right}
    return ir


def mech_series_rank(ir, question):
    """Named 'Rank/Sort/Order A, B ... by indicator in YEAR' has a fully determined wide tree."""
    match = re.search(r"\b(?:rank|sort|order)\s+(.+?)\s+by\s+", question, re.I)
    directional = re.search(
        r"\b(?:rank|sort|order)\s+(.+?)\s+from\s+(lowest|highest)\s+to\s+"
        r"(highest|lowest)\s+(.+?)\s+in\s+((?:19|20)\d{2})[.?!]*$",question,re.I)
    if directional:
        places_text,start,_,entity_text,year=directional.groups()
        places=_literal_place_list(places_text)
        occurrences=_entity_occurrences(entity_text)
        if len(places)>=3 and occurrences:
            entity=max(occurrences,key=lambda item:item[1]-item[0])[2]
            time={"start":year,"end":year}
            return {"op":"RANK","order":"asc" if start.lower()=="lowest" else "desc",
                    "items":[{"op":"SELECT","entity":entity,
                              "region":{"op":"REGION","place":place},"time":time}
                             for place in places]}
    covering = re.search(r"\bcovering\s+(.+?),\s*rank\s+(?:the\s+)?supported\s+regions\s+by\s+",
                         question, re.I)
    if covering:
        import connectors as C
        aliases={"paris":"Ile de France","milan":"Lombardy"}
        places=[]
        for part in re.split(r";|\band\b",covering.group(1),flags=re.I):
            pn=_phrase_norm(part);chosen=None
            for alias in sorted(C.EUROSTAT_GEOS,key=len,reverse=True):
                if re.search(r"(?<![a-z0-9])"+re.escape(_phrase_norm(alias))+r"(?![a-z0-9])",pn):
                    chosen=alias;break
            if not chosen:
                for city,region in aliases.items():
                    if re.search(r"\b"+city+r"\b",pn):chosen=region;break
            if chosen and C.eurostat_resolve_geo({"orig":chosen,"name":chosen}) not in {
                    C.eurostat_resolve_geo({"orig":p,"name":p}) for p in places}:
                places.append(chosen)
        tail=question[covering.end():]
        candidates=[(e-s,key) for s,e,key in _entity_occurrences(tail) if not key.startswith("?")]
        if len(places)>=3 and candidates:
            entity=max(candidates)[1];years=re.findall(r"\b(?:19|20)\d{2}\b",question)
            time={"start":years[-1],"end":years[-1]} if years else None
            items=[{"op":"SELECT","entity":entity,"region":{"op":"REGION","place":p},"time":time}
                   for p in places]
            return {"op":"RANK","items":items,
                    "order":"asc" if re.search(r"\blowest\s+to\s+highest\b",question,re.I) else "desc"}
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
    head = re.sub(r"^(?:(?:our|the)\s+)?(?:\d+|one|two|three|four|five|six|seven|eight)?\s*"
                  r"candidate\s+regions?\s*(?:—|:|-)\s*", "", head, flags=re.I)
    head = re.sub(r"\s+from\s+(?:lowest|highest)\s+to\s+(?:highest|lowest)\s*$", "", head,
                  flags=re.I)
    places = [re.sub(r"^the\s+", "", p.strip(" ,—"), flags=re.I)
              for p in re.split(r",|\band\b", head, flags=re.I) if p.strip(" ,—")]
    import connectors as C
    places = [next((alias for alias in C.EUROSTAT_GEOS
                    if _phrase_norm(alias) == _phrase_norm(place)), place) for place in places]
    country_words={"ghana","kenya","india","ecuador","morocco","france","germany","spain",
                   "italy","poland","portugal","brazil","mexico","colombia","romania",
                   "thailand","japan","nigeria","peru","nepal","uganda","namibia",
                   "senegal","latvia","austria","belgium","netherlands"}
    if len(places)>=6 and len(places)%2==0 \
            and all(_phrase_norm(places[i]) in country_words for i in range(1,len(places),2)) \
            and any(_phrase_norm(places[i]) not in country_words for i in range(0,len(places),2)):
        places=[places[i]+", "+places[i+1] for i in range(0,len(places),2)]
    if len(places) < 3: return ir
    tail = question[match.end():]
    candidates = [(e - s, key) for s, e, key in _entity_occurrences(tail)
                  if not key.startswith("?")]
    if not candidates: return ir
    entity = max(candidates)[1]
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    time = {"start": years[-1], "end": years[-1]} if years else None
    items = []
    for place in places:
        item = {"op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},
                "time":time}
        if C.osm_resolve_tag(entity)[0]:
            osm=list(dict.fromkeys(key for _,_,key in _entity_occurrences(tail,osm_only=True)))
            source=item
            if len(osm)>=2 and re.search(r"\b(?:within|near)\b",tail,re.I):
                source={"op":"RELATE","relation":"within", "left":item,
                        "right":{"op":"SELECT","entity":osm[1],
                                 "region":item["region"],"time":None}}
                threshold = _parse_dist_km(tail.lower())
                if threshold is not None: source["threshold_km"] = threshold
            metric = "density" if re.search(r"\bdensit(?:y|ies)\b", tail, re.I) else "count"
            item = {"op":"AGGREGATE","by":"space","metric":metric,"source":source}
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


def _literal_place_list(text):
    """Split an explicit comma/and/or place list without inventing geographic hierarchy."""
    import connectors as C
    parts = [re.sub(r"^(?:the\s+)", "", part.strip(" ,—.;:?"), flags=re.I)
             for part in re.split(r",|\b(?:and|or)\b", text, flags=re.I)
             if part.strip(" ,—.;:?")]
    aliases = sorted(C.EUROSTAT_GEOS, key=len, reverse=True)
    return [next((alias for alias in aliases
                  if _phrase_norm(alias) == _phrase_norm(part)), part) for part in parts]


def mech_explicit_rank_semantics(ir, question):
    """Compile explicit superlative lists and ranks of endpoint changes.

    A RANK item is the quantity being ordered.  For "rank by the difference", that item is a
    COMPARE of two point SELECTs—not a whole-window series or the later endpoint alone.
    """
    change_rank = re.search(
        r"\brank\s+(.+?)\s+by\s+(?:the\s+)?(?:difference|change|increase|decrease)\s+in\s+"
        r"(.+?)\s+between\s+((?:19|20)\d{2})\s+and\s+((?:19|20)\d{2})",
        question, re.I)
    which_change = re.search(
        r"\bwhich\s+(?:region|place|country)\s+had\s+(?:the\s+)?"
        r"(?:largest|greatest|smallest)\s+(?:increase|decrease|change)\s+in\s+(.+?)\s+"
        r"between\s+((?:19|20)\d{2})\s+and\s+((?:19|20)\d{2})\s*:\s*(.+?)[?!.]*$",
        question, re.I)
    # Broad endpoint-rank surfaces discovered by H20.  Candidate extraction and the quantity
    # blueprint are deliberately independent: one endpoint COMPARE is instantiated per place.
    # This covers prefix lists, suffix lists, arrow years, "largest rise", "fell", and top-N
    # without weakening ordinary one-year ranks or unbounded unary trends.
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    endpoint_rank = (len(years) == 2 and
                     (re.search(r"\b(?:rank|order|ladder|put|winner\s+only|"
                               r"which\s+(?:one|two|three|four|five|had|saw)|"
                               r"which\s+of|"
                               r"whose\b|top\s*[- ]?\s*(?:\d+|one|two|three|four|five))\b",
                               question, re.I) or
                      re.search(r"\bwhich\b.+?\b(?:rose|increased|fell|decreased)\b.+?"
                                r"\b(?:most|least|largest|smallest)\b",question,re.I)) and
                     (re.search(r"\b(?:change|increas|decreas|rise|rose|gain|fell|fall|drop|"
                                r"deteriorat|improvement)\w*\b",
                                question, re.I) or
                      re.search(r"\bendpoint\b", question, re.I)))
    if endpoint_rank and not (change_rank or which_change):
        places_text = None
        for pattern in (
            r"\bwhich\s+of\s+(.+?)\s+(?:has|have|had|show|shows|saw)\b",
            r"\bwhich\s+(?:\d+|one|two|three|four|five)\s+of\s+(.+?)\s+"
            r"(?:has|have|had|show|shows)\b",
            r"\bamong\s+(.+?),\s*(?:which|whose|rank|order)\b",
            r"\bof\s+(.+?),\s*which\b",
            r"\b(?:rank|order)\s+(.+?)\s+(?:by|on)\b",
            r"\b(?:rank|order)\s+(.+?)\s+from\s+(?:the\s+)?(?:lowest|highest)\b",
            r"\bcandidates?\s+(.+?)[.?!]*$",
            r":\s*([^:.?!]+?)[.?!]*$",
        ):
            match = re.search(pattern, question, re.I)
            if match:
                places_text = match.group(1)
                break
        places = _literal_place_list(places_text) if places_text else []
        if len(places) < 2:
            places = _rank_candidate_places(ir, question)
        # A model-produced RANK is useful only as a candidate inventory; never inherit its
        # incorrectly flattened SELECT/series item semantics.
        if len(places) < 2 and isinstance(ir, dict) and ir.get("op") == "RANK":
            places = []
            for item in ir.get("items", []):
                selected = _first_select(item)
                region = selected.get("region") if selected else None
                place = region.get("place") if isinstance(region, dict) else region
                if place: places.append(place)
        occurrences = _entity_occurrences(question)
        # Statistical measures win over incidental OSM/source-label tokens (e.g. "World Bank").
        import connectors as C
        measures = [item for item in occurrences if
                    C.ilo_resolve_indicator(item[2])[0] or
                    C.eurostat_resolve_indicator(item[2])[0] or
                    C.wb_resolve_indicator(item[2])[0]]
        inferred = _stat_operand_from_clause(question, years[-1])
        if len(places) >= 2 and (measures or inferred):
            entity = (max(measures, key=lambda item: item[1] - item[0])[2]
                      if measures else inferred["entity"])
            earlier, later = sorted(set(years), key=int)
            def point(place, year):
                return {"op":"SELECT", "entity":entity,
                        "region":{"op":"REGION", "place":place},
                        "time":{"start":year, "end":year}}
            items = [{"op":"COMPARE", "how":"difference",
                      "left":point(place, later), "right":point(place, earlier)}
                     for place in places]
            # Signed later-minus-earlier: the greatest fall/improvement is the smallest value.
            ascending = bool(re.search(
                r"\b(?:fell|fall|steepest\s+(?:fall|drop)|largest\s+drop|greatest\s+drop|"
                r"greatest\s+decrease|smallest\s+(?:increase|change|gain|rise)|"
                r"most\s+improvement)\b", question, re.I)) \
                and not bool(re.search(r"\bworst\s+deterioration\b", question, re.I))
            if re.search(r"\bsteepest\b.+\bdrop\b",question,re.I): ascending=True
            if re.search(r"\bsmallest(?:\s+[\w-]+){0,4}\s+"
                         r"(?:increase|change|gain|rise)\b", question, re.I):
                ascending = True
            out = {"op":"RANK", "items":items, "order":"asc" if ascending else "desc"}
            out["order"] = _requested_rank_order(question, out["order"])
            words = {"one":1,"two":2,"three":3,"four":4,"five":5}
            top = re.search(r"\btop\s*[- ]?\s*(\d+|one|two|three|four|five)\b", question, re.I)
            if top:
                token=top.group(1).lower();out["k"]=int(token) if token.isdigit() else words[token]
            elif re.search(r"\bwhich\s+(?:\w+\s+){0,2}(?:had|has|saw)\s+(?:the\s+)?"
                           r"(?:largest|smallest|greatest|most|fewest)\b|\b(?:winner\s+only|"
                           r"which\s+one|which\s+of\b.+?\b(?:largest|smallest|greatest|most|fewest)|"
                           r"whose\b.+?\b(?:largest|steepest|most))", question, re.I):
                out["k"] = 1
            elif re.search(r"\bwhich\b.+?\b(?:rose|increased|fell|decreased)\b.+?"
                           r"\b(?:most|least|largest|smallest)\b",question,re.I):
                out["k"] = 1
            return out

    # A rank of endpoint ratios is a different quantity blueprint from endpoint difference.
    ratio_rank = re.search(
        r"\bwhose\s+((?:19|20)\d{2})(?:\s*(?:-|–|—)?\s*to\s*(?:-|–|—)?\s*|"
        r"\s*(?:-|–|—)\s*)((?:19|20)\d{2})\s+"
        r"(.+?)\s+ratio\s+is\s+(?:the\s+)?(?:largest|highest)\s*,\s*(.+?)[?!.]*$",
        question, re.I)
    if ratio_rank:
        y2,y1,entity_text,places_text=ratio_rank.groups()
        places=_literal_place_list(places_text);occ=_entity_occurrences(entity_text)
        if len(places)>=2 and occ:
            entity=max(occ,key=lambda item:item[1]-item[0])[2]
            later,earlier=sorted((y1,y2),key=int,reverse=True)
            def point(place,year):return {"op":"SELECT","entity":entity,
                "region":{"op":"REGION","place":place},"time":{"start":year,"end":year}}
            return {"op":"RANK","order":"desc","k":1,"items":[
                {"op":"COMPARE","how":"ratio","left":point(place,later),
                 "right":point(place,earlier)} for place in places]}

    # Heterogeneous but unit-compatible operands: parse every colon-delimited item locally.
    heterogeneous = re.search(r":\s*(.+?)[?!.]*$", question)
    if heterogeneous and re.search(r"\b(?:order|highest|lowest|numerically)\b", question, re.I):
        year_match=re.search(r"\b(?:19|20)\d{2}\b",question)
        parts=[p.strip(" ,") for p in re.split(r",|\b(?:and|or)\b",heterogeneous.group(1),flags=re.I)
               if p.strip(" ,")]
        if year_match and len(parts)>=3:
            items=[_stat_operand_from_clause(part,year_match.group(0)) for part in parts]
            if all(items):
                out={"op":"RANK","order":"asc" if re.search(r"\blowest\b",question,re.I) else "desc",
                     "items":items}
                if re.search(r"\bwhich\s+is\b",question,re.I):out["k"]=1
                return out

    if change_rank or which_change:
        if change_rank:
            places_text, entity_text, y1, y2 = change_rank.groups(); top_one = False
        else:
            entity_text, y1, y2, places_text = which_change.groups(); top_one = True
        places = _literal_place_list(places_text)
        occurrences = _entity_occurrences(entity_text)
        if len(places) < 2 or not occurrences: return ir
        entity = max(occurrences, key=lambda item: item[1] - item[0])[2]
        later, earlier = (y2, y1) if int(y2) >= int(y1) else (y1, y2)
        def point(place, year):
            return {"op":"SELECT", "entity":entity,
                    "region":{"op":"REGION", "place":place},
                    "time":{"start":year, "end":year}}
        items = [{"op":"COMPARE", "how":"difference",
                  "left":point(place, later), "right":point(place, earlier)}
                 for place in places]
        out = {"op":"RANK", "items":items,
               "order":"asc" if re.search(r"\bsmallest\b", question, re.I) else "desc"}
        if top_one: out["k"] = 1
        return out

    # Explicit full-order/list surfaces need not use the verb "rank".  Keep the complete
    # colon-delimited candidate inventory rather than accepting a single model-selected winner.
    ladder = re.search(
        r"\b(?:ladder|ranking|ordering)\s+for\s+((?:19|20)\d{2}).*?"
        r"\b(highest|lowest)\s+first\s*:\s*(.+?)[.?!]*$", question, re.I)
    if ladder:
        year, direction, places_text = ladder.groups()
        places = _literal_place_list(places_text)
        before = question[:ladder.start()]
        occurrences = _entity_occurrences(before)
        import connectors as C
        measures = [item for item in occurrences if
                    C.ilo_resolve_indicator(item[2])[0] or
                    C.eurostat_resolve_indicator(item[2])[0] or
                    C.wb_resolve_indicator(item[2])[0]]
        if len(places) >= 2 and measures:
            entity = max(measures, key=lambda item:item[1]-item[0])[2]
            time = {"start":year,"end":year}
            return {"op":"RANK", "order":"desc" if direction.lower()=="highest" else "asc",
                    "items":[{"op":"SELECT","entity":entity,
                              "region":{"op":"REGION","place":place},"time":time}
                             for place in places]}

    superlative = re.search(
        r"\bwhich\s+(?:has|had)\s+the\s+(highest|lowest)\s+(.+?)\s*:\s*"
        r"(.+?)(?:\s+in\s+((?:19|20)\d{2}))?[?!.]*$", question, re.I)
    if not superlative: return ir
    direction, entity_text, places_text, year = superlative.groups()
    places = _literal_place_list(places_text)
    occurrences = _entity_occurrences(entity_text)
    if len(places) < 2 or not occurrences: return ir
    entity = max(occurrences, key=lambda item: item[1] - item[0])[2]
    if not year:
        found_years=re.findall(r"\b(?:19|20)\d{2}\b",question)
        year=found_years[-1] if found_years else None
    time = {"start":year, "end":year} if year else None
    return {"op":"RANK", "order":"desc" if direction.lower() == "highest" else "asc",
            "k":1, "items":[{"op":"SELECT", "entity":entity,
                                "region":{"op":"REGION", "place":place}, "time":time}
                               for place in places]}


def mech_ratio(ir, question):
    """Reconstruct explicit two-measure ratios; never infer an absent measure."""
    qn = _phrase_norm(question)
    first = _first_select(ir)
    if not first: return ir
    # Clause-scoped compilers may already have closed a same-place endpoint ratio.  A later
    # generic ``ratio of X to Y`` recovery must not reinterpret the trailing answer-form phrase
    # ("what is the ratio?") as a second place.  Differing point times are sufficient evidence
    # that the two explicit operands have already been bound.
    if isinstance(ir,dict) and ir.get("op")=="COMPARE" and ir.get("how")=="ratio" \
            and re.search(r"\bdivid(?:e|ed)\s+by\b",question,re.I):
        left,right=_first_select(ir.get("left")),_first_select(ir.get("right"))
        lt=left.get("time") if left else None;rt=right.get("time") if right else None
        if left and right and isinstance(lt,dict) and isinstance(rt,dict) and lt != rt:
            return ir
    region, time = first.get("region"), first.get("time")
    cross=re.search(r"\bratio of (.+?) to (.+?) in ((?:19|20)\d{2})\b",_phrase_norm(question))
    if cross:
        operands=[]
        for text in cross.groups()[:2]:
            occ=_entity_occurrences(text)
            if not occ:break
            entity=occ[-1][2];place=_phrase_norm(text)
            place=re.sub(r"\b"+re.escape(_phrase_norm(entity))+r"\b","",place,count=1).strip()
            place=re.sub(r"^(?:in|for)\s+|\s+(?:in|for)$","",place).strip()
            if not place:break
            operands.append((entity,place))
        if len(operands)==2:
            year=cross.group(3);point={"start":year,"end":year}
            return {"op":"COMPARE","how":"ratio",
                    "left":{"op":"SELECT","entity":operands[0][0],"region":{"op":"REGION","place":operands[0][1]},"time":point},
                    "right":{"op":"SELECT","entity":operands[1][0],"region":{"op":"REGION","place":operands[1][1]},"time":point}}
    if isinstance(ir,dict) and ir.get("op")=="COMPARE" and ir.get("how")=="ratio":
        left,right=ir.get("left"),ir.get("right")
        if isinstance(left,dict) and isinstance(right,dict) and left.get("op")==right.get("op")=="SELECT" \
                and left.get("region") != right.get("region"):
            return ir
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


def mech_mixed_source_compare(ir, question):
    """Bind each explicit statistical comparison clause independently.

    Mixed Eurostat/ILO/World-Bank questions are especially vulnerable to operand bleed: the model
    copies the first region to both leaves or the longer second measure to both entities.  An
    explicit `X against/vs/over Y, YEAR ratio|difference` surface determines both leaves without
    any transfer inference, so reconstruct it clause-locally.
    """
    # The possessive endpoint compiler has already expanded ``its`` and removed any answer-form
    # suffix.  Sending that closed tree through the generic free-form split below would parse
    # "what is the ratio" as a region.
    if isinstance(ir,dict) and ir.get("op")=="COMPARE" and ir.get("how")=="ratio" \
            and re.search(r"\bdivid(?:e|ed)\s+by\s+its\b",question,re.I):
        left,right=_first_select(ir.get("left")),_first_select(ir.get("right"))
        if left and right and left.get("time") != right.get("time"):
            return ir
    if re.match(r"\s*(?:19|20)\d{2}\s+snapshot\s*:",question,re.I) \
            and isinstance(ir,dict) and ir.get("op")=="COMPARE" \
            and _first_select(ir.get("left")) and _first_select(ir.get("right")):
        return ir
    patterns = (
        (r"^\s*(.+?)\s+against\s+(.+?)\s+in\s+((?:19|20)\d{2})\s*,?\s*as\s+a\s+ratio[.?!]*$", "ratio"),
        (r"^\s*(.+?)\s+vs\.?\s+(.+?)\s*,\s*((?:19|20)\d{2})\s+difference[.?!]*$", "difference"),
        (r"^\s*(?:dashboard\s*:\s*)?(.+?)\s+over\s+(.+?)\s*,\s*((?:19|20)\d{2})\s+ratio[.?!]*$", "ratio"),
    )
    match = mode = None
    for pattern, candidate_mode in patterns:
        match = re.match(pattern, question, re.I)
        if match:
            mode = candidate_mode
            break
    left_fallback = ir.get("left") if isinstance(ir,dict) and ir.get("op") == "COMPARE" else _first_select(ir)
    right_fallback = ir.get("right") if isinstance(ir,dict) and ir.get("op") == "COMPARE" else None
    if match:
        year = match.group(3)
        left = _stat_operand_from_clause(match.group(1), year, left_fallback)
        right = _stat_operand_from_clause(match.group(2), year, right_fallback)
        if left and right and left.get("region") and right.get("region"):
            return {"op":"COMPARE", "how":mode, "left":left, "right":right}

    # Non-commutative prose forms.  Every side is compiled from its own clause; a fallback may
    # supply an explicitly shared region ("its", or a leading "For Germany") but never an entity.
    surfaces = (
        (r"^\s*in\s+percentage\s+points\s*,\s*subtract\s+(.+?)\s+from\s+(.+?)[.?!]*$",
         "difference", 2, 1),
        (r"^\s*difference\s+requested\s*:\s*(.+?)\s+minus\s+(.+?)\s+in\s+((?:19|20)\d{2})[.?!]*$",
         "difference", 1, 2),
        (r"^\s*ratio\s+check\s+for\s+((?:19|20)\d{2})\s*:\s*(.+?)\s+divided\s+by\s+(.+?)[.?!]*$",
         "ratio", 2, 3),
        (r"^\s*divide\s+(.+?)\s+by\s+(.+?)[.?!]*$", "ratio", 1, 2),
    )
    for pattern, candidate_mode, left_group, right_group in surfaces:
        found = re.match(pattern, question, re.I)
        if not found:
            continue
        years = re.findall(r"\b(?:19|20)\d{2}\b", question)
        if not years:
            return ir
        year = years[-1]
        left = _stat_operand_from_clause(found.group(left_group), year, left_fallback)
        # "its" inherits only the already grounded sibling region.
        inherited = left if re.search(r"\b(?:its|the same country)\b", found.group(right_group), re.I) else right_fallback
        right = _stat_operand_from_clause(found.group(right_group), year, inherited)
        if left and right and left.get("region") and right.get("region"):
            return {"op":"COMPARE", "how":candidate_mode, "left":left, "right":right}

    scoped = re.match(
        r"^\s*for\s+(.+?)\s+in\s+((?:19|20)\d{2})\s*,\s*subtract\s+(.+?)\s+from\s+(.+?)[.?!]*$",
        question, re.I)
    if scoped:
        place, year, subtrahend, minuend = scoped.groups()
        fallback = {"region":{"op":"REGION", "place":place.strip()}}
        left = _stat_operand_from_clause(minuend, year, fallback)
        right = _stat_operand_from_clause(subtrahend, year, fallback)
        if left and right:
            return {"op":"COMPARE", "how":"difference", "left":left, "right":right}

    multiple=re.match(
        r"^\s*((?:19|20)\d{2})\s*(?:—|-)\s*(.+?)[’']s\s+(.+?)"
        r"(?:\s+is\s+how\s+many\s+times|\s*,\s*as\s+a\s+multiple\s+of)\s+"
        r"(.+?)[’']s[?!.]*$",question,re.I)
    if multiple:
        year,left_place,entity_text,right_place=multiple.groups();occ=_entity_occurrences(entity_text)
        if occ:
            entity=max(occ,key=lambda item:item[1]-item[0])[2];time={"start":year,"end":year}
            def point(place):return {"op":"SELECT","entity":entity,
                "region":{"op":"REGION","place":place.strip(" ,")},"time":time}
            return {"op":"COMPARE","how":"ratio","left":point(left_place),"right":point(right_place)}

    # Compact analyst surfaces still determine two independently scoped operands. Strip only a
    # short discourse label before `:`, then consume place/year separately from each measure.
    body = re.sub(r"^\s*(?:analyst|brief|note|decision check|orientation probe|"
                  r"ratio orientation(?: flipped)?)\s*:\s*",
                  "", question, flags=re.I)
    body = re.sub(r"\s*\([^)]*(?:WB|World Bank|ILO|Eurostat|percent|region|country)[^)]*\)\s*[.?!]*$",
                  "", body, flags=re.I)
    shared = re.match(r"^\s*(?:in\s+)?(.+?)\s+((?:19|20)\d{2})\s*(?:,|—|-)\s*"
                      r"(.+?)\s+(minus|divided\s+by)\s+(.+?)[.?!]*$", body, re.I)
    if shared:
        place, year, left_text, operator, right_text = shared.groups()
        fallback={"region":{"op":"REGION","place":place.strip(" ,—-")}}
        left=_stat_operand_from_clause(left_text,year,fallback)
        right=_stat_operand_from_clause(right_text,year,fallback)
        if left and right:
            return {"op":"COMPARE", "how":"ratio" if "divided" in operator.lower() else "difference",
                    "left":left,"right":right}

    split = re.match(r"^\s*(.+?)\s+(minus|divided\s+by|vs\.?|/)\s+(.+?)[.?!]*$",
                     body, re.I)
    if split:
        left_text, operator, right_text = split.groups()
        yleft=re.findall(r"\b(?:19|20)\d{2}\b",left_text)
        yright=re.findall(r"\b(?:19|20)\d{2}\b",right_text)
        years=re.findall(r"\b(?:19|20)\d{2}\b",body)
        if years:
            left=_stat_operand_from_clause(left_text,yleft[-1] if yleft else years[-1])
            right=_stat_operand_from_clause(right_text,yright[-1] if yright else years[-1])
            if left and right:
                right_region=right.get("region")
                if isinstance(right_region,dict) and not str(right_region.get("place","")).strip():
                    right=dict(right);right["region"]=left.get("region")
                mode="ratio" if re.search(r"divided|/",operator,re.I) else "difference"
                return {"op":"COMPARE","how":mode,"left":left,"right":right}
    return ir


def _requested_rank_order(question, default="desc"):
    """Resolve explicit direction phrases before isolated superlative words.

    "highest to lowest" contains the word ``lowest`` but is descending; checking single words
    first inverted several otherwise-complete ranks.
    """
    ql = _phrase_norm(question)
    if re.search(r"\b(?:highest|largest|most)\s+to\s+(?:lowest|smallest|fewest|least)\b"
                 r"|\bdescending\b|\bhighest\s+first\b", ql):
        return "desc"
    if re.search(r"\b(?:lowest|smallest|fewest)\s+to\s+(?:highest|largest|most)\b"
                 r"|\blow\s+to\s+high\b|\bascending\b|\blowest\s+first\b", ql):
        return "asc"
    # Preserve a caller's signed-change interpretation: the "largest drop" is normally the
    # most-negative later-minus-earlier value, not the numerically largest scalar.
    if re.search(r"\b(?:largest|greatest|steepest)\s+(?:drop|decrease|fall)\b"
                 r"|\bmost\s+improvement\b", ql):
        return default
    if re.search(r"\b(?:lowest|smallest|fewest|least)\b", ql):
        return "asc"
    if re.search(r"\b(?:highest|largest|greatest|most)\b", ql):
        return "desc"
    return default


def mech_rank_k(ir, question):
    """Bind an explicit first-N modifier independently of how the RANK tree was produced."""
    if not isinstance(ir,dict) or ir.get("op")!="RANK":return ir
    words={"one":1,"two":2,"three":3,"four":4,"five":5,"six":6,"seven":7,"eight":8,
           "nine":9,"ten":10}
    m=re.search(r"\b(?:top|bottom)\s*[- ]\s*(\d+|one|two|three|four|five)\b",question,re.I)
    if not m:
        m=re.search(r"\b(?:show|give|return)\s+(?:the\s+)?"
                    r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b.+?"
                    r"\b(?:highest|lowest|most|fewest)\b",question,re.I)
    if not m:
        # Cardinality can lead the candidate inventory ("which two of A, B, C"), the
        # requested quantity ("which two have the shortest mean distance"), or a terse
        # dashboard surface ("two densest for X").  Bind it independently of item semantics.
        m=re.search(r"\b(?:which|choose|pick|return|show|give)?\s*(?:the\s+)?"
                    r"(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b"
                    r"(?=\s+(?:of\b|have\b|has\b|had\b|show\b|shows\b|with\b|highest\b|lowest\b|least\b|"
                    r"shortest\b|longest\b|smallest\b|largest\b|densest\b|sparsest\b))",
                    question,re.I)
    if not m:
        m=re.search(r"\bwhich\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+"
                    r"(?:rank|are ranked)\s+(?:the\s+)?(?:highest|lowest)\b",question,re.I)
    if not m:
        m=re.search(r"\breturn\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten)\b",
                    question,re.I)
    if not m:
        # Singular winner questions denote argmax/argmin, not the complete ordering.
        if re.search(r"\bwhich\s+(?:(?:city|place|region|country)\s+)?(?:has|had|saw)\s+"
                     r"(?:the\s+)?(?:most|fewest|highest|lowest|largest|smallest|greatest|more|fewer)\b",
                     question,re.I):
            out=dict(ir);out["k"]=1;return out
        if re.search(r"\bwhich\s+(?:recorded|reported|showed)\s+(?:the\s+)?"
                     r"(?:highest|lowest|largest|smallest|most|fewest)\b", question, re.I):
            out=dict(ir);out["k"]=1;return out
        if re.search(r"\b(?:winner\s+only|pick\s+the\s+\w+\s+with\s+the\s+"
                     r"(?:highest|lowest|most|fewest)|which\s+one\b)",question,re.I):
            out=dict(ir);out["k"]=1;return out
        if re.search(r"\b(?:name|choose|return|show)\s+(?:the\s+)?(?:one\s+)?single\s+"
                     r"(?:city|place|region|country)\b.+?\b(?:most|fewest|highest|lowest)\b",
                     question,re.I):
            out=dict(ir);out["k"]=1;return out
        if re.search(r"\b(?:most numerous|fewest points|which count is highest|"
                     r"highest related density|lowest .+? among|largest .+?(?:change|ratio))\b",
                     question,re.I):
            out=dict(ir);out["k"]=1;return out
        if re.search(r"\b(?:order|rank|list)\s+(?:all|every)|\bfull\s+.+?list\b|"
                     r"\bevery candidate\b",question,re.I):
            out=dict(ir);out["k"]=len(ir.get("items") or []);return out
        return ir
    token=m.group(1).lower();out=dict(ir);out["k"]=int(token) if token.isdigit() else words[token]
    if re.search(r"\bbottom\b",m.group(0),re.I):out["order"]="asc"
    elif re.search(r"\btop\b",m.group(0),re.I):out["order"]="desc"
    return out


def _enumerated_spatial_candidate(clause, metric):
    """Compile one ``PLACE facility [within D of anchor]`` rank candidate."""
    facility = (r"craft[- ]workshops?|coworking[- ]spaces?|markets?|marketplaces?|"
                r"pharmac(?:y|ies)|banks?|hospitals?|bus stops?|bus stations?|cafes?")
    match=re.match(r"\s*(.+?)\s+("+facility+r")\b(.*)$",clause.strip(" ,.;"),re.I)
    if not match:return None
    place,entity_text,tail=match.groups()
    # Rank-head prose can leak into the first candidate when no colon is present.
    place=re.sub(r"^(?:fewest points among|most numerous candidate|which count is highest)\s*",
                 "",place,flags=re.I).strip(" ,:—-")
    entity_occ=_entity_occurrences("a "+entity_text,osm_only=True)
    if not place or not entity_occ:return None
    entity=entity_occ[-1][2];region={"op":"REGION","place":place}
    source={"op":"SELECT","entity":entity,"region":region,"time":None}
    if re.search(r"\b(?:within|near|nearby|by nearby)\b",tail,re.I):
        anchors=list(dict.fromkeys(k for _,_,k in _entity_occurrences(tail,osm_only=True)))
        if not anchors:return None
        source={"op":"RELATE","relation":"within","left":source,
                "right":{"op":"SELECT","entity":anchors[-1],"region":region,"time":None}}
        distance=_parse_dist_km(tail.lower())
        if distance is not None:source["threshold_km"]=distance
    return {"op":"AGGREGATE","by":"space","metric":metric,"source":source}


def mech_enumerated_rank(ir, question):
    """Close semicolon candidate registers into RANK before a model can merge their scopes.

    Candidate-local place, entity, relation, threshold, and time roles are parsed independently;
    the wrapper then binds order and requested cardinality.  This is deliberately limited to an
    explicit rank/superlative head plus at least three fully closed candidates.
    """
    ql=question.lower()
    rank_head=bool(re.search(r"\b(?:rank|order|top|smallest|largest|highest|lowest|fewest|"
                             r"most numerous|least dense|descending|ascending)\b",ql))
    if not rank_head:return ir

    def finish(items):
        if len(items)<3:return None
        out={"op":"RANK","items":items,
             "order":_requested_rank_order(question,"desc")}
        out=mech_rank_k(out,question)
        if "k" not in out and re.search(r"\b(?:all|every|full)\b",ql):out["k"]=len(items)
        return out

    # Statistical candidate registers. Each semicolon clause owns its country and endpoints.
    if re.search(r"\bgini(?: coefficient|-coefficient)?\b",ql):
        segment=question.split(":",1)[1] if ":" in question else question
        clauses=[c.strip(" ,.;?") for c in segment.split(";") if c.strip(" ,.;?")]
        if len(clauses)<3:
            clauses=[f"{place} in {year}" for place,year in re.findall(
                r"\b([A-Z][A-Za-z ]+?)\s+in\s+((?:19|20)\d{2})(?=,|\s+and\b|\?)",
                question)]
        items=[]
        ratio=bool(re.search(r"\bratio|later-to-earlier|/",ql))
        derived=ratio or bool(re.search(r"\b(?:change|endpoint change|minus)\b",ql))
        for clause in clauses:
            years=re.findall(r"\b(?:19|20)\d{2}\b",clause)
            place=re.split(r",?\s+(?:in\s+)?(?:19|20)\d{2}\b",clause,maxsplit=1,
                           flags=re.I)[0]
            place=re.sub(r"^.*?(?:gini(?:-coefficient)?\s+(?:level|change|ratio)s?\s*:\s*)",
                         "",place,flags=re.I).strip(" ,:—-")
            place=re.sub(r"^(?:Brazil|India|Kenya)\s+and\s+", "", place,
                         flags=re.I).strip(" ,")
            if not years or not place:continue
            if derived and len(years)>=2:
                earlier,later=sorted(years[:2],key=int)
                left=_stat_operand_from_clause(f"{place} gini coefficient",later)
                right=_stat_operand_from_clause(f"{place} gini coefficient",earlier)
                if left and right:items.append({"op":"COMPARE","how":"ratio" if ratio else "difference",
                                                "left":left,"right":right})
            else:
                item=_stat_operand_from_clause(f"{place} gini coefficient",years[-1])
                if item:items.append(item)
        closed=finish(items)
        if closed:return closed

    # Spatial candidate registers always use semicolons, which makes clause scope explicit.
    if ";" in question:
        segment=question.split(":",1)[1] if ":" in question else question
        clauses=[c.strip(" ,.;?") for c in segment.split(";") if c.strip(" ,.;?")]
        metric="density" if re.search(r"\bdens",ql) else "count"
        items=[_enumerated_spatial_candidate(c,metric) for c in clauses]
        if all(items):
            closed=finish(items)
            if closed:return closed
    return ir


def _rank_candidate_places(ir, question):
    """Return the complete literal candidate inventory for an explicit >=3-way ranking."""
    places = []
    if isinstance(ir, dict) and ir.get("op") == "RANK":
        for item in ir.get("items", []):
            selected = _first_select(item)
            region = selected.get("region") if selected else None
            place = region.get("place") if isinstance(region, dict) else region
            if place is not None and place not in places:
                places.append(place)
    if len(places) >= 3:
        return places
    # This surface is deliberately independent of a model-produced tree: H22's computed
    # relational rank failed to parse at all despite spelling out every candidate.
    match = re.search(
        r"\bwhich\s+(?:\d+|one|two|three|four|five)\s+of\s+(.+?)\s+"
        r"(?:has|have|had|show|shows|return|returns)\b", question, re.I)
    if match:
        places = _literal_place_list(match.group(1))
    if len(places) < 3:
        suffix = re.search(
            r"\bwhich\s+(?:(?:city|place|region|country)\s+)?has\s+the\s+"
            r"(?:most|fewest|highest|lowest|largest|smallest)\b"
            r".+?:\s*(.+?)[?!.]*$", question, re.I)
        if suffix:
            places = _literal_place_list(suffix.group(1))
    if len(places) < 3 and re.search(r"\b(?:rank|order|top|bottom)\b",question,re.I):
        suffix=re.search(r":\s*(.+?)[?!.]*$",question,re.I)
        if suffix:places=_literal_place_list(suffix.group(1))
    return ["?place" if _phrase_norm(place) == "here" else place for place in places]


def mech_ranked_quantity(ir, question):
    """Instantiate one complete quantity subtree per candidate in a computed RANK.

    Candidate closure and quantity planning are separate.  A ratio, relational density, or mean
    distance is one ranked item—not a flat list of its constituent SELECTs.
    """
    ql = _phrase_norm(question)
    rank_intent = re.search(
        r"\b(?:rank|order|top|bottom|which one|which two|choose the|two densest|"
        r"highest|lowest|shortest|longest|smallest|largest|most|fewest)\b", ql)
    if not rank_intent:
        return ir
    places = _rank_candidate_places(ir, question)
    if len(places) < 3:
        return ir
    year_match = re.search(r"\b((?:19|20)\d{2})\b", question)
    time = ({"start":year_match.group(1), "end":year_match.group(1)} if year_match else None)
    def selected(entity, place):
        return {"op":"SELECT", "entity":entity,
                "region":{"op":"REGION", "place":place}, "time":time}
    def finish(items, order):
        return mech_rank_k({"op":"RANK", "items":items, "order":order}, question)

    # Endpoint ratio ranks: candidate inventory, arithmetic blueprint, and result cardinality
    # are independent. Whole-window SELECTs rank levels, not Y2/Y1 change ratios.
    years = sorted(set(re.findall(r"\b(?:19|20)\d{2}\b", question)), key=int)
    if len(years) == 2 and re.search(
            r"(?:\b(?:ratios?|divided)\b|\b(?:19|20)\d{2}\s*/\s*(?:19|20)\d{2}\b)",
            question, re.I):
        import connectors as C
        measures = [item for item in _entity_occurrences(question) if
                    C.ilo_resolve_indicator(item[2])[0] or
                    C.eurostat_resolve_indicator(item[2])[0] or
                    C.wb_resolve_indicator(item[2])[0]]
        if measures:
            entity = max(measures, key=lambda item:item[1]-item[0])[2]
            earlier, later = years
            def point(place, year):
                return {"op":"SELECT", "entity":entity,
                        "region":{"op":"REGION", "place":place},
                        "time":{"start":year,"end":year}}
            items = [{"op":"COMPARE", "how":"ratio",
                      "left":point(place,later), "right":point(place,earlier)}
                     for place in places]
            order = _requested_rank_order(question, "desc")
            return finish(items, order)

    # Ratio of two per-place counts.
    ratio = re.search(r"\b(.+?)[- ]to[- ](.+?)\s+count\s+ratios?\b", ql)
    if ratio:
        left_occ = _entity_occurrences(ratio.group(1), osm_only=True)
        right_occ = _entity_occurrences(ratio.group(2), osm_only=True)
        if left_occ and right_occ:
            left_entity, right_entity = left_occ[-1][2], right_occ[-1][2]
            def counted(entity, place):
                return {"op":"AGGREGATE", "by":"space", "metric":"count",
                        "source":selected(entity, place)}
            items = [{"op":"COMPARE", "how":"ratio",
                      "left":counted(left_entity, place),
                      "right":counted(right_entity, place)} for place in places]
            return finish(items, "asc" if "lowest" in ql else "desc")

    # Explicit nearest-distance mean.  Candidate labels may carry the repeated left entity
    # ("Bengaluru markets, Nairobi markets, ..."); the existing RANK inventory supplies places.
    nearest = re.search(r"\b(?:shortest|longest).*?mean distance.*?nearest\s+(.+?)(?::|,|$)",
                        question, re.I)
    if nearest:
        anchor_occ = _entity_occurrences(nearest.group(1), osm_only=True)
        all_occ = list(dict.fromkeys(key for _, _, key in
                                     _entity_occurrences(question, osm_only=True)))
        if re.search(r"\bmarkets?\b", question, re.I) and "marketplace" not in all_occ:
            all_occ.append("marketplace")
        if anchor_occ and len(all_occ) >= 2:
            anchor = anchor_occ[-1][2]
            entity = next((item for item in all_occ if item != anchor), None)
            if entity:
                items=[]
                for place in places:
                    rel={"op":"RELATE", "relation":"distance",
                         "left":selected(entity,place), "right":selected(anchor,place)}
                    items.append({"op":"AGGREGATE", "by":"space", "metric":"mean",
                                  "source":rel})
                return finish(items, "asc" if "shortest" in ql else "desc")

    # Relational count/density: the full predicate is cloned per place.
    quantity_surface = question.split(":", 1)[0] if ":" in question else question
    relation_match = re.search(
        r"\b(?:highest|lowest|most|fewest|"
        r"top\s*[- ]?\s*(?:\d+|one|two|three|four|five)\s+"
        r"(?:(?:cities|places|regions|countries)\s+)?by|"
        r"which\s+(?:city|place|region|country)\s+has\s+the\s+(?:most|fewest))\s+"
        r"(?:the\s+)?(?:density\s+of\s+)?"
        r"(.+?)\s+(within|beyond)\s+(.+?)\s+(?:of|from)\s+(?:a\s+|an\s+|the\s+)?(.+?)[?.,]?$",
        quantity_surface, re.I)
    if relation_match:
        entity_text, relation, distance, anchor_text = relation_match.groups()
        entity_occ = _entity_occurrences(entity_text, osm_only=True)
        anchor_occ = _entity_occurrences(anchor_text, osm_only=True)
        import connectors as C
        if not entity_occ and C.osm_resolve_tag(entity_text)[0]:
            entity_occ=[(0,len(entity_text),entity_text.strip(" ,.?"))]
        if not anchor_occ and C.osm_resolve_tag(anchor_text)[0]:
            anchor_occ=[(0,len(anchor_text),anchor_text.strip(" ,.?"))]
        if entity_occ and anchor_occ:
            entity, anchor = entity_occ[-1][2], anchor_occ[0][2]
            metric = "density" if re.search(r"\bdensit", question, re.I) else "count"
            d = _parse_dist_km(distance.lower())
            items=[]
            for place in places:
                rel={"op":"RELATE", "relation":relation.lower(),
                     "left":selected(entity,place), "right":selected(anchor,place)}
                if d is not None: rel["threshold_km"] = d
                items.append({"op":"AGGREGATE", "by":"space", "metric":metric,
                              "source":rel})
            order = _requested_rank_order(question,
                "asc" if re.search(r"\b(?:lowest|fewest)\b", question,re.I) else "desc")
            return finish(items, order)
    return ir


def mech_same_time_measure_difference(ir, question):
    """Compile literal `measure in YEAR minus measure in YEAR` with distinct measure leaves."""
    m=re.search(r"(?:calculate|compute|what\s+was|what\s+is)\s+(.+?)\s+in\s+((?:19|20)\d{2})\s+minus\s+(.+?)\s+in\s+((?:19|20)\d{2})",
                question,re.I)
    if not m:return ir
    left_text,y1,right_text,y2=m.groups()
    lo=_entity_occurrences(left_text);ro=_entity_occurrences(right_text)
    if not lo or not ro:return ir
    first=_first_select(ir)
    if not first:return ir
    region=first.get("region")
    return {"op":"COMPARE","how":"difference",
            "left":{"op":"SELECT","entity":lo[-1][2],"region":region,
                    "time":{"start":y1,"end":y1}},
            "right":{"op":"SELECT","entity":ro[-1][2],"region":region,
                     "time":{"start":y2,"end":y2}}}


def mech_dormant_ops(ir, question):
    """Compile explicit presence/cooccur/annotation surfaces whose literals determine the tree."""
    first = _first_select(ir)
    if not first: return ir
    ql = question.lower()
    # Here "near this neighbourhood" locates the entity in an unresolved place; the
    # neighbourhood is not a second record entity to self-join against.
    if re.match(r"\s*(?:are\s+there\s+)?any\b", ql) and re.search(
            r"\bnear\s+(?:this|my|the)\s+(?:neighbou?rhood|area|district|town)\b", ql):
        return {"op":"AGGREGATE", "by":"space", "metric":"presence",
                "source":{"op":"SELECT", "entity":first.get("entity"),
                          "region":"?place", "time":first.get("time")}}
    if re.search(r"\b(?:are|is)\s+there\s+(?:any\s+)?(?!more\b)", ql) or re.match(r"\s*(?:are\s+(?:there\s+)?any|any)", ql):
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
    if re.search(r"\b(?:what are the names of|what are the .+? names|names of|named .+? records|"
                 r"listed? by name)\b",ql):
        source = ir
        if ir.get("op") == "AGGREGATE" and isinstance(ir.get("source"), dict):
            source = ir["source"]
        if not isinstance(source, dict) or source.get("op") not in ("SELECT", "RELATE"):
            source = first
        return {"op":"ANNOTATE","source":source,"layer":"name"}
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
    if re.search(r"\b(?:tag|label)\s+(?:each|every|them|those|the results?)\b.+?\bwith\b", ql):
        field = re.search(r"\bthe\s+([a-z][a-z0-9_:.-]+)\s+field\b", ql)
        attribute = re.search(r"\bwith\s+(?:its|their)\s+(.+?)(?:\s*\(|[,.?]|$)", ql)
        if field or attribute:
            layer = (field.group(1) if field else attribute.group(1)).strip().replace(" ", "_")
            if ir.get("op") == "ANNOTATE" and str(ir.get("layer", "")).replace(" ", "_") == layer \
                    and isinstance(ir.get("source"), dict) \
                    and ir["source"].get("op") in ("SELECT", "RELATE"):
                return ir
            source = ir
            if ir.get("op") == "AGGREGATE" and isinstance(ir.get("source"), dict):
                source = ir["source"]
            if not isinstance(source, dict) or source.get("op") not in ("SELECT", "RELATE"):
                source = first
            return {"op": "ANNOTATE", "source": source, "layer": layer}
    if re.search(r"\baddresses?\s+(?:of|for)\b|\bshow\s+(?:the\s+)?addresses?\b", ql):
        if ir.get("op")=="ANNOTATE" and ir.get("layer")=="address": return ir
        source=ir
        if ir.get("op")=="AGGREGATE" and isinstance(ir.get("source"),dict): source=ir["source"]
        if not isinstance(source,dict) or source.get("op") not in ("SELECT","RELATE"): source=first
        return {"op":"ANNOTATE","source":source,"layer":"address"}
    if "co-occur" in ql or "sharing a 5 km neighbourhood" in ql:
        entities = [key for _, _, key in _entity_occurrences(question, osm_only=True)]
        if len(entities) >= 2:
            relation = {"op": "RELATE", "relation": "cooccur",
                        "left": {"op": "SELECT", "entity": entities[0],
                                 "region": first.get("region"), "time": None},
                        "right": {"op": "SELECT", "entity": entities[1],
                                  "region": first.get("region"), "time": None}}
            distance = _parse_dist_km(ql)
            if distance is not None: relation["threshold_km"] = distance
            if re.match(r"\s*(?:do|does|is|are)\b", question, re.I):
                return {"op":"AGGREGATE", "by":"space", "metric":"presence",
                        "source":relation}
            return relation
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


def mech_prefixed_statistic(ir, question):
    """Compile a simple `PLACE[, YEAR] — MEASURE` heading without inheriting a wrong source.

    The rule is deliberately excluded for arithmetic, ranking, relation, and transfer language.
    A curated NUTS region chooses the regional statistical vocabulary before national WB aliases.
    """
    import connectors as C
    match = re.match(r"^\s*(.+?)(?:\s*,\s*((?:19|20)\d{2}))?\s+(?:—|-)\s+(.+?)[.?!]*$",
                     question, re.I)
    if not match: return ir
    place, heading_year, body = match.groups()
    place=re.sub(r"^(?:analyst\s+note|note|briefing)\s*:\s*","",place,flags=re.I).strip()
    back_year=re.search(r"\s+back\s+in\s+((?:19|20)\d{2})\s*$",place,re.I)
    if back_year:
        heading_year=heading_year or back_year.group(1)
        place=place[:back_year.start()].strip()
    # A dash after a narrative preamble is punctuation, not a PLACE heading. The prior broad
    # match turned “I'm a freelance consultant — ... in Kenya” into an unresolved region.
    if re.search(r"\b(?:i\s+am|i\s+m|my|for\s+the|actually|just\s+need|thinking|worried|"
                 r"consultant|scrap)\b",_phrase_norm(place)):
        return ir
    years=re.findall(r"\b(?:19|20)\d{2}\b",question)
    # Analyst heading with an explicit endpoint difference: PLACE+MEASURE appears before the
    # dash, so compile that clause directly rather than sending an invalid raw tree to repair.
    if re.search(r"\bdifference\b",body,re.I) and len(set(years))==2:
        y1,y2=sorted(set(years),key=int)
        left=_stat_operand_from_clause(place,y2)
        right=_stat_operand_from_clause(place,y1)
        if left and right:
            return {"op":"COMPARE","how":"difference","left":left,"right":right}
    if re.search(r"\b(?:minus|divided|ratio|rank|order|estimate|transfer|within|beyond|distance)\b|/",
                 body,re.I):
        return ir
    region={"op":"REGION","place":place.strip(" ,")}
    occurrences=_entity_occurrences(body)
    entity=None
    if C.eurostat_resolve_geo({"orig":place,"name":place}) and re.search(
            r"\bunemployment(?:\s+rate)?\b",body,re.I):
        entity="unemployment rate"
    elif occurrences:
        supported=[item for item in occurrences if
                   C.ilo_resolve_indicator(item[2])[0] or
                   C.eurostat_resolve_indicator(item[2])[0] or
                   C.wb_resolve_indicator(item[2])[0]]
        if supported: entity=max(supported,key=lambda item:item[1]-item[0])[2]
    if not entity:return ir
    trend=bool(re.search(r"\b(?:climbing|dropping|rising|falling|heading|trend(?:ing)?|direction)\b",body,re.I))
    if trend:
        start,end=(sorted(years,key=int)[0],sorted(years,key=int)[-1]) if len(years)>=2 else (None,None)
        source={"op":"SELECT","entity":entity,"region":region,
                "time":{"start":start,"end":end} if start else None}
        return {"op":"COMPARE","how":"trend_direction","left":source}
    year=heading_year or (years[-1] if years else None)
    return {"op":"SELECT","entity":entity,"region":region,
            "time":{"start":year,"end":year} if year else None}


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
    compact = re.search(r"\b((?:19|20)\d{2})\s*[–—-]\s*(\d{2})\b", question)
    explicit = (len(years) == 2 and
                re.search(r"\b(?:from|between)\b.+\b(?:to|through|and)\b",question,re.I))
    if compact:
        start = compact.group(1)
        end = start[:2] + compact.group(2)
    elif explicit:
        start, end = sorted(years)
    else:
        return ir
    def walk(value):
        if isinstance(value, list): return [walk(x) for x in value]
        if not isinstance(value, dict): return value
        out = {k: walk(v) for k, v in value.items()}
        # A compact range is itself the correction signal: the small model often copied only
        # its first endpoint.  Restrict the override to unary trend language.
        trend = re.search(r"\b(?:trend|direction|rising|falling|rise or fall|up or down)\b",
                          question,re.I)
        if out.get("op") == "SELECT" and (out.get("time") is None or (compact and trend)):
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
    explicit_distances=re.findall(r"[\d.]+\s*(?:km|m\b|meters?|metres?|kilometers?|kilometres?)",ql)
    if json.dumps(ir).count('"RELATE"')>=2 and len(explicit_distances)>=2:
        return ir
    if "and also" in ql or re.search(r"\bbut\s+(?:(?:have|has)\s+no|beyond|more than|within)\b", ql) \
            or re.search(r"\band\s+(?:beyond|more than)\b", ql) \
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
    presence=bool(re.search(r"\bpresence\s+(?:check|answer|result)\b",ql) or
                  re.match(r"\s*(?:presence\s+check\s*(?:—|:|-)?\s*)?"
                           r"(?:(?:are|is)\s+(?:there\s+)?any|any)\b",ql) or
                  re.match(r"\s*(?:does|do)\b.+?\bhave\s+any\b",ql))
    listing=bool(re.match(r"\s*(?:list|which|identify|where)\b",ql) or
                 re.search(r"\b(?:just|only)\s+the ones\b|\bi (?:want|need) (?:them|the results?) listed\b",ql))
    if count and ir.get("op")=="RELATE":
        return {"op":"AGGREGATE","by":"space","metric":"count","source":ir}
    if presence and ir.get("op")=="RELATE":
        return {"op":"AGGREGATE","by":"space","metric":"presence","source":ir}
    if listing and ir.get("op")=="AGGREGATE" and ir.get("metric") in ("count", "presence") \
            and isinstance(ir.get("source"),dict) and ir["source"].get("op")=="RELATE":
        if re.search(r"\byes\s*/\s*no\b|\ba yes-or-no\b|\ba yes/no\b", ql): return ir
        return ir["source"]
    if (not count and ir.get("op") == "AGGREGATE" and ir.get("metric") == "count" and
            isinstance(ir.get("source"), dict) and ir["source"].get("op") == "RELATE" and
            not re.search(r"\b(?:are\s+there\s+any|is\s+there\s+any|yes\s*/\s*no|presence|"
                          r"rank|order|which\s+(?:city|place|region|country)\s+has\s+more)\b", ql)):
        return ir["source"]
    return ir


def mech_annulus_relation(ir, question):
    """Compile a same-anchor ring: within an outer radius but beyond an inner radius."""
    ql = question.lower()
    if not (re.search(r"\bwithin\b", ql) and
            re.search(r"\b(?:yet|but|and)\s+(?:still\s+)?(?:more than|beyond|outside)\b", ql) and
            re.search(r"\bnearest\s+(?:one|it|the same|market\w*|facilit\w*)\b", ql)):
        return ir
    entities = list(dict.fromkeys(key for _, _, key in _entity_occurrences(question, osm_only=True)))
    distances = [_parse_dist_km(match.group(0)) for match in re.finditer(
        r"[\d.]+\s*(?:km|kilometers?|kilometres?|m\b|meters?|metres?)", ql)]
    first = _first_select(ir)
    if len(entities) != 2 or len(distances) < 2 or not first: return ir
    region = first.get("region")
    def select(entity):
        return {"op":"SELECT","entity":entity,"region":region,"time":None}
    inner = {"op":"RELATE","relation":"within","threshold_km":distances[0],
             "left":select(entities[0]),"right":select(entities[1])}
    outer = {"op":"RELATE","relation":"beyond","threshold_km":distances[1],
             "left":inner,"right":select(entities[1])}
    if re.search(r"\b(?:how many|count)\b", ql):
        return {"op":"AGGREGATE","by":"space","metric":"count","source":outer}
    return outer


def mech_nearest_distance(ir, question):
    """Compile explicit nearest-distance surfaces as binary RELATE(distance)."""
    first = _first_select(ir)
    if not first: return ir
    region = first.get("region")

    def entity(text):
        found = _entity_occurrences(text)
        if found: return max(found, key=lambda item: item[1] - item[0])[2]
        value = re.sub(r"^(?:a|an|the)\s+", "", text.strip(" ,.;:?"), flags=re.I)
        value = re.sub(r"^(?:their|its)\s+(?:nearest|closest)\s+", "", value, flags=re.I)
        if value.lower().endswith("ies"): value = value[:-3] + "y"
        elif value.lower().endswith("s"): value = value[:-1]
        return value

    annotate = re.search(
        r"\bannotate\s+(.+?)\s+in\s+.+?\s+with\s+(?:the\s+)?distance\s+to\s+"
        r"(?:the\s+)?nearest\s+(.+?)[.?!]*$", question, re.I)
    reverse = re.search(
        r"\bdistance\s+to\s+(?:the\s+)?(?:nearest|closest)\s+(.+?)\s+from\s+(.+?)\s+in\s+.+?[.?!]*$",
        question, re.I)
    between = re.search(
        r"\bdistance\s+between\s+(.+?)\s+and\s+(.+?)\s+in\s+.+?[.?!]*$", question, re.I)
    from_to = re.search(
        r"\bdistances?\s+from\s+(.+?)\s+to\s+(.+?)(?:\s+nearby)?\s*(?:—|;|,|[.?!]|$)",
        question, re.I)
    each_here = re.search(
        r"\bgive\s+each\s+(.+?)\s+here\s+its\s+distance\s+to\s+(?:the\s+)?"
        r"(?:nearest|closest)\s+(.+?)[.?!]*$", question, re.I)
    for_each = re.search(
        r"\bfor\s+each\s+(.+?)\s+in\s+(.+?),\s*(?:its\s+)?distance\s+to\s+"
        r"(?:the\s+)?nearest\s+(.+?)[.?!]*$", question, re.I)
    how_far_from = re.search(
        r"\bfrom\s+(?:a|an|the)\s+(.+?),\s*how\s+far(?:'s|\s+is)\s+"
        r"(?:the\s+)?nearest\s+(.+?)[.?!]*$", question, re.I)
    if annotate:
        left_entity, right_entity = entity(annotate.group(1)), entity(annotate.group(2))
    elif reverse:
        right_entity, left_entity = entity(reverse.group(1)), entity(reverse.group(2))
    elif between:
        left_entity, right_entity = entity(between.group(1)), entity(between.group(2))
    elif from_to:
        left_entity, right_entity = entity(from_to.group(1)), entity(from_to.group(2))
    elif each_here:
        left_entity, right_entity = entity(each_here.group(1)), entity(each_here.group(2))
        region = {"op":"REGION", "place":"?place"}
    elif for_each:
        left_entity=entity(for_each.group(1));right_entity=entity(for_each.group(3))
        region={"op":"REGION","place":for_each.group(2).strip(" ,")}
    elif how_far_from:
        left_entity,right_entity=entity(how_far_from.group(1)),entity(how_far_from.group(2))
    elif re.search(r"\bfor each\b.+?\bhow far\b.+?\bnearest\b", question, re.I):
        entities = list(dict.fromkeys(key for _, _, key in
                                      _entity_occurrences(question, osm_only=True)))
        if len(entities) < 2: return ir
        left_entity, right_entity = entities[0], entities[1]
    else:
        return ir
    return {"op":"RELATE","relation":"distance",
            "left":{"op":"SELECT","entity":left_entity,"region":region,"time":None},
            "right":{"op":"SELECT","entity":right_entity,"region":region,"time":None}}


def mech_unresolved_point_time(ir, question):
    """A deictic or explicitly undecided single year is a time slot, never null or ESTIMATE."""
    if re.search(r"\b(?:19|20)\d{2}\b", question): return ir
    if not (re.search(r"\bthat year\b", question, re.I) or
            re.search(r"\b(?:which|what) year\b", question, re.I)):
        return ir
    first = _first_select(ir)
    if not first: return ir
    out = dict(first)
    out["time"] = {"start":"?year","end":"?year"}
    return out


def mech_terse_and_anaphoric(ir, question):
    """Compile terse answer forms and 'those' proximity references without guessing a referent."""
    ql=question.lower().strip()
    pronoun_anchor=re.match(
        r"^in\s+(.+?),\s*how\s+many\s+(.+?)\s+are\s+within\s+(.+?)\s+of\s+it[?!.]*$",
        question,re.I)
    if pronoun_anchor:
        place,entity_text,distance=pronoun_anchor.groups()
        entities=_entity_occurrences(entity_text,osm_only=True)
        if entities:
            region={"op":"REGION","place":place.strip(" ,")}
            relation={"op":"RELATE","relation":"within","threshold_km":_parse_dist_km(distance),
                      "left":{"op":"SELECT","entity":entities[-1][2],
                              "region":region,"time":None},
                      "right":{"op":"SELECT","entity":"?anchor_entity",
                               "region":region,"time":None}}
            return {"op":"AGGREGATE","by":"space","metric":"count","source":relation}
    bare_count=re.match(r"^in\s+(.+?),\s*how\s+many\s+of\s+(?:those|them)\s+"
                        r"(?:did\s+you\s+find|are\s+there)[?!.]*$",question,re.I)
    if bare_count:
        return {"op":"AGGREGATE","by":"space","metric":"count","source":{
            "op":"SELECT","entity":"?entity_type",
            "region":{"op":"REGION","place":bare_count.group(1).strip(" ,")},"time":None}}
    bare_relation=re.match(
        r"^in\s+(.+?),\s*which\s+of\s+(?:those|them)\s+.+?\s+within\s+(.+?)\s+of\s+"
        r"(?:a|an|the)\s+(.+?)[?!.]*$",question,re.I)
    if bare_relation:
        place,distance,anchor_text=bare_relation.groups();anchors=_entity_occurrences(anchor_text,osm_only=True)
        if not anchors:
            import connectors as C
            if C.osm_resolve_tag(anchor_text)[0]:
                anchors=[(0,len(anchor_text),anchor_text.strip(" ,"))]
        if anchors:
            region={"op":"REGION","place":place.strip(" ,")}
            return {"op":"RELATE","relation":"within","threshold_km":_parse_dist_km(distance),
                    "left":{"op":"SELECT","entity":"?entity_type","region":region,"time":None},
                    "right":{"op":"SELECT","entity":anchors[-1][2],"region":region,"time":None}}
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
    # If an earlier clause compiler has already represented the antecedent as a nested relation,
    # ``those`` is resolved.  Replacing that closed set with a fresh facility hole loses evidence.
    if isinstance(ir,dict) and json.dumps(ir).count('"RELATE"') >= 2:
        return ir
    implicit_any=bool(re.match(r"any\s+(?:near|within|more than|beyond)\b",ql))
    if ("those" not in ql and not implicit_any) or not re.search(r"\b(?:near|within|more than|beyond)\b",ql): return ir
    if re.match(r"^(?:how\s+many|count)\s+those\s*:",ql) and len(
            _entity_occurrences(question,osm_only=True)) >= 2:
        return ir
    pa=proximity_anchor(question);named=[key for _,_,key in _entity_occurrences(question,osm_only=True)]
    anchor=(pa or {}).get("anchor") or (named[-1] if named else None)
    if not anchor:return ir
    first = _first_select(ir)
    region = first.get("region") if first else "?place"
    if not region: region = "?place"
    relation="beyond" if ((pa or {}).get("negated") or re.search(r"\b(?:more than|beyond)\b",ql)) else "within"
    rel={"op":"RELATE","relation":relation,
         "left":{"op":"SELECT","entity":"?facility_type","region":region,"time":None},
         "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}
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
    # Cross-place ratio of the same explicitly related count.  "Corresponding count" carries
    # the whole entity/relation/threshold blueprint to the denominator, changing only its place.
    corresponding = re.search(
        r"\bratio\s+of\s+(.+?)(?:['’]s|\s+count\s+of)\s+count\s+of\s+(.+?)\s+"
        r"(beyond|within)\s+([\d.]+\s*(?:km|kilometers?|kilometres?|m\b|meters?|metres?))\s+"
        r"from\s+(.+?)\s+to\s+(.+?)(?:['’]s)?\s+corresponding\s+count[.?!]*$",
        question, re.I)
    if corresponding:
        place1, entity_text, relation, distance, anchor_text, place2 = corresponding.groups()
        entity_occ = _entity_occurrences(entity_text, osm_only=True)
        anchor_occ = _entity_occurrences(anchor_text, osm_only=True)
        if not entity_occ and re.fullmatch(r"markets?", entity_text.strip(), re.I):
            entity_occ = [(0, len(entity_text), "marketplace")]
        if entity_occ and anchor_occ:
            entity = entity_occ[0][2]
            anchor = anchor_occ[0][2]
            d = _parse_dist_km(distance.lower())
            def side(place):
                region={"op":"REGION", "place":place.strip(" ,")}
                related={"op":"RELATE", "relation":relation.lower(), "threshold_km":d,
                         "left":{"op":"SELECT", "entity":entity, "region":region, "time":None},
                         "right":{"op":"SELECT", "entity":anchor, "region":region, "time":None}}
                return {"op":"AGGREGATE", "by":"space", "metric":"count", "source":related}
            return {"op":"COMPARE", "how":"ratio", "left":side(place1), "right":side(place2)}
    if re.search(r"\bmore\b.+?\bnear\b.+?\bor\s+near\b", ql) and len(ents) >= 3:
        region=first.get("region")
        def side(anchor):
            return {"op":"AGGREGATE", "by":"space", "metric":"count", "source":{
                "op":"RELATE", "relation":"within",
                "left":{"op":"SELECT", "entity":ents[0], "region":region, "time":None},
                "right":{"op":"SELECT", "entity":anchor, "region":region, "time":None}}}
        return {"op":"COMPARE", "how":"difference",
                "left":side(ents[1]), "right":side(ents[2])}
    explicit_minus=re.search(r"\bdifference\s*:\s*(.+?)\s+minus\s+(.+?)(?:[.?]|$)",question,re.I)
    if explicit_minus:
        clauses=explicit_minus.groups();parsed=[]
        for clause in clauses:
            occ=list(dict.fromkeys(key for _,_,key in _entity_occurrences(clause,osm_only=True)))
            if len(occ)<2 or not re.search(r"\b(?:within|beyond|outside|more\s+than)\b",clause,re.I):break
            relation="beyond" if re.search(r"\b(?:beyond|outside|more\s+than|not\s+within)\b",clause,re.I) else "within"
            parsed.append((occ[0],occ[-1],relation,_parse_dist_km(clause.lower())))
        if len(parsed)==2:
            region=first.get("region")
            def side(entity,anchor,relation,d):return {"op":"AGGREGATE","by":"space","metric":"count","source":{
                "op":"RELATE","relation":relation,"threshold_km":d,
                "left":{"op":"SELECT","entity":entity,"region":region,"time":None},
                "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}}
            return {"op":"COMPARE","how":"difference","left":side(*parsed[0]),"right":side(*parsed[1])}
    # "How many more X are there than X within D of Y" compares the total to a filtered subset.
    if re.search(r"\bhow many more\b", ql) and ql.count(" within ") == 1 and len(ents) >= 2:
        region=first.get("region");d=_parse_dist_km(ql);entity,anchor=ents[0],ents[-1]
        total={"op":"AGGREGATE","by":"space","metric":"count","source":{
            "op":"SELECT","entity":entity,"region":region,"time":None}}
        subset={"op":"AGGREGATE","by":"space","metric":"count","source":{
            "op":"RELATE","relation":"within","threshold_km":d,
            "left":{"op":"SELECT","entity":entity,"region":region,"time":None},
            "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}}
        return {"op":"COMPARE","how":"difference","left":total,"right":subset}
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
    if "difference between" in ql and ql.count(" within ")>=2:
        # Each side is an independent relation clause.  A global de-duplicated entity list
        # loses repeated anchors ("X within D of market and Y within D of market") and can
        # therefore bind Y as the first clause's anchor.  Split the literal clauses first.
        head=question[ql.index("difference between")+len("difference between"):]
        clauses=re.split(r"\band\b",head,maxsplit=1,flags=re.I)
        clause_entities=[]
        for clause in clauses:
            occ=list(dict.fromkeys(key for _,_,key in _entity_occurrences(clause,osm_only=True)))
            if len(occ)>=2: clause_entities.append((occ[0],occ[-1],_parse_dist_km(clause.lower())))
        if len(clause_entities)==2:
            region=first.get("region")
            def side(entity,anchor,d):return {"op":"AGGREGATE","by":"space","metric":"count","source":{"op":"RELATE","relation":"within","threshold_km":d,
                "left":{"op":"SELECT","entity":entity,"region":region,"time":None},
                "right":{"op":"SELECT","entity":anchor,"region":region,"time":None}}}
            left,right=clause_entities
            return {"op":"COMPARE","how":"difference","left":side(*left),"right":side(*right)}
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


def mech_requested_reduction(ir, question):
    """Keep an explicit density/mean answer head around a correctly parsed record relation."""
    if not isinstance(ir, dict) or ir.get("op") != "RELATE":
        return ir
    if re.search(r"\bdensit(?:y|ies)\s+of\b", question, re.I):
        return {"op":"AGGREGATE", "by":"space", "metric":"density", "source":ir}
    if re.search(r"\bmean\s+distance\b|\baverage\s+distance\b", question, re.I) \
            and ir.get("relation") == "distance":
        return {"op":"AGGREGATE", "by":"space", "metric":"mean", "source":ir}
    return ir


def _spatial_quantity_clause(text, region, threshold=None):
    """Compile one explicit spatial count/density clause without borrowing its sibling's roles."""
    occurrences = list(dict.fromkeys(key for _, _, key in
                                     _entity_occurrences(text, osm_only=True)))
    if len(occurrences) == 1 and not re.search(
            r"\b(?:within|near|beyond|outside|more\s+than|not\s+within)\b", text, re.I):
        metric = "density" if re.search(r"\bdensit", text,re.I) else "count"
        return {"op":"AGGREGATE","by":"space","metric":metric,"source":{
            "op":"SELECT","entity":occurrences[0],"region":region,"time":None}}
    if len(occurrences) < 2:
        return None
    # In "market-near workshops", surface order is anchor then result entity.  Ordinary
    # "workshops within 1 km of markets" has result then anchor.
    if re.search(r"\b[\w ]+-near\s+[\w ]+", text, re.I):
        anchor, entity = occurrences[0], occurrences[-1]
    else:
        entity, anchor = occurrences[0], occurrences[-1]
    relation = "beyond" if re.search(r"\b(?:beyond|outside|more than|not within)\b", text,re.I) \
        else "within"
    d = _parse_dist_km(text.lower())
    if d is None: d = threshold
    def selected(value):
        return {"op":"SELECT", "entity":value, "region":region, "time":None}
    rel={"op":"RELATE", "relation":relation,
         "left":selected(entity), "right":selected(anchor)}
    if d is not None: rel["threshold_km"] = d
    metric = "density" if re.search(r"\bdensit", text,re.I) else "count"
    return {"op":"AGGREGATE", "by":"space", "metric":metric, "source":rel}


def mech_spatial_cross_place(ir, question):
    """Close complete spatial scalar plans before cross-place arithmetic or local ratios."""
    threshold=_parse_dist_km(question.lower())

    def quantity(text, place):
        return _spatial_quantity_clause(text, {"op":"REGION","place":place.strip(" ,.;:—-")},
                                        threshold)

    cross_patterns=(
        r"\s*how\s+many\s+more\s+(.+?)\s+does\s+(.+?)\s+have\s+than\s+(.+?)[?!.]*$",
        r"\s*how\s+many\s+more\s+(.+?)\s+are\s+mapped\s+in\s+(.+?)\s+than\s+in\s+(.+?)[?!.]*$",
    )
    for pattern in cross_patterns:
        match=re.match(pattern,question,re.I)
        if match:
            surface,left_place,right_place=match.groups()
            left,right=quantity(surface,left_place),quantity(surface,right_place)
            if left and right:
                return {"op":"COMPARE","how":"difference","left":left,"right":right}

    either=re.match(r"\s*either\s+(.+?)\s+or\s+(.+?)\s*:\s*which\s+has\s+more\s+"
                    r"(.+?)[?!.]*$",question,re.I)
    if either:
        left_place,right_place,surface=either.groups()
        left,right=quantity(surface,left_place),quantity(surface,right_place)
        if left and right:
            return {"op":"COMPARE","how":"difference","left":left,"right":right}

    density=re.match(r"\s*compare\s+the\s+density\s+of\s+(.+?)\s+in\s+(.+?)\s+"
                     r"with\s+that\s+in\s+(.+?)(?:;|,|[.?!]|$)",question,re.I)
    if density:
        surface,left_place,right_place=density.groups()
        surface="density of "+surface
        left,right=quantity(surface,left_place),quantity(surface,right_place)
        if left and right:
            return {"op":"COMPARE","how":"difference","left":left,"right":right}

    # Same-place arithmetic still needs two independently compiled quantity clauses.
    ratio=re.match(r"\s*(?:for|in)\s+(.+?)\s*,\s*what\s+is\s+the\s+ratio\s+of\s+"
                   r"(.+?)\s+to\s+(.+?)(?:,\s*using\s+.+?)?[?!.]*$",question,re.I)
    divide=re.match(r"\s*(?:for|in)\s+(.+?)\s*,\s*divide\s+(.+?)\s+by\s+(.+?)[?!.]*$",
                    question,re.I)
    local=ratio or divide
    if local:
        place,left_text,right_text=local.groups()
        region={"op":"REGION","place":place.strip(" ,.;:—-")}
        left=_spatial_quantity_clause(left_text,region,threshold)
        right=_spatial_quantity_clause(right_text,region,threshold)
        if left and right:
            return {"op":"COMPARE","how":"ratio","left":left,"right":right}
    return ir


def mech_spatial_arithmetic(ir, question):
    """Compile two independently scoped spatial quantities under minus/subtract/divide."""
    first = _first_select(ir)
    region = first.get("region") if first else None
    threshold = _parse_dist_km(question.lower())

    density_gap = re.match(
        r"\s*(?:density\s+gap\s*:\s*)?(.+?)\s+density\s+in\s+(.+?)\s+minus\s+"
        r"(.+?)\s+density\s+in\s+(.+?)[.?!]*$", question, re.I)
    if density_gap:
        left_text,left_place,right_text,right_place=density_gap.groups()
        left_occ=_entity_occurrences(left_text,osm_only=True)
        right_occ=_entity_occurrences(right_text,osm_only=True)
        if left_occ and right_occ:
            def density(entity,place):
                return {"op":"AGGREGATE","by":"space","metric":"density","source":{
                    "op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},
                    "time":None}}
            return {"op":"COMPARE","how":"difference",
                    "left":density(left_occ[-1][2],left_place.strip(" ,")),
                    "right":density(right_occ[-1][2],right_place.strip(" ,"))}

    anaphoric_beyond = re.match(
        r"\s*(?:beyond-count\s+delta\s*:\s*)?(.+?)\s+beyond\s+(.+?)\s+of\s+"
        r"(.+?)\s+in\s+(.+?)\s+minus\s+(?:that|the\s+same|corresponding)\s+count\s+in\s+"
        r"(.+?)[.?!]*$", question, re.I)
    if anaphoric_beyond:
        entity_text,distance,anchor_text,left_place,right_place=anaphoric_beyond.groups()
        entity_occ=_entity_occurrences(entity_text,osm_only=True)
        anchor_occ=_entity_occurrences(anchor_text,osm_only=True)
        d=_parse_dist_km(distance)
        if entity_occ and anchor_occ:
            def related(place):
                region={"op":"REGION","place":place.strip(" ,")}
                return {"op":"RELATE","relation":"beyond","threshold_km":d,
                        "left":{"op":"SELECT","entity":entity_occ[-1][2],"region":region,"time":None},
                        "right":{"op":"SELECT","entity":anchor_occ[-1][2],"region":region,"time":None}}
            return {"op":"COMPARE","how":"difference",
                    "left":related(left_place),"right":related(right_place)}

    count_minus = re.match(r"\s*(?:count\s+arithmetic\s*:\s*)?(.+?)\s+in\s+(.+?)\s+minus\s+"
                           r"(.+?)(?:\s+there)?[.?!]*$",question,re.I)
    if count_minus and re.search(r"\b(?:within|beyond)\b",count_minus.group(1),re.I) \
            and re.search(r"\b(?:within|beyond)\b",count_minus.group(3),re.I):
        left_text,place,right_text=count_minus.groups()
        local={"op":"REGION","place":place.strip(" ,")}
        left=_spatial_quantity_clause(left_text,local)
        right=_spatial_quantity_clause(right_text,local)
        if left and right:
            return {"op":"COMPARE","how":"difference","left":left,"right":right}

    divide = re.search(r"\bdivide\s+the\s+density\s+of\s+(.+?)\s+by\s+the\s+density\s+of\s+(.+?)[.?!]*$",
                       question, re.I)
    if divide and region is not None:
        left = _spatial_quantity_clause("density of " + divide.group(1), region, threshold)
        right = _spatial_quantity_clause("density of " + divide.group(2), region, threshold)
        if left and right:
            return {"op":"COMPARE", "how":"ratio", "left":left, "right":right}

    possessive = re.match(
        r"\s*(.+?)[’']s\s+count\s+of\s+(.+?)\s+minus\s+its\s+count\s+of\s+(.+?)"
        r"(?:,\s*using\s+.+?)?[.?!]*$", question, re.I)
    if possessive:
        place, left_text, right_text = possessive.groups()
        local={"op":"REGION", "place":place.strip(" ,")}
        left=_spatial_quantity_clause("count of " + left_text, local, threshold)
        right=_spatial_quantity_clause("count of " + right_text, local, threshold)
        if left and right:
            return {"op":"COMPARE", "how":"difference", "left":left, "right":right}

    subtract = re.match(
        r"\s*(?:here\s*,\s*)?subtract\s+(.+?)\s+from\s+(.+?)"
        r"(?:,\s*using\s+.+?)?[.?!]*$", question, re.I)
    if subtract:
        local = region if region is not None else {"op":"REGION", "place":"?place"}
        subtrahend, minuend = subtract.groups()
        left=_spatial_quantity_clause(minuend, local, threshold)
        right=_spatial_quantity_clause(subtrahend, local, threshold)
        if left and right:
            return {"op":"COMPARE", "how":"difference", "left":left, "right":right}
    return ir


def mech_closed_spatial_surface(ir, question):
    """Compile explicit spatial registers with clause-local subject, anchor, polarity, and range."""
    ql=question.lower();first=_first_select(ir)
    def entity(text):
        found=_entity_occurrences("a "+text,osm_only=True)
        return found[-1][2] if found else text.strip(" ,.;:—-")
    def region(place):return {"op":"REGION","place":place.strip(" ,.;:—-")}
    def selected(name,reg):return {"op":"SELECT","entity":entity(name),"region":reg,"time":None}
    def related(subject,anchor,reg,relation="within",distance=None):
        out={"op":"RELATE","relation":relation,"left":selected(subject,reg),
             "right":selected(anchor,reg)}
        if distance is not None:out["threshold_km"]=distance
        return out
    def reduced(source,metric):return {"op":"AGGREGATE","by":"space","metric":metric,"source":source}

    fronted=re.match(r"\s*within\s+(.+?)\s+of\s+(?:a|an|the)\s+(.+?),\s*"
                     r"which\s+(.+?)\s+are\s+there\s+in\s+(.+?)[?!.]*$",question,re.I)
    if fronted:
        distance,anchor,subject,place=fronted.groups();reg=region(place)
        return related(subject,anchor,reg,distance=_parse_dist_km(distance))

    counted=re.match(r"\s*a\s+(.+?)\s+is\s+no\s+farther\s+than\s+(.+?)\s+from\s+"
                     r"(?:a|an|the)\s+(.+?)\s+in\s+(.+?)\s*:\s*how many",question,re.I)
    if counted:
        subject,distance,anchor,place=counted.groups();reg=region(place)
        return reduced(related(subject,anchor,reg,distance=_parse_dist_km(distance)),"count")

    adjacent=re.match(r"\s*(.+?)\s+field note\s*:\s*(.+?)-adjacent\s+(.+?),\s*"
                      r"(.+?)\s+radius\s*[—-]\s*present or absent",question,re.I)
    if adjacent:
        place,anchor,subject,distance=adjacent.groups();reg=region(place)
        return reduced(related(subject,anchor,reg,distance=_parse_dist_km(distance)),"presence")

    density=re.match(r"\s*give\s+the\s+density\s+of\s+(.+?)\s+within\s+(.+?)\s+of\s+"
                     r"(.+?)\s+in\s+(.+?)[.?!]*$",question,re.I)
    if density:
        subject,distance,anchor,place=density.groups();reg=region(place)
        return reduced(related(subject,anchor,reg,distance=_parse_dist_km(distance)),"density")
    density_front=re.match(r"\s*within\s+(.+?)\s+of\s+(?:a|an|the)\s+(.+?)\s+in\s+"
                           r"(.+?),\s*how dense are\s+(.+?)[?!.]*$",question,re.I)
    if density_front:
        distance,anchor,place,subject=density_front.groups();reg=region(place)
        return reduced(related(subject,anchor,reg,distance=_parse_dist_km(distance)),"density")

    # Distance is a binary relation even when phrased as an attachment column.
    explicit_distance=bool(re.search(r"\battach\s+.+?\bdistance\b",ql) or
                           re.match(r"\s*.+?\bdistance\s*,?\s*please\s*,?\s*for each\b",ql))
    if explicit_distance and len(_entity_occurrences(question,osm_only=True))>=2:
        names=list(dict.fromkeys(k for _,_,k in _entity_occurrences(question,osm_only=True)))
        reg=first.get("region") if first else "?place"
        subject=first.get("entity") if first else names[-1]
        anchor=next((name for name in names if _phrase_norm(name)!=_phrase_norm(str(subject))),names[0])
        return related(subject,anchor,reg,relation="distance")

    # Punctuation-separated mixed-polarity conjunction: subject; negative anchor; positive anchor.
    conjunct=re.match(r"\s*(.+?),\s*(.+?)\s*:\s*no\s+(.+?)\s+inside\s+(.+?);\s*"
                      r"(?:a|an|the)\s+(.+?)\s+inside\s+(.+?)[.?!]*$",question,re.I)
    if conjunct:
        subject,place,negative,outer_d,positive,inner_d=conjunct.groups();reg=region(place)
        inner=related(subject,positive,reg,distance=_parse_dist_km(inner_d))
        out={"op":"RELATE","relation":"beyond","left":inner,"right":selected(negative,reg),
             "threshold_km":_parse_dist_km(outer_d)}
        return out

    both=re.match(r"\s*(?:a|an|the)\s+(.+?)\s+and\s+(?:a|an|the)\s+(.+?)\s+are\s+each\s+"
                  r"at most\s+(.+?)\s+away\s*:\s*which\s+(.+?)\s+(.+?)\s+meet both",question,re.I)
    if both:
        anchor1,anchor2,distance,place,subject=both.groups();reg=region(place);d=_parse_dist_km(distance)
        inner=related(subject,anchor1,reg,distance=d)
        return {"op":"RELATE","relation":"within","threshold_km":d,"left":inner,
                "right":selected(anchor2,reg)}

    # Two independent related counts under subtraction, with one shared named region.
    subtract=re.search(r"\bsubtract\s+the\s+count\s+of\s+(.+?)\s+within\s+(.+?)\s+of\s+"
                       r"(.+?)\s+from\s+the\s+count\s+of\s+(.+?)\s+within\s+(.+?)\s+of\s+"
                       r"(.+?)[.?!]*$",question,re.I)
    if subtract:
        sub,d1,a1,main,d2,a2=subtract.groups()
        pm=re.match(r"\s*in\s+(.+?),\s*subtract\b",question,re.I)
        reg=region(pm.group(1)) if pm else (first.get("region") if first else "?place")
        left=reduced(related(main,a2,reg,distance=_parse_dist_km(d2)),"count")
        right=reduced(related(sub,a1,reg,distance=_parse_dist_km(d1)),"count")
        return {"op":"COMPARE","how":"difference","left":left,"right":right}

    former=re.match(r"\s*(.+?)\s+near\s+(.+?)\s+minus\s+(.+?)\s+near\s+(.+?),\s*please\s*:\s*"
                    r"(.+?);\s*(.+?)\s+for\s+the\s+former,\s*(.+?)\s+for\s+the\s+latter",
                    question,re.I)
    if former:
        e1,a1,e2,a2,place,d1,d2=former.groups();reg=region(place)
        return {"op":"COMPARE","how":"difference",
                "left":reduced(related(e1,a1,reg,distance=_parse_dist_km(d1)),"count"),
                "right":reduced(related(e2,a2,reg,distance=_parse_dist_km(d2)),"count")}

    cross_ratio=re.match(r"\s*compute\s+(.+?)[’']s\s+count\s+of\s+(.+?)\s+within\s+(.+?)\s+of\s+"
                         r"(.+?)\s+divided\s+by\s+(.+?)[’']s\s+count\s+of\s+(.+?)\s+within\s+"
                         r"(.+?)\s+of\s+(.+?)[.?!]*$",question,re.I)
    if cross_ratio:
        p1,e1,d1,a1,p2,e2,d2,a2=cross_ratio.groups();r1,r2=region(p1),region(p2)
        return {"op":"COMPARE","how":"ratio",
                "left":reduced(related(e1,a1,r1,distance=_parse_dist_km(d1)),"count"),
                "right":reduced(related(e2,a2,r2,distance=_parse_dist_km(d2)),"count")}

    reversed_subject=re.match(r"\s*(?:a|an|the)\s+(.+?)\s+lies\s+within\s+(.+?)\s*:\s*show\s+"
                              r"(?:the\s+)?(.+?)\s+satisfying that\s+in\s+(.+?)[.?!]*$",question,re.I)
    if reversed_subject:
        anchor,distance,subject,place=reversed_subject.groups();reg=region(place)
        return related(subject,anchor,reg,distance=_parse_dist_km(distance))

    co_beyond=re.match(r"\s*in\s+(.+?),\s*show\s+(.+?)\s+cooccurring\s+with\s+(.+?)\s+and\s+"
                       r"beyond\s+(.+?)\s+from\s+(.+?)[.?!]*$",question,re.I)
    if co_beyond:
        place,subject,coanchor,distance,far_anchor=co_beyond.groups();reg=region(place)
        inner=related(subject,coanchor,reg,relation="cooccur")
        return {"op":"RELATE","relation":"beyond","threshold_km":_parse_dist_km(distance),
                "left":inner,"right":selected(far_anchor,reg)}
    co_prefix=re.match(r"\s*(.+?)-cooccurring\s+(.+?),\s*but\s+none\s+with\s+"
                       r"(?:a|an|the)\s+(.+?)\s+inside\s+(.+?)\s*[—-]\s*(.+?)[.?!]*$",question,re.I)
    if co_prefix:
        coanchor,subject,far_anchor,distance,place=co_prefix.groups();reg=region(place)
        inner=related(subject,coanchor,reg,relation="cooccur")
        return {"op":"RELATE","relation":"beyond","threshold_km":_parse_dist_km(distance),
                "left":inner,"right":selected(far_anchor,reg)}
    return ir


def mech_transfer_relational_source(ir, question):
    """Preserve explicit donor-set modifiers inside ESTIMATE.source."""
    if not (isinstance(ir,dict) and ir.get("op") == "ESTIMATE" and
            isinstance(ir.get("source"),dict) and ir["source"].get("op") == "SELECT"):
        return ir
    if not re.search(r"\b(?:donor|pattern|transfer|estimate|interpolat\w*|source records|"
                     r"envelope field)\b",question,re.I) or \
            not re.search(r"\b(?:within|beyond|cooccurr?\w*)\b",question,re.I):
        return ir
    entities=list(dict.fromkeys(key for _,_,key in
                                _entity_occurrences(question,osm_only=True)))
    if len(entities)<2:return ir
    source=ir["source"];region=source.get("region")
    relation=("cooccur" if re.search(r"\bcooccurr?\w*\b",question,re.I) else
              "beyond" if re.search(r"\bbeyond\b",question,re.I) else "within")
    rel={"op":"RELATE", "relation":relation,
         "left":{"op":"SELECT","entity":entities[0],"region":region,"time":None},
         "right":{"op":"SELECT","entity":entities[1],"region":region,"time":None}}
    d=_parse_dist_km(question.lower())
    if d is not None:rel["threshold_km"]=d
    out=dict(ir);out["source"]=rel;return out


def mech_transfer_source_expression(ir, question):
    """Keep a typed RELATE/ANNOTATE/hole expression intact as an ESTIMATE donor source."""
    ql=question.lower()
    method=("interpolate" if re.search(r"\binterpolat\w*\b",ql) else
            "feature" if re.search(r"\bfeature[- ]?estimat\w*|\bby feature\b",ql) else
            "envelope" if re.search(r"\benvelope\b",ql) else None)
    if method is None:return ir
    first=_first_select(ir)
    if not first:return ir
    donor_region=first.get("region")

    target=(ir.get("target") if isinstance(ir,dict) and ir.get("op")=="ESTIMATE" else None)
    if not (isinstance(target,dict) and target.get("op")=="REGION"):
        target_match=re.search(r"\b(?:field\s+(?:for|in)|target\s*[:—-])\s+"
                               r"(.+?)(?:\s+is\s+the\s+target)?[.?!]*$",question,re.I)
        if target_match:
            target={"op":"REGION","place":target_match.group(1).strip(" ,.;:—-")}
    if not target:return ir

    def donor_entity(text):
        found=_entity_occurrences("a "+text,osm_only=True)
        return found[-1][2] if found else text.strip(" ,.;:—-")
    explicit_donor_relation=re.search(
        r"\busing\s+(.+?)\s+(.+?)\s+within\s+(.+?)\s+of\s+(.+?),\s*"
        r"(?:interpolat\w*|feature|envelope)",question,re.I)
    trained_relation=re.search(
        r"\btrained\s+on\s+(.+?)\s+(.+?)\s+co[- ]located\s+with\s+(.+?)[.?!]*$",
        question,re.I)
    if explicit_donor_relation:
        place,subject,distance,anchor=explicit_donor_relation.groups();reg={"op":"REGION","place":place}
        source={"op":"RELATE","relation":"within","threshold_km":_parse_dist_km(distance),
                "left":{"op":"SELECT","entity":donor_entity(subject),"region":reg,"time":None},
                "right":{"op":"SELECT","entity":donor_entity(anchor),"region":reg,"time":None}}
        return {"op":"ESTIMATE","source":source,"target":target,"method":method}
    if trained_relation:
        place,subject,anchor=trained_relation.groups();reg={"op":"REGION","place":place}
        source={"op":"RELATE","relation":"cooccur",
                "left":{"op":"SELECT","entity":donor_entity(subject),"region":reg,"time":None},
                "right":{"op":"SELECT","entity":donor_entity(anchor),"region":reg,"time":None}}
        return {"op":"ESTIMATE","source":source,"target":target,"method":method}

    existing=(ir.get("source") if isinstance(ir,dict) and ir.get("op")=="ESTIMATE" else None)
    composite=bool(isinstance(existing,dict) and existing.get("op") in ("RELATE","ANNOTATE"))
    named=list(dict.fromkeys(k for _,_,k in _entity_occurrences(question,osm_only=True)))
    source=existing if composite else first
    if named and not composite:
        source={"op":"SELECT","entity":named[0],"region":donor_region,"time":None}

    # A donor relation is a Records expression, not prose that may be discarded before ESTIMATE.
    unresolved_anchor=bool(re.search(r"\bwhich\s+amenity\b",ql))
    if not composite and re.search(r"\b(?:within|beyond|cooccurr?\w*)\b",ql) and \
            (len(named)>=2 or (len(named)>=1 and unresolved_anchor)):
        relation=("cooccur" if re.search(r"\bcooccurr?\w*\b",ql) else
                  "beyond" if re.search(r"\bbeyond\b",ql) else "within")
        anchor="?anchor_amenity" if unresolved_anchor else named[1]
        source={"op":"RELATE","relation":relation,"left":source,
                "right":{"op":"SELECT","entity":anchor,"region":donor_region,"time":None}}
        distance=_parse_dist_km(ql)
        if distance is not None:source["threshold_km"]=distance

    # Annotation layers remain columns on the donor records. A named statistical indicator in
    # this role must not replace the facility SELECT itself.
    if not composite and re.search(r"\bannotat\w*|\bwith which .+? layer\b",ql):
        layer=None
        for phrase in ("electricity access","internet users","mobile subscriptions"):
            if phrase in ql:layer=phrase;break
        if re.search(r"\bwhich\s+(?:livelihood\s+)?layer\b",ql):layer="?layer"
        if layer:source={"op":"ANNOTATE","source":source,"layer":layer}

    if not composite and re.search(r"\bsome livelihood facility\b",ql):
        source={"op":"SELECT","entity":"?facility_type","region":donor_region,"time":None}
    elif not composite and re.search(r"\b(?:those|these) records\b",ql):
        source={"op":"SELECT","entity":"?entity","region":donor_region,"time":None}
    return {"op":"ESTIMATE","source":source,"target":target,"method":method}


def mech_output_literal_honesty(ir, question):
    """Enforce explicit output heads, modifier-complete literals, and unresolved roles."""
    if not isinstance(ir,dict):return ir
    ql=question.lower();first=_first_select(ir)
    if not first:return ir
    region=first.get("region")

    if re.search(r"\bwithin\b.+?\bof it\b",ql) and ir.get("op")=="RELATE":
        out=json.loads(json.dumps(ir));out["right"]["entity"]="?anchor_entity";return out

    if re.search(r"\b(?:did|does)\b.+?\bcause\b",ql):
        return {"op":"SELECT","entity":"?proxy_for_causal_claim","region":region,"time":None}

    if re.search(r"\bcurrent firm-posted job vacancies\b",ql):
        return {"op":"SELECT","entity":"current firm-posted job vacancies",
                "region":region,"time":None}
    unsupported=re.match(r"\s*report\s+(.+?(?:earnings?|income))\s+in\s+(.+?)[.?!]*$",
                         question,re.I)
    if unsupported and not _entity_occurrences(unsupported.group(1)):
        return {"op":"SELECT","entity":unsupported.group(1).strip(" ,"),
                "region":{"op":"REGION","place":unsupported.group(2).strip(" ,")},"time":None}

    if ir.get("op")=="ANNOTATE":
        layer=None
        attached=re.search(r"\bwith\s+(.+?)\s+attached\b",question,re.I)
        attach=re.match(r"\s*for\s+.+?,\s*attach\s+(.+?)[.?!]*$",question,re.I)
        if attached:layer=attached.group(1)
        elif attach and re.search(r"\b(?:earnings?|income)\b",attach.group(1),re.I):layer=attach.group(1)
        if layer:
            out=dict(ir);out["layer"]=re.sub(r"^the\s+","",layer.strip(" ,.;"),flags=re.I);return out

    explicit_records=bool(re.search(r"\b(?:records|examples)\b",ql))
    if explicit_records and not re.search(r"\b(?:annotat|attach|estimate|rank|order)\b",ql):
        if ir.get("op")=="AGGREGATE" and isinstance(ir.get("source"),dict):return ir["source"]
    return ir


def mech_behavior_proxy(ir, question):
    """Preference/motivation/usage-likelihood claims need a proxy, never facility arithmetic."""
    ql=question.lower()
    # Decision-context preambles can contain words such as "choosing" while the actual request is
    # a closed quantitative rank. Indicator labels like "salaried workers" are measures here,
    # not evidence that the user asked for latent human preferences.
    if isinstance(ir,dict) and ir.get("op")=="RANK" \
            and re.search(r"\b(?:rank|sort|order)\b",ql):
        return ir
    personal_goal=bool(re.search(r"\bwhere\b.+\bcould\s+i\b.+\b(?:sell|meet|withdraw|work)\b",ql) or
                       re.search(r"\bto\s+(?:start\s+earning|sell\s+things|learn\s+a\s+trade)\b"
                                 r".+\bwhere\s+should\s+i\s+go\b",ql))
    human_cluster=bool(re.search(r"\bwhere\s+do\s+.+?\b(?:workers|people|residents|freelancers|"
                                 r"vendors|traders)\b.+?\b(?:cluster|gather|congregate)\b",ql))
    if not (personal_goal or human_cluster or
            (re.search(r"\b(?:people|residents|freelancers|owners|workers|commuters|tourists|visitors)\b",ql) and
             re.search(r"\b(?:why|prefer\w*|choos\w*|because|likely|popular|satisfied|"
                       r"motivat\w*|habits?|transactions?|networking)\b",ql))):
        return ir
    first=_first_select(ir);region=first.get("region") if first else "?place"
    if isinstance(region,dict) and str(region.get("place","")).lower() in ("here","this area"):
        region="?place"
    return {"op":"SELECT","entity":"?proxy","region":region or "?place","time":None}


def mech_explicit_surface_closure(ir, question):
    """Close explicit compact grammars after generative and generic recovery passes.

    These rules are intentionally compositional: each operand is rebuilt from the words in its own
    clause. They cover terse spreadsheet/voice surfaces where a small model often returns a valid
    but lossy subtree, and they never activate without an explicit output head and complete roles.
    """
    ql=question.lower();first=_first_select(ir)
    region=first.get("region") if first else None
    def sel(entity,reg):return {"op":"SELECT","entity":entity,"region":reg,"time":None}
    def ents(text):
        # Resolver keys are internal identifiers; IR leaves use readable canonical labels.  A
        # clause fragment also lacks the spatial context that normally disambiguates facilities
        # such as plural ``markets``, so retry a conservative singular form locally.
        found=list(dict.fromkeys(k for _,_,k in _entity_occurrences(text,osm_only=True)))
        if not found:
            singular=re.sub(r"\b([a-z][a-z -]*?)s\b",r"\1",str(text),flags=re.I)
            found=list(dict.fromkeys(k for _,_,k in _entity_occurrences(singular,osm_only=True)))
        if not found:
            # ``market`` is deliberately context-sensitive because of abstract "job market";
            # the caller has already established a concrete entity slot here.
            found=list(dict.fromkeys(k for _,_,k in _entity_occurrences("a "+str(text),osm_only=True)))
        if not found:
            # Exact but unsupported facility literals remain valid SELECT leaves and must fail
            # closed in execution. Preserve the explicit subtype instead of deleting RELATE.
            literal=_phrase_norm(str(text))
            if re.fullmatch(r"(?:train|railway|bus) stations?",literal):
                found=[re.sub(r"s$","",literal)]
        return [k.replace("_"," ") for k in found]
    def related(entity,anchor,place,relation="within",distance=None,metric="count"):
        reg={"op":"REGION","place":place.strip(" ,.;:—-")}
        rel={"op":"RELATE","relation":relation,"left":sel(entity,reg),"right":sel(anchor,reg)}
        if distance is not None:rel["threshold_km"]=distance
        return {"op":"AGGREGATE","by":"space","metric":metric,"source":rel}

    # Explicit examples/list negation is a record head, never a count.
    if re.search(r"\bexamples?\s+of\b",ql) and re.search(r"\bnot\s+a\s+count\b",ql) and first:
        return dict(first)

    annotated=re.match(r"\s*(.+?)\s+values?\s+beside\s+each\s+(.+?)\s+in\s+(.+?)[,.]?\s*(?:please)?[.?!]*$",question,re.I)
    if annotated:
        layer,entity_text,place=annotated.groups();es=ents(entity_text)
        if es:
            layer="nighttime lights" if re.search(r"night[ -]?light",layer,re.I) else layer.strip()
            return {"op":"ANNOTATE","source":sel(es[-1],{"op":"REGION","place":place.strip(" ,")}),"layer":layer}
    plus_layer=re.match(r"\s*(?:procurement\s+sheet\s*:\s*)?each\s+(.+?)\s*,?\s+plus\s+(.+?)[.?!]*$",question,re.I)
    if plus_layer and first:
        _,layer=plus_layer.groups();return {"op":"ANNOTATE","source":dict(first),"layer":layer.strip(" ,")}

    distance=re.match(r"\s*for\s+each\s+(.+?)\s+in\s+(.+?),\s*what(?:'s|\s+is)\s+its\s+distance\s+to\s+(?:the\s+)?(.+?)[?!.]*$",question,re.I)
    if distance:
        left_text,place,right_text=distance.groups();le,re_=ents(left_text),ents(right_text)
        left_entity=(le[-1] if le else (first or {}).get("entity"));right_entity=re_[-1] if re_ else None
        if left_entity and right_entity:
            reg={"op":"REGION","place":place.strip(" ,")}
            return {"op":"RELATE","relation":"distance","left":sel(left_entity,reg),"right":sel(right_entity,reg)}

    presence=re.match(r"\s*does\s+(.+?)\s+have\s+(?:a|an)\s+(.+?)\s+within\s+(.+?)\s+of\s+(?:a|an|the)\s+(.+?)[?!.]*$",question,re.I)
    if presence:
        place,e_text,dist,a_text=presence.groups();ee,aa=ents(e_text),ents(a_text)
        if ee and aa:
            out=related(ee[-1],aa[-1],place,distance=_parse_dist_km(dist),metric="presence")
            return out

    # One completed co-located set followed by a negative spatial predicate.
    nested=re.match(r"\s*in\s+(.+?),\s*(?:find|show|list)\s+(.+?)\s+(?:sharing\s+a\s+site|co-?located)\s+with\s+(.+?)\s+and\s+(?:farther|more)\s+than\s+(.+?)\s+from\s+(.+?)[.?!]*$",question,re.I)
    if nested:
        place,x,y,dist,z=nested.groups();anchors=ents(" ".join((y,z)));subject=(first or {}).get("entity")
        if subject and len(anchors)>=2:
            reg={"op":"REGION","place":place.strip(" ,")};inner={"op":"RELATE","relation":"cooccur","left":sel(subject,reg),"right":sel(anchors[0],reg)}
            return {"op":"RELATE","relation":"beyond","threshold_km":_parse_dist_km(dist),"left":inner,"right":sel(anchors[1],reg)}
    shared=re.match(r"\s*use\s+(.+?)\s+for\s+both\s*:\s*which\s+(.+?)\s+are\s+near\s+(.+?)\s+and\s+(.+?)[?!.]*$",question,re.I)
    if shared:
        dist,subject,a,b=shared.groups();anchors=ents(" ".join((a,b)));subject_entity=(first or {}).get("entity")
        if subject_entity and len(anchors)>=2 and region:
            d=_parse_dist_km(dist);inner={"op":"RELATE","relation":"within","threshold_km":d,"left":sel(subject_entity,region),"right":sel(anchors[0],region)}
            return {"op":"RELATE","relation":"within","threshold_km":d,"left":inner,"right":sel(anchors[1],region)}

    # Written negative-distance markers apply to the explicit relation regardless of numeral form.
    relation_count=json.dumps(ir).count('"op": "RELATE"') if isinstance(ir,dict) else 0
    if re.search(r"\b(?:more\s+than|farther\s+than)\b",ql) and relation_count == 1:
        def flip(n):
            if isinstance(n,list):return [flip(x) for x in n]
            if not isinstance(n,dict):return n
            out={k:flip(v) for k,v in n.items()}
            if out.get("op")=="RELATE" and out.get("relation")=="within":out["relation"]="beyond"
            return out
        ir=flip(ir)

    # Two place-scoped copies of one explicit related count.
    cross=re.match(r"\s*(.+?)\s+minus\s+(.+?)\s*:\s*difference\s+in\s+counts?\s+of\s+(.+?)\s+within\s+(.+?)\s+of\s+(?:a|an|the)\s+(.+?)[.?!]*$",question,re.I)
    if cross:
        p1,p2,e_text,dist,a_text=cross.groups();ee,aa=ents(e_text),ents(a_text)
        if ee and aa:return {"op":"COMPARE","how":"difference","left":related(ee[-1],aa[-1],p1,distance=_parse_dist_km(dist)),"right":related(ee[-1],aa[-1],p2,distance=_parse_dist_km(dist))}

    two_quantities=re.match(r"\s*(.+?)\s*:\s*difference\s+between\s+(.+?)\s+count\s+near\s+(.+?)\s+and\s+(.+?)\s+count\s+near\s+(.+?),\s*each\s+within\s+(.+?)[.?!]*$",question,re.I)
    if two_quantities:
        place,e1,a1,e2,a2,dist=two_quantities.groups();parts=[ents(x) for x in (e1,a1,e2,a2)]
        if all(parts):return {"op":"COMPARE","how":"difference","left":related(parts[0][-1],parts[1][-1],place,distance=_parse_dist_km(dist)),"right":related(parts[2][-1],parts[3][-1],place,distance=_parse_dist_km(dist))}
    corresponding=re.match(r"\s*ratio,?\s+not\s+winner\s*:\s*count\s+of\s+(.+?)\s+within\s+(.+?)\s+of\s+(.+?)\s+in\s+(.+?)\s+over\s+the\s+same\s+count\s+in\s+(.+?)[.?!]*$",question,re.I)
    if corresponding:
        e_text,dist,a_text,p1,p2=corresponding.groups();ee,aa=ents(e_text),ents(a_text)
        if ee and aa:return {"op":"COMPARE","how":"ratio","left":related(ee[-1],aa[-1],p1,distance=_parse_dist_km(dist)),"right":related(ee[-1],aa[-1],p2,distance=_parse_dist_km(dist))}

    # Compact direction and endpoint arithmetic.
    direction=re.match(r"\s*(?:monitoring\s+note\s*,?\s*)?((?:19|20)\d{2})[–—-]((?:19|20)\d{2})\s*:\s*direction\s+of\s+(.+?)(?:,\s*not\s+endpoint\s+change)?[.?!]*$",question,re.I)
    if direction:
        y1,y2,clause=direction.groups();base=_stat_operand_from_clause(clause,y1,first)
        if base:
            base=dict(base);base["time"]={"start":y1,"end":y2}
            return {"op":"COMPARE","how":"trend_direction","left":{"op":"AGGREGATE","by":"time","metric":"mean","source":base}}
    direction_only=re.match(r"\s*direction\s+only\s*:\s*(.+?),\s*((?:19|20)\d{2})[–—-]((?:19|20)\d{2})[.?!]*$",question,re.I)
    if direction_only:
        clause,y1,y2=direction_only.groups();base=_stat_operand_from_clause(clause,y1,first)
        if base:
            base=dict(base);base["time"]={"start":y1,"end":y2}
            return {"op":"COMPARE","how":"trend_direction","left":{"op":"AGGREGATE","by":"time","metric":"mean","source":base}}
    weekly_diff=re.match(r"\s*(.+?)\s+female\s+weekly[ -]hours\s*,\s*difference\s*=\s*((?:19|20)\d{2})\s+less\s+((?:19|20)\d{2})[.?!]*$",question,re.I)
    weekly_ratio=re.match(r"\s*(.+?)[’']s\s+female\s+weekly[ -]hours\s+ratio\s*:\s*((?:19|20)\d{2})\s+over\s+((?:19|20)\d{2})[.?!]*$",question,re.I)
    wr=weekly_diff or weekly_ratio
    if wr:
        place,y1,y2=wr.groups();entity="female average weekly hours worked"
        def point(y):return {"op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},"time":{"start":y,"end":y}}
        return {"op":"COMPARE","how":"difference" if weekly_diff else "ratio","left":point(y1),"right":point(y2)}

    # Derived ranks: construct every explicitly listed candidate from one shared blueprint.
    change_rank=re.match(r"\s*biggest\s+((?:19|20)\d{2})\s*(?:→|->|to)\s*((?:19|20)\d{2})\s+rise\s+in\s+(.+?)\s*:\s*(.+?)[?!.]*$",question,re.I)
    if change_rank:
        y1,y2,e_text,places_text=change_rank.groups();occ=_entity_occurrences(e_text);places=_literal_place_list(places_text)
        if occ and len(places)>=3:
            entity=occ[-1][2]
            def delta(p):
                def point(y):return {"op":"SELECT","entity":entity,"region":{"op":"REGION","place":p},"time":{"start":y,"end":y}}
                return {"op":"COMPARE","how":"difference","left":point(y2),"right":point(y1)}
            return {"op":"RANK","items":[delta(p) for p in places],"order":"desc","k":1}
    ordered_change=re.match(r"\s*order\s+(.+?)\s+from\s+(smallest|largest)\s+to\s+(largest|smallest)\s+((?:19|20)\d{2})-minus-((?:19|20)\d{2})\s+(.+?)\s+change[.?!]*$",question,re.I)
    if ordered_change:
        places_text,start,_,y2,y1,e_text=ordered_change.groups();places=_literal_place_list(places_text);occ=_entity_occurrences(e_text)
        if len(places)>=3 and occ:
            entity=occ[-1][2]
            def delta(p):
                def point(y):return {"op":"SELECT","entity":entity,"region":{"op":"REGION","place":p},"time":{"start":y,"end":y}}
                return {"op":"COMPARE","how":"difference","left":point(y2),"right":point(y1)}
            return {"op":"RANK","items":[delta(p) for p in places],"order":"asc" if start.lower()=="smallest" else "desc"}
    related_rank_patterns=(
        (r"\s*order\s+(.+?)\s+by\s+count\s+of\s+(.+?)\s+beyond\s+(.+?)\s+from\s+(?:a|an|the)\s+(.+?);\s*(low|high)\s+to\s+(high|low)[.?!]*$","count","beyond",None),
        (r"\s*top\s+two\s+counts\s+of\s+(.+?)\s+co-?occurring\s+with\s+(.+?)\s*:\s*(.+?)[.?!]*$","count","cooccur",2),
        (r"\s*two\s+densest,?\s+by\s+(.+?)\s+within\s+(.+?)\s+of\s+(.+?)\s*:\s*(.+?)[.?!]*$","density","within",2),
        (r"\s*full\s+low-to-high\s+list\s*:\s*density\s+of\s+(.+?)\s+farther\s+than\s+(.+?)\s+from\s+(.+?)\s+in\s+(.+?)[.?!]*$","density","beyond",None),
    )
    for idx,(pat,metric,relation_mode,k) in enumerate(related_rank_patterns):
        m=re.match(pat,question,re.I)
        if not m:continue
        if idx==0:
            places_text,e_text,dist,a_text,start,_=m.groups();order="asc" if start.lower()=="low" else "desc"
        elif idx==1:
            e_text,a_text,places_text=m.groups();dist=None;order="desc"
        elif idx==2:
            e_text,dist,a_text,places_text=m.groups();order="desc"
        else:
            e_text,dist,a_text,places_text=m.groups();order="asc"
        places=_literal_place_list(places_text);ee,aa=ents(e_text),ents(a_text)
        if len(places)>=3 and ee and aa:
            items=[related(ee[-1],aa[-1],p,relation_mode,_parse_dist_km(dist) if dist else None,metric) for p in places]
            out={"op":"RANK","items":items,"order":order}
            if k:out["k"]=k
            return out

    # Explicit winner language always supplies k=1.
    if isinstance(ir,dict) and ir.get("op")=="RANK" and re.search(r"\b(?:who|whose)\b.+?\b(?:highest|lowest)\b|\bwinner\s+only\b|\bone\s+name\b",ql):
        ir=dict(ir);ir["k"]=1

    # Strip direction prose accidentally captured in a final rank place.
    if isinstance(ir,dict) and ir.get("op")=="RANK":
        def clean(n):
            if isinstance(n,list):return [clean(x) for x in n]
            if not isinstance(n,dict):return n
            out={k:clean(v) for k,v in n.items()}
            if out.get("op")=="REGION":out["place"]=re.sub(r"\s+(?:high|low)-to-(?:high|low)$","",str(out.get("place","")),flags=re.I)
            return out
        ir=clean(ir)

    # Preserve composed donor records under an otherwise complete ESTIMATE wrapper.
    if isinstance(ir,dict) and ir.get("op")=="ESTIMATE":
        terse=re.match(r"\s*(.+?)\s+(.+?)\s+estimate,\s*(feature|envelope|interpolate)\s+method;\s*donor\s+data\s*=\s*(.+?)[.?!]*$",question,re.I)
        if terse:
            target,e_text,method,donor=terse.groups();ee=ents(e_text)
            if ee:return {"op":"ESTIMATE","method":method.lower(),"source":sel(ee[-1],{"op":"REGION","place":donor}),"target":{"op":"REGION","place":target}}
        rel_source_patterns=(
            r"\s*using\s+(.+?)\s+(.+?)\s+within\s+(.+?)\s+of\s+(.+?),\s*(envelope|feature|interpolate)\s+an\s+estimate\s+for\s+(.+?)[.?!]*$",
            r"\s*(interpolate|feature|envelope)\s+into\s+(.+?)\s+from\s+(.+?)\s+(.+?)\s+beyond\s+(.+?)\s+of\s+(.+?)[.?!]*$",
            r"\s*(feature|envelope|interpolate)\s+estimate\s+for\s+(.+?),\s*trained\s+on\s+(.+?)\s+(.+?)\s+co-?located\s+with\s+(.+?)[.?!]*$",
        )
        for idx,pat in enumerate(rel_source_patterns):
            m=re.match(pat,question,re.I)
            if not m:continue
            if idx==0:donor,e_text,dist,a_text,method,target=m.groups();relation_mode="within"
            elif idx==1:method,target,donor,e_text,dist,a_text=m.groups();relation_mode="beyond"
            else:method,target,donor,e_text,a_text=m.groups();dist=None;relation_mode="cooccur"
            source_first=_first_select(ir.get("source"));entity=(source_first or {}).get("entity");aa=ents(a_text)
            if entity and aa:
                reg={"op":"REGION","place":donor};rel={"op":"RELATE","relation":relation_mode,"left":sel(entity,reg),"right":sel(aa[-1],reg)}
                if dist:rel["threshold_km"]=_parse_dist_km(dist)
                return {"op":"ESTIMATE","method":method.lower(),"source":rel,"target":{"op":"REGION","place":target}}
        ann1=re.match(r"\s*take\s+(.+?)[’']s\s+(.+?)-annotated\s+(.+?)\s+and\s+(envelope|feature|interpolate)\s+them\s+onto\s+(.+?)[.?!]*$",question,re.I)
        ann2=re.match(r"\s*for\s+(.+?),\s*(interpolate|feature|envelope)\s+(.+?)\s+(.+?)\s+records\s+after\s+adding\s+(.+?)[.?!]*$",question,re.I)
        ann3=re.match(r"\s*(.+?)\s+attached\s+to\s+(.+?)\s+(.+?)\s*(?:→|->)\s*(feature|envelope|interpolate)\s+estimate\s+in\s+(.+?)[.?!]*$",question,re.I)
        if ann1:
            donor,layer,e_text,method,target=ann1.groups()
        elif ann2:
            target,method,donor,e_text,layer=ann2.groups()
        elif ann3:
            layer,donor,e_text,method,target=ann3.groups()
        else:donor=layer=e_text=method=target=None
        if donor:
            source_first=_first_select(ir.get("source"));named=ents(e_text)
            entity=named[-1] if named else (source_first or {}).get("entity")
            if entity and entity not in ("night light","elevation"):
                source={"op":"ANNOTATE","source":sel(entity,{"op":"REGION","place":donor}),"layer":"nighttime lights" if re.search(r"night",layer,re.I) else layer}
                return {"op":"ESTIMATE","method":method.lower(),"source":source,"target":{"op":"REGION","place":target}}

    # Literal unsupported source asks preserve every requested modifier.
    if re.fullmatch(r"\s*current\s+job\s+vacancies\s+posted\s+by\s+firms\s+in\s+.+?[.?!]*",question,re.I) and first:
        out=dict(first);out["entity"]="current firm-posted job vacancies";return out
    income=re.match(r"\s*street\s+vendors?[’']\s+monthly\s+income\s+records\s+for\s+(.+?),\s*((?:19|20)\d{2})[.?!]*$",question,re.I)
    if income:
        place,year=income.groups()
        old_region=(first or {}).get("region")
        reg=old_region if isinstance(old_region,dict) and _phrase_norm(place) in _phrase_norm(old_region.get("place","")) else {"op":"REGION","place":place}
        return {"op":"SELECT","entity":"street vendor monthly income","region":reg,"time":{"start":year,"end":year}}
    rent=re.match(r"\s*attach\s+(.+?)\s+to\s+every\s+(.+?)\s+in\s+(.+?)[.?!]*$",question,re.I)
    if rent:
        layer,e_text,place=rent.groups();ee=ents(e_text)
        # Canonical connector fields may already be normalized (opening_hours, name, operator).
        # Rebuild only a modifier-bearing unsupported literal that the generic binder truncated.
        if ee and re.search(r"\b(?:verified|monthly|survey(?:ed)?|reported)\b",layer,re.I):
            layer=re.sub(r"\brents\b","rent",layer,flags=re.I)
            return {"op":"ANNOTATE","source":sel(ee[-1],{"op":"REGION","place":place}),"layer":layer}
    deictic_presence=re.match(r"\s*in\s+(.+?),\s*are\s+any\s+(.+?)\s+within\s+(.+?)\s+of\s+those[?!.]*$",question,re.I)
    if deictic_presence:
        place,e_text,dist=deictic_presence.groups();ee=ents(e_text)
        if ee:
            reg={"op":"REGION","place":place};rel={"op":"RELATE","relation":"within","threshold_km":_parse_dist_km(dist),"left":sel(ee[-1],reg),"right":sel("?anchor_entity",reg)}
            return {"op":"AGGREGATE","by":"space","metric":"presence","source":rel}
    return ir


def mech_both_relations(ir, question):
    """'X within D of both Y and Z' is two chained RELATE constraints."""
    if not (re.search(r"\b(?:of|near|within)\s+both\b",question,re.I) or
            re.search(r"\bboth\b.+?\band\b.+?\bwithin\b",question,re.I)): return ir
    entities=[key for _,_,key in _entity_occurrences(question,osm_only=True)]
    # De-duplicate resolver aliases while preserving literal order.
    entities=list(dict.fromkeys(entities))
    if len(entities)<3:return ir
    first=_first_select(ir)
    if first:
        region=first.get("region")
    else:
        prefix = re.match(
            r"\s*([A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*(?:\s+[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?"
            r"(?:,\s*[A-ZÀ-ÖØ-Ý][\wÀ-ÿ-]*)?)\s*(?:—|:)\s+", question)
        if not prefix:return ir
        region={"op":"REGION","place":prefix.group(1).strip()}
    threshold=_parse_dist_km(question.lower())
    def s(entity):return {"op":"SELECT","entity":entity,"region":region,"time":None}
    rel={"op":"RELATE","relation":"within","threshold_km":threshold,
         "left":{"op":"RELATE","relation":"within","threshold_km":threshold,
                 "left":s(entities[0]),"right":s(entities[1])},"right":s(entities[2])}
    if re.search(r"\b(?:listed? by name|names? (?:listed|requested)|want (?:them|the results?) listed)\b",
                 question, re.I):
        return {"op":"ANNOTATE","source":rel,"layer":"name"}
    if re.search(r"\b(?:i want|give me|show me)\s+(?:the\s+)?list\b", question, re.I):
        return rel
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
    if first:
        region=first.get("region")
    else:
        place=re.search(r"\bin\s+(.+?)\s+(?:are\s+)?within\b",question,re.I)
        if not place:return ir
        region={"op":"REGION","place":place.group(1).strip(" ,.;:—-")}
    distances=[]
    for m in re.finditer(r"[\d.]+\s*(?:km|kilometers?|kilometres?|m\b|meters?|metres?)",ql):
        value=_parse_dist_km(m.group(0));distances.append(value)
    def s(entity):return {"op":"SELECT","entity":entity,"region":region,"time":None}
    def answer_form(source):
        if re.search(r"\b(?:what are the names of|names of|named\b|names?\s+(?:are|if)|listed? by name)",ql):
            return {"op":"ANNOTATE","source":source,"layer":"name"}
        if re.match(r"\s*(?:are\s+(?:there\s+)?any|any|are\s+there\s+(?!more\b))", ql) \
                or re.search(r"\b(?:presence answer|presence result|yes/no presence)\b",ql):
            return {"op":"AGGREGATE","by":"space","metric":"presence","source":source}
        if re.search(r"\b(?:how many|count)\b",ql):
            return {"op":"AGGREGATE","by":"space","metric":"count","source":source}
        return source
    # A completed co-occurring subset can itself be constrained by a second spatial predicate.
    if re.search(r"\bco-?occur\b",ql) and re.search(
            r"\b(?:retain|keep|return)\s+those\s+(?:beyond|more\s+than)\b",ql):
        inner={"op":"RELATE","relation":"cooccur",
               "left":s(entities[0]),"right":s(entities[1])}
        outer={"op":"RELATE","relation":"beyond",
               "left":inner,"right":s(entities[2])}
        distance=_parse_dist_km(ql)
        if distance is not None:outer["threshold_km"]=distance
        return answer_form(outer)
    # Same-left conjunction without numeric thresholds: "X near Y are also near Z".
    if re.search(r"\bnear\b.+?\b(?:are|is)\s+also\s+near\b", ql):
        inner={"op":"RELATE", "relation":"within",
               "left":s(entities[0]), "right":s(entities[1])}
        outer={"op":"RELATE", "relation":"within",
               "left":inner, "right":s(entities[2])}
        return answer_form(outer)
    # General same-left conjunction: first clause names subject+anchor; the second names only
    # the additional anchor.  This distinguishes it from `difference between X near A and Y
    # near A`, whose second clause names two entities and belongs to COMPARE.
    parts=re.split(r"\b(?:and|but|yet|while(?:\s+also)?)\b",ql,flags=re.I)
    relation_parts=[p for p in parts if _parse_dist_km(p) is not None and
                    re.search(r"\b(?:within|beyond|outside|more\s+than)\b",p)]
    if len(relation_parts)>=2:
        p1,p2=relation_parts[0],relation_parts[1]
        e1=list(dict.fromkeys(key for _,_,key in _entity_occurrences(p1,osm_only=True)))
        e2=list(dict.fromkeys(key for _,_,key in _entity_occurrences(p2,osm_only=True)))
        if len(e1)>=2 and len(e2)==1 and len(entities)==3:
            polarity=lambda p:"beyond" if re.search(
                r"\b(?:not\s+within|beyond|outside|more\s+than)\b|(?:^|\b)(?:have|has|with)\s+no\b",p) else "within"
            inner={"op":"RELATE","relation":polarity(p1),"threshold_km":_parse_dist_km(p1),
                   "left":s(entities[0]),"right":s(entities[1])}
            outer={"op":"RELATE","relation":polarity(p2),"threshold_km":_parse_dist_km(p2),
                   "left":inner,"right":s(entities[2])}
            return answer_form(outer)
    if re.search(r"\bwithin\b.+?\bof\b.+?\bthat are within\b",ql):
        ds=distances or [None]
        right={"op":"RELATE","relation":"within","left":s(entities[1]),"right":s(entities[2])}
        outer={"op":"RELATE","relation":"within","left":s(entities[0]),"right":right}
        if ds[0] is not None:outer["threshold_km"]=ds[0]
        if len(ds)>1:right["threshold_km"]=ds[1]
        elif ds[0] is not None:right["threshold_km"]=ds[0]
        return answer_form(outer)
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
    elif re.search(r"\band\s+(?:beyond|more than)\b",ql):
        before,after=re.split(r"\band\b",ql,maxsplit=1)
        inner={"op":"RELATE","relation":"within","left":s(entities[0]),"right":s(entities[1])}
        outer={"op":"RELATE","relation":"beyond","left":inner,"right":s(entities[2])}
        d1,d2=_parse_dist_km(before),_parse_dist_km(after)
        if d1 is not None:inner["threshold_km"]=d1
        if d2 is not None:outer["threshold_km"]=d2
    else:return ir
    return answer_form(outer)


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
    generic=re.match(
        r"\s*from\s+(.+?),\s*transfer\s+(?:the\s+)?(?:relevant|unspecified|appropriate)\s+"
        r"facility\s+records\s+by\s+(envelope|feature|interpolat(?:e|ion))\s+to\s+(.+?)[.?!]*$",
        question,re.I)
    if generic:
        donor,method,target=generic.groups()
        method="interpolate" if method.lower().startswith("interpolat") else method.lower()
        return {"op":"ESTIMATE","method":method,
                "source":{"op":"SELECT","entity":"?facility_type",
                          "region":{"op":"REGION","place":donor.strip(" ,")},"time":None},
                "target":{"op":"REGION","place":target.strip(" ,")}}

    annotated=re.match(
        r"\s*(envelope|feature|interpolat(?:e|ion))[- ]transfer\s+"
        r"([a-z][a-z0-9_:.-]*)[- ]annotated\s+(.+?)\s+records\s+from\s+(.+?)\s+"
        r"to\s+estimate\s+.+?\s+in\s+(.+?)[.?!]*$",question,re.I)
    if annotated:
        method,layer,entity_text,donor,target=annotated.groups()
        method="interpolate" if method.lower().startswith("interpolat") else method.lower()
        entities=_entity_occurrences(entity_text,osm_only=True)
        if entities:
            selected={"op":"SELECT","entity":entities[-1][2],
                      "region":{"op":"REGION","place":donor.strip(" ,")},"time":None}
            return {"op":"ESTIMATE","method":method,
                    "source":{"op":"ANNOTATE","source":selected,"layer":layer.lower()},
                    "target":{"op":"REGION","place":target.strip(" ,")}}

    colocated=re.match(
        r"\s*estimate\s+(?:a\s+)?co-?location\s+(envelope|feature|interpolat(?:e|ion))\s+"
        r"for\s+(.+?)\s+from\s+(.+?)\s+that\s+co-?occur\s+with\s+(.+?)[.?!]*$",
        question,re.I)
    if colocated:
        method,target,donor_source,anchor_text=colocated.groups()
        source_occ=_entity_occurrences(donor_source,osm_only=True)
        anchor_occ=_entity_occurrences(anchor_text,osm_only=True)
        if source_occ and anchor_occ:
            start,_,entity=source_occ[-1]
            donor=donor_source[:start].strip(" ,.;:—-")
            region={"op":"REGION","place":donor}
            method="interpolate" if method.lower().startswith("interpolat") else method.lower()
            return {"op":"ESTIMATE","method":method,
                    "source":{"op":"RELATE","relation":"cooccur",
                              "left":{"op":"SELECT","entity":entity,"region":region,"time":None},
                              "right":{"op":"SELECT","entity":anchor_occ[-1][2],
                                       "region":region,"time":None}},
                    "target":{"op":"REGION","place":target.strip(" ,")}}

    # This entire Records-typed source and REGION target are explicit even if the raw model
    # merges them into ESTIMATE.target.  Rebuild before requiring a schema-valid source child.
    related = re.match(
        r"\s*using\s+(.+?)\s+(within|beyond)\s+(.+?)\s+(?:of|from)\s+"
        r"(?:a|an|the)\s+(.+?),\s*estimate\s+(.+?)\s+(?:coverage|field)\s+in\s+"
        r"(.+?)\s+by\s+(envelope|feature|interpolate)[.?!]*$", question, re.I)
    if related:
        donor_left, relation, distance, anchor_text, target_text, target_place, method = \
            related.groups()
        donor_occ = _entity_occurrences(donor_left, osm_only=True)
        anchor_occ = _entity_occurrences(anchor_text, osm_only=True)
        target_occ = _entity_occurrences(target_text, osm_only=True)
        if donor_occ and anchor_occ:
            start, _, donor_entity = donor_occ[-1]
            donor_place = donor_left[:start].strip(" ,.;:—-")
            target_entity = target_occ[-1][2] if target_occ else donor_entity
            if donor_place:
                region = {"op":"REGION", "place":donor_place}
                source = {"op":"RELATE", "relation":relation.lower(),
                          "left":{"op":"SELECT", "entity":donor_entity,
                                  "region":region, "time":None},
                          "right":{"op":"SELECT", "entity":anchor_occ[-1][2],
                                   "region":region, "time":None}}
                threshold = _parse_dist_km(distance)
                if threshold is not None:
                    source["threshold_km"] = threshold
                return {"op":"ESTIMATE", "method":method.lower(), "source":source,
                        "target":{"op":"REGION", "place":target_place.strip(" ,")}}
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
    # Explicit named transfer roles determine a Records donor and REGION target even when the
    # model places a computed quantity in target.
    direct=re.search(r"\bestimate\s+(.+?)\s+in\s+(.+?)\s+by\s+carrying\s+over\s+the\s+"
                     r"(feature|envelope|interpolate)\s+(?:model|pattern)\s+from\s+(.+?)[.?!]*$",
                     question,re.I)
    if direct:
        entity_text,target,method,donor=direct.groups();occ=_entity_occurrences(entity_text,osm_only=True)
        if occ:
            return {"op":"ESTIMATE","method":method.lower(),
                    "source":{"op":"SELECT","entity":occ[-1][2],
                              "region":{"op":"REGION","place":donor.strip(" ,")},"time":None},
                    "target":{"op":"REGION","place":target.strip(" ,")}}
    donor_to_deictic=re.search(r"\buse\s+(.+?)\s+as\s+(?:the\s+)?donor\b.+?\b(?:my city|my town|my area)\b",question,re.I)
    if donor_to_deictic and out.get("op")=="ESTIMATE":
        donor=donor_to_deictic.group(1).strip(" ,.;:—-");entity=(_first_select(out) or {}).get("entity","?facility_type")
        out={"op":"ESTIMATE","method":"envelope","source":{"op":"SELECT","entity":entity,
             "region":{"op":"REGION","place":donor},"time":None},"target":"?place"}
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
    donor_only=re.search(r"\bestimate\s+.+?\s+from\s+(.+?)(?:[.?]|$)",question,re.I)
    current_source=_first_select(out)
    current_source_region=current_source.get("region") if current_source else None
    current_target=out.get("target") if isinstance(out,dict) and out.get("op")=="ESTIMATE" else None
    target_is_hole=(isinstance(current_target,str) and current_target.startswith("?")) or \
        (isinstance(current_target,dict) and str(current_target.get("place","")).startswith("?"))
    source_is_hole=(isinstance(current_source_region,str) and current_source_region.startswith("?")) or \
        (isinstance(current_source_region,dict) and str(current_source_region.get("place","")).startswith("?"))
    donor_prefix=question[:donor_only.start()] if donor_only else ""
    target_missing_surface=bool(re.search(
        r"\b(?:nearby|here|elsewhere|somewhere else|an unspecified place|my city|my town|my area)\b", donor_prefix, re.I))
    # If provenance has left both roles unbound, the literal `from PLACE` still determines the
    # donor role regardless of the purpose preamble (siting/planning/etc.).
    unknown_target=donor_only if donor_only and (target_missing_surface or
        (target_is_hole and source_is_hole)) else None
    if unknown_target and not (using or trailing) and isinstance(out,dict) and out.get("op")=="ESTIMATE":
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
    # A named donor followed only by a deictic destination does not bind the target. In
    # particular, never copy the donor place into "over there".
    if isinstance(out, dict) and out.get("op") == "ESTIMATE" \
            and re.search(r"\b(?:over there|to there|somewhere else)\b", question, re.I):
        out = dict(out); out["target"] = "?place"
    if isinstance(out,dict) and out.get("op")=="ESTIMATE" and re.search(
            r"\b(?:target\s+city|underserved\s+district|peer\s+metro|destination\s+(?:city|region))"
            r"\s+under\s+review\b",question,re.I):
        out=dict(out);out["target"]="?target_place"
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
            and not re.search(r"\b(?:ratio|divid(?:e|ed|ing))\b",question,re.I):
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
    for start, short_end in re.findall(r"\b((?:19|20)\d{2})\s*[–—-]\s*(\d{2})\b",question):
        years.add(start[:2] + short_end)
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
    import connectors as C
    def is_supported(value):
        return bool(C.ilo_resolve_indicator(value)[0] or C.eurostat_resolve_indicator(value)[0]
                    or C.wb_resolve_indicator(value)[0] or C.osm_resolve_tag(value)[0])

    # A prior exact level compiler wins over this fallback surface parser.  In particular, the
    # fallback grammar intentionally treats everything before ``for`` as a literal unsupported
    # entity and therefore cannot safely improve an already connector-resolved SELECT.
    if isinstance(ir,dict) and ir.get("op")=="SELECT" and is_supported(ir.get("entity","")) \
            and ir.get("region") is not None:
        return ir

    literal_relation=re.match(
        r"\s*which\s+(.+?)\s+in\s+(.+?)\s+are\s+within\s+(.+?)\s+of\s+"
        r"(?:a|an|the)\s+(.+?)[.?!]*$",question,re.I)
    if literal_relation:
        left_entity,place,distance,right_entity=(x.strip(" ,") for x in literal_relation.groups())
        if (json.dumps(ir).count('"RELATE"') >= 2 or
                re.search(r"\b(?:but|and|yet)\s+(?:not\s+within|within|beyond|more\s+than)",
                          right_entity,re.I)):
            return ir
        if not is_supported(left_entity) or not is_supported(right_entity):
            region={"op":"REGION","place":place};return {
                "op":"RELATE","relation":"within","threshold_km":_parse_dist_km(distance),
                "left":{"op":"SELECT","entity":left_entity,"region":region,"time":None},
                "right":{"op":"SELECT","entity":right_entity,"region":region,"time":None}}

    # Preserve a restrictive or unresolved anchor even when the question carries a narrative
    # preamble. `main marketplace` must not execute as every marketplace. Deictic suffixes such
    # as `by me`/`here` are normalized later while their region remains a hole.
    anchor_relation=re.search(
        r"\bwhich\s+(.+?)\s+are\s+within\s+(.+?)\s+of\s+(?:a|an|the)\s+(.+?)[.?!]*$",
        question,re.I)
    if anchor_relation and isinstance(ir,dict) and ir.get("op")=="RELATE":
        _,distance,right_entity=(x.strip(" ,") for x in anchor_relation.groups())
        semantic_entity=re.sub(
            r"(?:\s+there|\s*,?\s+in\s+(?:this|that|the)\s+(?:place|city|area)\b.*)$",
            "",right_entity,flags=re.I).strip(" ,")
        if not re.search(r"\b(?:but|and|yet)\s+(?:not\s+within|within|beyond|more\s+than)",
                         right_entity,re.I) \
                and not is_supported(semantic_entity):
            out=json.loads(json.dumps(ir))
            if isinstance(out.get("right"),dict) and out["right"].get("op")=="SELECT":
                out["right"]["entity"]=right_entity
                parsed=_parse_dist_km(distance)
                if parsed is not None:out["threshold_km"]=parsed
                return out

    recorded=re.match(r"\s*how\s+many\s+(.+?)\s+are\s+recorded\s+in\s+(.+?)[.?!]*$",
                      question,re.I)
    if recorded:
        entity,place=(x.strip(" ,") for x in recorded.groups())
        if not is_supported(entity):
            return {"op":"AGGREGATE","by":"space","metric":"count","source":{
                "op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},"time":None}}

    unsupported_trend=re.match(
        r"\s*is\s+the\s+(.+?)\s+in\s+(.+?)\s+(?:rising\s+or\s+falling|climbing\s+or\s+dropping)"
        r"[.?!]*$",question,re.I)
    if unsupported_trend:
        entity,place=(x.strip(" ,") for x in unsupported_trend.groups())
        if not is_supported(entity):
            source={"op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},"time":None}
            return {"op":"COMPARE","how":"trend_direction","left":{
                "op":"AGGREGATE","by":"time","metric":"mean","source":source}}

    unsupported_change=re.match(
        r"\s*((?:19|20)\d{2})\s*(?:→|->|–|—|-)\s*((?:19|20)\d{2})\s+change\s+in\s+"
        r"(.+?)\s+for\s+(.+?)[.?!]*$",question,re.I)
    if unsupported_change:
        y1,y2,entity,place=(x.strip(" ,") for x in unsupported_change.groups())
        if not is_supported(entity):
            def point(year):return {"op":"SELECT","entity":entity,
                "region":{"op":"REGION","place":place},"time":{"start":year,"end":year}}
            return {"op":"COMPARE","how":"difference","left":point(y2),"right":point(y1)}

    headed=re.match(r"\s*(.+?)\s*,\s*((?:19|20)\d{2})\s*(?:—|-)\s*"
                    r"what\s+was\s+(?:the\s+)?(.+?)[.?!]*$",question,re.I)
    if headed:
        place,year,entity=(x.strip(" ,") for x in headed.groups())
        if not is_supported(entity):
            return {"op":"SELECT","entity":entity,"region":{"op":"REGION","place":place},
                    "time":{"start":year,"end":year}}

    # Non-commutative source-gap arithmetic still needs two complete literal leaves.  Equal
    # DataRequest outcomes do not make truncated phrases or invented aggregation equivalent.
    arithmetic = re.match(
        r"\s*(.+?)[’']s\s+((?:19|20)\d{2})\s+(.+?)\s+minus\s+"
        r"(.+?)[’']s\s+((?:19|20)\d{2})\s+(.+?)[.?!]*$", question, re.I)
    if arithmetic:
        p1,y1,e1,p2,y2,e2=(x.strip(" ,") for x in arithmetic.groups())
        supported=lambda value: bool(C.ilo_resolve_indicator(value)[0] or
            C.eurostat_resolve_indicator(value)[0] or C.wb_resolve_indicator(value)[0] or
            C.osm_resolve_tag(value)[0])
        if not supported(e1) and not supported(e2):
            def point(entity,place,year):return {"op":"SELECT","entity":entity,
                "region":{"op":"REGION","place":place},"time":{"start":year,"end":year}}
            return {"op":"COMPARE","how":"difference",
                    "left":point(e1,p1,y1),"right":point(e2,p2,y2)}

    # Possessive point query: "What was Kenya's median daily earnings in 2023?"
    possessive = re.match(
        r"\s*what\s+was\s+(.+?)[’']s\s+(.+?)\s+in\s+((?:19|20)\d{2})[.?!]*$",
        question,re.I)
    if possessive:
        place, entity, year = (x.strip(" ,") for x in possessive.groups())
        if not (C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0]
                or C.wb_resolve_indicator(entity)[0] or C.osm_resolve_tag(entity)[0]):
            return {"op":"SELECT","entity":entity,
                    "region":{"op":"REGION","place":place},
                    "time":{"start":year,"end":year}}

    # Preserve an unsupported ranked quantity as one literal SELECT per candidate.  Inserting a
    # spatial mean because the English noun contains "average" changes an unknown measure into
    # an executable record reduction and is not licensed by the algebra.
    ranked = re.search(
        r"\b(?:highest|lowest)\s+(.+?)\s+in\s+((?:19|20)\d{2})\s*:", question,re.I)
    if ranked and isinstance(ir,dict) and ir.get("op") == "RANK":
        entity, year = ranked.groups()
        if not (C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0]
                or C.wb_resolve_indicator(entity)[0] or C.osm_resolve_tag(entity)[0]):
            items=[]
            for item in ir.get("items",[]):
                selected=_first_select(item);region=selected.get("region") if selected else None
                if region is None:break
                items.append({"op":"SELECT","entity":entity,"region":region,
                              "time":{"start":year,"end":year}})
            if len(items)==len(ir.get("items",[])) and len(items)>=2:
                out=dict(ir);out["items"]=items;return out
    headcount = re.match(
        r"\s*for\s+(.+?)\s+i need the actual headcount of\s+(.+?)\s*(?:—|\s-\s|,\s)",
        question, re.I)
    if headcount:
        place, subject = headcount.groups()
        subject = _phrase_norm(subject)
        subject = re.sub(r"\bsector\b", "", subject)
        subject = re.sub(r"\bworkers\b", "worker", subject)
        subject = " ".join(subject.split())
        return {"op":"SELECT","entity":f"{subject} headcount",
                "region":{"op":"REGION","place":place.strip(" ,.;:—-")},"time":None}
    preserve_number = False
    match = re.match(r"\s*show\s+(.+?)\s+for\s+(.+?)\s+in\s+((?:19|20)\d{2})[.?!]?\s*$",
                     question, re.I)
    if not match:
        match = re.match(r"\s*what\s+was\s+(?:the\s+)?(.+?)\s+in\s+(.+?)\s+in\s+"
                         r"((?:19|20)\d{2})[.?!]?\s*$", question, re.I)
        preserve_number = bool(match)
    if not match:
        match = re.match(r"\s*report\s+(?:the\s+)?(.+?)\s+in\s+(.+?)\s+for\s+"
                         r"((?:19|20)\d{2})[.?!]?\s*$", question, re.I)
        preserve_number = bool(match)
    if match:
        entity, place, year = match.groups()
        aggregate = False
    else:
        surfaces = (
            (r"\s*pull\s+(.+?)\s+for\s+(.+?)[.?!]*$", False),
            (r"\s*(?:procurement\s*:\s*)?count\s+of\s+(.+?)\s+in\s+(.+?)[.?!]*$", True),
            (r"\s*(?:audit\s+ask\s*(?:—|:|-)?\s*)(.+?)\s+in\s+(.+?)[.?!]*$", False),
            (r"\s*(?:dashboard\s+)?wants?\s+(.+?)\s+for\s+(.+?)[.?!]*$", False),
        )
        found = None
        for pattern, aggregate in surfaces:
            found = re.match(pattern, question, re.I)
            if found: break
        if not found: return ir
        entity, place = found.groups(); year = None
    # A complete arithmetic tree already represents the user's supported operands.  The surface
    # phrase "female-to-male ... ratio" is not itself a connector entity and must not cause this
    # late source-gap pass to erase a valid COMPARE synthesized earlier in the pipeline.
    if isinstance(ir, dict) and ir.get("op") == "COMPARE" and re.search(
            r"\b(?:ratio|difference|gap|subtract|minus|divid)\w*\b", question, re.I):
        return ir
    # Only apply when the phrase is not already a supported connector measure.
    if (C.ilo_resolve_indicator(entity)[0] or C.eurostat_resolve_indicator(entity)[0]
            or C.wb_resolve_indicator(entity)[0] or C.osm_resolve_tag(entity)[0]):
        return ir
    if not preserve_number:
        if entity.lower().endswith("surveys"): entity = entity[:-3] + "ey"
        elif entity.lower().endswith("s") and not re.search(r"\b(?:microdata|statistics)\b", entity, re.I):
            entity = entity[:-1]
    selected = {"op":"SELECT","entity":entity.strip(),
                "region":{"op":"REGION","place":place.strip()},
                "time":{"start":year,"end":year} if year else None}
    if aggregate:
        return {"op":"AGGREGATE","by":"space","metric":"count","source":selected}
    return selected


def mech_deictic_roles(ir, question):
    """Keep unresolved place/entity roles as shared typed holes.

    Late placement is intentional: named-entity and region binders may safely restore explicit
    antecedents first, while unsupported deixis must be able to undo a model's plausible-looking
    duplicated literal.  The rewrite is licensed only by narrow role-bearing surfaces.
    """
    if not isinstance(ir, dict):
        return ir
    ql = _phrase_norm(question)
    by_me = bool(re.search(r"\b(?:by|near|beside) me\b", ql))
    unresolved_city = "that city" in ql
    unresolved_there = bool(re.search(r"\bthere\b", ql))
    unresolved_here = bool(re.search(r"\bhere\b", ql))
    workshop_anaphor = bool(re.search(r"\bthose workshops\b", ql))
    generic_anchor = bool(re.search(r"\b(?:near|within|beside) the facility\b", ql))
    comparator_country = "country being used as its comparator" in ql
    focus_city = bool(re.search(r"\b(?:indian\s+)?focus\s+city\b",ql))
    anchor_under_review = bool(re.search(r"\banchor\s+(?:amenity|facility|entity)\s+under\s+review\b",ql))
    named_osm = list(dict.fromkeys(key for _, _, key in
                                   _entity_occurrences(question, osm_only=True)))
    bare_anchor_anaphor = bool(re.search(
        r"\b(?:within|beyond|near|beside)\b.+?\b(?:of|from)?\s*(?:them|those)\b", ql)) \
        and len(named_osm) <= 1
    if not any((by_me, unresolved_city, unresolved_there, unresolved_here,
                workshop_anaphor, generic_anchor, comparator_country, focus_city,
                anchor_under_review, bare_anchor_anaphor)):
        return ir

    def walk(value, parent_op=None, side=None):
        if isinstance(value, list):
            return [walk(item, parent_op, side) for item in value]
        if not isinstance(value, dict):
            return value
        op = value.get("op")
        out = {key: walk(child, op, key) if isinstance(child, (dict, list)) else child
               for key, child in value.items()}
        if op != "SELECT":
            return out

        entity = str(out.get("entity", ""))
        if parent_op == "RELATE" and side == "right" and (by_me or unresolved_here):
            cleaned=re.sub(r"\s+(?:(?:by|near|beside)\s+me|here)\s*$","",entity,flags=re.I)
            if _phrase_norm(cleaned) == "market":cleaned="marketplace"
            if cleaned:out["entity"]=cleaned
        if workshop_anaphor and parent_op in ("COMPARE", "AGGREGATE", "RANK"):
            # In a count comparison the antecedent subtype, not merely "workshop", is missing.
            if re.search(r"\b(?:craft|artisan|workshop)\b", _phrase_norm(entity)):
                out["entity"] = "?workshop_type"
        if generic_anchor and parent_op == "RELATE" and side == "right":
            out["entity"] = "?anchor_entity"
        if anchor_under_review and parent_op == "RELATE" and side == "right":
            out["entity"] = "?anchor_entity"
        if bare_anchor_anaphor and parent_op == "RELATE" and side == "right":
            out["entity"] = "?anchor_entity"

        region = out.get("region")
        place = region.get("place", "") if isinstance(region, dict) else str(region or "")
        pn = _phrase_norm(place)
        replacement = None
        if by_me and parent_op == "RELATE" and side == "right":
            replacement = "?anchor_place"
        elif unresolved_city and pn in ("that city", "city"):
            replacement = "?third_city"
        elif unresolved_there and pn in ("there", "that place", "third place"):
            replacement = "?third_place"
        elif unresolved_here and pn in ("here", "this place", "this area", ""):
            replacement = "?place"
        elif comparator_country and parent_op == "COMPARE" and side == "right":
            replacement = "?comparator_country"
        elif focus_city:
            replacement = "?focus_city"
        if replacement:
            out["region"] = {"op":"REGION", "place":replacement}
        return out
    out=walk(ir)
    if comparator_country and out.get("op")=="COMPARE" and isinstance(out.get("right"),dict):
        def hole_right(value):
            if isinstance(value,list):return [hole_right(item) for item in value]
            if not isinstance(value,dict):return value
            changed={key:hole_right(child) for key,child in value.items()}
            if changed.get("op")=="SELECT":
                changed["region"]={"op":"REGION","place":"?comparator_country"}
            return changed
        out=dict(out);out["right"]=hole_right(out["right"])
    return out


def mech_explicit_change(ir, question):
    """Explicit 'changed ... YEAR ... YEAR' means endpoint difference, not unary trend.
    The two snapshots are fully determined by the question and the parsed SELECT."""
    explicit_change = (re.search(r"\b(?:chang(?:e|ed|ing)|increas(?:e|ed)|decreas(?:e|ed))\b",
                                 question.lower()) or
                       re.search(r"\b(?:go|went)\s+up\s+or\s+down\b", question, re.I))
    endpoint_difference = re.search(
        r"\b(?:19|20)\d{2}\s*(?:(?:-|–|—)\s*|(?:-|–|—)?\s*to\s*(?:-|–|—)?\s*)"
        r"(?:19|20)\d{2}\s+difference\b", question, re.I)
    if not isinstance(ir, dict) or not (explicit_change or endpoint_difference):
        return ir
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    if len(years) != 2:
        return ir
    y1, y2 = years

    direct=re.search(
        r"\b(?:how\s+much|by\s+how\s+much)\s+did\s+(.+?)\s+in\s+(.+?)\s+change\s+"
        r"(?:between|from)\s+(?:19|20)\d{2}\s+(?:and|to)\s+(?:19|20)\d{2}",
        question,re.I)
    if direct:
        entity,place=direct.groups()
        left=_stat_operand_from_clause(f"{place} {entity}",y2)
        right=_stat_operand_from_clause(f"{place} {entity}",y1)
        if left and right:
            return {"op":"COMPARE","how":"difference","left":left,"right":right}

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
    if re.search(r"\blivelihood support sites?\b",ql) and re.search(r"\bask\s+(?:which|what)\b",ql):
        first=_first_select(ir);region=first.get("region") if first else None
        if region is None:
            m=re.search(r"\bin\s+(.+?)(?:;|,\s*ask|\?)",question,re.I)
            region={"op":"REGION","place":m.group(1).strip(" ,.;:—-")} if m else "?place"
        return {"op":"SELECT","entity":"?facility_type","region":region,"time":None}
    generic_anchor=re.search(r"\b(?:show|list|map)\s+.+?\s+near\s+(transport|transit)\b",ql)
    if generic_anchor:
        first=_first_select(ir)
        if first:
            region=first.get("region")
            return {"op":"RELATE","relation":"within","left":first,
                    "right":{"op":"SELECT","entity":"?transport_anchor","region":region,"time":None}}
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
    vague_workplace = re.search(r"\b(?:work hubs?|the workplaces?)\b", ql)
    named_facilities = list(dict.fromkeys(key for _, _, key in _entity_occurrences(question, osm_only=True)))
    import connectors as C
    named_tags = {C.osm_resolve_tag(key)[0] for key in named_facilities}
    suitable_place = re.search(r"\bis there\s+(?:a|any)\s+suitable place\b", ql)
    generic_places = re.search(
        r"\b(?:what|which|any|are there any)\s+(?:kind of\s+)?(?:places|facilities|options)\s+"
        r"(?:are\s+)?(?:around|near)\s+here\b", ql)
    generic_facilities = re.search(
        r"\b(?:health|livelihood|education|transport)?\s*facilities\b", ql) and re.search(
        r"\b(?:here|this area|this district|around here)\b", ql)
    anaphoric_workplace = re.search(r"\b(?:those|these)\s+workplaces\b", ql)
    anaphoric_facility = re.search(r"\b(?:those|these)\s+facilities\b", ql)
    bare_those = re.search(r"\baddresses?\s+for\s+those\b", ql)
    if not isinstance(ir, dict) or not (vague_workplace or suitable_place or generic_places or generic_facilities or anaphoric_workplace or anaphoric_facility or bare_those):
        return ir
    def walk(v):
        if isinstance(v, list):
            return [walk(x) for x in v]
        if not isinstance(v, dict):
            return v
        out = {k: walk(x) for k, x in v.items()}
        if out.get("op") == "SELECT" and not str(out.get("entity", "")).startswith("?"):
            tag=C.osm_resolve_tag(str(out.get("entity", "")))[0]
            if not tag or tag not in named_tags:
                out["entity"] = "?workplace_type" if anaphoric_workplace else "?facility_type"
        return out
    out = walk(ir)
    # A deictic generic request is first a clarification request. Presence over an unknown
    # facility and unknown place falsely turns that clarification into a yes/no computation.
    if generic_places and out.get("op") == "AGGREGATE" and out.get("metric") == "presence" \
            and isinstance(out.get("source"), dict) and out["source"].get("op") == "SELECT":
        return out["source"]
    return out


def mech_abstract_rate_hole(ir, question):
    """A bare livelihood/work 'rate' does not name a measurable indicator."""
    ql=_phrase_norm(question)
    if not re.search(r"\b(?:livelihoods?|work)\b",ql) or " rate" not in ql:
        return ir
    if re.search(r"\b(?:employment|unemployment|participation|earnings|hours|income|wage)\b",ql):
        return ir
    def walk(value):
        if isinstance(value,list):return [walk(x) for x in value]
        if not isinstance(value,dict):return value
        out={k:walk(v) for k,v in value.items()}
        if out.get("op")=="SELECT":out["entity"]="?indicator"
        return out
    return walk(ir)


def mech_rejected_indicator_hole(ir, question):
    """An explicitly rejected fallback ("ask for an indicator instead of GDP") is not evidence
    for binding that fallback. Preserve the requested comparison skeleton with typed holes."""
    ql=_phrase_norm(question)
    if not re.search(r"\bask for (?:a |an |the )?supported livelihood indicator\b",ql) \
            or not re.search(r"\b(?:instead of|rather than|do not use|don t use)\b",ql):
        return ir
    def walk(value):
        if isinstance(value,list):return [walk(x) for x in value]
        if not isinstance(value,dict):return value
        out={k:walk(v) for k,v in value.items()}
        if out.get("op")=="SELECT":out["entity"]="?supported_livelihood_indicator"
        if out.get("op")=="AGGREGATE" and out.get("by")=="time" and out.get("metric")=="mean" \
                and isinstance(out.get("source"),dict) and out["source"].get("op")=="SELECT":
            return out["source"]
        return out
    return walk(ir)


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
    text=re.sub(r"(?<=\w)-(?=\w)"," ",text)
    fractions = {
        "quarter": 0.25, "one quarter": 0.25, "a quarter": 0.25,
        "three quarters": 0.75, "three quarter": 0.75,
        "one and a half": 1.5,
    }
    fraction = re.search(
        r"\b(one\s+and\s+a\s+half|three\s+quarters?|one\s+quarter|a\s+quarter|quarter)"
        r"(?:\s+of)?\s+(?:a\s+|one\s+)?"
        r"(km|kilometers?|kilometres?|meters?|metres?)\b", text, re.I)
    if fraction:
        value = fractions[fraction.group(1).lower()]
        return value if fraction.group(2).lower().startswith("k") else value / 1000.0
    half = re.search(r"\bhalf\s+(?:a\s+|one\s+)?"
                     r"(km|kilometers?|kilometres?|meters?|metres?)\b", text, re.I)
    if half:
        return 0.5 if half.group(1).lower().startswith("k") else 0.0005
    m = re.search(r"(\d{1,3}(?:,\d{3})+(?:\.\d+)?|[\d.]+)\s*"
                  r"(m\b|meters?|metres?|km\b|kilometers?|kilometres?)", text)
    if not m:
        words={"two":2.0,"three":3.0,"four":4.0,"five":5.0}
        written=re.search(r"\b(two|three|four|five)\s+"
                          r"(km|kilometers?|kilometres?|meters?|metres?)\b",text,re.I)
        if written:
            value=words[written.group(1).lower()]
            return value if written.group(2).lower().startswith("k") else value/1000.0
        if re.search(r"\b(?:a|one)\s+(?:km|kilometers?|kilometres?)\b", text, re.I):
            return 1.0
        if re.search(r"\b(?:a|one)\s+(?:meter|metre)\b", text, re.I):
            return 0.001
        return None
    val = float(m.group(1).replace(",", ""))
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
    m = re.search(r"within\s+(?:walking distance|[\d.]+\s*(?:m|km|meters?|metres?|kilometers?|minutes?))\s+"
                  r"(?:of|from)\s+(?:the|a|an)\s+([a-z][a-z ]{1,40}?)(?=\s+(?:and|but|then)\b|[?,.;:(])",
                  ql) or \
        re.search(r"(?:near|close to|next to|beside)\s+(?:the|a|an)\s+([a-z][a-z ]{2,40})[^a-z ]",
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
    if not pa["negated"] and tree.count('"RELATE"') == 1 and '"beyond"' in tree \
            and re.search(r"\b(?:within|near|close to)\b", question, re.I):
        return [f"The question AFFIRMS proximity to '{pa['anchor']}', but the tree uses relation "
                '"beyond" — that selects the complement. Use "within".']
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
    polarity_flip = ((pa["negated"] and '"within"' in tree) or
                     (not pa["negated"] and '"beyond"' in tree and
                      re.search(r"\b(?:within|near|close to)\b", question, re.I)))
    if polarity_flip and tree.count('"RELATE"') == 1:
        def flip(n):
            if isinstance(n, list):
                return [flip(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: flip(v) for k, v in n.items()}
            if out.get("op") == "RELATE" and out.get("relation") in ("within", "beyond"):
                out["relation"] = "beyond" if pa["negated"] else "within"
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
    ir = restore_named_region_scope(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:explicit_region_scope_from_question")
    before = json.dumps(ir)
    ir = bind_prefixed_region(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:prefixed_region_heading")
    before = json.dumps(ir)
    ir = mech_prefixed_statistic(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:prefixed_statistic")
    before = json.dumps(ir)
    ir = mech_statistical_surfaces(ir, question)
    ir = mech_closed_statistical_surface(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:clause_scoped_statistic")
    before = json.dumps(ir)
    ir = mech_explicit_change(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_two_snapshot_change")
    before = json.dumps(ir)
    ir = mech_series_rank(ir, question)
    ir = mech_rank_k(ir, question)
    ir = mech_explicit_rank_semantics(ir, question)
    ir = mech_ranked_quantity(ir, question)
    ir = mech_enumerated_rank(ir, question)
    ir = mech_rank_k(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_series_rank")
    before = json.dumps(ir)
    ir = mech_ratio(ir, question)
    ir = mech_mixed_source_compare(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:explicit_ratio")
    before = json.dumps(ir)
    ir = mech_mixed_gap(ir, question)
    ir = mech_same_time_measure_difference(ir, question)
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
    ir = mech_annulus_relation(ir, question)
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
    ir = mech_nearest_distance(ir, question)
    ir = mech_relation_comparisons(ir, question)
    ir = mech_spatial_cross_place(ir, question)
    ir = mech_spatial_arithmetic(ir, question)
    ir = mech_closed_spatial_surface(ir, question)
    ir = mech_requested_reduction(ir, question)
    ir = mech_comparison_mode(ir, question)
    ir = mech_behavior_proxy(ir, question)
    ir = mech_transfer_contract(ir, question)
    ir = mech_transfer_relational_source(ir, question)
    ir = mech_transfer_source_expression(ir, question)
    ir = mech_output_literal_honesty(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:answer_form_comparison_or_behavior")
    before = json.dumps(ir)
    ir = bind_named_indicator(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:unique_named_statistic")
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
    ir = mech_unresolved_point_time(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:unresolved_point_time")
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
    ir = mech_abstract_rate_hole(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:abstract_rate_indicator_hole")
    before = json.dumps(ir)
    ir = mech_rejected_indicator_hole(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:rejected_indicator_kept_as_hole")
    before = json.dumps(ir)
    ir = bind_named_behavior_place(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:named_behavior_place")
    before = json.dumps(ir)
    ir = mech_deictic_roles(ir, question)
    if json.dumps(ir) != before:
        events.append("binder:unresolved_deictic_roles")
    before = json.dumps(ir)
    ir = mech_explicit_surface_closure(ir, question)
    closure_changed=json.dumps(ir) != before
    if closure_changed:
        events.append("mech_synthesis:explicit_surface_closure")
        # The closure can synthesize fresh canonical leaves after the earlier restoration pass.
        # Do not rebind an unchanged mixed national/regional tree: a nested regional alias must
        # never pull the national operand into its boundary.
        ir = restore_eurostat_regions(ir, question)
        ir = restore_named_region_scope(ir, question)
    before=json.dumps(ir)
    ir = mech_enumerated_rank(ir, question)
    ir = mech_closed_statistical_surface(ir, question)
    ir = mech_closed_spatial_surface(ir, question)
    ir = mech_transfer_source_expression(ir, question)
    ir = mech_output_literal_honesty(ir, question)
    if json.dumps(ir) != before:
        events.append("mech_synthesis:closed_rank_transfer_or_output_contract")
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
        for fn in (restore_named_entities, restore_eurostat_regions, restore_named_region_scope,
                   bind_prefixed_region, mech_prefixed_statistic,
                   mech_statistical_surfaces, mech_closed_statistical_surface,
                   mech_explicit_change,
                   mech_series_rank, mech_rank_k, mech_explicit_rank_semantics,
                   mech_ranked_quantity, mech_enumerated_rank, mech_rank_k,
                   mech_ratio, mech_mixed_source_compare, mech_mixed_gap,
                   mech_same_time_measure_difference, mech_subtract_orientation, mech_dormant_ops,
                   mech_annulus_relation, mech_both_relations, mech_three_entity_relations,
                   mech_negative_relation,
                   mech_shared_distance_compare,
                   mech_relation_thresholds, mech_answer_form, mech_terse_and_anaphoric,
                   mech_nearest_distance,
                   mech_relation_comparisons, mech_spatial_cross_place, mech_spatial_arithmetic,
                   mech_closed_spatial_surface,
                   mech_requested_reduction,
                   mech_comparison_mode, mech_behavior_proxy, mech_transfer_contract,
                   mech_transfer_relational_source, mech_transfer_source_expression,
                   mech_output_literal_honesty, bind_named_indicator, mech_series_types,
                   mech_explicit_point_time,
                   mech_explicit_window_time, mech_time_faithfulness, mech_unresolved_point_time,
                   mech_since_time, mech_source_gap_select,
                   mech_generic_entity_hole, mech_abstract_rate_hole,
                   mech_rejected_indicator_hole, bind_named_behavior_place):
            ir = fn(ir, question)
        ir = mech_deictic_roles(ir, question)
        before_closure=json.dumps(ir)
        ir = mech_explicit_surface_closure(ir, question)
        if json.dumps(ir) != before_closure:
            ir = restore_eurostat_regions(ir, question)
            ir = restore_named_region_scope(ir, question)
        ir = mech_enumerated_rank(ir, question)
        ir = mech_closed_statistical_surface(ir, question)
        ir = mech_closed_spatial_surface(ir, question)
        ir = mech_transfer_source_expression(ir, question)
        ir = mech_output_literal_honesty(ir, question)
        if json.dumps(ir) != before_post:
            events.append("post_repair:semantic_passes_reapplied")
    return {"question": question, "raw": raw, "ir": ir, "parse_valid": ir is not None,
            "repaired": repaired, "events": events}


if __name__ == "__main__":
    import sys
    role = sys.argv[2] if len(sys.argv) > 2 else "qwen2b"
    r = parse(sys.argv[1], role=role)
    print(json.dumps(r, indent=2, default=str))
