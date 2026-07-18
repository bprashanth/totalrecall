"""Thin typed-contract adapters over the locked origin connector snapshot.

The production algorithms live unchanged under ``integration/origin/connectors``. Adapters may
validate inputs and attach typed metadata, but must not reproduce connector computations.
"""
import csv
import hashlib
import importlib
import json
import os
import subprocess
import sys


HERE = os.path.dirname(os.path.abspath(__file__))
MEMORY = os.path.dirname(HERE)
INTEGRATION = os.path.join(MEMORY, "integration")
ORIGIN_CONNECTORS = os.environ.get(
    "DSS_ORIGIN_CONNECTORS",
    os.path.join(INTEGRATION, "origin", "connectors"),
)
ORIGIN_LOCK = os.path.join(INTEGRATION, "manifests", "origin-lock.json")


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify(names):
    with open(ORIGIN_LOCK, encoding="utf-8") as stream:
        lock = json.load(stream)
    for name in names:
        path = os.path.join(ORIGIN_CONNECTORS, name)
        expected = lock["files"][f"dss/connectors/{name}"]["sha256"]
        actual = _sha256(path)
        if actual != expected:
            raise RuntimeError(
                f"origin connector snapshot drift for {name}: expected {expected}, got {actual}"
            )


def _module(name):
    _verify(["_base.py", f"{name}.py"])
    if ORIGIN_CONNECTORS not in sys.path:
        sys.path.insert(0, ORIGIN_CONNECTORS)
    return importlib.import_module(name)


def points_occurrences(resolution, region, time_value=None, limit=200):
    """Use the exact origin points resolver/merger and normalize only its return envelope.

    The imported connector has no time argument and its cached CSV intentionally carries a small
    common schema.  A typed time window therefore fails closed instead of being silently ignored.
    """
    if time_value:
        return {
            "rows": [], "kind": "records", "source": "origin points.py",
            "label": "observed", "grain": "occurrence",
            "unsupported_time": True,
            "note": "origin points.get cannot enforce a typed time window",
        }
    _verify(["_base.py", "points.py", "occurrence.py", "inaturalist.py", "paper_data.py"])
    points = _module("points")
    s, n, w, e = region["bbox"]
    bbox = [w, s, e, n]
    result = points.get(
        resolution["canonical"], bbox=bbox, limit=min(int(limit), 500), resolve_name=False
    )
    raw_rows = []
    path = result.get("path")
    if path and os.path.exists(path):
        with open(path, newline="", encoding="utf-8") as stream:
            raw_rows = list(csv.DictReader(stream))
    rows = []
    for index, row in enumerate(raw_rows):
        try:
            lat, lon = float(row["lat"]), float(row["lon"])
        except (KeyError, TypeError, ValueError):
            continue
        dataset = row.get("dataset") or "origin points"
        provider = "iNaturalist" if "inaturalist" in dataset.lower() else "GBIF/paper-data"
        rows.append({
            "id": f"origin-points:{index}:{row.get('id', '')}",
            "lat": lat, "lon": lon,
            "name": resolution["canonical"],
            "scientific_name": row.get("species") or resolution["canonical"],
            "time": row.get("year"), "source": provider, "dataset": dataset,
        })
    return {
        "rows": rows,
        "kind": "records",
        "source": "origin points.py → GBIF + iNaturalist + paper_data",
        "label": "observed",
        "grain": "occurrence",
        "resolution": resolution,
        "count_admissible": resolution.get("count_admissible", False),
        "query_time": time_value,
        "region": region,
        "source_totals": result.get("by_source"),
        "connector_events": [{
            "tool": "origin.points.get",
            "implementation": os.path.join(ORIGIN_CONNECTORS, "points.py"),
            "parameters": {
                "species": resolution["canonical"], "bbox": bbox,
                "sources": ["gbif", "inat", "paper"], "limit": min(int(limit), 500),
            },
            "output_rows": len(rows),
            "cached": result.get("cached", False),
        }],
        "note": (
            f"{len(rows)} coordinate-deduplicated occurrence points from the exact origin resolver; "
            "the origin common CSV omits record URLs and licenses, an import incompatibility"
        ),
    }


def semantic_discovery(query, k=5, points_only=True):
    """Execute the exact origin semantic-card connector in its production dependency context."""
    _verify(["discovery.py"])
    script = os.path.join(ORIGIN_CONNECTORS, "discovery.py")
    command = [sys.executable, script, "search", "--query", query, "--k", str(int(k))]
    if points_only:
        command.append("--points-only")
    completed = subprocess.run(command, text=True, capture_output=True, timeout=180)
    implementation = script
    detail = (completed.stderr or completed.stdout).strip()
    if completed.returncode != 0 and "No module named 'fastembed'" in detail and \
            not os.path.exists("/.dockerenv"):
        container = os.environ.get("HERMES_CONTAINER", "hermes-live")
        container_script = "/opt/data/connectors/discovery.py"
        command = ["docker", "exec", container, "python", container_script,
                   "search", "--query", query, "--k", str(int(k))]
        if points_only:
            command.append("--points-only")
        completed = subprocess.run(command, text=True, capture_output=True, timeout=180)
        implementation = f"{container}:{container_script}"
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-500:]
        raise RuntimeError(f"origin discovery failed: {detail}")
    result = json.loads(completed.stdout)
    return {
        **result,
        "connector_events": [{
            "tool": "origin.discovery.search",
            "implementation": implementation,
            "parameters": {"query": query, "k": int(k), "points_only": points_only},
            "output_rows": len(result.get("results") or []),
        }],
    }


def fire_exposure(records, region, start_year=2020, end_year=2025, radius_km=5):
    """Run exact origin AOI-points and point-exposure functions; keep their grains separate."""
    if end_year < start_year:
        start_year, end_year = end_year, start_year
    fire = _module("fire")
    years = f"{start_year}-{end_year}"
    rows = fire.exposure(
        records,
        radius_km=radius_km,
        years=years,
        project=os.environ.get("EE_PROJECT", "plantwars"),
    )
    s, n, w, e = region["bbox"]
    site_points = fire.points(
        bbox=[w, s, e, n],
        years=years,
        project=os.environ.get("EE_PROJECT", "plantwars"),
    )
    normalized_rows = []
    for row in rows:
        normalized = {key: value for key, value in row.items() if key != "fire_count"}
        # Origin's `fire_count` is a sum of MODIS active-fire pixels across composite days. It is
        # not a count of ignition events. Name the physical proxy at the typed boundary so a
        # responder cannot silently turn it into “fires” or “events.”
        normalized["pixel_fire_days"] = row.get("fire_count")
        normalized.update({"period": years,
                           "analysis_bbox_active_fire_locations": len(site_points),
                           "analysis_bbox": [w, s, e, n]})
        normalized_rows.append(normalized)
    rows = normalized_rows
    return {
        "rows": rows,
        "kind": "records",
        "source": "origin fire.py → MODIS/061/MOD14A1 via Earth Engine",
        "label": "proxy",
        "measure_field": "fire_density",
        "unit": "pixel-fire-days/km²",
        "field_units": {"pixel_fire_days": "pixel-fire-days",
                        "fire_density": "pixel-fire-days/km²",
                        "analysis_bbox_active_fire_locations": "active-fire locations"},
        "measurement_scopes": [
            {
                "scope": "declared analysis bbox",
                "geometry": [w, s, e, n],
                "measure": "MODIS active-fire locations",
                "value": len(site_points),
                "period": years,
                "warning": "This bbox is not a surveyed property polygon.",
            },
            {
                "scope": f"{radius_km}-km buffer around the EBTL site-centre point",
                "measure": "MODIS fire exposure proxy",
                "pixel_fire_days": rows[0].get("pixel_fire_days") if rows else None,
                "fire_density": rows[0].get("fire_density") if rows else None,
                "units": {"pixel_fire_days": "pixel-fire-days",
                          "fire_density": "pixel-fire-days/km²"},
                "period": years,
            },
        ],
        "grain": f"{radius_km}-km-buffer-around-point",
        "layer": "fire_exposure",
        "query_time": {"start": str(start_year), "end": str(end_year)},
        "connector_events": [
            {
                "tool": "origin.fire.points",
                "implementation": os.path.join(ORIGIN_CONNECTORS, "fire.py"),
                "parameters": {"bbox": [w, s, e, n], "years": years,
                               "project": os.environ.get("EE_PROJECT", "plantwars")},
                "output_rows": len(site_points),
            },
            {
                "tool": "origin.fire.exposure",
                "implementation": os.path.join(ORIGIN_CONNECTORS, "fire.py"),
                "input_rows": len(records),
                "parameters": {"radius_km": radius_km, "years": years,
                               "project": os.environ.get("EE_PROJECT", "plantwars")},
                "output_rows": len(rows),
            },
        ],
        "note": (
            f"{len(site_points)} historical {start_year}-{end_year} MODIS active-fire locations "
            f"inside the declared analysis bbox; that bbox is not a surveyed property polygon; "
            f"point exposure was also measured within {radius_km} km; pixel-fire-days are a "
            "pressure proxy, not fire probability or burned area"
        ),
    }


def landcover_summary(records, region, scale=100):
    """Run exact origin point classification plus exact-AOI area histogram."""
    landcover = _module("landcover")
    project = os.environ.get("EE_PROJECT", "plantwars")
    classified = landcover.classify(records, project=project)
    s, n, w, e = region["bbox"]
    bbox = [w, s, e, n]
    area = landcover.area_by_class(bbox, project=project, scale=scale)
    rows = [{**row, "area_by_class_km2": area, "analysis_bbox": bbox} for row in classified]
    return {
        "rows": rows,
        "kind": "records",
        "source": "origin landcover.py → ESA/WorldCover/v200 via Earth Engine",
        "label": "modelled",
        "grain": "declared-site-center + exact-analysis-bbox-histogram",
        "layer": "landcover",
        "connector_events": [
            {"tool": "origin.landcover.classify",
             "implementation": os.path.join(ORIGIN_CONNECTORS, "landcover.py"),
             "input_rows": len(records), "parameters": {"project": project},
             "output_rows": len(classified)},
            {"tool": "origin.landcover.area_by_class",
             "implementation": os.path.join(ORIGIN_CONNECTORS, "landcover.py"),
             "parameters": {"bbox": bbox, "project": project, "scale": scale},
             "output_rows": len(area)},
        ],
        "note": (
            "WorldCover v200 classification at the declared centre plus class-area histogram over "
            "the exact analysis bbox; the bbox is not a surveyed property boundary"
        ),
    }


def greenness_trend(records, start_year=2019, end_year=2024):
    """Run the exact origin greenness point-trend connector and type its proxy result."""
    if end_year < start_year:
        start_year, end_year = end_year, start_year
    years = f"{start_year}-{end_year}"
    project = os.environ.get("EE_PROJECT", "plantwars")
    rows = _module("greenness").trend(records, years=years, project=project)
    return {
        "rows": [{**row, "period": years} for row in rows],
        "kind": "records",
        "source": "origin greenness.py → MODIS/061/MOD13Q1 via Earth Engine",
        "label": "proxy",
        "measure_field": "ndvi_slope",
        "unit": "NDVI/year",
        "grain": "250-m-pixel-at-declared-site-center",
        "layer": "greenness_trend",
        "query_time": {"start": str(start_year), "end": str(end_year)},
        "connector_events": [{
            "tool": "origin.greenness.trend",
            "implementation": os.path.join(ORIGIN_CONNECTORS, "greenness.py"),
            "input_rows": len(records),
            "parameters": {"years": years, "project": project},
            "output_rows": len(rows),
        }],
        "note": (
            "annual-mean MODIS NDVI trend at the declared centre pixel; a recovery proxy, not "
            "whole-property coverage or causal attribution to restoration"
        ),
    }
