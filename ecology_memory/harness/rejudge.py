"""rejudge — recompute ground truth (fixed gold_truth) + re-judge cached answers in A0/A1 runs."""
import glob, json, os, sys
import arms
banks = {}
for p in glob.glob("questions/*.json"):
    d = json.load(open(p))
    if isinstance(d, dict):
        for q in d.get("questions", []):
            banks[q["id"] + "|" + q["q"][:40]] = q
for run in sorted(glob.glob("../runs/curve-A[01]-*")):
    tp = os.path.join(run, "traces.jsonl")
    if not os.path.exists(tp): continue
    rows = [json.loads(l) for l in open(tp)]
    changed = 0
    for r in rows:
        q = banks.get(r["id"] + "|" + r["question"][:40])
        if not q: continue
        gt = arms.gold_truth(q["gold_ir"])
        j = arms.judge_prose(r["question"], r["answer"], gt)
        if j != r.get("judge"): changed += 1
        r["ground_truth"], r["judge"] = gt, j
    with open(tp, "w") as f:
        for r in rows: f.write(json.dumps(r, default=str) + "\n")
    n = len(rows)
    def rate(k): return round(sum(1 for r in rows if r["judge"].get(k)) / n, 3)
    s = json.load(open(os.path.join(run, "summary.json")))
    s.update(factual=rate("factual"), hallucinated=rate("hallucinated"),
             honest_unknown=rate("honest_unknown"), rejudged=True)
    json.dump(s, open(os.path.join(run, "summary.json"), "w"), indent=2)
    print(f"{os.path.basename(run)}: {changed}/{n} verdicts changed -> factual={s['factual']} halluc={s['hallucinated']} honest={s['honest_unknown']}")
