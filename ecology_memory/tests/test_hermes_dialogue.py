import importlib.util
import pathlib
import unittest


PATH = pathlib.Path(__file__).parents[1] / "integration" / "runtime" / "dialogue.py"
SPEC = importlib.util.spec_from_file_location("ecology_dialogue", PATH)
D = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(D)


class HermesDialogueRoutingTests(unittest.TestCase):
    def test_plain_site_opening_clarifies(self):
        self.assertTrue(D.is_broad_site_opening("tell me about ebtl"))

    def test_explicit_fire_opening_does_not_clarify_again(self):
        self.assertFalse(D.is_broad_site_opening("tell me about fire at the site"))
        self.assertIn("historical fire exposure", D.canonical_site_topic(
            "tell me about fire at the site"))

    def test_natural_clarification_reply_binds_topic(self):
        self.assertEqual(D.canonical_site_topic("i said fire"), D.SITE_CHOICES["3"])

    def test_wildlife_clarification_reply_binds_local_inventory(self):
        for wording in ("wildlife, what is seen there", "fauna", "animals at the site", "2"):
            with self.subTest(wording=wording):
                self.assertEqual(D.canonical_site_topic(wording), D.SITE_CHOICES["2"])

    def test_all_natural_language_menu_choices_bind(self):
        cases = {
            "vegetation, what is on the ground": "1",
            "wildlife, what is seen there": "2",
            "fire, what is the risk": "3",
            "restoration, how is it going": "4",
        }
        for wording, choice in cases.items():
            with self.subTest(wording=wording):
                self.assertEqual(D.canonical_site_topic(wording), D.SITE_CHOICES[choice])

    def test_specific_species_does_not_collapse_to_generic_wildlife(self):
        self.assertIsNone(D.canonical_site_topic("what snake species are there?"))


if __name__ == "__main__":
    unittest.main()
