import os
import sys
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hermes_bench"))

import engine as E


class BenchmarkEngineTests(unittest.TestCase):
    def test_composed_relation_is_never_replaced_by_single_selected_dataset(self):
        relation = {
            "op": "RELATE", "relation": "cooccur",
            "left": {"op": "SELECT", "entity": "elephant",
                     "region": "?place", "time": None},
            "right": {"op": "SELECT", "entity": "cormorant",
                      "region": "?place", "time": None},
        }
        selected = [{"entity": "EBTL evidence summary", "kind": "SELECT",
                     "selected": True}]
        bound = E._bind_single_capability(relation, selected)
        self.assertEqual(bound, relation)
        self.assertEqual(bound["op"], "RELATE")

    def test_composed_relation_survives_operator_data_and_region_ingredients(self):
        relation = {
            "op": "RELATE", "relation": "cooccur",
            "left": {"op": "SELECT", "entity": "elephant",
                     "region": {"op": "REGION", "place": "dry-Deccan donor belt"},
                     "time": None},
            "right": {"op": "SELECT", "entity": "cormorant",
                      "region": {"op": "REGION", "place": "dry-Deccan donor belt"},
                      "time": None},
        }
        selected = [
            {"entity": "spatial relation between occurrence records", "kind": "RELATE operator",
             "binding": "operator", "ops": ["RELATE"], "selected": True},
            {"entity": "taxon occurrence records", "kind": "SELECT",
             "binding": "compiler_entity", "selected": True},
            {"entity": "declared EBTL donor belt", "kind": "REGION support",
             "binding": "region", "place": "dry-Deccan donor belt", "selected": True},
        ]
        bound = E._bind_single_capability(relation, selected)
        self.assertEqual(bound, relation)
        self.assertEqual(bound["op"], "RELATE")

    def test_verifier_admits_minimal_multi_capability_composition(self):
        names = ["spatial relation between occurrence records", "taxon occurrence records",
                 "declared EBTL donor belt"]
        replies = iter([
            __import__("json").dumps({"mode": "execute", "entities": names}),
            __import__("json").dumps({"entities": names}),
        ])
        with mock.patch.object(E, "chat", side_effect=lambda *args, **kwargs: next(replies)):
            selected, _, _, mode = E._select_capabilities(
                "Compare elephant and cormorant occurrence proximity across the donor belt.",
                "qwen9b>deepseekv4", [])
        self.assertEqual(mode, "execute")
        self.assertEqual([item["entity"] for item in selected], names)

    def test_selector_observer_exposes_proposal_then_verified_selection(self):
        name = "EBTL bird inventory"
        replies = iter([
            __import__("json").dumps({"mode": "execute", "entities": [name]}),
            __import__("json").dumps({"entities": [name]}),
        ])
        stages = []
        with mock.patch.object(E, "chat", side_effect=lambda *args, **kwargs: next(replies)):
            E._select_capabilities(
                "What birds are documented at EBTL?", "qwen9b>deepseekv4", [],
                observer=lambda stage, payload: stages.append((stage, payload)))
        self.assertEqual([stage for stage, _ in stages],
                         ["capability_selected", "capability_verified"])
        self.assertEqual(stages[0][1]["model"], "qwen9b")
        self.assertEqual(stages[1][1]["model"], "deepseekv4")
        self.assertIn("capability_verifier:retained", " ".join(stages[1][1]["events"]))

    def test_regional_composition_prunes_incompatible_site_only_card(self):
        names = ["EBTL elephant evidence", "taxon occurrence records",
                 "spatial relation between occurrence records", "declared EBTL donor belt"]
        raw = __import__("json").dumps({"mode": "execute", "entities": names})
        with mock.patch.object(E, "chat", return_value=raw):
            selected, _, _, _ = E._select_capabilities(
                "Compare named taxa occurrence records in the donor region.", "qwen9b", [])
        self.assertEqual([item["entity"] for item in selected], [
            "taxon occurrence records", "spatial relation between occurrence records",
            "declared EBTL donor belt"])

    def test_buffer_relation_curriculum_keeps_search_and_pairwise_distances_separate(self):
        selected = [
            {"entity": "taxon occurrence records", "binding": "compiler_entity",
             "kind": "SELECT", "selected": True},
            {"entity": "spatial relation between occurrence records", "binding": "operator",
             "kind": "RELATE operator", "ops": ["RELATE"], "selected": True},
            {"entity": "buffered search region", "binding": "operator",
             "kind": "REGION operator", "ops": ["BUFFER"], "selected": True},
        ]
        ir = E._selected_examples(selected)[0]["ir"]
        self.assertEqual((ir["op"], ir["threshold_km"]), ("RELATE", 5.0))
        self.assertEqual(ir["left"]["region"]["op"], "BUFFER")
        self.assertEqual(ir["left"]["region"]["radius_km"], 25.0)

    def test_buffer_contract_never_copies_support_between_relation_operands(self):
        buffer_node = {"op": "BUFFER", "radius_km": 100.0,
                       "source": {"op": "REGION", "place": "EBTL"}}
        relation = {"op": "RELATE", "relation": "within", "threshold_km": 10.0,
                    "left": {"op": "SELECT", "entity": "cobra", "region": buffer_node,
                             "time": None},
                    "right": {"op": "SELECT", "entity": "elephant",
                              "region": {"op": "REGION", "place": "EBTL"}, "time": None}}
        selected = [{"entity": "buffered search region", "binding": "operator",
                     "ops": ["BUFFER"], "scope_policy": "shared_across_relation_operands",
                     "selected": True}]
        bound = E._bind_single_capability(relation, selected)
        self.assertEqual(bound["right"]["region"], {"op": "REGION", "place": "EBTL"})
        self.assertEqual(bound["threshold_km"], 10.0)

    def test_selected_operator_contract_projects_non_executable_metadata(self):
        estimate = {"op": "ESTIMATE", "method": "feature", "method_gate": "environmental",
                    "source": {"op": "SELECT", "entity": "elephant",
                               "region": "?donor", "time": None},
                    "target": "?target"}
        selected = [{"entity": "regional transfer", "binding": "operator",
                     "ops": ["ESTIMATE"], "selected": True}]
        bound = E._bind_single_capability(estimate, selected)
        self.assertNotIn("method_gate", bound)
        self.assertEqual(bound["op"], "ESTIMATE")

    def test_relation_proxy_audit_rejects_ungated_interaction_claim(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "proxy", "value": {
                "kind": "records", "grain": "occurrence-proximity-relation",
                "rows": [], "source": "relation", "left_record_count": 10,
                "right_record_count": 12, "matched_left_count": 3}, "provenance": []}}
        bad = "Proxy result: the species interact in this habitat."
        good = "Proxy result: three occurrence records were nearby; this does not establish interaction."
        self.assertFalse(E.audit_response("Are they related?", compiled, bad)["interaction_boundary"])
        self.assertTrue(E.audit_response("Are they related?", compiled, good)["interaction_boundary"])

    def test_suitability_fraction_cannot_become_presence_probability(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "modelled", "provenance": [], "value": {
                "kind": "field", "grain": "target-bbox-suitability-fraction",
                "measure_field": "suitability_fraction", "unit": "fraction",
                "rows": [{"suitability_fraction": 0.047}],
                "source": "AlphaEarth RF"}}}
        bad = ("The modelled suitability fraction is 0.047; this low value suggests limited "
               "potential presence.")
        good = ("The modelled suitability fraction is 0.047: the fraction of target analysis "
                "cells classified suitable. It is not a calibrated probability of presence.")
        self.assertFalse(E.audit_response("What is the estimate?", compiled, bad)[
            "suitability_boundary"])
        self.assertTrue(E.audit_response("What is the estimate?", compiled, good)[
            "suitability_boundary"])
        rendered = E.deterministic_render("What is the estimate?", compiled)
        self.assertIn("target analysis cells", rendered)
        self.assertIn("not a calibrated occurrence probability", rendered)
        self.assertTrue(E.audit_response("What is the estimate?", compiled, rendered)["passed"])

    def test_bbox_approximation_must_survive_response(self):
        support = {"name": "10 km buffer around X", "bbox": [0, 1, 0, 1],
                   "method": "bbox-approx", "approximate": True}
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "proxy", "provenance": [], "value": {
                "kind": "records", "grain": "occurrence-proximity-relation", "rows": [],
                "left_record_count": 10, "right_record_count": 12,
                "matched_left_count": 3, "matched_right_count": 2,
                "left_region": support, "right_region": support}}}
        bad = "Proxy result: three records had a nearby counterpart in the 10 km area."
        good = ("Proxy result: three records had a nearby counterpart; the search support is an "
                "approximate bbox, not an exact radius polygon.")
        self.assertFalse(E.audit_response("Compare them.", compiled, bad)[
            "approximate_support_boundary"])
        self.assertTrue(E.audit_response("Compare them.", compiled, good)[
            "approximate_support_boundary"])

    def test_declared_composite_capability_dominates_included_leaf(self):
        raw = ('{"mode":"execute","entities":["arachnids",'
               '"EBTL arachnid transfer evidence"]}')
        with mock.patch.object(E, "chat", return_value=raw):
            selected, _, events, mode = E._select_capabilities(
                "Start local, then apply the regional environmental gates.", "qwen9b", [])
        self.assertEqual(mode, "execute")
        self.assertEqual([item["entity"] for item in selected],
                         ["EBTL arachnid transfer evidence"])
        self.assertIn("capability_selector:mode:execute", events)

    def test_verifier_can_replace_broad_capability_with_specific_catalog_capability(self):
        replies = iter([
            '{"mode":"execute","entities":["snakes"]}',
            '{"entities":["EBTL cobra inventory"]}',
        ])
        with mock.patch.object(E, "chat", side_effect=lambda *args, **kwargs: next(replies)):
            selected, _, events, mode = E._select_capabilities(
                "Which documented cobra is listed, and is king cobra listed?",
                "qwen9b>deepseekv4", [])
        self.assertEqual(mode, "execute")
        self.assertEqual([item["entity"] for item in selected], ["EBTL cobra inventory"])
        self.assertIn("capability_verifier:reselected:EBTL cobra inventory", events)

    def test_first_turn_cannot_synthesize_empty_history(self):
        replies = iter([
            '{"mode":"synthesize_history","entities":[]}',
            '{"mode":"execute","entities":["EBTL evidence summary"]}',
        ])
        with mock.patch.object(E, "chat", side_effect=lambda *args, **kwargs: next(replies)):
            selected, _, _, mode = E._select_capabilities(
                "Give a new colleague the strongest facts and gaps.", "qwen9b", [])
        self.assertEqual(mode, "execute")
        self.assertEqual([item["entity"] for item in selected], ["EBTL evidence summary"])

    def test_single_clarification_candidate_executes(self):
        raw = '{"mode":"clarify","entities":["EBTL bird inventory"]}'
        with mock.patch.object(E, "chat", return_value=raw):
            selected, _, _, mode = E._select_capabilities(
                "Can this bird list show year-round richness?", "qwen9b", [])
        self.assertEqual(mode, "execute")
        self.assertEqual([item["entity"] for item in selected], ["EBTL bird inventory"])

    def test_verifier_failure_uses_constrained_selector_fallback(self):
        replies = [
            '{"mode":"execute","entities":["historical fire exposure",'
            '"EBTL soil dryness evidence"]}',
            RuntimeError("verifier unavailable"),
            '{"entities":["historical fire exposure"]}',
        ]

        def answer(*args, **kwargs):
            item = replies.pop(0)
            if isinstance(item, Exception):
                raise item
            return item

        with mock.patch.object(E, "chat", side_effect=answer):
            selected, _, events, _ = E._select_capabilities(
                "Give the fire proxy and name missing fuel measurements.",
                "qwen9b>deepseekv4", [])
        self.assertEqual([item["entity"] for item in selected],
                         ["historical fire exposure"])
        self.assertIn("capability_verifier:fallback_selector:historical fire exposure", events)

    def test_empty_verifier_disagreement_is_semantically_adjudicated(self):
        replies = iter([
            '{"mode":"execute","entities":["EBTL arachnid transfer evidence"]}',
            '{"entities":[]}',
            '{"entities":["EBTL arachnid transfer evidence"]}',
        ])
        with mock.patch.object(E, "chat", side_effect=lambda *args, **kwargs: next(replies)):
            selected, _, events, _ = E._select_capabilities(
                "Show the regional candidate transfer gates and rejected candidates.",
                "qwen9b>deepseekv4", [])
        self.assertEqual([item["entity"] for item in selected],
                         ["EBTL arachnid transfer evidence"])
        self.assertIn(
            "capability_verifier:disagreement_adjudicated:EBTL arachnid transfer evidence",
            events)

    def test_empty_verifier_disagreement_can_remain_unsupported(self):
        replies = iter([
            '{"mode":"execute","entities":["EBTL evidence summary"]}',
            '{"entities":[]}',
        ])
        with mock.patch.object(E, "chat", side_effect=lambda *args, **kwargs: next(replies)):
            selected, _, events, _ = E._select_capabilities(
                "Compare restoration jobs and crop-loss outcomes.",
                "qwen9b>deepseekv4", [])
        self.assertEqual(selected, [])
        self.assertIn("capability_verifier:empty_atomic_failed_closed", events)

    def test_subject_only_capability_does_not_answer_requested_interaction(self):
        replies = iter([
            '{"mode":"execute","entities":["EBTL elephant evidence"]}',
            '{"entities":[]}',
        ])
        with mock.patch.object(E, "chat", side_effect=lambda *args, **kwargs: next(replies)):
            selected, _, _, _ = E._select_capabilities(
                "Do the animals move through the named plant or avoid it?",
                "qwen9b>deepseekv4", [])
        self.assertEqual(selected, [])

    def test_conversation_brief_has_separate_bounded_length_policy(self):
        compiled = {"dialogue_mode": "synthesize_history", "execution": {
            "status": "answer", "label": "mixed", "value": {
                "kind": "conversation_evidence", "rows": [], "source": "audited history"},
            "provenance": []}}
        answer = " ".join(["evidence"] * 280)
        self.assertTrue(E.audit_response("Give me a brief.", compiled, answer)["length"])

    def test_list_ordinals_are_not_audited_as_factual_numbers(self):
        compiled = {"dialogue_mode": "synthesize_history", "execution": {
            "status": "answer", "label": "mixed", "value": {
                "kind": "conversation_evidence", "rows": [], "source": "audited history"},
            "provenance": []}}
        answer = "Priorities are (1) repeat survey, (2) plot comparison, and (3) interviews."
        self.assertTrue(E.audit_response("Give three priorities.", compiled, answer)["no_new_numbers"])

    def test_internal_hole_reason_is_not_user_facing(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "data_request", "reason": "unbound_holes", "detail": {},
            "provenance": []}}
        audit = E.audit_response(
            "What is missing?", compiled,
            "The unbound_holes error means measurements are missing and need collection.")
        self.assertFalse(audit["no_internal_leak"])

    def test_deterministic_data_request_hides_internal_reason(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "data_request", "reason": "unbound_holes",
            "detail": {"ask": "collect plot measurements"}, "provenance": []}}
        answer = E.deterministic_render("Can we compare treatments?", compiled)
        self.assertNotIn("unbound_holes", answer)
        self.assertIn("DATA REQUEST", answer)
        self.assertTrue(E.audit_response("Can we compare treatments?", compiled, answer)["passed"])

    def test_audited_history_preserves_local_transfer_boundary(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "observed", "provenance": [], "value": {
                "kind": "records", "source": "licensed occurrences",
                "rows": [{"scientific_name": "Observed spider"}],
                "assessments": [{"species": "Observed spider", "locally_observed": True,
                                 "transfer_admissible": False,
                                 "feature_gate": {"pass": True}}]}}}
        entry = E.audited_history_entry("What spiders?", compiled)
        assessment = entry["facts"]["assessments"][0]
        self.assertTrue(assessment["locally_observed"])
        self.assertFalse(assessment["transfer_admissible"])

    def test_conversation_audit_rejects_local_species_presented_for_transfer(self):
        compiled = {"dialogue_mode": "synthesize_history", "execution": {
            "status": "answer", "label": "mixed", "provenance": [], "value": {
                "kind": "conversation_evidence", "source": "audited history", "rows": [{
                    "question": "What spiders?", "status": "answer", "label": "observed",
                    "summary": "One local record.", "facts": {"assessments": [{
                        "species": "Observed spider", "locally_observed": True,
                        "transfer_admissible": False}]}}]}}}
        bad = "Observed spider passes the environmental gates for transfer."
        good = "Observed spider passed both gates but remains observed rather than a transfer."
        self.assertFalse(E.audit_response("Brief me.", compiled, bad)["history_boundary"])
        self.assertTrue(E.audit_response("Brief me.", compiled, good)["history_boundary"])
        repaired = E._repair_history_boundary(E.response_pack(compiled), bad)
        self.assertIn("locally observed", repaired)
        self.assertIn("admitted no regional transfer candidate", repaired)
        self.assertTrue(E.audit_response("Brief me.", compiled, repaired)["history_boundary"])

    def test_conversation_audit_rejects_local_species_as_regional_model(self):
        compiled = {"dialogue_mode": "synthesize_history", "execution": {
            "status": "answer", "label": "mixed", "provenance": [], "value": {
                "kind": "conversation_evidence", "source": "audited history", "rows": [{
                    "status": "answer", "label": "observed", "facts": {"assessments": [{
                        "species": "Observed spider", "locally_observed": True,
                        "transfer_admissible": False}]}}]}}}
        answer = "Regional models suggest Observed spider is compatible."
        self.assertFalse(E.audit_response("Brief me.", compiled, answer)["history_boundary"])

    def test_single_survey_cannot_confirm_ecological_absence(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "observed", "value": {"kind": "records", "rows": []},
            "provenance": []}}
        bad = "Survey next season to confirm the absence of the species."
        good = "Survey next season and report detections and non-detections under that effort."
        caution = "A short survey does not prove absence and cannot rule out undetected presence."
        self.assertFalse(E.audit_response("What next?", compiled, bad)["absence_boundary"])
        self.assertTrue(E.audit_response("What next?", compiled, good)["absence_boundary"])
        self.assertTrue(E.audit_response("What next?", compiled, caution)["absence_boundary"])

    def test_internal_terms_are_sanitized_without_losing_data_request_design(self):
        raw = ("The current audited result is a `data_request` caused by `unbound_holes`. "
               "Compare seedling survival in paired plots.")
        clean = E.sanitize_user_answer(raw)
        self.assertNotIn("audited result", clean)
        self.assertNotIn("data_request", clean)
        self.assertNotIn("unbound_holes", clean)
        self.assertIn("paired plots", clean)

    def test_positive_absence_claim_is_rewritten_as_effort_bounded_detection(self):
        clean = E.sanitize_user_answer(
            "Survey to confirm the presence or absence of candidate plants.")
        self.assertIn("record detections and non-detections", clean)
        self.assertNotIn("confirm", clean)

    def test_declared_threshold_cannot_be_replaced_by_observed_fraction(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "modelled", "provenance": [], "value": {
                "kind": "records", "rows": [], "gate": {
                    "target_in_envelope_fraction": 1.0,
                    "target_in_envelope_fraction_threshold": 0.8}}}}
        bad = ("The modelled gate requires a target_in_envelope_fraction of 1.0.")
        good = ("The modelled gate requires a target_in_envelope_fraction of at least 0.8; "
                "the observed fraction was 1.0.")
        self.assertFalse(E.audit_response("What is the gate?", compiled, bad)["threshold_boundary"])
        self.assertTrue(E.audit_response("What is the gate?", compiled, good)["threshold_boundary"])

    def test_occurrence_record_count_cannot_become_named_taxon_count(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "observed", "provenance": [], "value": {
                "kind": "records", "rows": [], "regional_inventory": {
                    "deduplicated_records": 58,
                    "named_species": [f"Species {i}" for i in range(31)]}}}}
        bad = "The regional query returned 58 additional named species."
        good = "The regional query returned 58 records spanning 31 named taxa."
        self.assertFalse(E.audit_response("What was returned?", compiled, bad)["count_grain"])
        self.assertTrue(E.audit_response("What was returned?", compiled, good)["count_grain"])

    def test_unknown_local_interaction_cannot_become_impossibility(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "modelled", "provenance": [], "value": {
                "kind": "records", "rows": [], "source_metadata": {
                    "local_interaction_admissible": False}}}}
        bad = "The birds cannot act as dispersers at the site."
        good = "The local bird-plant interaction is unknown and needs direct observation."
        self.assertFalse(E.audit_response("Do they interact?", compiled, bad)["interaction_boundary"])
        self.assertTrue(E.audit_response("Do they interact?", compiled, good)["interaction_boundary"])

    def test_explicit_conversation_brief_uses_audited_history_not_invented_ir(self):
        history = [
            {"role": "user", "content": "What did the survey find?"},
            {"role": "assistant", "content": "AUDITED EVIDENCE: " +
             '{"status":"answer","label":"observed","reason":null,'
             '"summary":"Observed result: 4 evidence records."}'},
        ]
        selection = ('{"mode":"synthesize_history","entities":[]}')
        with mock.patch.object(E, "chat", return_value=selection):
            compiled = E.compile_turn(
                "Give me a short brief from this conversation.",
                "qwen9b@qwen2b", history)
        self.assertEqual(compiled["dialogue_mode"], "synthesize_history")
        self.assertIsNone(compiled["ir"])
        self.assertEqual(compiled["execution"]["status"], "answer")
        self.assertEqual(compiled["execution"]["value"]["rows"][0]["label"], "observed")

    def test_failed_outer_operation_does_not_expose_upstream_fact_provenance(self):
        compiled = {"execution": {
            "status": "data_request", "reason": "no_connector",
            "detail": {"hint": "unsupported layer"},
            "provenance": [{"tool": "upstream", "species": "Invented bait"}],
        }}
        self.assertEqual(E.response_pack(compiled)["provenance"], [])

    def test_deterministic_responder_observer_exposes_pack_then_audit(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "observed", "provenance": [],
            "value": {"kind": "records", "rows": [], "source": "test source"}}}
        stages = []
        rendered = E.render_turn(
            "What was found?", compiled, "deterministic", [],
            observer=lambda stage, payload: stages.append((stage, payload)))
        self.assertEqual([stage for stage, _ in stages],
                         ["response_preview", "response_complete"])
        self.assertEqual(stages[0][1]["model"], "deterministic")
        self.assertEqual(stages[1][1]["audit"], rendered["audit"])

    def test_local_responder_plan_paragraphs_are_removed_at_both_edges(self):
        raw = ("The user is asking for the inventory. Let me organize it.\n\n"
               "Three snakes were encountered during the survey.\n\n"
               "I should present this clearly.")
        self.assertEqual(E.strip_reasoning(raw),
                         "Three snakes were encountered during the survey.")

    def test_response_audit_rejects_plan_narration(self):
        compiled = {"dialogue_mode": "execute", "execution": {
            "status": "answer", "label": "observed", "provenance": [],
            "value": {"kind": "records", "rows": [], "source": "test source"}}}
        audit = E.audit_response(
            "What was found?", compiled,
            "The user is asking what was found. Let me organize the answer.", [])
        self.assertFalse(audit["no_plan_narration"])


if __name__ == "__main__":
    unittest.main()
