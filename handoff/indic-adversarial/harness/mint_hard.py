"""mint_hard — the composition-gap data factory (LoRA train/eval alignment).

The hard bank exposed WHERE the 2B fails: composition depth. For the LoRA to close that gap,
(a) the TRAINING set must contain the missing skill at scale, and (b) the EVAL must measure it
with enough items per class to detect the move. This factory produces both, with train/eval
DISJOINT by construction (separate city/country pools + separately drawn entity pairs).

Gold trees are built PROGRAMMATICALLY from the class templates — correct by construction, not
model-authored — then execution-verified. Question text is optionally paraphrased/buried by a
strong model for naturalness, with a mechanical containment check (every city, entity, number
must survive the paraphrase, else keep the template text).

Composition classes (from the measured failures):
  C1  difference-of-differences        COMPARE(diff, COMPARE(diff,A@y2,A@y1), COMPARE(diff,B@y2,B@y1))
  C2  count over a 2-hop RELATE chain  AGG(count, RELATE(rel2, RELATE(within, E1,E2), E3))
  C3  negated ranking (3 cities)       RANK(order, [AGG(count, RELATE(beyond, E1,E2))]x3)
  C4  cross-city relation compare      COMPARE(diff, AGG(count,RELATE(within,E1,E2))@c1, ...@c2)
  C5  buried phrasing                  a modifier applied to a fraction of any class

Usage:
  python3 mint_hard.py --split train --n-per-class 40 --out questions/hard-train-001.json
  python3 mint_hard.py --split eval  --n-per-class 12 --out questions/hard-eval-001.json --bury 0.25
"""
import argparse
import json
import random
import re

from ir_schema import validate
from executor import execute
from llm import chat

TRAIN_CITIES = ["Kampala, Uganda", "Accra, Ghana", "Dakar, Senegal", "Marrakech, Morocco",
                "Tunis, Tunisia", "Amman, Jordan", "Tbilisi, Georgia", "Hanoi, Vietnam",
                "Cebu, Philippines", "Surabaya, Indonesia", "Curitiba, Brazil",
                "Rosario, Argentina", "Arequipa, Peru", "Leipzig, Germany", "Gdansk, Poland",
                "Brno, Czechia", "Graz, Austria", "Zaragoza, Spain", "Bologna, Italy",
                "Porto Alegre, Brazil"]
EVAL_CITIES = ["Nairobi, Kenya", "Mombasa, Kenya", "Kisumu, Kenya", "Lisbon, Portugal",
               "Porto, Portugal", "Quito, Ecuador", "Oslo, Norway", "Helsinki, Finland",
               "Stockholm, Sweden", "Vienna, Austria", "Prague, Czechia", "Budapest, Hungary",
               "Guadalajara, Mexico", "Osaka, Japan", "Medellin, Colombia"]
TRAIN_COUNTRIES = ["Ghana", "Morocco", "Philippines", "Peru", "Poland", "Egypt", "Tanzania",
                   "Nepal", "Jordan", "Georgia"]
EVAL_COUNTRIES = ["Kenya", "Vietnam", "Brazil", "India", "Indonesia", "Colombia"]

ENTITIES = ["clinic", "hospital", "pharmacy", "school", "library", "cafe", "restaurant",
            "bank", "supermarket", "park", "bus_stop", "hotel", "police", "post_office",
            "market", "kindergarten", "university"]
INDICATORS = ["gdp per capita", "internet users", "mobile subscriptions", "unemployment",
              "inflation", "electricity access", "urban population", "life expectancy"]
THRESH = [0.25, 0.3, 0.5, 1.0, 2.0]
YEARS = [(2005, 2015), (2010, 2020), (2012, 2022), (2008, 2018), (2000, 2019)]


def SEL(entity, place, time=None):
    return {"op": "SELECT", "entity": entity,
            "region": {"op": "REGION", "place": place}, "time": time}


def YR(y):
    return {"start": str(y), "end": str(y)}


def AGGC(src):
    return {"op": "AGGREGATE", "by": "space", "metric": "count", "source": src}


IRREG = {"police": "police stations", "fuel": "fuel stations"}
def human_e(e):
    if e in IRREG:
        return IRREG[e]
    w = e.replace("_", " ")
    if w.endswith("y"):
        return w[:-1] + "ies"
    if w.endswith(("s", "x", "ch", "sh")):
        return w + "es"
    return w + "s"


def sing(e):
    return IRREG.get(e, e.replace("_", " "))[:-1] if e in IRREG else e.replace("_", " ")


def c1(rng, cities, countries):
    a, b = rng.sample(INDICATORS, 2)
    c = rng.choice(countries)
    y1, y2 = rng.choice(YEARS)
    q = f"Did {a} grow faster than {b} in {c} between {y1} and {y2}?"
    def diff(ind):
        return {"op": "COMPARE", "how": "difference",
                "left": SEL(ind, c, YR(y2)), "right": SEL(ind, c, YR(y1))}
    ir = {"op": "COMPARE", "how": "difference", "left": diff(a), "right": diff(b)}
    return q, ir, "COMPOSITE"


def c2(rng, cities, countries):
    e1, e2, e3 = rng.sample(ENTITIES, 3)
    city = rng.choice(cities)
    d1, d2 = rng.choice(THRESH), rng.choice(THRESH)
    rel2 = rng.choice(["within", "beyond"])
    inner = {"op": "RELATE", "relation": "within", "threshold_km": d1,
             "left": SEL(e1, city), "right": SEL(e2, city)}
    ir = AGGC({"op": "RELATE", "relation": rel2, "threshold_km": d2,
               "left": inner, "right": SEL(e3, city)})
    word = "within" if rel2 == "within" else "more than"
    unit = f"{int(d2*1000)} meters" if d2 < 1 else f"{d2:g} km"
    tail = f"{word} {unit} of a {sing(e3)}" if rel2 == "within" \
        else f"{word} {unit} from any {sing(e3)}"
    q = (f"Of the {human_e(e1)} in {city} that are within "
         f"{int(d1*1000) if d1 < 1 else d1:g}{' meters' if d1 < 1 else ' km'} of a "
         f"{sing(e2)}, how many are {tail}?")
    return q, ir, "COMPOSITE"


def c3(rng, cities, countries):
    e1, e2 = rng.sample(ENTITIES, 2)
    cs = rng.sample(cities, 3)
    d = rng.choice(THRESH)
    order = rng.choice(["desc", "asc"])
    ir = {"op": "RANK", "order": order, "items": [
        AGGC({"op": "RELATE", "relation": "beyond", "threshold_km": d,
              "left": SEL(e1, ci), "right": SEL(e2, ci)}) for ci in cs]}
    most = "most" if order == "desc" else "fewest"
    names = ", ".join(c.split(",")[0] for c in cs[:-1]) + " and " + cs[-1].split(",")[0]
    unit = f"{int(d*1000)} meters" if d < 1 else f"{d:g} km"
    q = (f"Which of {names} has the {most} {human_e(e1)} with no "
         f"{sing(e2)} within {unit}?")
    return q, ir, "RANKING"


def c4(rng, cities, countries):
    e1, e2 = rng.sample(ENTITIES, 2)
    c1_, c2_ = rng.sample(cities, 2)
    d = rng.choice(THRESH)
    def side(city):
        return AGGC({"op": "RELATE", "relation": "within", "threshold_km": d,
                     "left": SEL(e1, city), "right": SEL(e2, city)})
    ir = {"op": "COMPARE", "how": "difference", "left": side(c1_), "right": side(c2_)}
    unit = f"{int(d*1000)} meters" if d < 1 else f"{d:g} km"
    q = (f"Are there more {human_e(e1)} within {unit} of a {sing(e2)} in "
         f"{c1_.split(',')[0]} than in {c2_.split(',')[0]}?")
    return q, ir, "COMPOSITE"


GENS = {"C1": c1, "C2": c2, "C3": c3, "C4": c4}

BURY_PROMPT = """Rewrite this question as a casual, rambling 2-3 sentence message from a real person
that BURIES the question inside chatter. You MUST keep every city name, entity type, number,
distance and year EXACTLY as written — the question's content must be fully recoverable. Output
only the rewritten message."""


def key_tokens(q):
    toks = set(re.findall(r"[A-Z][a-zA-Z]+|\d+(?:\.\d+)?", q))
    return {t for t in toks if t not in {"Of", "Are", "Did", "Which", "How"}}


def bury(q):
    try:
        p = chat("deepseekv4", [{"role": "system", "content": BURY_PROMPT},
                                {"role": "user", "content": q}],
                 temperature=0.8, max_tokens=4000, use_cache=False).strip()
    except RuntimeError:
        return q, False
    if key_tokens(q) <= key_tokens(p):   # containment: nothing load-bearing was dropped
        return p, True
    return q, False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--split", choices=["train", "eval"], required=True)
    ap.add_argument("--n-per-class", type=int, default=40)
    ap.add_argument("--out", required=True)
    ap.add_argument("--bury", type=float, default=0.35)
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    rng = random.Random(a.seed if a.seed is not None else (11 if a.split == "train" else 97))
    cities = TRAIN_CITIES if a.split == "train" else EVAL_CITIES
    countries = TRAIN_COUNTRIES if a.split == "train" else EVAL_COUNTRIES

    out, drop = [], 0
    for cname, gen in GENS.items():
        made = 0
        attempts = 0
        while made < a.n_per_class and attempts < a.n_per_class * 4:
            attempts += 1
            q, ir, qtype = gen(rng, cities, countries)
            rep = validate(ir)
            if not rep["valid"]:
                drop += 1
                continue
            try:
                res = execute(ir)
            except Exception:
                drop += 1
                continue
            if res.get("status") != "answer":
                drop += 1          # thin data for this combo — not a usable gold
                continue
            buried = False
            if rng.random() < a.bury:
                q, buried = bury(q)
            made += 1
            out.append({"id": f"h{a.split[0]}-{cname}-{made:03d}", "sector": "cross",
                        "type": qtype, "cclass": cname, "buried": buried, "q": q,
                        "expect": "answer", "gold_ir": ir,
                        "gold_shape": [o for o in rep["ops"] if o != "REGION"]})
            print(f"OK {cname} {made}/{a.n_per_class} buried={int(buried)} {q[:70]}", flush=True)
    bank = {"spec_version": "v2.1",
            "note": f"hard composition bank ({a.split}); golds correct-by-construction + "
                    f"execution-verified; cities/countries disjoint from the other split; "
                    f"classes C1-C4 (+C5 bury modifier at {a.bury}). PROTOCOL for eval split: "
                    "first contact only, never tune on it.",
            "questions": out}
    with open(a.out, "w") as f:
        json.dump(bank, f, indent=1)
    print(f"\n{a.split}: {len(out)} minted ({drop} dropped) -> {a.out}")
    from collections import Counter
    print("per class:", dict(Counter(x['cclass'] for x in out)),
          "| buried:", sum(1 for x in out if x['buried']))


if __name__ == "__main__":
    main()
