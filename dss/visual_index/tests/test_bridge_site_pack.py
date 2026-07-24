import contextlib
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from dss.visual_index.build import Builder
from ecology_memory.integration.codex_native import server
from ecology_memory.integration.codex_native import setup_idlisseus


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai"


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


if __name__ == "__main__":
    unittest.main()
