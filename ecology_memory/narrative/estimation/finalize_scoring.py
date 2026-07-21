#!/usr/bin/env python3
"""Combine machine rubric drafts with an explicit evidence-audit override ledger."""

from __future__ import annotations

import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
MODELS = ("claude-4.6-opus-high", "gpt-5.4-medium", "cursor-grok-4.5-medium")
DIMS = ("estimand", "execution", "fit", "evidence_state", "decision_record")


def normalize_tags(review: dict) -> None:
    tags = set(review.get("tags", []))
    tags -= {"executed_estimate", "partial_execution", "recipe_only"}
    execution = review["scores"]["execution"]
    if execution == 2:
        tags.add("executed_estimate")
    elif execution == 1:
        tags.add("partial_execution")
    elif "no_final_answer" not in tags:
        tags.add("recipe_only")
    review["tags"] = sorted(tags)


def main() -> None:
    bank = json.loads((HERE / "bank.json").read_text())["questions"]
    ledger = json.loads((HERE / "audit_overrides.json").read_text())
    overrides = ledger["overrides"]
    manual = ledger["manual_reviews"]
    rows = []
    for model in MODELS:
        for question in bank:
            key = f"{model}/{question['id']}"
            if key in manual:
                review = dict(manual[key])
                provenance = "manual Codex evidence review"
            else:
                source = HERE / "judge-drafts" / model / f"{question['id']}.json"
                review = json.loads(source.read_text())["draft"]
                provenance = "DeepSeek V4 draft, Codex-audited"
            if key in overrides:
                change = overrides[key]
                review["scores"].update(change.get("scores", {}))
                review["rationales"].update(change.get("rationales", {}))
                review["audit_note"] = change["audit_note"]
            for dim in DIMS:
                assert review["scores"][dim] in (0, 1, 2), (key, dim)
            normalize_tags(review)
            rows.append({
                "key": key,
                "model": model,
                "question_id": question["id"],
                "family": question["family"],
                "question": question["q"],
                "provenance": provenance,
                "review": review,
            })
    assert len(rows) == 60
    out = {
        "rubric": {"dimensions": list(DIMS), "range": [0, 2]},
        "review_process": {
            "first_pass": "DeepSeek V4 rubric coding over hidden gold, answer, and compact retained tool trace",
            "final": ledger["policy"],
            "override_count": len(overrides),
            "manual_review_count": len(manual),
        },
        "rows": rows,
    }
    (HERE / "scoring.json").write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} audited rows")


if __name__ == "__main__":
    main()
