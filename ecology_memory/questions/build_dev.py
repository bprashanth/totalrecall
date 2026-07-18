#!/usr/bin/env python3
"""Build the active dialect wall from execution-admitted seed golds.

Transforms are deliberately semantics-neutral wrappers. They pressure discourse register and
instruction noise without changing the ecological quantity, negation, place, time or record-vs-
organism distinction. Gold IR is inherited byte-for-byte from the audited base row.
"""
import copy
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def lower_first(text):
    return text[:1].lower() + text[1:] if text else text


TRANSFORMS = [
    ("ordinary", lambda q: "Please answer this ecology data question: " + q),
    ("indirect", lambda q: "What I need to establish from the data is this: " + lower_first(q)),
    ("colloquial", lambda q: "Can you check this for me — " + lower_first(q)),
    ("terse", lambda q: "Ecology check: " + q.rstrip("?")),
    ("adversarial", lambda q: "Use exactly the named entity, measure, place and time; do not silently substitute them. " + q),
    ("indian_english", lambda q: "Please check once and tell me clearly: " + lower_first(q)),
    ("light_codeswitch", lambda q: "Zara data se check karke batao: " + lower_first(q)),
    ("noisy_long", lambda q: "For a field note I am preparing, without filling any gaps from general knowledge or changing the requested evidence, " + lower_first(q)),
]


def main():
    seed_path = os.path.join(HERE, "seed.json")
    with open(seed_path) as f:
        seed = json.load(f)
    questions = [copy.deepcopy(x) for x in seed["questions"]]
    n = 0
    for base in seed["questions"]:
        for register, transform in TRANSFORMS:
            n += 1
            row = copy.deepcopy(base)
            row["id"] = f"eco-d{n:03d}"
            row["q"] = transform(base["q"])
            row["derived_from"] = base["id"]
            row["register"] = register
            questions.append(row)
    assert len(questions) == 270
    assert len({q["q"] for q in questions}) == 270
    out = {"bank": "ecology-active-v1", "generation": "deterministic semantic-preserving dialect wrappers",
           "questions": questions}
    with open(os.path.join(HERE, "active.json"), "w") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    types, registers = {}, {"seed": len(seed["questions"])}
    shapes, outcomes = {}, {}
    for q in questions:
        types[q["type"]] = types.get(q["type"], 0) + 1
        if q.get("register"):
            registers[q["register"]] = registers.get(q["register"], 0) + 1
        key = "+".join(sorted(x for x in q.get("gold_shape", []) if x not in {"REGION", "AGGREGATE"}))
        shapes[key] = shapes.get(key, 0) + 1
        outcomes[q["expect"]] = outcomes.get(q["expect"], 0) + 1
    matrix = {"bank": "questions/active.json", "n": len(questions), "types": types,
              "registers": registers, "normalized_shapes": shapes, "outcomes": outcomes,
              "source_capabilities": {
                  "taxon_occurrence": 108, "ebird_recent_or_gap": 18,
                  "ndvi_series": 72, "published_sites": 72,
                  "earth_engine_annotation": 45,
              }}
    coverage = os.path.abspath(os.path.join(HERE, "..", "coverage"))
    os.makedirs(coverage, exist_ok=True)
    with open(os.path.join(coverage, "question_matrix.json"), "w") as f:
        json.dump(matrix, f, indent=2)


if __name__ == "__main__":
    main()
