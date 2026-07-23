"""Thin typed-contract adapters over the locked origin connector snapshot.

The production algorithms live unchanged under ``integration/origin/connectors``. Adapters may
validate inputs and attach typed metadata, but must not reproduce connector computations.
"""
import csv
import concurrent.futures
import hashlib
import importlib
import json
import os
import re
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


def _connector_in_runtime(module, function, args=None, kwargs=None):
    """Invoke one locked Origin connector function in the complete Hermes runtime."""
    container = os.environ.get("HERMES_CONTAINER", "hermes-live")
    script = r"""
import importlib, json, sys
sys.path.insert(0, "/opt/data/connectors")
payload = json.load(sys.stdin)
connector = importlib.import_module(payload["module"])
result = getattr(connector, payload["function"])(*payload.get("args", []),
                                                  **payload.get("kwargs", {}))
json.dump(result, sys.stdout)
"""
    payload = json.dumps({
        "module": module, "function": function,
        "args": list(args or []), "kwargs": dict(kwargs or {}),
    })
    completed = subprocess.run(
        ["docker", "exec", "-i", container, "/opt/hermes/.venv/bin/python3", "-c", script],
        input=payload, text=True, capture_output=True, timeout=420,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-800:]
        raise RuntimeError(f"origin {module}.{function} runtime failed: {detail}")
    return json.loads(completed.stdout)


def _connector_call(module, function, *args, **kwargs):
    """Use local dependencies when present, otherwise cross the declared runtime boundary."""
    connector = _module(module)
    try:
        return getattr(connector, function)(*args, **kwargs)
    except ModuleNotFoundError as exc:
        if exc.name != "ee":
            raise
        return _connector_in_runtime(module, function, args, kwargs)


def _predict_in_runtime(action, rows, target, year):
    """Run the locked predictor in its dependency-complete runtime.

    The chat bridge normally runs inside Idlisseus's deliberately small virtualenv.  Importing
    ``predict.py`` there succeeds, but its first Earth Engine call fails because that virtualenv
    does not contain ``ee``.  The locked Origin runtime does contain Earth Engine and its
    credentials, so pass the typed inputs over stdin rather than making the public skill depend on
    whichever Python happened to launch the bridge.
    """
    container = os.environ.get("HERMES_CONTAINER", "hermes-live")
    script = r"""
import json, sys
sys.path.insert(0, "/opt/data/connectors")
import predict
payload = json.load(sys.stdin)
rows = payload["rows"]
bbox = payload["bbox"]
year = int(payload["year"])
action = payload["action"]
if action == "gate":
    result = predict.gate(rows, bbox, year=year)
elif action == "presence":
    result = predict.presence(rows, bbox, year=year)
elif action == "sdm":
    result = predict.sdm_climate(rows, bbox, year=year)
else:
    raise ValueError("unsupported predictor action: " + action)
json.dump(result, sys.stdout)
"""
    s, n, w, e = target["bbox"]
    payload = json.dumps({
        "action": action, "rows": rows, "bbox": [w, s, e, n], "year": int(year),
    })
    completed = subprocess.run(
        ["docker", "exec", "-i", container, "/opt/hermes/.venv/bin/python3", "-c", script],
        input=payload, text=True, capture_output=True, timeout=420,
    )
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()[-800:]
        raise RuntimeError(f"origin predictor runtime failed: {detail}")
    return json.loads(completed.stdout)


def _predict_call(action, rows, target, year):
    """Prefer the current interpreter, falling back only for a missing Earth Engine module."""
    predict = _module("predict")
    s, n, w, e = target["bbox"]
    bbox = [w, s, e, n]
    try:
        if action == "gate":
            return predict.gate(rows, bbox, year=int(year))
        if action == "presence":
            return predict.presence(rows, bbox, year=int(year))
        if action == "sdm":
            return predict.sdm_climate(rows, bbox, year=int(year))
        raise ValueError(f"unsupported predictor action: {action}")
    except ModuleNotFoundError as exc:
        if exc.name != "ee":
            raise
        return _predict_in_runtime(action, rows, target, year)


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
    # A typed occurrence leaf needs coordinate records. The imported `paper_data.search` path can
    # invoke an interactive LLM column matcher for up to several minutes on a cache miss, which is
    # neither a bounded point query nor an appropriate hidden side effect of RELATE. Keep the exact
    # origin merger, but admit its GBIF+iNaturalist point sources here; semantic paper discovery and
    # paper-dataset extraction remain explicit connector operations with their own provenance.
    point_sources = ("gbif", "inat")
    result = points.get(
        resolution["canonical"], bbox=bbox, sources=point_sources,
        limit=min(int(limit), 500), resolve_name=False
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
        "source": "origin points.py → GBIF + iNaturalist",
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
                "sources": list(point_sources), "limit": min(int(limit), 500),
            },
            "output_rows": len(rows),
            "cached": result.get("cached", False),
        }],
        "note": (
            f"{len(rows)} coordinate-deduplicated occurrence points from the exact origin resolver "
            "using its bounded GBIF+iNaturalist sources; paper discovery/extraction is separate; "
            "the origin common CSV omits record URLs and licenses, an import incompatibility"
        ),
    }


def predict_gate(rows, target, year=2023):
    """Run the locked origin environmental gate and return its native audit fields."""
    _verify(["_base.py", "predict.py"])
    return _predict_call("gate", rows, target, year)


def predict_presence(rows, target, year=2023):
    """Run the locked origin AlphaEarth presence model after a separately audited gate."""
    _verify(["_base.py", "predict.py"])
    return _predict_call("presence", rows, target, year)


def predict_sdm(rows, target, year=2023):
    """Run the locked origin WorldClim SDM branch after a separately audited gate."""
    _verify(["_base.py", "predict.py"])
    return _predict_call("sdm", rows, target, year)


def semantic_discovery(query, k=5, points_only=True):
    """Execute the exact origin semantic-card connector in its production dependency context."""
    _verify(["discovery.py"])
    script = os.path.join(ORIGIN_CONNECTORS, "discovery.py")
    command = [sys.executable, script, "search", "--query", query, "--k", str(int(k))]
    if points_only:
        command.append("--points-only")
    runtime_env = os.environ.copy()
    host_corpus = runtime_env.get("CORPUS_CARDS") or runtime_env.get("CODEX_NATIVE_CORPUS")
    if host_corpus and os.path.isfile(host_corpus):
        runtime_env["CORPUS_CARDS"] = host_corpus
    host_cache = runtime_env.get("CODEX_NATIVE_DISCOVERY_CACHE")
    if host_corpus:
        runtime_env["DISCOVERY_CACHE"] = (
            host_cache or os.path.join(HERE, "cache", "discovery"))
    completed = subprocess.run(
        command, text=True, capture_output=True, timeout=180, env=runtime_env)
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


def evidence_discovery(query, k=8, include_local=True, include_dryad=True):
    """Discover query-bound ecology evidence across the locked admitted connectors.

    OpenAlex supplies work and dataset metadata, Zenodo/Dryad supply archived datasets and the
    existing semantic connector supplies already-ingested content cards. Results remain discovery
    leads: this adapter does not turn paper prose into an observation or silently extract points.
    """
    query = " ".join(str(query or "").split()).strip()
    if not query:
        raise ValueError("evidence discovery requires a non-empty query")
    limit = max(1, min(int(k), 25))

    jobs = {
        "openalex_articles": lambda: _connector_call(
            "litscout", "works", query, "article", False, limit),
        "openalex_datasets": lambda: _connector_call(
            "litscout", "works", query, "dataset", False, limit),
        "zenodo_datasets": lambda: _connector_call(
            "paper_data", "find", query, "", limit),
    }
    if include_local:
        jobs["local_semantic"] = lambda: semantic_discovery(query, k=limit, points_only=False)
    if include_dryad:
        jobs["dryad_datasets"] = lambda: _connector_call(
            "paper_data", "dryad_find", query, limit)

    raw, errors = {}, {}
    dryad_attempts = 1 if include_dryad else 0
    dryad_recovered = False
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {name: pool.submit(call) for name, call in jobs.items()}
        for name, future in futures.items():
            try:
                raw[name] = future.result()
            except Exception as exc:
                errors[name] = f"{type(exc).__name__}: {str(exc)[:240]}"

    # Dryad's search result is followed by one file-list request per dataset. A transient failure
    # in any of those requests is intentionally swallowed by the locked connector, which can turn
    # an exact DOI lookup into an unexplained empty list. Retry that *same admitted query* once
    # when the user supplied a DOI; do not broaden it or substitute model memory.
    doi_match = re.search(r"10\.\d{4,9}/[^\s\]\[(){}<>]+", query, flags=re.IGNORECASE)
    if include_dryad and doi_match:
        requested_doi = doi_match.group(0).rstrip(".,;:").lower()
        returned_dois = {
            str(row.get("doi") or "").lower().removeprefix("doi:")
            for row in (raw.get("dryad_datasets") or [])
        }
        if requested_doi not in returned_dois:
            dryad_attempts += 1
            try:
                retried = _connector_call("paper_data", "dryad_find", requested_doi, limit)
                if retried:
                    raw["dryad_datasets"] = retried
                    errors.pop("dryad_datasets", None)
                    dryad_recovered = True
            except Exception as exc:
                errors["dryad_datasets_retry"] = (
                    f"{type(exc).__name__}: {str(exc)[:240]}")

    rows = []
    for item in (raw.get("openalex_articles") or {}).get("results", []):
        rows.append({**item, "source_connector": "OpenAlex via litscout",
                     "evidence_kind": "article_metadata", "query": query})
    for item in (raw.get("openalex_datasets") or {}).get("results", []):
        rows.append({**item, "source_connector": "OpenAlex via litscout",
                     "evidence_kind": "dataset_metadata", "query": query})
    for item in raw.get("zenodo_datasets") or []:
        rows.append({**item, "source_connector": "Zenodo via paper_data",
                     "evidence_kind": "archived_dataset", "query": query})
    for item in raw.get("dryad_datasets") or []:
        rows.append({**item, "source_connector": "Dryad via paper_data",
                     "evidence_kind": "archived_dataset", "query": query})
    for item in (raw.get("local_semantic") or {}).get("results", []):
        rows.append({**item, "source_connector": "local semantic corpus via discovery",
                     "evidence_kind": "ingested_content_card", "query": query})

    events = [{
        "tool": "origin.litscout.works",
        "implementation": os.path.join(ORIGIN_CONNECTORS, "litscout.py"),
        "parameters": {"query": query, "kind": kind, "limit": limit},
        "output_rows": len((raw.get(key) or {}).get("results", [])),
    } for key, kind in (("openalex_articles", "article"),
                        ("openalex_datasets", "dataset"))]
    events.extend([{
        "tool": "origin.paper_data.find",
        "implementation": os.path.join(ORIGIN_CONNECTORS, "paper_data.py"),
        "parameters": {"query": query, "repository": repository, "limit": limit},
        "output_rows": len(raw.get(key) or []),
    } for key, repository in (("zenodo_datasets", "Zenodo"),
                               ("dryad_datasets", "Dryad"))])
    for event in events:
        if event.get("parameters", {}).get("repository") == "Dryad":
            event["attempts"] = dryad_attempts
            event["recovered_after_exact_doi_retry"] = dryad_recovered
    events.extend((raw.get("local_semantic") or {}).get("connector_events") or [])
    return {
        "query": query, "rows": rows, "errors": errors, "connector_events": events,
        "note": ("Query-bound discovery leads from admitted metadata, repository and local-corpus "
                 "connectors. A lead is not a biological observation or causal finding; inspect "
                 "and extract its dataset before using it as model input."),
    }


def inspect_evidence_dataset(dataset):
    """Inspect files, headers and codebook for one discovered Zenodo/Dryad dataset."""
    _verify(["_base.py", "paper_data.py"])
    material = _connector_call("paper_data", "inspect", dataset, 4)
    return {
        **material,
        "connector_events": [{
            "tool": "origin.paper_data.inspect",
            "implementation": os.path.join(ORIGIN_CONNECTORS, "paper_data.py"),
            "parameters": {"doi": dataset.get("doi"), "title": dataset.get("title")},
            "output_rows": len(material.get("files") or []),
        }],
        "note": ("Headers, sample rows and codebook text are reported source material. Any field "
                 "protocol derived from them must label adaptations and must not invent methods."),
    }


def invasive_surface(species, year=2024, n=20):
    """Run the locked generic invasive-plant surface and return its audited grid in memory."""
    _verify(["_base.py", "invasive.py", "occurrence.py", "s2.py", "embedding.py"])
    out = _connector_call("invasive", "build", species, int(year), max(10, min(int(n), 32)))
    return {
        **out,
        "connector_events": [{
            "tool": "origin.invasive.build",
            "implementation": os.path.join(ORIGIN_CONNECTORS, "invasive.py"),
            "parameters": {"species": species, "year": int(year), "grid_n": int(out["grid_n"])},
            "output_rows": len(out.get("grid") or []),
        }],
    }


def fire_exposure(records, region, start_year=2020, end_year=2025, radius_km=5):
    """Run exact origin AOI-points and point-exposure functions; keep their grains separate."""
    if end_year < start_year:
        start_year, end_year = end_year, start_year
    years = f"{start_year}-{end_year}"
    rows = _connector_call(
        "fire", "exposure",
        records,
        radius_km=radius_km,
        years=years,
        project=os.environ.get("EE_PROJECT", "plantwars"),
    )
    s, n, w, e = region["bbox"]
    site_points = _connector_call(
        "fire", "points",
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
    project = os.environ.get("EE_PROJECT", "plantwars")
    classified = _connector_call("landcover", "classify", records, project=project)
    s, n, w, e = region["bbox"]
    bbox = [w, s, e, n]
    area = _connector_call("landcover", "area_by_class", bbox, project=project, scale=scale)
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
    rows = _connector_call("greenness", "trend", records, years=years, project=project)
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
