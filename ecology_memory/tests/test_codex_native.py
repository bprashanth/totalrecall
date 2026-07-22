import importlib.util
import json
import pathlib
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[2]
SERVER_PATH = ROOT / "ecology_memory" / "integration" / "codex_native" / "server.py"
SPEC = importlib.util.spec_from_file_location("codex_native_server", SERVER_PATH)
SERVER = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(SERVER)


class CodexNativeBridgeTests(unittest.TestCase):
    def test_skill_catalog_is_the_frozen_benchmark_catalog(self):
        self.assertEqual(len(SERVER.SKILLS), 12)
        self.assertIn("vegetation-greenness-trend", SERVER.SKILLS_BY_ID)
        self.assertIn("gated-species-presence-transfer", SERVER.SKILLS_BY_ID)

    def test_command_classification_exposes_skill_invocation(self):
        kind, label = SERVER._command_kind(
            "python3 /tmp/input/skill_call.py local-snake-inventory '{\"region\":\"EBTL\"}'"
        )
        self.assertEqual((kind, label), ("skill", "local-snake-inventory"))
        kind, label = SERVER._command_kind(
            "sed -n '1,200p' /tmp/input/skills/local-snake-inventory/SKILL.md"
        )
        self.assertEqual((kind, label), ("read_skill", "local-snake-inventory"))

    def test_result_summary_does_not_dump_rows(self):
        text = SERVER._summary({
            "execution": {"status": "answer", "label": "observed", "value": {
                "rows": [{"id": 1}, {"id": 2}], "source": "survey"
            }}
        })
        self.assertEqual(text, "answer · 2 rows · observed · survey")

    def test_trace_finishes_with_answer_and_audit_id(self):
        rendered = SERVER._trace_markdown({
            "type": "final", "answer": "Careful answer", "session_id": "abc",
            "turn": 2, "latency_s": 4.5,
        })
        self.assertIn("Audit id: `abc/2`", rendered)
        self.assertTrue(rendered.endswith("Careful answer"))

    def test_manual_bank_has_five_multiturn_conversations(self):
        bank = json.loads((
            ROOT / "ecology_memory" / "narrative" / "benchmarks" /
            "skills-agent-harness-v2" / "questions.json"
        ).read_text())
        self.assertEqual(len(bank["conversations"]), 5)
        self.assertTrue(all(len(item["turns"]) >= 3 for item in bank["conversations"]))


if __name__ == "__main__":
    unittest.main()
