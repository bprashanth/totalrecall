"""compile_corpus — distill all run traces into a training corpus for the laptop-sized model.

The stated goal of the whole exercise: a small model that translates a user question into the
algebra and answers with data. This produces its training set from everything the loop verified:

  corpus/parse.jsonl      {"messages":[{system},{user: question},{assistant: IR}]}
                          — one per question, the VERIFIED tree (parser's own tree when it scored
                          perfect; else the gold). Deduped by question, latest tick wins.
  corpus/clarify.jsonl    multiturn rows: question -> holed tree -> rendered clarify -> reply ->
                          bound tree (teaches turn-1 hole placement + that binding is mechanical).
  corpus/README.md        provenance + counts + how to use.

Only rows whose tree VALIDATES and whose execution matched the expected class are kept — the
corpus inherits the harness's honesty guarantees rather than trusting any single model.
"""
import glob
import json
import os

from ir_schema import validate
import parser as P

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "runs")
OUT = os.path.join(HERE, "..", "corpus")
GOLD_DEFECTS = os.path.join(HERE, "..", "coverage", "gold-defects.json")


def active_questions():
    active = set()
    for path in glob.glob(os.path.join(HERE, "..", "questions", "*.json")):
        try:
            d = json.load(open(path))
        except (json.JSONDecodeError, OSError):
            continue
        if isinstance(d, dict) and isinstance(d.get("questions"), list):
            active.update(q.get("q", "").strip() for q in d["questions"] if q.get("q"))
    return active


def declared_gold_defects():
    """Durable exclusions prevent validated-but-wrong historical golds entering training."""
    try:
        data = json.load(open(GOLD_DEFECTS))
    except (json.JSONDecodeError, OSError):
        return set()
    return {row.get("id") for row in data.get("rows", []) if row.get("id")}


def collect_parse_rows():
    best = {}  # question -> (mtime, row)
    active = active_questions()
    defects = declared_gold_defects()
    for path in sorted(glob.glob(os.path.join(RUNS, "*", "traces.jsonl"))):
        mtime = os.path.getmtime(path)
        for line in open(path):
            r = json.loads(line)
            if "question" not in r or "scores" not in r:
                continue
            if r.get("model") != "qwen2b":
                continue  # frontier controls are evaluation, not parser-under-test self-training
            if r.get("id") in defects:
                continue  # an executable/schema-valid tree can still be a declared bad gold
            s = r["scores"]
            ir = None
            if s.get("overall", 0) >= 0.999 and r.get("ir"):
                ir = r["ir"]                       # the parser's own verified tree
            elif r.get("gold_ir") and s.get("overall", 0) < 0.999:
                g = r["gold_ir"]
                if validate(g)["valid"]:
                    ir = g                          # fall back to validated gold
            if ir is None:
                continue
            q = r["question"].strip()
            if q not in active:
                continue  # superseded/rejected historical traces must not re-enter training
            if q not in best or mtime >= best[q][0]:
                best[q] = (mtime, {"question": q, "ir": ir,
                                   "sector": r.get("sector"), "type": r.get("type"),
                                   "source_run": os.path.basename(os.path.dirname(path))})
    return [v for _, v in sorted(best.values(), key=lambda x: x[1]["question"])]


def collect_clarify_rows():
    best = {}
    for path in sorted(glob.glob(os.path.join(RUNS, "*mt*", "traces.jsonl"))):
        mtime = os.path.getmtime(path)
        for line in open(path):
            r = json.loads(line)
            if not r.get("ir_turn1") or not r["scores"].get("asked_when_needed"):
                continue
            # Training target is mechanical binding; admit only fully verified substitutions.
            if not all(r["scores"].get(k) for k in
                       ("mech_bound", "mech_skeleton_kept", "mech_exec_ok")):
                continue
            bound = r.get("ir_bound_mech")
            rep = validate(bound) if bound else None
            if not rep or not rep["valid"] or rep["holes"]:
                continue
            key = (r["question"], r["reply"])
            row = {"question": r["question"], "ir_holed": r["ir_turn1"],
                   "clarify": r.get("clarify_rendered"), "reply": r["reply"],
                   "ir_bound": bound}
            if key not in best or mtime >= best[key][0]:
                best[key] = (mtime, row)
    return [v[1] for v in sorted(best.values(), key=lambda x: x[1]["question"])]


def main():
    os.makedirs(OUT, exist_ok=True)
    system = P.SYSTEM
    parse_rows = collect_parse_rows()
    with open(os.path.join(OUT, "parse.jsonl"), "w") as f:
        for r in parse_rows:
            f.write(json.dumps({"messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": r["question"]},
                {"role": "assistant", "content": json.dumps(r["ir"])}],
                "meta": {k: r[k] for k in ("sector", "type", "source_run")}}) + "\n")
    clar_rows = collect_clarify_rows()
    with open(os.path.join(OUT, "clarify.jsonl"), "w") as f:
        for r in clar_rows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write(f"""# Training corpus (auto-compiled by compile_corpus.py)

- `parse.jsonl` — {len(parse_rows)} verified (question → IR) pairs in chat format, across sectors.
  A row is included only if the tree validates AND its execution matched the expected outcome
  class in a benchmark run. When the small parser's own tree scored perfect, that tree is used
  (self-training signal); otherwise the validated gold.
- `clarify.jsonl` — {len(clar_rows)} multiturn rows (holed tree → rendered clarifying question →
  user reply → bound tree). Binding is mechanical; these teach turn-1 hole placement.
- System prompt = the live parser prompt (parser.SYSTEM) at compile time; recompile after prompt
  changes: `python3 harness/compile_corpus.py`.
""")
    print(f"parse.jsonl: {len(parse_rows)} rows | clarify.jsonl: {len(clar_rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
