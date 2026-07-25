"""Where to survey next must rank by what we do not know.

The bench caught the assistant arguing coverage-gap logic for six turns and then ranking the top
five places by record density — where we have already looked — and naming them by latitude band
while the pack holds hundreds of named places.
"""

import pathlib
import tempfile
import unittest

from dss.visual_index.build import Builder
from dss.visual_index.survey_priority import SurveyPriorityService


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai"


class SurveyPriorityTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        Builder(PACK, root).run()
        cls.service = SurveyPriorityService(
            PACK, root / "site_index.sqlite", root / "state")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_the_ranking_is_not_the_record_league_table(self):
        ranked = self.service.rank(limit=5)["ranked"]
        self.assertEqual(len(ranked), 5)
        by_records = sorted(ranked, key=lambda item: -item["records"])
        self.assertNotEqual(
            [item["cell_id"] for item in ranked],
            [item["cell_id"] for item in by_records],
            "ranking by gap must not reproduce ranking by record count",
        )
        scores = [item["gap_score"] for item in ranked]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_every_place_has_a_name_a_person_could_drive_to(self):
        ranked = self.service.rank(limit=5)["ranked"]
        for item in ranked:
            self.assertTrue(item["place"], "the pack holds named places; use them")
            self.assertTrue(item["place"]["name"])
            self.assertIn(item["place"]["name"], item["headline"])
            self.assertTrue(item["why"])

    def test_the_envelope_says_what_the_ranking_is_and_is_not(self):
        envelope = self.service.rank_result("test-gap", limit=5)
        self.assertEqual(envelope["status"], "complete")
        codes = {item["code"] for item in envelope["limitations"]}
        self.assertIn("ranked-by-missing-information", codes)
        message = next(
            item["message"] for item in envelope["limitations"]
            if item["code"] == "ranked-by-missing-information"
        )
        self.assertIn("NOT where the ecology is richest", message)
        layers = [layer["layer_id"] for layer in envelope["visuals"][0]["layers"]]
        self.assertIn("survey-priority", layers)
        self.assertTrue(envelope["actions"])


if __name__ == "__main__":
    unittest.main()
