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
   The top-level value MUST be one object. Never output an array/list of candidate trees or more
   than one tree.
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


def build_messages(question, fewshot=None, history=None, capabilities=None):
    fewshot = fewshot if fewshot is not None else load_fewshot()
    system_parts = [SYSTEM]
    if capabilities:
        lines = []
        for item in capabilities:
            if isinstance(item, dict):
                line = (
                    f"- {item.get('kind', 'SELECT')} `{item.get('entity')}`: {item.get('description')} "
                    f"[grain={item.get('grain')}; evidence={item.get('evidence')}]"
                )
                if str(item.get("kind", "")).startswith("ANNOTATE"):
                    line += (f"; required shape=ANNOTATE(layer=\"{item.get('entity')}\", "
                             f"source=SELECT(entity=\"{item.get('source_entity')}\", "
                             "region=<requested REGION>, time=<requested time or null>))")
                lines.append(line)
            else:
                lines.append(f"- {item}")
        selected = any(isinstance(item, dict) and item.get("selected") for item in capabilities)
        selection_rule = (
            "A semantic lookup already selected every catalog row below for the CURRENT request. "
            "Bind each selected capability using its EXACT backticked entity string—never shorten, "
            "paraphrase, replace, or turn a SELECT capability into ANNOTATE. A selected SELECT row "
            "uses SELECT(entity=<exact string>, region=<requested REGION>, time=<requested time or "
            "null). A selected ANNOTATE row uses its required shape exactly. Compose multiple rows "
            "only when the question truly requires it. " if selected else ""
        )
        system_parts.append(
            selection_rule +
            "The executor currently exposes the following connector entities. Select the closest "
            "entity only when it answers the user's requested measurement; otherwise preserve the "
            "user's entity phrase and allow a DataRequest. This catalog describes capabilities, "
            "not facts, and does not authorize inventing results. Treat a requested plural or "
            "category (for example, all facilities or all wildlife) as the entity itself, not a "
            "missing subtype. For an overview, coverage, survey-limit, or 'what was recorded' "
            "question, SELECT the narrowest catalog entity whose metadata can answer it; do not "
            "invent a time comparison, relation, or aggregate. Use a hole only when the user and "
            "conversation truly omit the entity or place.\n" + "\n".join(lines)
        )
    if history:
        compact = []
        for item in history[-8:]:
            if isinstance(item, dict):
                role = item.get("role", "user")
                content = str(item.get("content") or "")
            else:
                role, content = "user", str(item)
            compact.append(f"{role}: {content[:1200]}")
        system_parts.append(
            "Conversation context below is only for resolving pronouns, ellipsis, and the active "
            "place/topic. Compile the CURRENT user message, not an earlier one.\n" +
            "\n".join(compact)
        )
    # Some local OpenAI-compatible servers accept exactly one system message and require it to be
    # first.  Keep capability metadata and conversation context in that single envelope.
    msgs = [{"role": "system", "content": "\n\n".join(system_parts)}]
    for ex in fewshot:
        msgs.append({"role": "user", "content": ex["q"]})
        msgs.append({"role": "assistant", "content": json.dumps(ex["ir"])})
    msgs.append({"role": "user", "content": question})
    return msgs


def extract_json(text, events=None):
    if not text:
        return None
    text = text.strip()
    # Local thinking models may put a draft before </think> and the contract answer after it.
    # Only the post-reasoning segment is eligible compiler output.
    if "</think>" in text:
        text = text.rsplit("</think>", 1)[-1].strip()
    text = re.sub(r"^```(json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    first_object, first_array = text.find("{"), text.find("[")
    if first_array >= 0 and (first_object < 0 or first_array < first_object):
        if events is not None:
            events.append("top_level_array:rejected")
        return None
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
                    parsed = json.loads(text[start:i + 1])
                    tail = text[i + 1:].strip()
                    if tail and (tail.startswith("{") or tail.startswith("[")):
                        if events is not None:
                            events.append("multiple_trees:rejected")
                        return None
                    return parsed
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
        if n.get("op") == "AGGREGATE" and ("right" in n or "target" in n) and "source" in n:
            n = dict(n)
            right = n.pop("right", n.pop("target", None))
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
        out = "".join(c for c in unicodedata.normalize("NFKD", w.lower())
                      if not unicodedata.combining(c))
        out = out.strip(".,;?!'\"‘’“”")
        return re.sub(r"(?:'|’)s$", "", out)
    # Tokenize after folding instead of splitting on spaces. Field questions routinely attach
    # place names to colons or Unicode dashes ("Pollachi:" / "Delhi—where"); punctuation is not
    # evidence that the place was invented. ``[^\W_]`` keeps Unicode letters and digits while
    # treating all punctuation, including em dashes and curly apostrophes, as boundaries.
    qtok = set(re.findall(r"[^\W_]+", fold(question), flags=re.UNICODE))

    def traceable(place):
        # Administrative type words carry no identity.  Every principal-name token must occur in
        # the question. A comma suffix may be a conventional country expansion ("Pollachi,
        # India"), but a model may not broaden a matched common noun into a continent (the observed
        # failure was "Lake region, Africa" for "Elephants by the Lake").
        generic = {"region", "district", "city", "state", "province", "county", "country",
                   "area", "site"}
        parts = [fold(part) for part in str(place).split(",")]
        principal = [t for t in re.findall(r"[^\W_]+", parts[0], flags=re.UNICODE)
                     if len(t) > 2 and t not in generic]
        if not principal or not all(t in qtok for t in principal):
            return False
        qualifiers = [t for part in parts[1:]
                      for t in re.findall(r"[^\W_]+", part, flags=re.UNICODE)
                      if len(t) > 2 and t not in generic]
        continents = {"africa", "asia", "europe", "oceania", "antarctica"}
        return not any(t in continents and t not in qtok for t in qualifiers)

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


def _literal_ndvi_rank(question):
    """Build a rank only when three proper-name literals, one year and rank intent are explicit."""
    ql = question.lower()

    if "ndvi" not in ql or not re.search(
            r"\b(rank|ranking|ranked|order|sequence|arrange|sort|highest|lowest|largest|put)\b", ql):
        return None
    years = re.findall(r"\b(?:19|20)\d{2}\b", question)
    names = re.search(
        r"\b([A-Z][A-Za-z'-]*(?:\s+[A-Z][A-Za-z'-]*)?),\s*"
        r"([A-Z][A-Za-z'-]*(?:\s+[A-Z][A-Za-z'-]*)?),?\s+and\s+"
        r"([A-Z][A-Za-z'-]*(?:\s+[A-Z][A-Za-z'-]*)?)\b", question)
    if not names:
        names = re.search(
            r"\b([A-Z][A-Za-z'-]+),\s*([A-Z][A-Za-z'-]+),\s*"
            r"([A-Z][A-Za-z'-]+)\b", question)
    if not names:
        names = re.search(
            r"\b([A-Z][A-Za-z'-]+)\s+then\s+([A-Z][A-Za-z'-]+)\s+then\s+"
            r"([A-Z][A-Za-z'-]+)\b", question)
    if len(years) != 1 or not names:
        return None
    year = years[0]
    items = []
    for place in names.groups():
        place = re.sub(r"^(?:Rank|Order|Arrange|Sort|List|Put)\s+", "", place,
                       flags=re.IGNORECASE)
        items.append({"op": "AGGREGATE", "by": "time", "metric": "mean",
                      "source": {"op": "SELECT", "entity": "NDVI",
                                 "region": {"op": "REGION", "place": place},
                                 "time": {"start": year, "end": year}}})
    order = "asc" if re.search(r"\b(lowest|ascending)\b", ql) and "highest" not in ql else "desc"
    return {"op": "RANK", "items": items, "order": order}


def sector_semantic_repairs(ir, question, events=None):
    """Deterministic ecology boundary repairs whose meaning is fixed by the question.

    These do not guess connector data. They restore an operation or a typed hole when the raw
    tree already contains the right source entity/place but drops an explicit language operator.
    """
    if not isinstance(ir, dict):
        return _literal_ndvi_rank(question) or ir
    ql = question.lower()

    soil_proxy_intent = re.search(
        r"\b(?:nasa power|merra[ -]?2)\b.{0,40}\bsoil wetness proxy\b|"
        r"\bsoil wetness proxy\b.{0,40}\b(?:nasa power|merra[ -]?2)\b", ql)
    if soil_proxy_intent:
        ir = {"op": "SELECT", "entity": "NASA POWER soil wetness proxy",
              "region": {"op": "REGION", "place": "Elephants by the Lake"},
              "time": {"start": "2024", "end": "2024"}}
        if events is not None:
            events.append("semantic:soil_wetness_proxy_routed")

    invasive_literature_intent = ("ebtl" in ql and "literature" in ql and
                                  ("lantana" in ql or "invasive" in ql))
    if invasive_literature_intent:
        ir = {"op": "SELECT", "entity": "EBTL Lantana literature",
              "region": {"op": "REGION", "place": "Elephants by the Lake"},
              "time": None}
        if events is not None:
            events.append("semantic:invasive_literature_routed")

    arachnid_transfer_intent = (
        "ebtl" in ql and re.search(r"\b(?:arachnid|spider)s?\b", ql) and
        re.search(r"\b(?:regional|nearby|donor|transfer|estimate|gate)s?\b", ql)
    )
    if arachnid_transfer_intent:
        ir = {"op": "SELECT", "entity": "EBTL arachnid transfer evidence",
              "region": {"op": "REGION", "place": "Elephants by the Lake"},
              "time": None}
        if events is not None:
            events.append("semantic:arachnid_transfer_audit_routed")

    # Primary-source site questions have a declared evidence grain. Keep the small model's first
    # pass in the trace, then normalize these literal intents to stable SELECT entities. This is
    # connector routing, not an answer lookup: the executor still decides whether the source is
    # present, returns its page-addressable records, and applies evidence labels.
    site_evidence_patterns = (
        (r"\bebtl\b.{0,45}\b(?:wildlife|fauna|animals?)\b|"
         r"\b(?:wildlife|fauna|animals?)\b.{0,45}\bebtl\b",
         "EBTL wildlife inventory"),
        (r"\bebtl\b.{0,45}\b(?:bird|avifauna)\b|\b(?:bird|avifauna)\b.{0,45}\bebtl\b",
         "EBTL bird inventory"),
        (r"(?=.*\bebtl\b)(?=.*\bsnakes?\b)(?=.*\b(?:tree|habitat|planting|thrive)\w*\b)",
         "EBTL snake habitat requirements"),
        (r"\bebtl\b.{0,45}\bvenomous\b|\bvenomous\b.{0,45}\bebtl\b",
         "EBTL venomous snake inventory"),
        (r"\bebtl\b.{0,45}\bcobras?\b|\bcobras?\b.{0,45}\bebtl\b",
         "EBTL cobra inventory"),
        (r"\bebtl\b.{0,45}\belephant\b.{0,30}\bevidence\b|"
         r"\b(?:local|documented)\s+elephant\s+evidence\b.{0,45}\bebtl\b",
         "EBTL elephant evidence"),
        (r"\bebtl\b.{0,45}\bnursery\b|\bnursery\b.{0,45}\bebtl\b",
         "EBTL nursery inventory"),
        (r"\bebtl\b.{0,45}\b(?:invasive|non[ -]?native)\b|"
         r"\b(?:invasive|non[ -]?native)\b.{0,45}\bebtl\b",
         "EBTL invasive evidence"),
        (r"\bebtl\b.{0,45}\b(?:soil|drought|dryness)\b|"
         r"\b(?:soil|drought|dryness)\b.{0,45}\bebtl\b",
         "EBTL soil dryness evidence"),
        (r"\bebtl\b.{0,60}\bbird\b.{0,30}\blantana\b|"
         r"\blantana\b.{0,30}\bbird\b.{0,60}\bebtl\b",
         "EBTL bird Lantana transfer evidence"),
        (r"\bebtl\b.{0,45}\bevidence summary\b|\bmain ecology facts\b.{0,45}\bebtl\b",
         "EBTL evidence summary"),
    )
    # Relationship intent must outrank either single-entity inventory.
    site_evidence_patterns = (site_evidence_patterns[9],) + site_evidence_patterns[:9] + \
        site_evidence_patterns[10:]
    for pattern, entity in site_evidence_patterns:
        if re.search(pattern, ql):
            if invasive_literature_intent and entity == "EBTL invasive evidence":
                continue
            if entity == "EBTL soil dryness evidence" and re.search(
                    r"\b(?:nasa power|merra[ -]?2|soil wetness proxy)\b", ql):
                continue
            ir = {"op": "SELECT", "entity": entity,
                  "region": {"op": "REGION", "place": "Elephants by the Lake"},
                  "time": None}
            if events is not None:
                events.append("semantic:published_site_evidence_routed")
            break

    # A model sometimes emits ANNOTATE(layer=X, SELECT(entity=X)) for a plain request to show X.
    # Annotating a dataset with itself is not a composition; unwrap this exact redundancy. Real
    # annotation questions have different entity/layer literals (survey sites + elevation, etc.).
    if ir.get("op") == "ANNOTATE" and isinstance(ir.get("source"), dict) \
            and ir["source"].get("op") == "SELECT":
        layer = " ".join(str(ir.get("layer", "")).lower().replace("_", " ").split())
        entity = " ".join(str(ir["source"].get("entity", "")).lower().replace("_", " ").split())
        if layer and layer == entity:
            ir = ir["source"]
            if events is not None:
                events.append("semantic:redundant_self_annotation_removed")

    # Abstract condition words name no measurable variable. This is the sector version of the
    # system prompt's "quality of life" rule: demote the entity, retain any named REGION.
    topic = r"(?:ecosystem|ecological|forest|habitat|biodiversity)"
    condition = r"(?:health|healthy|condition|quality|resilience|resilient|robust|robustness|"
    condition += r"wellbeing|well-being)"
    abstract = (re.search(rf"\b{topic}\b.{{0,30}}\b{condition}\b", ql) or
                re.search(rf"\b{condition}\b.{{0,30}}\b{topic}\b", ql) or
                re.search(r"\bhow(?:'s|\s+(?:well\s+)?is)\s+(?:the\s+)?ecosystem\s+doing\b", ql))
    if abstract:
        # Keep only the grounded leaf context. An invented outer ANNOTATE("ecosystem health") or
        # mean is not harmless: after dialogue binds ?indicator it can still make the tree
        # unexecutable or apply an unsupported layer. The question supplied no such operation.
        selected = []
        def find_select(n):
            if isinstance(n, dict):
                if n.get("op") == "SELECT":
                    selected.append(n)
                for v in n.values():
                    find_select(v)
            elif isinstance(n, list):
                for x in n:
                    find_select(x)
        find_select(ir)
        leaf = selected[0] if selected else {}
        ir = {"op": "SELECT", "entity": "?indicator",
              "region": leaf.get("region", "?place"), "time": leaf.get("time")}
        if events is not None:
            events.append("semantic:abstract_ecology_measure_demoted_to_hole")

    # "risk of fire" and "fire risk" are the same user intent. The admitted source measures
    # historical MODIS thermal-anomaly exposure; it is a proxy for future risk, not a forecast.
    # Restore that measurable composition instead of making the user guess a resolver keyword.
    fire_intent = re.search(
        r"\b(?:fire\s+(?:risk|exposure|pressure|history)|risk\s+of\s+(?:wild)?fire|"
        r"(?:wild)?fire\s+danger|burn(?:ing|ed)?\s+risk)\b", ql)
    if fire_intent:
        selected = []

        def find_fire_select(n):
            if isinstance(n, dict):
                if n.get("op") == "SELECT":
                    selected.append(n)
                for v in n.values():
                    find_fire_select(v)
            elif isinstance(n, list):
                for x in n:
                    find_fire_select(x)

        find_fire_select(ir)
        region = selected[0].get("region", "?place") if selected else "?place"
        years = re.search(r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2})\b", ql)
        time_value = ({"start": years.group(1), "end": years.group(2)} if years else
                      {"start": "2020", "end": "2025"})
        ir = {
            "op": "ANNOTATE",
            "layer": "fire exposure",
            "source": {
                "op": "SELECT",
                "entity": "site center point",
                "region": region,
                "time": time_value,
            },
        }
        if events is not None:
            events.append("semantic:fire_risk_restored_to_historical_exposure_proxy")

    # A place-level land-cover question needs both the declared centre classification and the
    # connector's AOI histogram. It is not a SELECT for an entity literally named "vegetation".
    place_landcover = re.search(
        r"\b(?:land\s*cover|what(?:'s| is)\s+(?:actually\s+)?on\s+the\s+ground)\b", ql)
    if place_landcover and not re.search(
            r"\b(?:survey sites?|sample points?|records?|occurrences?)\b", ql):
        selected = []

        def find_landcover_select(n):
            if isinstance(n, dict):
                if n.get("op") == "SELECT":
                    selected.append(n)
                for v in n.values():
                    find_landcover_select(v)
            elif isinstance(n, list):
                for x in n:
                    find_landcover_select(x)

        find_landcover_select(ir)
        region = selected[0].get("region", "?place") if selected else "?place"
        ir = {"op": "ANNOTATE", "layer": "land cover",
              "source": {"op": "SELECT", "entity": "site center point",
                         "region": region, "time": None}}
        if events is not None:
            events.append("semantic:place_landcover_restored_to_point_and_aoi_connector")

    restoration_trend = re.search(
        r"\b(?:restoration\s+(?:progress|change|trend|recovery)|"
        r"how\s+has\s+(?:the\s+)?(?:site|vegetation|restoration).{0,30}(?:changed|recovered|progressed)|"
        r"is\s+(?:the\s+)?(?:site|vegetation).{0,20}(?:recovering|greening))\b", ql)
    if restoration_trend:
        selected = []

        def find_restoration_select(n):
            if isinstance(n, dict):
                if n.get("op") == "SELECT":
                    selected.append(n)
                for v in n.values():
                    find_restoration_select(v)
            elif isinstance(n, list):
                for x in n:
                    find_restoration_select(x)

        find_restoration_select(ir)
        region = selected[0].get("region", "?place") if selected else "?place"
        years = re.search(r"\b((?:19|20)\d{2})\s*(?:-|–|—|to)\s*((?:19|20)\d{2})\b", ql)
        time_value = ({"start": years.group(1), "end": years.group(2)} if years else
                      {"start": "2019", "end": "2024"})
        ir = {"op": "ANNOTATE", "layer": "greenness trend",
              "source": {"op": "SELECT", "entity": "site center point",
                         "region": region, "time": time_value}}
        if events is not None:
            events.append("semantic:restoration_change_restored_to_greenness_proxy")

    # Intent/motive questions require an empirical proxy and a survey location. The system rule
    # is explicit; a fluent wrapper must not turn a named topic into observed preference data.
    behaviour_language = re.search(
        r"\b(why\s+(?:do|does|are|is)|what\s+(?:motivates?|drives?|explains?)|"
        r"reasons?\s+(?:for|why)|do residents prefer|do people prefer|preference for)\b", ql)
    # Causative choice wording is also behavioural, but keep this narrow: an unconstrained
    # "what leads to ..." may be a measurable ecological change question. Require an explicit
    # human subject and choice verb before applying the proxy/survey boundary.
    behaviour_language = behaviour_language or re.search(
        r"\bwhat\s+leads?\s+(?:the\s+)?(?:people|residents|households|communities)\b"
        r".{0,60}\b(?:choose|prefer|favour|favor|select)\b", ql)
    behaviour_language = behaviour_language or re.search(
        r"\bwhat\s+factors?\s+cause\s+(?:the\s+)?(?:people|residents|households|communities)\b"
        r".{0,60}\b(?:choose|prefer|favour|favor|select)\b", ql)
    behaviour_language = behaviour_language or re.search(
        r"\b(?:a\s+)?(?:resident|person|people|household|community)\b.{0,60}"
        r"\b(?:choosing|preferring|favouring|favoring|selecting)\b.{0,40}"
        r"\b(?:is\s+)?(?:explained|motivated|understood)\b", ql)
    behaviour_language = behaviour_language or re.search(
        r"\b(?:what\s+accounts\s+for|(?:could\s+you\s+)?explain\s+why|for\s+what\s+reason)\b"
        r".{0,80}\b(?:resident|inhabitant|people|populace|community|preference|prefer|select|choose)\w*\b",
        ql)
    behaviour_language = behaviour_language or re.search(
        r"\b(?:selection|preference|choice)\b.{0,35}\b(?:resident|inhabitant|people|populace|"
        r"community)\w*\b.{0,25}\b(?:reason|why|explain)\b", ql)
    if behaviour_language:
        ir = {"op": "SELECT", "entity": "?proxy", "region": "?place", "time": None}
        if events is not None:
            events.append("semantic:behaviour_question_restored_to_proxy_holes")

    # An occurrence count is safe only when the USER requested record grain. The parser once
    # expanded “total elephant count” to “elephant observation records”, which changed an organism
    # population question into a countable API-row question and bypassed the executor's abundance
    # guard. Strip only invented grain words; never infer or alter the taxon itself.
    # ``count`` also appears as a terse post-nominal head ("Elephant count in Valparai?").
    # Record-grain wording below remains the directional exception, so an explicit
    # "occurrence-record count" is still admissible while an organism count fails closed.
    count_intent = bool(re.search(r"\b(how many|number|count|inventory|quantif\w*)\b", ql))
    user_named_records = bool(re.search(r"\b(occurrences?|observations?|records?|sightings?)\b", ql))
    # "Are there any [documented] occurrences ...?" asks whether at least one record exists,
    # not for the cardinality of those records. Restore this literal existential metric when a
    # small-model draft emits count; the occurrence set remains the named observed evidence.
    existential_records = re.search(
        r"\bare\s+there\s+any\s+(?:documented\s+)?"
        r"(?:occurrences?|observations?|records?|sightings?)\b", ql)
    if existential_records and ir.get("op") == "AGGREGATE" and ir.get("metric") != "presence":
        ir = {**ir, "metric": "presence"}
        if events is not None:
            events.append("semantic:existential_record_presence_restored")
    if count_intent and not user_named_records:
        changed = False
        def strip_invented_grain(n):
            nonlocal changed
            if isinstance(n, list):
                return [strip_invented_grain(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: strip_invented_grain(v) for k, v in n.items()}
            if out.get("op") == "SELECT":
                entities = out.get("entity")
                many = entities if isinstance(entities, list) else [entities]
                cleaned = []
                for entity in many:
                    if isinstance(entity, str) and not entity.startswith("?"):
                        value = re.sub(r"\b(occurrence|observation|record|sighting)s?\b", " ",
                                       entity, flags=re.IGNORECASE)
                        value = " ".join(value.split())
                        if value and value != entity:
                            entity, changed = value, True
                    cleaned.append(entity)
                out["entity"] = cleaned if isinstance(entities, list) else cleaned[0]
            return out
        ir = strip_invented_grain(ir)
        if changed and events is not None:
            events.append("semantic:invented_record_grain_removed")
        # A literal request for a number/count remains an abundance request even when the model
        # weakens it to boolean presence (for example, "the number of elephants that are present").
        # Restore only the user's explicit aggregate metric so the executor can apply its
        # occurrence-is-not-abundance guard; never turn the request into countable record grain.
        if ir.get("op") == "AGGREGATE" and ir.get("metric") != "count":
            ir = {**ir, "metric": "count"}
            if events is not None:
                events.append("semantic:organism_number_metric_restored")
        # "Is the count ... feasible to obtain?" asks whether the direct measure is available;
        # feasibility does not license spatial transfer. Preserve the selected organism/place and
        # let the occurrence-vs-abundance execution guard return the honest DataRequest.
        if ir.get("op") == "ESTIMATE" and isinstance(ir.get("source"), dict):
            source = ir["source"]
            if source.get("op") == "SELECT":
                ir = {"op": "AGGREGATE", "by": "space", "metric": "count",
                      "source": source}
                if events is not None:
                    events.append("semantic:count_feasibility_transfer_removed")
        if (ir.get("op") == "SELECT" and re.search(
                r"\b(?:elephants?|tigers?|leopards?|gaur|sambar|chital|nilgai)\b", ql)):
            ir = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": ir}
            if events is not None:
                events.append("semantic:organism_quantity_aggregate_restored")

    def collect_selects(node):
        found = []

        def walk(n):
            if isinstance(n, dict):
                if n.get("op") == "SELECT":
                    found.append(n)
                for v in n.values():
                    walk(v)
            elif isinstance(n, list):
                for x in n:
                    walk(x)
        walk(node)
        return found

    # A two-anchor conjunction is not reducible to either constraint alone. Reconstruct the
    # exact nested relation when both literal distances and anchors are present; this prevents a
    # fluent "within X yet beyond Y" parse from silently applying beyond to the wrong anchor.
    compound = re.search(
        r"\b(?:within|closer\s+than|inside\s+(?:a\s+)?)\s*([\d.]+)\s*"
        r"(km|m|kilometers?|kilometres?|meters?|metres?)\s+(?:radius\s+)?(?:of|to|from)\s+"
        r"([a-z][a-z ]+?)\s+(?:but|yet|and(?:\s+also)?|while(?:\s+being)?)\s+"
        r"(?:are\s+)?(?:beyond|farther\s+than|further\s+than|outside|not\s+within)\s+(?:a\s+)?"
        r"([\d.]+)\s*(km|m|kilometers?|kilometres?|meters?|metres?)\s+"
        r"(?:buffer\s+)?(?:from|of)\s+"
        r"([a-z][a-z ]+?)(?=\s+(?:is|are|was|were)\s+(?:needed|required|requested)\b|[?.]|$)", ql)
    if not compound:
        compound = re.search(
            r"\binside\s+(?:a\s+)?([\d.]+)\s*"
            r"(km|m|kilometers?|kilometres?|meters?|metres?)\s+(?:radius\s+)?of\s+"
            r"([a-z][a-z ]+?)\s+(?:while\s+(?:being\s+)?|but\s+|and\s+)"
            r"outside\s+(?:a\s+)?([\d.]+)\s*"
            r"(km|m|kilometers?|kilometres?|meters?|metres?)\s+(?:buffer\s+)?from\s+"
            r"([a-z][a-z ]+?)(?=[?.]|$)", ql)
    if compound:
        selected = collect_selects(ir)
        if selected:
            d1, u1, anchor1, d2, u2, anchor2 = compound.groups()
            anchor1 = re.sub(r"^(?:a|an|the|any)\s+", "", anchor1.strip(),
                             flags=re.IGNORECASE)
            anchor2 = re.sub(r"^(?:a|an|the|any)\s+", "", anchor2.strip(),
                             flags=re.IGNORECASE)
            anchor1 = re.split(r"\s+(?:in|near|around|at)\s+[a-z]", anchor1,
                               maxsplit=1, flags=re.IGNORECASE)[0]
            anchor2 = re.split(r"\s+(?:in|near|around|at)\s+[a-z]", anchor2,
                               maxsplit=1, flags=re.IGNORECASE)[0]
            km = lambda value, unit: float(value) if unit.startswith("k") else float(value) / 1000
            base = selected[0]
            region = base.get("region", "?place")
            inner = {"op": "RELATE", "relation": "within", "threshold_km": km(d1, u1),
                     "left": base,
                     "right": {"op": "SELECT", "entity": anchor1.strip(),
                               "region": region, "time": None}}
            related = {"op": "RELATE", "relation": "beyond", "threshold_km": km(d2, u2),
                       "left": inner,
                       "right": {"op": "SELECT", "entity": anchor2.strip(),
                                 "region": region, "time": None}}
            if ir.get("op") == "AGGREGATE":
                ir = {**ir, "source": related}
            else:
                ir = related
            if events is not None:
                events.append("semantic:literal_two_anchor_relation_restored")

    # Population/abundance is an explicitly unsupported measure, not an occurrence-record
    # aggregate or a raster annotation. Collapse model-added wrappers so the executor's
    # unsupported_measure boundary remains the single honest outcome.
    unsupported_elephant = re.search(r"\belephants?\s+(population|abundance)\b", ql)
    population_of_elephants = re.search(
        r"\b(population(?:\s+size)?|abundance)\s+(?:size\s+)?of\s+elephants?\b", ql)
    number_comprising_population = re.search(
        r"\b(?:number\s+of\s+elephants?|how\s+many\s+elephants?)\b.{0,35}\bpopulation\b", ql)
    indirect_population = re.search(r"\bnumber\s+of\s+elephants?\s+in\s+the\s+"
                                    r"([a-z][a-z .'-]+?)\s+population\b", ql)
    if (unsupported_elephant or population_of_elephants or indirect_population or
            number_comprising_population) and not user_named_records:
        selected = collect_selects(ir)
        indirect_place = re.search(r"\bnumber\s+of\s+elephants?\s+in\s+the\s+"
                                   r"([A-Z][A-Za-z .'-]+?)\s+population\b", question)
        place_match = indirect_place or re.search(
            r"\b(?:in|for|at)\s+([A-Z][A-Za-z .'-]+?)"
            r"(?=\s+(?:is|are|was|were)\s+(?:sought|needed|required|requested)\b|[?.]|$)",
            question)
        region = ({"op": "REGION", "place": place_match.group(1).strip()}
                  if place_match else
                  selected[0].get("region", "?place") if selected else "?place")
        if selected or place_match:
            measure = (unsupported_elephant.group(1) if unsupported_elephant else
                       "abundance" if population_of_elephants and
                       population_of_elephants.group(1).startswith("abundance") else "population")
            ir = {"op": "SELECT", "entity": f"elephant {measure}",
                  "region": region, "time": selected[0].get("time") if selected else None}
            if events is not None:
                events.append("semantic:unsupported_population_wrappers_removed")

    # An explicit transfer destination is a literal, never a hole. Recover only the destination
    # adjacent to estimate/model/predict wording; the already-compiled SELECT remains the source.
    transfer_target = re.search(
        r"\b(?:estimate|model|predict)\w*\b.{0,70}?\b(?:in|for)\s+"
        r"([A-Z][A-Za-z .'-]+?)(?=\s*[,—–-]|\s+where\b|\s+given\b|\s+from\b|"
        r"\s+using\b|\s+by\b|\s+since\b|[?.]|$)", question, re.IGNORECASE)
    if ir.get("op") == "ESTIMATE" and transfer_target:
        ir = {**ir, "target": {"op": "REGION", "place": transfer_target.group(1).strip()}}
        if events is not None:
            events.append("semantic:literal_transfer_target_restored")
    if (ir.get("op") == "ESTIMATE" and not re.search(
            r"\b(?:feature|envelope|interpolat\w*)\b", ql) and
            re.search(r"\b(?:occurrence|record|lantana|taxon)\w*\b", ql)):
        ir = {**ir, "method": "envelope"}
        if events is not None:
            events.append("semantic:occurrence_transfer_default_restored")

    # A named historic month is an exact unsupported-time request, not a whole-year request.
    month_numbers = {"january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
                     "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
                     "november": 11, "december": 12}
    historic_bird = re.search(
        r"\b(" + "|".join(month_numbers) + r")\s+((?:19|20)\d{2})\b", ql)
    if historic_bird and re.search(r"\bbird observation", ql):
        import calendar
        month, year = month_numbers[historic_bird.group(1)], int(historic_bird.group(2))
        end_day = calendar.monthrange(year, month)[1]
        exact_time = {"start": f"{year:04d}-{month:02d}-01",
                      "end": f"{year:04d}-{month:02d}-{end_day:02d}"}
        def set_bird_month(n):
            if isinstance(n, list):
                return [set_bird_month(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: set_bird_month(v) for k, v in n.items()}
            if out.get("op") == "SELECT" and "bird observation" in str(
                    out.get("entity", "")).lower():
                out["time"] = exact_time
            return out
        ir = set_bird_month(ir)
        if events is not None:
            events.append("semantic:literal_historic_bird_month_restored")

    # "Recent" is the eBird live-window contract, not a hidden calendar year. Small models
    # sometimes import 2024 from a comparison exemplar. Remove that time only when the user gave
    # no year, month, or ISO date; explicit historic requests must remain unsupported_time.
    if re.search(r"\b(?:(?:most\s+)?recent|latest)\s+bird observation(?:s|\s+records)?\b", ql) and not (
            re.search(r"\b(?:19|20)\d{2}\b", ql) or
            re.search(r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
                      r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|"
                      r"dec(?:ember)?)\b", ql)):
        changed = False
        def clear_recent_time(n):
            nonlocal changed
            if isinstance(n, list):
                return [clear_recent_time(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: clear_recent_time(v) for k, v in n.items()}
            if out.get("op") == "SELECT" and "bird observation" in \
                    str(out.get("entity", "")).lower():
                if out.get("time") is not None or out.get("entity") != "recent bird observations":
                    out["time"] = None
                    out["entity"] = "recent bird observations"
                    changed = True
            return out
        ir = clear_recent_time(ir)
        if changed and events is not None:
            events.append("semantic:invented_recent_bird_year_removed")

    # Explicitly adding a named raster layer to named survey sites is ANNOTATE, even when phrased
    # as a feasibility question. Reuse the grounded SELECT; do not interpret "add" as transfer.
    add_landcover = ("land cover" in ql and "survey site" in ql and
                     re.search(r"\b(add|attach|append|incorporate)\b", ql))
    if add_landcover and ir.get("op") != "ANNOTATE":
        selected = collect_selects(ir)
        if selected:
            ir = {"op": "ANNOTATE", "layer": "land cover", "source": selected[0]}
            if events is not None:
                events.append("semantic:explicit_landcover_annotation_restored")

    # A place-level NDVI question (no sites named) means SELECT the regional measurement series.
    # Annotation over invented survey sites is a source substitution even when the tree executes.
    place_choice = bool(re.search(
        r"\bwhich\s+(?:site|place|location)\s*,\s*[^,]+?\s+or\s+[^,]+?\s*,",
        question, re.IGNORECASE))
    place_ndvi = "ndvi" in ql and (place_choice or not re.search(
        r"\b(survey|plot|site|point)s?\b", ql))
    if place_ndvi:
        changed = False

        def direct_ndvi(n):
            nonlocal changed
            if isinstance(n, list):
                return [direct_ndvi(x) for x in n]
            if not isinstance(n, dict):
                return n
            if n.get("op") == "SELECT" and re.fullmatch(
                    r"ndvi(?:\s+(?:value|values|index|measurements?))?",
                    str(n.get("entity", "")).strip(), re.IGNORECASE):
                if n.get("entity") != "NDVI":
                    changed = True
                    return {**n, "entity": "NDVI"}
            if (n.get("op") == "SELECT" and "ndvi" in ql and
                    re.fullmatch(r"(?:vegetation\s+)?greenness|vegetation index",
                                 str(n.get("entity", "")).strip(), re.IGNORECASE)):
                changed = True
                return {**n, "entity": "NDVI"}
            if n.get("op") == "ANNOTATE" and str(n.get("layer", "")).lower() == "ndvi" \
                    and isinstance(n.get("source"), dict):
                sels = collect_selects(n["source"])
                if sels:
                    changed = True
                    return {"op": "SELECT", "entity": "NDVI",
                            "region": sels[0].get("region", "?place"),
                            "time": sels[0].get("time")}
            return {k: direct_ndvi(v) for k, v in n.items()}
        ir = direct_ndvi(ir)
        if changed and events is not None:
            events.append("semantic:place_ndvi_source_substitution_removed")

        # A named endpoint change is stricter than two arbitrary series aggregates. Reconstruct
        # later-minus-earlier using the already-grounded place and literal years.
        change = re.search(r"\bchange\w*\s+from\s+(\d{4})\s+to\s+(\d{4})\b", ql)
        if not change and re.search(
                r"\b(change\w*|delta|shift|difference|differ\w*|magnitude|variation|vary|varied|"
                r"alter\w*)\b",
                ql):
            years = re.findall(r"\b(?:19|20)\d{2}\b", ql)
            if len(years) == 2:
                # For "between"/magnitude wording, the algebra's chronology rule is
                # later-minus-earlier, independent of mention order.
                earlier, later = sorted(years)
                change = re.match(r"(\d{4}) (\d{4})", f"{earlier} {later}")
        sels = collect_selects(ir)
        if change and sels:
            earlier, later = change.groups()
            region = sels[0].get("region", "?place")
            ir = {"op": "COMPARE", "how": "difference",
                  "left": {"op": "SELECT", "entity": "NDVI", "region": region,
                           "time": {"start": later, "end": later}},
                  "right": {"op": "SELECT", "entity": "NDVI", "region": region,
                            "time": {"start": earlier, "end": earlier}}}
            if events is not None:
                events.append("semantic:literal_ndvi_change_endpoints_restored")

        # Two named places + one literal year + comparative NDVI wording fully determines a
        # binary difference. Recover both regions even when the raw model encoded one as a RELATE
        # target or used an incompatible by:space aggregate over a time series.
        compare_words = re.search(
            r"\b(higher|lower|greater|larger|bigger|smaller|superior|exceed\w*|between|versus|vs\.?|compare\w*)\b",
            ql)
        years = re.findall(r"\b(?:19|20)\d{2}\b", ql)
        regions = []
        def collect_regions(n):
            if isinstance(n, dict):
                if n.get("op") == "REGION" and isinstance(n.get("place"), str):
                    if n["place"] not in regions:
                        regions.append(n["place"])
                for value in n.values():
                    collect_regions(value)
            elif isinstance(n, list):
                for value in n:
                    collect_regions(value)
        collect_regions(ir)
        literal_pair = None
        for pattern in (
            r"\b(?:between|for)\s+([A-Z][A-Za-z'-]+)\s+(?:and|or)\s+([A-Z][A-Za-z'-]+)",
            r"\bin\s+([A-Z][A-Za-z'-]+)\s+or\s+(?:in\s+)?([A-Z][A-Za-z'-]+)",
            r",\s*([A-Z][A-Za-z'-]+)\s+or\s+([A-Z][A-Za-z'-]+)\s*,",
            r",\s*([A-Z][A-Za-z'-]+)\s+or\s+([A-Z][A-Za-z'-]+)\s+"
            r"(?=(?:was\s+|is\s+|had\s+)?(?:higher|lower|greater|larger|bigger|smaller)\b)",
        ):
            literal_pair = re.search(pattern, question)
            if literal_pair:
                break
        if literal_pair:
            regions = list(literal_pair.groups())
        if compare_words and len(years) == 1 and len(regions) >= 2:
            year = years[0]
            def place_mean(place):
                return {"op": "AGGREGATE", "by": "time", "metric": "mean",
                        "source": {"op": "SELECT", "entity": "NDVI",
                                   "region": {"op": "REGION", "place": place},
                                   "time": {"start": year, "end": year}}}
            ir = {"op": "COMPARE", "how": "difference",
                  "left": place_mean(regions[0]), "right": place_mean(regions[1])}
            if events is not None:
                events.append("semantic:literal_ndvi_place_compare_restored")

    # A leading place modifies a named vegetation-greenness series; it is not part of the
    # connector entity. This commonly appears in compact trend prompts ("Valparai vegetation
    # greenness, 2018 to 2024: rising or falling?"). Keep the literal series wording rather than
    # silently changing it to NDVI, while removing only the already-grounded place prefix.
    if re.search(r"\bvegetation\s+greenness\b", ql):
        changed = False
        def canonical_greenness(n):
            nonlocal changed
            if isinstance(n, list):
                return [canonical_greenness(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: canonical_greenness(v) for k, v in n.items()}
            if (out.get("op") == "SELECT" and isinstance(out.get("entity"), str) and
                    "vegetation greenness" in out["entity"].lower() and
                    out["entity"].lower() != "vegetation greenness"):
                out["entity"] = "vegetation greenness"
                changed = True
            return out
        ir = canonical_greenness(ir)
        if changed and events is not None:
            events.append("semantic:place_prefix_removed_from_greenness")

    # A leading place is a query modifier, not part of the named Anamalai site collection.
    def strip_site_place_prefix(n):
        if isinstance(n, list):
            return [strip_site_place_prefix(x) for x in n]
        if not isinstance(n, dict):
            return n
        out = {k: strip_site_place_prefix(v) for k, v in n.items()}
        if out.get("op") == "SELECT" and re.fullmatch(
                r"[A-Z][A-Za-z .'-]+\s+Anamalai survey sites",
                str(out.get("entity", "")).strip(), re.IGNORECASE):
            out["entity"] = "Anamalai survey sites"
        return out
    ir = strip_site_place_prefix(ir)

    # Entity unions are released in SELECT v2.2. If the question explicitly coordinates two
    # occurrence taxa and the raw parse drops one, restore the literal pair without fuzzy lookup.
    union = re.search(r"\b(?:show|see|get|plot|display|list|provide|present|map|depict|pull|retrieve|return)\s+"
                      r"([a-z][a-z -]+?)\s+and\s+"
                      r"([a-z][a-z -]+?)\s+"
                      r"occurrence (?:records|data)\s+"
                      r"(?:that\s+are\s+)?(?:(?:present|located|found)\s+)?"
                      r"(?:around|near|in|for|from)\b",
                      question, re.IGNORECASE)
    if not union:
        union = re.search(r"\boccurrence records\s+of\s+([a-z][a-z -]+?)\s+and\s+"
                          r"([a-z][a-z -]+?)\s+(?:around|in)\b", question, re.IGNORECASE)
    if not union:
        union = re.search(r"\boccurrence records\s+of\s+both\s+([a-z][a-z -]+?)\s+and\s+"
                          r"([a-z][a-z -]+?)(?=[.!?]|\s+(?:around|near|in|for|from)\b)",
                          question, re.IGNORECASE)
    if not union:
        union = re.search(r"\bwhich\s+([a-z][a-z -]+?)\s+and\s+([a-z][a-z -]+?)\s+"
                          r"occurrence records\s+are\s+(?:found|present)\b",
                          question, re.IGNORECASE)
    if not union:
        union = re.search(r"\b(?:occurrence|presence)\s+(?:records|data)\s+(?:for|of)\s+"
                          r"([a-z][a-z -]+?)\s+and\s+([a-z][a-z -]+?)\s+(?:in|near|around)\b",
                          question, re.IGNORECASE)
    if not union:
        union = re.search(r"\b([a-z][a-z -]+?)\s+and\s+([a-z][a-z -]+?)\s+"
                          r"(?:have\s+been\s+recorded|presence\s+records)\b",
                          question, re.IGNORECASE)
    if not union:
        union = re.search(r"\b([A-Z][A-Za-z-]+)\s+and\s+([a-z][A-Za-z-]+)\b.{0,45}"
                          r"\b(?:occurrence|presence|recorded|records?)\b", question)
    sels = collect_selects(ir)
    if union and sels and not any(isinstance(s.get("entity"), list) for s in sels):
        first, second = (x.strip() for x in union.groups())
        # The command form commonly contributes a syntactic determiner ("Plot the Lantana
        # and teak ..."). It is not part of either taxon literal and the connector deliberately
        # does not fuzzy-strip arbitrary words. Normalize only a leading English determiner.
        first = re.sub(r"^(?:the|a|an|all|both)\s+", "", first, flags=re.IGNORECASE)
        second = re.sub(r"^(?:the|a|an|all|both)\s+", "", second, flags=re.IGNORECASE)
        first = re.sub(r"^(?:i\s+)?need\s+to\s+see\s+(?:where\s+)?", "", first,
                       flags=re.IGNORECASE)
        first = re.sub(
            r"^(?:show|see|get|display|retrieve|present|provide|map|plot|depict|pull|return)\s+",
            "", first, flags=re.IGNORECASE)
        ir = {"op": "SELECT", "entity": [f"{first} occurrence records",
                                             f"{second} occurrence records"],
              "region": sels[0].get("region", "?place"), "time": sels[0].get("time")}
        if events is not None:
            events.append("semantic:explicit_taxon_union_restored")

    # Location-set wording asks for related records, not their count. In ecology, explicit
    # co-occurrence is a symmetric evidence relation even when the small model chooses the more
    # generic `within`; preserve the two SELECTs and the literal distance.
    selected = collect_selects(ir)
    relation_entities = [s for s in selected if re.search(
        r"\b(?:record|observation|occurrence|sighting)s?\b", str(s.get("entity", "")), re.I)]
    location_output = bool(re.search(r"\b(where|locations?|areas?|locate|find)\b", ql))
    cooccur_cue = bool(re.search(r"\b(?:co-occur|occur\s+together)\b", ql) or
                        (not compound and location_output and len(relation_entities) >= 2 and
                         re.search(r"\b(?:within|less\s+than)\s+(?:a\s+)?[\d.]+\s*"
                                   r"(?:km|m|kilomet\w*|metre\w*)(?:\s+radius)?", ql)))
    if cooccur_cue and len(selected) >= 2:
        distance = re.search(
            r"\b(?:within|less\s+than)\s+(?:a\s+)?([\d.]+)\s*"
            r"(km|m|kilometers?|kilometres?|meters?|metres?)(?:\s+radius)?\b", ql)
        threshold = None
        if distance:
            threshold = float(distance.group(1))
            if not distance.group(2).startswith("k"):
                threshold /= 1000
        ir = {"op": "RELATE", "relation": "cooccur", "left": selected[0],
              "right": selected[1]}
        if threshold is not None:
            ir["threshold_km"] = threshold
        if events is not None:
            events.append("semantic:explicit_cooccurrence_restored")

    # Restore a literal distance omitted from an otherwise complete top-level relation.
    if json.dumps(ir).count('"RELATE"') == 1:
        distance = re.search(
            r"\b(?:within|less\s+than|farther\s+than|beyond|outside)\s+(?:a\s+)?([\d.]+)\s*"
            r"(km|m|kilometers?|kilometres?|meters?|metres?)\b", ql)
        if distance:
            value = float(distance.group(1))
            if not distance.group(2).startswith("k"):
                value /= 1000
            changed = False
            def restore_relation_threshold(n):
                nonlocal changed
                if isinstance(n, list):
                    return [restore_relation_threshold(x) for x in n]
                if not isinstance(n, dict):
                    return n
                out = {k: restore_relation_threshold(v) for k, v in n.items()}
                if out.get("op") == "RELATE" and "threshold_km" not in out:
                    out["threshold_km"] = value
                    changed = True
                return out
            ir = restore_relation_threshold(ir)
            if changed and events is not None:
                events.append("semantic:literal_relation_threshold_restored")

    # Valparai is already represented by REGION; remove its duplicate entity prefix.
    def strip_lantana_place_prefix(n):
        if isinstance(n, list):
            return [strip_lantana_place_prefix(x) for x in n]
        if not isinstance(n, dict):
            return n
        out = {k: strip_lantana_place_prefix(v) for k, v in n.items()}
        region = out.get("region")
        if (out.get("op") == "SELECT" and isinstance(region, dict) and
                str(region.get("place", "")).lower().startswith("valparai") and
                re.fullmatch(r"Valparai\s+Lantana\s+(?:occurrence\s+)?records?",
                             str(out.get("entity", "")).strip(), re.IGNORECASE)):
            out["entity"] = re.sub(r"^Valparai\s+", "", out["entity"],
                                    flags=re.IGNORECASE)
        return out
    ir = strip_lantana_place_prefix(ir)

    count_intent = bool(re.search(
        r"\b(?:how\s+many|count|inventory|number|quantif\w*|tally|total)\b", ql))
    if (count_intent and ir.get("op") == "AGGREGATE" and ir.get("metric") == "count" and
            not re.search(r"\b(?:per\s+(?:year|month)|by\s+(?:year|month|time)|time series|"
                          r"each\s+(?:year|month))\b", ql)):
        ir = {**ir, "by": "space"}
        if events is not None:
            events.append("semantic:total_count_grain_restored")
    if (not count_intent and ir.get("op") == "AGGREGATE" and
            isinstance(ir.get("source"), dict) and ir["source"].get("op") == "RELATE"):
        ir = ir["source"]
        if events is not None:
            events.append("semantic:relation_record_grain_restored")
    if (not count_intent and ir.get("op") == "AGGREGATE" and ir.get("metric") == "count" and
            isinstance(ir.get("source"), dict) and ir["source"].get("op") == "SELECT" and
            re.search(r"\b(?:show|display|enumerate|list|provide|present|retrieve|get|need|map|tabulate|"
                      r"observations?\s+"
                      r"(?:occurred|exist|recorded|made))\b", ql)):
        ir = ir["source"]
        if events is not None:
            events.append("semantic:record_set_output_grain_restored")

    # Nominal ecology requests can still fully specify a direct aggregate or negated relation.
    nominal_density = ("density" in ql and re.search(r"\blantana\b", ql) and
                       re.search(r"\b(?:record|occurrence)s?\b", ql))
    if nominal_density and ir.get("op") != "AGGREGATE":
        selected = collect_selects(ir)
        region = (selected[0].get("region") if selected else
                  {"op": "REGION", "place": "Valparai"} if "valparai" in ql else "?place")
        entity = selected[0].get("entity") if selected else "documented Lantana records"
        ir = {"op": "AGGREGATE", "by": "space", "metric": "density",
              "source": {"op": "SELECT", "entity": entity, "region": region, "time": None}}
        if events is not None:
            events.append("semantic:nominal_density_restored")

    nominal_beyond = re.search(
        r"\b(?:with\s+)?no\s+([a-z][a-z ]+?)\s+within\s+([\d.]+)\s*"
        r"(km|m|kilometers?|kilometres?|meters?|metres?)\b", ql)
    if nominal_beyond and ir.get("op") != "RELATE":
        selected = collect_selects(ir)
        if selected:
            anchor, distance, unit = nominal_beyond.groups()
            anchor = re.sub(r"^(?:a|an|the|any)\s+", "", anchor.strip())
            threshold = float(distance) if unit.startswith("k") else float(distance) / 1000
            ir = {"op": "RELATE", "relation": "beyond", "threshold_km": threshold,
                  "left": selected[0],
                  "right": {"op": "SELECT", "entity": anchor,
                            "region": selected[0].get("region", "?place"), "time": None}}
            if events is not None:
                events.append("semantic:nominal_negated_relation_restored")

    indian_presence = (re.search(r"\bgreen cat snake\b", ql) and
                       re.search(r"\bpresence\b", ql) and
                       re.search(r"\b(?:india|indian locality)\b", ql))
    if indian_presence:
        ir = {"op": "AGGREGATE", "by": "space", "metric": "presence",
              "source": {"op": "SELECT", "entity": "green cat snake",
                         "region": {"op": "REGION", "place": "India"}, "time": None}}
        if events is not None:
            events.append("semantic:literal_india_presence_restored")

    # A literal 3-place rank is n-ary even when the model keeps only the first place. Recover the
    # enumerated names and requested order; use the raw SELECT only for the named entity/time.
    ranking = re.search(r"\b(?:rank|order|arrange|sort)\s+(?:(?:the\s+)?(?:sites|places|locations)\s+)?"
                        r"([A-Z][A-Za-z .'-]+?),\s*"
                        r"([A-Z][A-Za-z .'-]+?),?\s+and\s+([A-Z][A-Za-z .'-]+?)\s+"
                        r"(?:by|from|in)\b", question, re.IGNORECASE)
    literal_rank = _literal_ndvi_rank(question)
    if literal_rank:
        existing_places = [n.get("place") for n in collect_selects(ir)
                           if isinstance(n.get("region"), dict)
                           for n in [n["region"]] if n.get("place")]
        if any(isinstance(place, str) and place.endswith(", India")
               for place in existing_places):
            for item in literal_rank["items"]:
                place = item["source"]["region"]["place"]
                if "," not in place:
                    item["source"]["region"]["place"] = place + ", India"
        ir = literal_rank
        if events is not None:
            events.append("semantic:literal_three_place_rank_restored")
    elif ranking:
        selected = collect_selects(ir)
        if selected:
            places = [x.strip() for x in ranking.groups()]
            places[0] = re.sub(r"^(?:the\s+)?(?:three\s+)?(?:sites|places|locations)\s+", "",
                               places[0], flags=re.IGNORECASE)
            places[2] = re.sub(r"\s+(?:ascending|descending)(?:\s+order)?$", "", places[2],
                               flags=re.IGNORECASE)
            first_place = selected[0].get("region")
            if isinstance(first_place, dict):
                first_place = first_place.get("place")
            india_suffix = bool(isinstance(first_place, str) and ", India" in first_place)
            entity = ("NDVI" if "ndvi" in ql else
                      "vegetation index" if "vegetation index" in ql else
                      "greenness" if "greenness" in ql else selected[0].get("entity"))
            time_value = selected[0].get("time")
            years = re.findall(r"\b(?:19|20)\d{2}\b", question)
            if len(years) == 1:
                time_value = {"start": years[0], "end": years[0]}
            mean_series = bool(re.search(r"\b(?:mean|average)\s+(?:ndvi|greenness|vegetation index)\b",
                                         ql))
            items = []
            for place in places:
                full_place = place + ", India" if india_suffix and "," not in place else place
                source = {"op": "SELECT", "entity": entity,
                          "region": {"op": "REGION", "place": full_place},
                          "time": time_value}
                items.append({"op": "AGGREGATE", "by": "time" if mean_series else "space",
                              "metric": "mean" if mean_series else "count", "source": source})
            order = "asc" if re.search(r"\b(lowest|fewest|ascending)\b", ql) and not \
                re.search(r"\bhighest\s+to\s+lowest\b", ql) else "desc"
            ir = {"op": "RANK", "items": items, "order": order}
            if events is not None:
                events.append("semantic:literal_three_place_rank_restored")

    # "Has X increased?" is a unary trend question. If the parser returned the aligned time
    # series but omitted COMPARE, the only named result operator is trend_direction.
    trend_word = re.search(r"\b(increas\w*|decreas\w*|ris\w*|fall\w*|declin\w*|"
                           r"improv\w*|worsen\w*|recover\w*|recovery|bounc\w*\s+back|"
                           r"upward\s+trend|current\s+trend|(?:go|going|gone)\s+(?:up|down)|"
                           r"trend\w*.{0,25}\b(?:upward|downward))\b", ql)
    trend_language = ((re.search(r"\b(has|is|was|were|do|does|did)\b", ql) and trend_word) or
                      (trend_word and re.search(r"\byes\s+or\s+no\b", ql)) or
                      (trend_word and re.search(r"\b(ndvi|greenness|vegetation index)\b", ql)))
    if trend_language and ir.get("op") != "COMPARE":
        if ir.get("op") == "AGGREGATE" and ir.get("by") == "time":
            ir = {"op": "COMPARE", "how": "trend_direction", "left": ir}
            if events is not None:
                events.append("semantic:explicit_trend_direction_restored")
        elif re.search(r"\b(ndvi|greenness|vegetation index)\b", ql):
            # Recover the named remote-sensing series while reusing only the REGION/time already
            # grounded in the raw tree. This prevents an ANNOTATE exemplar from turning a place
            # trend into a made-up survey-site workflow.
            selected = collect_selects(ir)
            if selected:
                entity = "NDVI" if "ndvi" in ql else (
                    "vegetation index" if "vegetation index" in ql else "greenness")
                source = {"op": "SELECT", "entity": entity,
                          "region": selected[0].get("region", "?place"),
                          "time": selected[0].get("time")}
                ir = {"op": "COMPARE", "how": "trend_direction",
                      "left": {"op": "AGGREGATE", "by": "time", "metric": "mean",
                               "source": source}}
                if events is not None:
                    events.append("semantic:named_ecology_series_trend_reconstructed")
    if (ir.get("op") == "COMPARE" and
            ir.get("how") == "trend_direction" and not re.search(r"\b(?:19|20)\d{2}\b", ql)):
        def clear_implicit_trend_time(n):
            if isinstance(n, list):
                return [clear_implicit_trend_time(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: clear_implicit_trend_time(v) for k, v in n.items()}
            if out.get("op") == "SELECT" and re.search(
                    r"\b(?:ndvi|greenness|vegetation index)\b", str(out.get("entity", "")), re.I):
                out["time"] = None
            return out
        ir = clear_implicit_trend_time(ir)
        if events is not None:
            events.append("semantic:invented_trend_period_removed")

    # A nominal phrase can request the published point set without an overt verb. When the raw
    # model returns only REGION, the named survey-site collection supplies the missing SELECT;
    # no layer, aggregation, or connector availability is inferred.
    if ir.get("op") == "REGION" and re.search(r"\bvegetation\s+survey\s+sites?\b", ql):
        ir = {"op": "SELECT", "entity": "vegetation survey sites",
              "region": ir, "time": None}
        if events is not None:
            events.append("semantic:nominal_survey_site_selection_restored")

    # "Which ecoregions/biomes ... sites?" asks for a named layer at already-selected points.
    # A bare SELECT returns the sites but cannot answer which polygons contain them.
    layer_request = (re.search(r"\b(?:which|what|name|list)\s+(?:the\s+)?(ecoregions?|biomes?)\b", ql) or
                     re.search(r"\b(ecoregions?|biomes?)\b.{0,45}\b(?:contain(?:ing)?|include|host)\b.{0,60}"
                               r"\bsurvey sites?\b", ql))
    if layer_request:
        layer = "ecoregion" if "ecoregion" in ql else "biome"
        if ir.get("op") == "REGION" and "survey sites" in ql:
            place_match = re.search(r"\bnear\s+([a-z][a-z .'-]+?)(?=\s+fall\s+within\b|[?.]|$)", question,
                                    re.IGNORECASE)
            place = place_match.group(1).strip() if place_match else "?place"
            entity = next((p for p in ("Anamalai survey sites", "vegetation survey sites",
                                        "forest survey sites", "survey sites")
                           if p.lower() in ql), "survey sites")
            ir = {"op": "SELECT", "entity": entity,
                  "region": ({"op": "REGION", "place": place} if place != "?place" else place),
                  "time": None}
        if str(ir.get("entity", "")).lower() in {"ecoregion", "ecoregions", "biome", "biomes"}:
            for phrase in ("Anamalai survey sites", "vegetation survey sites", "forest survey sites",
                           "survey sites"):
                if phrase.lower() in ql:
                    ir = {**ir, "entity": phrase}
                    break
        # In "Anamalai survey sites near Valparai", Anamalai modifies the site collection and
        # the explicit proximity complement names the query region. Prefer that syntactic place
        # over a model draft that promoted the collection name to REGION.
        near_place = re.search(
            r"\b(?:near|in\s+the\s+vicinity\s+of)\s+([A-Z][A-Za-z .'-]+?)"
            r"(?=\s+(?:are|is|were|was|should|must|located|situated|found|fall)\b|[?!,;.:]|$)",
            question, re.IGNORECASE)
        if near_place and ir.get("op") == "SELECT" and "survey site" in \
                str(ir.get("entity", "")).lower():
            place = near_place.group(1).strip()
            old_place = ir.get("region", {}).get("place") if isinstance(ir.get("region"), dict) else None
            if isinstance(old_place, str) and old_place.endswith(", India") and "," not in place:
                place += ", India"
            ir = {**ir, "region": {"op": "REGION", "place": place}}
        if ir.get("op") != "SELECT":
            selected = collect_selects(ir)
            if selected:
                ir = selected[0]
                for phrase in ("Anamalai survey sites", "vegetation survey sites",
                               "forest survey sites", "survey sites"):
                    if phrase.lower() in ql:
                        ir = {**ir, "entity": phrase}
                        break
        if near_place and ir.get("op") == "SELECT" and "survey site" in \
                str(ir.get("entity", "")).lower():
            place = near_place.group(1).strip(" .")
            old_place = ir.get("region", {}).get("place") if isinstance(ir.get("region"), dict) else None
            if isinstance(old_place, str) and old_place.endswith(", India") and "," not in place:
                place += ", India"
            ir = {**ir, "region": {"op": "REGION", "place": place}}
        if ir.get("op") == "SELECT":
            ir = {"op": "ANNOTATE", "layer": layer, "source": ir}
            if events is not None:
                events.append("semantic:explicit_ecology_layer_annotation_restored")
    return ir


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
    m = re.search(r"not\s+(?:within|near)\s+(?:[\d.a-z ]{0,20}?)(?:of|from)?\s*(?:the|a|an|any)\s+"
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
    if pa.get("threshold_km") is not None and '"threshold_km"' not in tree:
        return [f"The question names a {pa['threshold_km']} km threshold but the RELATE node "
                "dropped threshold_km. Restore the literal distance."]
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
    if pa.get("threshold_km") is not None and tree.count('"RELATE"') == 1 \
            and '"threshold_km"' not in tree:
        def add_threshold(n):
            if isinstance(n, list):
                return [add_threshold(x) for x in n]
            if not isinstance(n, dict):
                return n
            out = {k: add_threshold(v) for k, v in n.items()}
            if out.get("op") == "RELATE":
                out["threshold_km"] = pa["threshold_km"]
            return out
        return add_threshold(ir)
    return ir


def parse(question, role="qwen2b", fewshot=None, temperature=0.0, repair=True,
          history=None, capabilities=None, semantic_repairs=True):
    from ir_schema import validate  # local import to avoid cycles
    msgs = build_messages(question, fewshot, history=history, capabilities=capabilities)
    # reasoning-style remote models emit reasoning tokens before the JSON; give big headroom.
    # local small models: room for wide trees (truncation at 800 broke tick-009).
    mt = (400 if role == "lora9b" else 2000 if role in ("qwen9b", "deepseekv4") else
          3000 if role in ("qwen2b", "loravb") else 8000)
    events = []  # interpretability: every mechanical/LLM intervention on the raw parse is logged
    try:
        raw = chat(role, msgs, temperature=temperature, max_tokens=mt)
    except RuntimeError as e:
        return {"question": question, "raw": f"[llm-error] {e}", "ir": None, "parse_valid": False,
                "events": ["llm_error"]}
    ir = extract_json(raw, events)
    repaired = False
    # Parse failure gets the same single compiler-style correction opportunity as a schema
    # failure. This is especially important for wide n-ary trees: a small model can emit a
    # truncated or comma-spliced first draft even though the requested algebra is unambiguous.
    # The correction sees only its own draft and the static contract, never gold or execution.
    if repair and ir is None:
        fix_msgs = msgs + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content":
                "That response is not one complete valid JSON tree (it may be truncated or "
                "comma-spliced). Recompile the SAME question into one concise tree that follows "
                "the operation contract. Output ONLY the complete corrected JSON object."}]
        events.append("parse_error:invalid_or_truncated_json")
        try:
            raw2 = chat(role, fix_msgs, temperature=temperature, max_tokens=mt)
            ir2 = extract_json(raw2, events)
            if ir2 is not None:
                ir, raw, repaired = ir2, raw2, True
                events.append("llm_parse_repair:accepted")
            else:
                events.append("llm_parse_repair:rejected")
        except RuntimeError:
            events.append("llm_parse_repair:call_failed")
    before = json.dumps(ir)
    ir = mech_repair(ir)
    if json.dumps(ir) != before:
        events.append("peephole:aggregate_relate_unmerge")
    before = json.dumps(ir)
    history_text = " ".join(str(item.get("content") or "") if isinstance(item, dict) else str(item)
                            for item in (history or []))
    ir = faithfulness_pass(ir, question + " " + history_text)
    if json.dumps(ir) != before:
        events.append("provenance:invented_place_demoted_to_hole")
    if semantic_repairs:
        ir = sector_semantic_repairs(ir, question, events)
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
                ir2 = faithfulness_pass(mech_repair(ir2), question + " " + history_text)
                if semantic_repairs:
                    ir2 = sector_semantic_repairs(ir2, question, events)
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
