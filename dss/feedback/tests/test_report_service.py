import json
import pathlib
import tempfile
import unittest

from dss.feedback.report_service import ReportService, visible_transcript_from_audit


class ReportServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)
        self.service = ReportService(
            self.root,
            {"repository": "example/public-reports", "labels": ["user-report"]},
        )

    def tearDown(self):
        self.temp.cleanup()

    def test_audit_transcript_excludes_hidden_and_tool_events(self):
        audit = self.root / "audit.jsonl"
        events = [
            {"type": "request", "message": "Show all raptors"},
            {"type": "tool_output", "output": "secret internal trace"},
            {"type": "status", "text": "hidden progress"},
            {
                "type": "final",
                "answer": (
                    '<!-- idli-result:{"result_id":"internal-result"} -->\n'
                    "Here is the map."
                ),
            },
        ]
        audit.write_text("\n".join(json.dumps(item) for item in events) + "\n")
        self.assertEqual(visible_transcript_from_audit(audit), [
            {"role": "user", "content": "Show all raptors"},
            {"role": "assistant", "content": "Here is the map."},
        ])

    def test_draft_defaults_are_reviewable_and_submission_is_separate(self):
        draft = self.service.draft(
            session_id="chat-1",
            turn=4,
            description="The broad selection showed the wrong thing.",
            include_conversation=True,
            transcript=[
                {"role": "user", "content": "Show all"},
                {"role": "assistant", "content": "Here is one"},
            ],
            diagnostics={"model": "idli-insight"},
        )
        self.assertEqual(draft["status"], "draft")
        self.assertTrue(draft["requires_confirmation"])
        self.assertTrue(draft["include_conversation"])
        self.assertIn("public issue", draft["public_warning"])
        self.assertIn("## Conversation included by the reporter", draft["body"])
        with self.assertRaises(PermissionError):
            self.service.submit(draft["report_id"], confirmed=False)
        submitted = self.service.submit(draft["report_id"], confirmed=True)
        self.assertEqual(submitted["status"], "ready_for_browser_confirmation")
        self.assertFalse(submitted["submitted"])
        self.assertIn("example/public-reports/issues/new", submitted["url"])

    def test_transcript_can_be_excluded(self):
        draft = self.service.draft(
            session_id="chat-2", turn=1, description="Bad visual",
            include_conversation=False,
            transcript=[{"role": "user", "content": "private conversation"}],
        )
        self.assertFalse(draft["include_conversation"])
        self.assertEqual(draft["conversation_messages"], 0)
        self.assertNotIn("private conversation", draft["body"])


if __name__ == "__main__":
    unittest.main()
