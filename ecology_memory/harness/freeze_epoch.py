"""Create or verify the hard-saturation epoch manifest."""
import argparse
import datetime as dt
import hashlib
import json
import os


HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FROZEN = [
    "framework-lock.json", "algebra/README.md", "algebra/ir-spec.md",
    "harness/parser.py", "harness/questions/fewshot.json", "harness/connectors.py",
    "harness/executor.py", "harness/ir_schema.py", "harness/scorer.py",
    "harness/synthesize.py", "harness/run_bench.py",
    "questions/seed.json", "questions/active.json", "questions/expressiveness.json",
    "coverage/question_matrix.json", "coverage/source_matrix.json",
    "data/imported/lantana_occurrence.csv", "data/imported/restoration_sites.csv",
]


def digest(path):
    h = hashlib.sha256()
    with open(os.path.join(ROOT, path), "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "epochs", "epoch-001.json"))
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        manifest = json.load(open(a.out))
        missing = [path for path in manifest["sha256"] if not os.path.isfile(os.path.join(ROOT, path))]
        current = {path: digest(path) for path in manifest["sha256"] if path not in missing}
        changed = [path for path, value in current.items() if value != manifest["sha256"][path]]
        print(json.dumps({"epoch": manifest["epoch"], "verified": not changed and not missing,
                          "changed": changed, "missing": missing}, indent=2))
        raise SystemExit(1 if changed or missing else 0)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    manifest = {
        "epoch": os.path.splitext(os.path.basename(a.out))[0],
        "frozen_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "saturation_tier": "hard",
        "parser": "qwen3.5-2b at 172.17.0.1:8001",
        "active_wall": {"bank": "questions/active.json", "run": "runs/active-053",
                        "n": 270, "overall": 1.0, "synthesis_failures": 0},
        "expressiveness_bank": {"bank": "questions/expressiveness.json", "n": 50,
                                "eval_only": True},
        "holdout_rule": "three consecutive untouched post-freeze banks >=40; any solver change invalidates epoch",
        "sha256": {path: digest(path) for path in FROZEN},
    }
    with open(a.out, "w") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    print(f"froze {len(FROZEN)} artifacts -> {a.out}")


if __name__ == "__main__":
    main()
