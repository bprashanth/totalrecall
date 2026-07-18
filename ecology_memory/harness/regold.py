"""regold — re-author gold for questions of given types in a bank (after a spec change).

tick-008: RANK was added to the spec; gen-003's RANKING golds (authored pre-RANK) are wrong
(dropped cities / nested COMPAREs). Re-author with the updated shared parser prompt and
re-admit under the updated structural rules.

Usage: python3 regold.py questions/gen-003.json RANKING
"""
import json
import sys

from ir_schema import validate
from propose import author_gold, admit


def main(bank_path, *types):
    bank = json.load(open(bank_path))
    kept, dropped = [], 0
    for q in bank["questions"]:
        if types and q["type"] not in types:
            kept.append(q)
            continue
        gold = author_gold({"q": q["q"], "type": q["type"], "sector": q["sector"]})
        ok, why = admit({"q": q["q"], "type": q["type"], "sector": q["sector"]}, gold)
        print(f"{'OK' if ok else 'XX'} {q['id']}: {why}")
        if ok:
            rep = validate(gold)
            q["gold_ir"] = gold
            q["gold_shape"] = [o for o in rep["ops"] if o != "REGION"]
            kept.append(q)
        else:
            dropped += 1
    bank["questions"] = kept
    with open(bank_path, "w") as f:
        json.dump(bank, f, indent=1)
    print(f"regolded {bank_path}: kept {len(kept)}, dropped {dropped}")


if __name__ == "__main__":
    main(sys.argv[1], *sys.argv[2:])
