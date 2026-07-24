import csv
import json
import pathlib
import tempfile
import unittest

from dss.visual_index.derive_grouped_indicators import derive


class DeriveGroupedIndicatorsTest(unittest.TestCase):
    def test_declarative_filters_aggregations_and_lineage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            (root / "dimensions.csv").write_text(
                "plot,category,lat,lon\np1,A,10,20\np2,B,11,21\n",
                encoding="utf-8",
            )
            (root / "observations.csv").write_text(
                "plot,name,kind,value,status\n"
                "p1,x,tree,2,EN\n"
                "p1,y,tree,3,LC\n"
                "p1,y,shrub,7,LC\n"
                "p2,z,tree,,VU\n",
                encoding="utf-8",
            )
            recipe = {
                "recipe_id": "fixture",
                "version": "1",
                "method_references": ["method-card"],
                "dimensions": {
                    "path": "dimensions.csv",
                    "key": "plot",
                    "fields": [
                        {"column": "plot", "output": "plot_id"},
                        {"column": "category", "output": "category"},
                    ],
                },
                "inputs": {
                    "records": {
                        "path": "observations.csv",
                        "group_by": "plot",
                    }
                },
                "rollups": [
                    {
                        "metric_id": "trees",
                        "label": "Trees",
                        "unit": "count",
                        "evidence_class": "derived",
                        "method_id": "method-card",
                        "input": "records",
                        "operation": "row_count",
                        "filter": {"field": "kind", "eq": "tree"},
                    },
                    {
                        "metric_id": "tree_species",
                        "label": "Tree species",
                        "unit": "species",
                        "evidence_class": "derived",
                        "method_id": "method-card",
                        "input": "records",
                        "operation": "n_distinct",
                        "field": "name",
                        "filter": {"field": "kind", "eq": "tree"},
                    },
                    {
                        "metric_id": "threatened_sum",
                        "label": "Threatened sum",
                        "unit": "source-unit",
                        "evidence_class": "derived",
                        "method_id": "method-card",
                        "input": "records",
                        "operation": "sum",
                        "field": "value",
                        "scale": 2,
                        "empty_value": 0,
                        "filter": {
                            "all": [
                                {"field": "kind", "eq": "tree"},
                                {
                                    "any": [
                                        {"field": "status", "eq": "EN"},
                                        {"field": "status", "eq": "VU"},
                                    ]
                                },
                            ]
                        },
                    },
                ],
            }
            recipe_path = root / "recipe.json"
            recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
            output = root / "output.csv"
            manifest_path = root / "manifest.json"
            manifest = derive(root, recipe_path, output, manifest_path)
            with output.open(encoding="utf-8", newline="") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(rows[0]["trees"], "2")
            self.assertEqual(rows[0]["tree_species"], "2")
            self.assertEqual(rows[0]["threatened_sum"], "4")
            self.assertEqual(rows[1]["trees"], "1")
            self.assertEqual(rows[1]["threatened_sum"], "0")
            self.assertEqual(manifest["output"]["rows"], 2)
            self.assertEqual(manifest["output"]["metrics"][0]["method_id"], "method-card")
            self.assertIn("observations.csv", manifest["input_sha256"])

    def test_recipe_cannot_escape_site_pack(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = pathlib.Path(temporary)
            outside = root.parent / "outside-grouped-indicator-test.csv"
            outside.write_text("id\nx\n", encoding="utf-8")
            self.addCleanup(lambda: outside.unlink(missing_ok=True))
            recipe = {
                "recipe_id": "fixture",
                "version": "1",
                "dimensions": {
                    "path": "../outside-grouped-indicator-test.csv",
                    "key": "id",
                    "fields": [{"column": "id", "output": "id"}],
                },
                "inputs": {},
                "rollups": [],
            }
            recipe_path = root / "recipe.json"
            recipe_path.write_text(json.dumps(recipe), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "escapes site pack"):
                derive(root, recipe_path, root / "out.csv", root / "manifest.json")


if __name__ == "__main__":
    unittest.main()
