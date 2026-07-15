"""xsector_stats — hallucination/factuality table with honest intervals.

Reads runs/xsector-h027-*-a0|a1 traces (dual-judged) and prints per (model, arm):
rates under judge1 (deepseek), judge2 (glm), the CONSENSUS rule we report
(hallucinated = both judges say hallucinated; factual = both say factual; disagreements
counted and listed for supervisor adjudication), and Wilson 95% intervals at the run's n.
"""
import glob
import json
import math
import os
import sys

RUNS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "runs")


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


def load(d):
    rows = []
    with open(os.path.join(d, "traces.jsonl")) as f:
        for line in f:
            rows.append(json.loads(line))
    return rows


def stats(rows):
    n = len(rows)
    out = {"n": n}
    for key in ("factual", "hallucinated", "honest_unknown"):
        k1 = sum(1 for r in rows if (r.get("judge") or {}).get(key))
        k2 = sum(1 for r in rows if (r.get("judge2") or {}).get(key))
        kc = sum(1 for r in rows if (r.get("judge") or {}).get(key)
                 and (r.get("judge2") or {}).get(key))
        lo, hi = wilson(kc, n)
        out[key] = {"j1": k1 / n, "j2": k2 / n, "consensus": kc / n,
                    "ci95": (round(lo, 3), round(hi, 3))}
    out["disagree"] = sum(1 for r in rows if r.get("judges_disagree"))
    return out


def main(pattern="xsector-h027-*-a[01]"):
    dirs = sorted(glob.glob(os.path.join(RUNS, pattern)))
    table = []
    for d in dirs:
        name = os.path.basename(d)
        parts = name.split("-")
        model, arm = parts[2], parts[3]
        try:
            rows = load(d)
        except FileNotFoundError:
            continue
        s = stats(rows)
        table.append((model, arm, s))
        h = s["hallucinated"]
        f_ = s["factual"]
        print(f"{model:12} {arm}  n={s['n']:3}  "
              f"halluc j1={h['j1']:.2f} j2={h['j2']:.2f} cons={h['consensus']:.2f} "
              f"CI95=[{h['ci95'][0]:.2f},{h['ci95'][1]:.2f}]  "
              f"factual cons={f_['consensus']:.2f}  disagree={s['disagree']}")
    out = os.path.join(RUNS, "..", "graphs", "xsector_a0a1_stats.json")
    with open(out, "w") as f:
        json.dump([{"model": m, "arm": a, **s} for m, a, s in table], f, indent=1)
    print(f"-> {os.path.normpath(out)}")


if __name__ == "__main__":
    main(*sys.argv[1:])
