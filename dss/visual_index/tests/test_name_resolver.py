"""A refusal has to be preceded by a lookup that actually ran.

The bench that prompted these checks found the system telling a field ecologist that the site
holds no lantana while 36 lantana records sat in the index, and that "mammal" resolved to nothing
while `Mammalia` sat there as a class with three dedicated sources. Neither was a data problem:
the lists of accepted values printed into the skill text were cut alphabetically, and the text
said anything not listed would not resolve.
"""

import pathlib
import sqlite3
import tempfile
import unittest

from dss.visual_index.build import Builder
from dss.visual_index.name_resolver import resolve_name
from dss.visual_index.target_catalogue import capability_vocabulary


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai"


class NameResolverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        Builder(PACK, root).run()
        cls.connection = sqlite3.connect(
            f"file:{root / 'site_index.sqlite'}?mode=ro", uri=True)
        cls.connection.row_factory = sqlite3.Row

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.temp.cleanup()

    def test_a_bare_genus_finds_the_species_the_pack_files_it_under(self):
        found = resolve_name(self.connection, "Lantana")
        self.assertTrue(found["looked_up"])
        labels = [item["label"] for item in found["candidates"]]
        self.assertTrue(
            any("Lantana camara" in label for label in labels),
            f"the binomial must be reachable from the genus; got {labels}",
        )
        best = found["candidates"][0]
        self.assertGreaterEqual(best["records"], 30)

    def test_an_everyday_word_finds_the_taxonomic_group(self):
        found = resolve_name(self.connection, "mammal")
        groups = [
            item for item in found["candidates"] if item["kind"] == "group"
        ]
        self.assertTrue(groups)
        self.assertIn(
            "Mammalia", [item["value"] for item in groups],
            "the class a person means by 'mammal' must be reachable",
        )

    def test_a_word_that_is_really_absent_returns_nothing_but_still_ran(self):
        found = resolve_name(self.connection, "quetzalcoatlus")
        self.assertTrue(found["looked_up"])
        self.assertEqual(found["candidates"], [])

    def test_the_printed_vocabulary_leads_with_the_biggest_groups(self):
        """Alphabetical truncation is what made the largest group in the pack invisible."""
        vocabulary = capability_vocabulary(self.connection)
        classes = next(
            item for item in vocabulary["hierarchy"] if item["rank"] == "class"
        )
        shown = [entry["group"] for entry in classes["groups"][:12]]
        self.assertEqual(shown[0], "Magnoliopsida", "the biggest group must come first")
        self.assertIn("Mammalia", shown)
        # Ordering is by size, so the sample can never hide the largest values.
        members = [entry["members"] for entry in classes["groups"]]
        self.assertEqual(members, sorted(members, reverse=True))
        metrics = [item["metric"] for item in vocabulary["metrics"]]
        self.assertEqual(len(metrics), vocabulary["metrics_total"])
        readings = [item["readings"] for item in vocabulary["metrics"]]
        self.assertEqual(readings, sorted(readings, reverse=True))


if __name__ == "__main__":
    unittest.main()
