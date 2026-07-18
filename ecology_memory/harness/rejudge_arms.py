"""Rejudge saved arm answers after judge-ground-truth fixes without rerunning answer models."""
import argparse
import json
import os

from arms import gold_truth, judge_prose_cursor, judge_prose


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--judge", default="cursor")
    a = ap.parse_args()
    by_id = {q["id"]: q for q in json.load(open(a.questions))["questions"]}
    trace = os.path.join(a.run, "traces.jsonl")
    rows = [json.loads(x) for x in open(trace)]
    tmp = trace + ".rejudge.tmp"
    with open(tmp, "w") as f:
        for row in rows:
            gt = gold_truth(by_id[row["id"]]["gold_ir"])
            judge = (judge_prose_cursor(row["question"], row["answer"], gt)
                     if a.judge == "cursor" else judge_prose(row["question"], row["answer"], gt,
                                                             a.judge))
            row["ground_truth"] = gt
            row["judge"] = judge
            f.write(json.dumps(row, default=str) + "\n")
            print(row["id"], judge)
    os.replace(tmp, trace)
    n = len(rows)
    def rate(key):
        return round(sum(bool(r["judge"].get(key)) for r in rows) / n, 3)
    summary = {"model": rows[0]["model"], "arm": rows[0]["arm"], "n": n,
               "factual": rate("factual"), "hallucinated": rate("hallucinated"),
               "honest_unknown": rate("honest_unknown"),
               "mean_latency_s": round(sum(r.get("latency_s", 0) for r in rows) / n, 2),
               "rejudged": True, "judge": a.judge}
    json.dump(summary, open(os.path.join(a.run, "summary.json"), "w"), indent=2)
    print(summary)


if __name__ == "__main__":
    main()
