from __future__ import annotations

import sys
import unittest
from unittest import mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kit" / "harness"))

import executor  # noqa: E402
import connectors  # noqa: E402
import ir_schema  # noqa: E402
import parser  # noqa: E402
import scorer  # noqa: E402
import synthesize  # noqa: E402


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

    def test_reference_connectors_publish_filter_field_schemas(self):
        self.assertEqual(connectors.CONNECTOR_FIELD_SCHEMAS["osm-overpass"],
                         connectors.OSM_FIELDS)
        self.assertEqual(connectors.OSM_FIELDS["lat"], "number")
        self.assertEqual(connectors.OSM_FIELDS["name"], "string|null")
        self.assertEqual(connectors.CONNECTOR_FIELD_SCHEMAS["worldbank"],
                         connectors.WB_FIELDS)


class FilterDraftContractTests(unittest.TestCase):
    PROFILE = "v2.4.0-draft"

    @staticmethod
    def select():
        return {"op": "SELECT", "entity": "clinic",
                "region": {"op": "REGION", "place": "Erode town"}, "time": None}

    def filt(self, where, source=None):
        return {"op": "FILTER", "source": source or self.select(), "where": where}

    @staticmethod
    def records():
        return {"kind": "records", "label": "observed", "source": "fixture",
                "fields": {"id": "identifier", "name": "string|null",
                           "score": "number", "status": "category"},
                "rows": [
                    {"id": 1, "name": "Alpha Health", "score": 8, "status": "open"},
                    {"id": 2, "name": None, "score": 9, "status": "open"},
                    {"id": 3, "name": "Beta Clinic", "score": 4, "status": "closed"},
                ]}

    def test_released_profile_rejects_filter_and_draft_accepts_it(self):
        node = self.filt([{"field": "status", "cmp": "eq", "value": "open"}])
        self.assertFalse(ir_schema.validate(node)["valid"])
        self.assertTrue(ir_schema.validate(node, self.PROFILE)["valid"])

    def test_filter_executes_and_accounts_for_nulls_without_changing_label(self):
        out, audit = executor._filter(self.records(), [
            {"field": "name", "cmp": "contains", "value": "health"},
            {"field": "score", "cmp": "ge", "value": 5},
        ])
        self.assertEqual([row["id"] for row in out["rows"]], [1])
        self.assertEqual(audit, {"rows_in": 3, "rows_out": 1, "null_excluded": 1})
        self.assertEqual(out["label"], "observed")

    def test_empty_filter_result_is_a_true_answer(self):
        selected = self.records()
        ir = self.filt([{"field": "name", "cmp": "contains", "value": "no-match"}])
        region = {"name": "Erode", "bbox": [11.2, 11.4, 77.6, 77.8],
                  "lat": 11.3, "lon": 77.7, "orig": "Erode town"}
        with mock.patch.object(executor.C, "resolve_region", return_value=region), \
                mock.patch.object(executor, "_route_select", return_value=selected):
            result = executor.execute(ir, algebra_version=self.PROFILE)
        self.assertEqual(result["status"], "answer")
        self.assertEqual(result["value"]["rows"], [])
        event = next(item for item in result["provenance"] if item["op"] == "FILTER")
        self.assertEqual((event["rows_in"], event["rows_out"]), (3, 0))

    def test_scorer_is_profile_aware_and_accepts_filter_true_negative(self):
        ir = self.filt([{"field": "status", "cmp": "eq", "value": "missing"}])
        result = {"status": "answer", "value": {
            "kind": "records", "rows": [], "fields": self.records()["fields"]},
            "provenance": [
                {"op": "SELECT", "note": "3 rows"},
                {"op": "FILTER", "rows_in": 3, "rows_out": 0},
            ]}
        question = {"gold_shape": ["FILTER", "SELECT"], "expect": "answer"}
        released = scorer.score(question, ir, result)
        draft = scorer.score(question, ir, result, algebra_version=self.PROFILE)
        self.assertFalse(released["schema_valid"])
        self.assertTrue(draft["schema_valid"])
        self.assertTrue(draft["exec_grounded"])

    def test_unknown_field_and_bad_literal_type_fail_closed(self):
        with self.assertRaises(executor.DataRequest) as unknown:
            executor._filter(self.records(), [
                {"field": "ward", "cmp": "eq", "value": "north"}])
        self.assertEqual(unknown.exception.reason, "unknown_filter_field")
        self.assertEqual(unknown.exception.detail["declared_fields"],
                         ["id", "name", "score", "status"])
        with self.assertRaises(executor.DataRequest) as mismatch:
            executor._filter(self.records(), [
                {"field": "score", "cmp": "gt", "value": "five"}])
        self.assertEqual(mismatch.exception.reason, "filter_predicate_type")

    def test_filter_over_non_records_is_rejected_statically(self):
        bad = self.filt([{"field": "value", "cmp": "gt", "value": 3}], source={
            "op": "AGGREGATE", "by": "space", "metric": "count",
            "source": self.select()})
        report = ir_schema.validate(bad, self.PROFILE)
        self.assertFalse(report["valid"])
        self.assertTrue(any("must produce Records" in error for error in report["errors"]))

    def test_predicate_shape_and_holes_are_typed(self):
        for field, value in (("?field", "open"), ("status", "?status")):
            report = ir_schema.validate(self.filt([
                {"field": field, "cmp": "eq", "value": value}]), self.PROFILE)
            self.assertTrue(report["valid"])
            self.assertTrue(report["unbound"])
        subtree = self.filt([{"field": "score", "cmp": "gt",
                              "value": {"op": "REGION", "place": "x"}}])
        self.assertFalse(ir_schema.validate(subtree, self.PROFILE)["valid"])

    def test_nested_filters_canonicalize_to_sorted_conjunction(self):
        p = {"field": "status", "cmp": "eq", "value": "open"}
        q = {"field": "score", "cmp": "ge", "value": 5}
        nested = self.filt([q], self.filt([p]))
        flat = self.filt([p, q])
        self.assertEqual(ir_schema.canonicalize(nested, self.PROFILE),
                         ir_schema.canonicalize(flat, self.PROFILE))

    def test_parser_surface_is_bundled_with_buffer_under_fewshot_cap(self):
        messages = parser.build_messages(
            "Which clinics in Erode town have health in their name?",
            algebra_version=self.PROFILE)
        self.assertIn("FILTER", messages[0]["content"])
        self.assertIn("BUFFER", messages[0]["content"])
        examples = [message for message in messages if message["role"] == "assistant"]
        self.assertLessEqual(len(examples), 15)
        self.assertTrue(any('"FILTER"' in message["content"] for message in examples))


class BufferDraftContractTests(unittest.TestCase):
    PROFILE = "v2.4.0-draft"

    @staticmethod
    def region(place="Erode town"):
        return {"op": "REGION", "place": place}

    def buffer(self, radius=10, place="Erode town"):
        return {"op": "BUFFER", "radius_km": radius, "source": self.region(place)}

    def test_released_profile_rejects_buffer_and_draft_accepts_it(self):
        node = self.buffer()
        self.assertFalse(ir_schema.validate(node)["valid"])
        self.assertTrue(ir_schema.validate(node, self.PROFILE)["valid"])

    def test_radius_contract_including_typed_hole(self):
        for radius in (0, -1, float("inf"), float("nan"), True):
            with self.subTest(radius=radius):
                self.assertFalse(ir_schema.validate(self.buffer(radius), self.PROFILE)["valid"])
        report = ir_schema.validate(self.buffer("?radius_km"), self.PROFILE)
        self.assertTrue(report["valid"])
        self.assertTrue(report["unbound"])

    def test_buffer_requires_region_producer(self):
        bad = {"op": "BUFFER", "radius_km": 10, "source": {
            "op": "SELECT", "entity": "clinic", "region": self.region(), "time": None}}
        self.assertFalse(ir_schema.validate(bad, self.PROFILE)["valid"])

    def test_nested_identity_and_support_interning(self):
        nested = {"op": "BUFFER", "radius_km": 3,
                  "source": {"op": "BUFFER", "radius_km": 5,
                             "source": self.region("Surat")}}
        canonical = ir_schema.canonicalize(nested, self.PROFILE)
        self.assertEqual(canonical, self.buffer(8, "Surat"))
        relation = {"op": "RELATE", "relation": "within", "threshold_km": 2,
                    "left": {"op": "SELECT", "entity": "clinic",
                             "region": nested, "time": None},
                    "right": {"op": "SELECT", "entity": "school",
                              "region": nested, "time": None}}
        canonical = ir_schema.canonicalize(relation, self.PROFILE)
        self.assertIs(canonical["left"]["region"], canonical["right"]["region"])

    def test_intentionally_different_supports_are_not_copied(self):
        calls = []

        def fake_route(entity, region, time, provenance):
            calls.append((entity, region["buffer_km"]))
            return {"kind": "records", "rows": [{"lat": 11.0, "lon": 77.0}],
                    "entity": entity, "label": "observed", "source": "fixture"}

        relation = {"op": "RELATE", "relation": "within", "threshold_km": 2,
                    "left": {"op": "SELECT", "entity": "clinic",
                             "region": self.buffer(5), "time": None},
                    "right": {"op": "SELECT", "entity": "school",
                              "region": self.buffer(15), "time": None}}
        resolved = {"name": "Erode", "bbox": [11.2, 11.4, 77.6, 77.8],
                    "lat": 11.3, "lon": 77.7, "orig": "Erode town"}
        with mock.patch.object(executor.C, "resolve_region", return_value=resolved), \
                mock.patch.object(executor, "_route_select", side_effect=fake_route):
            out = executor.execute(relation, algebra_version=self.PROFILE)
        self.assertEqual(out["status"], "answer")
        self.assertEqual(calls, [("clinic", 5.0), ("school", 15.0)])
        relation_event = next(item for item in out["provenance"] if item["op"] == "RELATE")
        self.assertEqual(relation_event["threshold_km"], 2)

    def test_execution_preserves_unerasable_bbox_approx_provenance(self):
        resolved = {"name": "Erode", "bbox": [11.2, 11.4, 77.6, 77.8],
                    "lat": 11.3, "lon": 77.7, "orig": "Erode town"}
        selected = {"kind": "records", "rows": [{"lat": 11.3, "lon": 77.7}],
                    "entity": "clinic", "label": "observed", "source": "fixture"}
        ir = {"op": "SELECT", "entity": "clinic", "region": self.buffer(), "time": None}
        with mock.patch.object(executor.C, "resolve_region", return_value=resolved), \
                mock.patch.object(executor, "_route_select", return_value=selected):
            out = executor.execute(ir, algebra_version=self.PROFILE)
        event = next(item for item in out["provenance"] if item["op"] == "BUFFER")
        self.assertEqual(event["method"], "bbox-approx")
        self.assertTrue(event["approximate"])
        self.assertEqual(event["radius_km"], 10)
        self.assertEqual(event["source_support"]["orig"], "Erode town")
        self.assertEqual(len(event["result_bbox"]), 4)
        self.assertEqual(out["value"]["spatial_support"]["method"], "bbox-approx")

    def test_dateline_and_pole_cases_return_typed_request(self):
        edge = {"name": "edge", "bbox": [-0.1, 0.1, 179.5, 179.9],
                "lat": 0, "lon": 179.7, "orig": "edge"}
        ir = {"op": "SELECT", "entity": "school", "region": self.buffer(100, "edge"),
              "time": None}
        with mock.patch.object(executor.C, "resolve_region", return_value=edge):
            out = executor.execute(ir, algebra_version=self.PROFILE)
        self.assertEqual(out["status"], "data_request")
        self.assertEqual(out["reason"], "unsupported_region_geometry")
        self.assertEqual(out["detail"]["method"], "bbox-approx")
        polar = {"name": "polar", "bbox": [89.8, 89.9, 0, 1],
                 "lat": 89.85, "lon": 0.5, "orig": "polar"}
        with self.assertRaisesRegex(ValueError, "pole"):
            connectors.buffer_region(polar, 10)

    def test_estimate_target_accepts_buffer_support(self):
        ir = {"op": "ESTIMATE", "method": "envelope",
              "source": {"op": "SELECT", "entity": "clinic",
                         "region": self.region("Coimbatore"), "time": None},
              "target": self.buffer(10, "Tiruppur")}
        report = ir_schema.validate(ir, self.PROFILE)
        self.assertTrue(report["valid"])
        self.assertEqual(report["ops"].count("BUFFER"), 1)

    def test_parser_surface_is_profile_gated_and_below_fewshot_cap(self):
        released = parser.build_messages("Search 10 km around Erode for clinics.")
        draft = parser.build_messages("Search 10 km around Erode for clinics.",
                                      algebra_version=self.PROFILE)
        self.assertNotIn("BUFFER", released[0]["content"])
        self.assertNotIn("FILTER", released[0]["content"])
        self.assertIn("BUFFER", draft[0]["content"])
        assistant_examples = [m for m in draft if m["role"] == "assistant"]
        self.assertLessEqual(len(assistant_examples), 15)
        self.assertTrue(any('"BUFFER"' in m["content"] for m in assistant_examples))

    def test_buffer_time_owner_peephole_is_structural_not_semantic_routing(self):
        malformed = {"op": "SELECT", "entity": "clinic", "region": {
            "op": "BUFFER", "radius_km": 10, "source": self.region(), "time": None}}
        repaired = parser.mech_repair(malformed)
        self.assertEqual(repaired["time"], None)
        self.assertNotIn("time", repaired["region"])
        self.assertTrue(ir_schema.validate(repaired, self.PROFILE)["valid"])

    def test_synthesis_audit_requires_approximation_language(self):
        support = {"method": "bbox-approx", "approximate": True,
                   "name": "10 km approximate bbox around Erode"}
        result = {"status": "answer", "label": "observed", "value": {
            "kind": "records", "rows": [{"name": "clinic"}], "n_rows": 1,
            "spatial_support": support}, "provenance": [{
                "op": "BUFFER", "method": "bbox-approx", "approximate": True}]}
        bad = synthesize.score_synthesis("Where?", result, "One clinic was returned.")
        good = synthesize.score_synthesis(
            "Where?", result, "One clinic was returned from the approximate search bbox.")
        self.assertFalse(bad["approximation_surfaced"])
        self.assertTrue(good["approximation_surfaced"])

if __name__ == "__main__":
    unittest.main()
