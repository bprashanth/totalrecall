import importlib.util
import io
import json
import os
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "step_chat", ROOT / "integration" / "step_chat.py")
STEP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(STEP)


class StepChatTests(unittest.TestCase):
    def test_checkpoint_is_rendered_and_saved_before_confirmation(self):
        with tempfile.TemporaryDirectory() as directory:
            store = STEP.TraceStore({"context": "ebtl"}, Path(directory))
            turn = store.new_turn("What birds are documented?")
            output = io.StringIO()
            display = STEP.StepDisplay(
                store, turn, STEP.Paint(False), False,
                input_stream=io.StringIO("?\ny\n"), output_stream=output)
            display("capability_selected", {
                "model": "qwen9b",
                "parsed": {"mode": "execute"},
                "selected": [{"entity": "EBTL bird inventory",
                              "description": "Published local bird inventory",
                              "evidence": "observed", "grain": "site inventory"}],
                "raw_output": '{"mode":"execute"}',
            })
            rendered = output.getvalue()
            self.assertIn("CAPABILITY SELECTED", rendered)
            self.assertIn("EBTL bird inventory", rendered)
            self.assertIn("Why this stage exists", rendered)
            self.assertNotIn("\033[", rendered)
            latest = json.loads((Path(directory) / "latest.json").read_text())
            self.assertEqual(latest["turns"][0]["stages"][0]["stage"],
                             "capability_selected")

    def test_no_stops_before_the_next_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            store = STEP.TraceStore({}, Path(directory))
            turn = store.new_turn("test")
            display = STEP.StepDisplay(
                store, turn, STEP.Paint(False), False,
                input_stream=io.StringIO("n\n"), output_stream=io.StringIO())
            with self.assertRaises(STEP.StopTurn):
                display("execution_preview", {
                    "model": None, "ir": {"op": "REGION", "place": "EBTL"},
                    "schema": {"valid": True, "ops": ["REGION"], "holes": []},
                })
            latest = json.loads((Path(directory) / "latest.json").read_text())
            self.assertEqual(latest["turns"][0]["current_stage"], "execution_preview")

    def test_color_mode_obeys_no_color(self):
        previous = os.environ.get("NO_COLOR")
        os.environ["NO_COLOR"] = "1"
        try:
            self.assertFalse(STEP.color_enabled("auto"))
            self.assertTrue(STEP.color_enabled("always"))
        finally:
            if previous is None:
                os.environ.pop("NO_COLOR", None)
            else:
                os.environ["NO_COLOR"] = previous


if __name__ == "__main__":
    unittest.main()
