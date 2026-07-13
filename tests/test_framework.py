from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit" / "harness"))

import executor  # noqa: E402


def series(value: float, year: int, entity: str):
    return {
        "kind": "series",
        "rows": [{"t": str(year), "value": value}],
        "entity": entity,
        "label": "observed",
    }


class CompareOrientationTests(unittest.TestCase):
    def test_same_entity_orients_later_minus_earlier(self):
        out = executor._compare(
            series(10, 2010, "unemployment rate"),
            series(30, 2020, "unemployment rate"),
            "difference",
        )
        self.assertEqual(out["value"], 20)
        self.assertIn("oriented later-minus-earlier", out["note"])

    def test_cross_entity_ratio_preserves_written_order(self):
        out = executor._compare(
            series(10, 2010, "air passengers"),
            series(2, 2020, "population"),
            "ratio",
        )
        self.assertEqual(out["value"], 5)
        self.assertNotIn("oriented", out["note"])

    def test_equal_year_preserves_written_order(self):
        out = executor._compare(
            series(12, 2020, "unemployment rate"),
            series(7, 2020, "unemployment rate"),
            "difference",
        )
        self.assertEqual(out["value"], 5)
        self.assertNotIn("oriented", out["note"])


if __name__ == "__main__":
    unittest.main()
