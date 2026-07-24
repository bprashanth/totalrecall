#!/usr/bin/env python3
"""Serve immutable idli-result/1 objects from a pinned visual site index.

This service is benchmark-side. It never interprets free-form questions and it does not expose
the site database to a browser. A dialogue layer resolves a request to one registered capability
and typed arguments; this service validates that binding, runs a site-agnostic query, stores its
result and data payloads immutably, and returns the result envelope.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import http.server
import json
import os
import pathlib
import re
import sqlite3
import sys
import urllib.parse
from typing import Any


MAX_REQUEST_BYTES = 64 * 1024
SAFE_HANDLE = re.compile(r"^[A-Za-z0-9_.-]{1,240}$")


def _stable_json(value: Any) -> str:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str
    )


def _digest(value: Any) -> str:
    raw = value if isinstance(value, bytes) else (
        value.encode() if isinstance(value, str) else _stable_json(value).encode()
    )
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _key(value: Any) -> str:
    return re.sub(
        r"[^a-z0-9]+", " ", str(value or "").replace("_", " ").casefold()
    ).strip()


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _atomic_write_once(path: pathlib.Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise RuntimeError(f"immutable result collision: {path}")
        return
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(payload)
    os.replace(temporary, path)


class ResultService:
    """Typed query facade over one pinned site pack and serving index."""

    def __init__(
        self, site_pack: pathlib.Path, index_path: pathlib.Path, state_root: pathlib.Path
    ):
        self.site_pack = site_pack.resolve()
        self.index_path = index_path.resolve()
        self.state_root = state_root.resolve()
        self.site = _load_json(self.site_pack / "site.json")
        self.capability_registry = _load_json(self.site_pack / "capabilities.json")
        self.capabilities = {
            item["capability_id"]: item
            for item in self.capability_registry.get("capabilities", [])
        }
        if not self.index_path.is_file():
            raise FileNotFoundError(self.index_path)
        if not self.capabilities:
            raise ValueError("site pack has no registered capabilities")
        digest_files = [
            self.site_pack / "site.json",
            self.site_pack / "sources.json",
            self.site_pack / "questions.json",
            self.site_pack / "capabilities.json",
        ]
        self.pack_digest = _digest(b"".join(path.read_bytes() for path in digest_files))
        self.state_root.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _source_versions(
        self, connection: sqlite3.Connection, source_ids: set[str] | None = None
    ) -> list[dict[str, Any]]:
        rows = connection.execute(
            "SELECT source_id,content_sha256 FROM sources ORDER BY source_id"
        ).fetchall()
        return [
            {
                "source_id": row["source_id"],
                "version": None,
                "digest": "sha256:" + row["content_sha256"],
            }
            for row in rows
            if source_ids is None or row["source_id"] in source_ids
        ]

    @staticmethod
    def _data_ref(
        handle: str, media_type: str, payload: Any
    ) -> dict[str, Any]:
        return {
            "kind": "result_data",
            "handle": handle,
            "media_type": media_type,
            "digest": _digest(payload),
        }

    @staticmethod
    def _limitation(
        code: str, message: str, *, severity: str = "warning",
        affects: list[str] | None = None
    ) -> dict[str, Any]:
        return {
            "code": code,
            "severity": severity,
            "message": message,
            "affects": affects or ["answer"],
            "details_ref": None,
        }

    @staticmethod
    def _action(
        action_id: str, kind: str, label: str, capability_id: str,
        arguments: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "action_id": action_id,
            "kind": kind,
            "label": label,
            "capability_id": capability_id,
            "arguments": arguments,
            "requires_confirmation": True,
        }

    def _base_result(
        self, request_id: str, capability_id: str, original: str, resolved: str,
        arguments: dict[str, Any], headline: str, evidence_classes: list[str],
        status: str, source_versions: list[dict[str, Any]],
    ) -> dict[str, Any]:
        query_material = {
            "site_id": self.site["site_id"],
            "pack_digest": self.pack_digest,
            "capability_id": capability_id,
            "arguments": arguments,
        }
        query_hash = _digest(query_material)
        result_id = "result-" + hashlib.sha256(
            _stable_json({"request_id": request_id, **query_material}).encode()
        ).hexdigest()[:24]
        descriptor = self.capabilities[capability_id]
        return {
            "schema_version": "idli-result/1",
            "result_id": result_id,
            "request_id": request_id,
            "revision": 1,
            "status": status,
            "site": {
                "site_id": self.site["site_id"],
                "label": self.site["label"],
                "pack_digest": self.pack_digest,
            },
            "question": {
                "original": original,
                "resolved": resolved,
                "bindings": arguments,
            },
            "answer": {
                "headline": headline,
                "detail": "",
                "evidence_classes": evidence_classes,
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
                    "status": (
                        "partial" if status == "partial" else
                        "blocked" if status == "blocked" else "complete"
                    ),
                }],
                "query_hash": query_hash,
            },
        }

    def _write_result(
        self, result: dict[str, Any], payloads: dict[str, tuple[str, Any]]
    ) -> dict[str, Any]:
        result_root = self.state_root / "results" / result["result_id"]
        for handle, (media_type, payload) in payloads.items():
            if not SAFE_HANDLE.fullmatch(handle):
                raise ValueError(f"unsafe data handle: {handle}")
            suffix = ".geojson" if media_type == "application/geo+json" else ".json"
            content = _stable_json(payload).encode()
            expected = next(
                (
                    layer["data_ref"]["digest"]
                    for visual in result["visuals"]
                    for layer in visual["layers"]
                    if layer["data_ref"].get("handle") == handle
                ),
                None,
            )
            if expected is None:
                expected = next(
                    (
                        drilldown["data_ref"]["digest"]
                        for visual in result["visuals"]
                        for drilldown in visual["drilldowns"]
                        if drilldown["data_ref"].get("handle") == handle
                    ),
                    None,
                )
            if expected != _digest(payload):
                raise RuntimeError(f"data-ref digest mismatch: {handle}")
            _atomic_write_once(result_root / "data" / f"{handle}{suffix}", content)
        result_content = (
            json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n"
        ).encode()
        _atomic_write_once(result_root / "result.json", result_content)
        return result

    def query(
        self, request_id: str, capability_id: str, arguments: dict[str, Any],
        original: str = ""
    ) -> dict[str, Any]:
        if not request_id or len(request_id) > 200:
            raise ValueError("request_id is required and must be at most 200 characters")
        descriptor = self.capabilities.get(capability_id)
        if not descriptor:
            raise ValueError(f"unknown capability: {capability_id}")
        if descriptor.get("availability") != "ready":
            return self._unavailable(
                request_id, capability_id, arguments, original,
                str(descriptor.get("reason") or "Capability is not ready for this pack."),
            )
        dispatch = {
            "site-orientation": self._site_orientation,
            "observed-presence-map": self._observed_presence,
            "coverage-versus-effort": self._coverage_effort,
            "metric-time-series": self._metric_time_series,
        }
        implementation = dispatch.get(capability_id)
        if not implementation:
            raise ValueError(f"ready capability has no implementation: {capability_id}")
        return implementation(request_id, arguments, original)

    def _unavailable(
        self, request_id: str, capability_id: str, arguments: dict[str, Any],
        original: str, reason: str
    ) -> dict[str, Any]:
        with self.connect() as connection:
            sources = self._source_versions(connection)
        result = self._base_result(
            request_id, capability_id, original,
            f"Run registered capability {capability_id}.", arguments,
            reason, ["missing"], "blocked", sources,
        )
        gap = self._limitation(
            "capability-not-ready", reason, severity="error",
            affects=["answer"],
        )
        result["limitations"] = [gap]
        return self._write_result(result, {})

    def _site_orientation(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if arguments:
            raise ValueError("site-orientation accepts no arguments")
        with self.connect() as connection:
            cells = [
                dict(row) for row in connection.execute(
                    """SELECT c.cell_id,c.west,c.south,c.east,c.north,c.target_role,
                              COUNT(e.event_id) AS records,
                              COUNT(DISTINCT e.entity_id) AS entities
                       FROM cells c LEFT JOIN events e ON e.cell_id=c.cell_id
                       GROUP BY c.cell_id ORDER BY records DESC"""
                )
            ]
            totals = connection.execute(
                """SELECT COUNT(*) AS records,COUNT(DISTINCT entity_id) AS entities,
                          COUNT(DISTINCT cell_id) AS cells
                   FROM events WHERE cell_id IS NOT NULL"""
            ).fetchone()
            sources = self._source_versions(connection)
        aoi = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": "target",
                "geometry": self.site["target_aoi"]["geometry"],
                "properties": {
                    "label": self.site["label"],
                    "geometry_role": self.site["target_aoi"]["geometry_role"],
                },
            }],
        }
        density = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": row["cell_id"],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [row["west"], row["south"]],
                        [row["east"], row["south"]],
                        [row["east"], row["north"]],
                        [row["west"], row["north"]],
                        [row["west"], row["south"]],
                    ]],
                },
                "properties": {
                    "role": row["target_role"],
                    "records": row["records"],
                    "entities": row["entities"],
                },
            } for row in cells],
        }
        result = self._base_result(
            request_id, "site-orientation", original or f"Tell me about {self.site['label']}.",
            "Orient to the declared AOI and indexed evidence coverage.", {},
            (
                f"{totals['records']:,} source-linked records representing "
                f"{totals['entities']:,} entities are mapped across {totals['cells']:,} cells."
            ),
            ["reported", "derived"], "complete", sources,
        )
        result["answer"]["detail"] = (
            "The boundary is shown using its declared geometry role; record density shows data "
            "coverage, not abundance or absence."
        )
        aoi_ref = self._data_ref("declared-aoi", "application/geo+json", aoi)
        density_ref = self._data_ref("event-density", "application/geo+json", density)
        result["visuals"] = [{
            "visual_id": "site-orientation",
            "visual_type": "map",
            "view": "site-orientation",
            "title": f"{self.site['label']}: area and indexed evidence",
            "priority": "primary",
            "status": "ready",
            "scope": {"aoi_ids": ["target", "context"], "time": {"start": None, "end": None}},
            "layers": [
                {
                    "layer_id": "declared-aoi", "evidence_class": "reported",
                    "geometry_type": "polygon", "data_ref": aoi_ref,
                    "legend": {"label": "Declared analysis area"},
                    "style_hint": {"palette_role": "reported"},
                },
                {
                    "layer_id": "event-density", "evidence_class": "derived",
                    "geometry_type": "cell", "data_ref": density_ref,
                    "legend": {"label": "Indexed record density"},
                    "style_hint": {"palette_role": "derived"},
                },
            ],
            "summary": {
                "headline": result["answer"]["headline"],
                "denominators": {
                    "records": totals["records"],
                    "entities": totals["entities"],
                    "cells": totals["cells"],
                    "sources": len(sources),
                },
            },
            "drilldowns": [],
            "limitations": [],
        }]
        result["actions"] = [self._action(
            "compare-coverage-effort", "run_capability",
            "Compare records with survey effort", "coverage-versus-effort", {},
        )]
        return self._write_result(
            result,
            {
                "declared-aoi": ("application/geo+json", aoi),
                "event-density": ("application/geo+json", density),
            },
        )

    def _resolve_entity(
        self, connection: sqlite3.Connection, entity: str
    ) -> sqlite3.Row | None:
        return connection.execute(
            """SELECT e.entity_id,e.canonical_name,e.display_name
               FROM entity_aliases a JOIN entities e ON e.entity_id=a.entity_id
               WHERE a.alias_key=?""",
            (_key(entity),),
        ).fetchone()

    def _observed_presence(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if set(arguments) != {"entity"} or not str(arguments.get("entity") or "").strip():
            raise ValueError("observed-presence-map requires only a non-empty entity")
        requested = str(arguments["entity"]).strip()
        with self.connect() as connection:
            entity = self._resolve_entity(connection, requested)
            if entity is None:
                sources = self._source_versions(connection)
                result = self._base_result(
                    request_id, "observed-presence-map", original,
                    "Resolve an entity alias, then map admitted observations.",
                    {"entity": requested},
                    f"No indexed entity matched “{requested}”.",
                    ["missing"], "blocked", sources,
                )
                unresolved = self._limitation(
                    "unresolved-entity",
                    "The supplied name did not resolve to a canonical entity in this pack.",
                    severity="error", affects=["answer"],
                )
                result["limitations"] = [unresolved]
                return self._write_result(result, {})
            rows = connection.execute(
                """SELECT e.event_id,e.source_id,e.source_row,e.event_date,e.latitude,
                          e.longitude,e.uncertainty_m,e.count_value,e.evidence_class,
                          COALESCE(c.target_role,'unlocated') AS target_role
                   FROM events e LEFT JOIN cells c ON c.cell_id=e.cell_id
                   WHERE e.entity_id=? AND e.latitude IS NOT NULL AND e.longitude IS NOT NULL
                   ORDER BY e.event_date,e.source_id,e.source_row""",
                (entity["entity_id"],),
            ).fetchall()
            source_ids = {row["source_id"] for row in rows}
            sources = self._source_versions(connection, source_ids)
        target_count = sum(row["target_role"] == "target" for row in rows)
        context_count = len(rows) - target_count
        points = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": row["event_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    "source_id": row["source_id"],
                    "source_row": row["source_row"],
                    "event_date": row["event_date"],
                    "coordinate_uncertainty_m": row["uncertainty_m"],
                    "count": row["count_value"],
                    "scope_role": row["target_role"],
                },
            } for row in rows],
        }
        source_rows = [{
            key: row[key] for key in (
                "event_id", "source_id", "source_row", "event_date", "latitude",
                "longitude", "uncertainty_m", "count_value", "target_role",
            )
        } for row in rows]
        if target_count:
            status = "complete"
            headline = (
                f"{len(rows):,} source-linked {entity['display_name']} records are mapped; "
                f"{target_count:,} fall in the target cells."
            )
            view = "observed-points"
            limitations: list[dict[str, Any]] = []
        elif rows:
            status = "partial"
            headline = (
                f"No {entity['display_name']} records fall in the target cells; "
                f"{context_count:,} records are available in the surrounding context."
            )
            view = "surrounding-data"
            limitations = [self._limitation(
                "no-target-records",
                "No admitted records fall inside the target cells; this is not evidence of absence.",
                affects=["observed-presence", "answer"],
            )]
        else:
            status = "partial"
            headline = f"No georeferenced {entity['display_name']} records are indexed."
            view = "observed-points"
            limitations = [self._limitation(
                "no-georeferenced-records",
                "The entity resolved, but no admitted georeferenced records can be mapped.",
                affects=["observed-presence", "answer"],
            )]
        result = self._base_result(
            request_id, "observed-presence-map", original,
            (
                f"Map admitted records for {entity['canonical_name']} and distinguish target "
                "from surrounding context."
            ),
            {
                "entity": entity["canonical_name"],
                "entity_id": entity["entity_id"],
                "aoi_ids": ["target", "context"],
            },
            headline, ["observed"] + (["missing"] if limitations else []),
            status, sources,
        )
        result["answer"]["detail"] = (
            "Points show source coverage. They do not establish abundance, absence, habitat "
            "preference or a transferable distribution."
        )
        result["limitations"] = limitations
        points_ref = self._data_ref("observations", "application/geo+json", points)
        rows_ref = self._data_ref("source-rows", "application/json", source_rows)
        result["visuals"] = [{
            "visual_id": "observed-presence",
            "visual_type": "map",
            "view": view,
            "title": f"Where {entity['display_name']} records are available",
            "priority": "primary",
            "status": "partial" if limitations else "ready",
            "scope": {"aoi_ids": ["target", "context"], "time": {"start": None, "end": None}},
            "layers": [{
                "layer_id": "observations",
                "evidence_class": "observed",
                "geometry_type": "point",
                "data_ref": points_ref,
                "legend": {"label": "Observed records"},
                "style_hint": {"palette_role": "observed"},
            }],
            "summary": {
                "headline": headline,
                "denominators": {
                    "records": len(rows),
                    "target_records": target_count,
                    "context_records": context_count,
                    "sources": len(sources),
                },
            },
            "drilldowns": [{
                "action_id": "inspect-source-rows",
                "label": "Inspect source rows",
                "data_ref": rows_ref,
            }],
            "limitations": limitations,
        }]
        if context_count:
            result["actions"].append(self._action(
                "test-transfer", "run_capability", "Test transfer to the target",
                "gated-transfer", {
                    "entity": entity["canonical_name"],
                    "donor_scope": "context",
                    "target_scope": "target",
                },
            ))
        result["actions"].append(self._action(
            "compare-effort", "run_capability", "Compare with documented effort",
            "coverage-versus-effort", {},
        ))
        payloads = {
            "observations": ("application/geo+json", points),
            "source-rows": ("application/json", source_rows),
        }
        return self._write_result(result, payloads)

    def _coverage_effort(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if arguments:
            raise ValueError("coverage-versus-effort accepts no arguments")
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT c.cell_id,c.west,c.south,c.east,c.north,c.target_role,
                          COUNT(e.event_id) AS records,
                          COALESCE((SELECT SUM(x.effort_value) FROM effort x
                                    WHERE x.cell_id=c.cell_id),0) AS effort,
                          (SELECT MIN(x.effort_unit) FROM effort x
                           WHERE x.cell_id=c.cell_id) AS effort_unit
                   FROM cells c LEFT JOIN events e ON e.cell_id=c.cell_id
                   GROUP BY c.cell_id ORDER BY records DESC"""
            ).fetchall()
            event_sources = {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT source_id FROM events"
                )
            }
            effort_sources = {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT source_id FROM effort"
                )
            }
            sources = self._source_versions(connection, event_sources | effort_sources)
        coverage_features = []
        effort_features = []
        for row in rows:
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [row["west"], row["south"]], [row["east"], row["south"]],
                    [row["east"], row["north"]], [row["west"], row["north"]],
                    [row["west"], row["south"]],
                ]],
            }
            coverage_features.append({
                "type": "Feature", "id": row["cell_id"], "geometry": geometry,
                "properties": {
                    "scope_role": row["target_role"], "records": row["records"],
                },
            })
            if row["effort"]:
                effort_features.append({
                    "type": "Feature", "id": row["cell_id"], "geometry": geometry,
                    "properties": {
                        "scope_role": row["target_role"], "effort": row["effort"],
                        "unit": row["effort_unit"],
                    },
                })
        coverage = {"type": "FeatureCollection", "features": coverage_features}
        effort = {"type": "FeatureCollection", "features": effort_features}
        record_cells = sum(bool(row["records"]) for row in rows)
        effort_cells = sum(bool(row["effort"]) for row in rows)
        headline = (
            f"Records occur in {record_cells:,} cells; explicit effort is documented in "
            f"{effort_cells:,} cells."
        )
        result = self._base_result(
            request_id, "coverage-versus-effort", original,
            "Compare mapped record coverage with explicit survey-effort denominators.",
            {}, headline, ["observed", "derived"], "complete", sources,
        )
        result["answer"]["detail"] = (
            "Cells without explicit effort may show source coverage, but they cannot support "
            "absence or effort-normalised rate claims."
        )
        coverage_ref = self._data_ref("coverage", "application/geo+json", coverage)
        effort_ref = self._data_ref("effort", "application/geo+json", effort)
        result["visuals"] = [{
            "visual_id": "coverage-versus-effort",
            "visual_type": "map",
            "view": "coverage-and-effort",
            "title": "Record coverage and documented effort",
            "priority": "primary",
            "status": "ready",
            "scope": {"aoi_ids": ["target", "context"], "time": {"start": None, "end": None}},
            "layers": [
                {
                    "layer_id": "coverage", "evidence_class": "derived",
                    "geometry_type": "cell", "data_ref": coverage_ref,
                    "legend": {"label": "Record coverage"},
                    "style_hint": {"palette_role": "derived"},
                },
                {
                    "layer_id": "effort", "evidence_class": "observed",
                    "geometry_type": "cell", "data_ref": effort_ref,
                    "legend": {"label": "Documented effort"},
                    "style_hint": {"palette_role": "observed"},
                },
            ],
            "summary": {
                "headline": headline,
                "denominators": {
                    "record_cells": record_cells,
                    "effort_cells": effort_cells,
                    "indexed_cells": len(rows),
                },
            },
            "drilldowns": [],
            "limitations": [],
        }]
        return self._write_result(
            result,
            {
                "coverage": ("application/geo+json", coverage),
                "effort": ("application/geo+json", effort),
            },
        )

    def _metric_time_series(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if set(arguments) != {"metric"} or not str(arguments.get("metric") or "").strip():
            raise ValueError("metric-time-series requires only a non-empty metric")
        metric = str(arguments["metric"]).strip()
        with self.connect() as connection:
            matches = connection.execute(
                "SELECT DISTINCT metric FROM measurements WHERE lower(metric)=lower(?)",
                (metric,),
            ).fetchall()
            if not matches:
                available = [
                    row[0] for row in connection.execute(
                        "SELECT DISTINCT metric FROM measurements ORDER BY metric"
                    )
                ]
                sources = self._source_versions(connection)
                result = self._base_result(
                    request_id, "metric-time-series", original,
                    "Resolve a metric and plot unit-compatible measurements with coverage.",
                    {"metric": metric}, f"No indexed metric matched “{metric}”.",
                    ["missing"], "blocked", sources,
                )
                missing = self._limitation(
                    "unresolved-metric",
                    "The requested metric is not in the measurement registry.",
                    severity="error", affects=["answer"],
                )
                result["limitations"] = [missing]
                result["actions"] = [self._action(
                    "choose-metric", "filter", "Choose an indexed metric",
                    "metric-time-series", {"available_metrics": available[:30]},
                )]
                return self._write_result(result, {})
            canonical = matches[0][0]
            rows = [
                dict(row) for row in connection.execute(
                    """SELECT year,month,source_id,value,unit
                       FROM measurement_time WHERE metric=?
                       ORDER BY year,month,source_id""",
                    (canonical,),
                )
            ]
            source_ids = {row["source_id"] for row in rows}
            sources = self._source_versions(connection, source_ids)
        units = sorted({row["unit"] for row in rows})
        limitations = []
        status = "complete"
        if len(units) > 1:
            status = "partial"
            limitations.append(self._limitation(
                "mixed-metric-units",
                "The selected metric has multiple units; series must not be combined silently.",
                affects=["metric-time-series", "answer"],
            ))
        coverage = [{
            "year": row["year"], "month": row["month"], "source_id": row["source_id"],
            "present": row["value"] is not None,
        } for row in rows]
        headline = (
            f"{len(rows):,} monthly {canonical} values are available from "
            f"{len(source_ids):,} source version{'s' if len(source_ids) != 1 else ''}."
        )
        result = self._base_result(
            request_id, "metric-time-series", original,
            f"Plot the indexed {canonical} series with units and a coverage strip.",
            {"metric": canonical}, headline, ["observed", "derived"], status, sources,
        )
        result["answer"]["detail"] = (
            "The series reports indexed measurements and coverage; no trend test is implied."
        )
        result["limitations"] = limitations
        series_ref = self._data_ref("metric-series", "application/json", rows)
        coverage_ref = self._data_ref("coverage-strip", "application/json", coverage)
        result["visuals"] = [{
            "visual_id": "metric-time-series",
            "visual_type": "chart",
            "view": "metric-time-series",
            "title": f"{canonical.replace('_', ' ').title()} through time",
            "priority": "primary",
            "status": "partial" if limitations else "ready",
            "scope": {
                "aoi_ids": ["target"],
                "time": {
                    "start": (
                        f"{rows[0]['year']:04d}-{rows[0]['month']:02d}" if rows else None
                    ),
                    "end": (
                        f"{rows[-1]['year']:04d}-{rows[-1]['month']:02d}" if rows else None
                    ),
                },
            },
            "layers": [
                {
                    "layer_id": "metric-series", "evidence_class": "observed",
                    "geometry_type": "series", "data_ref": series_ref,
                    "legend": {"label": f"{canonical} ({', '.join(units)})"},
                    "style_hint": {"palette_role": "observed"},
                },
                {
                    "layer_id": "coverage-strip", "evidence_class": "derived",
                    "geometry_type": "series", "data_ref": coverage_ref,
                    "legend": {"label": "Measurement coverage"},
                    "style_hint": {"palette_role": "derived"},
                },
            ],
            "summary": {
                "headline": headline,
                "denominators": {
                    "months": len(rows),
                    "sources": len(source_ids),
                    "units": ", ".join(units),
                },
            },
            "drilldowns": [{
                "action_id": "inspect-measurements",
                "label": "Inspect measurements",
                "data_ref": series_ref,
            }],
            "limitations": limitations,
        }]
        return self._write_result(
            result,
            {
                "metric-series": ("application/json", rows),
                "coverage-strip": ("application/json", coverage),
            },
        )

    def load_result(self, result_id: str) -> dict[str, Any] | None:
        if not SAFE_HANDLE.fullmatch(result_id):
            return None
        path = self.state_root / "results" / result_id / "result.json"
        return _load_json(path) if path.is_file() else None

    def load_data(self, result_id: str, handle: str) -> tuple[str, bytes] | None:
        if not SAFE_HANDLE.fullmatch(result_id) or not SAFE_HANDLE.fullmatch(handle):
            return None
        root = self.state_root / "results" / result_id / "data"
        for suffix, media_type in (
            (".geojson", "application/geo+json"),
            (".json", "application/json"),
        ):
            path = root / f"{handle}{suffix}"
            if path.is_file():
                return media_type, path.read_bytes()
        return None


class ResultHandler(http.server.BaseHTTPRequestHandler):
    server_version = "IdliResultService/0.1"
    service: ResultService
    api_token: str

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _authorized(self) -> bool:
        if self.api_token:
            return self.headers.get("Authorization") == f"Bearer {self.api_token}"
        return self.client_address[0] in {"127.0.0.1", "::1"}

    def _send(self, status: int, payload: bytes, media_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "private, immutable" if status == 200 else "no-store")
        self.end_headers()
        self.wfile.write(payload)

    def _send_json(self, status: int, value: Any) -> None:
        self._send(
            status,
            (json.dumps(value, ensure_ascii=False, default=str) + "\n").encode(),
            "application/json",
        )

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(200, {
                "status": "ok",
                "site_id": self.service.site["site_id"],
                "pack_digest": self.service.pack_digest,
                "capabilities": len(self.service.capabilities),
            })
            return
        if not self._authorized():
            self._send_json(401, {"error": "unauthorized"})
            return
        parts = [urllib.parse.unquote(part) for part in parsed.path.strip("/").split("/")]
        if len(parts) == 3 and parts[:2] == ["v1", "results"]:
            result = self.service.load_result(parts[2])
            self._send_json(200, result) if result else self._send_json(404, {"error": "not found"})
            return
        if len(parts) == 5 and parts[:2] == ["v1", "results"] and parts[3] == "data":
            data = self.service.load_data(parts[2], parts[4])
            self._send(200, data[1], data[0]) if data else self._send_json(404, {"error": "not found"})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/v1/results/query":
            self._send_json(404, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(401, {"error": "unauthorized"})
            return
        try:
            length = int(self.headers.get("Content-Length") or "0")
            if length <= 0 or length > MAX_REQUEST_BYTES:
                raise ValueError("invalid request size")
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError("JSON object required")
            result = self.service.query(
                request_id=str(body.get("request_id") or ""),
                capability_id=str(body.get("capability_id") or ""),
                arguments=(
                    body["arguments"] if isinstance(body.get("arguments"), dict) else {}
                ),
                original=str(body.get("question") or ""),
            )
            self._send_json(200, result)
        except ValueError as exc:
            self._send_json(400, {"error": str(exc)})
        except Exception as exc:
            self._send_json(500, {"error": f"{type(exc).__name__}: {exc}"})


def make_server(
    service: ResultService, host: str, port: int, api_token: str = ""
) -> http.server.ThreadingHTTPServer:
    handler = type(
        "PinnedResultHandler",
        (ResultHandler,),
        {"service": service, "api_token": api_token},
    )
    return http.server.ThreadingHTTPServer((host, port), handler)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7120)
    parser.add_argument("--api-token-file", type=pathlib.Path)
    parser.add_argument("--query", help="One-shot JSON query instead of serving HTTP")
    args = parser.parse_args(argv)
    service = ResultService(args.site_pack, args.index, args.state)
    if args.query:
        body = json.loads(args.query)
        print(json.dumps(service.query(
            request_id=str(body.get("request_id") or ""),
            capability_id=str(body.get("capability_id") or ""),
            arguments=body.get("arguments") if isinstance(body.get("arguments"), dict) else {},
            original=str(body.get("question") or ""),
        ), indent=2, ensure_ascii=False))
        return 0
    token = ""
    if args.api_token_file:
        token = args.api_token_file.read_text(encoding="utf-8").strip()
        if not token:
            raise ValueError("api token file is empty")
    server = make_server(service, args.host, args.port, token)
    print(json.dumps({
        "status": "listening",
        "site_id": service.site["site_id"],
        "pack_digest": service.pack_digest,
        "host": args.host,
        "port": args.port,
    }), flush=True)
    with contextlib.suppress(KeyboardInterrupt):
        server.serve_forever()
    server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
