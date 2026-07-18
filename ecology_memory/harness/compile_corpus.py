"""compile_corpus — distill all run traces into a training corpus for the laptop-sized model.

The stated goal of the whole exercise: a small model that translates a user question into the
algebra and answers with data. This produces its training set from everything the loop verified:

  corpus/parse.jsonl      {"messages":[{system},{user: question},{assistant: IR}]}
                          — one per question, the parser's VERIFIED tree from an allowlisted run.
                          Deduped by question, latest verified run wins.
  corpus/clarify.jsonl    multiturn rows: question -> holed tree -> rendered clarify -> reply ->
                          bound tree (teaches turn-1 hole placement + that binding is mechanical).
  corpus/README.md        provenance + counts + how to use.

Only rows whose tree VALIDATES and whose execution matched the expected class are kept — the
corpus inherits the harness's honesty guarantees rather than trusting any single model.
"""
import glob
import argparse
import json
import os

from ir_schema import validate
import parser as P

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "runs")
OUT = os.path.join(HERE, "..", "corpus")
DEFAULT_MANIFEST = os.path.join(OUT, "verified-runs.json")


def _trace_paths(run_names=None):
    if run_names is None:
        return sorted(glob.glob(os.path.join(RUNS, "*", "traces.jsonl")))
    paths = []
    for name in run_names:
        path = os.path.join(RUNS, name, "traces.jsonl")
        if not os.path.isfile(path):
            raise FileNotFoundError(f"verified run has no trace: {path}")
        paths.append(path)
    return paths


def collect_parse_rows(run_names=None):
    best = {}  # question -> (mtime, row)
    for path in _trace_paths(run_names):
        mtime = os.path.getmtime(path)
        for line in open(path):
            r = json.loads(line)
            if "question" not in r or "scores" not in r:
                continue
            s = r["scores"]
            # Corpus admission is stricter than a weighted aggregate. Every honesty and behavior
            # dimension must be green; a high overall score cannot compensate for a wrong outcome.
            required = ("schema_valid", "shape_match", "semantic_fidelity", "holes_correct", "estimate_ok",
                        "exec_class", "exec_grounded")
            if not all(s.get(k) is True for k in required):
                continue
            ir = None
            if s.get("overall", 0) >= 0.999 and r.get("ir"):
                ir = r["ir"]                       # the parser's own verified tree
            if ir is None:
                continue
            q = r["question"].strip()
            if q not in best or mtime >= best[q][0]:
                best[q] = (mtime, {"question": q, "ir": ir,
                                   "sector": r.get("sector"), "type": r.get("type"),
                                   "source_run": os.path.basename(os.path.dirname(path))})
    return [v for _, v in sorted(best.values(), key=lambda x: x[1]["question"])]


def collect_clarify_rows(run_names=None):
    rows = []
    paths = _trace_paths(run_names) if run_names is not None else \
        sorted(glob.glob(os.path.join(RUNS, "*mt*", "traces.jsonl")))
    for path in paths:
        if "mt" not in os.path.basename(os.path.dirname(path)):
            continue
        for line in open(path):
            r = json.loads(line)
            scores = r.get("scores") or {}
            if (not r.get("ir_turn1") or not scores.get("asked_when_needed") or
                    not all(scores.get(k) for k in
                            ("mech_bound", "mech_skeleton_kept", "mech_exec_ok"))):
                continue
            bound = r.get("ir_bound_mech")
            if not bound:
                continue
            rows.append({"question": r["question"], "ir_holed": r["ir_turn1"],
                         "clarify": r.get("clarify_rendered"), "reply": r["reply"],
                         "ir_bound": bound})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEFAULT_MANIFEST,
                    help="JSON file with a verified_runs array; only those traces are admitted")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)
    if not os.path.isfile(a.manifest):
        raise SystemExit(f"refusing broad corpus scan: create verified-run manifest {a.manifest}")
    manifest = json.load(open(a.manifest))
    run_names = manifest.get("verified_runs")
    if not isinstance(run_names, list) or not run_names:
        raise SystemExit("verified-run manifest needs a non-empty verified_runs list")
    system = P.SYSTEM
    parse_rows = collect_parse_rows(run_names)
    with open(os.path.join(OUT, "parse.jsonl"), "w") as f:
        for r in parse_rows:
            f.write(json.dumps({"messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": r["question"]},
                {"role": "assistant", "content": json.dumps(r["ir"])}],
                "meta": {k: r[k] for k in ("sector", "type", "source_run")}}) + "\n")
    clar_rows = collect_clarify_rows(run_names)
    with open(os.path.join(OUT, "clarify.jsonl"), "w") as f:
        for r in clar_rows:
            f.write(json.dumps(r) + "\n")
    with open(os.path.join(OUT, "README.md"), "w") as f:
        f.write(f"""# Training corpus (auto-compiled by compile_corpus.py)

- `parse.jsonl` — {len(parse_rows)} verified (question → IR) pairs in chat format.
  A row is included only if the tree validates AND its execution matched the expected outcome
  class, shape, hole, estimate, and grounding requirements in an allowlisted benchmark run. The
  row always uses the small parser's own verified tree; a gold fallback is never silently trained.
- `clarify.jsonl` — {len(clar_rows)} multiturn rows (holed tree → rendered clarifying question →
  user reply → bound tree). Binding is mechanical; these teach turn-1 hole placement.
- System prompt = the live parser prompt (parser.SYSTEM) at compile time; recompile after prompt
  changes: `python3 harness/compile_corpus.py`.
- Admission allowlist = `{os.path.basename(a.manifest)}`; verified runs: {', '.join(run_names)}.
""")
    print(f"parse.jsonl: {len(parse_rows)} rows | clarify.jsonl: {len(clar_rows)} rows -> {OUT}")


if __name__ == "__main__":
    main()
