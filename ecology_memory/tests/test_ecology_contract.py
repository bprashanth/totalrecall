import os
import sys
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "harness"))

import connectors as C
import executor as EX
import origin_adapters as OA
import parser as P
from executor import _aggregate, _relate, DataRequest, execute
from parser import sector_semantic_repairs, faithfulness_pass
from ir_schema import validate
from scorer import score
from synthesize import (_safe_fallback, _fire_exposure_answer, _inventory_answer,
                        _greenness_answer, _group_transfer_answer, _landcover_answer,
                        _occurrence_gap_answer,
                        _published_site_evidence_answer, score_synthesis)


class EcologyContractTests(unittest.TestCase):
    def test_buffer_region_is_distinct_valid_search_extent(self):
        node = {"op": "BUFFER", "radius_km": 25.0,
                "source": {"op": "REGION", "place": "EBTL"}}
        self.assertTrue(validate(node)["valid"])
        original = C.resolve_region("EBTL")
        expanded = C.buffer_region(original, 25.0)
        self.assertLess(expanded["bbox"][0], original["bbox"][0])
        self.assertGreater(expanded["bbox"][1], original["bbox"][1])
        self.assertEqual(expanded["buffer_km"], 25.0)

    def test_invalid_buffer_radius_fails_schema(self):
        node = {"op": "BUFFER", "radius_km": 0,
                "source": {"op": "REGION", "place": "EBTL"}}
        self.assertFalse(validate(node)["valid"])
        node["radius_km"] = float("inf")
        self.assertFalse(validate(node)["valid"])
        node["radius_km"] = "?radius_km"
        report = validate(node)
        self.assertTrue(report["valid"])
        self.assertTrue(report["unbound"])

    def test_nested_buffers_add_radii_and_identical_supports_are_interned(self):
        from ir_schema import canonicalize
        region = {"op": "REGION", "place": "EBTL"}
        nested = {"op": "BUFFER", "radius_km": 15.0, "source": {
            "op": "BUFFER", "radius_km": 10.0, "source": region}}
        self.assertEqual(canonicalize(nested), {
            "op": "BUFFER", "radius_km": 25.0, "source": region})
        relation = {"op": "RELATE", "relation": "within",
                    "left": {"op": "SELECT", "entity": "a", "region": nested, "time": None},
                    "right": {"op": "SELECT", "entity": "b", "region": nested, "time": None}}
        canonical = canonicalize(relation)
        self.assertIs(canonical["left"]["region"], canonical["right"]["region"])

    def test_buffer_rejects_non_region_source(self):
        node = {"op": "BUFFER", "radius_km": 10, "source": {
            "op": "SELECT", "entity": "clinic",
            "region": {"op": "REGION", "place": "x"}, "time": None}}
        self.assertFalse(validate(node)["valid"])

    def test_bbox_buffer_fails_closed_at_dateline(self):
        region = {"name": "edge", "bbox": [-1, 1, 179.5, 179.9],
                  "lat": 0, "lon": 179.7}
        with self.assertRaisesRegex(ValueError, "dateline"):
            C.buffer_region(region, 100)

    def test_relation_execution_returns_proxy_contract_and_denominators(self):
        region = C.resolve_region("EBTL")
        left = {"kind": "records", "rows": [
                    {"id": "l1", "lat": 12.73, "lon": 78.18},
                    {"id": "l2", "lat": 13.0, "lon": 78.18}],
                "label": "observed", "source": "left", "grain": "occurrence",
                "region": region, "input_entity": "elephant"}
        right = {"kind": "records", "rows": [
                    {"id": "r1", "lat": 12.731, "lon": 78.181}],
                 "label": "observed", "source": "right", "grain": "occurrence",
                 "region": region, "input_entity": "cormorant"}
        ir = {"op": "RELATE", "relation": "cooccur", "threshold_km": 5.0,
              "left": {"op": "SELECT", "entity": "elephant",
                       "region": {"op": "REGION", "place": "EBTL"}, "time": None},
              "right": {"op": "SELECT", "entity": "cormorant",
                        "region": {"op": "REGION", "place": "EBTL"}, "time": None}}
        with mock.patch.object(EX, "_route_select", side_effect=[left, right]):
            got = execute(ir)
        value = got["value"]
        self.assertEqual(got["label"], "proxy")
        self.assertEqual(value["grain"], "occurrence-proximity-relation")
        self.assertEqual((value["left_record_count"], value["right_record_count"],
                          value["matched_left_count"]), (2, 1, 1))
        self.assertEqual(value["matched_right_count"], 1)
        self.assertEqual(value["matched_left_fraction"], 0.5)
        self.assertEqual(value["matched_right_fraction"], 1.0)
        self.assertEqual(value["matched_left_percent"], 50.0)
        self.assertEqual(value["matched_right_percent"], 100.0)
        self.assertEqual(value["temporal_alignment"], "not established")

    def test_joint_relation_estimate_fails_explicitly(self):
        relation = {"kind": "records", "rows": [{"lat": 1, "lon": 1}],
                    "label": "proxy", "source": "relation",
                    "grain": "occurrence-proximity-relation"}
        ir = {"op": "ESTIMATE", "method": "feature",
              "source": {"op": "SELECT", "entity": "relation evidence",
                         "region": {"op": "REGION", "place": "EBTL"}, "time": None},
              "target": {"op": "REGION", "place": "EBTL"}}
        with mock.patch.object(EX, "_route_select", return_value=relation):
            got = execute(ir)
        self.assertEqual(got["reason"], "unsupported_relational_transfer")

    def test_estimate_output_retains_donor_and_target_for_followups(self):
        donor_region = C.resolve_region("dry-Deccan donor belt")
        target_region = C.resolve_region("EBTL")
        source = {"kind": "records", "rows": [{"lat": 11.5, "lon": 77.0}],
                  "label": "observed", "source": "points", "grain": "occurrence",
                  "region": donor_region, "input_entity": "test taxon"}
        model = {"kind": "field", "rows": [{"suitability_fraction": 0.1}],
                 "label": "modelled", "source": "predict", "grain": "target",
                 "gate": {"pass": True}, "note": "modelled"}
        ir = {"op": "ESTIMATE", "method": "feature",
              "source": {"op": "SELECT", "entity": "test taxon",
                         "region": {"op": "REGION", "place": "dry-Deccan donor belt"},
                         "time": None},
              "target": {"op": "REGION", "place": "EBTL"}}
        with mock.patch.object(EX, "_route_select", return_value=source), \
             mock.patch.object(C, "estimate_transfer", return_value=model):
            got = execute(ir)["value"]
        self.assertEqual(got["donor_entity"], "test taxon")
        self.assertEqual(got["donor_region"], donor_region)
        self.assertEqual(got["target_region"], target_region)

    def test_connector_exception_becomes_source_request_not_unbound_route_crash(self):
        resolution = {"kind": "published_site_evidence", "canonical": "invasive_evidence"}
        with mock.patch.object(C, "resolve_ecology_entity", return_value=resolution), \
             mock.patch.object(C, "published_site_evidence", side_effect=RuntimeError("offline")), \
             self.assertRaises(DataRequest) as raised:
            EX._route_select("EBTL invasive evidence", C.resolve_region("EBTL"), None, [])
        self.assertEqual(raised.exception.reason, "source_unavailable")
        self.assertEqual(raised.exception.detail["source"], "published-site-evidence")

    def test_published_site_intents_route_to_declared_evidence_entities(self):
        raw = {"op": "SELECT", "entity": "birds", "region": "?place", "time": None}
        cases = {
            "What is in the documented EBTL wildlife inventory?": "EBTL wildlife inventory",
            "What is in the EBTL bird inventory?": "EBTL bird inventory",
            "What is in the documented EBTL cobra inventory?": "EBTL cobra inventory",
            "What is in the documented EBTL venomous snake inventory?":
                "EBTL venomous snake inventory",
            "What local elephant evidence is documented at EBTL?": "EBTL elephant evidence",
            "What is in the documented EBTL nursery inventory?": "EBTL nursery inventory",
            "What soil dryness evidence is documented at EBTL?": "EBTL soil dryness evidence",
            "What does EBTL bird Lantana transfer evidence establish?":
                "EBTL bird Lantana transfer evidence",
            "What snake habitat and tree requirements are documented for EBTL?":
                "EBTL snake habitat requirements",
        }
        for question, entity in cases.items():
            with self.subTest(question=question):
                got = sector_semantic_repairs(raw, question)
                self.assertEqual(got["op"], "SELECT")
                self.assertEqual(got["entity"], entity)
                self.assertEqual(got["region"]["place"], "Elephants by the Lake")

    def test_local_wildlife_summary_preserves_seen_vs_earlier_records(self):
        resolution = C.resolve_ecology_entity("EBTL wildlife inventory")
        got = C.published_site_evidence(resolution, C.resolve_region("EBTL"))
        groups = {row["group"]: row for row in got["rows"]}
        self.assertEqual(groups["butterflies"]["recorded_taxa"], 54)
        self.assertEqual(groups["odonates"]["recorded_taxa"], 42)
        self.assertEqual(groups["birds"]["recorded_taxa"], 67)
        self.assertEqual(groups["herpetofauna"]["recorded_taxa"], 33)
        self.assertEqual(groups["herpetofauna"]["observed_during_survey"], 20)
        self.assertEqual(groups["herpetofauna"]["earlier_property_records_not_observed"], 13)
        answer = _published_site_evidence_answer(
            {"status": "answer", "value": got, "label": "observed"})
        self.assertIn("54 butterfly", answer)
        self.assertIn("42 odonates", answer)
        self.assertIn("67 birds", answer)
        self.assertIn("20 were encountered", answer)
        self.assertIn("two indirect elephant", answer)

    def test_local_bird_inventory_is_complete_and_page_addressable(self):
        resolution = C.resolve_ecology_entity("EBTL bird inventory")
        got = C.published_site_evidence(resolution, C.resolve_region("EBTL"))
        self.assertEqual(len(got["rows"]), 67)
        self.assertEqual(got["query_semantics"], "bird_inventory")
        self.assertIn("#page=18", got["rows"][0]["source_record"])
        answer = _published_site_evidence_answer(
            {"status": "answer", "value": got, "label": "observed"})
        self.assertIn("67 bird species", answer)
        self.assertIn("site survey", answer)

    def test_arachnid_transfer_intent_routes_to_dynamic_evidence(self):
        raw = {"op": "SELECT", "entity": "arachnids", "region": "?place", "time": None}
        got = sector_semantic_repairs(
            raw, "What regional arachnid records and transfer gates apply to EBTL?")
        self.assertEqual(got["entity"], "EBTL arachnid transfer evidence")
        self.assertEqual(C.resolve_ecology_entity(got["entity"])["kind"],
                         "taxon_group_transfer")

    def test_dynamic_arachnid_candidates_fail_closed_on_feature_gate(self):
        local = {
            "rows": [{"scientific_name": "Thelacantha brevispina"}],
            "inventory": {"deduplicated_records": 1,
                          "named_species": ["Thelacantha brevispina"]},
            "connector_events": [], "evidence_discovery": [{"title": "Spider data"}],
        }
        regional_rows = ([{"scientific_name": "Gasteracantha geminata"}] * 3 +
                         [{"scientific_name": "Plexippus petersi"}] * 2 +
                         [{"scientific_name": "Hyllus semicupreus"}])
        regional = {
            "rows": regional_rows,
            "inventory": {"deduplicated_records": 6, "gbif_api_total": 100,
                          "named_species": sorted({r["scientific_name"]
                                                   for r in regional_rows})},
            "connector_events": [], "evidence_discovery": [],
        }

        def fake_points(species, region, time_value=None, limit=300):
            return {"rows": [{"lat": 12.0, "lon": 77.0}] * 25,
                    "connector_events": [{"tool": "origin.points.get", "output_rows": 25}]}

        def fake_gate(source, target, method):
            local_species = source.get("resolution", {}).get("canonical") == \
                "Thelacantha brevispina"
            return {"pass": local_species or method == "envelope",
                    "strength": ("AlphaEarth-NN-analog" if method == "feature" else
                                 "WorldClim-MESS-envelope"),
                    "target_analog_fraction": 0.2,
                    "target_in_envelope_fraction": 1.0}

        def fake_points_with_resolution(species, region, time_value=None, limit=300):
            out = fake_points(species, region, time_value, limit)
            out["resolution"] = {"canonical": species}
            return out

        with mock.patch.object(C, "taxon_group_occurrences",
                               side_effect=[local, regional]), \
             mock.patch.object(C, "taxon_occurrences",
                               side_effect=fake_points_with_resolution), \
             mock.patch.object(C, "transfer_gate", side_effect=fake_gate):
            got = C.arachnid_transfer_evidence(C.resolve_region("EBTL"))
        self.assertEqual(got["query_semantics"], "taxon_group_transfer_audit")
        self.assertEqual(got["admitted_transfer_candidates"], [])
        self.assertEqual(got["assessment_counts"]["species_audited"], 4)
        self.assertEqual(got["assessment_counts"]["regional_not_locally_observed"], 3)
        self.assertTrue(got["assessments"][0]["locally_observed"])
        self.assertIn("at least 0.5", got["gate_contract"]["feature"])
        self.assertIn("does not change", got["assessments"][1]["feature_gate"]["ask"])
        self.assertTrue(all(not row["transfer_admissible"]
                            for row in got["assessments"]))
        answer = _group_transfer_answer({"status": "answer", "value": got})
        self.assertIn("No unobserved regional candidate passed both gates", answer)
        self.assertIn("not the property boundary", answer)

    def test_cached_transfer_gate_restores_declared_threshold(self):
        source = {"grain": "occurrence", "rows": [
            {"lat": 11.0 + i * 0.01, "lon": 76.0 + i * 0.01} for i in range(20)]}
        target = {"bbox": [12.7, 12.8, 78.1, 78.2]}
        cached = {"pass": False, "strength": "AlphaEarth-NN-analog",
                  "target_analog_fraction": 0.2}
        with mock.patch.object(C, "_cache_get", return_value=cached):
            got = C.transfer_gate(source, target, "feature")
        self.assertEqual(got["target_analog_fraction_threshold"], 0.5)

    def test_venomous_subset_preserves_survey_status(self):
        resolution = C.resolve_ecology_entity("EBTL venomous snake inventory")
        got = C.published_site_evidence(resolution, C.resolve_region("EBTL"))
        self.assertEqual([r["common_name"] for r in got["rows"]], [
            "Spectacled Cobra", "Russell's Viper", "Saw-scaled Viper", "Bamboo Pit Viper"])
        self.assertTrue(all(r["record_status"] ==
                            "previous_property_record_not_observed_during_survey"
                            for r in got["rows"]))

    def test_snake_tree_question_uses_inventory_but_invents_no_tree_link(self):
        resolution = C.resolve_ecology_entity("EBTL snake habitat requirements")
        got = C.published_site_evidence(resolution, C.resolve_region("EBTL"))
        self.assertEqual(len(got["rows"]), 14)
        self.assertEqual(got["query_semantics"], "snake_habitat_requirements")
        self.assertIn("no snake-by-tree use", got["note"])
        answer = _published_site_evidence_answer(
            {"status": "answer", "value": got, "label": "observed"})
        self.assertIn("No specific tree species", answer)
        self.assertIn("general ecology", answer)

    def test_elephant_site_evidence_is_indirect_not_api_absence(self):
        resolution = C.resolve_ecology_entity("EBTL elephant evidence")
        got = C.published_site_evidence(resolution, C.resolve_region("EBTL"))
        self.assertEqual(len(got["rows"]), 2)
        self.assertTrue(all(r["evidence_type"] == "indirect_site_evidence"
                            for r in got["rows"]))
        answer = _published_site_evidence_answer(
            {"status": "answer", "value": got, "label": "observed"})
        self.assertIn("indirect site-use evidence", answer)
        self.assertNotIn("no elephant records", answer.lower())

    def test_bird_lantana_join_keeps_regional_gate_and_exact_point_counts(self):
        resolution = C.resolve_ecology_entity("EBTL bird Lantana transfer evidence")
        counts = {"Lantana camara": 0, "Jatropha gossypiifolia": 1,
                  "Dichrostachys cinerea": 1, "Abrus precatorius": 3}

        def fake_points(resolved, region, time_value, limit):
            n = counts.get(resolved["canonical"], 2)
            return {"rows": [{"id": str(i)} for i in range(n)], "connector_events": [
                {"tool": "origin.points.get", "output_rows": n}]}

        with mock.patch.object(OA, "points_occurrences", side_effect=fake_points):
            got = C.published_site_evidence(resolution, C.resolve_region("EBTL"))
        self.assertEqual(got["label"], "modelled")
        self.assertEqual(got["source_metadata"]["site_bbox_public_plant_points"], counts)
        self.assertEqual(len(got["connector_events"]), 9)
        answer = _published_site_evidence_answer(
            {"status": "answer", "value": got, "label": "modelled"})
        self.assertIn("regional mechanism", answer)
        self.assertIn("not the property boundary", answer)

    def test_invalid_json_gets_one_compiler_style_repair(self):
        fixed = {"op": "SELECT", "entity": "Lantana records",
                 "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        with mock.patch.object(P, "chat", side_effect=["{broken", __import__("json").dumps(fixed)]):
            got = P.parse("Show Lantana records in Valparai.", role="qwen2b")
        self.assertEqual(got["ir"], fixed)
        self.assertIn("llm_parse_repair:accepted", got["events"])

    def test_top_level_candidate_array_is_not_silently_first_tree(self):
        events = []
        raw = '[{"op":"SELECT","entity":"wrong"},{"op":"SELECT","entity":"right"}]'
        self.assertIsNone(P.extract_json(raw, events))
        self.assertIn("top_level_array:rejected", events)

    def test_post_think_tree_is_the_only_compiler_output(self):
        raw = ('{"op":"SELECT","entity":"draft"}</think>\n'
               '{"op":"SELECT","entity":"final","region":"?place","time":null}')
        self.assertEqual(P.extract_json(raw)["entity"], "final")

    def test_abundance_is_not_routed_to_occurrence(self):
        got = C.resolve_ecology_entity("elephant population")
        self.assertEqual(got["kind"], "unsupported_measure")

    def test_ebtl_region_uses_declared_site_bbox_without_geocoding(self):
        with mock.patch.object(C, "_get", side_effect=AssertionError("must not geocode EBTL")):
            got = C.resolve_region("Elephants by the Lake")
        self.assertEqual(got["bbox"], [12.721, 12.747, 78.170, 78.197])
        self.assertEqual(got["source"], "SITE_EBTL.json")

    def test_ebtl_site_point_is_a_proxy_not_a_whole_aoi_observation(self):
        resolution = C.resolve_ecology_entity("EBTL restoration site")
        self.assertEqual(resolution["kind"], "site_point")
        got = C.site_center(C.resolve_region("EBTL"))
        self.assertEqual(got["label"], "proxy")
        self.assertEqual(got["grain"], "declared-site-center")
        self.assertFalse(got["count_admissible"])
        self.assertEqual(C.resolve_layer("land cover class"), "landcover")

    def test_snakes_resolve_to_a_group_inventory_not_one_guessed_species(self):
        for entity in ("snake", "snakes", "all snakes", "Serpentes"):
            got = C.resolve_ecology_entity(entity)
            self.assertEqual(got["kind"], "taxon_inventory")
            self.assertEqual(got["taxon"], "Serpentes")

    def test_snake_inventory_carries_declared_venomous_subset(self):
        resolution = C.resolve_ecology_entity("snakes")
        got = C.published_taxon_inventory(resolution, C.resolve_region("EBTL"))
        venomous = [row for row in got["rows"] if row["medically_venomous"]]
        self.assertEqual(len(venomous), 4)
        self.assertEqual({row["family"] for row in venomous}, {"Elapidae", "Viperidae"})

    def test_risk_of_fire_is_historical_exposure_not_a_keyword_gap(self):
        raw = {"op": "ESTIMATE", "method": "feature",
               "target": {"op": "REGION", "place": "EBTL"},
               "source": {"op": "SELECT", "entity": "fire risk",
                          "region": {"op": "REGION", "place": "EBTL"}, "time": None}}
        got = sector_semantic_repairs(raw, "What is the risk of fire there?")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["layer"], "fire exposure")
        self.assertEqual(got["source"]["entity"], "site center point")
        self.assertEqual(got["source"]["time"], {"start": "2020", "end": "2025"})

    def test_place_landcover_is_not_a_vegetation_entity_select(self):
        raw = {"op": "SELECT", "entity": "vegetation",
               "region": {"op": "REGION", "place": "EBTL"}, "time": None}
        got = sector_semantic_repairs(raw, "What is the current vegetation or land cover?")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["layer"], "land cover")
        self.assertEqual(got["source"]["entity"], "site center point")

    def test_restoration_progress_is_a_labelled_greenness_proxy(self):
        raw = {"op": "SELECT", "entity": "restoration progress",
               "region": {"op": "REGION", "place": "EBTL"}, "time": None}
        got = sector_semantic_repairs(raw, "How has restoration progressed over time?")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["layer"], "greenness trend")
        self.assertEqual(got["source"]["time"], {"start": "2019", "end": "2024"})

    def test_fire_adapter_delegates_to_locked_origin_connector(self):
        fake_fire = mock.Mock()
        fake_fire.exposure.return_value = [{"id": "site", "lat": 1.0, "lon": 2.0,
                                            "fire_count": 1.6, "fire_density": 0.021,
                                            "radius_km": 5}]
        fake_fire.points.return_value = []
        with mock.patch.object(OA, "_module", return_value=fake_fire):
            got = OA.fire_exposure(
                [{"id": "site", "lat": 1.0, "lon": 2.0}],
                {"bbox": [0.9, 1.1, 1.9, 2.1]}, 2020, 2025)
        fake_fire.exposure.assert_called_once()
        fake_fire.points.assert_called_once()
        self.assertEqual(got["rows"][0]["pixel_fire_days"], 1.6)
        self.assertNotIn("fire_count", got["rows"][0])
        self.assertEqual(got["field_units"]["pixel_fire_days"], "pixel-fire-days")
        self.assertEqual(got["measurement_scopes"][0]["scope"], "declared analysis bbox")
        self.assertEqual(got["measurement_scopes"][1]["scope"],
                         "5-km buffer around the EBTL site-centre point")
        self.assertEqual(got["connector_events"][0]["tool"], "origin.fire.points")
        self.assertEqual(got["label"], "proxy")

    def test_occurrence_adapter_delegates_to_exact_origin_points(self):
        fake = mock.Mock()
        fake.get.return_value = {"path": "/missing/empty.csv", "n": 0, "cached": False,
                                 "by_source": {"gbif": 0, "inat": 0, "paper": 0}}
        resolution = {"canonical": "Elephas maximus", "count_admissible": True}
        with mock.patch.object(OA, "_verify"), mock.patch.object(OA, "_module", return_value=fake):
            got = OA.points_occurrences(
                resolution, {"bbox": [12.721, 12.747, 78.170, 78.197]}, None, 200)
        fake.get.assert_called_once_with(
            "Elephas maximus", bbox=[78.17, 12.721, 78.197, 12.747],
            sources=("gbif", "inat"), limit=200, resolve_name=False)
        self.assertEqual(got["connector_events"][0]["tool"], "origin.points.get")
        self.assertEqual(got["rows"], [])

    def test_occurrence_adapter_refuses_unenforceable_time_window(self):
        got = OA.points_occurrences(
            {"canonical": "Elephas maximus"},
            {"bbox": [12.721, 12.747, 78.170, 78.197]},
            {"start": "2020", "end": "2025"})
        self.assertTrue(got["unsupported_time"])

    def test_predict_adapters_preserve_origin_bbox_order_and_year(self):
        fake = mock.Mock()
        fake.gate.return_value = {"pass": True}
        fake.presence.return_value = {"fraction": 0.039}
        fake.sdm_climate.return_value = {"fraction": 0.1}
        rows = [{"lat": 12.0, "lon": 77.0}]
        target = {"bbox": [12.721, 12.747, 78.170, 78.197]}
        with mock.patch.object(OA, "_verify"), mock.patch.object(
                OA, "_module", return_value=fake):
            self.assertEqual(OA.predict_gate(rows, target, 2023), {"pass": True})
            self.assertEqual(OA.predict_presence(rows, target, 2023), {"fraction": 0.039})
            self.assertEqual(OA.predict_sdm(rows, target, 2024), {"fraction": 0.1})
        bbox = [78.17, 12.721, 78.197, 12.747]
        fake.gate.assert_called_once_with(rows, bbox, year=2023)
        fake.presence.assert_called_once_with(rows, bbox, year=2023)
        fake.sdm_climate.assert_called_once_with(rows, bbox, year=2024)

    def test_fire_answer_states_metric_and_limitation(self):
        result = {"status": "answer", "value": {"layer": "fire_exposure", "rows": [{
            "pixel_fire_days": 1.6, "fire_density": 0.021, "radius_km": 5,
            "period": "2020-2025", "analysis_bbox_active_fire_locations": 0}]}}
        answer = _fire_exposure_answer(result)
        self.assertIn("0 active-fire locations", answer)
        self.assertIn("1.6 pixel-fire-days", answer)
        self.assertIn("historical pressure proxies", answer)
        self.assertIn("not a forecast", answer)

    def test_landcover_adapter_delegates_point_and_aoi_to_origin(self):
        fake = mock.Mock()
        fake.classify.return_value = [{"id": "site", "lat": 1.0, "lon": 2.0,
                                       "landcover_code": 20, "landcover": "Shrubland"}]
        fake.area_by_class.return_value = {"Shrubland": 4.37, "Tree cover": 3.63}
        with mock.patch.object(OA, "_module", return_value=fake):
            got = OA.landcover_summary(
                [{"id": "site", "lat": 1.0, "lon": 2.0}],
                {"bbox": [0.9, 1.1, 1.9, 2.1]})
        fake.classify.assert_called_once()
        fake.area_by_class.assert_called_once()
        self.assertEqual(got["connector_events"][1]["tool"],
                         "origin.landcover.area_by_class")
        self.assertEqual(got["label"], "modelled")

    def test_landcover_answer_separates_analysis_bbox_from_property(self):
        result = {"status": "answer", "value": {"layer": "landcover", "rows": [{
            "landcover": "Shrubland",
            "area_by_class_km2": {"Shrubland": 4.37, "Tree cover": 3.63}}]}}
        answer = _landcover_answer(result)
        self.assertIn("Shrubland 4.37 km²", answer)
        self.assertIn("not a surveyed composition of the 70-acre property", answer)

    def test_greenness_answer_does_not_claim_restoration_causality(self):
        result = {"status": "answer", "value": {"layer": "greenness_trend", "rows": [{
            "trend_class": "greening", "period": "2019-2024", "ndvi_start": 0.4924,
            "ndvi_end": 0.5585, "ndvi_slope": 0.01317}]}}
        answer = _greenness_answer(result)
        self.assertIn("0.01317 NDVI/year", answer)
        self.assertIn("not whole-property coverage", answer)
        self.assertIn("proof that restoration caused", answer)

    def test_empty_public_occurrence_is_not_evidence_of_absence(self):
        result = {"status": "data_request", "reason": "empty_select",
                  "detail": {"entity": "elephants", "region": "EBTL"},
                  "provenance": [{"route": "gbif+inaturalist",
                                  "resolved": "Elephas maximus"}]}
        answer = _occurrence_gap_answer(result)
        self.assertIn("coverage gap", answer)
        self.assertIn("not evidence the species is absent", answer)

    def test_published_snake_inventory_preserves_survey_semantics(self):
        ir = {"op": "SELECT", "entity": "snake species",
              "region": {"op": "REGION", "place": "EBTL"}, "time": None}
        got = execute(ir)
        self.assertEqual(got["status"], "answer")
        self.assertEqual(got["value"]["inventory"], {
            "taxon": "Serpentes", "species": 14, "observed_during_survey": 3,
            "previous_property_records_not_observed_during_survey": 11})
        self.assertEqual(got["provenance"][0]["route"], "published-taxon-inventory")
        answer = _inventory_answer(got)
        self.assertIn("14 documented snake species", answer)
        self.assertIn("three-day VES observed", answer)
        self.assertIn("those 11 were not encountered", answer)
        self.assertIn("Bamboo Pit Viper", answer)

    def test_occurrence_count_requires_record_wording(self):
        fake = {"scientific": "Elephas maximus", "rank": "SPECIES", "match": "EXACT",
                "confidence": 100, "usage_key": 1, "alternatives": []}
        with mock.patch.object(C, "_gbif_taxon_match", return_value=fake):
            self.assertFalse(C.resolve_ecology_entity("elephants")["count_admissible"])
            self.assertTrue(C.resolve_ecology_entity("elephant occurrence records")["count_admissible"])

    def test_existential_occurrences_restore_presence_metric(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "green cat snake",
            "region": {"op": "REGION", "place": "India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Are there any documented occurrences of the green cat snake in India?")
        self.assertEqual(got["metric"], "presence")

    def test_non_record_abundance_count_fails_closed(self):
        src = {"kind": "records", "rows": [{"lat": 1, "lon": 1}],
               "grain": "occurrence", "count_admissible": False, "label": "observed",
               "entity": "Elephas maximus"}
        with self.assertRaises(DataRequest) as ctx:
            _aggregate(src, "space", "count")
        self.assertEqual(ctx.exception.reason, "unsupported_measure")

    def test_cross_source_relation_keeps_true_empty(self):
        left = [{"id": "a", "lat": 10.0, "lon": 10.0}]
        right = [{"id": "b", "lat": 12.0, "lon": 12.0}]
        self.assertEqual(_relate(left, right, "within", 1), [])
        self.assertEqual(len(_relate(left, right, "beyond", 1)), 1)

    def test_yet_conjoined_two_anchor_relation_is_nested(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "RELATE", "relation": "beyond", "threshold_km": 0.3,
            "left": {"op": "SELECT", "entity": "Lantana records",
                     "region": {"op": "REGION", "place": "Valparai, India"}, "time": None},
            "right": {"op": "SELECT", "entity": "survey sites",
                      "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}}
        got = sector_semantic_repairs(
            raw, "In Valparai, what is the count of Lantana records that are within 1 km of survey sites yet beyond 300 m from elephant records?")
        self.assertEqual(got["source"]["relation"], "beyond")
        self.assertEqual(got["source"]["right"]["entity"], "elephant records")
        self.assertEqual(got["source"]["left"]["relation"], "within")
        self.assertEqual(got["source"]["left"]["right"]["entity"], "survey sites")

    def test_compound_anchor_stops_before_is_needed_tail(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "Lantana records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "The count of Lantana records in Valparai that are within 1 km of survey sites but beyond 300 m from elephant records is needed.")
        self.assertEqual(got["source"]["right"]["entity"], "elephant records")

    def test_transfer_requires_enough_occurrences_before_live_covariates(self):
        src = {"kind": "records", "grain": "occurrence",
               "rows": [{"lat": 10 + i / 100, "lon": 77.0} for i in range(19)]}
        target = {"bbox": [11, 12, 78, 79], "lat": 11.5, "lon": 78.5}
        got = C.transfer_gate(src, target, "feature")
        self.assertFalse(got["pass"])
        self.assertEqual(got["strength"], "sample-size")

    def test_transfer_refuses_when_observations_already_cover_target(self):
        src = {"kind": "records", "grain": "occurrence",
               "rows": [{"lat": 10.1 + i / 1000, "lon": 77.1} for i in range(20)]}
        target = {"bbox": [10, 11, 77, 78], "lat": 10.5, "lon": 77.5}
        got = C.transfer_gate(src, target, "envelope")
        self.assertFalse(got["pass"])
        self.assertEqual(got["strength"], "observed-overlap")

    def test_interpolation_never_extrapolates(self):
        src = {"kind": "records", "grain": "point", "measure_field": "height", "unit": "m",
               "rows": [{"lat": lat, "lon": lon, "height": lat + lon}
                        for lat, lon in [(0, 0), (0, 2), (2, 0), (2, 2), (1, 1)]]}
        inside = {"bbox": [0.8, 1.2, 0.8, 1.2], "lat": 1, "lon": 1, "name": "inside"}
        outside = {"bbox": [3, 4, 3, 4], "lat": 3.5, "lon": 3.5, "name": "outside"}
        self.assertTrue(C.transfer_gate(src, inside, "interpolate")["pass"])
        self.assertFalse(C.transfer_gate(src, outside, "interpolate")["pass"])
        out = C.estimate_transfer(src, inside, "interpolate")
        self.assertEqual(out["label"], "modelled")
        self.assertAlmostEqual(out["rows"][0]["height"], 2.0, places=5)

    def test_license_allowlist_is_directional(self):
        self.assertTrue(C._redistributable_license("CC0"))
        self.assertTrue(C._redistributable_license("https://creativecommons.org/licenses/by/4.0/"))
        self.assertFalse(C._redistributable_license("https://creativecommons.org/licenses/by-nc/4.0/"))

    def test_recovery_question_retains_trend_after_place_binding(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean",
               "source": {"op": "SELECT", "entity": "NDVI", "region": "?place", "time": None}}
        got = sector_semantic_repairs(raw, "Is NDVI recovering around here?")
        self.assertEqual(got["op"], "COMPARE")
        self.assertEqual(got["how"], "trend_direction")
        self.assertEqual(got["left"]["source"]["region"], "?place")

    def test_abstract_indicator_drops_invented_annotation(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean",
               "source": {"op": "ANNOTATE", "layer": "ecosystem health",
                          "source": {"op": "SELECT", "entity": "forest health",
                                     "region": {"op": "REGION", "place": "Valparai, India"},
                                     "time": None}}}
        got = sector_semantic_repairs(raw, "How healthy is the ecosystem in Valparai?")
        self.assertEqual(got, {"op": "SELECT", "entity": "?indicator",
                               "region": {"op": "REGION", "place": "Valparai, India"},
                               "time": None})

    def test_ecological_health_adjective_requires_indicator_hole(self):
        raw = {"op": "SELECT", "entity": "ecological health status",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(raw, "What is the ecological health status in Valparai?")
        self.assertEqual(got["entity"], "?indicator")

    def test_ecosystem_wellbeing_requires_indicator_hole(self):
        raw = {"op": "SELECT", "entity": "ecosystem wellbeing",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(raw, "What is the degree of ecosystem wellbeing in Valparai?")
        self.assertEqual(got["entity"], "?indicator")

    def test_how_is_ecosystem_doing_requires_indicator_hole(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
            "op": "ANNOTATE", "layer": "ecosystem", "source": {
                "op": "SELECT", "entity": "Valparai",
                "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}}
        got = sector_semantic_repairs(raw, "How's the ecosystem doing in Valparai?")
        self.assertEqual(got["entity"], "?indicator")

    def test_how_well_is_ecosystem_doing_requires_indicator_hole(self):
        raw = {"op": "ESTIMATE", "method": "envelope",
               "target": {"op": "REGION", "place": "Valparai, India"},
               "source": {"op": "SELECT", "entity": "ecosystem indicators",
                          "region": {"op": "REGION", "place": "Valparai, India"},
                          "time": None}}
        got = sector_semantic_repairs(raw, "How well is the ecosystem doing in Valparai?")
        self.assertEqual(got["entity"], "?indicator")

    def test_categorical_annotation_cannot_collapse_to_count(self):
        result = {"status": "answer", "label": "modelled", "value": {
            "kind": "records", "source": "RESOLVE/ECOREGIONS/2017", "layer": "ecoregion",
            "rows": [{"ecoregion": "South Western Ghats montane rain forests",
                      "biome": "Tropical & Subtropical Moist Broadleaf Forests"}]}}
        bare = "Modelled result: 1 record. Source: RESOLVE/ECOREGIONS/2017."
        self.assertFalse(score_synthesis("Which ecoregion?", result, bare)["states_finding"])
        fallback = _safe_fallback(result)
        self.assertIn("South Western Ghats montane rain forests", fallback)
        self.assertTrue(score_synthesis("Which ecoregion?", result, fallback)["states_finding"])

    def test_parser_cannot_invent_countable_record_grain(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "elephant observation records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(raw, "What is the total elephant count for Valparai?")
        self.assertEqual(got["source"]["entity"], "elephant")

    def test_terse_organism_count_cannot_invent_record_grain(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "elephant observation records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(raw, "Elephant count in Valparai?")
        self.assertEqual(got["source"]["entity"], "elephant")

    def test_number_present_cannot_weaken_abundance_to_presence(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "presence", "source": {
            "op": "SELECT", "entity": "elephants",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Can you tell me the number of elephants that are present in Valparai?")
        self.assertEqual(got["metric"], "count")
        self.assertEqual(got["source"]["entity"], "elephants")

    def test_elephant_inventory_cannot_invent_record_grain(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "elephant observation records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(raw, "Elephant inventory for Valparai.")
        self.assertEqual(got["source"]["entity"], "elephant")

    def test_free_standing_number_cannot_invent_record_grain(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "elephant observation records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "What number defines the elephant population in Valparai?")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(got["entity"], "elephant population")

    def test_count_feasibility_does_not_invoke_transfer(self):
        raw = {"op": "ESTIMATE", "method": "feature",
               "target": {"op": "REGION", "place": "Valparai, India"},
               "source": {"op": "SELECT", "entity": "elephant observation records",
                          "region": {"op": "REGION", "place": "Valparai, India"},
                          "time": None}}
        got = sector_semantic_repairs(raw, "Is the count of elephants in Valparai feasible to obtain?")
        self.assertEqual(got["op"], "AGGREGATE")
        self.assertEqual(got["source"]["entity"], "elephant")

    def test_explicit_occurrence_record_count_keeps_record_grain(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "Lantana occurrence records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(raw, "Lantana occurrence record count in Valparai?")
        self.assertEqual(got["source"]["entity"], "Lantana occurrence records")

    def test_population_wrappers_collapse_to_unsupported_select(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
            "op": "ANNOTATE", "layer": "elephant population size", "source": {
                "op": "SELECT", "entity": "elephant population",
                "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}}
        got = sector_semantic_repairs(raw, "What is the size of the elephant population in Valparai?")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(got["entity"], "elephant population")

    def test_abundance_schema_reroll_restores_literal_entity_and_place(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "AGGREGATE", "by": "space", "metric": "presence", "source": {
                "op": "SELECT", "entity": "green cat snake", "region": "?place", "time": None}}}
        got = sector_semantic_repairs(raw, "Give the elephant abundance for Valparai.")
        self.assertEqual(got["entity"], "elephant abundance")
        self.assertEqual(got["region"]["place"], "Valparai")

    def test_farther_than_conjoined_two_anchor_relation_is_nested(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "RELATE", "relation": "within", "threshold_km": 1.0,
            "left": {"op": "SELECT", "entity": "Lantana records",
                     "region": {"op": "REGION", "place": "Valparai, India"}, "time": None},
            "right": {"op": "SELECT", "entity": "elephant records",
                      "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}}
        got = sector_semantic_repairs(
            raw, "How many Lantana records in Valparai are located within 1 km of survey sites and farther than 300 m from elephant records?")
        self.assertEqual(got["source"]["relation"], "beyond")
        self.assertEqual(got["source"]["left"]["right"]["entity"], "survey sites")
        self.assertEqual(got["source"]["right"]["entity"], "elephant records")

    def test_two_anchor_relation_strips_directional_determiners(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "Lantana records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Count Lantana records in Valparai that lie within 1 km of a survey site and farther than 300 m from any elephant record.")
        self.assertEqual(got["source"]["left"]["right"]["entity"], "survey site")
        self.assertEqual(got["source"]["right"]["entity"], "elephant record")

    def test_curly_possessive_place_is_literal_provenance(self):
        raw = {"op": "SELECT", "entity": "Lantana records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = faithfulness_pass(raw, "Can Valparai’s Lantana records support a transfer?")
        self.assertEqual(got["region"], {"op": "REGION", "place": "Valparai, India"})

    def test_colon_attached_place_is_literal_provenance(self):
        raw = {"op": "SELECT", "entity": "NDVI",
               "region": {"op": "REGION", "place": "Pollachi, India"}, "time": None}
        got = faithfulness_pass(
            raw, "Compare mean NDVI in 2024 for Valparai and Pollachi: which was higher?")
        self.assertEqual(got["region"], {"op": "REGION", "place": "Pollachi, India"})

    def test_em_dash_attached_place_is_literal_provenance(self):
        raw = {"op": "ESTIMATE", "method": "envelope",
               "target": {"op": "REGION", "place": "Delhi, India"},
               "source": {"op": "SELECT", "entity": "Lantana records",
                          "region": {"op": "REGION", "place": "Valparai, India"},
                          "time": None}}
        got = faithfulness_pass(
            raw, "Estimate Lantana presence in Delhi—where no survey exists—using Valparai records.")
        self.assertEqual(got["target"], {"op": "REGION", "place": "Delhi, India"})

    def test_indirect_preference_wording_requires_proxy(self):
        raw = {"op": "SELECT", "entity": "native trees",
               "region": {"op": "REGION", "place": "Mysuru, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "What explains the preference for native trees among Mysuru's population?")
        self.assertEqual(got, {"op": "SELECT", "entity": "?proxy",
                               "region": "?place", "time": None})

    def test_causative_human_choice_wording_requires_proxy(self):
        raw = {"op": "SELECT", "entity": "native trees",
               "region": {"op": "REGION", "place": "Mysuru, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "What leads the people of Mysuru to choose native trees?")
        self.assertEqual(got, {"op": "SELECT", "entity": "?proxy",
                               "region": "?place", "time": None})

    def test_causal_factors_human_choice_wording_requires_proxy(self):
        raw = {"op": "SELECT", "entity": "people of Mysuru",
               "region": {"op": "REGION", "place": "Mysuru, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "What factors cause the people of Mysuru to choose native tree species?")
        self.assertEqual(got, {"op": "SELECT", "entity": "?proxy",
                               "region": "?place", "time": None})

    def test_indirect_ndvi_shift_restores_endpoint_difference(self):
        raw = {"op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2018", "end": "2024"}}}
        got = sector_semantic_repairs(
            raw, "The magnitude of the NDVI shift in Valparai between 2018 and 2024 is needed.")
        self.assertEqual(got["op"], "COMPARE")
        self.assertEqual(got["left"]["time"], {"start": "2024", "end": "2024"})
        self.assertEqual(got["right"]["time"], {"start": "2018", "end": "2018"})

    def test_ndvi_variation_restores_endpoint_difference(self):
        raw = {"op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2018", "end": "2024"}}}
        got = sector_semantic_repairs(
            raw, "Quantify the NDVI variation in Valparai from 2018 to 2024.")
        self.assertEqual(got["op"], "COMPARE")
        self.assertEqual(got["left"]["time"], {"start": "2024", "end": "2024"})
        self.assertEqual(got["right"]["time"], {"start": "2018", "end": "2018"})

    def test_declarative_two_place_ndvi_comparison(self):
        raw = {"op": "COMPARE", "how": "difference",
               "left": {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
                   "op": "SELECT", "entity": "NDVI",
                   "region": {"op": "REGION", "place": "Valparai, India"},
                   "time": {"start": "2024"}}},
               "right": {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
                   "op": "SELECT", "entity": "NDVI",
                   "region": {"op": "REGION", "place": "Pollachi, India"},
                   "time": {"start": "2024"}}}}
        got = sector_semantic_repairs(
            raw, "Whether the 2024 mean NDVI in Valparai exceeded that in Pollachi is determined.")
        self.assertEqual(got["op"], "COMPARE")

    def test_which_site_two_place_ndvi_is_regional_comparison(self):
        def wrong_side(place):
            return {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
                "op": "ANNOTATE", "layer": "NDVI", "source": {
                    "op": "SELECT", "entity": "vegetation survey sites",
                    "region": {"op": "REGION", "place": f"{place}, India"},
                    "time": {"start": "2024", "end": "2024"}}}}
        raw = {"op": "COMPARE", "how": "difference",
               "left": wrong_side("Valparai"), "right": wrong_side("Pollachi")}
        got = sector_semantic_repairs(
            raw, "Which site, Valparai or Pollachi, exhibited a higher mean NDVI in 2024?")
        self.assertEqual(got["left"]["source"]["entity"], "NDVI")
        self.assertEqual(got["right"]["source"]["entity"], "NDVI")
        self.assertTrue(all(got[side]["by"] == "time" for side in ("left", "right")))
        self.assertEqual(got["left"]["by"], "time")
        self.assertEqual(got["right"]["source"]["time"], {"start": "2024", "end": "2024"})

    def test_declarative_ecoregion_request_restores_annotation(self):
        raw = {"op": "SELECT", "entity": "Anamalai survey sites",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "The ecoregions containing the Anamalai survey sites near Valparai are to be identified.")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["layer"], "ecoregion")

    def test_records_of_two_taxa_restores_union(self):
        raw = {"op": "ANNOTATE", "layer": "Lantana occurrence records", "source": {
            "op": "SELECT", "entity": "Lantana occurrence records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "The occurrence records of Lantana and teak in the Valparai area are to be displayed.")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(len(got["entity"]), 2)
        self.assertIn("teak occurrence records", got["entity"])

    def test_redundant_self_annotation_is_unwrapped(self):
        raw = {"op": "ANNOTATE", "layer": "frog acoustic surveys", "source": {
            "op": "SELECT", "entity": "frog acoustic surveys",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(raw, "The frog acoustic surveys in Valparai are required.")
        self.assertEqual(got["op"], "SELECT")

    def test_plot_two_taxa_restores_union(self):
        raw = {"op": "ANNOTATE", "layer": "Lantana occurrence", "source": {
            "op": "SELECT", "entity": "Lantana occurrence records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Plot the Lantana and teak occurrence records around Valparai.")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(len(got["entity"]), 2)
        self.assertEqual(got["entity"][0], "Lantana occurrence records")
        self.assertEqual(got["entity"][1], "teak occurrence records")

    def test_map_two_taxa_with_present_clause_restores_union(self):
        raw = {"op": "ANNOTATE", "layer": "Lantana occurrence", "source": {
            "op": "SELECT", "entity": "Lantana occurrence records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Map the Lantana and teak occurrence records that are present around Valparai.")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(len(got["entity"]), 2)

    def test_map_all_two_taxa_strips_union_quantifier(self):
        raw = {"op": "SELECT", "entity": "Lantana occurrence records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "Map all Lantana and teak occurrence records around Valparai.")
        self.assertEqual(got["entity"][0], "Lantana occurrence records")
        self.assertEqual(got["entity"][1], "teak occurrence records")

    def test_depict_two_taxa_restores_union(self):
        raw = {"op": "ANNOTATE", "layer": "Lantana occurrence", "source": {
            "op": "SELECT", "entity": "Lantana occurrence records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Depict Lantana and teak occurrence records around Valparai.")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(len(got["entity"]), 2)

    def test_present_located_two_taxa_restores_union(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "teak occurrence records",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Present the Lantana and teak occurrence records that are located around Valparai.")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(len(got["entity"]), 2)

    def test_which_two_taxa_restores_union(self):
        raw = {"op": "RELATE", "relation": "cooccur",
               "left": {"op": "SELECT", "entity": "Lantana occurrence records",
                        "region": {"op": "REGION", "place": "Valparai, India"}, "time": None},
               "right": {"op": "SELECT", "entity": "teak occurrence records",
                         "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Which Lantana and teak occurrence records are found in the vicinity of Valparai?")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(len(got["entity"]), 2)

    def test_recent_bird_request_clears_only_invented_year(self):
        raw = {"op": "SELECT", "entity": "recent bird observations",
               "region": {"op": "REGION", "place": "Valparai, India"},
               "time": {"start": "2024", "end": "2024"}}
        got = sector_semantic_repairs(
            raw, "Show the most recent bird observations that have been recorded in Valparai.")
        self.assertIsNone(got["time"])

    def test_latest_bird_records_normalize_to_recent_contract(self):
        raw = {"op": "SELECT", "entity": "latest bird observation records",
               "region": {"op": "REGION", "place": "Valparai, India"},
               "time": {"start": "2024", "end": "2024"}}
        got = sector_semantic_repairs(
            raw, "Display the latest bird observation records from Valparai.")
        self.assertEqual(got["entity"], "recent bird observations")
        self.assertIsNone(got["time"])

    def test_feasible_add_landcover_is_annotation(self):
        raw = {"op": "ESTIMATE", "method": "feature",
               "target": {"op": "REGION", "place": "Valparai, India"},
               "source": {"op": "SELECT", "entity": "vegetation survey sites",
                          "region": {"op": "REGION", "place": "Valparai, India"},
                          "time": None}}
        got = sector_semantic_repairs(
            raw, "Would it be feasible to add land cover to the vegetation survey sites around Valparai?")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["layer"], "land cover")

    def test_what_ecoregions_include_sites_restores_annotation(self):
        raw = {"op": "SELECT", "entity": "ecoregions",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "What ecoregions include the Anamalai survey sites located near Valparai?")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["layer"], "ecoregion")
        self.assertEqual(got["source"]["entity"], "Anamalai survey sites")

    def test_ecoregion_sites_near_place_uses_near_place_as_region(self):
        raw = {"op": "SELECT", "entity": "Anamalai survey sites",
               "region": {"op": "REGION", "place": "Anamalai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "Which ecoregions encompass the Anamalai survey sites near Valparai?")
        self.assertEqual(got["source"]["region"],
                         {"op": "REGION", "place": "Valparai, India"})

    def test_near_place_capture_stops_before_declarative_tail(self):
        raw = {"op": "SELECT", "entity": "Anamalai survey sites",
               "region": {"op": "REGION", "place": "Anamalai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "The ecoregions containing the Anamalai survey sites near Valparai are to be identified.")
        self.assertEqual(got["source"]["region"],
                         {"op": "REGION", "place": "Valparai, India"})

    def test_near_place_capture_stops_before_located_in(self):
        raw = {"op": "SELECT", "entity": "Anamalai survey sites",
               "region": {"op": "REGION", "place": "Valparai located in"}, "time": None}
        got = sector_semantic_repairs(
            raw, "What ecoregions are the Anamalai survey sites near Valparai located in?")
        self.assertEqual(got["source"]["region"],
                         {"op": "REGION", "place": "Valparai"})

    def test_nominal_yes_no_ndvi_increase_restores_trend(self):
        raw = {"op": "ESTIMATE", "method": "interpolate",
               "target": {"op": "REGION", "place": "Valparai, India"},
               "source": {"op": "SELECT", "entity": "vegetation greenness",
                          "region": {"op": "REGION", "place": "Valparai, India"},
                          "time": None}}
        got = sector_semantic_repairs(raw, "General NDVI increase in Valparai: yes or no?")
        self.assertEqual(got["op"], "COMPARE")
        self.assertEqual(got["how"], "trend_direction")

    def test_going_up_ndvi_restores_trend(self):
        raw = {"op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2018", "end": "2024"}}}
        got = sector_semantic_repairs(raw, "Has NDVI been going up overall in Valparai?")
        self.assertEqual(got["op"], "COMPARE")
        self.assertEqual(got["how"], "trend_direction")

    def test_does_ndvi_increase_restores_trend(self):
        raw = {"op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2018", "end": "2024"}}}
        got = sector_semantic_repairs(raw, "Does NDVI show a general increase in Valparai?")
        self.assertEqual(got["op"], "COMPARE")
        self.assertEqual(got["how"], "trend_direction")

    def test_ndvi_values_routes_as_ndvi(self):
        raw = {"op": "COMPARE", "how": "trend_direction", "left": {
            "op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI values",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2018", "end": "2024"}}}}
        got = sector_semantic_repairs(
            raw, "Did NDVI values in Valparai show a general increase over time?")
        self.assertEqual(got["left"]["source"]["entity"], "NDVI")

    def test_gone_up_ndvi_restores_trend(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(raw, "Has NDVI gone up overall in Valparai?")
        self.assertEqual(got["op"], "COMPARE")

    def test_ecoregion_layer_unwraps_aggregate(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "Anamalai survey sites",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "Which ecoregions hold the Anamalai survey sites close to Valparai?")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["layer"], "ecoregion")

    def test_name_ecoregions_fall_within_restores_annotation(self):
        raw = {"op": "REGION", "place": "Anamalai"}
        got = sector_semantic_repairs(
            raw, "Name the ecoregions that the Anamalai survey sites near Valparai fall within.")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["source"]["entity"], "Anamalai survey sites")
        self.assertEqual(got["source"]["region"]["place"], "Valparai")

    def test_year_leading_three_place_rank_keeps_all_places(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2024", "end": "2024"}}}
        got = sector_semantic_repairs(
            raw, "For 2024 mean NDVI, rank Valparai, Pollachi, and Mysuru from highest to lowest.")
        self.assertEqual(got["op"], "RANK")
        self.assertEqual(len(got["items"]), 3)
        self.assertEqual(got["order"], "desc")
        self.assertTrue(all(item["by"] == "time" for item in got["items"]))

    def test_arrange_three_place_rank_keeps_all_places(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2024", "end": "2024"}}}
        got = sector_semantic_repairs(
            raw, "Arrange Valparai, Pollachi, and Mysuru in descending order based on their 2024 mean NDVI.")
        self.assertEqual(got["op"], "RANK")
        self.assertEqual(len(got["items"]), 3)
        self.assertEqual(got["order"], "desc")

    def test_rank_sites_introduces_places_not_survey_sites(self):
        def wrong_item(place):
            return {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
                "op": "ANNOTATE", "layer": "NDVI", "source": {
                    "op": "SELECT", "entity": "vegetation survey sites",
                    "region": {"op": "REGION", "place": f"{place}, India"},
                    "time": {"start": "2024", "end": "2024"}}}}
        raw = {"op": "RANK", "order": "desc",
               "items": [wrong_item(p) for p in ("Valparai", "Pollachi", "Mysuru")]}
        got = sector_semantic_repairs(
            raw, "Rank the sites Valparai, Pollachi, and Mysuru by 2024 mean NDVI, highest first.")
        self.assertEqual([x["source"]["entity"] for x in got["items"]], ["NDVI"] * 3)
        self.assertTrue(all(x["by"] == "time" for x in got["items"]))

    def test_sort_sites_introduces_places_not_survey_sites(self):
        raw = {"op": "RANK", "order": "desc", "items": [{
            "op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
                "op": "ANNOTATE", "layer": "NDVI", "source": {
                    "op": "SELECT", "entity": "vegetation survey sites",
                    "region": {"op": "REGION", "place": "Valparai, India"},
                    "time": {"start": "2024", "end": "2024"}}}}]}
        got = sector_semantic_repairs(
            raw, "Sort the three sites Valparai, Pollachi, and Mysuru by their 2024 mean NDVI, placing the highest first.")
        self.assertEqual([x["source"]["entity"] for x in got["items"]], ["NDVI"] * 3)

    def test_ecoregion_vicinity_binds_literal_place(self):
        raw = {"op": "SELECT", "entity": "Anamalai survey sites", "region": "?place",
               "time": None}
        got = sector_semantic_repairs(
            raw, "Identify which ecoregions contain the Anamalai survey sites in the vicinity of Valparai.")
        self.assertEqual(got["op"], "ANNOTATE")
        self.assertEqual(got["source"]["region"]["place"], "Valparai")

    def test_near_place_stops_before_situated(self):
        raw = {"op": "SELECT", "entity": "Anamalai survey sites",
               "region": {"op": "REGION", "place": "Valparai situated, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "In which ecoregions are the Anamalai survey sites near Valparai situated?")
        self.assertEqual(got["source"]["region"]["place"], "Valparai, India")

    def test_rank_three_locations_strips_enumeration_prefix(self):
        raw = {"op": "RANK", "order": "desc", "items": [{
            "op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2024", "end": "2024"}}}]}
        got = sector_semantic_repairs(
            raw, "Rank the three locations Valparai, Pollachi, and Mysuru by their 2024 mean NDVI, highest to lowest.")
        self.assertEqual(got["items"][0]["source"]["region"]["place"], "Valparai, India")

    def test_rank_average_ndvi_is_time_mean(self):
        raw = {"op": "RANK", "order": "desc", "items": [{
            "op": "AGGREGATE", "by": "space", "metric": "count", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2024", "end": "2024"}}}]}
        got = sector_semantic_repairs(
            raw, "Order Valparai, Pollachi, and Mysuru by descending 2024 average NDVI.")
        self.assertTrue(all(x["by"] == "time" and x["metric"] == "mean" for x in got["items"]))

    def test_rank_descending_does_not_enter_place_name(self):
        raw = {"op": "RANK", "order": "desc", "items": [{
            "op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2024", "end": "2024"}}}]}
        got = sector_semantic_repairs(
            raw, "Rank Valparai, Pollachi, and Mysuru descending by their 2024 mean NDVI.")
        self.assertEqual(got["items"][2]["source"]["region"]["place"], "Mysuru, India")

    def test_closer_than_conjoined_relation_keeps_both_thresholds_and_anchors(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "RELATE", "relation": "within", "left": {
                "op": "SELECT", "entity": "Lantana records",
                "region": {"op": "REGION", "place": "Valparai, India"}, "time": None},
            "right": {"op": "SELECT", "entity": "elephant records",
                      "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}}
        got = sector_semantic_repairs(
            raw, "How many Lantana records in Valparai are located closer than 1 km to survey sites and farther than 300 m from elephant records?")
        self.assertEqual((got["source"]["relation"], got["source"]["threshold_km"]),
                         ("beyond", 0.3))
        self.assertEqual((got["source"]["left"]["relation"],
                          got["source"]["left"]["threshold_km"]), ("within", 1.0))
        self.assertEqual(got["source"]["left"]["right"]["entity"], "survey sites")
        self.assertEqual(got["source"]["right"]["entity"], "elephant records")

    def test_pull_two_taxa_occurrence_data_restores_union(self):
        raw = {"op": "SELECT", "entity": "Lantana occurrence records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(raw, "Pull Lantana and teak occurrence records near Valparai.")
        self.assertEqual(got["entity"],
                         ["Lantana occurrence records", "teak occurrence records"])
        got = sector_semantic_repairs(raw, "Display Lantana and teak occurrence data near Valparai.")
        self.assertEqual(len(got["entity"]), 2)

    def test_union_located_clause_does_not_require_that_are(self):
        raw = {"op": "SELECT", "entity": "Lantana occurrence records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "Display the Lantana and teak occurrence records located around Valparai.")
        self.assertEqual(len(got["entity"]), 2)

    def test_location_set_within_two_record_sets_restores_cooccurrence(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "RELATE", "relation": "within", "threshold_km": 5.0,
            "left": {"op": "SELECT", "entity": "elephant records",
                     "region": {"op": "REGION", "place": "Valparai, India"}, "time": None},
            "right": {"op": "SELECT", "entity": "Lantana records",
                      "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}}
        got = sector_semantic_repairs(
            raw, "Show the locations where elephant records are within 5 km of Lantana records around Valparai.")
        self.assertEqual(got["op"], "RELATE")
        self.assertEqual((got["relation"], got["threshold_km"]), ("cooccur", 5.0))

    def test_indirect_population_number_remains_unsupported_measure(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "elephants",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "What is the number of elephants in the Valparai population?")
        self.assertEqual(got["op"], "SELECT")
        self.assertEqual(got["entity"], "elephant population")
        self.assertEqual(got["region"]["place"], "Valparai")

    def test_greater_two_place_ndvi_uses_time_mean(self):
        def side(place):
            return {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": place},
                "time": {"start": "2024", "end": "2024"}}}
        raw = {"op": "COMPARE", "how": "difference",
               "left": side("Valparai, India"), "right": side("Pollachi, India")}
        got = sector_semantic_repairs(
            raw, "In 2024, which area, Valparai or Pollachi, had a greater mean NDVI?")
        self.assertEqual(got["left"]["by"], "time")
        self.assertEqual(got["right"]["by"], "time")

    def test_semantic_scorer_rejects_dropped_union_and_relation_grain(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        gold_union = {"op": "SELECT", "entity": ["Lantana records", "teak records"],
                      "region": region, "time": None}
        q = {"gold_shape": ["SELECT"], "gold_ir": gold_union, "expect": "answer"}
        candidate = {"op": "SELECT", "entity": "Lantana occurrence records",
                     "region": region, "time": None}
        execution = {"status": "answer", "value": {"kind": "records", "rows": [{"id": 1}]}}
        self.assertFalse(score(q, candidate, execution)["semantic_fidelity"])

        left = {"op": "SELECT", "entity": "elephant records", "region": region, "time": None}
        right = {"op": "SELECT", "entity": "Lantana records", "region": region, "time": None}
        gold_rel = {"op": "RELATE", "relation": "cooccur", "threshold_km": 5.0,
                    "left": left, "right": right}
        q = {"gold_shape": ["RELATE", "SELECT", "SELECT"], "gold_ir": gold_rel,
             "expect": "answer"}
        candidate = {"op": "AGGREGATE", "by": "space", "metric": "count",
                     "source": {**gold_rel, "relation": "within"}}
        self.assertFalse(score(q, candidate, execution)["semantic_fidelity"])

    def test_semantic_scorer_allows_missing_country_but_not_conflicting_country(self):
        gold = {"op": "SELECT", "entity": "elephant population",
                "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        q = {"gold_shape": ["SELECT"], "gold_ir": gold, "expect": "data_request"}
        execution = {"status": "data_request", "reason": "unsupported_measure"}
        short = {**gold, "region": {"op": "REGION", "place": "Valparai"}}
        conflict = {**gold, "region": {"op": "REGION", "place": "Valparai, Sri Lanka"}}
        self.assertTrue(score(q, short, execution)["semantic_fidelity"])
        self.assertFalse(score(q, conflict, execution)["semantic_fidelity"])

    def test_comparison_synthesis_requires_and_fallback_states_winner(self):
        result = {"status": "answer", "label": "proxy", "value": {
            "kind": "scalar", "value": 0.2, "left_label": "Valparai, India",
            "right_label": "Pollachi, India", "left_value": 0.8, "right_value": 0.6,
            "winner": "Valparai, India"}, "provenance": []}
        bare = "The mean NDVI is 0.2."
        self.assertFalse(score_synthesis("Which place was higher?", result, bare)["states_finding"])
        fallback = _safe_fallback(result)
        self.assertIn("Valparai, India is higher than Pollachi, India", fallback)
        self.assertTrue(score_synthesis("Which place was higher?", result, fallback)["states_finding"])

    def test_differ_between_years_restores_endpoint_difference(self):
        raw = {"op": "COMPARE", "how": "difference", "left": {
            "op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2018", "end": "2024"}}}, "right": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2024", "end": "2024"}}}
        got = sector_semantic_repairs(
            raw, "How much did the NDVI in Valparai differ between 2018 and 2024?")
        self.assertEqual(got["left"]["time"], {"start": "2024", "end": "2024"})
        self.assertEqual(got["right"]["time"], {"start": "2018", "end": "2018"})

    def test_inside_radius_outside_buffer_restores_nested_negation(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "RELATE", "relation": "within",
            "left": {"op": "SELECT", "entity": "Lantana records", "region": region,
                     "time": None},
            "right": {"op": "SELECT", "entity": "survey sites", "region": region,
                      "time": None}}}
        got = sector_semantic_repairs(
            raw, "Count the Lantana records in Valparai that lie inside a 1 km radius of a survey site while being outside a 300 m buffer from elephant records.")
        self.assertEqual((got["source"]["relation"], got["source"]["threshold_km"]),
                         ("beyond", 0.3))
        self.assertEqual((got["source"]["left"]["relation"],
                          got["source"]["left"]["threshold_km"]), ("within", 1.0))

    def test_where_are_records_within_records_is_cooccurrence_output(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "RELATE", "relation": "within", "threshold_km": 5.0,
               "left": {"op": "SELECT", "entity": "elephant records", "region": region,
                        "time": None},
               "right": {"op": "SELECT", "entity": "Lantana records", "region": region,
                         "time": None}}
        got = sector_semantic_repairs(
            raw, "Around Valparai, where are elephant records that lie within 5 km of Lantana records?")
        self.assertEqual(got["relation"], "cooccur")

    def test_declarative_resident_choice_requires_proxy(self):
        raw = {"op": "SELECT", "entity": "?native_tree_type",
               "region": {"op": "REGION", "place": "Mysuru, India"}, "time": None}
        got = sector_semantic_repairs(raw, "A resident of Mysuru choosing native trees is explained.")
        self.assertEqual(got, {"op": "SELECT", "entity": "?proxy",
                               "region": "?place", "time": None})

    def test_retrieve_union_for_area_keeps_both_taxa(self):
        raw = {"op": "SELECT", "entity": "Lantana occurrence records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "Retrieve Lantana and teak occurrence data for the Valparai area.")
        self.assertEqual(len(got["entity"]), 2)

    def test_population_declarative_tail_not_captured_as_place(self):
        raw = {"op": "SELECT", "entity": "elephant population",
               "region": {"op": "REGION", "place": "Valparai is sought"}, "time": None}
        got = sector_semantic_repairs(raw, "The elephant population in Valparai is sought.")
        self.assertEqual(got["region"]["place"], "Valparai")

    def test_semantic_scorer_normalizes_survey_data_grain(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        gold = {"op": "SELECT", "entity": "frog acoustic surveys", "region": region,
                "time": None}
        candidate = {**gold, "entity": "frog acoustic survey data"}
        q = {"gold_shape": ["SELECT"], "gold_ir": gold, "expect": "data_request"}
        execution = {"status": "data_request", "reason": "no_connector"}
        self.assertTrue(score(q, candidate, execution)["semantic_fidelity"])

    def test_need_to_see_union_keeps_both_taxa(self):
        raw = {"op": "SELECT", "entity": "Lantana occurrence records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "I need to see Lantana and teak occurrence records around Valparai.")
        self.assertEqual(len(got["entity"]), 2)

    def test_show_where_records_occur_within_is_cooccurrence(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "RELATE", "relation": "within", "threshold_km": 5.0,
               "left": {"op": "SELECT", "entity": "elephant records", "region": region,
                        "time": None},
               "right": {"op": "SELECT", "entity": "Lantana records", "region": region,
                         "time": None}}
        got = sector_semantic_repairs(
            raw, "Can you show where elephant records occur within 5 km of Lantana records around Valparai?")
        self.assertEqual(got["relation"], "cooccur")

    def test_time_filtered_total_count_is_not_a_time_series(self):
        raw = {"op": "AGGREGATE", "by": "time", "metric": "count", "source": {
            "op": "SELECT", "entity": "Lantana occurrence records",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2021", "end": "2025"}}}
        got = sector_semantic_repairs(
            raw, "From 2021 through 2025 in Valparai, how many Lantana occurrence records were documented?")
        self.assertEqual(got["by"], "space")

    def test_union_capture_drops_command_scaffolding(self):
        raw = {"op": "SELECT", "entity": "Lantana occurrence records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "I need to see where Lantana and teak have been recorded around Valparai.")
        self.assertEqual(got["entity"][0], "Lantana occurrence records")
        got = sector_semantic_repairs(
            raw, "Retrieve Lantana and teak presence records in the vicinity of Valparai.")
        self.assertEqual(got["entity"][0], "Lantana occurrence records")

    def test_compound_anchor_drops_trailing_place_phrase(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "Lantana records", "region": region, "time": None}}
        got = sector_semantic_repairs(
            raw, "What is the tally of Lantana records found inside a 1 km radius of survey sites but outside 300 m from elephant records in Valparai?")
        self.assertEqual(got["source"]["right"]["entity"], "elephant records")

    def test_nominal_selection_reason_requires_proxy(self):
        raw = {"op": "SELECT", "entity": "native tree selection",
               "region": {"op": "REGION", "place": "Mysuru, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "Native tree selection by Mysuru inhabitants — reason?")
        self.assertEqual(got["entity"], "?proxy")

    def test_sequence_and_then_rank_lists_use_time_mean(self):
        raw = {"op": "RANK", "order": "desc", "items": []}
        for question in (
            "Sequence Valparai, Pollachi, Mysuru by 2024 mean NDVI from highest to lowest.",
            "Descending-order rank Valparai then Pollachi then Mysuru by 2024 mean NDVI.",
        ):
            got = sector_semantic_repairs(raw, question)
            self.assertEqual(len(got["items"]), 3)
            self.assertTrue(all(item["by"] == "time" for item in got["items"]))

    def test_delta_ndvi_restores_endpoint_change(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
            "op": "ANNOTATE", "layer": "delta NDVI", "source": {
                "op": "SELECT", "entity": "Valparai",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2018", "end": "2024"}}}}
        got = sector_semantic_repairs(raw, "Delta NDVI in Valparai from 2018 to 2024?")
        self.assertEqual(got["op"], "COMPARE")

    def test_place_prefix_is_not_part_of_anamalai_site_entity(self):
        raw = {"op": "ANNOTATE", "layer": "elevation", "source": {
            "op": "SELECT", "entity": "Valparai Anamalai survey sites",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(raw, "Mean elevation of the Valparai Anamalai survey sites?")
        self.assertEqual(got["source"]["entity"], "Anamalai survey sites")

    def test_robust_ecosystem_requires_indicator(self):
        raw = {"op": "ESTIMATE", "method": "envelope",
               "target": {"op": "REGION", "place": "Valparai, India"},
               "source": {"op": "SELECT", "entity": "Valparai ecosystem",
                          "region": {"op": "REGION", "place": "Valparai, India"},
                          "time": None}}
        got = sector_semantic_repairs(raw, "How robust is the Valparai ecosystem?")
        self.assertEqual(got["entity"], "?indicator")

    def test_not_within_second_compound_anchor_restores_beyond(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
            "op": "SELECT", "entity": "Lantana records", "region": region, "time": None}}
        got = sector_semantic_repairs(
            raw, "Count of Lantana records in Valparai inside 1 km of survey sites yet not within 300 m of elephant records?")
        self.assertEqual(got["source"]["relation"], "beyond")
        self.assertEqual(got["source"]["left"]["relation"], "within")

    def test_enumerate_and_tabulate_keep_record_set_grain(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        for question, entity in (
            ("Recent bird observations in Valparai — enumerate.", "recent bird observations"),
            ("Frog acoustic surveys in Valparai — tabulate.", "frog acoustic surveys"),
        ):
            raw = {"op": "AGGREGATE", "by": "space", "metric": "count", "source": {
                "op": "SELECT", "entity": entity, "region": region, "time": None}}
            self.assertEqual(sector_semantic_repairs(raw, question)["op"], "SELECT")

    def test_nominal_density_restores_aggregate(self):
        raw = {"op": "REGION", "place": "Valparai, India"}
        got = sector_semantic_repairs(
            raw, "Valparai bounding box, documented Lantana records density, what is it?")
        self.assertEqual((got["op"], got["metric"]), ("AGGREGATE", "density"))

    def test_nominal_no_site_within_restores_beyond(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "RANK", "order": "desc", "items": [{
            "op": "AGGREGATE", "by": "space", "metric": "count", "source": {
                "op": "SELECT", "entity": "Lantana records", "region": region, "time": None}}]}
        got = sector_semantic_repairs(
            raw, "Lantana records in Valparai, with no survey site within 300 metres, which?")
        self.assertEqual((got["op"], got["relation"], got["threshold_km"]),
                         ("RELATE", "beyond", 0.3))

    def test_indian_locality_is_literal_india_presence(self):
        raw = {"op": "RELATE", "relation": "within", "left": {
            "op": "SELECT", "entity": "green cat snake", "region": "?place", "time": None},
            "right": {"op": "SELECT", "entity": "survey sites", "region": "?place",
                      "time": None}}
        got = sector_semantic_repairs(
            raw, "Is green cat snake presence documented in any Indian locality?")
        self.assertEqual((got["op"], got["metric"]), ("AGGREGATE", "presence"))
        self.assertEqual(got["source"]["region"]["place"], "India")

    def test_terse_two_place_ndvi_comparison_keeps_both_places(self):
        raw = {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2024", "end": "2024"}}}
        got = sector_semantic_repairs(raw, "2024 mean NDVI, Valparai or Pollachi higher?")
        self.assertEqual(got["op"], "COMPARE")
        self.assertEqual(got["right"]["source"]["region"]["place"], "Pollachi")
        self.assertTrue(all(got[side]["by"] == "time" for side in ("left", "right")))

    def test_bigger_two_place_ndvi_comparison_uses_time_mean(self):
        def side(place):
            return {"op": "AGGREGATE", "by": "space", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": place},
                "time": {"start": "2024", "end": "2024"}}}
        raw = {"op": "COMPARE", "how": "difference",
               "left": side("Valparai, India"), "right": side("Pollachi, India")}
        got = sector_semantic_repairs(
            raw, "In 2024, was the mean NDVI bigger in Valparai or in Pollachi?")
        self.assertTrue(all(got[side]["by"] == "time" for side in ("left", "right")))

    def test_place_prefix_is_not_part_of_greenness_series(self):
        raw = {"op": "COMPARE", "how": "trend_direction", "left": {
            "op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
                "op": "SELECT", "entity": "Valparai vegetation greenness",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2018", "end": "2024"}}}}
        got = sector_semantic_repairs(
            raw, "Valparai vegetation greenness, 2018 to 2024: rising or falling?")
        self.assertEqual(got["left"]["source"]["entity"], "vegetation greenness")

    def test_need_records_keeps_record_set_output_grain(self):
        raw = {"op": "AGGREGATE", "by": "time", "metric": "count", "source": {
            "op": "SELECT", "entity": "bird observation records",
            "region": {"op": "REGION", "place": "Valparai, India"},
            "time": {"start": "2020-01-01", "end": "2020-01-31"}}}
        got = sector_semantic_repairs(
            raw, "I need the bird observation records for Valparai that fall within January 2020.")
        self.assertEqual(got["op"], "SELECT")

    def test_fronted_years_changed_restores_ndvi_endpoints(self):
        raw = {"op": "COMPARE", "how": "difference", "left": {
            "op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2018", "end": "2024"}}}, "right": {
            "op": "SELECT", "entity": "NDVI",
            "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}}
        got = sector_semantic_repairs(
            raw, "2018 to 2024, NDVI in Valparai changed by how much?")
        self.assertEqual(got["left"]["time"], {"start": "2024", "end": "2024"})
        self.assertEqual(got["right"]["time"], {"start": "2018", "end": "2018"})

    def test_nominal_published_vegetation_sites_restores_select(self):
        raw = {"op": "REGION", "place": "Valparai, India"}
        got = sector_semantic_repairs(raw, "Valparai: the published vegetation survey sites.")
        self.assertEqual(got, {"op": "SELECT", "entity": "vegetation survey sites",
                               "region": raw, "time": None})

    def test_terse_upward_trend_clears_invented_period(self):
        raw = {"op": "COMPARE", "how": "trend_direction", "left": {
            "op": "AGGREGATE", "by": "time", "metric": "mean", "source": {
                "op": "SELECT", "entity": "NDVI",
                "region": {"op": "REGION", "place": "Valparai, India"},
                "time": {"start": "2018", "end": "2024"}}}}
        got = sector_semantic_repairs(raw, "NDVI in Valparai generally up?")
        self.assertIsNone(got["left"]["source"]["time"])

    def test_documentation_framed_green_cat_snake_presence(self):
        raw = {"op": "SELECT", "entity": "green cat snake",
               "region": {"op": "REGION", "place": "India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "What documentation is available for green cat snake presence in India?")
        self.assertEqual((got["op"], got["metric"]), ("AGGREGATE", "presence"))

    def test_less_than_record_relation_is_cooccurrence(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "RELATE", "relation": "within", "threshold_km": 5.0,
               "left": {"op": "SELECT", "entity": "elephant records", "region": region,
                        "time": None},
               "right": {"op": "SELECT", "entity": "Lantana records", "region": region,
                         "time": None}}
        got = sector_semantic_repairs(
            raw, "In the region around Valparai, where are elephant records situated less than 5 km from Lantana records?")
        self.assertEqual((got["relation"], got["threshold_km"]), ("cooccur", 5.0))

    def test_literal_relation_threshold_is_restored(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        relation = {"op": "RELATE", "relation": "within",
               "left": {"op": "SELECT", "entity": "Lantana records", "region": region,
                        "time": None},
               "right": {"op": "SELECT", "entity": "vegetation survey sites",
                         "region": region, "time": None}}
        raw = {"op": "AGGREGATE", "by": "space", "metric": "count",
               "source": relation}
        got = sector_semantic_repairs(
            raw, "For Valparai, which Lantana records have a vegetation survey site located within 1 km of them?")
        self.assertEqual(got["threshold_km"], 1.0)

    def test_grounded_place_prefix_is_removed_from_lantana_entity(self):
        region = {"op": "REGION", "place": "Valparai, India"}
        raw = {"op": "RELATE", "relation": "beyond", "threshold_km": 0.3,
               "left": {"op": "SELECT", "entity": "Valparai Lantana records",
                        "region": region, "time": None},
               "right": {"op": "SELECT", "entity": "survey sites", "region": region,
                         "time": None}}
        got = sector_semantic_repairs(
            raw, "Among Valparai Lantana records, which ones are not within 300 metres of any survey site?")
        self.assertEqual(got["left"]["entity"], "Lantana records")

    def test_occurrence_records_of_both_taxa_restores_union(self):
        raw = {"op": "SELECT", "entity": "Lantana occurrence records",
               "region": {"op": "REGION", "place": "Valparai, India"}, "time": None}
        got = sector_semantic_repairs(
            raw, "For the area around Valparai, retrieve occurrence records of both Lantana and teak.")
        self.assertEqual(len(got["entity"]), 2)

    def test_colon_after_near_place_binds_ecoregion_source(self):
        raw = {"op": "ANNOTATE", "layer": "ecoregion", "source": {
            "op": "SELECT", "entity": "Anamalai survey sites", "region": "?place",
            "time": None}}
        got = sector_semantic_repairs(
            raw, "Ecoregions containing the Anamalai survey sites near Valparai: which ones?")
        self.assertEqual(got["source"]["region"]["place"], "Valparai")


if __name__ == "__main__":
    unittest.main()
