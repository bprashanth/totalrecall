"""An estimate must gate honestly, hold itself out, and never hide behind a number.

The checks here are deliberately about conduct rather than accuracy: that an approach the pack
cannot support is reported as unsupported with its gate named, that the interval a run publishes
actually covers held-out truth at roughly its declared level, and that a failed gate still returns
the observed evidence instead of an empty result.
"""

import pathlib
import tempfile
import unittest

from dss.visual_index.build import Builder
from dss.visual_index.estimate_service import (
    INTERVAL_LEVEL, MIN_TRAINING_CELLS, EstimateService,
)
from dss.visual_index.result_service import ResultService


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"
# A cell inside the AOI that the synthetic pack indexes, and one that carries effort rows.
SURVEYED_CELL = "at:10.30:76.94"
EFFORT_CELL = "g0.010:10.2600:76.9600"


class EstimateServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        cls.index_root = root / "index"
        cls.state_root = root / "state"
        Builder(PACK, cls.index_root).run()
        cls.result_service = ResultService(
            PACK, cls.index_root / "site_index.sqlite", cls.state_root
        )
        cls.service = EstimateService.from_result_service(cls.result_service)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    # ------------------------------------------------------------------ addressing

    def test_coordinate_resolves_to_the_builders_own_grid_cell(self):
        """`at:` must land on the same cell id the index builder would have written."""
        cell = self.service.resolve_cell(SURVEYED_CELL)
        self.assertEqual(cell["cell_id"], "g0.010:10.3000:76.9400")
        self.assertTrue(cell["inside_aoi"])
        self.assertAlmostEqual(cell["center_lat"], 10.305, places=6)
        self.assertAlmostEqual(cell["center_lon"], 76.945, places=6)
        # A cell id and the coordinate inside it must resolve identically.
        self.assertEqual(
            self.service.resolve_cell("g0.010:10.3000:76.9400")["cell_id"], cell["cell_id"]
        )
        self.assertEqual(
            self.service.resolve_cell({"lat": 10.30, "lon": 76.94})["cell_id"], cell["cell_id"]
        )

    def test_unparseable_cell_is_refused_not_guessed(self):
        for bad in ("somewhere near the estate", "at:999:999", ""):
            with self.assertRaises(ValueError):
                self.service.resolve_cell(bad)

    # ------------------------------------------------------------------ the menu

    def test_menu_reports_every_approach_with_its_gates(self):
        menu = self.service.suggest_approaches("likely record density", SURVEYED_CELL)
        self.assertEqual(menu["schema_version"], "idli-estimate-menu/1")
        self.assertGreaterEqual(len(menu["approaches"]), 2)
        self.assertLessEqual(len(menu["approaches"]), 4)
        self.assertEqual(menu["target"]["target_id"], "record_density")
        self.assertTrue(menu["target"]["matched_user_words"])
        for approach in menu["approaches"]:
            self.assertTrue(approach["gates"], approach["approach_id"])
            self.assertTrue(approach["required_planes"])
            for gate in approach["gates"]:
                # A gate must always say what it actually saw, not merely pass or fail.
                self.assertTrue(gate["observed"])
                self.assertTrue(gate["requirement"])
            self.assertEqual(
                approach["supported"], not approach["failed_gates"], approach["approach_id"]
            )
            if approach["supported"]:
                self.assertIn(approach["expected_confidence"], {"low", "high"})
                self.assertIsNotNone(approach["measured_skill"])
            else:
                self.assertEqual(approach["expected_confidence"], "unavailable")
                self.assertTrue(approach["blocked_reason"])

    def test_effort_transfer_is_unsupported_where_the_pack_has_no_effort(self):
        """The synthetic pack indexes effort in three cells only; the gate must say so."""
        menu = self.service.suggest_approaches("record density", SURVEYED_CELL)
        transfer = next(
            item for item in menu["approaches"]
            if item["approach_id"] == "per-source-rate-transfer"
        )
        self.assertFalse(transfer["supported"])
        self.assertIn("effort-rows-in-target-cell", transfer["failed_gates"])
        self.assertIn("effort", transfer["blocked_reason"])
        # And it must become supported for a cell that does carry effort.
        with_effort = self.service.suggest_approaches("record density", EFFORT_CELL)
        transfer = next(
            item for item in with_effort["approaches"]
            if item["approach_id"] == "per-source-rate-transfer"
        )
        self.assertTrue(transfer["supported"], transfer["blocked_reason"])

    def test_menu_recommends_the_approach_with_the_best_measured_skill(self):
        menu = self.service.suggest_approaches("record density", SURVEYED_CELL)
        scored = {
            item["approach_id"]: item["measured_skill"]["leave_one_out_r2"]
            for item in menu["approaches"] if item["supported"]
        }
        self.assertTrue(scored)
        self.assertEqual(
            menu["recommended_approach_id"], max(scored, key=lambda key: scored[key])
        )

    def test_menu_gates_the_aoi_and_the_training_minimum(self):
        outside = self.service.suggest_approaches("record density", "at:0.5:0.5")
        for approach in outside["approaches"]:
            self.assertFalse(approach["supported"])
            self.assertIn("target-cell-inside-aoi", approach["failed_gates"])
        # The pack must genuinely clear the training minimum, or the rest of this file is vacuous.
        inside = self.service.suggest_approaches("record density", SURVEYED_CELL)
        self.assertGreaterEqual(
            inside["pack_evidence"]["training_cells_available"], MIN_TRAINING_CELLS
        )

    # ------------------------------------------------------------------ the run

    def test_run_emits_a_modelled_layer_with_a_declared_interval(self):
        envelope = self.service.run_estimate(
            "spatial-neighbour-regression", "record density", SURVEYED_CELL,
            request_id="test-run", question="Estimate likely record density here.",
        )
        self.assertEqual(envelope["schema_version"], "idli-result/1")
        self.assertEqual(envelope["status"], "complete")
        self.assertEqual(envelope["audit"]["assurance"], "generated")
        self.assertIn("modelled", envelope["answer"]["evidence_classes"])

        layers = {item["layer_id"]: item for item in envelope["visuals"][0]["layers"]}
        self.assertEqual(layers["estimate-training-cells"]["evidence_class"], "derived")
        estimated = layers["estimated-cell"]
        self.assertEqual(estimated["evidence_class"], "modelled")
        self.assertEqual(estimated["geometry_type"], "cell")
        uncertainty = estimated["uncertainty"]
        self.assertEqual(uncertainty["kind"], "interval")
        self.assertEqual(uncertainty["level"], INTERVAL_LEVEL)
        self.assertLessEqual(uncertainty["low"], uncertainty["high"])
        self.assertIn("agreement", uncertainty)

        estimate = envelope["audit"]["estimate"]
        self.assertEqual(estimate["cell_id"], "g0.010:10.3000:76.9400")
        self.assertIn(estimate["confidence"], {"low", "high"})
        self.assertGreaterEqual(estimate["training_cells"], MIN_TRAINING_CELLS)
        self.assertEqual(len(estimate["coefficients"]), len(EstimateService.FEATURE_NAMES))

    def test_run_states_the_basis_of_its_own_confidence(self):
        envelope = self.service.run_estimate(
            "spatial-neighbour-regression", "record density", SURVEYED_CELL,
            request_id="test-confidence",
        )
        codes = {item["code"] for item in envelope["limitations"]}
        self.assertIn("estimate-confidence-basis", codes)
        self.assertIn("modelled-not-observed", codes)
        self.assertIn("estimate-inputs-declared", codes)
        basis = next(
            item for item in envelope["limitations"]
            if item["code"] == "estimate-confidence-basis"
        )["message"]
        # The confidence claim must carry its own arithmetic: how many cells, how wide the spread.
        self.assertIn("training cells", basis)
        self.assertIn("residual spread", basis)
        self.assertRegex(basis, r"LOW|HIGH")

    def test_run_names_exactly_which_sources_and_planes_fed_it(self):
        envelope = self.service.run_estimate(
            "spatial-neighbour-regression", "record density", SURVEYED_CELL,
            request_id="test-sources",
        )
        versions = envelope["audit"]["source_versions"]
        self.assertTrue(versions)
        for item in versions:
            self.assertTrue(item["digest"].startswith("sha256:"))
            self.assertTrue(item["planes_used"])
            self.assertTrue(item["title"])
        self.assertEqual(envelope["audit"]["estimate"]["planes_used"], ["events", "cells"])

    def test_run_suggests_what_data_would_shrink_the_interval(self):
        envelope = self.service.run_estimate(
            "spatial-neighbour-regression", "record density", SURVEYED_CELL,
            request_id="test-requests",
        )
        requests = [item for item in envelope["actions"] if item["kind"] == "data_request"]
        self.assertGreaterEqual(len(requests), 2)
        for item in requests:
            self.assertTrue(item["label"])
            self.assertTrue(item["expected_effect"])
        self.assertTrue(
            any("effort" in item["label"].casefold() for item in requests),
            "the pack's thinnest plane is effort; that should be asked for",
        )

    def test_unknown_approach_is_refused(self):
        with self.assertRaises(ValueError):
            self.service.run_estimate("magic-oracle", "record density", SURVEYED_CELL)

    # ------------------------------------------------------------------ leave-one-out truth

    def _surveyed_cells(self):
        with self.service.connect() as connection:
            table = self.service.cell_table(connection)
        return self.service._observed(table, "record_density")

    def test_held_out_cell_interval_contains_its_true_value(self):
        """The estimate for a surveyed cell is a leave-one-out prediction: it must cover truth."""
        observed = self._surveyed_cells()
        cell_id = "g0.010:10.3000:76.9400"
        envelope = self.service.run_estimate(
            "spatial-neighbour-regression", "record density", cell_id,
            request_id="loo-single",
        )
        estimate = envelope["audit"]["estimate"]
        truth = observed[cell_id]
        self.assertLessEqual(estimate["interval"]["low"], truth)
        self.assertGreaterEqual(estimate["interval"]["high"], truth)
        # The cell's own value must never have entered its own training set.
        self.assertEqual(estimate["training_cells"], len(observed) - 1)

    def test_interval_covers_held_out_truth_at_roughly_its_declared_level(self):
        """Run every surveyed cell as a held-out cell and count how often the interval is right."""
        observed = self._surveyed_cells()
        for approach_id, floor in (
            ("spatial-neighbour-regression", 0.6),
            ("analogue-nearest-cells", 0.7),
            ("aoi-baseline-mean", 0.7),
        ):
            covered = attempted = 0
            for cell_id, truth in observed.items():
                envelope = self.service.run_estimate(
                    approach_id, "record density", cell_id,
                    request_id=f"loo-{approach_id}-{cell_id}",
                )
                if envelope["status"] != "complete":
                    continue
                interval = envelope["audit"]["estimate"]["interval"]
                attempted += 1
                if interval["low"] <= truth <= interval["high"]:
                    covered += 1
            self.assertGreaterEqual(attempted, MIN_TRAINING_CELLS)
            coverage = covered / attempted
            self.assertGreaterEqual(
                coverage, floor,
                f"{approach_id} covered only {coverage:.0%} of held-out cells at a declared "
                f"{INTERVAL_LEVEL:.0%} level",
            )

    # ------------------------------------------------------------------ blocked path

    def test_gate_failure_keeps_the_observed_map_and_names_the_gate(self):
        envelope = self.service.run_estimate(
            "spatial-neighbour-regression", "record density", "at:0.5:0.5",
            request_id="blocked-outside-aoi",
        )
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual(envelope["audit"]["capability_runs"][0]["status"], "blocked")
        self.assertIsNone(envelope["audit"]["estimate"]["estimate"])
        self.assertIn("target-cell-inside-aoi", envelope["audit"]["estimate"]["failed_gates"])

        gate_limitation = next(
            item for item in envelope["limitations"] if item["code"] == "estimate-gate-failed"
        )
        self.assertEqual(gate_limitation["severity"], "error")
        self.assertIn("target-cell-inside-aoi", gate_limitation["message"])

        # The observed evidence is retained: a model that cannot run must not blank the map.
        layers = {item["layer_id"]: item for item in envelope["visuals"][0]["layers"]}
        self.assertIn("estimate-training-cells", layers)
        self.assertEqual(layers["estimate-blocked-cell"]["evidence_class"], "missing")
        payload = self.state_root / "results" / envelope["result_id"] / "data"
        self.assertTrue((payload / "estimate-training-cells.geojson").is_file())
        self.assertNotIn(
            "estimated-cell", {item["layer_id"] for item in envelope["visuals"][0]["layers"]}
        )

    def test_effort_transfer_blocks_where_the_target_cell_has_no_effort(self):
        envelope = self.service.run_estimate(
            "per-source-rate-transfer", "record density", SURVEYED_CELL,
            request_id="blocked-no-effort",
        )
        self.assertEqual(envelope["status"], "blocked")
        self.assertIn(
            "effort-rows-in-target-cell", envelope["audit"]["estimate"]["failed_gates"]
        )


if __name__ == "__main__":
    unittest.main()
