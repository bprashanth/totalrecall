#!/usr/bin/env python3
"""Generate parser-blind post-freeze ecology holdouts with execution-admitted golds.

The generator sees capabilities and the frozen algebra, never parser outputs, repairs, traces, or
few-shot performance. Gold is generated with each question, then admitted by deterministic schema,
literal-faithfulness, structural, and execution checks. Holdouts are eval-only forever.
"""
import argparse
from collections import Counter
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))

from executor import execute
from ir_schema import validate
from llm import chat
import parser as P


TYPES = ["STATE", "VALUE", "RELATION", "CHANGE", "TREND", "COMPARE", "RANKING",
         "TRANSFER", "AMBIGUOUS", "BEHAVIOUR", "SOURCE_GAP", "ADVERSARIAL", "COMPOSITE"]

PROMPT = """Create {n} UNIQUE, single-clause evaluation questions for an ecology place-data system.
Return ONLY a JSON array. Every row must be:
{{"type": one of {types}, "q": natural one-sentence question,
  "expect": "answer" or "data_request"}}.

This is a parser-blind exam. Do not discuss a parser, training examples, repairs, or likely errors.
Style for this bank: {style}.

Real admitted capabilities:
- licensed GBIF+iNaturalist taxon OCCURRENCE RECORDS (presence, never abundance/population), with
  aliases including Lantana, teak, neem, jamun, tamarind, karonda, green cat snake, gaur, sambar,
  elephant, chital, nilgai, tiger, leopard, and Indian peafowl;
- recent 1-30 day eBird observation records;
- annual QA-masked MODIS NDVI bbox means from 2000 onward;
- 26 published Anamalai vegetation survey sites, available around Valparai only;
- point annotations at those sites: elevation, slope, land cover, NDVI, surface-water occurrence,
  and ecoregion;
- spatial within/beyond/cooccur/distance relations; feature/envelope/interpolate transfer gates.

Use named Indian places, with strong representation of Valparai, Pollachi, Mysuru, Bengaluru, and
at least a few other named places. Deliberately mix ordinary, indirect, adversarial, concise Indian
English, field-worker language, and lightly noisy phrasing. Cover all listed types approximately
evenly. Include source gaps, record-vs-organism traps, deictic ambiguity, abstract indicators,
negated distances in metres/km, two-place comparison, 3-place ranking, named time endpoints,
annotation composition, taxon union, and transfer refusal. Do not request FILTER, GROUP, causal
attribution, documents, maps/exports, uncertainty, or paid imagery: those are a separate blocked
expressiveness bank.

Question/expectation rules:
- Explicit record/observation/sighting count may AGGREGATE count. “How many elephants/tigers” is
  NOT a record count and must expect data_request.
- Historic eBird (>30 days), unknown measurements, population/abundance/biomass/occupancy/richness,
  and unavailable survey types expect data_request.
- Deictic/missing place or missing measure uses a ?hole and expects data_request. Behaviour/motive
  uses SELECT entity ?proxy and a ?place if missing.
- CHANGE uses later-minus-earlier. Trend is unary COMPARE over a time series. Three-place ordering
  uses RANK with all places. Transfer must contain ESTIMATE and may expect data_request when gated.
- A question asks ONE answer only. No “and also”, two independent clauses, or half-golds.
"""

GOLD_SUFFIX = """
This is an evaluation gold. Return ONLY the single JSON IR tree for the supplied question. Every
literal entity, place, year, distance, layer, and operation must come from the question. Do not use
connector names or string shorthand where a child IR node is required. Ambiguity/behaviour needs
holes; ranking needs all 3+ items; transfer needs ESTIMATE; organism counts remain occurrence-source
requests so the executor can refuse abundance honestly.
"""


def _extract_array(raw):
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end <= start:
        raise ValueError("generator returned no JSON array")
    return json.loads(raw[start:end + 1])


def generate(provider, n, style):
    prompt = PROMPT.format(n=n, types=TYPES, style=style)
    if provider == "deepseekv4":
        raw = chat("deepseekv4", [{"role": "user", "content": prompt}], temperature=0.75,
                   max_tokens=6000, use_cache=False, timeout=300)
    elif provider == "cursor":
        proc = subprocess.run(
            ["agent", "-p", "--trust", "--mode", "ask", "--model", "gpt-5.4-mini-low", prompt],
            capture_output=True, text=True, timeout=600, cwd="/tmp")
        raw = proc.stdout
    else:
        raise ValueError(provider)
    return _extract_array(raw)


def author_gold(provider, question):
    if provider == "deepseekv4":
        messages = P.build_messages(question)
        messages[0]["content"] += GOLD_SUFFIX
        raw = chat("deepseekv4", messages, temperature=0.0, max_tokens=4000, timeout=240)
    else:
        examples = P.load_fewshot()
        curriculum = "\n".join(
            f"Q: {row['q']}\nIR: {json.dumps(row['ir'])}" for row in examples)
        prompt = P.SYSTEM + GOLD_SUFFIX + "\nExamples:\n" + curriculum + "\nQuestion: " + question
        proc = subprocess.run(
            ["agent", "-p", "--trust", "--mode", "ask", "--model", "gpt-5.4-mini-low", prompt],
            capture_output=True, text=True, timeout=300, cwd="/tmp")
        raw = proc.stdout
    return P.extract_json(raw)


def _norm(q):
    return re.sub(r"[^a-z0-9]+", " ", q.lower()).strip()


def _tokens(text):
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in _norm(text).split()}


def _walk(node):
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from _walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from _walk(value)


def literal_audit(question, ir):
    """Conservative audit against half-golds and invented literals; holes are exempt."""
    q = _norm(question)
    years_q = set(re.findall(r"\b(?:19|20)\d{2}\b", question))
    years_ir = set()
    for node in _walk(ir):
        if node.get("op") == "REGION":
            place = node.get("place")
            if isinstance(place, str) and not place.startswith("?"):
                anchor = _norm(place.split(",")[0])
                if anchor and anchor not in q:
                    return False, f"invented place {place!r}"
        if node.get("op") == "SELECT":
            entities = node.get("entity")
            entities = entities if isinstance(entities, list) else [entities]
            for entity in entities:
                if not isinstance(entity, str) or entity.startswith("?"):
                    continue
                # Resolver normalizations may add record words, but the biological/measure core
                # must still occur literally.
                core = _norm(re.sub(r"\b(occurrence|observation|sighting|documented|recent|records?|points?)\b",
                                    "", entity, flags=re.I))
                if core and not _tokens(core).issubset(_tokens(q)):
                    return False, f"invented entity {entity!r}"
        if node.get("op") == "ANNOTATE":
            layer = _norm(str(node.get("layer", "")).replace("_", " ").replace("landcover", "land cover"))
            if layer and not _tokens(layer).issubset(_tokens(q)):
                return False, f"invented layer {node.get('layer')!r}"
        time_value = node.get("time")
        if isinstance(time_value, dict):
            years_ir |= {str(v)[:4] for v in time_value.values()
                         if isinstance(v, (str, int)) and re.match(r"^(?:19|20)\d{2}", str(v))}
    if not years_ir.issubset(years_q):
        return False, f"invented years {sorted(years_ir - years_q)}"
    return True, "literal audit passed"


def admit(row):
    if not isinstance(row, dict) or row.get("type") not in TYPES or not isinstance(row.get("q"), str):
        return False, "bad row metadata", None
    ir = row.get("gold_ir")
    rep = validate(ir) if isinstance(ir, dict) else {"valid": False, "errors": ["missing IR"]}
    if not rep["valid"]:
        return False, f"schema {rep['errors'][:1]}", None
    typ = row["type"]
    if typ in {"AMBIGUOUS", "BEHAVIOUR"} and not rep["holes"]:
        return False, "ambiguity/behaviour has no holes", None
    if typ == "TRANSFER" and not rep["has_estimate"]:
        return False, "transfer has no ESTIMATE", None
    if typ == "RANKING":
        ranks = [n for n in _walk(ir) if n.get("op") == "RANK"]
        if not ranks or len(ranks[0].get("items", [])) < 3:
            return False, "ranking has no 3+-item RANK", None
    required_ops = {"RELATION": "RELATE", "CHANGE": "COMPARE", "TREND": "COMPARE",
                    "COMPARE": "COMPARE"}
    if required_ops.get(typ) and required_ops[typ] not in rep["ops"]:
        return False, f"{typ} has no {required_ops[typ]}", None
    okay, why = literal_audit(row["q"], ir)
    if not okay:
        return False, why, None
    result = execute(ir)
    expect = row.get("expect")
    if expect not in {"answer", "data_request"}:
        return False, "bad expect", None
    if result.get("status") != expect:
        return False, f"execution {result.get('status')}/{result.get('reason')} != {expect}", result
    if expect == "answer":
        value = result.get("value") or {}
        if not value.get("rows") and value.get("value") is None:
            return False, "ungrounded answer", result
    return True, "admitted", result


def existing_questions(paths):
    seen = set()
    for path in paths:
        if not os.path.isfile(path):
            continue
        data = json.load(open(path))
        for row in data.get("questions", []):
            seen.add(_norm(row.get("q", "")))
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["deepseekv4", "cursor"], required=True)
    ap.add_argument("--target", type=int, default=40)
    ap.add_argument("--batch", type=int, default=14)
    ap.add_argument("--max-batches", type=int, default=8)
    ap.add_argument("--style", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", nargs="*", default=[])
    a = ap.parse_args()
    seen = existing_questions([os.path.join(HERE, "active.json"), *a.exclude])
    admitted, rejected = [], []
    def coverage_ok():
        counts = Counter(row["type"] for row in admitted)
        return len(admitted) >= a.target and all(counts[t] >= 2 for t in TYPES)
    for batch in range(1, a.max_batches + 1):
        if coverage_ok():
            break
        try:
            candidates = generate(a.provider, a.batch, a.style + f"; independent batch {batch}")
        except Exception as exc:
            rejected.append({"batch": batch, "reason": f"generation: {type(exc).__name__}: {exc}"})
            print(rejected[-1]["reason"])
            continue
        for row in candidates:
            key = _norm(row.get("q", "")) if isinstance(row, dict) else ""
            if not key or key in seen:
                rejected.append({"q": row.get("q") if isinstance(row, dict) else None,
                                 "reason": "duplicate/empty"})
                continue
            try:
                row = {**row, "gold_ir": author_gold(a.provider, row["q"])}
            except Exception as exc:
                rejected.append({"q": row.get("q"), "type": row.get("type"),
                                 "reason": f"gold author: {type(exc).__name__}: {exc}"})
                print("REJECT", rejected[-1]["reason"], row.get("q"))
                continue
            ok, why, result = admit(row)
            if not ok:
                rejected.append({"q": row.get("q"), "type": row.get("type"), "reason": why})
                print("REJECT", why, row.get("q"))
                continue
            seen.add(key)
            admitted.append({"sector": "ecology", "type": row["type"], "q": row["q"],
                             "gold_ir": row["gold_ir"],
                             "gold_shape": [n["op"] for n in _walk(row["gold_ir"])
                                            if n.get("op") and n.get("op") != "REGION"],
                             "expect": row["expect"],
                             **({"must_hole": True} if row["type"] in {"AMBIGUOUS", "BEHAVIOUR"} else {}),
                             **({"must_estimate": True} if row["type"] == "TRANSFER" else {})})
            if coverage_ok():
                break
        print(f"batch {batch}: admitted={len(admitted)} rejected={len(rejected)}")
    if not coverage_ok():
        counts = Counter(row["type"] for row in admitted)
        raise SystemExit(f"admitted {len(admitted)} but coverage incomplete {dict(counts)}; no holdout written")
    # Preserve two of every family, then fill with earliest remaining admissions. This prevents a
    # prolific easy family from pushing a rare adversarial/transfer family out of the 40-row bank.
    selected, used = [], set()
    for typ in TYPES:
        for i, row in [(i, r) for i, r in enumerate(admitted) if r["type"] == typ][:2]:
            selected.append(row); used.add(i)
    for i, row in enumerate(admitted):
        if len(selected) >= a.target:
            break
        if i not in used:
            selected.append(row); used.add(i)
    prefix = os.path.basename(a.out).split('.')[0]
    for i, row in enumerate(selected, 1):
        row["id"] = f"{prefix}-{i:03d}"
    out = {"bank": os.path.basename(a.out).split(".")[0], "eval_only": True,
           "generated_after_freeze": True, "provider": a.provider,
           "generator_model": ("deepseek/deepseek-v4-flash" if a.provider == "deepseekv4"
                               else "cursor:gpt-5.4-mini-low"),
           "style": a.style, "questions": selected, "rejections": rejected}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote {a.target} untouched rows -> {a.out}; rejected {len(rejected)}")


if __name__ == "__main__":
    main()
