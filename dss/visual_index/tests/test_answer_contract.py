"""Requirements that live in the data hold; requirements that live in the prompt displace.

Four benchmark rounds established that adding a rule to the system prompt costs another rule that
was already working. These checks cover the replacement: each result carries what must be said
about it, and the invariants that need no judgement are enforced on the way out rather than hoped
for on the way in.
"""

import pathlib
import tempfile
import unittest

from dss.visual_index.answer_contract import (
    repair_wording, required_statements, review_answer, split_long_sentences,
)
from dss.visual_index.build import Builder
from dss.visual_index.cooccurrence_service import CooccurrenceService


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"


class RequiredStatementTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        Builder(PACK, root).run()
        cls.service = CooccurrenceService(
            PACK, root / "site_index.sqlite", root / "state")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_a_shared_square_result_carries_its_own_join_rule(self):
        envelope = self.service.co_occurrence_map(
            "contract-join", ["Footpath repair", "Construction labour"])
        statements = {item["id"]: item for item in required_statements(envelope)}
        self.assertIn("join-rule", statements)
        self.assertIn("effort-shapes-overlap", statements)
        # The statement is the capability's own wording, not something written here.
        join = next(
            item["message"] for item in envelope["limitations"]
            if item["code"] == "shared-square-is-not-interaction"
        )
        self.assertEqual(statements["join-rule"]["statement"], join)
        self.assertTrue(statements["join-rule"]["must_include"])
        self.assertTrue(statements["join-rule"]["why"])
        self.assertEqual(statements["join-rule"]["audience"], "reader")

    def test_instructions_are_marked_for_the_model_not_rendered_as_reader_prose(self):
        envelope = {
            "answer": {"headline": "12 records"},
            "audit": {
                "estimate": {
                    "estimate": 12,
                    "confidence_basis": "wide held-out residuals",
                    "cell_description_short": "the 1 km square around the village",
                },
                "source_versions": [{"title": "Household panel 2024"}],
            },
        }
        statements = {item["id"]: item for item in required_statements(envelope)}
        self.assertEqual(statements["estimate-is-modelled"]["audience"], "reader")
        self.assertEqual(statements["estimate-confidence"]["audience"], "model")
        self.assertEqual(statements["which-square"]["audience"], "model")
        self.assertEqual(statements["name-the-survey"]["audience"], "model")

    def test_a_result_with_nothing_to_require_requires_nothing(self):
        self.assertEqual(required_statements({}), [])
        self.assertEqual(required_statements({"answer": {"headline": "hello"}}), [])

    def test_a_missing_statement_is_reported_and_never_written(self):
        envelope = self.service.co_occurrence_map(
            "contract-missing", ["Footpath repair", "Construction labour"])
        statements = required_statements(envelope)
        answer = "Six squares hold both. If you want, I can map them."
        review = review_answer(answer, statements)
        missing = {item["id"] for item in review["missing_statements"]}
        self.assertIn("join-rule", missing)
        self.assertIn("required-statement-missing", {i["code"] for i in review["issues"]})
        # Reporting only: the answer text is never given prose it did not have.
        for item in review["missing_statements"]:
            self.assertNotIn(item["statement"], review["text"])

    def test_saying_it_in_your_own_words_counts(self):
        envelope = self.service.co_occurrence_map(
            "contract-said", ["Footpath repair", "Construction labour"])
        statements = [
            item for item in required_statements(envelope) if item["id"] == "join-rule"
        ]
        answer = (
            "Both were recorded in the same map square. That is not an interaction. "
            "If you want, I can pull the rows."
        )
        review = review_answer(answer, statements, expect_next_step=True)
        self.assertEqual(review["missing_statements"], [])
        self.assertEqual(review["issues"], [])


class DeterministicRepairTest(unittest.TestCase):
    def test_banned_wording_is_substituted_not_requested(self):
        text, applied = repair_wording("802 mapped records with 436 in the target cells.")
        self.assertIn("squares inside this site's boundary", text)
        self.assertNotIn("target cells", text)
        self.assertTrue(applied)

    def test_a_square_id_is_replaced_by_the_extent_the_result_carries(self):
        text, applied = repair_wording(
            "The value in g0.010:10.3000:76.9900 is high.",
            cell_description="the 1.1 km square covering 10.305 N, 76.995 E",
        )
        self.assertNotIn("g0.010", text)
        self.assertIn("1.1 km square", text)
        self.assertIn("grid square id", applied)

    def test_a_long_sentence_splits_only_where_both_halves_stand_alone(self):
        long_sentence = (
            "From the data this site has, elephants and hornbills were both recorded in 20 "
            "squares, and this shows where the records overlap across the plateau this season."
        )
        text, count = split_long_sentences(long_sentence, limit=20)
        self.assertEqual(count, 1)
        self.assertIn("squares. This shows", text)
        # A subordinate clause is left alone rather than turned into a fragment.
        subordinate = (
            "My confidence is moderate for this species, because the site holds 802 mapped "
            "records across the restoration, bird recovery and plant community surveys here."
        )
        text, count = split_long_sentences(subordinate, limit=20)
        self.assertEqual(count, 0)
        self.assertEqual(text, subordinate)

    def test_a_missing_next_step_is_reported(self):
        review = review_answer("Here is a figure. It is 42.", [], expect_next_step=True)
        self.assertIn("no-next-step", {item["code"] for item in review["issues"]})
        review = review_answer(
            "Here is a figure. If you want, I can show the rows.", [], expect_next_step=True)
        self.assertNotIn("no-next-step", {item["code"] for item in review["issues"]})

    def test_markers_and_tables_are_left_untouched(self):
        text = '<!-- idli-result:{"result_id":"result-abc"} -->\n\n| a | b |\n| --- | --- |'
        review = review_answer(text, [], expect_next_step=False)
        self.assertIn('<!-- idli-result:{"result_id":"result-abc"} -->', review["text"])
        self.assertIn("| a | b |", review["text"])


if __name__ == "__main__":
    unittest.main()
