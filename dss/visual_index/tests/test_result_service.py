import hashlib
import json
import pathlib
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

import jsonschema

from dss.visual_index.build import Builder
from dss.visual_index.result_service import ResultService, make_server


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai"
IDLISSEUS_SCHEMA = (
    ROOT.parent / "idlisseus" / "dss" / "contracts" / "idli-result.schema.json"
)


class ValparaiResultServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.temp.name)
        cls.index_root = cls.root / "index"
        cls.state_root = cls.root / "state"
        Builder(PACK, cls.index_root).run()
        cls.service = ResultService(
            PACK, cls.index_root / "site_index.sqlite", cls.state_root
        )
        cls.schema = (
            json.loads(IDLISSEUS_SCHEMA.read_text(encoding="utf-8"))
            if IDLISSEUS_SCHEMA.is_file() else None
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_contract(self, result):
        self.assertEqual(result["schema_version"], "idli-result/1")
        if self.schema:
            jsonschema.Draft202012Validator(self.schema).validate(result)

    def test_real_site_orientation_is_visual_first(self):
        result = self.service.query(
            "orientation-1", "site-orientation", {}, "Tell me about Valparai."
        )
        self.assert_contract(result)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["visuals"][0]["visual_type"], "map")
        self.assertEqual(
            result["visuals"][0]["summary"]["denominators"]["records"], 13_577
        )
        self.assertEqual(len(result["audit"]["source_versions"]), 7)
        for layer in result["visuals"][0]["layers"]:
            resolved = self.service.load_data(result["result_id"], layer["data_ref"]["handle"])
            self.assertIsNotNone(resolved)

    def test_real_entity_query_returns_source_linked_valparai_points(self):
        result = self.service.query(
            "presence-1",
            "observed-presence-map",
            {"entity": "lion-tailed macaque"},
            "Where have lion-tailed macaques been recorded?",
        )
        self.assert_contract(result)
        self.assertGreater(
            result["visuals"][0]["summary"]["denominators"]["records"], 10
        )
        self.assertIn("observed", result["answer"]["evidence_classes"])
        rows = self.service.load_data(result["result_id"], "source-rows")
        self.assertIsNotNone(rows)
        decoded = json.loads(rows[1])
        self.assertTrue(all(row["source_id"] and row["source_row"] for row in decoded))

    def test_empty_target_keeps_surrounding_data_and_offers_transfer(self):
        result = self.service.query(
            "surrounding-1",
            "observed-presence-map",
            {"entity": "Axis axis"},
            "Is Axis axis present here?",
        )
        self.assert_contract(result)
        counts = result["visuals"][0]["summary"]["denominators"]
        self.assertEqual(counts["target_records"], 0)
        self.assertGreater(counts["context_records"], 0)
        self.assertEqual(result["visuals"][0]["view"], "surrounding-data")
        self.assertIn(
            "test-transfer", {action["action_id"] for action in result["actions"]}
        )
        self.assertIn(
            "no-target-records",
            {item["code"] for item in result["limitations"]},
        )

    def test_real_metric_series_has_units_and_coverage(self):
        result = self.service.query(
            "rainfall-1",
            "metric-time-series",
            {"metric": "rainfall"},
            "How has rainfall changed over the available period?",
        )
        self.assert_contract(result)
        visual = result["visuals"][0]
        self.assertEqual(visual["visual_type"], "chart")
        self.assertGreater(visual["summary"]["denominators"]["months"], 100)
        self.assertTrue(visual["summary"]["denominators"]["units"])
        self.assertIsNotNone(
            self.service.load_data(result["result_id"], "coverage-strip")
        )

    def test_unavailable_model_capability_is_explicitly_blocked(self):
        result = self.service.query(
            "transfer-1",
            "gated-transfer",
            {
                "entity": "Macaca silenus",
                "donor_scope": "context",
                "target_scope": "target",
            },
            "Can the surrounding data be transferred?",
        )
        self.assert_contract(result)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["answer"]["evidence_classes"], ["missing"])
        self.assertEqual(result["limitations"][0]["code"], "capability-not-ready")

    def test_result_and_payloads_are_immutable(self):
        first = self.service.query(
            "immutable-1", "site-orientation", {}, "Tell me about the site."
        )
        second = self.service.query(
            "immutable-1", "site-orientation", {}, "Tell me about the site."
        )
        self.assertEqual(first, second)
        stored = self.service.load_result(first["result_id"])
        self.assertEqual(stored, first)

    def test_internal_http_surface_requires_token_and_serves_handles(self):
        server = make_server(self.service, "127.0.0.1", 0, "test-token")
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with self.assertRaises(urllib.error.HTTPError) as denied:
                urllib.request.urlopen(f"{base}/v1/results/unknown", timeout=2)
            self.assertEqual(denied.exception.code, 401)

            body = json.dumps({
                "request_id": "http-orientation-1",
                "capability_id": "site-orientation",
                "arguments": {},
                "question": "Tell me about Valparai.",
            }).encode()
            request = urllib.request.Request(
                f"{base}/v1/results/query",
                data=body,
                headers={
                    "Authorization": "Bearer test-token",
                    "Content-Type": "application/json",
                },
            )
            result = json.loads(urllib.request.urlopen(request, timeout=3).read())
            self.assert_contract(result)
            handle = result["visuals"][0]["layers"][0]["data_ref"]["handle"]
            data_request = urllib.request.Request(
                f"{base}/v1/results/{result['result_id']}/data/{handle}",
                headers={"Authorization": "Bearer test-token"},
            )
            response = urllib.request.urlopen(data_request, timeout=3)
            self.assertEqual(response.headers.get_content_type(), "application/geo+json")
            payload = response.read()
            self.assertEqual(json.loads(payload)["type"], "FeatureCollection")
            expected = result["visuals"][0]["layers"][0]["data_ref"]["digest"]
            self.assertEqual("sha256:" + hashlib.sha256(payload).hexdigest(), expected)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

    def test_result_handles_cannot_escape_pinned_state(self):
        self.assertIsNone(self.service.load_result("../site"))
        self.assertIsNone(self.service.load_data("anything", "../site.json"))


if __name__ == "__main__":
    unittest.main()
