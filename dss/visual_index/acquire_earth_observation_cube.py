#!/usr/bin/env python3
"""Acquire a reproducible, cell-aligned Earth-observation feature cube.

The script is site-agnostic: it reads the cells in a built visual-site-pack
index and samples declared Earth Engine assets over those cell polygons. It
writes a long-form CSV plus a manifest containing the assets, periods,
reducers, scale, feature semantics and output digest. Credentials remain in
Earth Engine's normal user configuration and are never copied into the pack.

The output is context/model input. It is not evidence that an entity occurs,
that an intervention caused a change, or that a model transfers successfully.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
import sqlite3
from datetime import datetime, timezone
from typing import Any

import ee


ASSETS = {
    "alphaearth": {
        "asset_id": "GOOGLE/SATELLITE_EMBEDDING/V1/ANNUAL",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/"
        "GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL",
        "evidence_class": "modelled",
        "native_scale_m": 10,
        "rights": "CC-BY-4.0; attribution required",
    },
    "sentinel2": {
        "asset_id": "COPERNICUS/S2_SR_HARMONIZED",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/"
        "COPERNICUS_S2_SR_HARMONIZED",
        "evidence_class": "derived",
        "native_scale_m": "10-20",
        "rights": "Copernicus Sentinel Data Terms and Conditions",
    },
    "dynamic_world": {
        "asset_id": "GOOGLE/DYNAMICWORLD/V1",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/"
        "GOOGLE_DYNAMICWORLD_V1",
        "evidence_class": "modelled",
        "native_scale_m": 10,
        "rights": "CC-BY-4.0; attribution required",
    },
    "terrain": {
        "asset_id": "USGS/SRTMGL1_003",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/"
        "USGS_SRTMGL1_003",
        "evidence_class": "derived",
        "native_scale_m": 30,
        "rights": "See USGS SRTM provider terms",
    },
    "era5_land": {
        "asset_id": "ECMWF/ERA5_LAND/MONTHLY_AGGR",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/"
        "ECMWF_ERA5_LAND_MONTHLY_AGGR",
        "evidence_class": "modelled",
        "native_scale_m": 11132,
        "rights": "Copernicus Climate Change Service attribution required",
    },
    "chirps": {
        "asset_id": "UCSB-CHG/CHIRPS/DAILY",
        "url": "https://developers.google.com/earth-engine/datasets/catalog/"
        "UCSB_CHG_CHIRPS_DAILY",
        "evidence_class": "modelled",
        "native_scale_m": 5566,
        "rights": "See CHIRPS provider terms",
    },
}


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _cells(index_path: pathlib.Path) -> list[dict[str, Any]]:
    connection = sqlite3.connect(f"file:{index_path.resolve()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = [
            dict(row) for row in connection.execute(
                """SELECT cell_id,west,south,east,north,center_lat,center_lon,target_role
                   FROM cells ORDER BY cell_id"""
            )
        ]
    finally:
        connection.close()
    if not rows:
        raise ValueError("the index contains no cells")
    return rows


def _feature_collection(cells: list[dict[str, Any]]) -> ee.FeatureCollection:
    return ee.FeatureCollection([
        ee.Feature(
            ee.Geometry.Rectangle(
                [cell["west"], cell["south"], cell["east"], cell["north"]],
                proj=None,
                geodesic=False,
            ),
            {
                "cell_id": cell["cell_id"],
                "west": cell["west"],
                "south": cell["south"],
                "east": cell["east"],
                "north": cell["north"],
                "center_lat": cell["center_lat"],
                "center_lon": cell["center_lon"],
                "target_role": cell["target_role"],
            },
        )
        for cell in cells
    ])


def _mask_sentinel2(image: ee.Image) -> ee.Image:
    """Mask common cloud, shadow and snow classes using the retained SCL band."""
    scl = image.select("SCL")
    clear = (
        scl.neq(1)
        .And(scl.neq(3))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )
    reflectance = image.select(["B2", "B3", "B4", "B8", "B11", "B12"]).divide(10000)
    return reflectance.updateMask(clear).copyProperties(image, ["system:time_start"])


def _sentinel_indices(image: ee.Image) -> ee.Image:
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("s2_ndvi")
    ndmi = image.normalizedDifference(["B8", "B11"]).rename("s2_ndmi")
    nbr = image.normalizedDifference(["B8", "B12"]).rename("s2_nbr")
    evi = image.expression(
        "2.5 * ((nir - red) / (nir + 6 * red - 7.5 * blue + 1))",
        {
            "nir": image.select("B8"),
            "red": image.select("B4"),
            "blue": image.select("B2"),
        },
    ).rename("s2_evi")
    return image.addBands([ndvi, ndmi, nbr, evi])


def _composite(year: int, region: ee.Geometry) -> tuple[ee.Image, list[dict[str, Any]]]:
    start = f"{year}-01-01"
    end = f"{year + 1}-01-01"
    features: list[dict[str, Any]] = []

    alpha_bands = [f"A{index:02d}" for index in range(64)]
    alpha_names = [f"alphaearth_{band}" for band in alpha_bands]
    alpha = (
        ee.ImageCollection(ASSETS["alphaearth"]["asset_id"])
        .filterDate(start, end)
        .filterBounds(region)
        .mosaic()
        .select(alpha_bands, alpha_names)
    )
    features.extend({
        "feature_id": name,
        "unit": "dimensionless",
        "asset_key": "alphaearth",
        "evidence_class": "modelled",
        "description": (
            "One axis of the 64-dimensional annual satellite embedding. "
            "Axes are not independently interpretable and must be used together."
        ),
    } for name in alpha_names)

    sentinel = (
        ee.ImageCollection(ASSETS["sentinel2"]["asset_id"])
        .filterDate(start, end)
        .filterBounds(region)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 60))
        .map(_mask_sentinel2)
        .map(_sentinel_indices)
    )
    annual_names = [
        "s2_ndvi_annual_median", "s2_evi_annual_median",
        "s2_ndmi_annual_median", "s2_nbr_annual_median",
    ]
    annual = sentinel.select(
        ["s2_ndvi", "s2_evi", "s2_ndmi", "s2_nbr"]
    ).median().rename(annual_names)
    features.extend({
        "feature_id": name,
        "unit": "dimensionless",
        "asset_key": "sentinel2",
        "evidence_class": "derived",
        "description": "Annual median of a cloud-masked Sentinel-2 surface-reflectance index.",
    } for name in annual_names)
    valid = sentinel.select("s2_ndvi").count().rename("s2_valid_observations_mean")
    features.append({
        "feature_id": "s2_valid_observations_mean",
        "unit": "valid-scenes-per-pixel",
        "asset_key": "sentinel2",
        "evidence_class": "derived",
        "description": "Mean number of valid Sentinel-2 observations contributing within the cell.",
    })
    monthly_images: list[ee.Image] = []
    for month in range(1, 13):
        month_start = ee.Date.fromYMD(year, month, 1)
        month_end = month_start.advance(1, "month")
        name = f"s2_ndvi_m{month:02d}_median"
        monthly_images.append(
            sentinel.filterDate(month_start, month_end).select("s2_ndvi").median().rename(name)
        )
        features.append({
            "feature_id": name,
            "unit": "dimensionless",
            "asset_key": "sentinel2",
            "evidence_class": "derived",
            "description": "Monthly median cloud-masked Sentinel-2 NDVI.",
        })
    sentinel_composite = annual.addBands(valid)
    for image in monthly_images:
        sentinel_composite = sentinel_composite.addBands(image)

    dynamic_bands = [
        "water", "trees", "grass", "flooded_vegetation", "crops",
        "shrub_and_scrub", "built", "bare", "snow_and_ice",
    ]
    dynamic_names = [f"dw_{name}_probability" for name in dynamic_bands]
    dynamic = (
        ee.ImageCollection(ASSETS["dynamic_world"]["asset_id"])
        .filterDate(start, end)
        .filterBounds(region)
        .select(dynamic_bands)
        .mean()
        .rename(dynamic_names)
    )
    features.extend({
        "feature_id": name,
        "unit": "probability-score",
        "asset_key": "dynamic_world",
        "evidence_class": "modelled",
        "description": "Annual mean Dynamic World class score; scores are model outputs, not cover measurements.",
    } for name in dynamic_names)

    elevation = ee.Image(ASSETS["terrain"]["asset_id"]).select("elevation")
    terrain = elevation.rename("terrain_elevation_m").addBands(
        ee.Terrain.slope(elevation).rename("terrain_slope_degrees")
    )
    features.extend([
        {
            "feature_id": "terrain_elevation_m",
            "unit": "m",
            "asset_key": "terrain",
            "evidence_class": "derived",
            "description": "Mean SRTM elevation within the cell.",
        },
        {
            "feature_id": "terrain_slope_degrees",
            "unit": "degrees",
            "asset_key": "terrain",
            "evidence_class": "derived",
            "description": "Mean slope derived from SRTM elevation.",
        },
    ])

    era = (
        ee.ImageCollection(ASSETS["era5_land"]["asset_id"])
        .filterDate(start, end)
        .filterBounds(region)
    )
    era_image = (
        era.select("temperature_2m").mean().subtract(273.15)
        .rename("era5_temperature_2m_c")
        .addBands(
            era.select("total_precipitation_sum").sum().multiply(1000)
            .rename("era5_total_precipitation_mm")
        )
        .addBands(
            era.select("volumetric_soil_water_layer_1").mean()
            .rename("era5_soil_water_layer_1")
        )
    )
    features.extend([
        {
            "feature_id": "era5_temperature_2m_c",
            "unit": "degC",
            "asset_key": "era5_land",
            "evidence_class": "modelled",
            "description": "Annual mean ERA5-Land 2 m air temperature.",
        },
        {
            "feature_id": "era5_total_precipitation_mm",
            "unit": "mm/year",
            "asset_key": "era5_land",
            "evidence_class": "modelled",
            "description": "Sum of ERA5-Land monthly total precipitation.",
        },
        {
            "feature_id": "era5_soil_water_layer_1",
            "unit": "m3/m3",
            "asset_key": "era5_land",
            "evidence_class": "modelled",
            "description": "Annual mean ERA5-Land volumetric soil water in layer 1.",
        },
    ])

    chirps = (
        ee.ImageCollection(ASSETS["chirps"]["asset_id"])
        .filterDate(start, end)
        .filterBounds(region)
        .select("precipitation")
        .sum()
        .rename("chirps_total_precipitation_mm")
    )
    features.append({
        "feature_id": "chirps_total_precipitation_mm",
        "unit": "mm/year",
        "asset_key": "chirps",
        "evidence_class": "modelled",
        "description": "Annual CHIRPS precipitation total; a gridded rainfall estimate, not a local gauge.",
    })

    return (
        alpha.addBands(sentinel_composite)
        .addBands(dynamic)
        .addBands(terrain)
        .addBands(era_image)
        .addBands(chirps),
        features,
    )


def _number(value: Any) -> float | None:
    if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        return None
    return float(value)


def acquire(
    index_path: pathlib.Path,
    output_dir: pathlib.Path,
    year: int,
    scale_m: int,
    tile_scale: int,
) -> dict[str, Any]:
    cells = _cells(index_path)
    collection = _feature_collection(cells)
    image, feature_catalog = _composite(year, collection.geometry())
    reduced = image.reduceRegions(
        collection=collection,
        reducer=ee.Reducer.mean(),
        scale=scale_m,
        tileScale=tile_scale,
    ).getInfo()
    by_cell = {
        feature["properties"]["cell_id"]: feature["properties"]
        for feature in reduced.get("features", [])
    }
    metadata = {item["feature_id"]: item for item in feature_catalog}
    monthly = [f"s2_ndvi_m{month:02d}_median" for month in range(1, 13)]
    derived_catalog = [
        {
            "feature_id": "s2_ndvi_amplitude",
            "unit": "dimensionless",
            "asset_key": "sentinel2",
            "evidence_class": "derived",
            "description": "Maximum minus minimum available monthly median NDVI.",
        },
        {
            "feature_id": "s2_ndvi_valid_months",
            "unit": "months",
            "asset_key": "sentinel2",
            "evidence_class": "derived",
            "description": "Number of months with a finite monthly median NDVI.",
        },
    ]
    feature_catalog.extend(derived_catalog)
    metadata.update({item["feature_id"]: item for item in derived_catalog})

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"cell_features_{year}.csv"
    fields = [
        "cell_id", "west", "south", "east", "north", "center_lat", "center_lon",
        "target_role", "year", "feature_id", "value", "unit", "evidence_class",
        "source_asset", "aggregation", "scale_m",
    ]
    rows_written = 0
    missing_values = 0
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for cell in cells:
            values = dict(by_cell.get(cell["cell_id"], {}))
            available_months = [
                _number(values.get(name)) for name in monthly
                if _number(values.get(name)) is not None
            ]
            values["s2_ndvi_amplitude"] = (
                max(available_months) - min(available_months)
                if len(available_months) >= 2 else None
            )
            values["s2_ndvi_valid_months"] = float(len(available_months))
            for item in feature_catalog:
                feature_id = item["feature_id"]
                value = _number(values.get(feature_id))
                if value is None:
                    missing_values += 1
                    continue
                asset = ASSETS[item["asset_key"]]
                writer.writerow({
                    **cell,
                    "year": year,
                    "feature_id": feature_id,
                    "value": format(value, ".12g"),
                    "unit": item["unit"],
                    "evidence_class": item["evidence_class"],
                    "source_asset": asset["asset_id"],
                    "aggregation": "cell-mean" if feature_id != "s2_ndvi_valid_months" else "count",
                    "scale_m": scale_m,
                })
                rows_written += 1

    manifest = {
        "schema_version": "earth-observation-feature-cube/0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "year": year,
        "cell_count": len(cells),
        "feature_count": len(feature_catalog),
        "row_count": rows_written,
        "missing_value_count": missing_values,
        "reducer": "mean over declared cell polygon",
        "requested_scale_m": scale_m,
        "tile_scale": tile_scale,
        "sentinel2_cloud_rule": (
            "SCL classes 1, 3, 8, 9, 10 and 11 excluded; scenes prefiltered below "
            "60 percent CLOUDY_PIXEL_PERCENTAGE"
        ),
        "assets": ASSETS,
        "features": feature_catalog,
        "output": {
            "path": csv_path.name,
            "sha256": _sha256(csv_path),
        },
        "limitations": [
            "Cell means smooth within-cell variation and do not represent a field measurement.",
            "AlphaEarth axes are not independently interpretable; use all 64 together.",
            "A mean AlphaEarth vector is not guaranteed to remain unit length; normalise it before cosine similarity.",
            "Dynamic World probabilities are model scores and should not be relabelled as measured cover.",
            "ERA5-Land and CHIRPS are coarser than the serving cells; repeated neighbouring values are expected.",
            "Cloud screening does not eliminate every atmospheric or terrain-shadow artefact.",
            "This cube is a predictor substrate. Transfer and causal claims require separate gates.",
        ],
    }
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--index", required=True, type=pathlib.Path)
    parser.add_argument("--output-dir", required=True, type=pathlib.Path)
    parser.add_argument("--year", type=int, default=2024)
    parser.add_argument("--scale-m", type=int, default=100)
    parser.add_argument("--tile-scale", type=int, default=4)
    args = parser.parse_args()
    ee.Initialize()
    manifest = acquire(
        args.index, args.output_dir, args.year, args.scale_m, args.tile_scale
    )
    print(json.dumps({
        "year": manifest["year"],
        "cells": manifest["cell_count"],
        "features": manifest["feature_count"],
        "rows": manifest["row_count"],
        "missing": manifest["missing_value_count"],
        "sha256": manifest["output"]["sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
