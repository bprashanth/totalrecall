#!/usr/bin/env python3
"""Export privacy-conscious aggregate Valparai data for the public visual demo."""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sqlite3
import statistics


ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_INDEX = ROOT / "runs" / "insight-valparai" / "visual-index" / "site_index.sqlite"
DEFAULT_SITE = ROOT / "dss" / "sites" / "valparai" / "site.json"
DEFAULT_OUTPUT = pathlib.Path(__file__).resolve().parents[1] / "public" / "demo" / "valparai.json"


def quantile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lo, hi = math.floor(position), math.ceil(position)
    if lo == hi:
        return ordered[lo]
    return ordered[lo] * (hi - position) + ordered[hi] * (position - lo)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", type=pathlib.Path, default=DEFAULT_INDEX)
    parser.add_argument("--site", type=pathlib.Path, default=DEFAULT_SITE)
    parser.add_argument("--output", type=pathlib.Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    site = json.loads(args.site.read_text(encoding="utf-8"))
    db = sqlite3.connect(f"file:{args.index.resolve()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row

    cells = []
    for row in db.execute(
        """
        SELECT c.cell_id,c.west,c.south,c.east,c.north,c.center_lat,c.center_lon,c.target_role,
               COUNT(DISTINCT e.event_id) records,
               COUNT(DISTINCT e.entity_id) entities,
               COUNT(DISTINCT f.effort_id) effort_visits,
               COALESCE(SUM(DISTINCT f.effort_value),0) effort_value
        FROM cells c
        LEFT JOIN events e ON e.cell_id=c.cell_id
        LEFT JOIN effort f ON f.cell_id=c.cell_id
        GROUP BY c.cell_id
        ORDER BY c.cell_id
        """
    ):
        cells.append(dict(row))

    seasonal = []
    for month in range(1, 13):
        feature = f"s2_ndvi_m{month:02d}_median"
        values = [
            float(row[0])
            for row in db.execute(
                "SELECT value FROM cell_features WHERE feature_id=? AND year=2024",
                (feature,),
            )
            if row[0] is not None
        ]
        seasonal.append(
            {
                "month": month,
                "median": statistics.median(values) if values else None,
                "p10": quantile(values, 0.1),
                "p90": quantile(values, 0.9),
                "cells": len(values),
            }
        )

    acoustic = [
        dict(row)
        for row in db.execute(
            """
            SELECT x_value hour,
                   CAST(CAST(y_value AS REAL)/1.5 AS INTEGER)*1.5 frequency_band,
                   AVG(value) value,COUNT(*) support
            FROM matrix_values
            WHERE matrix_id='acoustic_space_use_by_hour_frequency'
            GROUP BY x_value,frequency_band
            ORDER BY x_value,frequency_band
            """
        )
    ]

    restoration = [
        dict(row)
        for row in db.execute(
            """
            SELECT metric,json_extract(properties_json,'$.comparison_class') comparison_class,
                   value,unit,json_extract(properties_json,'$.plot_id') plot_id
            FROM measurements
            WHERE source_id='derived-restoration-plot-indicators-v1'
              AND metric IN (
                'regeneration_tree_species_richness',
                'regeneration_old_growth_species_richness',
                'adult_tree_species_richness',
                'adult_basal_area_per_ha'
              )
              AND value IS NOT NULL
            ORDER BY metric,comparison_class,plot_id
            """
        )
    ]

    summary = dict(
        db.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM sources) sources,
              (SELECT COUNT(*) FROM events) records,
              (SELECT COUNT(*) FROM events WHERE cell_id IS NOT NULL) mapped_records,
              (SELECT COUNT(*) FROM entities) entities,
              (SELECT COUNT(*) FROM effort) effort_rows,
              (SELECT COUNT(*) FROM measurements) measurements,
              (SELECT COUNT(*) FROM locations) locations
            """
        ).fetchone()
    )
    source_families = [
        dict(row)
        for row in db.execute(
            """
            SELECT source_id,title,license,capabilities_json
            FROM sources ORDER BY source_id
            """
        )
    ]
    for source in source_families:
        source["capabilities"] = json.loads(source.pop("capabilities_json"))

    payload = {
        "schema_version": "fieldnote-demo/1",
        "generated_from": "Valparai visual site index; aggregate public preview",
        "site": {
            "site_id": site["site_id"],
            "label": site["label"],
            "target_aoi": site["target_aoi"],
            "context_aoi": site["context_aoi"],
        },
        "summary": summary,
        "cells": cells,
        "seasonal_ndvi": seasonal,
        "acoustic": acoustic,
        "restoration": restoration,
        "sources": source_families,
        "limitations": [
            "This public preview contains aggregate cells, not precise occurrence coordinates.",
            "Record density reflects both nature and where people looked.",
            "The declared study envelope is not a legal property boundary.",
            "The 2024 greenness sequence has incomplete cloudy-season support.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print(json.dumps({"output": str(args.output), "cells": len(cells), "sources": len(source_families)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
