#!/usr/bin/env python3
"""Build a parser-blind holdout by independently paraphrasing execution-audited seed semantics."""
import argparse
import copy
from collections import defaultdict
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
from build_holdout import literal_audit, _norm


PROMPT = """Rewrite each ecology question in the requested style while preserving EXACTLY the
same single question and data semantics. Return ONLY a JSON array of {{"key":...,"q":...}}.

Style: {style}

Hard constraints:
- Preserve every named entity/taxon/measure/layer, named place, year/date, number, distance and
  unit, comparison direction, negation, record-vs-organism wording, and number of ranked places.
- Do not add a source, site, filter, grouping, cause, second request, or factual answer.
- Keep deictic/missing information missing: never fill “here”, an unspecified wildlife type, proxy,
  or indicator.
- One sentence and one answer only. Make the wording genuinely different, not just add a prefix.

Rows:
{rows}
"""


def slots(seed, n=40, variant=0):
    by_type = defaultdict(list)
    for row in seed:
        by_type[row["type"]].append(row)
    chosen = []
    # Two independently worded rows per family guarantees coverage even for one-row families.
    for typ in sorted(by_type):
        group = by_type[typ]
        for i in range(2):
            chosen.append(group[(variant + i) % len(group)])
    i = 0
    while len(chosen) < n:
        chosen.append(seed[(variant * 7 + i) % len(seed)])
        i += 1
    return [{"key": f"slot-{i+1:03d}", "base": copy.deepcopy(row)}
            for i, row in enumerate(chosen[:n])]


def call(provider, batch, style, attempt):
    rows = [{"key": row["key"], "type": row["base"]["type"],
             "original": row["base"]["q"]} for row in batch]
    prompt = PROMPT.format(style=style + f"; rewrite attempt {attempt}",
                           rows=json.dumps(rows, ensure_ascii=False, indent=2))
    if provider == "deepseekv4":
        raw = chat("deepseekv4", [{"role": "user", "content": prompt}], temperature=0.8,
                   max_tokens=5000, use_cache=False, timeout=300)
    else:
        raw = subprocess.run(
            ["agent", "-p", "--trust", "--mode", "ask", "--model", "gpt-5.4-mini-low", prompt],
            capture_output=True, text=True, timeout=300, cwd="/tmp").stdout
    start, end = raw.find("["), raw.rfind("]")
    if start < 0 or end <= start:
        return []
    return json.loads(raw[start:end + 1])


def faithful(base, question):
    if not isinstance(question, str) or not question.strip() or _norm(question) == _norm(base["q"]):
        return False, "empty/unchanged"
    if len(re.findall(r"[.!?]", question)) > 1:
        return False, "not one sentence"
    okay, why = literal_audit(question, base["gold_ir"])
    if not okay:
        return False, why
    original_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", base["q"]))
    new_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", question))
    if original_nums != new_nums:
        return False, f"number drift {original_nums}->{new_nums}"
    negative = bool(re.search(r"\b(no|not|without|beyond)\b", base["q"], re.I))
    if negative and not re.search(r"\b(no|not|without|beyond|farther|outside)\b", question, re.I):
        return False, "negation dropped"
    # Do not let a paraphrase add/drop an explicit unsupported ecological measure. Although both
    # forms may safely DataRequest, `how many elephants` and `elephant abundance` compile through
    # different honest IR boundaries and therefore cannot inherit one another's gold.
    unsupported = r"\b(population|abundance|biomass|occupancy|richness)\b"
    if bool(re.search(unsupported, base["q"], re.I)) != bool(re.search(unsupported, question, re.I)):
        return False, "unsupported-measure wording drift"
    return True, "faithful"


def existing(paths):
    seen = set()
    for path in paths:
        if os.path.isfile(path):
            seen |= {_norm(row["q"]) for row in json.load(open(path)).get("questions", [])}
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", choices=["deepseekv4", "cursor"], required=True)
    ap.add_argument("--style", required=True)
    ap.add_argument("--variant", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--exclude", nargs="*", default=[])
    a = ap.parse_args()
    seed = json.load(open(os.path.join(HERE, "seed.json")))["questions"]
    pending = {row["key"]: row for row in slots(seed, 40, a.variant)}
    accepted, rejected = {}, []
    seen = existing([os.path.join(HERE, "active.json"), *a.exclude])
    # Lower-tier independent authors can need several literal-preserving retries on numeric and
    # negated slots. Attempts are generator-side only; no parser output or failure trace is fed
    # back, and an incomplete bank is still never written.
    for attempt in range(1, 33):
        if not pending:
            break
        items = list(pending.values())
        for pos in range(0, len(items), 10):
            batch = items[pos:pos + 10]
            try:
                output = call(a.provider, batch, a.style, attempt)
            except Exception as exc:
                rejected.append({"attempt": attempt, "reason": f"generator {type(exc).__name__}: {exc}"})
                continue
            by_key = {row.get("key"): row.get("q") for row in output if isinstance(row, dict)}
            for slot in batch:
                question = by_key.get(slot["key"])
                okay, why = faithful(slot["base"], question)
                if okay and _norm(question) not in seen:
                    base = slot["base"]
                    rep = validate(base["gold_ir"])
                    result = execute(base["gold_ir"])
                    if rep["valid"] and result.get("status") == base["expect"]:
                        accepted[slot["key"]] = {**copy.deepcopy(base), "q": question,
                                                 "derived_from": base["id"],
                                                 "generation_family": a.provider}
                        seen.add(_norm(question))
                        pending.pop(slot["key"], None)
                        continue
                    why = f"inherited gold no longer executes: {result.get('status')}"
                rejected.append({"key": slot["key"], "attempt": attempt,
                                 "q": question, "reason": why})
        print(f"attempt {attempt}: accepted={len(accepted)} pending={len(pending)}")
    if pending:
        raise SystemExit(f"no bank written; unresolved slots: {sorted(pending)}")
    ordered = [accepted[f"slot-{i:03d}"] for i in range(1, 41)]
    prefix = os.path.basename(a.out).split(".")[0]
    for i, row in enumerate(ordered, 1):
        row["id"] = f"{prefix}-{i:03d}"
    out = {"bank": prefix, "eval_only": True, "generated_after_freeze": True,
           "provider": a.provider,
           "generator_model": ("deepseek/deepseek-v4-flash" if a.provider == "deepseekv4"
                               else "cursor:gpt-5.4-mini-low"),
           "style": a.style, "variant": a.variant, "questions": ordered,
           "rejections": rejected}
    with open(a.out, "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"wrote 40 parser-blind rows -> {a.out}; rejected rewrites={len(rejected)}")


if __name__ == "__main__":
    main()
