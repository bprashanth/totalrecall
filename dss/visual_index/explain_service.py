#!/usr/bin/env python3
"""Explain how one stored idli-result/1 value was computed.

This service is deterministic and read-only. It never calls a model, never re-runs a capability
and never invents a number. It opens the immutable result envelope written by
`result_service.ResultService`, opens the stored layer payload that carried the mark the user is
asking about, and re-reads the same pinned site index rows that produced it. The answer it returns
is a structured lineage object: which capability ran, what question and bindings it was given,
which source versions fed it, which exact source rows stand behind one mark, what aggregation was
applied to them, and which declared limitations affect that mark.

Contract note: this is *not* a new idli-result/1 producer. It returns `idli-explain/1`, an audit
object about an existing result id. The result it describes is unchanged.
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
    from dss.visual_index.result_service import SAFE_HANDLE, _load_json
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/explain_service.py
    from result_service import SAFE_HANDLE, _load_json


EXPLAIN_VERSION = "idli-explain/1"
MAX_ROWS = 60
MAX_MARKS = 5
YEAR_MONTH = re.compile(r"^(\d{4})[-/](\d{1,2})$")
YEAR_ONLY = re.compile(r"^(\d{4})$")
COORDINATE_MARK = re.compile(
    r"^at:\s*(-?\d{1,3}(?:\.\d+)?)\s*[:,]\s*(-?\d{1,3}(?:\.\d+)?)$"
)
# A click on a point layer counts as that point only when it lands close by: about 250 m,
# expressed in degrees of latitude (longitude is scaled by cos(latitude) in the distance).
POINT_HIT_RADIUS_DEG = 0.00225


def _row(row: sqlite3.Row) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()}


def _clean(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.split())
    return value


class ExplainService:
    """Reconstruct the lineage of one mark inside one stored result."""

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
        capability_path = self.site_pack / "capabilities.json"
        registry = _load_json(capability_path) if capability_path.is_file() else {}
        self.capabilities = {
            item["capability_id"]: item
            for item in (registry.get("capabilities") or [])
            if isinstance(item, dict) and item.get("capability_id")
        }

    @classmethod
    def from_result_service(cls, service: Any) -> "ExplainService":
        """Build from a live ResultService without reaching into its private state."""
        return cls(service.site_pack, service.index_path, service.state_root)

    # ------------------------------------------------------------------ storage

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def load_envelope(self, result_id: str) -> dict[str, Any] | None:
        if not SAFE_HANDLE.fullmatch(str(result_id or "")):
            return None
        path = self.state_root / "results" / result_id / "result.json"
        return _load_json(path) if path.is_file() else None

    def load_payload(self, result_id: str, handle: str) -> Any:
        if not SAFE_HANDLE.fullmatch(result_id) or not SAFE_HANDLE.fullmatch(handle):
            return None
        root = self.state_root / "results" / result_id / "data"
        for suffix in (".geojson", ".json"):
            path = root / f"{handle}{suffix}"
            if path.is_file():
                return json.loads(path.read_text(encoding="utf-8"))
        return None

    # ------------------------------------------------------------------ selection

    @staticmethod
    def _select_layer(
        envelope: dict[str, Any], layer_id: str | None
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        visuals = [item for item in (envelope.get("visuals") or []) if isinstance(item, dict)]
        if layer_id:
            for visual in visuals:
                for layer in visual.get("layers") or []:
                    if layer.get("layer_id") == layer_id:
                        return visual, layer
            return None, None
        for wanted in ("primary", "supporting", "audit"):
            for visual in visuals:
                if visual.get("priority") == wanted and visual.get("layers"):
                    return visual, visual["layers"][0]
        if visuals and visuals[0].get("layers"):
            return visuals[0], visuals[0]["layers"][0]
        return (visuals[0] if visuals else None), None

    @staticmethod
    def _features(payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, dict) and payload.get("type") == "FeatureCollection":
            return [item for item in payload.get("features") or [] if isinstance(item, dict)]
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return []

    @staticmethod
    def _feature_identity(feature: dict[str, Any]) -> str:
        if feature.get("id") is not None:
            return str(feature["id"])
        properties = feature.get("properties") if isinstance(feature, dict) else {}
        properties = properties if isinstance(properties, dict) else feature
        for key in ("cell_id", "event_id", "site_id", "entity_id", "label", "category"):
            if properties.get(key) is not None:
                return str(properties[key])
        year, month = properties.get("year"), properties.get("month")
        if year is not None and month is not None:
            return f"{int(year):04d}-{int(month):02d}"
        return ""

    @staticmethod
    def _feature_value(feature: dict[str, Any]) -> float | None:
        properties = feature.get("properties") if isinstance(feature, dict) else None
        properties = properties if isinstance(properties, dict) else feature
        for key in ("value", "records", "effort", "event_records", "count", "events"):
            candidate = properties.get(key)
            if isinstance(candidate, (int, float)) and not isinstance(candidate, bool):
                return float(candidate)
        return None

    def _find_feature(
        self, features: list[dict[str, Any]], mark: dict[str, Any]
    ) -> dict[str, Any] | None:
        wanted = {
            str(value) for key, value in mark.items()
            if key in {
                "id", "mark", "feature_id", "cell_id", "event_id", "interaction_id",
                "measurement_id", "site_id", "entity_id", "time", "bucket",
            } and value not in (None, "")
        }
        if not wanted:
            return None
        for feature in features:
            identity = self._feature_identity(feature)
            if identity and identity in wanted:
                return feature
            properties = feature.get("properties")
            properties = properties if isinstance(properties, dict) else {}
            for key in (
                "cell_id", "event_id", "site_id", "entity_id", "source_row",
                "uploaded_name", "display_name", "canonical_name", "label", "category",
                "bucket",
            ):
                if properties.get(key) is not None and str(properties[key]) in wanted:
                    return feature
        return None

    # ------------------------------------------------------------------ coordinate marks

    @staticmethod
    def _mark_coordinate(mark: dict[str, Any]) -> tuple[float, float] | None:
        """Extract (lat, lon) when the mark identifies a map location, not a feature id."""
        for key in ("mark", "id", "at", "coordinate"):
            value = mark.get(key)
            if isinstance(value, str):
                match = COORDINATE_MARK.match(value.strip())
                if match:
                    lat, lon = float(match.group(1)), float(match.group(2))
                    if -90 <= lat <= 90 and -180 <= lon <= 180:
                        return lat, lon
        lat_value = mark.get("lat", mark.get("latitude"))
        lon_value = mark.get("lon", mark.get("lng", mark.get("longitude")))
        if lat_value in (None, "") or lon_value in (None, ""):
            return None
        try:
            lat, lon = float(lat_value), float(lon_value)
        except (TypeError, ValueError):
            return None
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon
        return None

    @staticmethod
    def _ring_contains(lat: float, lon: float, ring: list[Any]) -> bool:
        """Even-odd ray cast over one GeoJSON ring of [lon, lat] pairs."""
        inside = False
        count = len(ring)
        for index in range(count):
            x1, y1 = float(ring[index][0]), float(ring[index][1])
            x2, y2 = float(ring[(index + 1) % count][0]), float(ring[(index + 1) % count][1])
            if (y1 > lat) != (y2 > lat):
                crossing = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
                if lon < crossing:
                    inside = not inside
        return inside

    @classmethod
    def _geometry_contains(cls, lat: float, lon: float, geometry: dict[str, Any]) -> bool:
        kind = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if not isinstance(coordinates, list):
            return False
        try:
            if kind == "Polygon":
                rings = coordinates
            elif kind == "MultiPolygon":
                return any(
                    cls._geometry_contains(lat, lon, {"type": "Polygon", "coordinates": part})
                    for part in coordinates
                )
            else:
                return False
            if not rings or not cls._ring_contains(lat, lon, rings[0]):
                return False
            return not any(cls._ring_contains(lat, lon, hole) for hole in rings[1:])
        except (TypeError, ValueError, IndexError):
            # Malformed geometry: fall back to its bounding box below via _geometry_bbox.
            return False

    @staticmethod
    def _geometry_bbox(geometry: dict[str, Any]) -> tuple[float, float, float, float] | None:
        points: list[tuple[float, float]] = []

        def collect(node: Any) -> None:
            if (
                isinstance(node, list) and len(node) >= 2
                and all(isinstance(value, (int, float)) for value in node[:2])
            ):
                points.append((float(node[0]), float(node[1])))
            elif isinstance(node, list):
                for child in node:
                    collect(child)

        collect(geometry.get("coordinates"))
        if not points:
            return None
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        return min(xs), min(ys), max(xs), max(ys)

    @classmethod
    def _feature_at(
        cls, features: list[dict[str, Any]], lat: float, lon: float
    ) -> dict[str, Any] | None:
        """Resolve a coordinate against the stored layer geometry, exactly as rendered.

        Area features (cells, polygons) win by containment, with a bounding-box fallback for
        geometry the ray cast cannot parse. Point features win by proximity within a small
        radius. Nothing outside the stored payload is consulted, so the answer names the same
        feature the user saw.
        """
        fallback: dict[str, Any] | None = None
        nearest: tuple[float, dict[str, Any]] | None = None
        scale = max(math.cos(math.radians(lat)), 0.01)
        for feature in features:
            geometry = feature.get("geometry")
            if not isinstance(geometry, dict):
                continue
            kind = geometry.get("type")
            if kind in {"Polygon", "MultiPolygon"}:
                if cls._geometry_contains(lat, lon, geometry):
                    return feature
                if fallback is None:
                    bbox = cls._geometry_bbox(geometry)
                    if bbox and bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                        fallback = feature
            elif kind == "Point":
                coordinates = geometry.get("coordinates")
                try:
                    point_lon, point_lat = float(coordinates[0]), float(coordinates[1])
                except (TypeError, ValueError, IndexError):
                    continue
                distance = math.hypot((point_lon - lon) * scale, point_lat - lat)
                if distance <= POINT_HIT_RADIUS_DEG and (
                    nearest is None or distance < nearest[0]
                ):
                    nearest = (distance, feature)
            elif kind in {"LineString", "MultiLineString"} and fallback is None:
                bbox = cls._geometry_bbox(geometry)
                if bbox and bbox[0] <= lon <= bbox[2] and bbox[1] <= lat <= bbox[3]:
                    fallback = feature
        if nearest is not None:
            return nearest[1]
        return fallback

    # ------------------------------------------------------------------ mark identity

    def _classify(
        self, connection: sqlite3.Connection, mark: dict[str, Any]
    ) -> dict[str, Any]:
        """Decide what kind of thing the requested mark is, using the index as the authority."""
        explicit = [
            ("event", "event_id"), ("interaction", "interaction_id"),
            ("measurement", "measurement_id"), ("cell", "cell_id"),
            ("survey_site", "site_id"), ("entity", "entity_id"),
        ]
        for kind, key in explicit:
            value = mark.get(key)
            if value not in (None, ""):
                return {"kind": kind, "id": str(value)}
        for key in ("id", "mark", "feature_id", "bucket", "time"):
            value = mark.get(key)
            if value in (None, ""):
                continue
            identity = str(value)
            probes = (
                ("event", "SELECT 1 FROM events WHERE event_id=?"),
                ("interaction", "SELECT 1 FROM interactions WHERE interaction_id=?"),
                ("cell", "SELECT 1 FROM cells WHERE cell_id=?"),
                ("measurement", "SELECT 1 FROM measurements WHERE measurement_id=?"),
                ("entity", "SELECT 1 FROM entities WHERE entity_id=?"),
            )
            for kind, sql in probes:
                try:
                    if connection.execute(sql, (identity,)).fetchone():
                        return {"kind": kind, "id": identity}
                except sqlite3.Error:
                    continue
            match = YEAR_MONTH.match(identity)
            if match:
                return {
                    "kind": "time_bucket", "id": identity,
                    "year": int(match.group(1)), "month": int(match.group(2)),
                }
            match = YEAR_ONLY.match(identity)
            if match:
                return {"kind": "time_bucket", "id": identity, "year": int(match.group(1))}
            return {"kind": "unresolved", "id": identity}
        year = mark.get("year")
        if year not in (None, ""):
            month = mark.get("month")
            identity = (
                f"{int(year):04d}-{int(month):02d}" if month not in (None, "")
                else f"{int(year):04d}"
            )
            return {
                "kind": "time_bucket", "id": identity, "year": int(year),
                **({"month": int(month)} if month not in (None, "") else {}),
            }
        return {"kind": "none", "id": ""}

    # ------------------------------------------------------------------ row lineage

    def _event_rows(
        self, connection: sqlite3.Connection, where: str, parameters: tuple[Any, ...]
    ) -> list[dict[str, Any]]:
        return [
            _row(row) for row in connection.execute(
                f"""SELECT e.event_id,e.source_id,e.source_row,e.event_date,e.event_type,
                           e.evidence_class,e.latitude,e.longitude,e.count_value,e.cell_id,
                           e.entity_id,en.display_name AS entity
                    FROM events e LEFT JOIN entities en ON en.entity_id=e.entity_id
                    WHERE {where}
                    ORDER BY e.event_date,e.source_id,e.source_row LIMIT {MAX_ROWS}""",
                parameters,
            )
        ]

    def _lineage_for(
        self, connection: sqlite3.Connection, identity: dict[str, Any],
        bindings: dict[str, Any], layer_id: str, feature: dict[str, Any] | None,
    ) -> dict[str, Any]:
        kind = identity.get("kind")
        mark_id = str(identity.get("id") or "")
        value = self._feature_value(feature) if feature else None
        if kind == "event":
            rows = self._event_rows(connection, "e.event_id=?", (mark_id,))
            return {
                "aggregation": "none",
                "statement": (
                    f"This mark is one admitted source row carried through unchanged: "
                    f"event {mark_id} from {rows[0]['source_id']} row {rows[0]['source_row']}."
                    if rows else f"No indexed event row matches {mark_id}."
                ),
                "plane": "events", "rows": rows, "row_count": len(rows),
            }
        if kind == "interaction":
            rows = [
                _row(row) for row in connection.execute(
                    """SELECT i.interaction_id,i.source_id,i.source_row,i.interaction_type,
                              i.event_date,i.latitude,i.longitude,i.count_value,
                              s.display_name AS subject,o.display_name AS object
                       FROM interactions i
                       JOIN entities s ON s.entity_id=i.subject_entity_id
                       JOIN entities o ON o.entity_id=i.object_entity_id
                       WHERE i.interaction_id=?""",
                    (mark_id,),
                )
            ]
            return {
                "aggregation": "none",
                "statement": (
                    "This mark is one source-reported association row carried through "
                    f"unchanged: interaction {mark_id}."
                ),
                "plane": "interactions", "rows": rows, "row_count": len(rows),
            }
        if kind == "measurement":
            rows = [
                _row(row) for row in connection.execute(
                    """SELECT measurement_id,source_id,source_row,metric,value,unit,
                              event_date,year,month,location_id
                       FROM measurements WHERE measurement_id=?""",
                    (mark_id,),
                )
            ]
            return {
                "aggregation": "none",
                "statement": f"This mark is one indexed measurement row: {mark_id}.",
                "plane": "measurements", "rows": rows, "row_count": len(rows),
            }
        if kind == "cell":
            if layer_id in {"effort"}:
                rows = [
                    _row(row) for row in connection.execute(
                        """SELECT effort_id,source_id,source_row,method,event_date,
                                  effort_value,effort_unit
                           FROM effort WHERE cell_id=?
                           ORDER BY event_date,source_id,source_row LIMIT ?""",
                        (mark_id, MAX_ROWS),
                    )
                ]
                total = connection.execute(
                    "SELECT COUNT(*),SUM(effort_value) FROM effort WHERE cell_id=?",
                    (mark_id,),
                ).fetchone()
                return {
                    "aggregation": "sum",
                    "statement": (
                        f"cell {mark_id} effort = sum of effort_value over "
                        f"{total[0]:,} effort rows = {total[1]}"
                    ),
                    "plane": "effort", "rows": rows, "row_count": int(total[0] or 0),
                }
            if layer_id in {"cell-feature-values", "seasonal-cell-values"}:
                feature_id = str(bindings.get("feature_id") or "")
                year = bindings.get("year")
                rows = [
                    _row(row) for row in connection.execute(
                        """SELECT cell_id,source_id,source_row,feature_id,year,value,unit,
                                  evidence_class,source_asset,aggregation,scale_m
                           FROM cell_features WHERE cell_id=? AND feature_id=?
                             AND (? IS NULL OR year=?)""",
                        (mark_id, feature_id, year, year),
                    )
                ]
                aggregation = rows[0]["aggregation"] if rows else "unknown"
                return {
                    "aggregation": str(aggregation or "unknown"),
                    "statement": (
                        f"cell {mark_id} value = one indexed cell_features row for "
                        f"{feature_id}{f' in {year}' if year else ''}, produced upstream by "
                        f"'{aggregation}' over the source asset at "
                        f"{rows[0]['scale_m'] if rows else '?'} m."
                    ),
                    "plane": "cell_features", "rows": rows, "row_count": len(rows),
                }
            entity_id = str(bindings.get("entity_id") or "")
            where = "e.cell_id=?"
            parameters: tuple[Any, ...] = (mark_id,)
            if entity_id:
                where += " AND e.entity_id=?"
                parameters = (mark_id, entity_id)
            rows = self._event_rows(connection, where, parameters)
            totals = connection.execute(
                f"""SELECT COUNT(*) AS records,COUNT(DISTINCT entity_id) AS entities
                    FROM events e WHERE {where}""",
                parameters,
            ).fetchone()
            observed = (
                f" The stored mark value is {value:g}." if isinstance(value, float) else ""
            )
            return {
                "aggregation": "count",
                "statement": (
                    f"cell {mark_id} value = count of {totals['records']:,} indexed event rows "
                    f"({totals['entities']:,} distinct entities) whose cell_id is {mark_id}."
                    + observed
                ),
                "plane": "events", "rows": rows, "row_count": int(totals["records"]),
            }
        if kind == "time_bucket":
            metric = str(bindings.get("metric") or "")
            year, month = identity.get("year"), identity.get("month")
            if metric:
                where = "metric=? AND year=?"
                parameters = (metric, year)
                if month is not None:
                    where += " AND month=?"
                    parameters = (metric, year, month)
                rows = [
                    _row(row) for row in connection.execute(
                        f"""SELECT measurement_id,source_id,source_row,metric,value,unit,
                                   event_date,year,month
                            FROM measurements WHERE {where} AND value IS NOT NULL
                            ORDER BY event_date,source_id,source_row LIMIT {MAX_ROWS}""",
                        parameters,
                    )
                ]
                aggregate = connection.execute(
                    f"""SELECT COUNT(*),AVG(value),MIN(unit) FROM measurements
                        WHERE {where} AND value IS NOT NULL""",
                    parameters,
                ).fetchone()
                mean = aggregate[1]
                return {
                    "aggregation": "mean",
                    "statement": (
                        f"the {mark_id} point = mean of {aggregate[0]:,} indexed {metric} "
                        f"measurement rows = "
                        f"{f'{mean:.4g}' if isinstance(mean, float) else mean} "
                        f"{aggregate[2] or ''}".strip()
                    ),
                    "plane": "measurements", "rows": rows,
                    "row_count": int(aggregate[0] or 0),
                }
            where = "e.year=?"
            parameters = (year,)
            if month is not None:
                where += " AND e.month=?"
                parameters = (year, month)
            entity_id = str(bindings.get("entity_id") or "")
            if entity_id:
                where += " AND e.entity_id=?"
                parameters = (*parameters, entity_id)
            rows = self._event_rows(connection, where, parameters)
            total = connection.execute(
                f"SELECT COUNT(*) FROM events e WHERE {where}", parameters
            ).fetchone()[0]
            return {
                "aggregation": "count",
                "statement": (
                    f"the {mark_id} point = count of {total:,} indexed event rows dated in "
                    f"that bucket."
                ),
                "plane": "events", "rows": rows, "row_count": int(total or 0),
            }
        if kind == "entity":
            rows = self._event_rows(connection, "e.entity_id=?", (mark_id,))
            total = connection.execute(
                "SELECT COUNT(*) FROM events WHERE entity_id=?", (mark_id,)
            ).fetchone()[0]
            return {
                "aggregation": "count",
                "statement": (
                    f"entity {mark_id} value = {total:,} indexed event rows for that entity."
                ),
                "plane": "events", "rows": rows, "row_count": int(total or 0),
            }
        if kind == "survey_site":
            rows = self._event_rows(
                connection,
                "json_extract(e.properties_json,'$.Site_ID')=?",
                (mark_id,),
            )
            total = connection.execute(
                "SELECT COUNT(*) FROM events WHERE json_extract(properties_json,'$.Site_ID')=?",
                (mark_id,),
            ).fetchone()[0]
            return {
                "aggregation": "count",
                "statement": (
                    f"site {mark_id} value = {total:,} indexed event rows whose source row "
                    f"reports Site_ID {mark_id}."
                ),
                "plane": "events", "rows": rows, "row_count": int(total or 0),
            }
        return {
            "aggregation": "unknown",
            "statement": (
                "The requested mark did not resolve to an indexed row; ask for a mark id that "
                "the stored layer actually contains."
                if mark_id else
                "No mark was requested, so this lineage describes the whole result."
            ),
            "plane": None, "rows": [], "row_count": 0,
        }

    @staticmethod
    def _upload_lineage(
        envelope: dict[str, Any], feature: dict[str, Any] | None, identity: dict[str, Any]
    ) -> dict[str, Any]:
        """Explain a mark in a user-upload result from the upload itself, never from the pack.

        An upload-derived mark counts the user's own rows. Re-querying the site index for an
        entity id that appears in such a result would attribute pack evidence to user data.
        """
        binding = (envelope.get("audit") or {}).get("session_binding") or {}
        properties = (feature or {}).get("properties")
        properties = properties if isinstance(properties, dict) else {}
        file_rows = properties.get("source_rows")
        uploaded = properties.get("uploaded_rows")
        detail = ""
        if uploaded is not None:
            detail = f" It aggregates {uploaded} uploaded row(s)."
        if isinstance(file_rows, list) and file_rows:
            detail += " File rows: " + ", ".join(str(item) for item in file_rows[:25]) + "."
        return {
            "aggregation": "user-supplied",
            "statement": (
                f"Mark {identity.get('id') or '(whole result)'} comes from the user-supplied "
                f"upload {binding.get('upload_id') or ''}, not from a registered source."
                + detail
            ),
            "plane": "upload",
            "rows": [properties] if properties else [],
            "row_count": int(uploaded) if isinstance(uploaded, int) else (
                1 if properties else 0
            ),
        }

    # ------------------------------------------------------------------ context

    def _source_details(
        self, connection: sqlite3.Connection, envelope: dict[str, Any],
        source_ids: set[str],
    ) -> list[dict[str, Any]]:
        declared = {
            str(item.get("source_id")): item
            for item in ((envelope.get("audit") or {}).get("source_versions") or [])
            if isinstance(item, dict)
        }
        wanted = source_ids or set(declared)
        rows = {
            row["source_id"]: _row(row) for row in connection.execute(
                "SELECT source_id,title,publisher,license,url,doi,content_sha256,"
                "capabilities_json FROM sources"
            )
        }
        details = []
        for source_id in sorted(wanted):
            row = rows.get(source_id, {})
            capabilities = json.loads(row.get("capabilities_json") or "[]")
            details.append({
                "source_id": source_id,
                "title": _clean(row.get("title")),
                "publisher": _clean(row.get("publisher")),
                "license": row.get("license"),
                "digest": declared.get(source_id, {}).get("digest")
                or ("sha256:" + row["content_sha256"] if row.get("content_sha256") else None),
                "synthetic": "synthetic" in capabilities,
                "declared_in_result": source_id in declared,
            })
        return details

    @staticmethod
    def _limitations(
        envelope: dict[str, Any], visual: dict[str, Any] | None, layer_id: str
    ) -> list[dict[str, Any]]:
        wanted = {"answer", layer_id}
        if visual:
            wanted.add(str(visual.get("visual_id") or ""))
        collected: dict[str, dict[str, Any]] = {}
        pools = list(envelope.get("limitations") or [])
        if visual:
            pools += list(visual.get("limitations") or [])
        for item in pools:
            if not isinstance(item, dict):
                continue
            affects = {str(value) for value in (item.get("affects") or [])}
            if affects and not (affects & wanted):
                continue
            collected[str(item.get("code"))] = {
                "code": str(item.get("code") or ""),
                "severity": str(item.get("severity") or ""),
                "message": _clean(item.get("message")),
                "affects": sorted(affects),
            }
        return list(collected.values())

    def _top_marks(
        self, features: list[dict[str, Any]], layer_id: str
    ) -> list[dict[str, Any]]:
        scored = []
        for feature in features:
            value = self._feature_value(feature)
            identity = self._feature_identity(feature)
            if identity and value is not None:
                scored.append({"mark": identity, "value": value})
        scored.sort(key=lambda item: (-item["value"], item["mark"]))
        return scored[:MAX_MARKS]

    # ------------------------------------------------------------------ entry point

    def explain(
        self, result_id: str, layer_id: str | None = None,
        mark: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        envelope = self.load_envelope(result_id)
        if envelope is None:
            raise LookupError(f"unknown result_id: {result_id}")
        if isinstance(mark, str):
            mark = {"mark": mark} if mark.strip() else {}
        mark = {
            key: value for key, value in (mark or {}).items()
            if value not in (None, "") and isinstance(key, str)
        }
        visual, layer = self._select_layer(envelope, layer_id)
        if layer_id and layer is None:
            raise LookupError(f"result {result_id} has no layer {layer_id}")
        resolved_layer = str((layer or {}).get("layer_id") or "")
        handle = str(((layer or {}).get("data_ref") or {}).get("handle") or "")
        payload = self.load_payload(result_id, handle) if handle else None
        features = self._features(payload)
        capability_run = (
            (envelope.get("audit") or {}).get("capability_runs") or [{}]
        )[0]
        capability_id = str(capability_run.get("capability_id") or "")
        descriptor = self.capabilities.get(capability_id, {})
        bindings = (envelope.get("question") or {}).get("bindings") or {}
        top_marks = self._top_marks(features, resolved_layer)
        requested_mark = dict(mark)
        auto_selected = False
        resolution = "identity" if mark else "none"
        coordinate = self._mark_coordinate(mark) if mark else None
        coordinate_missed = False
        if coordinate is not None:
            # The caller pointed at a place, not a feature id. Resolve it against the stored
            # geometry the user actually saw. When nothing is there, say so — never substitute
            # a different mark for a location the user explicitly chose.
            hit = self._feature_at(features, coordinate[0], coordinate[1])
            if hit is not None:
                mark = {"mark": self._feature_identity(hit)}
                resolution = "coordinate"
            else:
                coordinate_missed = True
                resolution = "coordinate"
        elif not mark and top_marks:
            # "Why is there a hotspot?" arrives with no mark of any kind. Explaining the largest
            # stored mark is the deterministic, useful default; the flag below obliges the
            # caller to say that this is what happened.
            mark = {"mark": top_marks[0]["mark"]}
            auto_selected = True
            resolution = "auto-largest"
        user_supplied = bool(
            ((envelope.get("audit") or {}).get("session_binding"))
            or any(
                item.get("user_supplied")
                for item in ((envelope.get("audit") or {}).get("source_versions") or [])
                if isinstance(item, dict)
            )
        )
        with self.connect() as connection:
            if coordinate_missed:
                lat, lon = coordinate
                identity = {"kind": "no_mark_at_location", "id": f"at:{lat:g}:{lon:g}"}
                feature = None
                lineage = {
                    "aggregation": "none",
                    "statement": (
                        f"No mark exists at latitude {lat:g}, longitude {lon:g} in layer "
                        f"{resolved_layer or '(none)'}: none of the layer's "
                        f"{len(features):,} stored marks covers that location. This is a miss, "
                        "not evidence of absence; ask about a location the layer covers or "
                        "name a mark id."
                    ),
                    "plane": None, "rows": [], "row_count": 0,
                }
            else:
                identity = self._classify(connection, mark) if not user_supplied else {
                    "kind": "upload_mark" if mark else "none",
                    "id": str(next(iter(mark.values()), "")) if mark else "",
                }
                feature = self._find_feature(features, mark) if mark else None
                if feature is None and identity.get("kind") not in {"none", "unresolved"}:
                    feature = self._find_feature(features, {"mark": identity.get("id")})
                lineage = (
                    self._upload_lineage(envelope, feature, identity) if user_supplied
                    else self._lineage_for(
                        connection, identity, bindings, resolved_layer, feature
                    )
                )
            source_ids = {
                str(row.get("source_id")) for row in lineage["rows"] if row.get("source_id")
            }
            sources = self._source_details(connection, envelope, source_ids)
        answer = envelope.get("answer") or {}
        explanation = {
            "schema_version": EXPLAIN_VERSION,
            "result_id": str(envelope.get("result_id") or ""),
            "request_id": str(envelope.get("request_id") or ""),
            "revision": envelope.get("revision"),
            "status": str(envelope.get("status") or ""),
            "site": envelope.get("site") or {},
            "capability": {
                "capability_id": capability_id,
                "version": capability_run.get("version"),
                "run_status": capability_run.get("status"),
                "label": descriptor.get("label"),
                "evidence_classes": descriptor.get("evidence_classes") or [],
                "required_planes": descriptor.get("required_planes") or [],
            },
            "question": {
                "original": _clean((envelope.get("question") or {}).get("original")),
                "resolved": _clean((envelope.get("question") or {}).get("resolved")),
                "bindings": bindings,
            },
            "answer": {
                "headline": _clean(answer.get("headline")),
                "evidence_classes": answer.get("evidence_classes") or [],
            },
            "visual": {
                "visual_id": (visual or {}).get("visual_id"),
                "visual_type": (visual or {}).get("visual_type"),
                "view": (visual or {}).get("view"),
                "title": _clean((visual or {}).get("title")),
            },
            "layer": {
                "layer_id": resolved_layer,
                "evidence_class": (layer or {}).get("evidence_class"),
                "geometry_type": (layer or {}).get("geometry_type"),
                "handle": handle,
                "digest": ((layer or {}).get("data_ref") or {}).get("digest"),
                "marks_in_layer": len(features),
            },
            "mark": {
                "requested": requested_mark,
                "resolution": resolution,
                "auto_selected": auto_selected,
                "kind": identity.get("kind"),
                "id": identity.get("id"),
                "stored_properties": (
                    (feature.get("properties") if isinstance(feature, dict) else None)
                    or (feature if isinstance(feature, dict) else None)
                ) if feature else None,
                "stored_value": self._feature_value(feature) if feature else None,
            },
            "computation": {
                "aggregation": lineage["aggregation"],
                "statement": _clean(
                    (
                        "AUTO-SELECTED: no specific mark was identified, so this lineage is "
                        "for the layer's largest mark. " if auto_selected else ""
                    )
                    + str(lineage["statement"])
                ),
                "plane": lineage["plane"],
                "contributing_rows": lineage["row_count"],
                "rows_returned": len(lineage["rows"]),
                "truncated": lineage["row_count"] > len(lineage["rows"]),
            },
            "source_rows": lineage["rows"],
            "source_versions": sources,
            "limitations": self._limitations(envelope, visual, resolved_layer),
            "top_marks": top_marks,
            "evidence_origin": "user_upload" if user_supplied else "site_pack",
            "method": (
                "Deterministic lineage: the stored idli-result/1 envelope and its immutable layer "
                "payload were re-read, and "
                + (
                    "the mark is attributed to the user's own uploaded rows; the site index was "
                    "not consulted."
                    if user_supplied else
                    "the same pinned site index rows were re-queried."
                )
                + " No model was called and no value was recomputed."
            ),
        }
        return explanation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--result-id", required=True)
    parser.add_argument("--layer")
    parser.add_argument("--mark")
    args = parser.parse_args(argv)
    service = ExplainService(args.site_pack, args.index, args.state)
    print(json.dumps(
        service.explain(args.result_id, args.layer, args.mark),
        indent=2, ensure_ascii=False, default=str,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
