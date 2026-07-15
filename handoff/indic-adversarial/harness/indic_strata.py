"""Per-stratum scores for an Indic-eval run: by transform, style, lang, and source family."""
import json
import os
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
BANK = json.load(open(os.path.join(HERE, "questions", "indic-eval-001.json")))
META = {q["id"]: q.get("meta", {}) for q in BANK["questions"]}


def strata(run_dir):
    rows = [json.loads(l) for l in open(os.path.join(run_dir, "traces.jsonl"))]
    cells = defaultdict(list)
    for r in rows:
        m = META.get(r["id"], {})
        ov = r["scores"]["overall"]
        cells[("transform", m.get("transform") or "?")].append(ov)
        cells[("style", m.get("style") or "native")].append(ov)
        if m.get("lang"):
            cells[("lang", m["lang"])].append(ov)
        src = (m.get("source") or (m.get("source_id") or "?").split(":")[0])
        cells[("source", src)].append(ov)
        cells[("mtvsnative", "mt" if m.get("transform") == "mt" else "native")].append(ov)
    out = {}
    for (dim, key), vals in sorted(cells.items()):
        out.setdefault(dim, {})[key] = (round(sum(vals) / len(vals), 3), len(vals))
    return out


if __name__ == "__main__":
    for rd in sys.argv[1:]:
        print(f"\n== {os.path.basename(rd)}")
        s = strata(rd)
        for dim in ("transform", "style", "mtvsnative", "lang", "source"):
            if dim in s:
                print(f"  {dim:11}: " + "  ".join(f"{k}={v[0]}(n={v[1]})"
                                                  for k, v in s[dim].items()))
