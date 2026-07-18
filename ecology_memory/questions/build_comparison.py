"""Build a small, fixed representative arm-comparison bank from the audited seed."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
IDS = ["eco-s001", "eco-s003", "eco-s005", "eco-s007", "eco-s009", "eco-s012",
       "eco-s015", "eco-s016", "eco-s018", "eco-s020", "eco-s023", "eco-s025"]

seed = json.load(open(os.path.join(HERE, "seed.json")))
by_id = {q["id"]: q for q in seed["questions"]}
out = {"bank": "ecology-comparison-v1", "provenance": "fixed audited subset of seed.json",
       "questions": [by_id[i] for i in IDS]}
with open(os.path.join(HERE, "comparison.json"), "w") as f:
    json.dump(out, f, indent=2)
    f.write("\n")
print(f"comparison.json: {len(IDS)} questions")
