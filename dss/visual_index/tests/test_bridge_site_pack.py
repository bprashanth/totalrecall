import contextlib
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from dss.visual_index.build import Builder
from dss.visual_index.cooccurrence_service import CooccurrenceService
from dss.visual_index.result_service import ResultService
from ecology_memory.integration.codex_native import server
from ecology_memory.integration.codex_native import setup_idlisseus


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai"
LIVELIHOODS = ROOT / "dss" / "sites" / "valparai_livelihoods"


class BridgeSitePackTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = pathlib.Path(cls.temp.name)
        Builder(PACK, cls.output).run()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def configured_bridge(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.dict(
            os.environ,
            {"CODEX_NATIVE_SITE_ALIASES": "valparai|Valparai Plateau"},
        ))
        stack.enter_context(mock.patch.object(server, "SITE_PACK_PATH", PACK))
        stack.enter_context(mock.patch.object(server, "SITE_PROFILE_PATH", PACK / "site.json"))
        stack.enter_context(mock.patch.object(
            server, "VISUAL_INDEX_PATH", self.output / "site_index.sqlite"
        ))
        return stack

    def test_site_overview_routes_to_the_configured_pack(self):
        with self.configured_bridge():
            self.assertEqual(
                server._required_first_skill("Tell me about Valparai."),
                "site-overview",
            )
            result = server._site_overview({"site_id": "Valparai"}, None)
        self.assertEqual(result["status"], "answer")
        rows = result["value"]["rows"]
        sources = next(row for row in rows if row["id"] == "site-profile:source-registry")
        self.assertEqual(len(sources["sources"]), 21)
        self.assertTrue(any(row["id"] == "site-profile:poc-capability-gap" for row in rows))

    def test_local_alias_search_returns_source_linked_points(self):
        with self.configured_bridge():
            result = server._visual_index_local_search("lion-tailed macaque", 5)
        self.assertEqual(result["query_semantics"]["match_mode"], "exact_alias")
        self.assertEqual(len(result["rows"]), 5)
        self.assertTrue(all(row["source_id"] and row["source_row"] for row in result["rows"]))
        self.assertTrue(any(row["latitude"] is not None for row in result["rows"]))

    def test_legacy_site_bound_skill_is_refused_for_the_pack(self):
        with self.configured_bridge():
            self.assertEqual(
                server._required_first_skill("Show fire exposure at Valparai"),
                "local-site-evidence-search",
            )
            result = server._execute_skill(
                "historical-fire-exposure",
                {"region": "Valparai"},
                None,
            )
        self.assertEqual(
            result["execution"]["reason"],
            "site_pack_capability_not_parameterised",
        )

    def test_setup_reads_site_identity_without_copying_the_pack(self):
        config = setup_idlisseus._site_config(PACK)
        self.assertEqual(config["site_id"], "valparai")
        self.assertEqual(config["pack"], PACK.resolve())
        self.assertEqual(config["aliases"], ["valparai", "Valparai Plateau"])

    def test_verified_subject_shape_passes_the_shared_argument_sanitizer_intact(self):
        ids = [f"ent-{index:03d}" for index in range(20)]
        supplied = {
            "capability_id": "co-occurrence-map",
            "arguments": {
                "subjects": [
                    "Elephant",
                    {"requested": "recorded group", "entity_ids": ids},
                ],
            },
        }
        self.assertEqual(server._clean_plan_args(supplied), supplied)
        with self.assertRaisesRegex(ValueError, "exceeds 512"):
            server._clean_plan_args({"entity_ids": ["ent-x"] * 513})

    def test_loose_groups_return_a_bounded_choice_then_verified_ids_make_the_map(self):
        state = self.output / "subject-selection-state"
        result_service = ResultService(PACK, self.output / "site_index.sqlite", state)
        cooccurrence = CooccurrenceService(PACK, self.output / "site_index.sqlite", state)
        patches = (
            mock.patch.object(server, "_result_service", return_value=result_service),
            mock.patch.object(server, "_cooccurrence_service", return_value=cooccurrence),
            mock.patch.object(server, "VISUAL_RESULTS_STATE", state),
            mock.patch.object(server, "MODEL", "test-dialogue-model"),
        )
        with contextlib.ExitStack() as stack:
            for patch in patches:
                stack.enter_context(patch)
            first = server._visual_result_query({
                "capability_id": "co-occurrence-map",
                "arguments": {"subjects": ["elephants", "hornbills"]},
                "question": "Show me squares where elephants and hornbills were both recorded.",
            }, None)
            self.assertEqual(first["reason"], "subject_selection_required")
            request = first["detail"]["requests"][0]
            self.assertEqual(request["requested"], "hornbills")
            self.assertEqual(
                {item["name"] for item in request["candidate_entities"]},
                {"Great Hornbill", "Malabar Grey Hornbill"},
            )
            self.assertEqual(
                first["detail"]["entity_catalogue_columns"],
                ["entity_id", "recorded_name"],
            )
            self.assertEqual(len(first["detail"]["entity_catalogue"]), 1_143)
            self.assertTrue(all(len(row) == 2 for row in first["detail"]["entity_catalogue"]))
            ids = [item["entity_id"] for item in request["candidate_entities"]]
            second = server._visual_result_query({
                "capability_id": "co-occurrence-map",
                # The controller repairs this common model-authored nesting error without
                # changing the selected ids or guessing the other subject.
                "arguments": {
                    "subjects": ["elephants"],
                    "requested": "hornbills",
                    "entity_ids": ids,
                },
                "question": "Show me squares where elephants and hornbills were both recorded.",
            }, None)
            correction = next(
                item for item in second["value"]["actions"]
                if item["action_id"].startswith("correct-subject-")
            )
            reopened = server._visual_result_query({
                "capability_id": correction["capability_id"],
                "arguments": correction["arguments"],
                "question": "Change what hornbills includes.",
            }, None)
            self.assertEqual(reopened["reason"], "subject_selection_required")
        self.assertEqual(second["status"], "answer")
        summary = second["value"]
        self.assertEqual(summary["argument_repair"]["repair"], "nested_selected_subject")
        readings = {item["you_asked_for"]: item for item in summary["subject_resolution"]}
        self.assertEqual(readings["elephants"]["read_as"], ["Elephant"])
        self.assertEqual(
            set(readings["hornbills"]["read_as"]),
            {"Great Hornbill", "Malabar Grey Hornbill"},
        )
        self.assertEqual(readings["hornbills"]["selected_by"], "test-dialogue-model")
        self.assertTrue(summary["answer_marker"].startswith("<!-- idli-result:"))


class BridgeEstimateTargetsTest(unittest.TestCase):
    """The bridge must publish the estimable vocabulary, and must never speak our own."""

    # Words that describe our plumbing rather than the user's district. They are allowed in a
    # skill's *instructions* (that text is for the model) but must be banned there explicitly,
    # and must never be presented to the model as something to say.
    JARGON = ("pack", "gate", "capability", "skill", "envelope", "evidence class")

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        cls.index_root = root / "index"
        Builder(LIVELIHOODS, cls.index_root).run()
        cls.state = root / "state"

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def configured_bridge(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(server, "SITE_PACK_PATH", LIVELIHOODS))
        stack.enter_context(mock.patch.object(
            server, "SITE_PROFILE_PATH", LIVELIHOODS / "site.json"))
        stack.enter_context(mock.patch.object(
            server, "VISUAL_INDEX_PATH", self.index_root / "site_index.sqlite"))
        stack.enter_context(mock.patch.object(server, "VISUAL_RESULTS_STATE", self.state))
        stack.enter_context(mock.patch.object(server, "_RESULT_SERVICE", None))
        stack.enter_context(mock.patch.object(server, "_ESTIMATE_SERVICE", None))
        stack.enter_context(mock.patch.object(server, "_VISUAL_SERVICE_ERRORS", {}))
        # The visual skills only exist when a pack is pinned, and the module built its skill
        # table at import time with none. Rebuild it inside the patched configuration.
        skills = server._load_skills()
        stack.enter_context(mock.patch.object(server, "SKILLS", skills))
        stack.enter_context(mock.patch.object(
            server, "SKILLS_BY_ID", {item["id"]: item for item in skills}))
        return stack

    def test_targets_mode_lists_the_estimable_quantities_and_estimates_nothing(self):
        with self.configured_bridge():
            result = server._execute_skill("visual-estimate", {"mode": "targets"}, None)
        self.assertEqual(result["ir"]["op"], "VISUAL_ESTIMATE_TARGETS")
        execution = result["execution"]
        self.assertEqual(execution["status"], "answer")
        value = execution["value"]
        self.assertEqual(value["kind"], "visual_estimate_targets")
        self.assertIn("event_total:mgnrega_work", value["target_ids"])
        rows = {item["target_id"]: item for item in value["targets"]}
        self.assertEqual(rows["event_total:mgnrega_work"]["counts_column"], "persondays")
        self.assertIn("Footpath repair", rows["event_total:mgnrega_work"]["record_labels"])
        # A catalogue call is not an estimate: no result, no marker, no number to relay.
        self.assertNotIn("result_id", value)
        self.assertNotIn("answer_marker", value)
        self.assertFalse(result["schema"]["has_estimate"])

    def test_a_word_the_index_does_not_carry_is_refused_with_the_vocabulary(self):
        """The bug this fixes: "jobs" must never come back as "no variable called job"."""
        with self.configured_bridge():
            result = server._execute_skill(
                "visual-estimate",
                {"mode": "suggest", "cell": "at:10.30:76.94", "target": "jobs"},
                None,
            )
        detail = result["execution"]["detail"]
        self.assertEqual(result["execution"]["reason"], "invalid_estimate_request")
        self.assertIn("event_total:mgnrega_work", detail["target_ids"])
        self.assertIn("does not exist", detail["ask"])
        self.assertTrue(any(
            item["counts_column"] == "persondays" for item in detail["available_targets"]
        ))

    def test_a_catalogued_id_runs_and_the_summary_carries_its_semantics(self):
        with self.configured_bridge():
            menu = server._execute_skill("visual-estimate", {
                "mode": "suggest", "cell": "at:10.30:76.94",
                "target": "event_total:mgnrega_work",
            }, None)["execution"]["value"]
            self.assertTrue(menu["available_targets"])
            run = server._execute_skill("visual-estimate", {
                "mode": "run", "approach_id": menu["recommended_approach_id"],
                "cell": "at:10.30:76.94", "target": "event_total:mgnrega_work",
            }, None)["execution"]["value"]
        self.assertEqual(run["target_id"], "event_total:mgnrega_work")
        self.assertIn("persondays", run["target_unit"])
        self.assertIn("persondays", run["what_it_counts"])
        self.assertTrue(run["answer_marker"].startswith("<!-- idli-result:"))

    def test_every_visual_skill_bans_our_vocabulary_from_the_answer(self):
        with self.configured_bridge():
            skills = {item["id"]: item for item in server._load_skills()}
        visual = [
            key for key in skills
            if key.startswith("visual-") and skills[key].get("binding", {}).get("mode")
        ]
        self.assertGreaterEqual(len(visual), 5)
        for skill_id in visual:
            instructions = skills[skill_id]["instructions"]
            self.assertIn("PLAIN ENGLISH IS NOT OPTIONAL", instructions, skill_id)
            for word in self.JARGON:
                self.assertIn(word, instructions.casefold(), f"{skill_id} must ban {word!r}")

    def test_source_rows_uses_the_local_copy_through_the_existing_visual_skill(self):
        with self.configured_bridge():
            skills = {item["id"]: item for item in server._load_skills()}
            instructions = skills["visual-result"]["instructions"]
            self.assertIn("READ THE LOCAL COPY FIRST", instructions)
            result = server._execute_skill(
                "visual-result",
                {
                    "capability_id": "source-rows",
                    "arguments": {
                        "source_id": "syn-estate-labour",
                        "file": "estates.csv",
                        "limit": 2,
                    },
                    "question": "Show me two rows from the estate source.",
                },
                None,
            )
            value = result["execution"]["value"]
            service = server._result_service()
            stored = service.load_data(value["result_id"], "source-rows")
        self.assertEqual(result["execution"]["status"], "answer")
        self.assertEqual(value["capability_id"], "source-rows")
        self.assertTrue(value["answer_marker"].startswith("<!-- idli-result:"))
        self.assertIsNotNone(stored)
        self.assertIn(b"_source_row", stored[1])

    def test_a_resolved_square_is_relayed_as_an_extent_that_covers_the_point(self):
        """The complaint this fixes: a user clicked 10.305 and was answered about a cell id.

        The grid labels each square by its south-west corner, so 10.305 belongs to the square
        starting at 10.300. That is right, and `g0.010:10.3000:76.9900` is an unreadable way to
        say it: it looks like the system replaced the user's coordinates with different ones.
        """
        with self.configured_bridge():
            menu = server._execute_skill("visual-estimate", {
                "mode": "suggest", "cell": "at:10.30500:76.99500",
                "target": "event_total:mgnrega_work",
            }, None)["execution"]["value"]
            run = server._execute_skill("visual-estimate", {
                "mode": "run", "approach_id": "aoi-baseline-mean",
                "cell": "at:10.30500:76.99500", "target": "event_total:mgnrega_work",
            }, None)["execution"]["value"]
        for value in (menu, run):
            description = value["cell_description"]
            self.assertIn("km square", description)
            self.assertIn("10.305 N", description)
            self.assertIn("10.300", description)
            self.assertIn("76.990", description)
            self.assertNotIn("g0.0", description)
            # The id itself stays available for the map and the audit trail.
            self.assertEqual(value["cell_id"], "g0.010:10.3000:76.9900")
        self.assertEqual(run["requested_point"], {"lat": 10.305, "lon": 76.995})
        for text in (run["headline"], run["detail"]):
            self.assertNotIn("g0.0", text)
        for item in run["limitations"]:
            self.assertNotIn("g0.0", item["message"])
        for item in run["improvements"]:
            self.assertNotIn("g0.0", item["label"])
        self.assertIn("cell_description", run["instruction"])

    def test_the_result_summary_forwards_the_real_option_menu(self):
        """A menu the model cannot see is a menu the model invents."""
        with self.configured_bridge():
            summary = server._visual_result_summary({
                "result_id": "result-abc123",
                "status": "partial",
                "answer": {"headline": "Choose a measure."},
                "actions": [{
                    "action_id": "choose-metric", "kind": "choice",
                    "label": "Which measure?", "capability_id": "metric-time-series",
                    "arguments": {"available_metrics": ["daily_wage", "paid_days_per_month"]},
                }],
            })
        self.assertEqual(summary["actions"][0]["action_id"], "choose-metric")
        self.assertIn(
            "daily_wage", summary["actions"][0]["arguments"]["available_metrics"]
        )
        self.assertIn("actions", summary["instruction"])

    def test_named_places_travel_with_the_catalogue_so_nobody_types_coordinates(self):
        with self.configured_bridge():
            targets = server._execute_skill(
                "visual-estimate", {"mode": "targets"}, None)["execution"]["value"]
        places = {item["name"]: item for item in targets["places"]}
        self.assertIn("Kadamparai Village", places)
        self.assertAlmostEqual(places["Kadamparai Village"]["lat"], 10.261, places=3)
        self.assertAlmostEqual(places["Kadamparai Village"]["lon"], 76.966, places=3)
        self.assertIn("never ask a person to type", targets["instruction"].casefold())

    def test_headline_stats_speak_in_the_reader_s_nouns_not_ours(self):
        """The rail said "entities". A programme manager does not have entities; they have data."""
        with self.configured_bridge():
            stats = server._site_headline_stats()
        self.assertEqual(stats["schema_version"], "idli-site-stats/1")
        self.assertEqual(stats["site_id"], "valparai_livelihoods")
        self.assertGreaterEqual(len(stats["stats"]), 3)
        self.assertLessEqual(len(stats["stats"]), 5)
        labels = {item["label"] for item in stats["stats"]}
        self.assertIn("Households surveyed", labels)
        self.assertIn("Villages covered", labels)
        # The count column the pack declared names the quantity, spelled the pack's own way.
        persondays = next(
            item for item in stats["stats"] if item["id"] == "total:mgnrega_work"
        )
        self.assertEqual(persondays["value"], 56636)
        self.assertIn("MGNREGA", persondays["detail"])
        for item in stats["stats"]:
            self.assertTrue(item["detail"])
            for word in ("entit", "cell", "adapter", "plane", "source_id", "event_total"):
                self.assertNotIn(word, item["label"].casefold(), item["label"])

    def test_a_result_carries_what_must_be_said_about_it(self):
        """The requirement travels with the result, so it competes with nothing in the prompt."""
        with self.configured_bridge():
            result = server._execute_skill("visual-result", {
                "capability_id": "co-occurrence-map",
                "arguments": {"subjects": ["Footpath repair", "Construction labour"]},
                "question": "Where are both recorded?",
            }, None)
            summary = result["execution"]["value"]
        statements = {item["id"]: item for item in summary["required_statements"]}
        self.assertIn("join-rule", statements)
        self.assertTrue(statements["join-rule"]["statement"])
        self.assertTrue(statements["join-rule"]["must_include"])
        self.assertIn("must be said", summary["required_statements_note"])

    def test_the_outgoing_check_repairs_wording_and_reports_what_it_may_not_write(self):
        class _Session:
            def __init__(self, statements):
                self.turn_skill_calls = [{
                    "skill": "visual-result",
                    "result": {"execution": {"value": {"required_statements": statements}}},
                }]

        with self.configured_bridge():
            result = server._execute_skill("visual-result", {
                "capability_id": "co-occurrence-map",
                "arguments": {"subjects": ["Footpath repair", "Construction labour"]},
                "question": "Where are both recorded?",
            }, None)
            statements = result["execution"]["value"]["required_statements"]
            session = _Session(statements)
            review = server._review_final_answer(
                session, "Six squares hold both, in the target cells."
            )
        # Wording that belongs to the plumbing is substituted, not asked for.
        self.assertNotIn("target cells", review["text"])
        self.assertIn("squares inside this site's boundary", review["text"])
        # A missing required statement is reported and never written into the answer.
        missing = {item["id"] for item in review["missing_statements"]}
        self.assertIn("join-rule", missing)
        for item in review["missing_statements"]:
            self.assertNotIn(item["statement"], review["text"])
        self.assertIn("no-next-step", {item["code"] for item in review["issues"]})

    def test_the_relay_instructions_never_ask_the_model_to_speak_in_ids(self):
        """What the model is told to say is what it says. The instruction must be plain."""
        with self.configured_bridge():
            targets = server._execute_skill(
                "visual-estimate", {"mode": "targets"}, None)["execution"]["value"]
            run = server._execute_skill("visual-estimate", {
                "mode": "run", "approach_id": "aoi-baseline-mean",
                "cell": "at:10.30:76.94", "target": "event_total:mgnrega_work",
            }, None)["execution"]["value"]
        self.assertIn("plain language", targets["instruction"])
        self.assertIn("never tell the user", targets["instruction"].casefold())
        self.assertIn("plain", run["instruction"].casefold())
        self.assertIn("no internal vocabulary", run["instruction"].casefold())


if __name__ == "__main__":
    unittest.main()
