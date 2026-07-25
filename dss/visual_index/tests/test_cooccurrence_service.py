"""Two subjects in the same square is a question this site could not answer at all.

`interaction-map` maps only the associations a source explicitly declared, so "where do both
hornbills and elephants occur" came back blocked while the answer sat in the index. These checks
are about conduct as much as arithmetic: that the shared squares really are the intersection, that
the map leads with them rather than with two competing choropleths, that the drill-down names the
rows on both sides, and that no result can be published without saying — in words a reader will
actually understand — that sharing a square is not an interaction.
"""

import json
import pathlib
import tempfile
import unittest

from dss.visual_index.build import Builder
from dss.visual_index.cooccurrence_service import CooccurrenceService
from dss.visual_index.result_service import ResultService


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"


class CooccurrenceServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        Builder(PACK, root).run()
        cls.state = root / "state"
        cls.service = CooccurrenceService(PACK, root / "site_index.sqlite", cls.state)
        cls.results = ResultService(PACK, root / "site_index.sqlite", cls.state)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def _squares(self, name):
        with self.service.connect() as connection:
            subject = self.service.resolve_subject(connection, name)
            return set(self.service.subject_squares(connection, subject))

    def test_shared_squares_are_the_intersection_and_are_drawn_first(self):
        envelope = self.service.co_occurrence_map(
            "test-shared", ["Footpath repair", "Construction labour"],
            question="Where do both occur?",
        )
        expected = self._squares("Footpath repair") & self._squares("Construction labour")
        self.assertTrue(expected, "the fixture must actually share squares")
        self.assertEqual(envelope["status"], "complete")

        visual = envelope["visuals"][0]
        layers = visual["layers"]
        # The answer is the overlap, so it is the first layer and the only filled one; each
        # subject keeps its own layer for context rather than a second choropleth.
        self.assertEqual(layers[0]["layer_id"], "shared-squares")
        self.assertEqual(layers[0]["style_hint"]["render"], "fill")
        self.assertEqual(layers[0]["style_hint"]["emphasis"], "primary")
        self.assertEqual(
            [layer["layer_id"] for layer in layers[1:3]],
            ["subject-1-squares", "subject-2-squares"],
        )
        for layer in layers[1:]:
            self.assertEqual(layer["style_hint"]["render"], "outline")

        payload = json.loads(
            (self.state / "results" / envelope["result_id"] / "data" / "shared-squares.geojson")
            .read_text()
        )
        self.assertEqual({item["id"] for item in payload["features"]}, expected)

        denominators = visual["summary"]["denominators"]
        self.assertEqual(denominators["shared_squares"], len(expected))
        self.assertEqual(
            set(denominators["squares_per_subject"]),
            {"Footpath repair", "Construction labour"},
        )
        self.assertTrue(denominators["records_per_subject_in_shared_squares"])

    def test_the_drilldown_names_the_rows_on_both_sides(self):
        envelope = self.service.co_occurrence_map(
            "test-rows", ["Footpath repair", "Construction labour"]
        )
        rows = json.loads(
            (self.state / "results" / envelope["result_id"] / "data"
             / "shared-square-records.json").read_text()
        )
        self.assertTrue(rows)
        self.assertEqual(
            {row["subject"] for row in rows}, {"Footpath repair", "Construction labour"}
        )
        for row in rows:
            self.assertTrue(row["source_id"] and row["event_id"])
            self.assertIsNotNone(row["source_row"])

    def test_no_result_can_be_published_without_the_honesty_it_needs(self):
        envelope = self.service.co_occurrence_map(
            "test-caveats", ["Footpath repair", "Construction labour"]
        )
        codes = {item["code"] for item in envelope["limitations"]}
        self.assertIn("shared-square-is-not-interaction", codes)
        self.assertIn("different-surveys-and-effort", codes)
        self.assertIn("no-overlap-is-not-separation", codes)
        self.assertIn("records-not-contemporaneous", codes)
        message = next(
            item["message"] for item in envelope["limitations"]
            if item["code"] == "shared-square-is-not-interaction"
        )
        # Said in words, with the size of the square, and with the claim explicitly refused.
        self.assertIn("km square", message)
        self.assertIn("not an interaction", message)
        for item in envelope["limitations"]:
            self.assertNotIn("g0.0", item["message"])

    def test_same_year_is_offered_and_can_be_run(self):
        envelope = self.service.co_occurrence_map(
            "test-year", ["Footpath repair", "Construction labour"]
        )
        audit = envelope["audit"]["co_occurrence"]
        self.assertLessEqual(audit["shared_squares_same_year"], audit["shared_squares_any_year"])
        if audit["shared_squares_same_year"] != audit["shared_squares_any_year"]:
            self.assertTrue(any(
                item["action_id"] == "restrict-to-same-year" for item in envelope["actions"]
            ))
        restricted = self.service.co_occurrence_map(
            "test-year-only", ["Footpath repair", "Construction labour"], same_year=True
        )
        self.assertLessEqual(
            restricted["visuals"][0]["summary"]["denominators"]["shared_squares"],
            audit["shared_squares_any_year"],
        )
        self.assertIn(
            "same-year-only", {item["code"] for item in restricted["limitations"]}
        )

    def test_a_group_resolves_without_the_caller_naming_the_rank(self):
        envelope = self.service.co_occurrence_map(
            "test-group", ["Footpath repair", {"kind": "group", "value": "north_division"}]
        )
        subjects = envelope["question"]["bindings"]["subjects"]
        self.assertEqual(subjects[1]["kind"], "group")
        self.assertEqual(subjects[1]["rank"], "division")

    def test_a_kind_of_record_is_a_subject_too(self):
        """"Where are both public works and people leaving recorded" names no entity at all."""
        envelope = self.service.co_occurrence_map(
            "test-record-kind", ["mgnrega work", "out migration"]
        )
        self.assertEqual(envelope["status"], "complete")
        subjects = envelope["question"]["bindings"]["subjects"]
        self.assertEqual({item["kind"] for item in subjects}, {"record_kind"})
        # The pack's own spelling comes back, not the column token.
        self.assertEqual(subjects[0]["label"], "MGNREGA work")
        self.assertNotIn("_", envelope["answer"]["headline"])
        denominators = envelope["visuals"][0]["summary"]["denominators"]
        self.assertGreater(denominators["shared_squares"], 0)
        rows = json.loads(
            (self.state / "results" / envelope["result_id"] / "data"
             / "shared-square-records.json").read_text()
        )
        self.assertEqual({row["subject"] for row in rows}, {"MGNREGA work", "Out migration"})

    def test_an_unknown_subject_is_a_naming_gap_not_an_absence(self):
        envelope = self.service.co_occurrence_map(
            "test-unknown", ["Footpath repair", "snow leopard"]
        )
        self.assertEqual(envelope["status"], "blocked")
        codes = {item["code"] for item in envelope["limitations"]}
        self.assertIn("unresolved-subject", codes)
        message = next(
            item["message"] for item in envelope["limitations"]
            if item["code"] == "unresolved-subject"
        )
        self.assertIn("not evidence that it is absent", message)

    def test_two_subjects_are_required(self):
        with self.assertRaises(ValueError):
            self.service.co_occurrence_map("test-one", ["Footpath repair"])

    def test_the_profile_says_what_is_recorded_and_who_shares_the_squares(self):
        envelope = self.service.activity_profile("test-profile", entity="Footpath repair")
        self.assertEqual(envelope["status"], "complete")
        rows = json.loads(
            (self.state / "results" / envelope["result_id"] / "data"
             / "activity-profile.json").read_text()
        )
        sections = {row["section"] for row in rows}
        self.assertIn("Kind of record", sections)
        self.assertIn("Survey", sections)
        self.assertIn("Shares squares with", sections)
        for row in rows:
            # Machine tokens are humanised before they reach a table a person reads.
            self.assertNotIn("_", row["name"])
        codes = {item["code"] for item in envelope["limitations"]}
        self.assertIn("records-not-abundance", codes)
        self.assertIn("shared-square-is-not-interaction", codes)
        self.assertTrue(any(
            item["capability_id"] == "co-occurrence-map" for item in envelope["actions"]
        ))

    def test_the_envelope_is_a_readable_idli_result(self):
        envelope = self.service.co_occurrence_map(
            "test-envelope", ["Footpath repair", "Construction labour"]
        )
        stored = self.results.load_result(envelope["result_id"])
        self.assertIsNotNone(stored, "the shared-square result must be readable over the same "
                                     "transport as every other visual")
        self.assertEqual(stored["schema_version"], "idli-result/1")
        self.assertEqual(stored["audit"]["assurance"], "observed")
        for text in (stored["answer"]["headline"], stored["answer"]["detail"],
                     stored["question"]["resolved"]):
            self.assertNotIn("g0.0", text)


if __name__ == "__main__":
    unittest.main()
