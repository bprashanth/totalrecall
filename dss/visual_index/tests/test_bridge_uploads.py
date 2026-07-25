"""An inlined file must behave exactly like a staged one, and must outrank evidence search."""

import contextlib
import json
import os
import pathlib
import tempfile
import unittest
from unittest import mock

from dss.visual_index.build import Builder
from ecology_memory.integration.codex_native import server


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"

# Exactly the block Idlisseus inlines into the user message for a small text file.
INLINE_TURN = """Attached is our household income survey CSV. Profile and visualize it, then \
cross-check the villages against the site data.

=== File: household_income_survey.csv ===
[Type: csv, Lines: 5, Size: 214 bytes]

village,survey_month,households,median_income
Thonimalai,2024-01,42,9800
Perumpallam,2024-01,37,10450
Kadamparai,2024-02,51,8900
Puliyara Colony,2024-02,18,7600
"""


class StubSession:
    """Only the surface `_stage_inline_files` and the routing helpers actually touch."""

    def __init__(self, root: pathlib.Path):
        self.id = "stub-session"
        self.input = root / "input"
        self.input.mkdir(parents=True, exist_ok=True)
        self.attachments: list[dict] = []
        self.saves = 0

    def _save(self) -> None:
        self.saves += 1


class InlineFileStagingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.session = StubSession(pathlib.Path(self.temp.name))

    def tearDown(self):
        self.temp.cleanup()

    def test_inline_block_is_parsed_with_its_metadata_line(self):
        blocks = server._inline_file_blocks(INLINE_TURN)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0]["name"], "household_income_survey.csv")
        self.assertIn("Type: csv", blocks[0]["meta"])
        text = blocks[0]["bytes"].decode()
        self.assertTrue(text.startswith("village,survey_month,households,median_income"))
        self.assertTrue(text.rstrip().endswith("Puliyara Colony,2024-02,18,7600"))

    def test_several_blocks_and_non_text_blocks(self):
        message = (
            "two files\n\n=== File: a.csv ===\n[Type: csv]\n\nx,y\n1,2\n\n"
            "=== File: b.tsv ===\n\nx\ty\n1\t2\n\n"
            "=== File: c.png ===\n[Type: png]\n\nnot text\n"
        )
        names = [item["name"] for item in server._inline_file_blocks(message)]
        self.assertEqual(names, ["a.csv", "b.tsv"])

    def test_staging_registers_the_block_like_a_real_attachment(self):
        staged = server._stage_inline_files(self.session, INLINE_TURN)
        self.assertEqual(len(staged), 1)
        item = staged[0]
        self.assertTrue(item["id"].startswith("inline-"))
        self.assertEqual(item["name"], "household_income_survey.csv")
        self.assertEqual(item["origin"], "inline")
        self.assertTrue(item["path"].startswith("attachments/inline-"))
        target = self.session.input / item["path"]
        self.assertTrue(target.is_file())
        self.assertEqual(target.stat().st_size, item["size"])
        self.assertIn("Puliyara Colony", target.read_text())
        manifest = json.loads((self.session.input / "ATTACHMENTS.json").read_text())
        self.assertEqual(manifest["attachments"], staged)
        # Re-sending the same turn is idempotent: same content hash, same single record.
        again = server._stage_inline_files(self.session, INLINE_TURN)
        self.assertEqual([entry["id"] for entry in again], [item["id"]])

    def test_staged_inline_file_resolves_and_stays_inside_the_session(self):
        server._stage_inline_files(self.session, INLINE_TURN)
        path = self.session.attachments[0]["path"]
        for supplied in (
            path,
            "household_income_survey.csv",
            str(server.CONTAINER_ROOT / "sessions" / self.session.id / "input" / path),
            "",                       # empty: fall back to this session's only table
            "attachments/wrong.csv",  # wrong guess: fall back rather than lose the file
        ):
            resolved = server._session_attachment_path(self.session, supplied)
            self.assertTrue(resolved.is_file())
            self.assertTrue(str(resolved).startswith(str(self.session.input.resolve())))
        self.session.attachments = []
        with self.assertRaises(ValueError):
            server._session_attachment_path(self.session, "/etc/passwd")


class UploadRoutingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = pathlib.Path(cls.temp.name) / "index"
        Builder(PACK, cls.output).run()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def configured_bridge(self):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.dict(
            os.environ,
            {"CODEX_NATIVE_SITE_ALIASES": "valparai_livelihoods|Valparai Livelihoods"},
        ))
        stack.enter_context(mock.patch.object(server, "SITE_PACK_PATH", PACK))
        stack.enter_context(mock.patch.object(server, "SITE_PROFILE_PATH", PACK / "site.json"))
        stack.enter_context(mock.patch.object(
            server, "VISUAL_INDEX_PATH", self.output / "site_index.sqlite"))
        stack.enter_context(mock.patch.dict(
            server.SKILLS_BY_ID, {"visual-upload": {"id": "visual-upload"}}))
        return stack

    def session_with_table(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        session = StubSession(pathlib.Path(temp.name))
        server._stage_inline_files(session, INLINE_TURN)
        return session

    def test_the_live_failing_turn_now_routes_to_visual_upload(self):
        session = self.session_with_table()
        with self.configured_bridge():
            self.assertEqual(server._upload_turn_intent(INLINE_TURN, session), "profile")
            self.assertEqual(
                server._required_first_skill(INLINE_TURN, None, session), "visual-upload")

    def test_follow_up_cross_check_routes_to_the_join_not_a_site_search(self):
        session = self.session_with_table()
        follow_up = "Now check it against the site data."
        with self.configured_bridge():
            self.assertEqual(server._upload_turn_intent(follow_up, session), "cross-join")
            self.assertEqual(
                server._required_first_skill(follow_up, None, session), "visual-upload")
            self.assertEqual(
                server._upload_turn_intent(
                    "cross-check the villages against the site pack", session),
                "cross-join",
            )

    def test_a_site_question_without_a_table_is_unaffected(self):
        empty = StubSession(pathlib.Path(tempfile.mkdtemp()))
        with self.configured_bridge():
            self.assertIsNone(server._upload_turn_intent(INLINE_TURN, empty))
            self.assertEqual(
                server._required_first_skill("What do we know about this site?", None, empty),
                "site-overview",
            )
            # A table staged in an earlier turn must not hijack later site questions.
            session = self.session_with_table()
            for unrelated in (
                "Which estates pay the highest wages?",
                "Show me where records are available at this site.",
                "How have daily wages changed since 2017?",
            ):
                self.assertIsNone(
                    server._upload_turn_intent(unrelated, session), unrelated)
                self.assertNotEqual(
                    server._required_first_skill(unrelated, None, session), "visual-upload")


if __name__ == "__main__":
    unittest.main()
