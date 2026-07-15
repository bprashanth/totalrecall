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
            "coder30b": 30, "deepseekv4": 671, "loravb": 2, "hammer7b": 7, "lora9b": 9}
LABELS = {"qwen2b": "Qwen3.5-2B (local)", "qwen9b": "Qwen3.5-9B", "qwen27b": "Qwen3.5-27B",
          "qwen122b": "Qwen3.5-122B", "qwen397b": "Qwen3.5-397B",
          "coder30b": "Qwen3-Coder-30B (specialist)", "deepseekv4": "DeepSeek-V4 (frontier)",
          "loravb": "Qwen3.5-2B + LoRA (A3)", "hammer7b": "Hammer2.1-7B (fc-specialist)",
          "lora9b": "Qwen3.5-9B + LoRA (A3)"}


def rows():
    out = []
    # curve-A2-qwen9b-seed (original) + xsector-h025-qwen2b-a2 (livelihoods holdouts, 2026-07-13)
    dirs = sorted(glob.glob(os.path.join(RUNS, "curve-*"))) + \
        sorted(glob.glob(os.path.join(RUNS, "xsector-h0*")))
    for d in dirs:
        name = os.path.basename(d)
        parts = name.split("-")
        if len(parts) < 4:
            continue
        if name.startswith("xsector"):
            arm, model, bank = parts[3].upper(), parts[2], "xliv-" + parts[1]
            if model in ("loravb", "lora9b") and arm == "A2":
                arm = "A3"  # the LoRA arm keeps its A3 identity on cross-sector runs
        else:
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
            row.update(n=a.get("n"), score=a.get("overall"), shape=a.get("shape_match"),
                       factual=None, hallucinated=None, honest_unknown=None,
                       mean_latency_s=lat)
        else:                                # arms.py (A0/A1)
            row.update(n=s.get("n"), score=s.get("factual"),
                       factual=s.get("factual"), hallucinated=s.get("hallucinated"),
                       honest_unknown=s.get("honest_unknown"),
                       mean_latency_s=s.get("mean_latency_s"))
        out.append(row)
    # Canonical runs that predate the curve-* naming — inject them so results.csv is complete.
    # (lora3 = post-cache-purge reruns; lora/lora2 were the GOTCHA-8 poisoned false negatives.)
    INJECT = [  # dir, model, arm, bank
        ("tick-023-seed", "qwen2b", "A2", "seed"),
        ("hardeval-baseline2-qwen2b", "qwen2b", "A2", "hardeval"),
        ("hard1-A2-qwen2b", "qwen2b", "A2", "hard1"),
        ("hard1-A2-qwen9b", "qwen9b", "A2", "hard1"),
        ("hard1-A2-qwen27b", "qwen27b", "A2", "hard1"),
        ("hard1-A2-qwen122b", "qwen122b", "A2", "hard1"),
        ("hard1-A2-qwen397b", "qwen397b", "A2", "hard1"),
        ("hard1-A2-coder30b", "coder30b", "A2", "hard1"),
        ("hard1-A2-hammer7b", "hammer7b", "A2", "hard1"),
        ("hard1-A2-deepseekv4", "deepseekv4", "A2", "hard1"),
        ("hardeval-deepseek", "deepseekv4", "A2", "hardeval"),
        ("hardeval-hammer7b", "hammer7b", "A2", "hardeval"),
        ("seed-lora3", "loravb", "A3", "seed"),
        ("hardeval-lora3", "loravb", "A3", "hardeval"),
        ("hard1-lora", "loravb", "A3", "hard1"),
    ]
    for dname, model, arm, bank in INJECT:
        sp = os.path.join(RUNS, dname, "summary.json")
        if not os.path.exists(sp):
            continue
        a = json.load(open(sp))["aggregate"]
        out.append({"model": model, "label": LABELS.get(model, model),
                    "params_b": PARAMS_B.get(model), "arm": arm, "bank": bank,
                    "n": a["n"], "score": a["overall"], "shape": a.get("shape_match"),
                    "factual": None, "hallucinated": None, "honest_unknown": None,
                    "mean_latency_s": None})
    return out


def main():
    os.makedirs(GRAPHS, exist_ok=True)
    rs = rows()
    with open(os.path.join(GRAPHS, "results.json"), "w") as f:
        json.dump(rs, f, indent=1)
    cols = ["model", "label", "params_b", "arm", "bank", "n", "score", "shape",
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
