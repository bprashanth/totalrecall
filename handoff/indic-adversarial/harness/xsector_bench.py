"""xsector_bench — run OUR model arms on the LIVELIHOODS holdout banks (cross-sector OOD).

Ground truth = the livelihoods snapshot's executor + connectors + scorer + ir_schema
(that repo is FINISHED and READ-ONLY; the only writes its modules do are to its gitignored
harness/cache). The parser/prompt/llm stack is OURS — the models under test. Modules are
stitched by preloading sys.modules from explicit paths, so each side keeps its own __file__
(and therefore its own cache dirs and fewshots).

Arms:
  a2  compile scaffold  -> heartwood run_bench.run (supports --minimal for the LoRA roles)
  a0  no tools          -> arms.run_a0 + DUAL judge (deepseekv4 + cursor CLI), resumable
  a1  freeform tools    -> arms.run_a1 + DUAL judge, resumable

Usage (cwd anywhere; outputs land where --out says — keep them in heartwood runs/):
  python3 xsector_bench.py --arm a2 --model qwen2b  --questions <bank> --out ../runs/xsector-h25-qwen2b
  python3 xsector_bench.py --arm a2 --model loravb --minimal --questions <bank> --out ...
  python3 xsector_bench.py --arm a0 --model qwen9b --questions <bank> --out ...
"""
import argparse
import importlib.util
import json
import os
import sys
import time

HW = os.path.dirname(os.path.abspath(__file__))
LIV = os.path.expanduser(
    "~/src/github.com/bprashanth/totalrecall/livelihoods_memory/harness")


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


# dependency order matters: llm first (parser/arms import it), ground-truth stack from the
# livelihoods snapshot, then our parser and the runners on top.
_load("llm", os.path.join(HW, "llm.py"))                 # OUR roles (:8001/:8002/:8003/:8004/API)
_load("connectors", os.path.join(LIV, "connectors.py"))  # THEIR data snapshot + data cache
_load("ir_schema", os.path.join(LIV, "ir_schema.py"))    # THEIR pinned spec (v2.2 superset)
_load("executor", os.path.join(LIV, "executor.py"))      # THEIR execution semantics
_load("scorer", os.path.join(LIV, "scorer.py"))          # THEIR gold-side scoring
_load("parser", os.path.join(HW, "parser.py"))           # OUR prompt = the thing under test
RB = _load("run_bench", os.path.join(HW, "run_bench.py"))
ARMS = _load("arms", os.path.join(HW, "arms.py"))


JUDGE2 = "glm"  # 2026-07-13: cursor CLI is usage-capped until 8/2 (all models); judge #2 is
                # glm-5.2 (z-ai) via OpenRouter — still a different vendor from judge #1 (deepseek).


def run_a0a1(arm, model, questions_path, out_dir, limit=None, dual=True):
    """arms.py __main__ equivalent, plus: dual judge (deepseek + glm), resume-on-restart."""
    os.makedirs(out_dir, exist_ok=True)
    bank = json.load(open(questions_path))
    qs = bank["questions"][:limit] if limit else bank["questions"]
    trace_path = os.path.join(out_dir, "traces.jsonl")
    done = set()
    rows = []
    if os.path.exists(trace_path):  # resume: keep completed records
        with open(trace_path) as f:
            for line in f:
                try:
                    r = json.loads(line)
                    done.add(r["id"])
                    rows.append(r)
                except json.JSONDecodeError:
                    pass
    with open(trace_path, "a") as tf:
        for q in qs:
            if q["id"] in done:
                continue
            gt = ARMS.gold_truth(q["gold_ir"])
            t0 = time.time()
            if arm == "a0":
                ans, transcript = ARMS.run_a0(q["q"], model), None
            else:
                ans, transcript = ARMS.run_a1(q["q"], model)
            js = ARMS.judge_prose(q["q"], ans, gt, "deepseekv4")
            js2 = ARMS.judge_prose(q["q"], ans, gt, JUDGE2) if dual else None
            rec = {"id": q["id"], "sector": q.get("sector"), "type": q.get("type"),
                   "question": q["q"], "model": model, "arm": arm, "answer": ans,
                   "ground_truth": gt, "judge": js, "judge2": js2, "judge2_role": JUDGE2,
                   "judges_disagree": bool(js2) and any(
                       js.get(k) is not None and js2.get(k) is not None and js[k] != js2[k]
                       for k in ("factual", "hallucinated")),
                   "transcript": transcript, "latency_s": round(time.time() - t0, 2)}
            tf.write(json.dumps(rec, default=str) + "\n")
            tf.flush()
            rows.append(rec)
            d = " DISAGREE" if rec["judges_disagree"] else ""
            print(f"{q['id']:12} factual={js.get('factual')} halluc={js.get('hallucinated')}"
                  f"{d} {q['q'][:40]}", flush=True)

    def rate(k, judge_key="judge"):
        vals = [r for r in rows if r.get(judge_key)]
        if not vals:
            return None
        return round(sum(1 for r in vals if r[judge_key].get(k)) / len(vals), 3)

    summ = {"model": model, "arm": arm, "n": len(rows), "questions": questions_path,
            "factual": rate("factual"), "hallucinated": rate("hallucinated"),
            "honest_unknown": rate("honest_unknown"),
            "factual_j2": rate("factual", "judge2"),
            "hallucinated_j2": rate("hallucinated", "judge2"),
            "n_disagree": sum(1 for r in rows if r.get("judges_disagree")),
            "mean_latency_s": round(sum(r["latency_s"] for r in rows) / max(len(rows), 1), 2)}
    json.dump(summ, open(os.path.join(out_dir, "summary.json"), "w"), indent=2)
    print(f"\n== {model} {arm} == factual={summ['factual']} halluc={summ['hallucinated']} "
          f"(j2: {summ['factual_j2']}/{summ['hallucinated_j2']}) "
          f"disagree={summ['n_disagree']} n={len(rows)}", flush=True)
    return summ


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", choices=["a0", "a1", "a2"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--questions", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--minimal", action="store_true")
    ap.add_argument("--single-judge", action="store_true")
    a = ap.parse_args()
    if a.arm == "a2":
        RB.run(a.model, a.questions, a.out, fewshot_path=None, judge=None,
               limit=a.limit, synth=False, minimal=a.minimal)
    else:
        run_a0a1(a.arm, a.model, a.questions, a.out, a.limit, dual=not a.single_judge)
