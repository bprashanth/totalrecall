"""curve — aggregate all arm runs into the results table the ROI graphs are built from.

Emits ../graphs/results.csv + results.json with one row per (model, arm, bank):
  model, params_b, arm, n, score, hallucinated, honest_unknown, factual, mean_latency_s
'score' semantics per arm: A2/A3 = behavioral+structural overall (run_bench); A0/A1 = judged
factual rate (arms.py). They share a 0..1 scale and the graphs label them honestly.
"""
import csv
import glob
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RUNS = os.path.join(HERE, "..", "runs")
GRAPHS = os.path.join(HERE, "..", "graphs")

PARAMS_B = {"qwen2b": 2, "qwen9b": 9, "qwen27b": 27, "qwen122b": 122, "qwen397b": 397,
            "coder30b": 30, "deepseekv4": 671, "loravb": 2}
LABELS = {"qwen2b": "Qwen3.5-2B (local)", "qwen9b": "Qwen3.5-9B", "qwen27b": "Qwen3.5-27B",
          "qwen122b": "Qwen3.5-122B", "qwen397b": "Qwen3.5-397B",
          "coder30b": "Qwen3-Coder-30B (specialist)", "deepseekv4": "DeepSeek-V4 (frontier)",
          "loravb": "Qwen3.5-2B + LoRA"}


def rows():
    out = []
    for d in sorted(glob.glob(os.path.join(RUNS, "curve-*"))):
        name = os.path.basename(d)          # curve-A2-qwen9b-seed
        parts = name.split("-")
        if len(parts) < 4:
            continue
        arm, model, bank = parts[1], parts[2], "-".join(parts[3:])
        sp = os.path.join(d, "summary.json")
        if not os.path.exists(sp):
            continue
        s = json.load(open(sp))
        row = {"model": model, "label": LABELS.get(model, model),
               "params_b": PARAMS_B.get(model), "arm": arm, "bank": bank}
        if "aggregate" in s:                 # run_bench (A2/A3)
            a = s["aggregate"]
            # latency: mean over trace rows (includes connector time)
            lat = None
            tp = os.path.join(d, "traces.jsonl")
            if os.path.exists(tp):
                ls = [json.loads(l).get("latency_s", 0) for l in open(tp)]
                lat = round(sum(ls) / max(len(ls), 1), 2)
            row.update(n=a.get("n"), score=a.get("overall"),
                       factual=None, hallucinated=None, honest_unknown=None,
                       mean_latency_s=lat)
        else:                                # arms.py (A0/A1)
            row.update(n=s.get("n"), score=s.get("factual"),
                       factual=s.get("factual"), hallucinated=s.get("hallucinated"),
                       honest_unknown=s.get("honest_unknown"),
                       mean_latency_s=s.get("mean_latency_s"))
        out.append(row)
    # A2 for the local 2B lives in the tick runs (same bank, same scorer) — inject the canonical one
    seed_2b = os.path.join(RUNS, "tick-023-seed", "summary.json")
    if os.path.exists(seed_2b):
        a = json.load(open(seed_2b))["aggregate"]
        out.append({"model": "qwen2b", "label": LABELS["qwen2b"], "params_b": 2, "arm": "A2",
                    "bank": "seed", "n": a["n"], "score": a["overall"], "factual": None,
                    "hallucinated": None, "honest_unknown": None, "mean_latency_s": None})
    return out


def main():
    os.makedirs(GRAPHS, exist_ok=True)
    rs = rows()
    with open(os.path.join(GRAPHS, "results.json"), "w") as f:
        json.dump(rs, f, indent=1)
    cols = ["model", "label", "params_b", "arm", "bank", "n", "score",
            "factual", "hallucinated", "honest_unknown", "mean_latency_s"]
    with open(os.path.join(GRAPHS, "results.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rs:
            w.writerow({k: r.get(k) for k in cols})
    print(f"{len(rs)} rows -> graphs/results.csv")
    for r in sorted(rs, key=lambda x: (x["arm"], x["params_b"] or 0)):
        print(f"  {r['arm']} {r['model']:12} score={r['score']} halluc={r['hallucinated']}")


if __name__ == "__main__":
    main()
