import importlib.util
import json
import pathlib
import sqlite3
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE_PATH = ROOT / "dss" / "visual_index" / "build.py"
SPEC = importlib.util.spec_from_file_location("visual_index_build", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class ValparaiVisualIndexTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.output = pathlib.Path(cls.temp.name)
        started = time.perf_counter()
        cls.bundle = MODULE.Builder(ROOT / "dss" / "sites" / "valparai", cls.output).run()
        cls.elapsed = time.perf_counter() - started
        cls.db = sqlite3.connect(cls.output / "site_index.sqlite")

    @classmethod
    def tearDownClass(cls):
        cls.db.close()
        cls.temp.cleanup()

    def test_build_is_complete_and_fast(self):
        report = json.loads((self.output / "build_report.json").read_text())
        self.assertEqual(report["integrity"], "ok")
        self.assertEqual(report["sources"], 19)
        self.assertEqual(report["events"], 45_328)
        self.assertEqual(report["georeferenced_events"], 42_348)
        self.assertEqual(report["effort_rows"], 974)
        self.assertEqual(report["measurements"], 68_194)
        self.assertEqual(report["interactions"], 5_622)
        self.assertEqual(report["cell_features"], 28_764)
        self.assertEqual(report["entities"], 1_145)
        self.assertEqual(report["cells"], 302)
        self.assertGreaterEqual(report["ready_views"], 8)
        self.assertLess(self.elapsed, 3.0)

    def test_feature_cube_retains_units_support_and_evidence_class(self):
        count, features, cells = self.db.execute(
            """SELECT COUNT(*),COUNT(DISTINCT feature_id),COUNT(DISTINCT cell_id)
               FROM cell_features
               WHERE source_id='earth-engine-feature-cube-2024'"""
        ).fetchone()
        self.assertEqual(count, 28_764)
        self.assertEqual(features, 97)
        self.assertEqual(cells, 302)
        tree_score = self.db.execute(
            """SELECT MIN(value),MAX(value),MIN(unit),MIN(evidence_class),
                      MIN(source_asset),MIN(scale_m)
               FROM cell_features WHERE feature_id='dw_trees_probability'"""
        ).fetchone()
        self.assertGreaterEqual(tree_score[0], 0)
        self.assertLessEqual(tree_score[1], 1)
        self.assertEqual(tree_score[2], "probability-score")
        self.assertEqual(tree_score[3], "modelled")
        self.assertEqual(tree_score[4], "GOOGLE/DYNAMICWORLD/V1")
        self.assertEqual(tree_score[5], 100)
        label = self.db.execute(
            """SELECT MIN(feature_label),MIN(feature_description)
               FROM cell_features WHERE feature_id='dw_trees_probability'"""
        ).fetchone()
        self.assertEqual(label[0], "Dynamic World trees class score")
        self.assertIn("model outputs", label[1])
        july = self.db.execute(
            """SELECT COUNT(*) FROM cell_features
               WHERE feature_id='s2_ndvi_m07_median'"""
        ).fetchone()[0]
        self.assertEqual(july, 0)

    def test_restoration_inventory_retains_plot_traits_and_conservation_fields(self):
        counts = self.db.execute(
            """SELECT COUNT(*),COUNT(DISTINCT location_id),COUNT(DISTINCT metric)
               FROM measurements
               WHERE source_id='dryad-8kprr4xvb-restoration-opportunities'"""
        ).fetchone()
        self.assertEqual(counts, (11_239, 132, 7))
        events = dict(
            self.db.execute(
                """SELECT event_type,COUNT(*) FROM events
                   WHERE source_id='dryad-8kprr4xvb-restoration-opportunities'
                   GROUP BY event_type"""
            ).fetchall()
        )
        self.assertEqual(events["adult_tree_inventory"], 2195)
        self.assertEqual(events["regeneration_inventory"], 1632)
        lantana = self.db.execute(
            """SELECT COUNT(*),SUM(count_value)
               FROM events JOIN entities USING(entity_id)
               WHERE source_id='dryad-8kprr4xvb-restoration-opportunities'
                 AND canonical_name='Lantana camara'
                 AND json_extract(hierarchy_json,'$.origin')='Introduced'"""
        ).fetchone()
        self.assertGreater(lantana[0], 0)
        self.assertGreater(lantana[1], 0)
        trait = json.loads(
            self.db.execute(
                """SELECT properties_json FROM events
                   WHERE source_id='dryad-8kprr4xvb-restoration-opportunities'
                     AND json_extract(properties_json,'$.IUCN_status')='VU'
                     AND json_extract(properties_json,'$.disperser') IS NOT NULL
                   LIMIT 1"""
            ).fetchone()[0]
        )
        self.assertIn("Distribution", trait)
        self.assertIn("disperser", trait)

    def test_duplicate_upstream_keys_do_not_drop_source_rows(self):
        expected = {
            "zenodo-7008315": 3741,
            "zenodo-11903722": 879,
            "zenodo-13910696": 638,
            "zenodo-10077040": 3684,
            "zenodo-7060430": 2473,
            "zenodo-7457732": 3744,
            "dryad-rjdfn2zc3-restoration-birds": 10752,
            "dryad-b2rbnzsff-shade-birds": 2965,
            "gbif-v6ku49-butterflies": 231,
            "gbif-ysrzbw-frogs": 143,
            "gbif-d96cu4-herpetofauna": 435,
            "gbif-4e53vk-threatened-trees": 8397,
            "gbif-2bqrzp-frugivory": 2640,
            "gbif-utzvkm-seed-predation": 779,
            "dryad-8kprr4xvb-restoration-opportunities": 3827,
        }
        actual = dict(
            self.db.execute(
                "SELECT source_id,COUNT(*) FROM events GROUP BY source_id"
            ).fetchall()
        )
        self.assertEqual(actual, expected)

    def test_common_and_scientific_names_resolve_to_one_entity(self):
        row = self.db.execute(
            """SELECT canonical_name,display_name,COUNT(*)
               FROM events JOIN entities USING(entity_id)
               WHERE canonical_name='Bos gaurus'"""
        ).fetchone()
        self.assertEqual(row[0], "Bos gaurus")
        self.assertEqual(row[1], "Gaur")
        self.assertGreater(row[2], 750)
        aliases = self.db.execute(
            "SELECT COUNT(*) FROM entity_aliases WHERE alias_key IN ('gaur','bos gaurus')"
        ).fetchone()[0]
        self.assertEqual(aliases, 2)

    def test_plot_rows_join_to_real_locations(self):
        joined = self.db.execute(
            """SELECT COUNT(*) FROM events
               WHERE source_id='zenodo-10077040' AND cell_id IS NOT NULL"""
        ).fetchone()[0]
        self.assertEqual(joined, 3684)

    def test_effort_is_not_inferred_from_presence(self):
        sources = self.db.execute(
            "SELECT DISTINCT source_id FROM effort ORDER BY source_id"
        ).fetchall()
        self.assertEqual(
            sources,
            [
                ("dryad-8kprr4xvb-restoration-opportunities",),
                ("dryad-rjdfn2zc3-restoration-birds",),
                ("gbif-v6ku49-butterflies",),
                ("gbif-ysrzbw-frogs",),
                ("zenodo-7060430",),
            ],
        )
        georeferenced = self.db.execute(
            "SELECT COUNT(*) FROM effort WHERE cell_id IS NOT NULL"
        ).fetchone()[0]
        self.assertGreater(georeferenced, 200)

    def test_plot_and_station_measurements_keep_location_units_and_lineage(self):
        by_source = dict(
            self.db.execute(
                "SELECT source_id,COUNT(*) FROM measurements GROUP BY source_id"
            ).fetchall()
        )
        self.assertEqual(by_source["zenodo-10077040"], 10_956)
        self.assertEqual(by_source["zenodo-7457732"], 880)
        self.assertEqual(by_source["zenodo-18646715"], 44_490)
        mapped = self.db.execute(
            """SELECT COUNT(*) FROM measurements
               WHERE source_id='zenodo-7457732'
                 AND location_id IS NOT NULL AND cell_id IS NOT NULL"""
        ).fetchone()[0]
        self.assertEqual(mapped, 880)
        daily = self.db.execute(
            """SELECT COUNT(*),COUNT(DISTINCT metric),MIN(unit)
               FROM measurements WHERE source_id='zenodo-18646715'
                 AND metric='daily_precipitation'"""
        ).fetchone()
        self.assertEqual(daily, (4391, 1, "mm/day"))
        properties = json.loads(
            self.db.execute(
                """SELECT properties_json FROM measurements
                   WHERE source_id='zenodo-10077040'
                     AND metric='canopy_cover' LIMIT 1"""
            ).fetchone()[0]
        )
        self.assertIn("Fragment", properties)

    def test_omitted_optional_fields_do_not_read_empty_csv_headers(self):
        event_types = dict(
            self.db.execute(
                """SELECT event_type,COUNT(*) FROM events
                   WHERE source_id='zenodo-7457732' GROUP BY event_type"""
            ).fetchall()
        )
        self.assertEqual(event_types["adult_tree_measurement"], 2177)
        self.assertEqual(event_types["woody_regeneration_measurement"], 1567)
        self.assertNotIn("TRUE", event_types)

    def test_darwin_core_sources_keep_methods_hierarchy_and_effort_denominators(self):
        hierarchy = json.loads(
            self.db.execute(
                """SELECT hierarchy_json FROM entities
                   WHERE canonical_name='Papilio polymnestor'"""
            ).fetchone()[0]
        )
        self.assertEqual(hierarchy["class"], "Insecta")
        self.assertEqual(hierarchy["order"], "Lepidoptera")
        butterfly_effort = self.db.execute(
            """SELECT COUNT(*),SUM(effort_value),MIN(effort_unit)
               FROM effort WHERE source_id='gbif-v6ku49-butterflies'"""
        ).fetchone()
        self.assertEqual(butterfly_effort, (8, 278.0, "point-counts"))
        frog_effort = self.db.execute(
            """SELECT COUNT(*),SUM(effort_value),MIN(effort_unit)
               FROM effort WHERE source_id='gbif-ysrzbw-frogs'"""
        ).fetchone()
        self.assertEqual(frog_effort, (13, 567.5, "minutes"))
        methods = dict(
            self.db.execute(
                """SELECT event_type,COUNT(*) FROM events
                   WHERE source_id='gbif-d96cu4-herpetofauna'
                   GROUP BY event_type"""
            ).fetchall()
        )
        self.assertEqual(methods["time-constrained visual encounter survey"], 410)
        self.assertEqual(methods["ad-hoc observation"], 25)

    def test_interactions_require_an_explicit_source_mapping(self):
        count, relation, sources = self.db.execute(
            """SELECT COUNT(*),MIN(interaction_type),COUNT(DISTINCT source_id)
               FROM interactions"""
        ).fetchone()
        self.assertEqual(count, 5_622)
        self.assertEqual(relation, "camera_detected_at_focal_seed_tree")
        self.assertEqual(sources, 3)
        cullenia = self.db.execute(
            """SELECT COUNT(DISTINCT i.subject_entity_id)
               FROM interactions i JOIN entities e ON e.entity_id=i.object_entity_id
               WHERE e.canonical_name='Cullenia exarillata'"""
        ).fetchone()[0]
        self.assertGreater(cullenia, 5)

    def test_evidence_classes_and_source_capabilities_are_explicit(self):
        classes = self.db.execute(
            "SELECT evidence_class,COUNT(*) FROM events GROUP BY evidence_class"
        ).fetchall()
        self.assertEqual(classes, [("observed", self.bundle["build"]["events"])])
        capabilities = json.loads(
            self.db.execute(
                "SELECT capabilities_json FROM sources WHERE source_id='zenodo-7060430'"
            ).fetchone()[0]
        )
        self.assertIn("mappable", capabilities)
        self.assertIn("has_effort", capabilities)

    def test_every_probe_has_a_declared_visual(self):
        questions = json.loads(
            (ROOT / "dss" / "sites" / "valparai" / "questions.json").read_text()
        )["questions"]
        views = {item["view_id"]: item for item in self.bundle["views"]}
        for question in questions:
            with self.subTest(question=question["id"]):
                self.assertIn(question["first_visual"], views)
        self.assertEqual(views["donor_coverage_and_gate_map"]["availability"], "partial")
        self.assertEqual(views["value_of_information_map"]["availability"], "blocked")

    def test_preview_is_a_real_visual_artifact(self):
        preview = self.output / "preview.png"
        self.assertTrue(preview.is_file())
        self.assertGreater(preview.stat().st_size, 30_000)

    def test_interactive_filter_query_is_immediate(self):
        entity_id = self.db.execute(
            "SELECT entity_id FROM entity_aliases WHERE alias_key='lion tailed macaque'"
        ).fetchone()[0]
        started = time.perf_counter()
        rows = self.db.execute(
            """SELECT cell_id,COUNT(*),MIN(event_date),MAX(event_date)
               FROM events WHERE entity_id=? AND cell_id IS NOT NULL
               GROUP BY cell_id ORDER BY COUNT(*) DESC""",
            (entity_id,),
        ).fetchall()
        elapsed = time.perf_counter() - started
        self.assertGreater(len(rows), 10)
        self.assertLess(elapsed, 0.1)


if __name__ == "__main__":
    unittest.main()
