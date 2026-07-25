#!/usr/bin/env python3
"""Estimate a cell-level quantity for one map cell, from the pinned index and nothing else.

A user points at a cell and asks "what would the value be here?". That question has no observed
answer: either the cell was never surveyed, or the user wants a held-out check of a cell that was.
This service answers it the only honest way available offline — by fitting a small, fully
deterministic model to the cells the pack *does* have, and declaring exactly how weak that is.

Three entry points, deliberately separated:

- `target_catalogue()` (in `target_catalogue.py`) lists every quantity this index can be asked
  for — per event type with the raw column it counts, per measured metric, per effort method,
  plus the whole-cell quantities. It matches no words: the caller reads the list, interprets the
  user's own phrasing against it in the open, and passes back one `target_id`.
- `suggest_approaches(target_id, cell)` inspects the pinned index (per-cell event counts by source,
  effort rows, measurements, entity richness, neighbouring values) and returns 2-4 concrete
  approach descriptors. Each descriptor carries its required planes, its gate precheck against
  *this* pack, and the confidence class it can plausibly reach. An approach the pack cannot
  support is returned as unsupported with the failing gate named, never silently dropped.
- `run_estimate(approach_id, target, cell)` runs one of them and emits an ordinary `idli-result/1`
  envelope whose estimated cell is `modelled` evidence with a residual-based interval.

Three rules hold everywhere in this module:

1. The target cell is never in its own training set, and a cell's features never include its own
   value. Every prediction is therefore a leave-one-out prediction, including for a surveyed cell,
   which is what makes the interval checkable.
2. The interval comes from the model's own leave-one-out residual quantiles, not from a formula
   that assumes normality, and its basis (training n, residual spread) is stated as a limitation.
3. A failed gate produces a `blocked` envelope that still shows the observed data. A model that
   cannot run is not a reason to hide the evidence that exists.

Stdlib only: the least-squares fit is normal equations solved by Gaussian elimination with
partial pivoting on a matrix of at most seven columns.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import re
import sqlite3
from typing import Any

try:
    from dss.visual_index.explain_service import COORDINATE_MARK
    from dss.visual_index.result_service import (
        SAFE_HANDLE, _atomic_write_once, _digest, _load_json, _percentile, _stable_json,
    )
    from dss.visual_index.target_catalogue import (
        TARGET_CATALOGUE_CAPABILITIES, build_target_catalogue, catalogue_index,
    )
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/estimate_service.py
    from explain_service import COORDINATE_MARK  # type: ignore[no-redef]
    from result_service import (  # type: ignore[no-redef]
        SAFE_HANDLE, _atomic_write_once, _digest, _load_json, _percentile, _stable_json,
    )
    from target_catalogue import (  # type: ignore[no-redef]
        TARGET_CATALOGUE_CAPABILITIES, build_target_catalogue, catalogue_index,
    )


MENU_VERSION = "idli-estimate-menu/1"
GRID_RESOLUTION = 0.01
CELL_ID = re.compile(r"^g(\d+\.\d+):(-?\d+\.\d+):(-?\d+\.\d+)$")
MIN_TRAINING_CELLS = 8
INTERVAL_LEVEL = 0.8
NEAREST_K = 3
RIDGE = 1e-8
# A cell with no observed cell within two grid steps has no neighbourhood to learn from; the
# regression would return its intercept and dress a global mean up as a local estimate.
NEIGHBOUR_SUPPORT_RADIUS = 2


# The default when a caller names no target at all. Every other target this service will run is
# enumerated from the index itself by `target_catalogue`; there is deliberately no list of
# synonyms here, because a synonym list is a semantic judgement and this service makes none.
DEFAULT_TARGET_ID = "record_density"

ESTIMATE_CAPABILITIES: list[dict[str, Any]] = [
    *TARGET_CATALOGUE_CAPABILITIES,
    {
        "capability_id": "cell-estimate-suggest",
        "version": "1.0.0",
        "label": "List the estimation approaches this pack's data can actually support",
        "input_schema": {
            "type": "object",
            "properties": {
                "target": {"type": "string"},
                "cell": {"type": "string"},
                "purpose": {"type": "string"},
            },
            "required": ["cell"],
        },
        "output_views": ["estimate-approach-menu"],
        "required_planes": ["cells"],
        "optional_planes": ["events", "effort", "measurements", "entities"],
        "latency_class": "interactive",
        "evidence_classes": ["derived"],
        "availability": "ready",
        "scope": "site",
        "reason": "Precheck only: it returns a menu, never an estimate and never a result envelope.",
    },
    {
        "capability_id": "cell-estimate-run",
        "version": "1.0.0",
        "label": "Estimate one cell-level quantity for one map cell, with an uncertainty interval",
        "input_schema": {
            "type": "object",
            "properties": {
                "approach_id": {"type": "string"},
                "target": {"type": "string"},
                "cell": {"type": "string"},
                "purpose": {"type": "string"},
            },
            "required": ["approach_id", "cell"],
        },
        "output_views": ["estimate-cell-surface", "estimate-summary"],
        "required_planes": ["cells", "events"],
        "optional_planes": ["effort", "measurements", "entities"],
        "latency_class": "interactive",
        "evidence_classes": ["derived", "modelled", "missing"],
        "availability": "ready",
        "scope": "site",
        "reason": "Modelled output: every estimate is generated, never observed.",
    },
]


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _solve(matrix: list[list[float]], vector: list[float]) -> list[float] | None:
    """Gaussian elimination with partial pivoting on a small symmetric system."""
    size = len(vector)
    rows = [list(matrix[index]) + [vector[index]] for index in range(size)]
    for column in range(size):
        pivot = max(range(column, size), key=lambda index: abs(rows[index][column]))
        if abs(rows[pivot][column]) < 1e-12:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        for index in range(column + 1, size):
            factor = rows[index][column] / rows[column][column]
            if factor:
                for position in range(column, size + 1):
                    rows[index][position] -= factor * rows[column][position]
    solution = [0.0] * size
    for column in range(size - 1, -1, -1):
        total = rows[column][size] - sum(
            rows[column][index] * solution[index] for index in range(column + 1, size)
        )
        solution[column] = total / rows[column][column]
    return solution


def _least_squares(design: list[list[float]], target: list[float]) -> list[float] | None:
    """Ordinary least squares by normal equations, with a token ridge for conditioning only."""
    if not design or len(design) != len(target):
        return None
    width = len(design[0])
    normal = [[0.0] * width for _ in range(width)]
    right = [0.0] * width
    for row, observed in zip(design, target):
        for i in range(width):
            right[i] += row[i] * observed
            for j in range(width):
                normal[i][j] += row[i] * row[j]
    trace = sum(normal[i][i] for i in range(width)) or 1.0
    for i in range(width):
        normal[i][i] += RIDGE * trace
    return _solve(normal, right)


class EstimateService:
    """Fit small deterministic models over one pinned site index and declare their weakness."""

    def __init__(
        self,
        site_pack: pathlib.Path,
        index_path: pathlib.Path,
        state_root: pathlib.Path,
    ):
        self.site_pack = pathlib.Path(site_pack).resolve()
        self.index_path = pathlib.Path(index_path).resolve()
        self.state_root = pathlib.Path(state_root).resolve()
        if not self.index_path.is_file():
            raise FileNotFoundError(self.index_path)
        self.site = _load_json(self.site_pack / "site.json")
        registry = _load_json(self.site_pack / "sources.json")
        self.synthetic = any(
            "synthetic" in (source.get("capabilities") or [])
            for source in registry.get("sources", [])
        )
        self.pack_digest = ""

    @classmethod
    def from_result_service(cls, service: Any) -> "EstimateService":
        estimator = cls(service.site_pack, service.index_path, service.state_root)
        estimator.site = service.site
        estimator.pack_digest = service.pack_digest
        estimator.synthetic = bool(getattr(service, "synthetic", False))
        return estimator

    # ------------------------------------------------------------------ storage

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    # ------------------------------------------------------------------ geography

    def aoi_geometry(self) -> dict[str, Any]:
        return self.site["target_aoi"]["geometry"]

    def aoi_bbox(self) -> tuple[float, float, float, float]:
        ring = self.aoi_geometry()["coordinates"][0]
        xs = [float(point[0]) for point in ring]
        ys = [float(point[1]) for point in ring]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def cell_id_for(lat: float, lon: float, resolution: float = GRID_RESOLUTION) -> str:
        """The builder's own grid convention (dss/visual_index/build.py::_cell)."""
        south = math.floor(lat / resolution) * resolution
        west = math.floor(lon / resolution) * resolution
        return f"g{resolution:.3f}:{south:.4f}:{west:.4f}"

    @staticmethod
    def cell_box(cell_id: str) -> tuple[float, float, float, float] | None:
        match = CELL_ID.match(str(cell_id or "").strip())
        if not match:
            return None
        resolution = float(match.group(1))
        south, west = float(match.group(2)), float(match.group(3))
        return west, south, west + resolution, south + resolution

    def resolve_cell(self, cell: Any) -> dict[str, Any]:
        """Resolve `at:<lat>:<lon>`, a cell id, or an explicit lat/lon pair to one grid cell.

        The coordinate conventions are the ones `explain_service` already applies to a map click,
        so a cell the user clicked to explain and the cell they then ask to estimate are the same
        cell.
        """
        if isinstance(cell, (int, float)):
            cell = str(cell)
        lat = lon = None
        cell_id = ""
        if isinstance(cell, dict):
            for key in ("cell_id", "cell", "mark", "id", "at"):
                if cell.get(key):
                    return self.resolve_cell(cell[key])
            lat_value = cell.get("lat", cell.get("latitude"))
            lon_value = cell.get("lon", cell.get("lng", cell.get("longitude")))
            if lat_value in (None, "") or lon_value in (None, ""):
                raise ValueError("cell must be 'at:<lat>:<lon>', a cell id, or lat/lon")
            lat, lon = float(lat_value), float(lon_value)
        elif isinstance(cell, str):
            text = cell.strip()
            match = COORDINATE_MARK.match(text)
            if match:
                lat, lon = float(match.group(1)), float(match.group(2))
            elif CELL_ID.match(text):
                cell_id = text
            else:
                raise ValueError(
                    f"unrecognised cell reference: {text!r}; use 'at:<lat>:<lon>' or a cell id"
                )
        else:
            raise ValueError("cell is required")
        if cell_id:
            box = self.cell_box(cell_id)
            if box is None:
                raise ValueError(f"unrecognised cell id: {cell_id}")
            west, south, east, north = box
        else:
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise ValueError(f"coordinate out of range: {lat}, {lon}")
            cell_id = self.cell_id_for(lat, lon)
            west, south, east, north = self.cell_box(cell_id)  # type: ignore[misc]
        center_lat, center_lon = (south + north) / 2, (west + east) / 2
        aoi_west, aoi_south, aoi_east, aoi_north = self.aoi_bbox()
        return {
            "cell_id": cell_id,
            "west": west, "south": south, "east": east, "north": north,
            "center_lat": center_lat, "center_lon": center_lon,
            "requested_lat": lat, "requested_lon": lon,
            "inside_aoi": (
                aoi_west <= center_lon <= aoi_east and aoi_south <= center_lat <= aoi_north
            ),
            "aoi_bbox": [aoi_west, aoi_south, aoi_east, aoi_north],
        }

    @staticmethod
    def _grid_distance(left: str, right: str) -> float | None:
        """Chebyshev distance in whole grid steps between two cell ids."""
        first, second = EstimateService.cell_box(left), EstimateService.cell_box(right)
        if first is None or second is None:
            return None
        step = max(first[2] - first[0], 1e-9)
        return max(
            abs(second[0] - first[0]) / step, abs(second[1] - first[1]) / step
        )

    # ------------------------------------------------------------------ pack inspection

    def cell_table(self, connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
        """Everything the pinned index knows per cell, for features, gates and the menu."""
        table: dict[str, dict[str, Any]] = {}
        for row in connection.execute(
            "SELECT cell_id,west,south,east,north,center_lat,center_lon,target_role FROM cells"
        ):
            table[row["cell_id"]] = {
                "cell_id": row["cell_id"],
                "west": row["west"], "south": row["south"],
                "east": row["east"], "north": row["north"],
                "center_lat": row["center_lat"], "center_lon": row["center_lon"],
                "target_role": row["target_role"],
                "records": 0, "entities": 0, "sources": 0, "per_source": {},
                "effort_rows": 0, "effort_value": 0.0, "measurements": 0,
                "event_total": {}, "event_records": {}, "metric_mean": {},
            }
        for row in connection.execute(
            """SELECT cell_id,COUNT(*) AS records,COUNT(DISTINCT entity_id) AS entities,
                      COUNT(DISTINCT source_id) AS sources
               FROM events WHERE cell_id IS NOT NULL GROUP BY cell_id"""
        ):
            if row["cell_id"] in table:
                table[row["cell_id"]].update({
                    "records": int(row["records"]),
                    "entities": int(row["entities"]),
                    "sources": int(row["sources"]),
                })
        for row in connection.execute(
            """SELECT cell_id,source_id,COUNT(*) AS records FROM events
               WHERE cell_id IS NOT NULL GROUP BY cell_id,source_id"""
        ):
            if row["cell_id"] in table:
                table[row["cell_id"]]["per_source"][row["source_id"]] = int(row["records"])
        for row in connection.execute(
            """SELECT cell_id,COUNT(*) AS rows_count,
                      COALESCE(SUM(effort_value),0) AS effort_value
               FROM effort WHERE cell_id IS NOT NULL GROUP BY cell_id"""
        ):
            if row["cell_id"] in table:
                table[row["cell_id"]]["effort_rows"] = int(row["rows_count"])
                table[row["cell_id"]]["effort_value"] = float(row["effort_value"])
        for row in connection.execute(
            """SELECT cell_id,COUNT(*) AS rows_count FROM measurements
               WHERE cell_id IS NOT NULL GROUP BY cell_id"""
        ):
            if row["cell_id"] in table:
                table[row["cell_id"]]["measurements"] = int(row["rows_count"])
        # Per event type and per metric, so a target the catalogue enumerated — "the persondays
        # on public works", "the average daily wage" — has an observed per-cell value of its own
        # rather than being folded into an undifferentiated record count.
        for row in connection.execute(
            """SELECT cell_id,event_type,COUNT(*) AS records,
                      COUNT(count_value) AS valued,
                      COALESCE(SUM(count_value),0) AS total
               FROM events WHERE cell_id IS NOT NULL GROUP BY cell_id,event_type"""
        ):
            if row["cell_id"] in table:
                table[row["cell_id"]]["event_records"][row["event_type"]] = int(row["records"])
                if int(row["valued"]):
                    table[row["cell_id"]]["event_total"][row["event_type"]] = float(row["total"])
        for row in connection.execute(
            """SELECT cell_id,metric,AVG(value) AS mean_value FROM measurements
               WHERE cell_id IS NOT NULL AND value IS NOT NULL GROUP BY cell_id,metric"""
        ):
            if row["cell_id"] in table:
                table[row["cell_id"]]["metric_mean"][row["metric"]] = float(row["mean_value"])
        return table

    def target_catalogue(self) -> dict[str, Any]:
        """Everything this index can be asked to estimate, enumerated, never interpreted."""
        return build_target_catalogue(self, minimum_cells=MIN_TRAINING_CELLS)

    def resolve_target(
        self, target_text: str, catalogue: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Bind a caller-supplied target to one catalogued id. No words are interpreted here.

        The caller must pass a `target_id` this pack's catalogue prints. Free text is refused
        rather than guessed at: a service that quietly decided "jobs" meant record density would
        be making an interpretation the user never saw and could not correct. Interpretation is
        the model's job, said out loud; binding is this method's job, and it binds exactly.
        """
        catalogue = catalogue or self.target_catalogue()
        entries = catalogue_index(catalogue)
        requested = _clean(target_text)
        target_id = requested
        if not target_id:
            target_id = catalogue.get("default_target_id") or DEFAULT_TARGET_ID
        elif target_id not in entries:
            folded = {key.casefold(): key for key in entries}
            target_id = folded.get(target_id.casefold(), "")
        entry = entries.get(target_id)
        if entry is None:
            raise ValueError(
                f"unknown estimate target: {requested!r}. This pack estimates "
                + ", ".join(entries) + ". Fetch the target catalogue and pass one of those ids."
            )
        return {
            "target_id": entry["target_id"],
            "label": entry["label"],
            "unit": entry["unit"],
            "planes": list(entry["planes"]),
            "counts": entry.get("counts") or {},
            "family": entry.get("family"),
            "sources": entry.get("sources") or [],
            "record_labels": entry.get("record_labels") or [],
            "coverage": entry.get("coverage") or {},
            "requested": requested,
            # True whenever the caller named the target; the only unnamed case is the default.
            "matched": bool(requested),
        }

    @staticmethod
    def _observed(
        table: dict[str, dict[str, Any]], target_id: str
    ) -> dict[str, float]:
        family, _, key = str(target_id or "").partition(":")
        observed: dict[str, float] = {}
        for cell_id, row in table.items():
            if family == "event_total":
                if key in row["event_total"]:
                    observed[cell_id] = float(row["event_total"][key])
            elif family == "event_records":
                if key in row["event_records"]:
                    observed[cell_id] = float(row["event_records"][key])
            elif family == "metric_mean":
                if key in row["metric_mean"]:
                    observed[cell_id] = float(row["metric_mean"][key])
            elif target_id == "record_density":
                if row["records"]:
                    observed[cell_id] = float(row["records"])
            elif target_id == "entity_richness":
                if row["records"]:
                    observed[cell_id] = float(row["entities"])
            elif target_id == "survey_effort":
                if row["effort_rows"]:
                    observed[cell_id] = float(row["effort_value"])
            elif target_id == "effort_normalised_rate":
                if row["effort_value"] > 0:
                    observed[cell_id] = 100.0 * row["records"] / row["effort_value"]
        return observed

    # ------------------------------------------------------------------ features

    def _features(
        self, cell_id: str, observed: dict[str, float], table: dict[str, dict[str, Any]],
        exclude: set[str],
    ) -> list[float]:
        """Neighbourhood features for one cell, never using that cell's own observed value."""
        ring1: list[float] = []
        ring2: list[float] = []
        weighted_total = weight_total = 0.0
        breadth: list[float] = []
        for other, value in observed.items():
            if other == cell_id or other in exclude:
                continue
            distance = self._grid_distance(cell_id, other)
            if distance is None or distance <= 0:
                continue
            if distance <= 1:
                ring1.append(value)
            if distance <= NEIGHBOUR_SUPPORT_RADIUS:
                ring2.append(value)
                breadth.append(float(table.get(other, {}).get("sources", 0)))
            weight = 1.0 / (distance * distance)
            weighted_total += weight * value
            weight_total += weight
        return [
            1.0,
            _mean(ring1),
            _mean(ring2),
            float(len(ring1)),
            weighted_total / weight_total if weight_total else 0.0,
            _mean(breadth),
        ]

    FEATURE_NAMES = (
        "intercept", "adjacent_cell_mean", "two_step_cell_mean", "adjacent_cell_count",
        "inverse_distance_weighted_mean", "adjacent_source_breadth",
    )

    def _neighbour_support(self, cell_id: str, observed: dict[str, float]) -> int:
        count = 0
        for other in observed:
            if other == cell_id:
                continue
            distance = self._grid_distance(cell_id, other)
            if distance is not None and 0 < distance <= NEIGHBOUR_SUPPORT_RADIUS:
                count += 1
        return count

    # ------------------------------------------------------------------ predictors

    def _predict(
        self, approach_id: str, cell_id: str, observed: dict[str, float],
        table: dict[str, dict[str, Any]], exclude: set[str],
    ) -> tuple[float | None, list[float] | None]:
        """One deterministic prediction for one cell, from cells outside `exclude` only."""
        pool = {key: value for key, value in observed.items()
                if key != cell_id and key not in exclude}
        if not pool:
            return None, None
        if approach_id == "aoi-baseline-mean":
            return _mean(list(pool.values())), None
        if approach_id == "analogue-nearest-cells":
            ranked = sorted(
                (
                    (self._grid_distance(cell_id, other) or 1e9, other)
                    for other in pool
                ),
                key=lambda item: (item[0], item[1]),
            )[:NEAREST_K]
            if not ranked:
                return None, None
            return _mean([pool[other] for _, other in ranked]), None
        if approach_id == "per-source-rate-transfer":
            rates = [
                100.0 * table[other]["records"] / table[other]["effort_value"]
                for other in pool
                if table.get(other, {}).get("effort_value", 0) > 0
                and table[other]["records"] is not None
            ]
            effort = float(table.get(cell_id, {}).get("effort_value", 0.0))
            if not rates or effort <= 0:
                return None, None
            rates.sort()
            return _percentile(rates, 0.5) * effort / 100.0, None
        if approach_id == "spatial-neighbour-regression":
            design = [
                self._features(other, observed, table, exclude | {other})
                for other in sorted(pool)
            ]
            response = [pool[other] for other in sorted(pool)]
            coefficients = _least_squares(design, response)
            if coefficients is None:
                return None, None
            row = self._features(cell_id, observed, table, exclude)
            return sum(a * b for a, b in zip(coefficients, row)), coefficients
        return None, None

    # ------------------------------------------------------------------ held-out skill

    def _holdout(
        self, approach_id: str, training_ids: list[str], observed: dict[str, float],
        table: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """Leave-one-out performance of one approach over the training cells.

        This is the only honest basis for claiming an approach is better than another on *this*
        pack. It is computed the same way for the menu and for the run, so the confidence a user
        is offered before choosing is the confidence they get after running.
        """
        residuals: list[float] = []
        held_out: list[dict[str, Any]] = []
        for held in training_ids:
            predicted, _ = self._predict(approach_id, held, observed, table, {held})
            if predicted is None:
                continue
            residuals.append(observed[held] - predicted)
            held_out.append({
                "cell_id": held, "observed": round(observed[held], 4),
                "predicted": round(predicted, 4),
                "residual": round(observed[held] - predicted, 4),
            })
        values = [observed[key] for key in training_ids]
        mean_observed = _mean(values)
        ss_total = sum((value - mean_observed) ** 2 for value in values)
        ss_residual = sum(value * value for value in residuals)
        tail = (1.0 - INTERVAL_LEVEL) / 2.0
        low_offset = _percentile(residuals, tail) if residuals else 0.0
        high_offset = _percentile(residuals, 1.0 - tail) if residuals else 0.0
        covered = sum(
            1 for item in held_out
            if item["predicted"] + low_offset <= item["observed"] <= item["predicted"] + high_offset
        )
        return {
            "residuals": residuals,
            "held_out": held_out,
            "r2": 1.0 - ss_residual / ss_total if ss_total > 0 else 0.0,
            "low_offset": low_offset,
            "high_offset": high_offset,
            "spread": high_offset - low_offset,
            "coverage": covered / len(held_out) if held_out else 0.0,
        }

    @staticmethod
    def _confidence_class(training_count: int, r2: float, signal_to_noise: float) -> str:
        return (
            "high" if training_count >= 12 and r2 >= 0.3 and signal_to_noise >= 2.0 else "low"
        )

    # ------------------------------------------------------------------ approach menu

    APPROACHES: list[dict[str, Any]] = [
        {
            "approach_id": "spatial-neighbour-regression",
            "label": "Spatial-neighbour least-squares regression",
            "description": (
                "Fit a least-squares model on every surveyed cell, predicting that cell's value "
                "from its neighbours' values (adjacent mean, two-step mean, how many adjacent "
                "cells carry data, an inverse-distance-weighted mean, and how many distinct "
                "sources the neighbourhood draws on), then apply the fitted model to the cell you "
                "asked about. No cell ever sees its own value, so the fit is honest."
            ),
            "required_planes": ["cells", "events"],
            "best_confidence": "high",
        },
        {
            "approach_id": "analogue-nearest-cells",
            "label": "Nearest surveyed cells (analogue average)",
            "description": (
                f"Average the {NEAREST_K} nearest surveyed cells. It assumes the neighbourhood is "
                "a fair analogue and fits nothing, so it is robust but cannot represent a gradient."
            ),
            "required_planes": ["cells", "events"],
            "best_confidence": "low",
        },
        {
            "approach_id": "per-source-rate-transfer",
            "label": "Effort-normalised rate transfer",
            "description": (
                "Take the median records-per-100-effort-units rate across cells that carry "
                "documented survey effort, and apply it to this cell's own documented effort. "
                "It needs effort rows in the cell you asked about, and it estimates what the "
                "recorded count would be at the typical recording rate — not what is really there."
            ),
            "required_planes": ["cells", "events", "effort"],
            "best_confidence": "high",
        },
        {
            "approach_id": "aoi-baseline-mean",
            "label": "AOI baseline mean",
            "description": (
                "The mean of every surveyed cell in the area, with no spatial structure at all. "
                "It is the floor: use it only to show what ignoring location costs."
            ),
            "required_planes": ["cells", "events"],
            "best_confidence": "low",
        },
    ]

    def _gates(
        self, approach_id: str, cell: dict[str, Any], observed: dict[str, float],
        table: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Precheck one approach against this pack. Every gate reports what it actually saw."""
        target_cell = cell["cell_id"]
        training = {key: value for key, value in observed.items() if key != target_cell}
        support = self._neighbour_support(target_cell, observed)
        gates = [{
            "gate": "target-cell-inside-aoi",
            "requirement": "the cell must lie inside the pack's declared AOI",
            "observed": (
                f"cell centre {cell['center_lat']:.4f},{cell['center_lon']:.4f} is "
                + ("inside" if cell["inside_aoi"] else "outside")
                + " the declared AOI"
            ),
            "passed": bool(cell["inside_aoi"]),
        }, {
            "gate": "minimum-training-cells",
            "requirement": f"at least {MIN_TRAINING_CELLS} surveyed cells excluding the target",
            "observed": f"{len(training)} surveyed cells available for training",
            "passed": len(training) >= MIN_TRAINING_CELLS,
        }]
        if approach_id in {"spatial-neighbour-regression", "analogue-nearest-cells"}:
            gates.append({
                "gate": "neighbourhood-support",
                "requirement": (
                    f"at least one surveyed cell within {NEIGHBOUR_SUPPORT_RADIUS} grid steps"
                ),
                "observed": f"{support} surveyed cells within {NEIGHBOUR_SUPPORT_RADIUS} steps",
                "passed": support >= 1,
            })
        if approach_id == "spatial-neighbour-regression":
            variances: list[float] = []
            if len(training) >= 2:
                rows = [
                    self._features(other, observed, table, {target_cell, other})
                    for other in sorted(training)
                ]
                for column in range(1, len(self.FEATURE_NAMES)):
                    values = [row[column] for row in rows]
                    average = _mean(values)
                    variances.append(
                        sum((value - average) ** 2 for value in values) / len(values)
                    )
            varying = [
                name for name, variance in zip(self.FEATURE_NAMES[1:], variances)
                if variance > 0
            ]
            gates.append({
                "gate": "feature-variance",
                "requirement": "at least one neighbourhood feature must vary across training cells",
                "observed": (
                    f"{len(varying)} of {len(self.FEATURE_NAMES) - 1} features vary"
                    + (f" ({', '.join(varying)})" if varying else "")
                ),
                "passed": bool(varying),
            })
        if approach_id == "per-source-rate-transfer":
            with_effort = [
                key for key, row in table.items()
                if row["effort_value"] > 0 and key != target_cell
            ]
            gates.append({
                "gate": "effort-rows-in-donor-cells",
                "requirement": "at least 2 cells must carry documented effort",
                "observed": f"{len(with_effort)} cells carry documented effort",
                "passed": len(with_effort) >= 2,
            })
            gates.append({
                "gate": "effort-rows-in-target-cell",
                "requirement": "the target cell must itself carry documented effort to scale",
                "observed": (
                    f"{table.get(target_cell, {}).get('effort_rows', 0)} effort rows indexed "
                    f"in {target_cell}"
                ),
                "passed": float(table.get(target_cell, {}).get("effort_value", 0.0)) > 0,
            })
        return gates

    def suggest_approaches(self, target_text: str, cell: Any) -> dict[str, Any]:
        """Return the estimation approaches this pack's data can and cannot support, with gates."""
        resolved_cell = self.resolve_cell(cell)
        catalogue = self.target_catalogue()
        target = self.resolve_target(target_text, catalogue)
        with self.connect() as connection:
            table = self.cell_table(connection)
            source_rows = [dict(row) for row in connection.execute(
                "SELECT source_id,title,publisher,license FROM sources ORDER BY source_id"
            )]
        observed = self._observed(table, target["target_id"])
        target_cell = resolved_cell["cell_id"]
        training = {key: value for key, value in observed.items() if key != target_cell}
        training_ids = sorted(training)
        approaches = []
        for descriptor in self.APPROACHES:
            approach_id = descriptor["approach_id"]
            gates = self._gates(approach_id, resolved_cell, observed, table)
            failed = [item["gate"] for item in gates if not item["passed"]]
            supported = not failed
            skill: dict[str, Any] | None = None
            confidence = "unavailable"
            if supported:
                # Measure, do not assume. An approach's expected confidence is its own
                # leave-one-out skill on this pack, so the menu cannot promise what the run
                # will not deliver.
                measured = self._holdout(approach_id, training_ids, observed, table)
                prediction, _ = self._predict(approach_id, target_cell, observed, table, set())
                signal_to_noise = (
                    max(prediction or 0.0, 0.0) / (measured["spread"] / 2.0)
                    if measured["spread"] > 0 else float(len(measured["residuals"]))
                )
                confidence = self._confidence_class(
                    len(training_ids), measured["r2"], signal_to_noise)
                skill = {
                    "leave_one_out_r2": round(measured["r2"], 4),
                    "residual_spread": round(measured["spread"], 4),
                    "interval_coverage": round(measured["coverage"], 4),
                    "held_out_cells": len(measured["held_out"]),
                    "beats_aoi_mean": measured["r2"] > 0,
                }
            approaches.append({
                "approach_id": approach_id,
                "label": descriptor["label"],
                "description": descriptor["description"],
                "required_planes": descriptor["required_planes"],
                "supported": supported,
                "expected_confidence": confidence,
                "best_case_confidence": descriptor["best_confidence"],
                "measured_skill": skill,
                "gates": gates,
                "failed_gates": failed,
                "blocked_reason": (
                    None if supported else
                    "; ".join(
                        f"{item['gate']}: {item['observed']}"
                        for item in gates if not item["passed"]
                    )
                ),
            })
        ranking = {descriptor["approach_id"]: index
                   for index, descriptor in enumerate(self.APPROACHES)}
        scored = [item for item in approaches if item["supported"] and item["measured_skill"]]
        recommended = (
            max(
                scored,
                key=lambda item: (
                    item["measured_skill"]["leave_one_out_r2"], -ranking[item["approach_id"]]
                ),
            )["approach_id"] if scored else None
        )
        return {
            "schema_version": MENU_VERSION,
            "site": {
                "site_id": self.site.get("site_id"), "label": self.site.get("label"),
                "pack_digest": self.pack_digest,
                **({"synthetic": True} if self.synthetic else {}),
            },
            "cell": resolved_cell,
            "target": {
                "target_id": target["target_id"], "label": target["label"],
                "unit": target["unit"], "requested": target["requested"],
                "matched_user_words": target["matched"],
                "planes": target["planes"],
                "counts": target["counts"],
                "sources": target["sources"],
                "record_labels": target["record_labels"],
            },
            # The whole catalogue travels with the menu, so a caller that guessed the target can
            # see every other quantity this pack carries and correct itself in the same turn.
            "target_catalogue": catalogue,
            "pack_evidence": {
                "cells_indexed": len(table),
                "cells_with_observed_target": len(observed),
                "training_cells_available": len(training),
                "target_cell_is_surveyed": target_cell in observed,
                "target_cell_observed_value": observed.get(target_cell),
                "cells_with_effort": sum(1 for row in table.values() if row["effort_rows"]),
                "cells_with_measurements": sum(
                    1 for row in table.values() if row["measurements"]),
                "distinct_sources": len({
                    source for row in table.values() for source in row["per_source"]
                }),
                "neighbour_support": self._neighbour_support(target_cell, observed),
            },
            "approaches": approaches,
            "recommended_approach_id": recommended,
            "sources": source_rows,
            "method": (
                "Deterministic precheck. Each approach was gated against this pinned index only; "
                "nothing was estimated and no model was called."
            ),
        }

    # ------------------------------------------------------------------ envelope helpers

    @staticmethod
    def _limitation(
        code: str, message: str, *, severity: str = "warning",
        affects: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "code": code, "severity": severity, "message": message,
            "affects": affects or ["answer"], "details_ref": None,
        }

    @staticmethod
    def _data_ref(handle: str, media_type: str, payload: Any) -> dict[str, Any]:
        return {
            "kind": "result_data", "handle": handle, "media_type": media_type,
            "digest": _digest(payload),
        }

    def _base(
        self, result_id: str, request_id: str, capability_id: str, original: str,
        resolved: str, bindings: dict[str, Any], headline: str,
        evidence_classes: list[str], status: str, source_versions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        site = {
            "site_id": self.site.get("site_id"), "label": self.site.get("label"),
            "pack_digest": self.pack_digest,
        }
        if self.synthetic:
            site["synthetic"] = True
        descriptor = next(
            item for item in ESTIMATE_CAPABILITIES if item["capability_id"] == capability_id
        )
        result = {
            "schema_version": "idli-result/1",
            "result_id": result_id,
            "request_id": request_id,
            "revision": 1,
            "status": status,
            "site": site,
            "question": {"original": original, "resolved": resolved, "bindings": bindings},
            "answer": {
                "headline": headline, "detail": "", "evidence_classes": evidence_classes,
            },
            "visuals": [],
            "limitations": [],
            "actions": [],
            "audit": {
                "audit_id": f"{result_id}/1",
                "source_versions": source_versions,
                "capability_runs": [{
                    "capability_id": capability_id,
                    "version": descriptor["version"],
                    "status": "partial" if status == "partial" else (
                        "blocked" if status == "blocked" else "complete"
                    ),
                }],
                "query_hash": _digest({"capability_id": capability_id, "bindings": bindings}),
                # Every number in this envelope's modelled layer was produced by a fitted model,
                # not read from a source row. The transport must say so without being asked.
                "assurance": "generated",
            },
        }
        if self.synthetic:
            result["limitations"].append(self._limitation(
                "synthetic-data",
                "This result uses synthetic test data and is not evidence about a real place.",
                severity="info", affects=["answer"],
            ))
        return result

    def _write(
        self, result: dict[str, Any], payloads: dict[str, tuple[str, Any]]
    ) -> dict[str, Any]:
        root = self.state_root / "results" / result["result_id"]
        for handle, (media_type, payload) in payloads.items():
            if not SAFE_HANDLE.fullmatch(handle):
                raise ValueError(f"unsafe data handle: {handle}")
            suffix = ".geojson" if media_type == "application/geo+json" else ".json"
            declared = [
                reference["digest"]
                for visual in result["visuals"]
                for reference in (
                    [layer["data_ref"] for layer in visual["layers"]]
                    + [item["data_ref"] for item in visual.get("drilldowns") or []]
                )
                if reference.get("handle") == handle
            ]
            if _digest(payload) not in declared:
                raise RuntimeError(f"data-ref digest mismatch: {handle}")
            _atomic_write_once(
                root / "data" / f"{handle}{suffix}", _stable_json(payload).encode()
            )
        _atomic_write_once(
            root / "result.json",
            (json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n").encode(),
        )
        return result

    def _source_versions(
        self, connection: sqlite3.Connection, source_ids: set[str], planes: list[str]
    ) -> list[dict[str, Any]]:
        rows = {
            row["source_id"]: row for row in connection.execute(
                "SELECT source_id,title,content_sha256,capabilities_json FROM sources"
            )
        }
        return [
            {
                "source_id": source_id,
                "version": None,
                "digest": "sha256:" + rows[source_id]["content_sha256"],
                "synthetic": "synthetic" in json.loads(rows[source_id]["capabilities_json"]),
                "title": rows[source_id]["title"],
                # Which planes of this source the model actually consumed. An estimate that does
                # not name its inputs cannot be argued with.
                "planes_used": planes,
            }
            for source_id in sorted(source_ids) if source_id in rows
        ]

    # ------------------------------------------------------------------ visuals

    @staticmethod
    def _cell_feature(row: dict[str, Any], properties: dict[str, Any]) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": row["cell_id"],
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [row["west"], row["south"]], [row["east"], row["south"]],
                    [row["east"], row["north"]], [row["west"], row["north"]],
                    [row["west"], row["south"]],
                ]],
            },
            "properties": properties,
        }

    def _aoi_payload(self) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "id": "target",
                "geometry": self.aoi_geometry(),
                "properties": {
                    "label": self.site.get("label"),
                    "geometry_role": self.site["target_aoi"].get("geometry_role"),
                },
            }],
        }

    def _training_payload(
        self, table: dict[str, dict[str, Any]], observed: dict[str, float],
        target: dict[str, Any], target_cell: str,
    ) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [
                self._cell_feature(table[cell_id], {
                    "value": round(value, 4),
                    "unit": target["unit"],
                    "label": f"observed {target['label']}",
                    "role": "training cell (observed)",
                })
                for cell_id, value in sorted(observed.items()) if cell_id != target_cell
                and cell_id in table
            ],
        }

    # ------------------------------------------------------------------ entry point

    def run_estimate(
        self, approach_id: str, target_text: str, cell: Any,
        request_id: str = "", question: str = "", purpose: str = "",
    ) -> dict[str, Any]:
        """Run one approach for one cell and emit an idli-result/1 envelope."""
        approach = next(
            (item for item in self.APPROACHES if item["approach_id"] == approach_id), None
        )
        if approach is None:
            raise ValueError(
                f"unknown approach: {approach_id}; known: "
                + ", ".join(item["approach_id"] for item in self.APPROACHES)
            )
        resolved_cell = self.resolve_cell(cell)
        target = self.resolve_target(target_text)
        target_cell = resolved_cell["cell_id"]
        request_id = _clean(request_id)[:200] or f"estimate-{_digest(
            {'a': approach_id, 'c': target_cell, 't': target['target_id']}
        ).split(':', 1)[1][:12]}"
        with self.connect() as connection:
            table = self.cell_table(connection)
            observed = self._observed(table, target["target_id"])
            training_ids = sorted(key for key in observed if key != target_cell)
            gates = self._gates(approach_id, resolved_cell, observed, table)
            # The catalogue already knows which sources carry this target; naming those is more
            # honest than naming every source that happens to touch a training cell.
            source_ids = {
                _clean(item.get("source_id")) for item in target.get("sources") or []
                if item.get("source_id")
            } or {
                source for cell_id in training_ids
                for source in table.get(cell_id, {}).get("per_source", {})
            }
            if target["target_id"] in {"survey_effort", "effort_normalised_rate"}:
                source_ids |= {
                    row[0] for row in connection.execute(
                        "SELECT DISTINCT source_id FROM effort WHERE cell_id IS NOT NULL"
                    )
                }
            planes = list(target["planes"])
            source_versions = self._source_versions(connection, source_ids, planes)
        bindings = {
            "approach_id": approach_id, "target": target["target_id"],
            "cell_id": target_cell,
            "at": f"at:{resolved_cell['center_lat']:.4f}:{resolved_cell['center_lon']:.4f}",
            "purpose": _clean(purpose)[:400] or None,
        }
        original = _clean(question) or (
            f"Estimate {target['requested'] or target['label']} for the cell at "
            f"{bindings['at']}."
        )
        resolved_question = (
            f"Estimate {target['label']} for cell {target_cell} using "
            f"{approach['label'].lower()}, fitted on the pack's other surveyed cells."
        )
        result_id = "result-est-" + _digest({
            "site": self.site.get("site_id"), "pack": self.pack_digest,
            "request_id": request_id, **bindings,
        }).split(":", 1)[1][:20]
        failed = [item for item in gates if not item["passed"]]
        if failed:
            return self._blocked(
                result_id, request_id, original, resolved_question, bindings, approach,
                target, resolved_cell, table, observed, gates, failed, source_versions,
            )

        estimate, coefficients = self._predict(
            approach_id, target_cell, observed, table, set()
        )
        if estimate is None:
            failed = [{
                "gate": "predictor-degenerate",
                "requirement": "the fitted system must be solvable on this pack",
                "observed": "the normal equations were singular for every feature set tried",
                "passed": False,
            }]
            return self._blocked(
                result_id, request_id, original, resolved_question, bindings, approach,
                target, resolved_cell, table, observed, gates + failed, failed, source_versions,
            )

        # Leave-one-out residuals: refit without each training cell and predict it. This is the
        # only spread that describes how the model performs on data it did not see.
        measured = self._holdout(approach_id, training_ids, observed, table)
        residuals, held_out = measured["residuals"], measured["held_out"]
        if len(residuals) < 3:
            failed = [{
                "gate": "leave-one-out-residuals",
                "requirement": "at least 3 leave-one-out residuals are needed for an interval",
                "observed": f"{len(residuals)} residuals were computable",
                "passed": False,
            }]
            return self._blocked(
                result_id, request_id, original, resolved_question, bindings, approach,
                target, resolved_cell, table, observed, gates + failed, failed, source_versions,
            )

        low_offset, high_offset = measured["low_offset"], measured["high_offset"]
        # Every target here is a non-negative count or rate, so the interval is clipped at zero
        # rather than allowed to promise a negative quantity.
        floor = 0.0
        estimate_value = max(estimate, floor)
        low = max(estimate + low_offset, floor)
        high = max(estimate + high_offset, low)
        spread = high - low
        r2_loo, coverage = measured["r2"], measured["coverage"]
        signal_to_noise = (
            estimate_value / (spread / 2.0) if spread > 0 else float(len(residuals))
        )
        confidence = self._confidence_class(len(training_ids), r2_loo, signal_to_noise)
        confidence_basis = (
            f"{len(training_ids)} training cells; leave-one-out residual spread "
            f"{spread:.3g} {target['unit']} at the {int(INTERVAL_LEVEL * 100)}% level; "
            f"leave-one-out R² {r2_loo:.2f}; signal-to-noise {signal_to_noise:.2f}"
        )

        headline = (
            f"Estimated {target['label']} for cell {target_cell}: {estimate_value:.3g} "
            f"{target['unit']} ({int(INTERVAL_LEVEL * 100)}% interval {low:.3g}–{high:.3g}); "
            f"confidence {confidence.upper()}."
        )
        result = self._base(
            result_id, request_id, "cell-estimate-run", original, resolved_question,
            bindings, headline, ["derived", "modelled"], "complete", source_versions,
        )
        result["answer"]["detail"] = (
            f"This value was generated by {approach['label'].lower()} fitted on "
            f"{len(training_ids)} surveyed cells; the cell itself was held out of its own "
            "training set. It is a modelled expectation of what the pack's own recording would "
            "show here, not an observation and not a real-world quantity."
        )

        aoi = self._aoi_payload()
        training_payload = self._training_payload(table, observed, target, target_cell)
        estimated_payload = {
            "type": "FeatureCollection",
            "features": [self._cell_feature(
                {
                    "cell_id": target_cell,
                    "west": resolved_cell["west"], "south": resolved_cell["south"],
                    "east": resolved_cell["east"], "north": resolved_cell["north"],
                },
                {
                    "estimate": round(estimate_value, 4),
                    "interval_low": round(low, 4),
                    "interval_high": round(high, 4),
                    "interval_level": INTERVAL_LEVEL,
                    "unit": target["unit"],
                    "label": f"modelled {target['label']}",
                    "role": "estimated cell (modelled)",
                    "confidence": confidence,
                    "approach": approach_id,
                    **(
                        {"observed_value_for_comparison": round(observed[target_cell], 4)}
                        if target_cell in observed else {}
                    ),
                },
            )],
        }
        uncertainty = {
            "kind": "interval",
            "level": INTERVAL_LEVEL,
            "low": round(low, 4),
            "high": round(high, 4),
            "unit": target["unit"],
            "basis": "leave-one-out training residual quantiles",
            "agreement": {
                "fraction": round(coverage, 3),
                "signal_to_noise": round(signal_to_noise, 3),
            },
        }
        aoi_ref = self._data_ref("declared-aoi", "application/geo+json", aoi)
        training_ref = self._data_ref(
            "estimate-training-cells", "application/geo+json", training_payload)
        estimated_ref = self._data_ref(
            "estimated-cell", "application/geo+json", estimated_payload)
        residual_ref = self._data_ref(
            "estimate-holdout-residuals", "application/json", held_out)

        model_rows = (
            [
                {"feature": name, "coefficient": round(value, 6)}
                for name, value in zip(self.FEATURE_NAMES, coefficients)
            ] if coefficients else [
                {"feature": approach["label"], "coefficient": None},
            ]
        )
        model_ref = self._data_ref("estimate-model-terms", "application/json", model_rows)
        tiles = [
            {"label": "Estimate", "value": round(estimate_value, 3), "unit": target["unit"]},
            {
                "label": f"{int(INTERVAL_LEVEL * 100)}% interval",
                "value": f"{low:.3g} – {high:.3g}", "unit": target["unit"],
            },
            {"label": "Confidence", "value": confidence.upper(), "unit": "stated"},
            {"label": "Training cells", "value": len(training_ids), "unit": "cells"},
            {"label": "Leave-one-out R²", "value": round(r2_loo, 3), "unit": "held out"},
            {
                "label": "Interval coverage in held-out cells",
                "value": round(coverage, 3), "unit": "fraction",
            },
        ]
        tiles_ref = self._data_ref("estimate-summary-tiles", "application/json", tiles)

        limitations = [
            self._limitation(
                "estimate-confidence-basis",
                (
                    f"Confidence is {confidence.upper()} on this basis: {confidence_basis}. "
                    f"The interval is the {int(INTERVAL_LEVEL * 100)}% band of the model's own "
                    "leave-one-out residuals; it covered "
                    f"{coverage:.0%} of held-out surveyed cells."
                ),
                severity="info" if confidence == "high" else "warning",
                affects=["answer", "estimated-cell"],
            ),
            self._limitation(
                "modelled-not-observed",
                (
                    f"The value in cell {target_cell} is generated, not observed. It describes "
                    "what this pack's recording would be expected to show, so it inherits every "
                    "bias in where the pack's sources looked; it is not a measurement of the "
                    "place."
                ),
                severity="warning", affects=["estimated-cell"],
            ),
            self._limitation(
                "estimate-inputs-declared",
                (
                    "Features came only from the planes "
                    + ", ".join(planes)
                    + " of "
                    + ", ".join(item["source_id"] for item in source_versions)
                    + "; no other data of any kind entered the fit."
                ),
                severity="info", affects=["answer", "estimated-cell"],
            ),
        ]
        if len(training_ids) < 12:
            limitations.append(self._limitation(
                "sparse-training-set",
                (
                    f"Only {len(training_ids)} surveyed cells were available to fit; with this "
                    "few cells the interval is wide and the fitted structure may not generalise."
                ),
                severity="warning", affects=["answer"],
            ))
        if target_cell in observed:
            limitations.append(self._limitation(
                "target-cell-already-surveyed",
                (
                    f"Cell {target_cell} already carries observed data "
                    f"({observed[target_cell]:.3g} {target['unit']}). The estimate here is a "
                    "held-out check of the model, not new information about the cell; prefer the "
                    "observed value."
                ),
                severity="info", affects=["answer", "estimated-cell"],
            ))
        if not target["matched"]:
            limitations.append(self._limitation(
                "target-defaulted",
                (
                    f"No target was named, so the pack's default — {target['label']} — was "
                    "estimated. Name a target from the catalogue to estimate something else."
                ),
                severity="warning", affects=["answer"],
            ))
        counted = _clean((target.get("counts") or {}).get("column"))
        if counted:
            limitations.append(self._limitation(
                "target-count-semantics",
                (
                    f"This target sums the source column {counted!r}: "
                    + _clean((target.get("counts") or {}).get("aggregation"))
                    + ". Say what that column counts in the reader's own words."
                ),
                severity="info", affects=["answer"],
            ))
        result["limitations"].extend(limitations)

        result["visuals"] = [
            {
                "visual_id": "cell-estimate",
                "visual_type": "map",
                "view": "estimate-cell-surface",
                "title": (
                    f"{target['label'].capitalize()}: observed cells and the estimate for "
                    f"{target_cell}"
                ),
                "priority": "primary",
                "status": "ready",
                "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
                "layers": [
                    {
                        "layer_id": "declared-aoi", "evidence_class": "reported",
                        "geometry_type": "polygon", "data_ref": aoi_ref,
                        "legend": {"label": "Declared analysis area"},
                        "style_hint": {"palette_role": "reported"},
                    },
                    {
                        "layer_id": "estimate-training-cells", "evidence_class": "derived",
                        "geometry_type": "cell", "data_ref": training_ref,
                        "legend": {"label": f"Observed {target['label']} (training cells)"},
                        "style_hint": {"palette_role": "derived"},
                    },
                    {
                        "layer_id": "estimated-cell", "evidence_class": "modelled",
                        "geometry_type": "cell", "data_ref": estimated_ref,
                        "legend": {
                            "label": (
                                f"Estimated {target['label']} "
                                f"({int(INTERVAL_LEVEL * 100)}% interval "
                                f"{low:.3g}–{high:.3g})"
                            ),
                        },
                        "style_hint": {"palette_role": "modelled"},
                        "uncertainty": uncertainty,
                    },
                ],
                "summary": {
                    "headline": headline,
                    "denominators": {
                        "training_cells": len(training_ids),
                        "held_out_cells": len(held_out),
                        "sources": len(source_versions),
                        "interval_level": INTERVAL_LEVEL,
                    },
                },
                "drilldowns": [{
                    "action_id": "inspect-holdout-residuals",
                    "label": "Inspect the leave-one-out residual for every training cell",
                    "data_ref": residual_ref,
                }, {
                    "action_id": "inspect-model-terms",
                    "label": "Inspect the fitted model terms",
                    "data_ref": model_ref,
                }],
                "limitations": limitations,
            },
            {
                "visual_id": "estimate-summary",
                "visual_type": "metric",
                "view": "estimate-summary",
                "title": "How strong is this estimate?",
                "priority": "supporting",
                "status": "ready",
                "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
                "layers": [{
                    "layer_id": "estimate-summary-tiles", "evidence_class": "derived",
                    "geometry_type": "table", "data_ref": tiles_ref,
                    "legend": {"label": "Estimate, interval and held-out performance"},
                    "style_hint": {"palette_role": "derived"},
                }],
                "summary": {
                    "headline": confidence_basis,
                    "denominators": {"tiles": len(tiles)},
                },
                "drilldowns": [],
                "limitations": limitations[:1],
            },
        ]
        result["actions"] = self._data_requests(
            target_cell, target, table, observed, resolved_cell, spread, len(training_ids)
        )
        result["audit"]["estimate"] = {
            "approach_id": approach_id,
            "target_id": target["target_id"],
            "target_label": target["label"],
            "target_unit": target["unit"],
            "target_counts": target["counts"],
            "target_requested": target["requested"],
            "cell_id": target_cell,
            "estimate": round(estimate_value, 6),
            "interval": {
                "kind": "interval", "level": INTERVAL_LEVEL,
                "low": round(low, 6), "high": round(high, 6),
            },
            "training_cells": len(training_ids),
            "leave_one_out_r2": round(r2_loo, 4),
            "residual_spread": round(spread, 6),
            "interval_coverage": round(coverage, 4),
            "confidence": confidence,
            "confidence_basis": confidence_basis,
            "features": list(self.FEATURE_NAMES) if coefficients else [approach_id],
            "coefficients": (
                [round(value, 6) for value in coefficients] if coefficients else None
            ),
            "planes_used": planes,
            "gates": gates,
        }
        return self._write(result, {
            "declared-aoi": ("application/geo+json", aoi),
            "estimate-training-cells": ("application/geo+json", training_payload),
            "estimated-cell": ("application/geo+json", estimated_payload),
            "estimate-holdout-residuals": ("application/json", held_out),
            "estimate-model-terms": ("application/json", model_rows),
            "estimate-summary-tiles": ("application/json", tiles),
        })

    # ------------------------------------------------------------------ data requests

    def _data_requests(
        self, target_cell: str, target: dict[str, Any], table: dict[str, dict[str, Any]],
        observed: dict[str, float], resolved_cell: dict[str, Any], spread: float,
        training_count: int,
    ) -> list[dict[str, Any]]:
        """What extra data would most shrink this interval, named concretely, never vaguely."""
        unsurveyed = sorted(
            (
                (self._grid_distance(target_cell, cell_id) or 1e9, cell_id)
                for cell_id in table
                if cell_id not in observed and cell_id != target_cell
            ),
        )[:3]
        neighbours_missing = max(0, 8 - self._neighbour_support(target_cell, observed))
        requests = [{
            "action_id": "request-effort-in-nearest-unsurveyed-cells",
            "kind": "data_request",
            "label": (
                "Add effort rows for the nearest cells with no observed value: "
                + (", ".join(cell_id for _, cell_id in unsurveyed) or "none in the index")
            ),
            "capability_id": "cell-estimate-run",
            "arguments": {"cell": target_cell, "target": target["target_id"]},
            "requires_confirmation": True,
            "expected_effect": (
                f"Each surveyed neighbour tightens the adjacent-cell features directly; the "
                f"current interval spans {spread:.3g} {target['unit']} because the model is "
                f"fitted on only {training_count} cells."
            ),
        }, {
            "action_id": "request-survey-in-target-cell",
            "kind": "data_request",
            "label": (
                f"Survey cell {target_cell} itself "
                f"(centre {resolved_cell['center_lat']:.4f}, {resolved_cell['center_lon']:.4f})"
            ),
            "capability_id": "cell-estimate-run",
            "arguments": {"cell": target_cell, "target": target["target_id"]},
            "requires_confirmation": True,
            "expected_effect": (
                "One observed value replaces the estimate outright and removes its interval."
            ),
        }]
        if neighbours_missing:
            requests.append({
                "action_id": "request-neighbourhood-completion",
                "kind": "data_request",
                "label": (
                    f"Complete the 8-cell neighbourhood of {target_cell}: "
                    f"{neighbours_missing} of its 8 adjacent cells carry no observed value"
                ),
                "capability_id": "cell-estimate-run",
                "arguments": {"cell": target_cell, "target": target["target_id"]},
                "requires_confirmation": True,
                "expected_effect": (
                    "The adjacent-cell mean is the strongest feature in the fit; a complete ring "
                    "is what moves this estimate from a regional guess to a local one."
                ),
            })
        if target["target_id"] != "effort_normalised_rate":
            requests.append({
                "action_id": "request-effort-denominator",
                "kind": "data_request",
                "label": (
                    "Add documented survey effort for every cell so counts can be "
                    "effort-normalised instead of compared raw"
                ),
                "capability_id": "cell-estimate-run",
                "arguments": {"cell": target_cell, "target": "effort_normalised_rate"},
                "requires_confirmation": True,
                "expected_effect": (
                    "Record counts partly measure where people looked; an effort denominator "
                    "separates recording intensity from the quantity being estimated."
                ),
            })
        return requests

    # ------------------------------------------------------------------ blocked path

    def _blocked(
        self, result_id: str, request_id: str, original: str, resolved_question: str,
        bindings: dict[str, Any], approach: dict[str, Any], target: dict[str, Any],
        resolved_cell: dict[str, Any], table: dict[str, dict[str, Any]],
        observed: dict[str, float], gates: list[dict[str, Any]],
        failed: list[dict[str, Any]], source_versions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """A gate failed. Keep the observed map, name the gate, estimate nothing."""
        target_cell = resolved_cell["cell_id"]
        names = ", ".join(item["gate"] for item in failed)
        headline = (
            f"No estimate was produced for cell {target_cell}: "
            f"{approach['label'].lower()} failed the gate {names}."
        )
        result = self._base(
            result_id, request_id, "cell-estimate-run", original, resolved_question,
            bindings, headline, ["derived", "missing"], "blocked", source_versions,
        )
        result["answer"]["detail"] = (
            "The observed cells are still shown. A failed gate is a statement about this pack's "
            "data, not about the place: "
            + "; ".join(f"{item['gate']} — {item['observed']}" for item in failed)
            + "."
        )
        aoi = self._aoi_payload()
        training_payload = self._training_payload(table, observed, target, target_cell)
        blocked_payload = {
            "type": "FeatureCollection",
            "features": [self._cell_feature(
                {
                    "cell_id": target_cell,
                    "west": resolved_cell["west"], "south": resolved_cell["south"],
                    "east": resolved_cell["east"], "north": resolved_cell["north"],
                },
                {
                    "label": "no estimate: gate failed",
                    "role": "requested cell",
                    "failed_gates": names,
                },
            )],
        }
        aoi_ref = self._data_ref("declared-aoi", "application/geo+json", aoi)
        training_ref = self._data_ref(
            "estimate-training-cells", "application/geo+json", training_payload)
        blocked_ref = self._data_ref(
            "estimate-blocked-cell", "application/geo+json", blocked_payload)
        gate_ref = self._data_ref("estimate-gates", "application/json", gates)
        limitations = [
            self._limitation(
                "estimate-gate-failed",
                (
                    f"Gate {names} failed, so no value was generated. "
                    + "; ".join(
                        f"{item['gate']} requires {item['requirement']}, but {item['observed']}"
                        for item in failed
                    )
                    + "."
                ),
                severity="error", affects=["answer", "estimate-blocked-cell"],
            ),
            self._limitation(
                "observed-data-retained",
                (
                    f"{len(training_payload['features'])} surveyed cells are still drawn. The "
                    "absence of an estimate is not the absence of evidence."
                ),
                severity="info", affects=["estimate-training-cells"],
            ),
        ]
        result["limitations"].extend(limitations)
        result["visuals"] = [{
            "visual_id": "cell-estimate",
            "visual_type": "map",
            "view": "estimate-cell-surface",
            "title": f"Observed {target['label']} (no estimate for {target_cell})",
            "priority": "primary",
            "status": "blocked",
            "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
            "layers": [
                {
                    "layer_id": "declared-aoi", "evidence_class": "reported",
                    "geometry_type": "polygon", "data_ref": aoi_ref,
                    "legend": {"label": "Declared analysis area"},
                    "style_hint": {"palette_role": "reported"},
                },
                {
                    "layer_id": "estimate-training-cells", "evidence_class": "derived",
                    "geometry_type": "cell", "data_ref": training_ref,
                    "legend": {"label": f"Observed {target['label']}"},
                    "style_hint": {"palette_role": "derived"},
                },
                {
                    "layer_id": "estimate-blocked-cell", "evidence_class": "missing",
                    "geometry_type": "cell", "data_ref": blocked_ref,
                    "legend": {"label": f"Requested cell — gate {names} failed"},
                    "style_hint": {"palette_role": "missing"},
                },
            ],
            "summary": {
                "headline": headline,
                "denominators": {
                    "observed_cells": len(training_payload["features"]),
                    "failed_gates": len(failed),
                },
            },
            "drilldowns": [{
                "action_id": "inspect-gates",
                "label": "Inspect every gate and what it saw",
                "data_ref": gate_ref,
            }],
            "limitations": limitations,
        }]
        result["actions"] = self._data_requests(
            target_cell, target, table, observed, resolved_cell, 0.0, len(observed)
        )
        result["audit"]["estimate"] = {
            "approach_id": approach["approach_id"],
            "target_id": target["target_id"],
            "target_label": target["label"],
            "target_unit": target["unit"],
            "target_counts": target["counts"],
            "target_requested": target["requested"],
            "cell_id": target_cell,
            "estimate": None,
            "failed_gates": [item["gate"] for item in failed],
            "gates": gates,
        }
        return self._write(result, {
            "declared-aoi": ("application/geo+json", aoi),
            "estimate-training-cells": ("application/geo+json", training_payload),
            "estimate-blocked-cell": ("application/geo+json", blocked_payload),
            "estimate-gates": ("application/json", gates),
        })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--cell", help="at:<lat>:<lon> or a cell id")
    parser.add_argument("--target", default="", help="a target_id from --targets")
    parser.add_argument("--approach", help="omit to list approaches instead of running one")
    parser.add_argument("--purpose", default="")
    parser.add_argument(
        "--targets", action="store_true",
        help="list every quantity this index can be asked to estimate, and exit",
    )
    args = parser.parse_args(argv)
    service = EstimateService(args.site_pack, args.index, args.state)
    if args.targets:
        payload = service.target_catalogue()
    elif not args.cell:
        parser.error("--cell is required unless --targets is given")
    payload = payload if args.targets else (
        service.run_estimate(args.approach, args.target, args.cell, purpose=args.purpose)
        if args.approach else service.suggest_approaches(args.target, args.cell)
    )
    print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
