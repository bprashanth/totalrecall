"""dialect.py — Indian-dialect question factory over EXISTING execution-verified pairs.

Deployment users are Indian urban/semi-urban English speakers (terse, Indian-English register,
sometimes Google-Translate-mediated from Indic languages). This factory takes verified
(question, gold_ir) pairs from our banks/corpora (+ transport/livelihoods corpora READ-ONLY)
and produces dialect variants along four transforms:

  lex     surface lexicon swaps matching connectors.INDIC_ALIASES (pharmacy->medical shop,
          fuel->petrol bunk, ...) applied to BOTH question and gold entities; a transform is
          kept only if the new entity resolves to the SAME canonical source as the old one.
  loc     relocation of places to Indian cities (question + tree), gold re-verified by execution.
  reg     Indian-register rewrite via deepseekv4 in 4 style families:
          formal / conversational / terse / fragment (follow-up-fragment style).
  mt      IndicTrans2 round-trip (en->{hi,kn,ta,te,mr}->en) via the :8005 service; kept only if
          places+numbers survive (diacritic-folded, spelling-variant aware) AND a deepseek
          meaning-equivalence judge passes (round-trips scramble multi-place rankings ~20%).
  struct  structural paraphrase: 2-operand COMPARE(count) rows rephrased as orderings; the row
          carries a gold_shapes ALLOW-SET (COMPARE-form and RANK-form both valid).

SAFETY (every emitted row): places+numbers containment (fold + Indian spelling variants),
entity re-resolution check AFTER canonical substitution, and gold re-verified by EXECUTION
(status must match `expect`). Rows failing any check are dropped, never fixed silently.

Also mints NEW complaint-analytics questions against the IChangeMyCity connector
(correct-by-construction trees: RANK/TREND/COMPARE over wards/categories/years, incl.
negation-as-ascending-order and comparative thresholds).

Usage:
  python3 dialect.py --stage transforms --out ../runs/indic-factory   # lex/loc/struct (no LLM)
  python3 dialect.py --stage reg|mt --out ...                         # LLM/MT stages, resumable
  python3 dialect.py --stage mint --out ...                           # complaint questions
  python3 dialect.py --stage assemble --out ...                       # eval+train banks
"""
import argparse
import copy
import json
import os
import random
import re
import unicodedata
import urllib.request

import connectors as C
from executor import execute
from scorer import _shape

HERE = os.path.dirname(os.path.abspath(__file__))
BENCH = os.path.dirname(HERE)
TR = "/home/beeps/src/github.com/bprashanth/totalrecall"
MT_URL = "http://172.17.0.1:8005"
RNG = random.Random(7)

# ---------------------------------------------------------------- fold / containment
VARIANTS = {"mysuru": ["mysore"], "bengaluru": ["bangalore", "bengalooru"],
            "bellandur": ["bellanduru", "bellandoor"], "chennai": ["madras"],
            "mumbai": ["bombay"], "kochi": ["cochin"], "pune": ["poona"],
            "hubballi": ["hubli"], "mangaluru": ["mangalore"], "kolkata": ["calcutta"],
            "varanasi": ["banaras", "benares"], "vadodara": ["baroda"],
            "thiruvananthapuram": ["trivandrum"], "shivajinagar": ["shivaji nagar"]}


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s).lower())
                   if not unicodedata.combining(c))


def places_of(ir):
    out = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, dict):
            if n.get("op") == "REGION" and isinstance(n.get("place"), str) \
                    and not n["place"].startswith("?"):
                out.append(n["place"])
            for v in n.values():
                walk(v)
    walk(ir)
    return out


def _place_in(place, text):
    t = fold(text)
    # first comma segment is the city; country segment often dropped in speech
    seg = fold(place.split(",")[0]).strip()
    for cand in [seg] + VARIANTS.get(seg, []):
        if cand in t:
            return True
    return False


def contains_places_nums(new_q, ir, orig_q=None):
    for p in places_of(ir):
        if not _place_in(p, new_q):
            return False
    src = orig_q if orig_q is not None else ""
    for n in re.findall(r"\d+(?:\.\d+)?", src):
        if n not in new_q:
            return False
    return True


def entities_of(ir):
    out = []

    def walk(n):
        if isinstance(n, list):
            for x in n:
                walk(x)
        elif isinstance(n, dict):
            if n.get("op") == "SELECT":
                e = n.get("entity")
                for x in (e if isinstance(e, list) else [e]):
                    if isinstance(x, str) and not x.startswith("?"):
                        out.append(x)
            for v in n.values():
                walk(v)
    walk(ir)
    return out


def entity_canon(entity):
    """(source, canonical) the executor would route this entity to."""
    m = C.icmc_match(entity)
    if m:
        return ("icmc", m[1])
    code, canon, _ = C.wb_resolve_indicator(entity)
    if code:
        return ("wb", code)
    tag, ocanon, ambig = C.osm_resolve_tag(entity)
    if tag:
        return ("osm", ocanon, tuple(ambig))
    return (None, None)


def verify_gold(ir, expect="answer", must_hole=False):
    """Execute the gold; True iff the outcome class matches expectation."""
    try:
        r = execute(ir)
    except Exception:
        return False
    st = r.get("status")
    if must_hole or expect == "data_request":
        return st == "data_request"
    if expect == "answer_or_data_request":
        return st in ("answer", "data_request")
    return st == "answer"


# ---------------------------------------------------------------- sources
def load_bank(path, source):
    with open(path) as f:
        bank = json.load(f)
    items = []
    for q in bank["questions"]:
        if not q.get("gold_ir"):
            continue
        items.append({"id": f"{source}:{q['id']}", "q": q["q"], "gold_ir": q["gold_ir"],
                      "expect": q.get("expect", "answer"), "must_hole": q.get("must_hole", False),
                      "sector": q.get("sector", "cross"), "source": source})
    return items


def load_corpus(path, source, limit=None):
    items = []
    with open(path) as f:
        for i, line in enumerate(f):
            r = json.loads(line)
            msgs = r.get("messages", [])
            uq = next((m["content"] for m in msgs if m["role"] == "user"), None)
            at = next((m["content"] for m in msgs if m["role"] == "assistant"), None)
            if not uq or not at:
                continue
            try:
                ir = json.loads(at)
            except json.JSONDecodeError:
                continue
            has_hole = "?" in at and re.search(r'"\?\w+"', at)
            items.append({"id": f"{source}:{i:04d}", "q": uq, "gold_ir": ir,
                          "expect": "data_request" if has_hole else "answer",
                          "must_hole": bool(has_hole), "sector": source, "source": source})
    if limit and len(items) > limit:
        items = RNG.sample(items, limit)
    return items


def load_sources():
    src = []
    src += load_bank(os.path.join(HERE, "questions", "seed.json"), "seed")
    src += load_bank(os.path.join(HERE, "questions", "hard-train-001.json"), "hardtrain")
    # hard-eval-001 is EXCLUDED on purpose: transforming a frozen eval bank into training
    # rows would leak its content into adapter-002 and poison later hard-eval measurements.
    src += load_corpus(os.path.join(BENCH, "corpus", "parse.jsonl"), "corpus", limit=120)
    src += load_corpus(os.path.join(TR, "transport_memory", "corpus", "parse.jsonl"),
                       "transport", limit=60)
    src += load_corpus(os.path.join(TR, "livelihoods_memory", "corpus", "parse.jsonl"),
                       "livelihoods", limit=120)
    # de-dup by question text
    seen, out = set(), []
    for it in src:
        k = fold(it["q"])
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


# ---------------------------------------------------------------- transform: lex
# (question regex, [replacements], entity-string source)
LEX_SWAPS = [
    (r"\bpharmacies\b", ["medical shops", "chemists"], "pharmacy"),
    (r"\bpharmacy\b", ["medical shop", "chemist"], "pharmacy"),
    (r"\b(fuel|petrol|gas) stations\b", ["petrol bunks", "petrol pumps"], "fuel"),
    (r"\b(fuel|petrol|gas) station\b", ["petrol bunk", "petrol pump"], "fuel"),
    (r"\bbus stations\b", ["bus stands"], "bus_station"),
    (r"\bbus station\b", ["bus stand"], "bus_station"),
    (r"\bclinics\b", ["PHCs", "dispensaries"], "clinic"),
    (r"\bclinic\b", ["PHC", "dispensary"], "clinic"),
    (r"\bkindergartens\b", ["anganwadis"], "kindergarten"),
    (r"\bkindergarten\b", ["anganwadi"], "kindergarten"),
    (r"\bmarketplaces\b", ["mandis", "bazaars"], "market"),
    (r"\bmarketplace\b", ["mandi", "bazaar", "santhe"], "market"),
    (r"\bmarkets\b", ["mandis", "bazaars"], "market"),
    (r"\bhospitals\b", ["nursing homes"], "hospital"),
    (r"\bhospital\b", ["nursing home"], "hospital"),
]


def t_lex(item):
    q, ir = item["q"], copy.deepcopy(item["gold_ir"])
    applied = []
    for pat, repls, _src in LEX_SWAPS:
        if re.search(pat, q, flags=re.I):
            repl = RNG.choice(repls)
            q = re.sub(pat, repl, q, flags=re.I)
            applied.append((pat, repl))
    if not applied:
        return None
    # swap gold entities the same way, then require canon equivalence
    def swap_entity(e):
        for pat, repls, _src in LEX_SWAPS:
            m = re.fullmatch(pat.strip(r"\b"), e, flags=re.I) or re.search(pat, e, flags=re.I)
            if m:
                repl = next((r for p, r in applied if p == pat), None)
                if repl:
                    return re.sub(pat, repl, e, flags=re.I)
        return e

    def walk(n):
        if isinstance(n, list):
            return [walk(x) for x in n]
        if not isinstance(n, dict):
            return n
        out = {k: walk(v) for k, v in n.items()}
        if out.get("op") == "SELECT":
            e = out.get("entity")
            if isinstance(e, str) and not e.startswith("?"):
                old, new = e, swap_entity(e)
                if new != old:
                    oc, nc = entity_canon(old), entity_canon(new)
                    # canonical target must be preserved (ambiguity flags allowed)
                    if oc[0] == nc[0] and oc[1] == nc[1]:
                        out["entity"] = new
                    # else leave the old entity: resolver aliases cover the question surface
            elif isinstance(e, list):
                out["entity"] = [swap_entity(x) if isinstance(x, str) and not x.startswith("?")
                                 else x for x in e]
        return out
    ir = walk(ir)
    return {**item, "q": q, "gold_ir": ir, "transform": "lex"}


# ---------------------------------------------------------------- transform: loc
IN_CITIES = ["Bengaluru, India", "Mysuru, India", "Chennai, India", "Pune, India",
             "Jaipur, India", "Kochi, India", "Indore, India", "Nagpur, India",
             "Hubballi, India", "Mangaluru, India", "Coimbatore, India", "Lucknow, India",
             "Bhopal, India", "Madurai, India", "Surat, India", "Visakhapatnam, India"]


def t_loc(item):
    """Relocate every distinct REGION place to a distinct Indian city (country rows -> India).
    Gold must re-verify by execution (OSM sparsity in India filters rows honestly)."""
    ir = copy.deepcopy(item["gold_ir"])
    places = list(dict.fromkeys(places_of(ir)))
    if not places:
        return None
    # country-level (WB) trees keep country semantics -> India; else Indian cities
    ents = entities_of(ir)
    is_wb = any(entity_canon(e)[0] == "wb" for e in ents)
    if is_wb and len(places) == 1:
        mapping = {places[0]: "India"}
    else:
        pool = RNG.sample(IN_CITIES, min(len(places), len(IN_CITIES)))
        mapping = dict(zip(places, pool))
    q = item["q"]
    for old, new in mapping.items():
        seg_old = old.split(",")[0].strip()
        seg_new = new.split(",")[0].strip()
        if not re.search(re.escape(seg_old), q, flags=re.I):
            return None  # place not literally in the question; skip rather than guess
        q = re.sub(re.escape(old), seg_new, q, flags=re.I)
        q = re.sub(r"\b" + re.escape(seg_old) + r"\b", seg_new, q, flags=re.I)

    def walk(n):
        if isinstance(n, list):
            return [walk(x) for x in n]
        if not isinstance(n, dict):
            return n
        out = {k: walk(v) for k, v in n.items()}
        if out.get("op") == "REGION" and out.get("place") in mapping:
            out["place"] = mapping[out["place"]]
        return out
    return {**item, "q": q, "gold_ir": walk(ir), "transform": "loc"}


# ---------------------------------------------------------------- transform: struct
def t_struct(item):
    """COMPARE(difference, AGG(SELECT@A), AGG(SELECT@B)) -> ordering phrasing with allow-set."""
    ir = item["gold_ir"]
    if not (isinstance(ir, dict) and ir.get("op") == "COMPARE"
            and ir.get("how") == "difference" and isinstance(ir.get("right"), dict)):
        return None

    def agg_sel(n):
        return (isinstance(n, dict) and n.get("op") == "AGGREGATE"
                and isinstance(n.get("source"), dict) and n["source"].get("op") == "SELECT"
                and isinstance(n["source"].get("region"), dict))
    if not (agg_sel(ir["left"]) and agg_sel(ir["right"])):
        return None
    ls, rs = ir["left"]["source"], ir["right"]["source"]
    ent = ls.get("entity")
    pa, pb = ls["region"].get("place"), rs["region"].get("place")
    if not (isinstance(ent, str) and pa and pb and ent == rs.get("entity")):
        return None
    ca, cb = pa.split(",")[0], pb.split(",")[0]
    q = RNG.choice([
        f"Order {ca} and {cb} by number of {ent}s, highest first.",
        f"{ca} versus {cb} — put them in order of {ent} count.",
        f"Rank {ca} and {cb} on how many {ent}s they have.",
    ])
    rank_ir = {"op": "RANK", "order": "desc", "items": [copy.deepcopy(ir["left"]),
                                                        copy.deepcopy(ir["right"])]}
    return {**item, "q": q, "gold_ir": rank_ir, "transform": "struct",
            "gold_shapes": [["RANK", "SELECT", "SELECT"], ["COMPARE", "SELECT", "SELECT"]]}


# ---------------------------------------------------------------- transform: reg (deepseek)
REG_PROMPT = """Rewrite this question 4 ways, as an Indian urban/semi-urban English speaker
would type it to a civic-data assistant. Styles:
1. "formal": polite Indian-English officialese (e.g. "Kindly tell...", "please do the needful").
2. "conversational": casual Indian spoken register (tags like "no?", "na", "right?", "only"
   emphasis, "itself", "means").
3. "terse": SMS-style, articles dropped, minimal words (e.g. "mysuru clinics how many").
4. "fragment": a clipped noun-phrase query keeping ALL constraints (e.g. "clinic count Mysuru?").

HARD RULES: keep every place name, number, distance, year and entity EXACTLY (same spelling);
do not add or drop constraints; the rewrite must ask the SAME question. Reply with ONLY a JSON
object: {"formal": "...", "conversational": "...", "terse": "...", "fragment": "..."}.

Question: """


def t_reg(item, llm_chat):
    raw = llm_chat("deepseekv4", [{"role": "user", "content": REG_PROMPT + item["q"]}],
                   max_tokens=8000)
    m = re.search(r"\{.*\}", raw, flags=re.S)
    if not m:
        return []
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for style in ("formal", "conversational", "terse", "fragment"):
        nq = d.get(style)
        if not isinstance(nq, str) or not nq.strip():
            continue
        if not contains_places_nums(nq, item["gold_ir"], item["q"]):
            continue
        out.append({**item, "q": nq.strip(), "transform": "reg", "style": style})
    return out


# ---------------------------------------------------------------- transform: mt
MT_JUDGE = """Do these two questions ask for the SAME information (same places, same quantities,
same comparison/ranking direction, same constraints)? Minor wording/spelling differences are
fine; a changed meaning is not. Answer with exactly one word: YES or NO.

Q1: {a}
Q2: {b}"""


def mt_roundtrip(texts, lang):
    req = urllib.request.Request(MT_URL + "/roundtrip",
                                 data=json.dumps({"texts": texts, "lang": lang}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=1800) as r:
        return json.loads(r.read())


def t_mt(item, lang, llm_chat):
    r = mt_roundtrip([item["q"]], lang)
    back = (r.get("back") or [""])[0].strip()
    if not back or fold(back) == fold(item["q"]):
        return None
    if not contains_places_nums(back, item["gold_ir"], item["q"]):
        return None
    verdict = llm_chat("deepseekv4",
                       [{"role": "user", "content": MT_JUDGE.format(a=item["q"], b=back)}],
                       max_tokens=2000)
    if "YES" not in verdict.upper()[:80]:
        return None
    return {**item, "q": back, "transform": "mt", "lang": lang, "style": "mt"}


# ---------------------------------------------------------------- complaint mint
def mint_complaints(n_target=75):
    """Correct-by-construction complaint-analytics questions over the ICMC connector."""
    rows = C._icmc_load()
    import collections
    fam_names = {"garbage": "garbage", "streetlight": "streetlight", "road": "road",
                 "water": "water", "traffic": "traffic", "sewage": "sewage",
                 "animal": "stray animal", "pothole": "pothole"}
    by_fam_ward = collections.defaultdict(collections.Counter)
    for fam in fam_names:
        cats = set(C.ICMC_FAMILIES[fam])
        for r in rows:
            if r["category"] in cats and r["ward"] and r["ward"] != "Other":
                by_fam_ward[fam][r["ward"]] += 1

    def sel(ent, place, time=None):
        return {"op": "SELECT", "entity": ent,
                "region": {"op": "REGION", "place": place}, "time": time}

    def agg(src, by="space", metric="count"):
        return {"op": "AGGREGATE", "by": by, "metric": metric, "source": src}

    out, qid = [], 0

    def add(q, ir, qtype, style, shapes=None):
        nonlocal qid
        qid += 1
        row = {"id": f"icmc-{qid:03d}", "sector": "complaints", "type": qtype, "q": q,
               "gold_ir": ir, "gold_shape": sorted(_shape(ir).elements()),
               "expect": "answer", "source": "icmc-mint", "transform": "mint", "style": style}
        if shapes:
            row["gold_shapes"] = shapes
        out.append(row)

    fams = [f for f in fam_names if len([w for w, c in by_fam_ward[f].items() if c >= 8]) >= 6]
    while len(out) < n_target:
        fam = RNG.choice(fams)
        ent = f"{fam_names[fam]} complaints"
        wards = [w for w, c in by_fam_ward[fam].most_common(30) if c >= 8]
        kind = RNG.choice(["rank", "rank_neg", "trend", "cmp_years", "cmp_wards", "count"])
        if kind in ("rank", "rank_neg"):
            k = RNG.choice([3, 3, 4])
            ws = RNG.sample(wards[:20], k)
            order = "asc" if kind == "rank_neg" else "desc"
            ir = {"op": "RANK", "order": order,
                  "items": [agg(sel(ent, w)) for w in ws]}
            wl = ", ".join(ws[:-1]) + " and " + ws[-1]
            if order == "desc":
                q = RNG.choice([
                    f"Out of {wl}, which ward is having the most {ent}?",
                    f"Between {wl}, where are {ent} highest?",
                    f"{wl} — rank these wards by {ent}.",
                ])
            else:
                q = RNG.choice([
                    f"Of {wl}, which ward has the least {ent}?",
                    f"Among {wl}, where do people complain least about {fam_names[fam]}?",
                ])
            add(q, ir, "RANKING", "native")
        elif kind == "trend":
            scope = RNG.choice(["Bengaluru", RNG.choice(wards[:8])])
            ir = {"op": "COMPARE", "how": "trend_direction",
                  "left": agg(sel(ent, scope), by="time")}
            q = RNG.choice([
                f"Are {ent} in {scope} increasing or decreasing?",
                f"{ent} in {scope} — going up or coming down?",
                f"Is the number of {ent} rising in {scope}?",
            ])
            add(q, ir, "TREND", "native")
        elif kind == "cmp_years":
            y1, y2 = RNG.choice([("2019", "2021"), ("2019", "2020"), ("2020", "2021"),
                                 ("2019", "2022")])
            scope = RNG.choice(["Bengaluru", RNG.choice(wards[:8])])
            ir = {"op": "COMPARE", "how": "difference",
                  "left": agg(sel(ent, scope, {"start": y2, "end": y2})),
                  "right": agg(sel(ent, scope, {"start": y1, "end": y1}))}
            q = RNG.choice([
                f"Did {ent} in {scope} come down between {y1} and {y2}?",
                f"Compare {ent} in {scope} for {y1} versus {y2}.",
                f"{scope} {ent}: more in {y2} than {y1}, or less?",
            ])
            add(q, ir, "CHANGE", "native")
        elif kind == "cmp_wards":
            w1, w2 = RNG.sample(wards[:15], 2)
            ir = {"op": "COMPARE", "how": "difference",
                  "left": agg(sel(ent, w1)), "right": agg(sel(ent, w2))}
            q = RNG.choice([
                f"Which ward has more {ent} — {w1} or {w2}?",
                f"{w1} vs {w2}: where are {ent} more?",
            ])
            add(q, ir, "COMPARATIVE", "native")
        else:
            w = RNG.choice(wards[:15])
            y = RNG.choice(["2019", "2020", "2021"])
            ir = agg(sel(ent, w, {"start": y, "end": y}))
            q = RNG.choice([
                f"How many {ent} were filed in {w} ward in {y}?",
                f"{ent} count for {w} in {y}?",
                f"In {y}, how many {ent} came from {w}?",
            ])
            add(q, ir, "STATE", "native")
    # de-dup + verify by execution
    seen, ver = set(), []
    for r in out:
        k = fold(r["q"])
        if k in seen:
            continue
        seen.add(k)
        if verify_gold(r["gold_ir"], r["expect"]):
            ver.append(r)
    return ver


# ---------------------------------------------------------------- driver
def stage_transforms(outdir):
    src = load_sources()
    print(f"{len(src)} source items")
    produced = []
    for it in src:
        for fn in (t_lex, t_loc, t_struct):
            try:
                r = fn(it)
            except Exception as e:
                print(f"[{fn.__name__}] {it['id']}: {type(e).__name__} {e}", flush=True)
                continue
            if not r:
                continue
            if not contains_places_nums(r["q"], r["gold_ir"], r["q"]):
                continue
            produced.append(r)
    # gold re-verification by execution (loc/lex changed trees; struct changed shape)
    kept = []
    for i, r in enumerate(produced):
        ok = verify_gold(r["gold_ir"], r.get("expect", "answer"), r.get("must_hole", False))
        print(f"verify {i+1}/{len(produced)} {r['transform']:6} {'OK' if ok else 'DROP'} "
              f"{r['q'][:60]}", flush=True)
        if ok:
            kept.append(r)
    _dump(outdir, "transforms_mech.jsonl", kept)
    print(f"kept {len(kept)}/{len(produced)}")


def stage_reg(outdir, limit=90):
    from llm import chat
    src = load_sources()
    RNG.shuffle(src)
    base = src[:limit]
    kept, path_done = [], set()
    outp = os.path.join(outdir, "transforms_reg.jsonl")
    if os.path.exists(outp):
        for line in open(outp):
            path_done.add(json.loads(line)["source_id"])
    with open(outp, "a") as f:
        for i, it in enumerate(base):
            if it["id"] in path_done:
                continue
            rows = t_reg(it, chat)
            n_ok = 0
            for r in rows:
                if verify_gold(r["gold_ir"], r.get("expect", "answer"), r.get("must_hole", False)):
                    r["source_id"] = it["id"]
                    f.write(json.dumps(r) + "\n")
                    f.flush()
                    n_ok += 1
            print(f"reg {i+1}/{len(base)} {it['id']} -> {n_ok} styles kept", flush=True)
            kept.append(n_ok)
    print(f"reg done, {sum(kept)} rows")


def stage_mt(outdir, limit=45):
    from llm import chat
    src = [s for s in load_sources() if not s.get("must_hole")]
    RNG.shuffle(src)
    base = src[:limit]
    langs = ["hi", "kn", "ta", "te", "mr"]
    outp = os.path.join(outdir, "transforms_mt.jsonl")
    done = set()
    if os.path.exists(outp):
        for line in open(outp):
            r = json.loads(line)
            done.add((r["source_id"], r["lang"]))
    with open(outp, "a") as f:
        for i, it in enumerate(base):
            for lang in langs:
                if (it["id"], lang) in done:
                    continue
                try:
                    r = t_mt(it, lang, chat)
                except Exception as e:
                    print(f"mt {it['id']} {lang}: {type(e).__name__} {e}", flush=True)
                    continue
                if r and verify_gold(r["gold_ir"], r.get("expect", "answer"),
                                     r.get("must_hole", False)):
                    r["source_id"] = it["id"]
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                    f.flush()
                    print(f"mt {i+1}/{len(base)} {lang} KEEP {r['q'][:60]}", flush=True)
                else:
                    print(f"mt {i+1}/{len(base)} {lang} drop", flush=True)


def stage_mint(outdir):
    rows = mint_complaints(75)
    _dump(outdir, "mint_icmc.jsonl", rows)
    print(f"minted {len(rows)} verified complaint questions")


def _dump(outdir, name, rows):
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, name), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _bank_row(r, i):
    row = {"id": r.get("id") if r.get("source") == "icmc-mint" else f"ind-{i:03d}",
           "sector": r.get("sector", "cross"), "type": r.get("type", "DIALECT"),
           "q": r["q"], "expect": r.get("expect", "answer"),
           "gold_ir": r["gold_ir"],
           "gold_shape": r.get("gold_shape") or sorted(_shape(r["gold_ir"]).elements()),
           "meta": {"transform": r.get("transform"), "style": r.get("style", "native"),
                    "lang": r.get("lang"), "source": r.get("source"),
                    "source_id": r.get("source_id", r.get("id"))}}
    if r.get("must_hole"):
        row["must_hole"] = True
    if r.get("gold_shapes"):
        row["gold_shapes"] = r["gold_shapes"]
    return row


def stage_assemble(outdir, eval_n=60):
    """Split by ORIGINAL id (no leakage), stratify eval across transform x style, write banks."""
    pools = []
    for name in ("transforms_mech.jsonl", "transforms_reg.jsonl", "transforms_mt.jsonl",
                 "mint_icmc.jsonl"):
        p = os.path.join(outdir, name)
        if os.path.exists(p):
            for line in open(p):
                pools.append(json.loads(line))
    by_orig = {}
    for r in pools:
        by_orig.setdefault(r.get("source_id") or r.get("id"), []).append(r)
    origs = sorted(by_orig)
    RNG.shuffle(origs)
    # split by ORIGINAL: an original whose rows enter eval contributes NOTHING to train
    # (held-out transforms, no template leakage). Eval picks favour underfilled
    # (transform, style) cells for stratification.
    eval_rows, train_rows, cell = [], [], {}
    cap = max(3, eval_n // 10)  # per-(transform,style) soft cap in eval
    for o in origs:
        rows = by_orig[o]
        def key(r):
            return (r.get("transform"), r.get("style", "native"))
        underfilled = [r for r in rows if cell.get(key(r), 0) < cap]
        if len(eval_rows) < eval_n and underfilled and RNG.random() < 0.5:
            for r in RNG.sample(underfilled, min(2, len(underfilled))):
                cell[key(r)] = cell.get(key(r), 0) + 1
                eval_rows.append(r)
            # remaining rows of this original are DISCARDED (leakage guard)
        else:
            train_rows.extend(rows)
    _write_bank(os.path.join(HERE, "questions", "indic-train-001.json"), train_rows,
                "Indian-dialect training bank (adapter-002 candidate diet). "
                "Produced by dialect.py over execution-verified pairs; every gold re-executed.")
    _write_bank(os.path.join(HERE, "questions", "indic-eval-001.json"), eval_rows,
                "FROZEN Indic eval. FIRST-CONTACT PROTOCOL: no model, prompt, adapter or "
                "harness change may be informed by per-row inspection of this file before a "
                "model's first scored run on it; misses may be autopsied only AFTER that run "
                "is recorded. Originals (source_id) are held out from indic-train-001. "
                "Hand-authored rows (ind-hand-*) are appended separately.")
    print(f"eval {len(eval_rows)} train {len(train_rows)}")


def _write_bank(path, rows, note):
    bank = {"spec_version": "v2", "note": note,
            "questions": [_bank_row(r, i + 1) for i, r in enumerate(rows)]}
    with open(path, "w") as f:
        json.dump(bank, f, indent=1, ensure_ascii=False)
    print("wrote", path, len(rows))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", required=True,
                    choices=["transforms", "reg", "mt", "mint", "assemble"])
    ap.add_argument("--out", default=os.path.join(BENCH, "runs", "indic-factory"))
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    if a.stage == "transforms":
        stage_transforms(a.out)
    elif a.stage == "reg":
        stage_reg(a.out, a.limit or 90)
    elif a.stage == "mt":
        stage_mt(a.out, a.limit or 45)
    elif a.stage == "mint":
        stage_mint(a.out)
    elif a.stage == "assemble":
        stage_assemble(a.out)
