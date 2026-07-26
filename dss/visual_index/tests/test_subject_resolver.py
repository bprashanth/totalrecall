import pathlib
import sqlite3
import tempfile
import unittest

from dss.visual_index.build import Builder
from dss.visual_index.subject_resolver import SubjectResolver


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai"


class SubjectResolverTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.temp.name)
        Builder(PACK, cls.root).run()
        cls.connection = sqlite3.connect(cls.root / "site_index.sqlite")
        cls.connection.row_factory = sqlite3.Row
        cls.resolver = SubjectResolver(cls.connection, cls.root / "state")
        cls.selector = {"model": "test-model", "prompt_version": "test-prompt/1"}

    @classmethod
    def tearDownClass(cls):
        cls.connection.close()
        cls.temp.cleanup()

    def test_plural_widening_resolves_one_registered_name_without_a_model(self):
        found = self.resolver.inspect("elephants", self.selector)
        self.assertEqual(found["status"], "resolved")
        binding = found["binding"]
        self.assertEqual(binding["member_labels"], ["Elephant"])
        self.assertEqual(binding["resolution_method"], "number_variant")
        self.assertNotIn("selector", binding)

    def test_hornbills_are_two_candidates_after_the_reviewed_identity_merge(self):
        found = self.resolver.inspect("hornbills", self.selector)
        self.assertEqual(found["status"], "selection_required")
        self.assertEqual(found["reason"], "ambiguous_name")
        self.assertEqual(
            {item["name"] for item in found["candidates"]},
            {"Great Hornbill", "Malabar Grey Hornbill"},
        )

    def test_an_open_group_gets_the_complete_bounded_catalogue(self):
        found = self.resolver.inspect("raptors", self.selector)
        self.assertEqual(found["status"], "selection_required")
        self.assertEqual(found["reason"], "open_group_or_unknown_name")
        self.assertEqual(len(found["catalogue"]), 1_144)
        self.assertTrue(all(item["entity_id"] for item in found["catalogue"]))

    def test_substring_widening_does_not_silently_choose_a_false_positive(self):
        found = self.resolver.inspect("falcon", self.selector)
        self.assertEqual(found["status"], "selection_required")
        self.assertEqual(
            {item["name"] for item in found["candidates"]},
            {"Peregrine Falcon", "Falconeria insignis"},
        )

    def test_model_ids_are_verified_versioned_and_cached(self):
        hornbills = [
            item["entity_id"] for item in self.resolver.catalogue
            if "hornbill" in item["name"].casefold()
        ]
        binding = self.resolver.verify("hornbills", hornbills, self.selector)
        self.assertEqual(binding["resolution_method"], "model_selected")
        self.assertEqual(binding["shared_hierarchy"]["value"], "Bucerotidae")
        self.assertTrue(
            (self.root / "state" / "subject-bindings" / "bindings"
             / f"{binding['binding_id']}.json").is_file()
        )
        cached = self.resolver.inspect("hornbills", self.selector)["binding"]
        self.assertEqual(cached["resolution_method"], "cached_model_selection")
        self.assertEqual(cached["entity_ids"], binding["entity_ids"])

    def test_an_id_outside_the_catalogue_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "outside the supplied site catalogue"):
            self.resolver.verify("raptors", ["ent-invented"], self.selector)

    def test_cache_identity_includes_model_prompt_and_catalogue(self):
        first = self.resolver._cache_key("raptors", self.selector)
        other_model = self.resolver._cache_key(
            "raptors", {"model": "other-model", "prompt_version": "test-prompt/1"}
        )
        other_prompt = self.resolver._cache_key(
            "raptors", {"model": "test-model", "prompt_version": "test-prompt/2"}
        )
        self.assertEqual(len({first, other_model, other_prompt}), 3)


if __name__ == "__main__":
    unittest.main()
