"""Lineage must be exact: the same rows, the same aggregation, no model in the loop."""

import pathlib
import tempfile
import unittest

from dss.visual_index.build import Builder
from dss.visual_index.explain_service import ExplainService
from dss.visual_index.result_service import ResultService


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"
ECOLOGY_PACK = ROOT / "dss" / "sites" / "valparai"


class ExplainServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        cls.index_root = root / "index"
        cls.state_root = root / "state"
        Builder(PACK, cls.index_root).run()
        cls.service = ResultService(
            PACK, cls.index_root / "site_index.sqlite", cls.state_root
        )
        cls.explain = ExplainService.from_result_service(cls.service)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_unknown_result_is_refused(self):
        with self.assertRaises(LookupError):
            self.explain.explain("result-does-not-exist")

    def test_density_cell_lineage_names_its_exact_event_rows(self):
        result = self.service.query(
            "explain-orientation", "site-orientation", {}, "Tell me about this site."
        )
        lineage = self.explain.explain(result["result_id"], "event-density")
        self.assertEqual(lineage["schema_version"], "idli-explain/1")
        self.assertEqual(lineage["capability"]["capability_id"], "site-orientation")
        self.assertEqual(lineage["layer"]["layer_id"], "event-density")
        self.assertTrue(lineage["mark"]["auto_selected"])
        self.assertEqual(lineage["mark"]["kind"], "cell")
        self.assertEqual(lineage["computation"]["aggregation"], "count")
        self.assertIn("count of", lineage["computation"]["statement"])
        # The stored mark value must equal the number of contributing rows for a count.
        self.assertEqual(
            int(lineage["mark"]["stored_value"]), lineage["computation"]["contributing_rows"]
        )
        self.assertTrue(lineage["source_rows"])
        for row in lineage["source_rows"]:
            self.assertEqual(row["cell_id"], lineage["mark"]["id"])
            self.assertIn("event_id", row)
            self.assertIn("source_row", row)
            self.assertIn("event_date", row)
        # Every source id used by the rows is described with its pinned digest.
        described = {item["source_id"] for item in lineage["source_versions"]}
        self.assertTrue({row["source_id"] for row in lineage["source_rows"]} <= described)
        self.assertTrue(all(item["digest"] for item in lineage["source_versions"]))
        self.assertIn("synthetic-data", {item["code"] for item in lineage["limitations"]})

    def test_named_cell_mark_is_explained_without_auto_selection(self):
        result = self.service.query(
            "explain-orientation-2", "site-orientation", {}, "Where is the data?"
        )
        top = self.explain.explain(result["result_id"], "event-density")["top_marks"]
        lineage = self.explain.explain(result["result_id"], "event-density", top[1]["mark"])
        self.assertFalse(lineage["mark"]["auto_selected"])
        self.assertEqual(lineage["mark"]["id"], top[1]["mark"])
        self.assertEqual(
            float(lineage["computation"]["contributing_rows"]), top[1]["value"]
        )

    def test_a_click_resolves_against_the_layer_that_holds_data_not_the_boundary(self):
        """The bug: clicking a density square answered "0 source rows contributed there".

        The orientation map draws the declared boundary first and the density squares on top of
        it. Defaulting to the visual's first layer therefore explained the boundary polygon —
        which carries no countable rows — for a coordinate that lands squarely inside a density
        square. Both layers contain the point; only one of them can answer.
        """
        result = self.service.query(
            "explain-layer-choice", "site-orientation", {}, "Where is the data?"
        )
        layers = [
            layer["layer_id"] for visual in result["visuals"] for layer in visual["layers"]
        ]
        self.assertEqual(layers[:2], ["declared-aoi", "event-density"])
        cell = self.explain.load_payload(result["result_id"], "event-density")["features"][0]
        ring = cell["geometry"]["coordinates"][0]
        lat = (ring[0][1] + ring[2][1]) / 2
        lon = (ring[0][0] + ring[2][0]) / 2

        lineage = self.explain.explain(result["result_id"], None, f"at:{lat}:{lon}")
        self.assertEqual(lineage["layer"]["layer_id"], "event-density")
        self.assertTrue(lineage["layer"]["auto_selected"])
        self.assertIn("contains", lineage["layer"]["chosen_because"])
        self.assertEqual(lineage["mark"]["kind"], "cell")
        self.assertEqual(lineage["mark"]["id"], cell["id"])
        self.assertGreater(lineage["computation"]["contributing_rows"], 0)
        self.assertTrue(lineage["source_rows"])
        # The boundary layer was considered and passed over, and the reason is legible.
        passed_over = {
            item["layer_id"]: item for item in lineage["layer"]["alternatives"]
        }
        self.assertEqual(passed_over["declared-aoi"]["marks_with_a_value"], 0)

        # Naming the boundary layer explicitly is still honoured, and then the caller is told
        # which layer would have answered instead of being left with an empty result.
        boundary = self.explain.explain(result["result_id"], "declared-aoi", f"at:{lat}:{lon}")
        self.assertEqual(boundary["layer"]["layer_id"], "declared-aoi")
        self.assertFalse(boundary["layer"]["auto_selected"])

    def test_a_clicked_square_is_named_by_its_extent_not_by_its_id(self):
        """A click at 10.305 lands in the square starting at 10.300; say that, do not print an id.

        The user's complaint was that the answer looked like the system had quietly swapped their
        coordinates for different ones. The square is the same square either way; only the way it
        is named to a person changes.
        """
        result = self.service.query(
            "explain-square-language", "site-orientation", {}, "Where is the data?"
        )
        payload = self.explain.load_payload(result["result_id"], "event-density")
        cell = next(
            feature for feature in payload["features"]
            if str(feature.get("id", "")).startswith("g0.0")
        )
        west, south = cell["geometry"]["coordinates"][0][0]
        inside_lat, inside_lon = south + 0.005, west + 0.005
        lineage = self.explain.explain(
            result["result_id"], "event-density", f"at:{inside_lat}:{inside_lon}"
        )
        mark = lineage["mark"]
        self.assertEqual(mark["kind"], "cell")
        self.assertEqual(mark["id"], cell["id"])
        self.assertEqual(mark["resolution"], "coordinate")
        # The description says how big the square is, which point of theirs it covers, and the
        # band it spans — computed from the geometry the layer actually stored.
        self.assertIn("km square", mark["description"])
        self.assertIn("covering your point", mark["description"])
        self.assertIn(f"{south:.3f}", mark["description"])
        self.assertNotIn("g0.0", mark["description"])
        self.assertNotIn("g0.0", lineage["computation"]["statement"])
        self.assertIn(mark["description_short"], lineage["computation"]["statement"])
        # Other marks a caller might offer are nameable too.
        self.assertTrue(all("description" in item for item in lineage["top_marks"]))

    def test_point_mark_is_one_unchanged_source_row(self):
        result = self.service.query(
            "explain-entity", "entity-record-map", {"entity": "Karumalai Estate"},
            "Where are Karumalai Estate records?",
        )
        payload = self.explain.load_payload(result["result_id"], "observations")
        event_id = payload["features"][0]["id"]
        lineage = self.explain.explain(result["result_id"], "observations", event_id)
        self.assertEqual(lineage["mark"]["kind"], "event")
        self.assertEqual(lineage["computation"]["aggregation"], "none")
        self.assertEqual(lineage["computation"]["contributing_rows"], 1)
        row = lineage["source_rows"][0]
        self.assertEqual(row["event_id"], event_id)
        self.assertEqual(
            row["latitude"], payload["features"][0]["geometry"]["coordinates"][1]
        )
        self.assertEqual(
            lineage["question"]["bindings"]["entity"], "Karumalai Estate"
        )

    def test_time_bucket_mark_reports_the_mean_of_its_measurement_rows(self):
        result = self.service.query(
            "explain-metric", "metric-time-series", {"metric": "daily_wage"},
            "How have daily wages changed?",
        )
        series = self.explain.load_payload(result["result_id"], "metric-series")
        point = series[3]
        bucket = f"{point['year']:04d}-{point['month']:02d}"
        lineage = self.explain.explain(result["result_id"], "metric-series", bucket)
        self.assertEqual(lineage["mark"]["kind"], "time_bucket")
        self.assertEqual(lineage["computation"]["aggregation"], "mean")
        self.assertEqual(lineage["computation"]["plane"], "measurements")
        self.assertTrue(lineage["source_rows"])
        values = [row["value"] for row in lineage["source_rows"]]
        self.assertAlmostEqual(sum(values) / len(values), point["value"], places=6)
        for row in lineage["source_rows"]:
            self.assertEqual(row["metric"], "daily_wage")
            self.assertEqual(row["year"], point["year"])

    def test_coordinate_mark_resolves_the_containing_cell_not_the_largest(self):
        """A clicked location must explain the cell under the click, never the hotspot."""
        result = self.service.query(
            "explain-coordinate-1", "site-orientation", {}, "Where is the data?"
        )
        payload = self.explain.load_payload(result["result_id"], "event-density")
        top = self.explain.explain(result["result_id"], "event-density")["top_marks"]
        # Pick a NON-largest cell and click its centre.
        target = next(
            feature for feature in payload["features"]
            if feature["id"] == top[2]["mark"]
        )
        ring = target["geometry"]["coordinates"][0]
        lon = sum(point[0] for point in ring[:4]) / 4
        lat = sum(point[1] for point in ring[:4]) / 4
        for mark in (f"at:{lat}:{lon}", {"lat": lat, "lon": lon}):
            lineage = self.explain.explain(result["result_id"], "event-density", mark)
            self.assertEqual(lineage["mark"]["resolution"], "coordinate")
            self.assertFalse(lineage["mark"]["auto_selected"])
            self.assertEqual(lineage["mark"]["id"], target["id"])
            self.assertNotEqual(lineage["mark"]["id"], top[0]["mark"])
            self.assertEqual(
                lineage["computation"]["contributing_rows"],
                target["properties"]["records"],
            )
            for row in lineage["source_rows"]:
                self.assertEqual(row["cell_id"], target["id"])

    def test_coordinate_mark_resolves_the_nearest_point_within_radius(self):
        result = self.service.query(
            "explain-coordinate-2", "entity-record-map", {"entity": "Karumalai Estate"},
            "Where are Karumalai Estate records?",
        )
        payload = self.explain.load_payload(result["result_id"], "observations")
        # Click slightly off one record, inside the hit radius (~250 m). Records cluster, so
        # the correct answer is whichever stored point is nearest to the click.
        lon, lat = payload["features"][1]["geometry"]["coordinates"]
        click_lat, click_lon = lat + 0.0008, lon - 0.0008
        expected = min(
            payload["features"],
            key=lambda feature: (
                (feature["geometry"]["coordinates"][0] - click_lon) ** 2
                + (feature["geometry"]["coordinates"][1] - click_lat) ** 2
            ),
        )
        lineage = self.explain.explain(
            result["result_id"], "observations", f"at:{click_lat}:{click_lon}"
        )
        self.assertEqual(lineage["mark"]["resolution"], "coordinate")
        self.assertEqual(lineage["mark"]["kind"], "event")
        self.assertEqual(lineage["mark"]["id"], expected["id"])
        self.assertEqual(lineage["computation"]["contributing_rows"], 1)
        self.assertEqual(lineage["source_rows"][0]["event_id"], expected["id"])

    def test_coordinate_miss_is_reported_never_swapped_for_the_largest_mark(self):
        result = self.service.query(
            "explain-coordinate-3", "site-orientation", {}, "Orientation please."
        )
        lineage = self.explain.explain(
            result["result_id"], "event-density", "at:0.0:0.0"
        )
        self.assertEqual(lineage["mark"]["resolution"], "coordinate")
        self.assertEqual(lineage["mark"]["kind"], "no_mark_at_location")
        self.assertFalse(lineage["mark"]["auto_selected"])
        self.assertEqual(lineage["source_rows"], [])
        self.assertEqual(lineage["computation"]["contributing_rows"], 0)
        self.assertIn("No mark exists at", lineage["computation"]["statement"])
        self.assertIn("not evidence of absence", lineage["computation"]["statement"])
        # The auto-largest default remains only for the truly mark-less question.
        bare = self.explain.explain(result["result_id"], "event-density")
        self.assertTrue(bare["mark"]["auto_selected"])
        self.assertEqual(bare["mark"]["resolution"], "auto-largest")
        self.assertTrue(
            bare["computation"]["statement"].startswith("AUTO-SELECTED:")
        )

    def test_unknown_layer_is_refused_and_unresolved_mark_is_explicit(self):
        result = self.service.query(
            "explain-orientation-3", "site-orientation", {}, "Orientation please."
        )
        with self.assertRaises(LookupError):
            self.explain.explain(result["result_id"], "no-such-layer")
        lineage = self.explain.explain(
            result["result_id"], "event-density", "not-a-real-mark"
        )
        self.assertEqual(lineage["mark"]["kind"], "unresolved")
        self.assertEqual(lineage["source_rows"], [])
        self.assertIn("did not match", lineage["computation"]["statement"])


class CategoryMarkTest(unittest.TestCase):
    """A declared category must be explainable as itself, on the ecology pack that declares one."""

    SOURCE = "dryad-rjdfn2zc3-restoration-birds"
    CATEGORY = "Site_type"

    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        Builder(ECOLOGY_PACK, root).run()
        cls.state = root / "state"
        cls.service = ResultService(ECOLOGY_PACK, root / "site_index.sqlite", cls.state)
        cls.explain = ExplainService(ECOLOGY_PACK, root / "site_index.sqlite", cls.state)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def test_a_named_category_beats_a_layer_that_merely_carries_it(self):
        """Asking about "Benchmark" must reach the row that IS Benchmark, not a site tagged so.

        The stratified result draws 69 survey sites, each tagged with its plot type, and a
        three-row category table. Both "contain" the word; only the table can say how Benchmark
        compares, and the sites layer was winning by being drawn first.
        """
        result = self.service.query(
            "explain-category", "stratified-survey-summary",
            {"source_id": self.SOURCE, "category_property": self.CATEGORY},
            "How do the categories compare?",
        )
        categories = self.explain.load_payload(
            result["result_id"], "stratified-category-summary")
        self.assertTrue(categories, "the fixture must compute a category table")
        wanted = str(categories[0].get("category"))

        lineage = self.explain.explain(result["result_id"], None, wanted)
        self.assertEqual(lineage["layer"]["layer_id"], "stratified-category-summary")
        self.assertEqual(lineage["mark"]["id"], wanted)
        self.assertFalse(lineage["mark"]["auto_selected"])
        # A computed summary row is real lineage, not an unresolved mark.
        self.assertEqual(lineage["computation"]["aggregation"], "summary_row")
        self.assertIn(wanted, lineage["computation"]["statement"])
        self.assertNotIn("did not match", lineage["computation"]["statement"])
        self.assertEqual(lineage["computation"]["contributing_rows"], 1)

    def test_the_marks_a_caller_could_ask_about_are_offered(self):
        result = self.service.query(
            "explain-offer", "stratified-survey-summary",
            {"source_id": self.SOURCE, "category_property": self.CATEGORY},
            "Compare the categories.",
        )
        lineage = self.explain.explain(result["result_id"], "stratified-category-summary")
        self.assertTrue(lineage["top_marks"])
        self.assertTrue(all(item.get("mark") for item in lineage["top_marks"]))


if __name__ == "__main__":
    unittest.main()
