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
import statistics
import sys
import urllib.parse
from typing import Any

try:
    from dss.visual_index.analogue_transfer import score_analogues
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/result_service.py
    from analogue_transfer import score_analogues


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
        self.source_registry = _load_json(self.site_pack / "sources.json")
        self.capability_registry = _load_json(self.site_pack / "capabilities.json")
        self.capabilities = {
            item["capability_id"]: item
            for item in self.capability_registry.get("capabilities", [])
        }
        if not self.index_path.is_file():
            raise FileNotFoundError(self.index_path)
        if not self.capabilities:
            raise ValueError("site pack has no registered capabilities")
        self.synthetic = any(
            "synthetic" in source.get("capabilities", [])
            for source in self.source_registry.get("sources", [])
        )
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
            "SELECT source_id,content_sha256,capabilities_json FROM sources ORDER BY source_id"
        ).fetchall()
        return [
            {
                "source_id": row["source_id"],
                "version": None,
                "digest": "sha256:" + row["content_sha256"],
                "synthetic": "synthetic" in json.loads(row["capabilities_json"]),
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
        site = {
            "site_id": self.site["site_id"],
            "label": self.site["label"],
            "pack_digest": self.pack_digest,
        }
        if self.synthetic:
            site["synthetic"] = True
        result = {
            "schema_version": "idli-result/1",
            "result_id": result_id,
            "request_id": request_id,
            "revision": 1,
            "status": status,
            "site": site,
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
        if self.synthetic:
            result["limitations"].append(self._limitation(
                "synthetic-data",
                "This result uses synthetic test data and is not evidence about a real place.",
                severity="info", affects=["answer"],
            ))
        return result

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
            "entity-record-map": self._entity_records,
            "group-record-map": self._group_records,
            "interaction-map": self._interaction_map,
            "stratified-survey-summary": self._stratified_survey_summary,
            "cell-feature-map": self._cell_feature_map,
            "gated-transfer": self._gated_transfer,
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
        result["limitations"].append(gap)
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
            "coverage, not a rate, outcome or non-occurrence."
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

    def _entity_records(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if set(arguments) != {"entity"} or not str(arguments.get("entity") or "").strip():
            raise ValueError("entity-record-map requires only a non-empty entity")
        requested = str(arguments["entity"]).strip()
        with self.connect() as connection:
            entity = self._resolve_entity(connection, requested)
            if entity is None:
                sources = self._source_versions(connection)
                result = self._base_result(
                    request_id, "entity-record-map", original,
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
                result["limitations"].append(unresolved)
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
                affects=["entity-records", "answer"],
            )]
        else:
            status = "partial"
            headline = f"No georeferenced {entity['display_name']} records are indexed."
            view = "observed-points"
            limitations = [self._limitation(
                "no-georeferenced-records",
                "The entity resolved, but no admitted georeferenced records can be mapped.",
                affects=["entity-records", "answer"],
            )]
        result = self._base_result(
            request_id, "entity-record-map", original,
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
            "Points show source coverage. They do not by themselves establish rates, "
            "non-occurrence, causal conditions or whether a model transfers to another scope."
        )
        result["limitations"].extend(limitations)
        points_ref = self._data_ref("observations", "application/geo+json", points)
        rows_ref = self._data_ref("source-rows", "application/json", source_rows)
        result["visuals"] = [{
            "visual_id": "entity-records",
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

    def _group_records(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if set(arguments) != {"rank", "group"}:
            raise ValueError("group-record-map requires only rank and group")
        rank = str(arguments.get("rank") or "").strip().casefold()
        group = str(arguments.get("group") or "").strip()
        if not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", rank) or not group:
            raise ValueError("rank must be a safe non-empty hierarchy level and group is required")
        path = f"$.{rank}"
        with self.connect() as connection:
            rows = connection.execute(
                """SELECT v.event_id,v.source_id,v.source_row,v.event_date,v.latitude,
                          v.longitude,v.uncertainty_m,v.count_value,v.evidence_class,
                          e.entity_id,e.canonical_name,e.display_name,
                          COALESCE(c.target_role,'unlocated') AS target_role
                   FROM events v JOIN entities e ON e.entity_id=v.entity_id
                   LEFT JOIN cells c ON c.cell_id=v.cell_id
                   WHERE lower(json_extract(e.hierarchy_json,?))=lower(?)
                     AND v.latitude IS NOT NULL AND v.longitude IS NOT NULL
                   ORDER BY v.event_date,v.source_id,v.source_row""",
                (path, group),
            ).fetchall()
            if not rows:
                available = [
                    row[0] for row in connection.execute(
                        """SELECT DISTINCT json_extract(hierarchy_json,?)
                           FROM entities
                           WHERE json_extract(hierarchy_json,?) IS NOT NULL
                           ORDER BY 1 LIMIT 100""",
                        (path, path),
                    )
                ]
                sources = self._source_versions(connection)
                result = self._base_result(
                    request_id, "group-record-map", original,
                    "Resolve a hierarchy value, then map source-linked records for its members.",
                    {"rank": rank, "group": group},
                    f"No indexed {rank} matched “{group}”.",
                    ["missing"], "blocked", sources,
                )
                result["limitations"].append(self._limitation(
                    "unresolved-group",
                    "The requested hierarchy value is not present in this pack.",
                    severity="error", affects=["answer"],
                ))
                result["actions"] = [self._action(
                    "choose-group", "filter", f"Choose an indexed {rank}",
                    "group-record-map", {"rank": rank, "available_groups": available},
                )]
                return self._write_result(result, {})
            source_ids = {row["source_id"] for row in rows}
            sources = self._source_versions(connection, source_ids)
        target_count = sum(row["target_role"] == "target" for row in rows)
        context_count = len(rows) - target_count
        entities = {}
        for row in rows:
            item = entities.setdefault(
                row["entity_id"],
                {
                    "entity_id": row["entity_id"],
                    "canonical_name": row["canonical_name"],
                    "display_name": row["display_name"],
                    "records": 0,
                    "target_records": 0,
                },
            )
            item["records"] += 1
            item["target_records"] += int(row["target_role"] == "target")
        entity_summary = sorted(
            entities.values(), key=lambda item: (-item["records"], item["display_name"])
        )
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
                    "entity_id": row["entity_id"],
                    "entity": row["display_name"],
                    "canonical_name": row["canonical_name"],
                    "source_id": row["source_id"],
                    "source_row": row["source_row"],
                    "event_date": row["event_date"],
                    "coordinate_uncertainty_m": row["uncertainty_m"],
                    "count": row["count_value"],
                    "scope_role": row["target_role"],
                },
            } for row in rows],
        }
        limitations = [self._limitation(
            "mixed-observation-processes",
            "These records may come from different protocols and effort; compare coverage before comparing counts.",
            affects=["group-records", "answer"],
        )]
        if not target_count:
            limitations.append(self._limitation(
                "no-target-records",
                "No admitted group records fall inside target cells; this is not evidence of absence.",
                affects=["group-records", "answer"],
            ))
        headline = (
            f"{len(rows):,} source-linked records for {len(entities):,} members of "
            f"{group} are mapped; {target_count:,} fall in target cells."
        )
        result = self._base_result(
            request_id, "group-record-map", original,
            f"Map records whose canonical hierarchy has {rank}={group}.",
            {"rank": rank, "group": group, "aoi_ids": ["target", "context"]},
            headline, ["observed", "missing"], "partial", sources,
        )
        result["answer"]["detail"] = (
            "The map is an inventory of indexed records, not a complete checklist or an "
            "effort-normalised comparison."
        )
        result["limitations"].extend(limitations)
        points_ref = self._data_ref("group-observations", "application/geo+json", points)
        entities_ref = self._data_ref("group-entities", "application/json", entity_summary)
        result["visuals"] = [{
            "visual_id": "group-records",
            "visual_type": "map",
            "view": "group-observed-points",
            "title": f"Where {group} members have source-linked records",
            "priority": "primary",
            "status": "partial",
            "scope": {"aoi_ids": ["target", "context"], "time": {"start": None, "end": None}},
            "layers": [{
                "layer_id": "group-observations",
                "evidence_class": "observed",
                "geometry_type": "point",
                "data_ref": points_ref,
                "legend": {"label": f"Observed {group} records"},
                "style_hint": {"palette_role": "observed", "category_field": "entity"},
            }],
            "summary": {
                "headline": headline,
                "denominators": {
                    "records": len(rows),
                    "entities": len(entities),
                    "target_records": target_count,
                    "context_records": context_count,
                    "sources": len(sources),
                },
            },
            "drilldowns": [{
                "action_id": "inspect-group-entities",
                "label": "Inspect members and record counts",
                "data_ref": entities_ref,
            }],
            "limitations": limitations,
        }]
        result["actions"] = [self._action(
            "compare-group-effort", "run_capability",
            "Compare all records with documented effort", "coverage-versus-effort", {},
        )]
        return self._write_result(
            result,
            {
                "group-observations": ("application/geo+json", points),
                "group-entities": ("application/json", entity_summary),
            },
        )

    def _interaction_map(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if not set(arguments).issubset({"interaction_type", "entity"}):
            raise ValueError("interaction-map accepts only interaction_type and optional entity")
        interaction_type = str(arguments.get("interaction_type") or "").strip()
        requested = str(arguments.get("entity") or "").strip()
        if not interaction_type:
            raise ValueError("interaction-map requires a non-empty interaction_type")
        with self.connect() as connection:
            entity = self._resolve_entity(connection, requested) if requested else None
            if requested and entity is None:
                sources = self._source_versions(connection)
                result = self._base_result(
                    request_id, "interaction-map", original,
                    "Resolve an optional entity, then map explicitly admitted associations.",
                    {"interaction_type": interaction_type, "entity": requested},
                    f"No indexed entity matched “{requested}”.",
                    ["missing"], "blocked", sources,
                )
                result["limitations"].append(self._limitation(
                    "unresolved-entity",
                    "The supplied name did not resolve to a canonical entity in this pack.",
                    severity="error", affects=["answer"],
                ))
                return self._write_result(result, {})
            parameters: list[Any] = [interaction_type]
            entity_filter = ""
            if entity:
                entity_filter = " AND (i.subject_entity_id=? OR i.object_entity_id=?)"
                parameters.extend([entity["entity_id"], entity["entity_id"]])
            rows = connection.execute(
                f"""SELECT i.interaction_id,i.source_id,i.source_row,i.interaction_type,
                           i.event_date,i.latitude,i.longitude,i.uncertainty_m,i.count_value,
                           s.entity_id AS subject_id,s.canonical_name AS subject_canonical,
                           s.display_name AS subject_name,
                           o.entity_id AS object_id,o.canonical_name AS object_canonical,
                           o.display_name AS object_name,
                           COALESCE(c.target_role,'unlocated') AS target_role
                    FROM interactions i
                    JOIN entities s ON s.entity_id=i.subject_entity_id
                    JOIN entities o ON o.entity_id=i.object_entity_id
                    LEFT JOIN cells c ON c.cell_id=i.cell_id
                    WHERE lower(i.interaction_type)=lower(?) {entity_filter}
                      AND i.latitude IS NOT NULL AND i.longitude IS NOT NULL
                    ORDER BY i.event_date,i.source_id,i.source_row""",
                parameters,
            ).fetchall()
            available_types = [
                row[0] for row in connection.execute(
                    "SELECT DISTINCT interaction_type FROM interactions ORDER BY interaction_type"
                )
            ]
            source_ids = {row["source_id"] for row in rows}
            sources = self._source_versions(connection, source_ids)
        if not rows:
            result = self._base_result(
                request_id, "interaction-map", original,
                "Map explicitly admitted subject-object associations without inferring them from proximity.",
                {
                    "interaction_type": interaction_type,
                    **({"entity": requested} if requested else {}),
                },
                "No matching source-reported associations are indexed.",
                ["missing"], "blocked", sources,
            )
            result["limitations"].append(self._limitation(
                "no-matching-interactions",
                "No rows match this relation and optional entity; spatial co-occurrence was not used as a substitute.",
                severity="error", affects=["answer"],
            ))
            result["actions"] = [self._action(
                "choose-interaction-type", "filter", "Choose an indexed relation",
                "interaction-map", {"available_interaction_types": available_types},
            )]
            return self._write_result(result, {})
        edge_counts: dict[tuple[str, str], dict[str, Any]] = {}
        nodes: dict[str, dict[str, Any]] = {}
        for row in rows:
            subject_node = nodes.setdefault(row["subject_id"], {
                "id": row["subject_id"], "label": row["subject_name"],
                "canonical_name": row["subject_canonical"], "role": "subject",
            })
            if subject_node["role"] == "object":
                subject_node["role"] = "both"
            object_node = nodes.setdefault(row["object_id"], {
                "id": row["object_id"], "label": row["object_name"],
                "canonical_name": row["object_canonical"], "role": "object",
            })
            if object_node["role"] == "subject":
                object_node["role"] = "both"
            key = (row["subject_id"], row["object_id"])
            edge = edge_counts.setdefault(key, {
                "source": row["subject_id"], "target": row["object_id"],
                "interaction_type": row["interaction_type"], "records": 0,
                "count_sum": 0.0, "source_ids": set(),
            })
            edge["records"] += 1
            edge["count_sum"] += row["count_value"] or 0
            edge["source_ids"].add(row["source_id"])
        edges = [
            {**edge, "source_ids": sorted(edge["source_ids"])}
            for edge in sorted(
                edge_counts.values(),
                key=lambda item: (-item["records"], item["source"], item["target"]),
            )
        ]
        points = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": row["interaction_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    "subject": row["subject_name"],
                    "subject_canonical": row["subject_canonical"],
                    "object": row["object_name"],
                    "object_canonical": row["object_canonical"],
                    "interaction_type": row["interaction_type"],
                    "source_id": row["source_id"],
                    "source_row": row["source_row"],
                    "event_date": row["event_date"],
                    "count": row["count_value"],
                    "coordinate_uncertainty_m": row["uncertainty_m"],
                    "scope_role": row["target_role"],
                },
            } for row in rows],
        }
        focus = f" involving {entity['display_name']}" if entity else ""
        headline = (
            f"{len(rows):,} source-reported {interaction_type.replace('_', ' ')} records"
            f"{focus} link {len(nodes):,} entities in {len(edges):,} distinct pairs."
        )
        limitations = [self._limitation(
            "association-not-causation",
            "The visual retains the source-reported relation; it does not turn association into causation, dispersal, effect or preference.",
            affects=["interaction-points", "interaction-network", "answer"],
        )]
        result = self._base_result(
            request_id, "interaction-map", original,
            "Map and connect explicitly admitted subject-object associations.",
            {
                "interaction_type": interaction_type,
                **({"entity": entity["canonical_name"]} if entity else {}),
            },
            headline, ["observed"], "partial", sources,
        )
        result["answer"]["detail"] = (
            "Each map point retains both entities and its source row. The network aggregates "
            "those same rows into pairs; it is not inferred from nearby records."
        )
        result["limitations"].extend(limitations)
        point_ref = self._data_ref("interaction-points", "application/geo+json", points)
        node_ref = self._data_ref("interaction-nodes", "application/json", list(nodes.values()))
        edge_ref = self._data_ref("interaction-edges", "application/json", edges)
        scope = {"aoi_ids": ["target", "context"], "time": {"start": None, "end": None}}
        denominators = {
            "records": len(rows), "entities": len(nodes), "pairs": len(edges),
            "sources": len(source_ids),
        }
        result["visuals"] = [
            {
                "visual_id": "interaction-points",
                "visual_type": "map",
                "view": "source-reported-interaction-map",
                "title": "Where source-reported associations were recorded",
                "priority": "primary",
                "status": "partial",
                "scope": scope,
                "layers": [{
                    "layer_id": "interaction-points",
                    "evidence_class": "observed",
                    "geometry_type": "point",
                    "data_ref": point_ref,
                    "legend": {"label": interaction_type.replace("_", " ")},
                    "style_hint": {
                        "palette_role": "observed", "category_field": "subject",
                        "linked_category_field": "object",
                    },
                }],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [],
                "limitations": limitations,
            },
            {
                "visual_id": "interaction-network",
                "visual_type": "network",
                "view": "source-reported-interaction-network",
                "title": "Who or what is linked in the admitted source",
                "priority": "supporting",
                "status": "partial",
                "scope": scope,
                "layers": [
                    {
                        "layer_id": "interaction-nodes", "evidence_class": "observed",
                        "geometry_type": "node", "data_ref": node_ref,
                        "legend": {"label": "Entities"},
                        "style_hint": {"palette_role": "observed", "category_field": "role"},
                    },
                    {
                        "layer_id": "interaction-edges", "evidence_class": "derived",
                        "geometry_type": "edge", "data_ref": edge_ref,
                        "legend": {"label": "Aggregated source-reported pairs"},
                        "style_hint": {"palette_role": "derived", "weight_field": "records"},
                    },
                ],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [{
                    "action_id": "inspect-interaction-pairs",
                    "label": "Inspect pair counts and source IDs",
                    "data_ref": edge_ref,
                }],
                "limitations": limitations,
            },
        ]
        return self._write_result(
            result,
            {
                "interaction-points": ("application/geo+json", points),
                "interaction-nodes": ("application/json", list(nodes.values())),
                "interaction-edges": ("application/json", edges),
            },
        )

    def _stratified_survey_summary(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if set(arguments) != {"source_id", "category_property"}:
            raise ValueError(
                "stratified-survey-summary requires only source_id and category_property"
            )
        source_id = str(arguments.get("source_id") or "").strip()
        category_property = str(arguments.get("category_property") or "").strip()
        if not source_id or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9_]{0,63}", category_property
        ):
            raise ValueError("source_id and a safe category_property are required")
        category_path = f"$.{category_property}"
        with self.connect() as connection:
            source_exists = connection.execute(
                "SELECT 1 FROM sources WHERE source_id=?", (source_id,)
            ).fetchone()
            event_rows = [
                dict(row) for row in connection.execute(
                    """SELECT json_extract(properties_json,'$.Site_ID') AS site_id,
                              json_extract(properties_json,?) AS category,
                              AVG(latitude) AS latitude,AVG(longitude) AS longitude,
                              COUNT(*) AS event_records,
                              COUNT(DISTINCT entity_id) AS detected_entities,
                              SUM(COALESCE(count_value,0)) AS detected_count
                       FROM events
                       WHERE source_id=? AND latitude IS NOT NULL AND longitude IS NOT NULL
                         AND json_extract(properties_json,'$.Site_ID') IS NOT NULL
                         AND json_extract(properties_json,?) IS NOT NULL
                       GROUP BY site_id,category ORDER BY category,site_id""",
                    (category_path, source_id, category_path),
                )
            ]
            effort_rows = [
                dict(row) for row in connection.execute(
                    """SELECT json_extract(properties_json,'$.Site_ID') AS site_id,
                              json_extract(properties_json,?) AS category,
                              COUNT(*) AS visits,SUM(effort_value) AS effort,
                              MIN(effort_unit) AS effort_unit
                       FROM effort
                       WHERE source_id=?
                         AND json_extract(properties_json,'$.Site_ID') IS NOT NULL
                         AND json_extract(properties_json,?) IS NOT NULL
                       GROUP BY site_id,category ORDER BY category,site_id""",
                    (category_path, source_id, category_path),
                )
            ]
            sources = self._source_versions(connection, {source_id})
        if not source_exists or not event_rows or not effort_rows:
            result = self._base_result(
                request_id, "stratified-survey-summary", original,
                "Summarise one source whose event and effort rows share a site and category.",
                {"source_id": source_id, "category_property": category_property},
                "This source does not have compatible site-level events, effort and categories.",
                ["missing"], "blocked", sources,
            )
            result["limitations"].append(self._limitation(
                "incompatible-stratified-survey",
                "Both event and effort planes must retain the same Site_ID and category property.",
                severity="error", affects=["answer"],
            ))
            return self._write_result(result, {})
        effort_by_site = {
            (row["site_id"], row["category"]): row for row in effort_rows
        }
        sites = []
        for row in event_rows:
            effort = effort_by_site.get((row["site_id"], row["category"]), {})
            sites.append({
                **row,
                "visits": effort.get("visits", 0),
                "effort": effort.get("effort"),
                "effort_unit": effort.get("effort_unit"),
                "records_per_visit": (
                    row["event_records"] / effort["visits"]
                    if effort.get("visits") else None
                ),
            })
        category_rows: list[dict[str, Any]] = []
        for category in sorted({row["category"] for row in sites}):
            members = [row for row in sites if row["category"] == category]
            category_rows.append({
                "category": category,
                "sites": len(members),
                "visits": sum(row["visits"] for row in members),
                "effort": sum(row["effort"] or 0 for row in members),
                "effort_unit": next(
                    (row["effort_unit"] for row in members if row["effort_unit"]), None
                ),
                "event_records": sum(row["event_records"] for row in members),
                "detected_count": sum(row["detected_count"] or 0 for row in members),
                "mean_detected_entities_per_site": (
                    sum(row["detected_entities"] for row in members) / len(members)
                ),
                "records_per_visit": (
                    sum(row["event_records"] for row in members)
                    / sum(row["visits"] for row in members)
                    if sum(row["visits"] for row in members) else None
                ),
            })
        points = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": row["site_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    "label": f"{row['site_id']} · {row['category']}",
                    **{
                        key: row[key] for key in (
                            "site_id", "category", "event_records",
                            "detected_entities", "detected_count", "visits",
                            "effort", "effort_unit", "records_per_visit",
                        )
                    },
                },
            } for row in sites],
        }
        total_visits = sum(row["visits"] for row in sites)
        headline = (
            f"{len(sites):,} surveyed sites in {len(category_rows):,} categories are mapped "
            f"with {total_visits:,} explicit visits; category summaries retain effort."
        )
        limitations = [
            self._limitation(
                "descriptive-not-causal",
                "These are effort-visible descriptive summaries, not a causal treatment effect.",
                affects=["survey-sites", "category-comparison", "answer"],
            ),
            self._limitation(
                "detections-not-populations",
                "Records per visit and detected entities are observation-process summaries, not population abundance.",
                affects=["category-comparison", "answer"],
            ),
        ]
        result = self._base_result(
            request_id, "stratified-survey-summary", original,
            f"Compare {source_id} by source-reported {category_property} with site replication and effort.",
            {"source_id": source_id, "category_property": category_property},
            headline, ["observed", "derived"], "partial", sources,
        )
        result["answer"]["detail"] = (
            "The map shows every surveyed site and its denominator. The category comparison is "
            "suitable for orientation; an inferential comparison still needs the declared design "
            "and uncertainty."
        )
        result["limitations"].extend(limitations)
        points_ref = self._data_ref("stratified-survey-sites", "application/geo+json", points)
        summary_ref = self._data_ref(
            "stratified-category-summary", "application/json", category_rows
        )
        scope = {"aoi_ids": ["target", "context"], "time": {"start": None, "end": None}}
        denominators = {
            "sites": len(sites), "categories": len(category_rows),
            "visits": total_visits, "source": source_id,
        }
        result["visuals"] = [
            {
                "visual_id": "stratified-survey-sites",
                "visual_type": "map",
                "view": "stratified-survey-sites",
                "title": "Survey sites, categories and effort",
                "priority": "primary",
                "status": "partial",
                "scope": scope,
                "layers": [{
                    "layer_id": "stratified-survey-sites",
                    "evidence_class": "observed",
                    "geometry_type": "point",
                    "data_ref": points_ref,
                    "legend": {"label": category_property.replace("_", " ")},
                    "style_hint": {
                        "palette_role": "observed", "category_field": "category",
                        "size_field": "visits",
                    },
                }],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [],
                "limitations": limitations,
            },
            {
                "visual_id": "stratified-category-comparison",
                "visual_type": "table",
                "view": "stratified-category-comparison",
                "title": "Detection summaries with effort by category",
                "priority": "supporting",
                "status": "partial",
                "scope": scope,
                "layers": [{
                    "layer_id": "stratified-category-summary",
                    "evidence_class": "derived",
                    "geometry_type": "table",
                    "data_ref": summary_ref,
                    "legend": {"label": "Effort-visible category summary"},
                    "style_hint": {
                        "palette_role": "derived", "category_field": "category",
                        "value_fields": [
                            "mean_detected_entities_per_site", "records_per_visit",
                        ],
                    },
                }],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [{
                    "action_id": "inspect-category-summary",
                    "label": "Inspect denominators by category",
                    "data_ref": summary_ref,
                }],
                "limitations": limitations,
            },
        ]
        return self._write_result(
            result,
            {
                "stratified-survey-sites": ("application/geo+json", points),
                "stratified-category-summary": ("application/json", category_rows),
            },
        )

    def _cell_feature_map(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if (
            not {"feature_id", "year"}.issubset(arguments)
            or not set(arguments).issubset({"feature_id", "year", "scope"})
        ):
            raise ValueError(
                "cell-feature-map requires feature_id and year, with optional scope"
            )
        feature_id = str(arguments.get("feature_id") or "").strip()
        year = arguments.get("year")
        scope_name = str(arguments.get("scope") or "context")
        if (
            not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,127}", feature_id)
            or not isinstance(year, int)
            or isinstance(year, bool)
            or not 1900 <= year <= 2200
            or scope_name not in {"target", "context", "all_indexed"}
        ):
            raise ValueError(
                "a safe feature_id, integer year and declared scope are required"
            )
        if scope_name == "target":
            scope_sql = "c.target_role='target'"
            scope_parameters: tuple[Any, ...] = ()
        elif scope_name == "context":
            west, south, east, north = self.site["context_aoi"]["bbox"]
            scope_sql = (
                "c.center_lon BETWEEN ? AND ? AND c.center_lat BETWEEN ? AND ?"
            )
            scope_parameters = (west, east, south, north)
        else:
            scope_sql = "1=1"
            scope_parameters = ()
        with self.connect() as connection:
            rows = [
                dict(row) for row in connection.execute(
                    f"""SELECT f.cell_id,c.west,c.south,c.east,c.north,c.target_role,
                               f.value,f.unit,f.evidence_class,f.feature_label,
                               f.feature_description,f.source_asset,
                               f.aggregation,f.scale_m,f.source_id
                        FROM cell_features f JOIN cells c USING(cell_id)
                        WHERE f.feature_id=? AND f.year=? AND {scope_sql}
                        ORDER BY f.cell_id""",
                    (feature_id, year, *scope_parameters),
                )
            ]
            total_cells = connection.execute(
                f"SELECT COUNT(*) FROM cells c WHERE {scope_sql}",
                scope_parameters,
            ).fetchone()[0]
            source_ids = {row["source_id"] for row in rows}
            sources = self._source_versions(connection, source_ids)
        if not rows:
            result = self._base_result(
                request_id, "cell-feature-map", original,
                f"Map cell feature {feature_id} for {year} in the {scope_name} scope.",
                {"feature_id": feature_id, "year": year, "scope": scope_name},
                f"No finite {feature_id} values are indexed for {year} in the {scope_name} scope.",
                ["missing"], "blocked", sources,
            )
            result["limitations"].append(self._limitation(
                "feature-not-indexed",
                "The requested feature-year has no finite values in this pinned pack.",
                severity="error", affects=["answer"],
            ))
            return self._write_result(result, {})
        units = {row["unit"] for row in rows}
        classes = {row["evidence_class"] for row in rows}
        if len(units) != 1 or len(classes) != 1:
            raise RuntimeError(
                f"feature has incompatible units or evidence classes: {feature_id}:{year}"
            )
        unit = next(iter(units))
        evidence_class = next(iter(classes))
        labels = {row["feature_label"] for row in rows if row["feature_label"]}
        descriptions = {
            row["feature_description"] for row in rows if row["feature_description"]
        }
        if len(labels) > 1 or len(descriptions) > 1:
            raise RuntimeError(f"feature has inconsistent metadata: {feature_id}:{year}")
        values = [row["value"] for row in rows]
        missing = max(total_cells - len(rows), 0)
        status = "partial" if missing else "complete"
        visual_status = "partial" if missing else "ready"
        label = next(iter(labels), feature_id.replace("_", " "))
        description = next(iter(descriptions), "")
        headline = (
            f"{label} is mapped for {len(rows):,} of {total_cells:,} indexed cells "
            f"in the {scope_name} scope for {year}; "
            f"range {min(values):.3g}–{max(values):.3g} {unit}."
        )
        cells = {
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
                    "label": row["cell_id"],
                    "value": row["value"],
                    "unit": row["unit"],
                    "scope_role": row["target_role"],
                    "source_asset": row["source_asset"],
                    "aggregation": row["aggregation"],
                    "scale_m": row["scale_m"],
                },
            } for row in rows],
        }
        target_boundary = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": "target-aoi-boundary",
                "geometry": {
                    "type": "LineString",
                    "coordinates": self.site["target_aoi"]["geometry"]["coordinates"][0],
                },
                "properties": {
                    "label": self.site["label"],
                    "role": self.site["target_aoi"]["geometry_role"],
                },
            }],
        }
        metadata = [{
            "feature_id": feature_id,
            "feature_label": label,
            "feature_description": description,
            "year": year,
            "scope": scope_name,
            "cells_with_values": len(rows),
            "cells_without_values": missing,
            "minimum": min(values),
            "median": statistics.median(values),
            "maximum": max(values),
            "unit": unit,
            "evidence_class": evidence_class,
            "source_assets": ", ".join(sorted({
                row["source_asset"] for row in rows if row["source_asset"]
            })),
            "aggregation": ", ".join(sorted({
                row["aggregation"] for row in rows if row["aggregation"]
            })),
            "requested_scales_m": ", ".join(
                f"{value:g}" for value in sorted({
                    row["scale_m"] for row in rows if row["scale_m"] is not None
                })
            ),
        }]
        limitations = [
            self._limitation(
                "context-not-occurrence",
                "This cell-aligned surface is environmental context or a model input; it is not evidence that an entity occurs.",
                affects=["feature-map", "answer"],
            ),
            self._limitation(
                "cell-aggregation",
                "Cell aggregation smooths within-cell variation and is not a field measurement.",
                affects=["feature-map", "answer"],
            ),
        ]
        if feature_id.startswith("alphaearth_"):
            limitations.append(self._limitation(
                "embedding-axis-not-independent",
                "One AlphaEarth axis is not independently interpretable; modelling must use all 64 axes and normalise cell means when required.",
                affects=["feature-map", "answer"],
            ))
        if feature_id.startswith("dw_"):
            limitations.append(self._limitation(
                "class-score-not-cover",
                "Dynamic World values are model class scores, not measured land-cover proportions.",
                affects=["feature-map", "answer"],
            ))
        if feature_id.startswith(("era5_", "chirps_")):
            limitations.append(self._limitation(
                "coarse-source-grid",
                "The upstream climate grid is coarser than the serving cells; neighbouring values are not independent local measurements.",
                affects=["feature-map", "answer"],
            ))
        if missing:
            limitations.append(self._limitation(
                "incomplete-cell-support",
                f"{missing:,} indexed cells have no finite value for this feature-year.",
                affects=["feature-map", "answer"],
            ))
        result = self._base_result(
            request_id, "cell-feature-map", original,
            f"Map {feature_id} for {year} in the {scope_name} scope without treating it as occurrence evidence.",
            {"feature_id": feature_id, "year": year, "scope": scope_name},
            headline, ["reported", evidence_class], status, sources,
        )
        result["answer"]["detail"] = (
            "The colour ramp shows the indexed cell value. Open a cell or the metadata table "
            "to inspect its source asset, aggregation, scale and support."
        )
        result["limitations"].extend(limitations)
        cells_ref = self._data_ref("cell-feature-values", "application/geo+json", cells)
        boundary_ref = self._data_ref(
            "target-aoi-boundary", "application/geo+json", target_boundary
        )
        metadata_ref = self._data_ref(
            "cell-feature-metadata", "application/json", metadata
        )
        scope = {
            "aoi_ids": [scope_name],
            "time": {"start": f"{year}-01-01", "end": f"{year}-12-31"},
        }
        denominators = {
            "cells_with_values": len(rows),
            "cells_without_values": missing,
            "year": year,
            "scope": scope_name,
            "unit": unit,
        }
        result["visuals"] = [
            {
                "visual_id": "cell-feature-map",
                "visual_type": "map",
                "view": "cell-feature-map",
                "title": f"{label} · {year}",
                "priority": "primary",
                "status": visual_status,
                "scope": scope,
                "layers": [{
                    "layer_id": "cell-feature-values",
                    "evidence_class": evidence_class,
                    "geometry_type": "cell",
                    "data_ref": cells_ref,
                    "legend": {"label": f"{label} ({unit})"},
                    "style_hint": {
                        "palette_role": evidence_class,
                        "value_field": "value",
                    },
                }, {
                    "layer_id": "target-aoi-boundary",
                    "evidence_class": "reported",
                    "geometry_type": "line",
                    "data_ref": boundary_ref,
                    "legend": {"label": "Declared study envelope"},
                    "style_hint": {"palette_role": "reported"},
                }],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [{
                    "action_id": "inspect-feature-metadata",
                    "label": "Inspect feature lineage and support",
                    "data_ref": metadata_ref,
                }],
                "limitations": limitations,
            },
            {
                "visual_id": "cell-feature-metadata",
                "visual_type": "table",
                "view": "cell-feature-metadata",
                "title": "Feature lineage and support",
                "priority": "supporting",
                "status": visual_status,
                "scope": scope,
                "layers": [{
                    "layer_id": "cell-feature-metadata",
                    "evidence_class": evidence_class,
                    "geometry_type": "table",
                    "data_ref": metadata_ref,
                    "legend": {"label": "Lineage and support"},
                    "style_hint": {"palette_role": evidence_class},
                }],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [],
                "limitations": limitations,
            },
        ]
        return self._write_result(
            result,
            {
                "cell-feature-values": ("application/geo+json", cells),
                "target-aoi-boundary": ("application/geo+json", target_boundary),
                "cell-feature-metadata": ("application/json", metadata),
            },
        )

    def _gated_transfer(
        self, request_id: str, arguments: dict[str, Any], original: str
    ) -> dict[str, Any]:
        if set(arguments) != {"entity", "donor_scope", "target_scope"}:
            raise ValueError(
                "gated-transfer requires only entity, donor_scope and target_scope"
            )
        requested = str(arguments.get("entity") or "").strip()
        donor_scope = str(arguments.get("donor_scope") or "").strip()
        target_scope = str(arguments.get("target_scope") or "").strip()
        valid_scopes = {"target", "context", "all_indexed"}
        if (
            not requested
            or donor_scope not in valid_scopes
            or target_scope not in valid_scopes
            or donor_scope == target_scope
        ):
            raise ValueError("entity and two distinct declared scopes are required")

        def scope_clause(scope_name: str) -> tuple[str, tuple[Any, ...]]:
            if scope_name == "target":
                return "c.target_role='target'", ()
            if scope_name == "context":
                west, south, east, north = self.site["context_aoi"]["bbox"]
                return (
                    "c.center_lon BETWEEN ? AND ? AND c.center_lat BETWEEN ? AND ?",
                    (west, east, south, north),
                )
            return "1=1", ()

        donor_clause, donor_parameters = scope_clause(donor_scope)
        target_clause, target_parameters = scope_clause(target_scope)
        with self.connect() as connection:
            entity = self._resolve_entity(connection, requested)
            if entity is None:
                sources = self._source_versions(connection)
                result = self._base_result(
                    request_id, "gated-transfer", original,
                    "Resolve an entity before testing environmental transfer.",
                    {
                        "entity": requested,
                        "donor_scope": donor_scope,
                        "target_scope": target_scope,
                    },
                    f"No indexed entity matched “{requested}”.",
                    ["missing"], "blocked", sources,
                )
                result["limitations"].append(self._limitation(
                    "unresolved-entity",
                    "The supplied name did not resolve to a canonical entity in this pack.",
                    severity="error", affects=["answer"],
                ))
                return self._write_result(result, {})
            target_rows = [
                dict(row) for row in connection.execute(
                    f"""SELECT c.cell_id,c.west,c.south,c.east,c.north,
                               c.center_lat,c.center_lon,c.target_role
                        FROM cells c WHERE {target_clause} ORDER BY c.cell_id""",
                    target_parameters,
                )
            ]
            target_ids = {row["cell_id"] for row in target_rows}
            donor_event_rows = [
                dict(row) for row in connection.execute(
                    f"""SELECT e.event_id,e.source_id,e.source_row,e.event_date,
                               e.latitude,e.longitude,e.uncertainty_m,e.count_value,
                               e.cell_id,c.center_lat,c.center_lon
                        FROM events e JOIN cells c ON c.cell_id=e.cell_id
                        WHERE e.entity_id=? AND {donor_clause}
                          AND e.latitude IS NOT NULL AND e.longitude IS NOT NULL
                        ORDER BY e.source_id,e.source_row""",
                    (entity["entity_id"], *donor_parameters),
                )
            ]
            donor_event_rows = [
                row for row in donor_event_rows if row["cell_id"] not in target_ids
            ]
            feature_year_row = connection.execute(
                """SELECT MAX(year) FROM cell_features
                   WHERE feature_id GLOB 'alphaearth_A[0-9][0-9]'"""
            ).fetchone()
            feature_year = feature_year_row[0] if feature_year_row else None
            vector_rows = [
                dict(row) for row in connection.execute(
                    """SELECT f.cell_id,f.feature_id,f.value,f.source_id,
                              c.center_lat,c.center_lon
                       FROM cell_features f JOIN cells c USING(cell_id)
                       WHERE f.year=?
                         AND f.feature_id GLOB 'alphaearth_A[0-9][0-9]'
                       ORDER BY f.cell_id,f.feature_id""",
                    (feature_year,),
                )
            ] if feature_year is not None else []
            event_source_ids = {row["source_id"] for row in donor_event_rows}
            feature_source_ids = {row["source_id"] for row in vector_rows}
            sources = self._source_versions(
                connection, event_source_ids | feature_source_ids
            )
        if not target_rows:
            result = self._base_result(
                request_id, "gated-transfer", original,
                f"Test transfer for {entity['canonical_name']} into {target_scope}.",
                {
                    "entity": entity["canonical_name"],
                    "donor_scope": donor_scope,
                    "target_scope": target_scope,
                },
                f"The declared target scope “{target_scope}” contains no indexed cells.",
                ["missing"], "blocked", sources,
            )
            result["limitations"].append(self._limitation(
                "empty-target-scope",
                "A transfer cannot be evaluated without target cells.",
                severity="error", affects=["answer"],
            ))
            return self._write_result(result, {})
        if feature_year is None:
            result = self._base_result(
                request_id, "gated-transfer", original,
                f"Test transfer for {entity['canonical_name']} into {target_scope}.",
                {
                    "entity": entity["canonical_name"],
                    "donor_scope": donor_scope,
                    "target_scope": target_scope,
                },
                "No complete, versioned environmental feature cube is indexed.",
                ["observed", "missing"], "blocked", sources,
            )
            result["limitations"].append(self._limitation(
                "feature-cube-not-indexed",
                "Environmental analogy cannot be scored without a common feature vector in donor and target cells.",
                severity="error", affects=["answer"],
            ))
            return self._write_result(result, {})

        vector_parts: dict[str, dict[str, Any]] = {}
        for row in vector_rows:
            item = vector_parts.setdefault(
                row["cell_id"],
                {
                    "latitude": row["center_lat"],
                    "longitude": row["center_lon"],
                    "values": {},
                },
            )
            item["values"][row["feature_id"]] = row["value"]
        feature_ids = [f"alphaearth_A{index:02d}" for index in range(64)]
        vectors = {
            cell_id: {
                "latitude": item["latitude"],
                "longitude": item["longitude"],
                "vector": [item["values"][feature_id] for feature_id in feature_ids],
            }
            for cell_id, item in vector_parts.items()
            if all(feature_id in item["values"] for feature_id in feature_ids)
        }
        donor_cell_ids = {row["cell_id"] for row in donor_event_rows}
        donor_vectors = {
            cell_id: vectors[cell_id] for cell_id in donor_cell_ids
            if cell_id in vectors
        }
        target_vectors = {
            row["cell_id"]: vectors[row["cell_id"]] for row in target_rows
            if row["cell_id"] in vectors
        }
        analogue = score_analogues(donor_vectors, target_vectors)
        threshold = analogue["threshold"]
        scores = analogue["scores"]
        supported_ids = {
            cell_id for cell_id, score in scores.items()
            if threshold is not None and score >= threshold
        }
        unsupported_ids = target_ids - supported_ids
        feature_support = (
            len(target_vectors) / len(target_rows) if target_rows else 0.0
        )
        environmental_support = (
            len(supported_ids) / len(target_rows)
            if threshold is not None and target_rows else None
        )
        donor_blocks = analogue["donor_spatial_blocks"]
        gates = [
            {
                "gate_id": "donor-sample",
                "status": (
                    "pass" if len(donor_event_rows) >= 20 and len(donor_vectors) >= 10
                    else "fail"
                ),
                "observed": (
                    f"{len(donor_event_rows)} records in "
                    f"{len(donor_vectors)} feature-complete cells"
                ),
                "threshold": "at least 20 records and 10 cells",
                "explanation": "Avoid fitting or transferring from a handful of clustered records.",
            },
            {
                "gate_id": "spatial-replication",
                "status": "pass" if donor_blocks >= 4 else "fail",
                "observed": f"{donor_blocks} donor blocks",
                "threshold": "at least 4 blocks of 0.05 degrees",
                "explanation": "The analogue threshold uses other spatial blocks, not the focal donor cell.",
            },
            {
                "gate_id": "target-feature-support",
                "status": "pass" if feature_support >= 0.95 else "fail",
                "observed": f"{feature_support:.1%} of target cells",
                "threshold": "at least 95 percent",
                "explanation": "All 64 embedding axes must be finite in a target cell.",
            },
            {
                "gate_id": "environmental-support",
                "status": (
                    "pass" if environmental_support is not None
                    and environmental_support >= 0.50 else "fail"
                ),
                "observed": (
                    f"{environmental_support:.1%} of target cells"
                    if environmental_support is not None else "not estimable"
                ),
                "threshold": (
                    f"at least 50 percent above donor holdout q10={threshold:.3f}"
                    if threshold is not None else "no defensible threshold"
                ),
                "explanation": "Marks target cells with an environmental analogue among donor occurrence cells.",
            },
            {
                "gate_id": "predictive-discrimination",
                "status": "not_evaluated",
                "observed": "no compatible effort-linked nondetection or background evaluation",
                "threshold": "spatially separated evaluation against a declared baseline",
                "explanation": "Similarity alone cannot establish occurrence probability or species-level discrimination.",
            },
        ]

        donor_points = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": row["event_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    "label": entity["display_name"],
                    "source_id": row["source_id"],
                    "source_row": row["source_row"],
                    "event_date": row["event_date"],
                    "coordinate_uncertainty_m": row["uncertainty_m"],
                    "count": row["count_value"],
                    "scope_role": donor_scope,
                },
            } for row in donor_event_rows],
        }

        def cell_feature(row: dict[str, Any], score: float | None, reason: str) -> dict:
            properties: dict[str, Any] = {
                "label": row["cell_id"],
                "scope_role": row["target_role"],
                "support_status": reason,
            }
            if score is not None:
                properties["estimate"] = score
                properties["unit"] = "cosine-similarity"
                properties["support_threshold"] = threshold
            return {
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
                "properties": properties,
            }

        analogue_cells = {
            "type": "FeatureCollection",
            "features": [
                cell_feature(row, scores[row["cell_id"]], "supported-analogue")
                for row in target_rows if row["cell_id"] in supported_ids
            ],
        }
        unsupported_cells = {
            "type": "FeatureCollection",
            "features": [
                cell_feature(
                    row,
                    scores.get(row["cell_id"]),
                    (
                        "below-donor-support-threshold"
                        if row["cell_id"] in scores else "missing-feature-vector"
                    ),
                )
                for row in target_rows if row["cell_id"] in unsupported_ids
            ],
        }
        target_boundary = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": "target-aoi-boundary",
                "geometry": {
                    "type": "LineString",
                    "coordinates": self.site["target_aoi"]["geometry"]["coordinates"][0],
                },
                "properties": {
                    "label": self.site["label"],
                    "role": self.site["target_aoi"]["geometry_role"],
                },
            }],
        }
        limitations = [
            self._limitation(
                "analogue-not-occurrence-probability",
                "The orange surface is embedding similarity to donor occurrence cells, not occurrence probability, abundance or a confirmed distribution.",
                affects=["analogue-transfer", "answer"],
            ),
            self._limitation(
                "predictive-gate-not-evaluated",
                "No compatible effort-linked nondetection or target-group background was available for spatially separated predictive evaluation.",
                affects=["analogue-transfer", "answer"],
            ),
            self._limitation(
                "mixed-observation-processes",
                "Donor records may combine protocols and reporting processes; repeated records do not become independent samples.",
                affects=["donor-observations", "answer"],
            ),
        ]
        headline = (
            f"{len(donor_event_rows):,} {entity['display_name']} donor records in "
            f"{len(donor_vectors):,} feature-complete cells support an environmental-analogue "
            f"screen for {len(supported_ids):,} of {len(target_rows):,} target cells."
        )
        result = self._base_result(
            request_id, "gated-transfer", original,
            (
                f"Use all 64 normalised {feature_year} AlphaEarth axes to test environmental "
                f"analogy from {donor_scope} records of {entity['canonical_name']} into "
                f"{target_scope}; keep predictive discrimination unevaluated."
            ),
            {
                "entity": entity["canonical_name"],
                "entity_id": entity["entity_id"],
                "donor_scope": donor_scope,
                "target_scope": target_scope,
                "feature_year": feature_year,
            },
            headline, ["reported", "observed", "modelled", "missing"],
            "partial", sources,
        )
        result["answer"]["detail"] = (
            "Observed donor points, environmentally supported target cells and unsupported "
            "target cells are separate layers. The screen is useful for deciding whether a "
            "full model is worth attempting; it does not pass the predictive-model gate."
        )
        result["limitations"].extend(limitations)
        donor_ref = self._data_ref(
            "donor-observations", "application/geo+json", donor_points
        )
        analogue_ref = self._data_ref(
            "target-analogue-cells", "application/geo+json", analogue_cells
        )
        unsupported_ref = self._data_ref(
            "unsupported-target-cells", "application/geo+json", unsupported_cells
        )
        boundary_ref = self._data_ref(
            "transfer-target-boundary", "application/geo+json", target_boundary
        )
        gates_ref = self._data_ref("transfer-gates", "application/json", gates)
        scope = {
            "aoi_ids": [donor_scope, target_scope],
            "time": {"start": f"{feature_year}-01-01", "end": f"{feature_year}-12-31"},
        }
        denominators = {
            "donor_records": len(donor_event_rows),
            "donor_cells": len(donor_vectors),
            "donor_spatial_blocks": donor_blocks,
            "target_cells": len(target_rows),
            "supported_target_cells": len(supported_ids),
            "feature_year": feature_year,
            "embedding_axes": 64,
        }
        result["visuals"] = [
            {
                "visual_id": "analogue-transfer",
                "visual_type": "map",
                "view": "donor-target-gates",
                "title": f"Environmental analogue screen for {entity['display_name']}",
                "priority": "primary",
                "status": "partial",
                "scope": scope,
                "layers": [
                    {
                        "layer_id": "target-analogue-cells",
                        "evidence_class": "modelled",
                        "geometry_type": "raster",
                        "data_ref": analogue_ref,
                        "legend": {"label": "Supported environmental analogue score"},
                        "style_hint": {
                            "palette_role": "modelled",
                            "value_field": "estimate",
                        },
                    },
                    {
                        "layer_id": "unsupported-target-cells",
                        "evidence_class": "missing",
                        "geometry_type": "cell",
                        "data_ref": unsupported_ref,
                        "legend": {"label": "Unsupported or missing target cells"},
                        "style_hint": {"palette_role": "missing"},
                    },
                    {
                        "layer_id": "donor-observations",
                        "evidence_class": "observed",
                        "geometry_type": "point",
                        "data_ref": donor_ref,
                        "legend": {"label": "Observed donor records"},
                        "style_hint": {"palette_role": "observed"},
                    },
                    {
                        "layer_id": "transfer-target-boundary",
                        "evidence_class": "reported",
                        "geometry_type": "line",
                        "data_ref": boundary_ref,
                        "legend": {"label": "Declared target envelope"},
                        "style_hint": {"palette_role": "reported"},
                    },
                ],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [{
                    "action_id": "inspect-transfer-gates",
                    "label": "Inspect every transfer gate",
                    "data_ref": gates_ref,
                }],
                "limitations": limitations,
            },
            {
                "visual_id": "transfer-gates",
                "visual_type": "table",
                "view": "transfer-gates",
                "title": "Transfer gates",
                "priority": "supporting",
                "status": "partial",
                "scope": scope,
                "layers": [{
                    "layer_id": "transfer-gates",
                    "evidence_class": "derived",
                    "geometry_type": "table",
                    "data_ref": gates_ref,
                    "legend": {"label": "Gate result"},
                    "style_hint": {"palette_role": "derived"},
                }],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [],
                "limitations": limitations,
            },
        ]
        if donor_scope != "all_indexed":
            result["actions"].append(self._action(
                "broaden-donor-scope", "run_capability",
                "Check all indexed donor records", "gated-transfer",
                {
                    "entity": entity["canonical_name"],
                    "donor_scope": "all_indexed",
                    "target_scope": target_scope,
                },
            ))
        result["actions"].append(self._action(
            "request-predictive-model", "request_model",
            "Request an effort-aware predictive model", "gated-transfer",
            {
                "entity": entity["canonical_name"],
                "donor_scope": donor_scope,
                "target_scope": target_scope,
                "missing_gate": "predictive-discrimination",
            },
        ))
        return self._write_result(
            result,
            {
                "donor-observations": ("application/geo+json", donor_points),
                "target-analogue-cells": ("application/geo+json", analogue_cells),
                "unsupported-target-cells": (
                    "application/geo+json", unsupported_cells
                ),
                "transfer-target-boundary": (
                    "application/geo+json", target_boundary
                ),
                "transfer-gates": ("application/json", gates),
            },
        )

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
                result["limitations"].append(missing)
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
        result["limitations"].extend(limitations)
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
