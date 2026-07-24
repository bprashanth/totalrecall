import importlib.util
import pathlib
import unittest


MODULE_PATH = pathlib.Path(__file__).with_name("sanitize_traces.py")
SPEC = importlib.util.spec_from_file_location("sanitize_traces", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class SanitizeTracesTest(unittest.TestCase):
    def test_google_key_shape_is_redacted_in_nested_trace_fields(self):
        google_key = "AIza" + "A" * 35
        value = {
            "command": f"curl 'https://example.invalid/data?key={google_key}'",
            "result": [{"stdout": f"bootstrap={google_key}"}],
        }
        sanitized, replacements = MODULE.sanitize_value(value)
        rendered = repr(sanitized)
        self.assertNotIn(google_key, rendered)
        self.assertIn("[REDACTED_GOOGLE_API_KEY]", rendered)
        self.assertEqual(replacements, 2)

    def test_non_google_url_key_and_existing_token_rules_remain_covered(self):
        value = {
            "url": "https://example.invalid/data?key=client-value-123456",
            "authorization": "Bearer abcdefghijklmnopqrstuvwxyz",
            "provider": "api_key=provider-value-123456",
        }
        sanitized, replacements = MODULE.sanitize_value(value)
        self.assertEqual(
            sanitized["url"],
            "https://example.invalid/data?key=[REDACTED_TOKEN]",
        )
        self.assertEqual(
            sanitized["authorization"],
            "Bearer [REDACTED_TOKEN]",
        )
        self.assertEqual(
            sanitized["provider"],
            "api_key=[REDACTED_TOKEN]",
        )
        self.assertEqual(replacements, 3)

    def test_safe_text_is_unchanged(self):
        value = {"status": "usage limit", "url": "https://example.invalid/public"}
        sanitized, replacements = MODULE.sanitize_value(value)
        self.assertEqual(sanitized, value)
        self.assertEqual(replacements, 0)


if __name__ == "__main__":
    unittest.main()
