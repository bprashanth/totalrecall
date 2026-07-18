from __future__ import annotations

import sys
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit" / "harness"))

import executor  # noqa: E402
import connectors  # noqa: E402


def series(value: float, year: int, entity: str, **metadata):
    return {
        "kind": "series",
        "rows": [{"t": str(year), "value": value}],
        "entity": entity,
        "label": "observed",
        **metadata,
    }


def scalar(value, measure="m", unit="count", grain="country", **metadata):
    return {"kind": "scalar", "value": value, "label": "observed",
            "measure": measure, "unit": unit, "grain": grain, **metadata}


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


class ArithmeticMetadataContractTests(unittest.TestCase):
    def test_compatible_difference_preserves_tags(self):
        out = executor._compare(scalar(12), scalar(7), "difference")
        self.assertEqual(out["value"], 5)
        self.assertEqual((out["measure"], out["unit"], out["grain"]),
                         ("m", "count", "country"))
        self.assertEqual(out["lineage"]["operation"], "difference")

    def test_difference_fails_closed_on_every_compatibility_dimension(self):
        cases = [
            scalar(7, measure="other"), scalar(7, unit="percent"),
            scalar(7, grain="district"),
        ]
        for right in cases:
            with self.subTest(right=right), self.assertRaises(executor.DataRequest) as raised:
                executor._compare(scalar(12), right, "difference")
            self.assertEqual(raised.exception.reason, "incompatible_arithmetic")

    def test_ratio_forms_unit_and_full_lineage(self):
        left = scalar(10, measure="visits", unit="visit", lineage=[{"source": "a"}])
        right = scalar(2, measure="population", unit="person", lineage=[{"source": "b"}])
        out = executor._compare(left, right, "ratio")
        self.assertEqual(out["value"], 5)
        self.assertEqual(out["unit"], "visit/person")
        self.assertEqual(out["measure"], "ratio:visits/population")
        self.assertEqual(out["lineage"]["left"]["lineage"], [{"source": "a"}])
        self.assertEqual(out["lineage"]["right"]["lineage"], [{"source": "b"}])

    def test_ratio_zero_denominator_fails_closed(self):
        with self.assertRaises(executor.DataRequest) as raised:
            executor._compare(scalar(10), scalar(0), "ratio")
        self.assertEqual(raised.exception.reason, "zero_denominator")

    def test_ratio_grain_mismatch_needs_declared_proxy(self):
        with self.assertRaises(executor.DataRequest):
            executor._compare(scalar(10, grain="district"),
                              scalar(2, grain="country"), "ratio")
        right = scalar(2, grain="country",
                       grain_proxy={"declared": True, "reason": "national denominator"})
        out = executor._compare(scalar(10, grain="district"), right, "ratio")
        self.assertEqual(out["label"], "proxy")
        self.assertIn("declared grain proxy", out["note"])

    def test_rank_rejects_heterogeneous_measures(self):
        region = {"op": "REGION", "place": "x"}
        rank = {"op": "RANK", "order": "desc", "items": [
            {"op": "SELECT", "entity": "a", "region": region, "time": None},
            {"op": "SELECT", "entity": "b", "region": region, "time": None},
        ]}
        routed = [
            {"kind": "series", "rows": [{"t": "2020", "value": 1}], "entity": "a",
             "label": "observed", "measure": "a", "unit": "count", "grain": "country"},
            {"kind": "series", "rows": [{"t": "2020", "value": 2}], "entity": "b",
             "label": "observed", "measure": "b", "unit": "count", "grain": "country"},
        ]
        with mock.patch.object(executor.C, "resolve_region", return_value={"name": "x"}), \
             mock.patch.object(executor, "_route_select", side_effect=routed), \
             self.assertRaises(executor.DataRequest) as raised:
            executor._ev(rank, [], {})
        self.assertEqual(raised.exception.reason, "rank_incompatible")


class TemporalAlignmentContractTests(unittest.TestCase):
    def value(self, rows, **metadata):
        return {"kind": "series", "rows": rows, "entity": "same", "label": "observed",
                "measure": "worldbank:test", "unit": "count", "grain": "country",
                "frequency": "annual", **metadata}

    def test_partial_overlap_uses_only_exact_periods_and_certifies_drops(self):
        left = self.value([{"t": "2019", "value": 1}, {"t": "2020", "value": 2},
                           {"t": "2021", "value": 3}])
        right = self.value([{"t": "2020", "value": 10}, {"t": "2021", "value": 20},
                            {"t": "2022", "value": 30}])
        out = executor._compare(left, right, "difference")
        self.assertEqual(out["alignment"]["used_periods"], ["2020", "2021"])
        self.assertEqual(out["alignment"]["dropped_left"], ["2019"])
        self.assertEqual(out["alignment"]["dropped_right"], ["2022"])
        self.assertTrue(set(out["alignment"]["used_periods"]) <= {"2019", "2020", "2021"})
        self.assertIn("exact common coverage 2020–2021", out["note"])

    def test_full_overlap_has_no_drop_certificate(self):
        rows = [{"t": "2020", "value": 1}, {"t": "2021", "value": 2}]
        out = executor._compare(self.value(rows), self.value(rows), "difference")
        self.assertNotIn("alignment", out)

    def test_zero_overlap_names_both_windows(self):
        left = self.value([{"t": "2018", "value": 1}, {"t": "2019", "value": 2}])
        right = self.value([{"t": "2020", "value": 3}, {"t": "2021", "value": 4}])
        with self.assertRaises(executor.DataRequest) as raised:
            executor._compare(left, right, "difference")
        self.assertEqual(raised.exception.reason, "temporal_no_overlap")
        self.assertEqual(raised.exception.detail["left_window"], ["2018", "2019"])
        self.assertEqual(raised.exception.detail["right_window"], ["2020", "2021"])

    def test_duplicate_periods_fail_closed(self):
        left = self.value([{"t": "2020", "value": 1}, {"t": "2020", "value": 2}])
        right = self.value([{"t": "2020", "value": 3}, {"t": "2021", "value": 4}])
        with self.assertRaises(executor.DataRequest) as raised:
            executor._compare(left, right, "difference")
        self.assertEqual(raised.exception.reason, "duplicate_periods")

    def test_declared_monthly_flow_can_coarsen_to_annual(self):
        monthly = self.value(
            [{"t": f"2020-{month:02d}", "value": 1} for month in range(1, 13)],
            frequency="monthly", temporal_semantics="flow", coarsen="sum")
        annual = self.value([{"t": "2020", "value": 10}], frequency="annual")
        out = executor._compare(monthly, annual, "difference")
        self.assertEqual(out["value"], 2)
        self.assertEqual(out["alignment"]["coarsened"],
                         {"side": "left", "from": "monthly", "to": "annual", "method": "sum"})

    def test_mixed_frequency_without_declared_semantics_fails(self):
        monthly = self.value([{"t": "2020-01", "value": 1},
                              {"t": "2020-02", "value": 2}], frequency="monthly")
        annual = self.value([{"t": "2020", "value": 3}], frequency="annual")
        with self.assertRaises(executor.DataRequest) as raised:
            executor._compare(monthly, annual, "difference")
        self.assertEqual(raised.exception.reason, "temporal_frequency_mismatch")

    def test_scalar_window_exemption_keeps_pre_post_change(self):
        out = executor._compare(
            series(10, 2010, "same", measure="m", unit="count", grain="country"),
            series(30, 2020, "same", measure="m", unit="count", grain="country"),
            "difference")
        self.assertEqual(out["value"], 20)
        self.assertNotIn("alignment", out)

    def test_differing_vintages_are_surfaced(self):
        left = self.value([{"t": "2020", "value": 3}], vintage="2025-01-01")
        right = self.value([{"t": "2020", "value": 2}], vintage="2026-01-01")
        out = executor._compare(left, right, "difference")
        self.assertIn("source vintages differ", out["note"])
        self.assertEqual(out["vintage"]["right"], "2026-01-01")


class ConnectorMetadataTests(unittest.TestCase):
    def test_world_bank_leaf_declares_v23_metadata(self):
        payload = [{"lastupdated": "2026-07-01"}, [
            {"date": "2020", "value": 100}, {"date": "2019", "value": 90}]]
        with mock.patch.object(connectors, "_get", return_value=payload), \
             mock.patch.object(connectors, "wb_resolve_iso", return_value="IND"):
            out = connectors.wb_series("population", {"orig": "India"})
        self.assertEqual(out["measure"], "worldbank:SP.POP.TOTL")
        self.assertEqual(out["unit"], "person")
        self.assertEqual(out["grain"], "country")
        self.assertEqual(out["frequency"], "annual")
        self.assertEqual(out["vintage"], "2026-07-01")
        self.assertEqual(out["fields"]["value"], "number")

if __name__ == "__main__":
    unittest.main()
