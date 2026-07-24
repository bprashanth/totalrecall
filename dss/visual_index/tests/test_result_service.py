import hashlib
import json
import os
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

try:
    import jsonschema
except ImportError:  # The producer itself remains standard-library only.
    jsonschema = None

from dss.visual_index.build import Builder
from dss.visual_index.result_service import ResultService, make_server


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai"
IDLISSEUS_SCHEMA = pathlib.Path(
    os.environ.get(
        "IDLI_RESULT_SCHEMA",
        str(ROOT.parent / "idlisseus" / "dss" / "contracts" / "idli-result.schema.json"),
    )
)


class ValparaiResultServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.temp.name)
        cls.index_root = cls.root / "index"
        cls.state_root = cls.root / "state"
        Builder(PACK, cls.index_root).run()
        cls.service = ResultService(
            PACK, cls.index_root / "site_index.sqlite", cls.state_root
        )
        cls.schema = (
            json.loads(IDLISSEUS_SCHEMA.read_text(encoding="utf-8"))
            if jsonschema is not None and IDLISSEUS_SCHEMA.is_file() else None
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_contract(self, result):
        self.assertEqual(result["schema_version"], "idli-result/1")
        if self.schema:
            jsonschema.Draft202012Validator(self.schema).validate(result)

    def test_real_site_orientation_is_visual_first(self):
        result = self.service.query(
            "orientation-1", "site-orientation", {}, "Tell me about Valparai."
        )
        self.assert_contract(result)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["visuals"][0]["visual_type"], "map")
        self.assertEqual(
            result["visuals"][0]["summary"]["denominators"]["records"], 42_348
        )
        self.assertEqual(len(result["audit"]["source_versions"]), 21)
        for layer in result["visuals"][0]["layers"]:
            resolved = self.service.load_data(result["result_id"], layer["data_ref"]["handle"])
            self.assertIsNotNone(resolved)

    def test_real_entity_query_returns_source_linked_valparai_points(self):
        result = self.service.query(
            "presence-1",
            "entity-record-map",
            {"entity": "lion-tailed macaque"},
            "Where have lion-tailed macaques been recorded?",
        )
        self.assert_contract(result)
        self.assertGreater(
            result["visuals"][0]["summary"]["denominators"]["records"], 10
        )
        self.assertIn("observed", result["answer"]["evidence_classes"])
        rows = self.service.load_data(result["result_id"], "source-rows")
        self.assertIsNotNone(rows)
        decoded = json.loads(rows[1])
        self.assertTrue(all(row["source_id"] and row["source_row"] for row in decoded))

    def test_empty_target_keeps_surrounding_data_and_offers_transfer(self):
        result = self.service.query(
            "surrounding-1",
            "entity-record-map",
            {"entity": "Axis axis"},
            "Is Axis axis present here?",
        )
        self.assert_contract(result)
        counts = result["visuals"][0]["summary"]["denominators"]
        self.assertEqual(counts["target_records"], 0)
        self.assertGreater(counts["context_records"], 0)
        self.assertEqual(result["visuals"][0]["view"], "surrounding-data")
        self.assertIn(
            "test-transfer", {action["action_id"] for action in result["actions"]}
        )
        self.assertIn(
            "no-target-records",
            {item["code"] for item in result["limitations"]},
        )

    def test_real_metric_series_has_units_and_coverage(self):
        result = self.service.query(
            "rainfall-1",
            "metric-time-series",
            {"metric": "rainfall"},
            "How has rainfall changed over the available period?",
        )
        self.assert_contract(result)
        visual = result["visuals"][0]
        self.assertEqual(visual["visual_type"], "chart")
        self.assertGreater(visual["summary"]["denominators"]["months"], 100)
        self.assertTrue(visual["summary"]["denominators"]["units"])
        self.assertIsNotNone(
            self.service.load_data(result["result_id"], "coverage-strip")
        )

    def test_real_hierarchy_group_query_maps_members_without_flattening_them(self):
        result = self.service.query(
            "amphibian-group-1",
            "group-record-map",
            {"rank": "class", "group": "Amphibia"},
            "Show me where amphibians have been recorded. I want the species separately.",
        )
        self.assert_contract(result)
        visual = result["visuals"][0]
        self.assertEqual(visual["view"], "group-observed-points")
        counts = visual["summary"]["denominators"]
        self.assertGreater(counts["records"], 1)
        self.assertGreater(counts["entities"], 1)
        members = json.loads(
            self.service.load_data(result["result_id"], "group-entities")[1]
        )
        self.assertTrue(all(item["canonical_name"] for item in members))
        self.assertIn(
            "mixed-observation-processes",
            {item["code"] for item in result["limitations"]},
        )

    def test_seasonal_surface_profile_maps_peak_and_keeps_coverage(self):
        result = self.service.query(
            "seasonal-greenness-1",
            "seasonal-surface-profile",
            {
                "series_id": "sentinel2-ndvi-monthly",
                "year": 2024,
                "scope": "context",
            },
            "How does greenness change through the year?",
        )
        self.assert_contract(result)
        self.assertEqual(
            [item["visual_type"] for item in result["visuals"]], ["map", "chart"]
        )
        denominators = result["visuals"][0]["summary"]["denominators"]
        self.assertEqual(denominators["declared_steps"], 12)
        self.assertGreaterEqual(denominators["available_steps"], 10)
        profile = json.loads(
            self.service.load_data(
                result["result_id"], "seasonal-surface-profile"
            )[1]
        )
        self.assertGreaterEqual(len(profile), 10)
        self.assertTrue(
            all(
                {"position", "median", "p10", "p90", "cells_with_values"}
                <= set(row)
                for row in profile
            )
        )
        peaks = json.loads(
            self.service.load_data(result["result_id"], "seasonal-peak-cells")[1]
        )
        self.assertGreater(len(peaks["features"]), 100)
        self.assertIn(
            "seasonal-profile-not-trend",
            {item["code"] for item in result["limitations"]},
        )

    def test_real_interaction_query_returns_linked_map_and_network(self):
        result = self.service.query(
            "interaction-1",
            "interaction-map",
            {
                "interaction_type": "observed_visiting_focal_tree",
                "entity": "Canarium strictum",
            },
            "Which animals were observed visiting Canarium strictum fruiting trees, and where?",
        )
        self.assert_contract(result)
        self.assertEqual([item["visual_type"] for item in result["visuals"]], ["map", "network"])
        self.assertGreater(
            result["visuals"][0]["summary"]["denominators"]["records"], 20
        )
        edges = json.loads(
            self.service.load_data(result["result_id"], "interaction-edges")[1]
        )
        self.assertGreaterEqual(len(edges), 4)
        self.assertIn(
            "association-not-causation",
            {item["code"] for item in result["limitations"]},
        )

    def test_real_stratified_survey_keeps_effort_and_replication_visible(self):
        result = self.service.query(
            "restoration-summary-1",
            "stratified-survey-summary",
            {
                "source_id": "dryad-rjdfn2zc3-restoration-birds",
                "category_property": "Site_type",
            },
            "How do bird detections compare across restored, naturally growing and benchmark plots?",
        )
        self.assert_contract(result)
        self.assertEqual(
            [item["visual_type"] for item in result["visuals"]], ["map", "table"]
        )
        denominators = result["visuals"][0]["summary"]["denominators"]
        self.assertEqual(denominators["sites"], 69)
        self.assertEqual(denominators["categories"], 3)
        self.assertEqual(denominators["visits"], 460)
        summary = json.loads(
            self.service.load_data(
                result["result_id"], "stratified-category-summary"
            )[1]
        )
        self.assertEqual(
            {item["category"] for item in summary},
            {"Benchmark", "Restored", "Unrestored"},
        )
        self.assertTrue(all(item["sites"] and item["visits"] for item in summary))
        points = json.loads(
            self.service.load_data(
                result["result_id"], "stratified-survey-sites"
            )[1]
        )
        self.assertTrue(
            all(
                " · " in feature["properties"]["label"]
                and feature["properties"]["category"]
                for feature in points["features"]
            )
        )
        self.assertIn(
            "descriptive-not-causal",
            {item["code"] for item in result["limitations"]},
        )

    def test_real_cell_feature_map_retains_lineage_and_semantics(self):
        result = self.service.query(
            "tree-score-1",
            "cell-feature-map",
            {
                "feature_id": "dw_trees_probability",
                "year": 2024,
                "scope": "context",
            },
            "Show me where the 2024 tree-cover score is high or low.",
        )
        self.assert_contract(result)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(
            [item["visual_type"] for item in result["visuals"]], ["map", "table"]
        )
        self.assertEqual(
            result["visuals"][0]["layers"][0]["evidence_class"], "modelled"
        )
        self.assertEqual(
            result["visuals"][0]["layers"][1]["geometry_type"], "line"
        )
        self.assertEqual(
            result["visuals"][0]["summary"]["denominators"]["cells_with_values"], 255
        )
        self.assertIn("Dynamic World trees class score", result["answer"]["headline"])
        self.assertIn(
            "class-score-not-cover",
            {item["code"] for item in result["limitations"]},
        )
        cells = json.loads(
            self.service.load_data(result["result_id"], "cell-feature-values")[1]
        )
        self.assertEqual(len(cells["features"]), 255)
        self.assertTrue(all(
            0 <= feature["properties"]["value"] <= 1
            for feature in cells["features"]
        ))
        self.assertTrue(all(
            feature["properties"]["source_asset"] == "GOOGLE/DYNAMICWORLD/V1"
            for feature in cells["features"]
        ))

    def test_stratified_survey_can_filter_compatible_protocols(self):
        result = self.service.query(
            "adult-tree-comparison-1",
            "stratified-survey-summary",
            {
                "source_id": "dryad-8kprr4xvb-restoration-opportunities",
                "category_property": "Treatment",
                "event_type": "adult_tree_inventory",
                "effort_method": "adult_tree_inventory_plot",
            },
            "Compare adult-tree records between fragments and benchmark forests.",
        )
        self.assert_contract(result)
        denominators = result["visuals"][0]["summary"]["denominators"]
        self.assertEqual(denominators["sites"], 132)
        self.assertEqual(denominators["categories"], 2)
        self.assertEqual(denominators["visits"], 132)
        summary = json.loads(
            self.service.load_data(
                result["result_id"], "stratified-category-summary"
            )[1]
        )
        self.assertEqual(
            {item["category"] for item in summary},
            {"Benchmark", "Fragment"},
        )
        self.assertEqual(sum(item["event_records"] for item in summary), 2195)

    def test_plot_indicator_profile_maps_values_and_category_distributions(self):
        result = self.service.query(
            "plot-carbon-1",
            "plot-indicator-profile",
            {
                "metric": "adult_aboveground_carbon_per_ha",
                "source_id": "derived-restoration-plot-indicators-v1",
                "category_property": "comparison_class",
            },
            "Show adult-tree carbon across the plots and compare fragments with benchmark forests.",
        )
        self.assert_contract(result)
        self.assertEqual(
            [item["visual_type"] for item in result["visuals"]], ["map", "table"]
        )
        denominators = result["visuals"][0]["summary"]["denominators"]
        self.assertEqual(denominators["plots"], 132)
        self.assertEqual(denominators["categories"], 2)
        self.assertEqual(denominators["unit"], "Mg/ha")
        points = json.loads(
            self.service.load_data(result["result_id"], "plot-indicator-points")[1]
        )
        self.assertEqual(len(points["features"]), 132)
        self.assertTrue(all(
            feature["properties"]["method_id"]
            == "plot-area-normalised-adult-tree-stocks"
            for feature in points["features"]
        ))
        summary = json.loads(
            self.service.load_data(
                result["result_id"], "plot-indicator-category-summary"
            )[1]
        )
        self.assertEqual(
            {item["category"] for item in summary}, {"Benchmark", "Fragment"}
        )
        self.assertTrue(all(item["plots"] and item["q25"] <= item["q75"] for item in summary))
        self.assertIn(
            "descriptive-not-causal",
            {item["code"] for item in result["limitations"]},
        )

    def test_acoustic_matrix_profile_keeps_frequency_time_and_sites_visible(self):
        result = self.service.query(
            "acoustic-matrix-1",
            "matrix-profile",
            {
                "source_id": "github-acoustics-restoration-v1",
                "matrix_id": "acoustic_space_use_by_hour_frequency",
                "category_property": "comparison_class",
            },
            "How does the soundscape change through the day across the three site types?",
        )
        self.assert_contract(result)
        self.assertEqual(
            [item["visual_type"] for item in result["visuals"]], ["matrix", "map"]
        )
        denominators = result["visuals"][0]["summary"]["denominators"]
        self.assertEqual(denominators["series"], 43)
        self.assertEqual(denominators["categories"], 3)
        self.assertEqual(denominators["x_bins"], 24)
        self.assertEqual(denominators["y_bins"], 128)
        self.assertEqual(denominators["source_rows"], 132_096)
        matrix = json.loads(
            self.service.load_data(result["result_id"], "grouped-matrix-values")[1]
        )
        self.assertEqual(len(matrix), 3 * 24 * 128)
        self.assertTrue(all(0 <= item["value"] <= 1 for item in matrix))
        points = json.loads(
            self.service.load_data(result["result_id"], "matrix-series-sites")[1]
        )
        self.assertEqual(len(points["features"]), 43)
        self.assertIn(
            "soundscape-not-species-abundance",
            {item["code"] for item in result["limitations"]},
        )

    def test_method_catalog_exposes_occupancy_inputs_gates_and_claim_limits(self):
        result = self.service.query(
            "occupancy-method-1",
            "method-catalog",
            {"method_id": "detection-aware-single-season-occupancy"},
            "How can we model bird presence when survey effort is uneven?",
        )
        self.assert_contract(result)
        self.assertEqual(result["visuals"][0]["visual_type"], "table")
        self.assertEqual(
            result["visuals"][0]["summary"]["denominators"]["methods"], 1
        )
        details = json.loads(
            self.service.load_data(result["result_id"], "method-card-details")[1]
        )
        self.assertEqual(
            details[0]["method_id"], "detection-aware-single-season-occupancy"
        )
        self.assertIn("repeat_visit_id", details[0]["required_inputs"])
        self.assertGreaterEqual(len(details[0]["gates"]), 6)
        self.assertIn("confirmed local presence", details[0]["forbidden_claim"])
        self.assertIn(
            "method-card-not-model-run",
            {item["code"] for item in result["limitations"]},
        )

    def test_method_catalog_exposes_effort_adjusted_trend_claim_limits(self):
        result = self.service.query(
            "bird-trend-method-1",
            "method-catalog",
            {"method_id": "effort-adjusted-reporting-rate-trend"},
            "Can these bird records tell us whether a species is declining?",
        )
        self.assert_contract(result)
        details = json.loads(
            self.service.load_data(result["result_id"], "method-card-details")[1]
        )
        self.assertEqual(len(details), 1)
        self.assertIn("complete_checklist_detection_history", details[0]["required_inputs"])
        self.assertIn("population abundance", details[0]["forbidden_claim"])
        self.assertTrue(
            any("spatial coverage" in gate for gate in details[0]["gates"])
        )

    def test_feature_with_no_finite_support_is_blocked_not_zero_filled(self):
        result = self.service.query(
            "cloudy-july-1",
            "cell-feature-map",
            {"feature_id": "s2_ndvi_m07_median", "year": 2024},
            "Show me the July NDVI.",
        )
        self.assert_contract(result)
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["visuals"])
        self.assertIn(
            "feature-not-indexed",
            {item["code"] for item in result["limitations"]},
        )

    def test_gated_transfer_separates_observations_analogues_and_failed_gate(self):
        result = self.service.query(
            "transfer-1",
            "gated-transfer",
            {
                "entity": "Macaca silenus",
                "donor_scope": "context",
                "target_scope": "target",
            },
            "Can the surrounding data be transferred?",
        )
        self.assert_contract(result)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["visuals"][0]["view"], "donor-target-gates")
        self.assertEqual(
            [layer["evidence_class"] for layer in result["visuals"][0]["layers"]],
            ["modelled", "missing", "observed", "reported"],
        )
        denominators = result["visuals"][0]["summary"]["denominators"]
        self.assertGreaterEqual(denominators["donor_records"], 20)
        self.assertGreaterEqual(denominators["donor_cells"], 10)
        self.assertEqual(denominators["embedding_axes"], 64)
        gates = json.loads(
            self.service.load_data(result["result_id"], "transfer-gates")[1]
        )
        self.assertEqual(
            next(
                gate["status"] for gate in gates
                if gate["gate_id"] == "predictive-discrimination"
            ),
            "not_evaluated",
        )
        self.assertIn(
            "analogue-not-occurrence-probability",
            {item["code"] for item in result["limitations"]},
        )

    def test_result_and_payloads_are_immutable(self):
        first = self.service.query(
            "immutable-1", "site-orientation", {}, "Tell me about the site."
        )
        second = self.service.query(
            "immutable-1", "site-orientation", {}, "Tell me about the site."
        )
        self.assertEqual(first, second)
        stored = self.service.load_result(first["result_id"])
        self.assertEqual(stored, first)

    def test_internal_http_surface_requires_token_and_serves_handles(self):
        server = make_server(self.service, "127.0.0.1", 0, "test-token")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(f"{base}/v1/results/unknown", timeout=2)
            self.assertEqual(denied.exception.code, 401)

            body = json.dumps({
                "request_id": "http-orientation-1",
                "capability_id": "site-orientation",
                "arguments": {},
                "question": "Tell me about Valparai.",
            }).encode()
            request = urllib.request.Request(
                f"{base}/v1/results/query",
                data=body,
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
            )
            result = json.loads(urllib.request.urlopen(request, timeout=3).read())
            self.assert_contract(result)
            handle = result["visuals"][0]["layers"][0]["data_ref"]["handle"]
            data_request = urllib.request.Request(
                f"{base}/v1/results/{result['result_id']}/data/{handle}",
                headers={"Authorization": "Bearer test-token"},
            )
            response = urllib.request.urlopen(data_request, timeout=3)
            self.assertEqual(response.headers.get_content_type(), "application/geo+json")
            payload = response.read()
            self.assertEqual(json.loads(payload)["type"], "FeatureCollection")
            expected = result["visuals"][0]["layers"][0]["data_ref"]["digest"]
            self.assertEqual("sha256:" + hashlib.sha256(payload).hexdigest(), expected)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_result_handles_cannot_escape_pinned_state(self):
        self.assertIsNone(self.service.load_result("../site"))
        self.assertIsNone(self.service.load_data("anything", "../site.json"))


class PackSwapContractTest(unittest.TestCase):
    """The synthetic and real Valparai packs must use one producer/UI contract."""

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.temp.name)
        cls.packs = {
            "real": ROOT / "dss" / "sites" / "valparai",
            "synthetic": ROOT / "dss" / "sites" / "valparai_livelihoods",
        }
        cls.services = {}
        for name, pack in cls.packs.items():
            index = cls.root / name / "index"
            state = cls.root / name / "state"
            Builder(pack, index).run()
            cls.services[name] = ResultService(
                pack, index / "site_index.sqlite", state
            )
        cls.schema = (
            json.loads(IDLISSEUS_SCHEMA.read_text(encoding="utf-8"))
            if jsonschema is not None and IDLISSEUS_SCHEMA.is_file() else None
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    @staticmethod
    def capability_interface(item):
        return {
            key: item.get(key) for key in (
                "version", "input_schema", "output_views", "required_planes",
                "optional_planes", "latency_class", "evidence_classes", "availability",
            )
        }

    @staticmethod
    def visual_grammar(result):
        if not result["visuals"]:
            return None
        visual = result["visuals"][0]
        return {
            "visual_type": visual["visual_type"],
            "view": visual["view"],
            "layers": [{
                key: layer[key] for key in (
                    "layer_id", "evidence_class", "geometry_type",
                )
            } for layer in visual["layers"]],
            "drilldowns": [
                item["action_id"] for item in visual["drilldowns"]
            ],
        }

    def test_capability_interfaces_are_identical_across_packs(self):
        real = self.services["real"].capabilities
        synthetic = self.services["synthetic"].capabilities
        self.assertEqual(set(real), set(synthetic))
        for capability_id in sorted(real):
            with self.subTest(capability=capability_id):
                self.assertEqual(
                    self.capability_interface(real[capability_id]),
                    self.capability_interface(synthetic[capability_id]),
                )

    def test_every_typed_question_probe_emits_the_contract(self):
        for pack_name, pack in self.packs.items():
            probes = json.loads(
                (pack / "questions.json").read_text(encoding="utf-8")
            )["questions"]
            typed = [probe for probe in probes if probe.get("capability_id")]
            expected_typed = 17 if pack_name == "real" else 7
            self.assertEqual(len(typed), expected_typed)
            for probe in typed:
                with self.subTest(pack=pack_name, probe=probe["id"]):
                    result = self.services[pack_name].query(
                        f"{pack_name}-{probe['id']}",
                        probe["capability_id"],
                        probe.get("arguments") or {},
                        probe["question"],
                    )
                    if self.schema:
                        jsonschema.Draft202012Validator(self.schema).validate(result)
                    else:
                        self.assertEqual(result["schema_version"], "idli-result/1")
                    self.assertEqual(
                        result["status"], probe.get("expected_status", "complete")
                    )
                    expected_view = probe.get("expected_result_view")
                    if expected_view:
                        self.assertEqual(result["visuals"][0]["view"], expected_view)

    def test_ready_capabilities_have_the_same_renderer_grammar(self):
        pairs = {
            "site-orientation": ({}, {}),
            "entity-record-map": (
                {"entity": "lion-tailed macaque"},
                {"entity": "Karumalai Estate"},
            ),
            "coverage-versus-effort": ({}, {}),
            "group-record-map": (
                {"rank": "class", "group": "Amphibia"},
                {"rank": "sector", "group": "plantation_labour"},
            ),
            "metric-time-series": (
                {"metric": "rainfall"},
                {"metric": "daily_wage"},
            ),
            "interaction-map": (
                {
                    "interaction_type": "observed_visiting_focal_tree",
                    "entity": "Canarium strictum",
                },
                {
                    "interaction_type": "reported_migration_destination",
                    "entity": "tea_plucker",
                },
            ),
        }
        for capability_id, (real_args, synthetic_args) in pairs.items():
            with self.subTest(capability=capability_id):
                real = self.services["real"].query(
                    f"swap-real-{capability_id}", capability_id, real_args
                )
                synthetic = self.services["synthetic"].query(
                    f"swap-synthetic-{capability_id}", capability_id, synthetic_args
                )
                self.assertEqual(
                    self.visual_grammar(real), self.visual_grammar(synthetic)
                )

    def test_synthetic_status_is_visible_but_real_pack_is_not_mislabelled(self):
        synthetic = self.services["synthetic"].query(
            "synthetic-label", "metric-time-series", {"metric": "daily_wage"}
        )
        real = self.services["real"].query(
            "real-label", "metric-time-series", {"metric": "rainfall"}
        )
        self.assertTrue(synthetic["site"]["synthetic"])
        self.assertIn(
            "synthetic-data", {item["code"] for item in synthetic["limitations"]}
        )
        self.assertTrue(all(
            source["synthetic"] for source in synthetic["audit"]["source_versions"]
        ))
        self.assertNotIn("synthetic", real["site"])
        self.assertNotIn(
            "synthetic-data", {item["code"] for item in real["limitations"]}
        )
        self.assertTrue(all(
            not source["synthetic"] for source in real["audit"]["source_versions"]
        ))


if __name__ == "__main__":
    unittest.main()
