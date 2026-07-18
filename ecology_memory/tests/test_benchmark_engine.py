import os
import sys
import unittest
from unittest import mock


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "hermes_bench"))

import engine as E


class BenchmarkEngineTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
