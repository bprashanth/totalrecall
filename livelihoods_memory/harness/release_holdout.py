#!/usr/bin/env python3
"""Release independently adjudicated holdout rows into disclosed development.

The immutable holdout is never edited.  Composite (bank,id) defects from the durable registry are
excluded mechanically so duplicate IDs in unrelated banks cannot remove valid evidence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bank", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    bank_path = ROOT / args.bank
    data = json.loads(bank_path.read_text())
    registry = json.loads((ROOT / "coverage/gold-defects.json").read_text())
    defects = {row["id"] for row in registry["rows"] if row["bank"] == args.bank}
    rows = [row for row in data["questions"] if row["id"] not in defects]
    if len(rows) + len(defects) != len(data["questions"]):
        missing = sorted(defects - {row["id"] for row in data["questions"]})
        raise SystemExit(f"registered defects absent from bank: {missing}")
    payload = {
        "spec_version": data.get("spec_version", "v2.1"),
        "note": (f"Disclosed development release from {args.bank}: {len(rows)} independently "
                 f"adjudicated valid rows; immutable defects "
                 f"{', '.join(sorted(defects)) if defects else 'none'} excluded"),
        "source_holdout": args.bank,
        "excluded_gold_defects": sorted(defects),
        "questions": rows,
    }
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"bank": args.bank, "released": len(rows),
                      "excluded": sorted(defects), "out": str(args.out)}, indent=2))


if __name__ == "__main__":
    main()
