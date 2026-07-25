#!/usr/bin/env python3
"""Where were two or more subjects recorded in the same square, and what else is one of them doing.

"Show me where both hornbills and elephants occur" had no answer here. The one capability that
sounded close — `interaction-map` — only maps associations a source explicitly declared (a bird
seen feeding on a tree), so it came back blocked, and the user was left with nothing while the
answer sat in the index: elephant in 96 squares, hornbills in 34, and twenty squares holding both.

Two capabilities close that gap, and neither one is about any particular kind of subject:

* `co-occurrence-map` intersects the squares each subject's records fall in. The shared squares are
  the answer and are drawn first; each subject keeps its own layer so a reader can see which side
  of the overlap is thin.
* `entity-activity-profile` answers "what else is X doing" from the same engine: which kinds of
  record exist for X, from which surveys, over which years, what was measured where X was seen,
  and which other subjects share its squares.

The honesty burden here is unusually heavy and is carried in the envelope rather than left to the
model. Two records in one square is not an interaction, not an association and not contact; it is
two rows written down inside the same square, possibly by different people, using different
methods, in different years. Every result says so, and says how big the square is, because "they
overlap" is exactly the sentence a reader wants to believe.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
from typing import Any

try:
    from dss.visual_index.cell_language import describe_box
    from dss.visual_index.result_service import (
        SAFE_HANDLE, _atomic_write_once, _digest, _load_json, _stable_json,
    )
    from dss.visual_index.site_stats import cased_vocabulary, humanise
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/cooccurrence_service.py
    from cell_language import describe_box  # type: ignore[no-redef]
    from result_service import (  # type: ignore[no-redef]
        SAFE_HANDLE, _atomic_write_once, _digest, _load_json, _stable_json,
    )
    from site_stats import cased_vocabulary, humanise  # type: ignore[no-redef]


COOCCURRENCE_VERSION = "idli-result/1"
MAX_SUBJECTS = 4
MAX_DRILLDOWN_ROWS = 400
MAX_PROFILE_PARTNERS = 5
SAFE_RANK = re.compile(r"^[a-z][a-z0-9_]{0,63}$")

COOCCURRENCE_CAPABILITIES: list[dict[str, Any]] = [
    {
        "capability_id": "co-occurrence-map",
        "version": "1.0.0",
        "label": "Map the squares where two or more subjects were both recorded",
        "input_schema": {
            "type": "object",
            "properties": {
                "subjects": {"type": "array", "minItems": 2, "maxItems": MAX_SUBJECTS},
                "time": {"type": "object"},
                "same_year": {"type": "boolean"},
            },
            "required": ["subjects"],
        },
        "output_views": ["co-occurrence-map", "co-occurrence-summary"],
        "required_planes": ["events", "cells", "entities"],
        "optional_planes": [],
        "latency_class": "interactive",
        "evidence_classes": ["observed", "derived"],
        "availability": "ready",
        "scope": "site",
        "reason": (
            "Set intersection over the squares each subject's own records fall in. It reports "
            "shared recording, never interaction: nothing about contact is inferred or claimed."
        ),
    },
    {
        "capability_id": "interaction-pairs",
        "version": "1.0.0",
        "label": "Name the recorded subject-object pairs: who was recorded on or with what",
        "input_schema": {
            "type": "object",
            "properties": {
                "interaction_type": {"type": "string", "minLength": 1},
                "entity": {"type": "string", "minLength": 1},
                "object": {"type": "string", "minLength": 1},
                "limit": {"type": "integer", "minimum": 1, "maximum": 60},
            },
            "required": [],
        },
        "output_views": ["interaction-pairs", "interaction-network"],
        "required_planes": ["interactions", "entities"],
        "optional_planes": [],
        "latency_class": "interactive",
        "evidence_classes": ["observed"],
        "availability": "ready",
        "scope": "site",
        "reason": (
            "Reads the stored subject-object rows and names the pairs. Each pair is what a "
            "source recorded, not a demonstrated ecological function."
        ),
    },
    {
        "capability_id": "entity-activity-profile",
        "version": "1.0.0",
        "label": "Summarise everything recorded for one subject, and who shares its squares",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "minLength": 1},
                "rank": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,63}$"},
                "group": {"type": "string", "minLength": 1},
            },
            "required": [],
        },
        "output_views": ["entity-activity-profile", "co-occurrence-summary"],
        "required_planes": ["events", "entities"],
        "optional_planes": ["measurements", "cells", "effort"],
        "latency_class": "interactive",
        "evidence_classes": ["observed", "derived"],
        "availability": "ready",
        "scope": "site",
        "reason": "Counts of what exists for one subject; nothing is modelled and nothing inferred.",
    },
]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _key(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _flatten(value: Any) -> str:
    """Compare a name the way a person types it: case, spaces and underscores do not count."""
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


class CooccurrenceService:
    """Shared-square analysis over the pinned index, for any subject the pack can resolve."""

    def __init__(
        self, site_pack: pathlib.Path, index_path: pathlib.Path, state_root: pathlib.Path
    ):
        self.site_pack = pathlib.Path(site_pack).resolve()
        self.index_path = pathlib.Path(index_path).resolve()
        self.state_root = pathlib.Path(state_root).resolve()
        if not self.index_path.is_file():
            raise FileNotFoundError(self.index_path)
        self.site = _load_json(self.site_pack / "site.json")
        self.pack_digest = _digest(self.site)
        self.synthetic = bool(self.site.get("synthetic"))
        self._cased: dict[str, str] | None = None

    @classmethod
    def from_result_service(cls, service: Any) -> "CooccurrenceService":
        return cls(service.site_pack, service.index_path, service.state_root)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def _vocabulary(self, connection: sqlite3.Connection) -> dict[str, str]:
        """How this pack spells its own words, read once for the life of the service."""
        if self._cased is None:
            self._cased = cased_vocabulary(connection)
        return self._cased

    # ------------------------------------------------------------------ subjects

    def resolve_subject(
        self, connection: sqlite3.Connection, subject: Any
    ) -> dict[str, Any]:
        """Resolve one subject the way the site already resolves names, and say how it resolved.

        A subject arrives as the user's own word — "elephant", "hornbills", "Bucerotidae" — or as
        an explicit `{kind, value}`. A registered alias wins; otherwise every hierarchy rank the
        pack declares is searched for that value, which is how "all hornbills together" reaches a
        family without anybody naming the rank. Nothing is guessed: an unresolved subject is
        returned as unresolved, with what the pack does hold at that rank.
        """
        kind = ""
        rank = ""
        value = ""
        if isinstance(subject, dict):
            kind = _key(subject.get("kind"))
            rank = _key(subject.get("rank"))
            value = _clean(
                subject.get("value") or subject.get("entity") or subject.get("group")
                or subject.get("name")
            )
        else:
            value = _clean(subject)
        if not value:
            raise ValueError("each subject needs a name")
        if rank and not SAFE_RANK.fullmatch(rank):
            raise ValueError(f"unsafe hierarchy rank: {rank}")

        if kind not in {"group", "record_kind"}:
            row = connection.execute(
                """SELECT e.entity_id, e.display_name
                   FROM entity_aliases a JOIN entities e ON e.entity_id = a.entity_id
                   WHERE a.alias_key=?""",
                (_key(value),),
            ).fetchone()
            if row is not None:
                return {
                    "requested": value, "kind": "entity", "rank": None,
                    "label": row["display_name"], "entity_ids": [row["entity_id"]],
                    "event_types": [], "members": 1, "resolved": True,
                }
        if kind != "group":
            # A subject can be a KIND OF RECORD rather than a named thing: "public works" and
            # "people leaving" are event types here, not entities, and a question about where
            # both are recorded is the same question.
            for row in connection.execute("SELECT DISTINCT event_type FROM events"):
                if _flatten(row[0]) == _flatten(value):
                    return {
                        "requested": value, "kind": "record_kind", "rank": None,
                        # Humanised here, because this label is read out to a person:
                        # `mgnrega_work` is not a phrase anybody says.
                        "label": humanise(row[0], self._vocabulary(connection)),
                        "entity_ids": [], "event_types": [row[0]], "members": 1,
                        "resolved": True,
                    }
        ranks = [rank] if rank else self._ranks(connection)
        for candidate in ranks:
            members = [
                row["entity_id"] for row in connection.execute(
                    "SELECT entity_id FROM entities "
                    "WHERE lower(json_extract(hierarchy_json,?))=lower(?)",
                    (f"$.{candidate}", value),
                )
            ]
            if members:
                return {
                    "requested": value, "kind": "group", "rank": candidate,
                    "label": value, "entity_ids": members, "event_types": [],
                    "members": len(members), "resolved": True,
                }
        return {
            "requested": value, "kind": kind or "entity", "rank": rank or None,
            "label": value, "entity_ids": [], "event_types": [], "members": 0,
            "resolved": False,
            "known_here": self._known_names(connection, rank),
            "known_record_kinds": [
                str(row[0]) for row in connection.execute(
                    "SELECT DISTINCT event_type FROM events ORDER BY event_type LIMIT 12"
                )
            ],
        }

    @staticmethod
    def _selector(subject: dict[str, Any], alias: str = "") -> tuple[str, list[Any]]:
        """The WHERE fragment that selects this subject's own rows, whatever kind it is."""
        prefix = f"{alias}." if alias else ""
        if subject.get("entity_ids"):
            placeholders = ",".join("?" * len(subject["entity_ids"]))
            return f"{prefix}entity_id IN ({placeholders})", list(subject["entity_ids"])
        if subject.get("event_types"):
            placeholders = ",".join("?" * len(subject["event_types"]))
            return f"{prefix}event_type IN ({placeholders})", list(subject["event_types"])
        return "0", []

    @staticmethod
    def _ranks(connection: sqlite3.Connection) -> list[str]:
        ranks: set[str] = set()
        for row in connection.execute(
            "SELECT hierarchy_json FROM entities WHERE hierarchy_json IS NOT NULL"
        ):
            try:
                hierarchy = json.loads(row[0] or "{}")
            except (TypeError, ValueError):
                continue
            ranks.update(
                str(key) for key in (hierarchy or {}) if SAFE_RANK.fullmatch(str(key))
            )
        # Narrow ranks first: a name that is both a genus and a family should resolve to the
        # narrower reading, and taxonomic packs order that way by convention.
        order = ["species", "genus", "subfamily", "family", "order", "class", "phylum", "kingdom"]
        return sorted(ranks, key=lambda name: (order.index(name) if name in order else 99, name))

    @staticmethod
    def _known_names(connection: sqlite3.Connection, rank: str) -> list[str]:
        if rank:
            return sorted({
                str(row[0]) for row in connection.execute(
                    "SELECT DISTINCT json_extract(hierarchy_json,?) FROM entities "
                    "WHERE json_extract(hierarchy_json,?) IS NOT NULL",
                    (f"$.{rank}", f"$.{rank}"),
                ) if row[0]
            })[:20]
        return [
            str(row[0]) for row in connection.execute(
                """SELECT en.display_name FROM entities en JOIN events e
                   ON e.entity_id = en.entity_id GROUP BY en.display_name
                   ORDER BY COUNT(*) DESC LIMIT 20"""
            )
        ]

    # ------------------------------------------------------------------ squares

    def subject_squares(
        self, connection: sqlite3.Connection, subject: dict[str, Any],
        window: tuple[int | None, int | None] = (None, None),
    ) -> dict[str, dict[str, Any]]:
        """Every square this subject's own records fall in, with how many and which years."""
        selector, selector_parameters = self._selector(subject, "e")
        if not selector_parameters:
            return {}
        clauses = [selector, "e.cell_id IS NOT NULL"]
        parameters: list[Any] = list(selector_parameters)
        if window[0] is not None:
            clauses.append("e.year >= ?")
            parameters.append(window[0])
        if window[1] is not None:
            clauses.append("e.year <= ?")
            parameters.append(window[1])
        squares: dict[str, dict[str, Any]] = {}
        for row in connection.execute(
            f"""SELECT e.cell_id AS cell_id, COUNT(*) AS records,
                       MIN(e.year) AS first_year, MAX(e.year) AS last_year,
                       COUNT(DISTINCT e.source_id) AS sources
                FROM events e WHERE {' AND '.join(clauses)}
                GROUP BY e.cell_id""",
            parameters,
        ):
            squares[row["cell_id"]] = {
                "records": int(row["records"]),
                "first_year": row["first_year"],
                "last_year": row["last_year"],
                "sources": int(row["sources"]),
            }
        return squares

    def _years_in_squares(
        self, connection: sqlite3.Connection, subject: dict[str, Any], cells: list[str],
    ) -> dict[str, set[int]]:
        selector, selector_parameters = self._selector(subject)
        if not selector_parameters or not cells:
            return {}
        squares = ",".join("?" * len(cells))
        found: dict[str, set[int]] = {}
        for row in connection.execute(
            f"""SELECT cell_id, year FROM events
                WHERE {selector} AND cell_id IN ({squares}) AND year IS NOT NULL
                GROUP BY cell_id, year""",
            [*selector_parameters, *cells],
        ):
            found.setdefault(row["cell_id"], set()).add(int(row["year"]))
        return found

    def _cell_geometry(
        self, connection: sqlite3.Connection, cells: list[str]
    ) -> dict[str, dict[str, float]]:
        if not cells:
            return {}
        placeholders = ",".join("?" * len(cells))
        return {
            row["cell_id"]: {
                "west": row["west"], "south": row["south"],
                "east": row["east"], "north": row["north"],
            }
            for row in connection.execute(
                f"SELECT cell_id,west,south,east,north FROM cells "
                f"WHERE cell_id IN ({placeholders})",
                cells,
            )
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

    def _source_versions(
        self, connection: sqlite3.Connection, source_ids: set[str]
    ) -> list[dict[str, Any]]:
        rows = {
            row["source_id"]: row for row in connection.execute(
                "SELECT source_id,title,content_sha256,capabilities_json FROM sources"
            )
        }
        return [{
            "source_id": source_id,
            "version": None,
            "digest": "sha256:" + rows[source_id]["content_sha256"],
            "synthetic": "synthetic" in json.loads(rows[source_id]["capabilities_json"]),
            "title": rows[source_id]["title"],
        } for source_id in sorted(source_ids) if source_id in rows]

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
            item for item in COOCCURRENCE_CAPABILITIES
            if item["capability_id"] == capability_id
        )
        result = {
            "schema_version": COOCCURRENCE_VERSION,
            "result_id": result_id,
            "request_id": request_id,
            "revision": 1,
            "status": status,
            "site": site,
            "question": {"original": original, "resolved": resolved, "bindings": bindings},
            "answer": {"headline": headline, "detail": "", "evidence_classes": evidence_classes},
            "visuals": [],
            "limitations": [],
            "actions": [],
            "audit": {
                "audit_id": f"{result_id}/1",
                "source_versions": source_versions,
                "capability_runs": [{
                    "capability_id": capability_id,
                    "version": descriptor["version"],
                    "status": "blocked" if status == "blocked" else "complete",
                }],
                "query_hash": _digest({"capability_id": capability_id, "bindings": bindings}),
                # Every square here was read from stored rows. Nothing was fitted or predicted.
                "assurance": "observed",
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
            _atomic_write_once(
                root / "data" / f"{handle}{suffix}", _stable_json(payload).encode()
            )
        _atomic_write_once(
            root / "result.json",
            (json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n").encode(),
        )
        return result

    def _aoi_payload(self) -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "id": "target",
                "geometry": self.site["target_aoi"]["geometry"],
                "properties": {"label": self.site.get("label")},
            }],
        }

    @staticmethod
    def _square_feature(
        cell_id: str, box: dict[str, float], properties: dict[str, Any]
    ) -> dict[str, Any]:
        return {
            "type": "Feature",
            "id": cell_id,
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [box["west"], box["south"]], [box["east"], box["south"]],
                    [box["east"], box["north"]], [box["west"], box["north"]],
                    [box["west"], box["south"]],
                ]],
            },
            "properties": properties,
        }

    @staticmethod
    def _square_size(geometry: dict[str, dict[str, float]]) -> str:
        for box in geometry.values():
            return describe_box(
                box["west"], box["south"], box["east"], box["north"]
            )["size"]
        return "map square"

    # ------------------------------------------------------------------ co-occurrence

    def co_occurrence_map(
        self, request_id: str, subjects: Any, question: str = "",
        time: Any = None, same_year: bool = False,
    ) -> dict[str, Any]:
        """Map the squares where every named subject was recorded."""
        if not isinstance(subjects, (list, tuple)) or not 2 <= len(subjects) <= MAX_SUBJECTS:
            raise ValueError(
                f"co-occurrence-map needs between 2 and {MAX_SUBJECTS} subjects"
            )
        window = self._window(time)
        request_id = _clean(request_id)[:200] or f"cooccur-{_digest(subjects).split(':', 1)[1][:12]}"
        with self.connect() as connection:
            resolved = [self.resolve_subject(connection, item) for item in subjects]
            bindings = {
                "subjects": [{
                    "requested": item["requested"], "kind": item["kind"],
                    "rank": item["rank"], "label": item["label"],
                } for item in resolved],
                "time": {"from": window[0], "to": window[1]},
                "same_year": bool(same_year),
            }
            original = _clean(question) or (
                "Where were " + " and ".join(item["requested"] for item in resolved)
                + " both recorded?"
            )
            result_id = "result-co-" + _digest(
                {"site": self.site.get("site_id"), "pack": self.pack_digest,
                 "request_id": request_id, **bindings}
            ).split(":", 1)[1][:20]
            unresolved = [item for item in resolved if not item["resolved"]]
            if unresolved:
                return self._unresolved(
                    result_id, request_id, original, bindings, unresolved, resolved, connection
                )
            squares = [self.subject_squares(connection, item, window) for item in resolved]
            shared = sorted(set.intersection(*[set(item) for item in squares]) if squares else [])
            same_year_shared: list[str] = []
            if shared:
                per_subject_years = [
                    self._years_in_squares(connection, item, shared) for item in resolved
                ]
                for cell_id in shared:
                    common = set.intersection(*[
                        years.get(cell_id, set()) for years in per_subject_years
                    ]) if per_subject_years else set()
                    if common:
                        same_year_shared.append(cell_id)
            drawn = same_year_shared if (same_year and same_year_shared) else shared
            all_cells = sorted({cell for item in squares for cell in item})
            geometry = self._cell_geometry(connection, all_cells)
            rows, source_ids = self._shared_rows(connection, resolved, drawn, window)
            source_versions = self._source_versions(connection, source_ids)
            year_span = self._year_span(connection, resolved, window)
        size = self._square_size(geometry)
        labels = [item["label"] for item in resolved]
        joined = " and ".join(labels)
        headline = (
            f"{len(drawn)} {size}s hold records of both {joined}."
            if len(labels) == 2 else
            f"{len(drawn)} {size}s hold records of all of: {joined}."
        ) if drawn else (
            f"No {size} holds records of {joined} together."
        )
        resolved_question = (
            f"Squares inside this site's boundary where records exist for every one of: {joined}"
            + (f", both in the same year" if same_year and same_year_shared else "")
            + "."
        )
        status = "complete" if drawn else "partial"
        result = self._base(
            result_id, request_id, "co-occurrence-map", original, resolved_question,
            bindings, headline, ["observed", "derived"], status, source_versions,
        )
        result["answer"]["detail"] = (
            "Each square counts records that fall inside it. "
            + "; ".join(
                f"{item['label']}: {len(square):,} {size}s, "
                f"{sum(cell['records'] for cell in square.values()):,} records"
                for item, square in zip(resolved, squares)
            )
            + f". Shared: {len(shared):,}"
            + (
                f", of which {len(same_year_shared):,} have records from the same year"
                if shared else ""
            )
            + "."
        )

        aoi = self._aoi_payload()
        shared_payload = {
            "type": "FeatureCollection",
            "features": [
                self._square_feature(cell_id, geometry[cell_id], {
                    "role": "shared square",
                    "subjects": labels,
                    "same_year": cell_id in same_year_shared,
                    **{
                        f"records: {item['label']}": square.get(cell_id, {}).get("records", 0)
                        for item, square in zip(resolved, squares)
                    },
                    "value": min(
                        square.get(cell_id, {}).get("records", 0) for square in squares
                    ),
                })
                for cell_id in drawn if cell_id in geometry
            ],
        }
        subject_payloads = [{
            "type": "FeatureCollection",
            "features": [
                self._square_feature(cell_id, geometry[cell_id], {
                    "role": f"recorded: {item['label']}",
                    "subject": item["label"],
                    "value": cell["records"],
                    "records": cell["records"],
                    "years": (
                        f"{cell['first_year']}–{cell['last_year']}"
                        if cell["first_year"] else None
                    ),
                    "shared": cell_id in drawn,
                })
                for cell_id, cell in sorted(square.items()) if cell_id in geometry
            ],
        } for item, square in zip(resolved, squares)]

        shared_ref = self._data_ref("shared-squares", "application/geo+json", shared_payload)
        subject_refs = [
            self._data_ref(f"subject-{index + 1}-squares", "application/geo+json", payload)
            for index, payload in enumerate(subject_payloads)
        ]
        aoi_ref = self._data_ref("declared-aoi", "application/geo+json", aoi)
        rows_ref = self._data_ref("shared-square-records", "application/json", rows)
        tiles = [
            {"label": "Shared squares", "value": len(drawn), "unit": f"{size}s"},
            *[
                {"label": f"Squares with {item['label']}", "value": len(square),
                 "unit": f"{size}s"}
                for item, square in zip(resolved, squares)
            ],
            {"label": "Shared squares with same-year records", "value": len(same_year_shared),
             "unit": f"{size}s"},
        ]
        tiles_ref = self._data_ref("co-occurrence-tiles", "application/json", tiles)

        limitations = self._shared_limitations(
            size, labels, shared, same_year_shared, year_span, same_year
        )
        result["limitations"].extend(limitations)
        denominators = {
            "shared_squares": len(drawn),
            "shared_squares_any_year": len(shared),
            "shared_squares_same_year": len(same_year_shared),
            "squares_per_subject": {
                item["label"]: len(square) for item, square in zip(resolved, squares)
            },
            "records_per_subject_in_shared_squares": {
                item["label"]: sum(
                    square[cell]["records"] for cell in drawn if cell in square
                ) for item, square in zip(resolved, squares)
            },
            "drilldown_rows": len(rows),
        }
        result["visuals"] = [
            {
                "visual_id": "co-occurrence",
                "visual_type": "map",
                "view": "co-occurrence-map",
                "title": f"Squares holding records of {joined}",
                "priority": "primary",
                "status": "ready" if drawn else "partial",
                "scope": {"aoi_ids": ["target"], "time": {
                    "start": window[0], "end": window[1]}},
                # The shared squares come first and are the only filled layer: they are the
                # answer. Each subject's own squares follow as their own layer so a reader can
                # see which side of the overlap is thin, without two choropleths fighting.
                "layers": [
                    {
                        "layer_id": "shared-squares", "evidence_class": "derived",
                        "geometry_type": "cell", "data_ref": shared_ref,
                        "legend": {"label": f"Recorded together ({len(drawn)} {size}s)"},
                        "style_hint": {
                            "palette_role": "derived", "render": "fill",
                            "emphasis": "primary",
                        },
                    },
                    *[
                        {
                            "layer_id": f"subject-{index + 1}-squares",
                            "evidence_class": "observed",
                            "geometry_type": "cell", "data_ref": reference,
                            "legend": {
                                "label": f"{item['label']} recorded "
                                         f"({len(square)} {size}s)"
                            },
                            "style_hint": {
                                "palette_role": "observed", "render": "outline",
                                "emphasis": "supporting", "series": index + 1,
                            },
                        }
                        for index, (item, square, reference) in enumerate(
                            zip(resolved, squares, subject_refs)
                        )
                    ],
                    {
                        "layer_id": "declared-aoi", "evidence_class": "reported",
                        "geometry_type": "polygon", "data_ref": aoi_ref,
                        "legend": {"label": "This site's boundary"},
                        "style_hint": {"palette_role": "reported", "render": "outline"},
                    },
                ],
                "summary": {"headline": headline, "denominators": denominators},
                "drilldowns": [{
                    "action_id": "inspect-shared-square-records",
                    "label": "Inspect the records behind every shared square, by subject",
                    "data_ref": rows_ref,
                }],
                "limitations": limitations,
            },
            {
                "visual_id": "co-occurrence-summary",
                "visual_type": "metric",
                "view": "co-occurrence-summary",
                "title": "How much of each subject's range is shared?",
                "priority": "supporting",
                "status": "ready",
                "scope": {"aoi_ids": ["target"], "time": {
                    "start": window[0], "end": window[1]}},
                "layers": [{
                    "layer_id": "co-occurrence-tiles", "evidence_class": "derived",
                    "geometry_type": "table", "data_ref": tiles_ref,
                    "legend": {"label": "Squares per subject and shared"},
                    "style_hint": {"palette_role": "derived"},
                }],
                "summary": {"headline": headline, "denominators": {"tiles": len(tiles)}},
                "drilldowns": [],
                "limitations": limitations[:1],
            },
        ]
        if same_year_shared and not same_year and len(same_year_shared) != len(shared):
            result["actions"].append({
                "action_id": "restrict-to-same-year",
                "kind": "filter",
                "label": (
                    f"Show only the {len(same_year_shared)} squares where both were recorded "
                    "in the same year"
                ),
                "capability_id": "co-occurrence-map",
                "arguments": {"subjects": subjects, "same_year": True},
                "requires_confirmation": True,
            })
        for item in resolved:
            result["actions"].append({
                "action_id": f"profile-{_key(item['label']).replace(' ', '-')[:40]}",
                "kind": "run_capability",
                "label": f"What else is recorded for {item['label']}?",
                "capability_id": "entity-activity-profile",
                "arguments": (
                    {"entity": item["label"]} if item["kind"] == "entity"
                    else {"rank": item["rank"], "group": item["label"]}
                ),
                "requires_confirmation": True,
            })
        result["audit"]["co_occurrence"] = {
            "subjects": bindings["subjects"],
            "squares_per_subject": denominators["squares_per_subject"],
            "shared_squares_any_year": len(shared),
            "shared_squares_same_year": len(same_year_shared),
            "square_size": size,
            "same_year_only": bool(same_year and same_year_shared),
        }
        return self._write(result, {
            "declared-aoi": ("application/geo+json", aoi),
            "shared-squares": ("application/geo+json", shared_payload),
            **{
                f"subject-{index + 1}-squares": ("application/geo+json", payload)
                for index, payload in enumerate(subject_payloads)
            },
            "shared-square-records": ("application/json", rows),
            "co-occurrence-tiles": ("application/json", tiles),
        })

    @staticmethod
    def _window(time: Any) -> tuple[int | None, int | None]:
        if not isinstance(time, dict):
            return (None, None)
        def year(*keys: str) -> int | None:
            for key in keys:
                value = time.get(key)
                if value in (None, ""):
                    continue
                match = re.search(r"\d{4}", str(value))
                if match:
                    return int(match.group(0))
            return None
        return year("from", "start", "after"), year("to", "end", "before")

    def _year_span(
        self, connection: sqlite3.Connection, resolved: list[dict[str, Any]],
        window: tuple[int | None, int | None],
    ) -> str:
        clauses = []
        parameters: list[Any] = []
        for item in resolved:
            selector, selector_parameters = self._selector(item)
            if selector_parameters:
                clauses.append(selector)
                parameters.extend(selector_parameters)
        if not clauses:
            return ""
        row = connection.execute(
            f"SELECT MIN(year), MAX(year) FROM events WHERE {' OR '.join(clauses)}",
            parameters,
        ).fetchone()
        if not row or row[0] is None:
            return ""
        return f"{int(row[0])}" if row[0] == row[1] else f"{int(row[0])}–{int(row[1])}"

    def _shared_rows(
        self, connection: sqlite3.Connection, resolved: list[dict[str, Any]],
        shared: list[str], window: tuple[int | None, int | None],
    ) -> tuple[list[dict[str, Any]], set[str]]:
        """The actual rows behind every shared square, labelled by which subject they are."""
        rows: list[dict[str, Any]] = []
        sources: set[str] = set()
        if not shared:
            return rows, sources
        squares = ",".join("?" * len(shared))
        for item in resolved:
            selector, selector_parameters = self._selector(item, "e")
            if not selector_parameters:
                continue
            clauses = [selector, f"e.cell_id IN ({squares})"]
            parameters: list[Any] = [*selector_parameters, *shared]
            if window[0] is not None:
                clauses.append("e.year >= ?")
                parameters.append(window[0])
            if window[1] is not None:
                clauses.append("e.year <= ?")
                parameters.append(window[1])
            for row in connection.execute(
                f"""SELECT e.cell_id, e.event_id, e.source_id, e.source_row, e.event_date,
                           e.count_value,
                           COALESCE(en.display_name, e.event_type) AS subject_name
                    FROM events e LEFT JOIN entities en ON en.entity_id = e.entity_id
                    WHERE {' AND '.join(clauses)}
                    ORDER BY e.cell_id, e.event_date, e.source_id, e.source_row
                    LIMIT {MAX_DRILLDOWN_ROWS}""",
                parameters,
            ):
                sources.add(row["source_id"])
                rows.append({
                    "square": row["cell_id"],
                    "subject": item["label"],
                    "recorded_as": row["subject_name"],
                    "event_id": row["event_id"],
                    "source_id": row["source_id"],
                    "source_row": row["source_row"],
                    "event_date": row["event_date"],
                    "count": row["count_value"],
                })
        rows.sort(key=lambda item: (str(item["square"]), str(item["subject"])))
        return rows[:MAX_DRILLDOWN_ROWS], sources

    def _shared_limitations(
        self, size: str, labels: list[str], shared: list[str],
        same_year_shared: list[str], year_span: str, same_year: bool,
    ) -> list[dict[str, Any]]:
        """The caveats a shared-square map cannot be published without."""
        joined = " and ".join(labels)
        limitations = [
            self._limitation(
                "shared-square-is-not-interaction",
                (
                    f"A shared square means each of {joined} was written down inside the same "
                    f"{size}. It is not an interaction, an association or contact between them, "
                    "and it does not mean they were there at the same moment."
                ),
                severity="warning", affects=["answer", "shared-squares"],
            ),
            self._limitation(
                "different-surveys-and-effort",
                (
                    "The records can come from different surveys, different methods, different "
                    "amounts of survey work and different years. Where they overlap therefore "
                    "partly shows where people looked, not only where both were present."
                ),
                severity="warning", affects=["answer", "shared-squares"],
            ),
            self._limitation(
                "no-overlap-is-not-separation",
                (
                    "Squares with no overlap are not evidence that they keep apart. Nobody may "
                    "have recorded both there."
                ),
                severity="info", affects=["answer"],
            ),
        ]
        if shared:
            if same_year and same_year_shared:
                limitations.append(self._limitation(
                    "same-year-only",
                    (
                        f"This map shows only the {len(same_year_shared)} squares where the "
                        "records fall in the same year. Same year is still not the same day."
                    ),
                    severity="info", affects=["answer", "shared-squares"],
                ))
            else:
                limitations.append(self._limitation(
                    "records-not-contemporaneous",
                    (
                        f"This map shows squares where both were recorded at any time"
                        + (f" ({year_span})" if year_span else "")
                        + f". {len(same_year_shared)} of the {len(shared)} shared squares have "
                        "records from the same year; the rest pair up records from different "
                        "years."
                    ),
                    severity="warning", affects=["answer", "shared-squares"],
                ))
        return limitations

    def _unresolved(
        self, result_id: str, request_id: str, original: str, bindings: dict[str, Any],
        unresolved: list[dict[str, Any]], resolved: list[dict[str, Any]],
        connection: sqlite3.Connection,
    ) -> dict[str, Any]:
        names = ", ".join(f"“{item['requested']}”" for item in unresolved)
        result = self._base(
            result_id, request_id, "co-occurrence-map", original,
            "Resolve every subject before comparing where they were recorded.",
            bindings, f"No records here are filed under {names}.",
            ["missing"], "blocked", [],
        )
        result["limitations"].append(self._limitation(
            "unresolved-subject",
            (
                f"{names} did not match any name or group this site records. That is a naming "
                "gap, not evidence that it is absent from the area."
            ),
            severity="error", affects=["answer"],
        ))
        known = unresolved[0].get("known_here") or []
        if known:
            result["limitations"].append(self._limitation(
                "known-subjects",
                "Names this site does record include: " + ", ".join(known[:12]) + ".",
                severity="info", affects=["answer"],
            ))
        return self._write(result, {})

    # ------------------------------------------------------------------ activity profile

    def activity_profile(
        self, request_id: str, entity: Any = None, rank: str = "", group: str = "",
        question: str = "",
    ) -> dict[str, Any]:
        """Everything this site records for one subject, and who shares its squares."""
        subject_input: Any = (
            {"kind": "group", "rank": rank, "value": group} if group else entity
        )
        if not subject_input:
            raise ValueError("entity-activity-profile needs an entity, or a rank and group")
        request_id = _clean(request_id)[:200] or (
            "profile-" + _digest(subject_input).split(":", 1)[1][:12]
        )
        with self.connect() as connection:
            subject = self.resolve_subject(connection, subject_input)
            bindings = {
                "requested": subject["requested"], "kind": subject["kind"],
                "rank": subject["rank"], "label": subject["label"],
            }
            original = _clean(question) or f"What is recorded here for {subject['requested']}?"
            result_id = "result-prof-" + _digest(
                {"site": self.site.get("site_id"), "pack": self.pack_digest,
                 "request_id": request_id, **bindings}
            ).split(":", 1)[1][:20]
            if not subject["resolved"]:
                return self._unresolved(
                    result_id, request_id, original, bindings, [subject], [subject], connection
                )
            vocabulary = self._vocabulary(connection)
            selector, selector_parameters = self._selector(subject)
            aliased, _ = self._selector(subject, "e")
            kinds = [{
                "kind": humanise(row["event_type"], vocabulary),
                "records": int(row["records"]),
                "counted": row["total"],
                "years": (
                    f"{int(row['first_year'])}–{int(row['last_year'])}"
                    if row["first_year"] and row["last_year"] != row["first_year"]
                    else (str(int(row["first_year"])) if row["first_year"] else None)
                ),
                "squares": int(row["squares"]),
            } for row in connection.execute(
                f"""SELECT event_type, COUNT(*) AS records, COUNT(DISTINCT cell_id) AS squares,
                           SUM(count_value) AS total, MIN(year) AS first_year,
                           MAX(year) AS last_year
                    FROM events WHERE {selector}
                    GROUP BY event_type ORDER BY records DESC""",
                selector_parameters,
            )]
            surveys = [{
                "source": row["title"], "records": int(row["records"]),
            } for row in connection.execute(
                f"""SELECT s.title AS title, COUNT(*) AS records
                    FROM events e JOIN sources s ON s.source_id = e.source_id
                    WHERE {aliased}
                    GROUP BY s.title ORDER BY records DESC LIMIT 8""",
                selector_parameters,
            )]
            source_ids = {
                row[0] for row in connection.execute(
                    f"SELECT DISTINCT source_id FROM events WHERE {selector}",
                    selector_parameters,
                )
            }
            squares = self.subject_squares(connection, subject)
            cells = sorted(squares)
            measured = []
            if cells:
                placeholders = ",".join("?" * len(cells))
                measured = [{
                    "measured": (
                        row["label"] or humanise(row["metric"], vocabulary)
                    ),
                    "readings": int(row["readings"]),
                    "unit": row["unit"],
                } for row in connection.execute(
                    f"""SELECT m.metric AS metric, COUNT(*) AS readings,
                               MIN(d.label) AS label, MIN(m.unit) AS unit
                        FROM measurements m LEFT JOIN metric_definitions d ON d.metric = m.metric
                        WHERE m.cell_id IN ({placeholders}) AND m.value IS NOT NULL
                        GROUP BY m.metric ORDER BY readings DESC LIMIT 6""",
                    cells,
                )]
            partners = self._partners(connection, subject, squares)
            source_versions = self._source_versions(connection, source_ids)
            geometry = self._cell_geometry(connection, cells[:1])
        size = self._square_size(geometry)
        records = sum(item["records"] for item in kinds)
        years = [item["years"] for item in kinds if item["years"]]
        headline = (
            f"{records:,} records for {subject['label']}, in {len(squares):,} {size}s"
            + (f", {min(years)[:4]}–{max(years)[-4:]}" if years else "")
            + "."
        )
        result = self._base(
            result_id, request_id, "entity-activity-profile", original,
            f"Everything recorded for {subject['label']}, and which subjects share its squares.",
            bindings, headline, ["observed", "derived"], "complete", source_versions,
        )
        result["answer"]["detail"] = (
            "Kinds of record: "
            + "; ".join(f"{item['kind']} ({item['records']:,})" for item in kinds[:6])
            + ". Surveys: "
            + "; ".join(item["source"] for item in surveys[:4])
            + "."
        )
        profile_rows = [
            {"section": "Kind of record", "name": item["kind"], "records": item["records"],
             "detail": _clean(
                 f"{item['squares']} squares"
                 + (f", {item['years']}" if item["years"] else "")
                 + (f", {int(item['counted']):,} counted" if item["counted"] else "")
             )}
            for item in kinds
        ] + [
            {"section": "Survey", "name": item["source"], "records": item["records"],
             "detail": ""}
            for item in surveys
        ] + [
            {"section": "Measured where it was seen", "name": item["measured"],
             "records": item["readings"], "detail": _clean(item["unit"])}
            for item in measured
        ] + [
            {"section": "Shares squares with", "name": item["label"],
             "records": item["shared_squares"],
             "detail": f"{item['shared_squares']} shared {size}s"}
            for item in partners
        ]
        tiles = [
            {"label": "Records", "value": records, "unit": None},
            {"label": f"{size}s with records".capitalize(), "value": len(squares), "unit": None},
            {"label": "Kinds of record", "value": len(kinds), "unit": None},
            {"label": "Surveys", "value": len(surveys), "unit": None},
        ]
        profile_ref = self._data_ref("activity-profile", "application/json", profile_rows)
        tiles_ref = self._data_ref("activity-tiles", "application/json", tiles)
        limitations = [
            self._limitation(
                "records-not-abundance",
                (
                    f"These are records of {subject['label']}, not a count of how many there "
                    "are. More records can mean more survey work rather than more of them."
                ),
                severity="warning", affects=["answer"],
            ),
            self._limitation(
                "shared-square-is-not-interaction",
                (
                    f"\"Shares squares with\" means both were written down inside the same "
                    f"{size}. It is not an interaction, an association or contact, and the "
                    "records may be from different surveys and different years."
                ),
                severity="warning", affects=["answer", "activity-profile"],
            ),
        ]
        result["limitations"].extend(limitations)
        result["visuals"] = [{
            "visual_id": "activity-profile",
            "visual_type": "table",
            "view": "entity-activity-profile",
            "title": f"What this site records for {subject['label']}",
            "priority": "primary",
            "status": "ready",
            "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
            "layers": [{
                "layer_id": "activity-profile", "evidence_class": "derived",
                "geometry_type": "table", "data_ref": profile_ref,
                "legend": {"label": f"Records, surveys and shared squares for "
                                    f"{subject['label']}"},
                "style_hint": {"palette_role": "derived"},
            }],
            "summary": {
                "headline": headline,
                "denominators": {
                    "records": records, "squares": len(squares),
                    "kinds_of_record": len(kinds), "surveys": len(surveys),
                    "partners": len(partners),
                },
            },
            "drilldowns": [{
                "action_id": "inspect-activity-tiles",
                "label": "Inspect the headline counts",
                "data_ref": tiles_ref,
            }],
            "limitations": limitations,
        }]
        for partner in partners[:3]:
            result["actions"].append({
                "action_id": f"co-occurrence-with-{_key(partner['label']).replace(' ', '-')[:40]}",
                "kind": "run_capability",
                "label": f"Map the squares {subject['label']} shares with {partner['label']}",
                "capability_id": "co-occurrence-map",
                "arguments": {"subjects": [subject["label"], partner["label"]]},
                "requires_confirmation": True,
            })
        result["audit"]["activity_profile"] = {
            "subject": bindings, "records": records, "squares": len(squares),
            "kinds_of_record": [item["kind"] for item in kinds],
            "partners": [item["label"] for item in partners],
        }
        return self._write(result, {
            "activity-profile": ("application/json", profile_rows),
            "activity-tiles": ("application/json", tiles),
        })

    # ------------------------------------------------------------------ named pairs

    def named_pairs(
        self, interaction_type: str = "", entity: str = "", other: str = "",
        limit: int = 25,
    ) -> dict[str, Any]:
        """The recorded subject-object pairs, named and ranked. The pack's richest plane.

        The index holds thousands of rows saying which animal was recorded on which tree, and the
        answer to "which trees get their seed moved, and by whom" was "there are no recorded rows
        for seed movement itself". The relation totals were being relayed and the pairs underneath
        them never were, so the network was described as a shape — "37 things in 72 pairs" — and
        never named.
        """
        clauses: list[str] = []
        parameters: list[Any] = []
        with self.connect() as connection:
            if interaction_type:
                clauses.append("i.interaction_type = ?")
                parameters.append(interaction_type)
            for value, column in ((entity, "subject"), (other, "object")):
                if not value:
                    continue
                resolved = self.resolve_subject(connection, value)
                if resolved["entity_ids"]:
                    placeholders = ",".join("?" * len(resolved["entity_ids"]))
                    clauses.append(
                        f"(i.subject_entity_id IN ({placeholders}) "
                        f"OR i.object_entity_id IN ({placeholders}))"
                        if column == "subject" else
                        f"i.object_entity_id IN ({placeholders})"
                    )
                    parameters.extend(resolved["entity_ids"])
                    if column == "subject":
                        parameters.extend(resolved["entity_ids"])
            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
            rows = [dict(row) for row in connection.execute(
                f"""SELECT s.display_name AS subject, o.display_name AS object,
                           i.interaction_type AS interaction_type,
                           COUNT(*) AS records,
                           COALESCE(SUM(i.count_value), 0) AS counted,
                           COUNT(DISTINCT i.source_id) AS sources,
                           MIN(i.year) AS first_year, MAX(i.year) AS last_year,
                           GROUP_CONCAT(DISTINCT i.source_id) AS source_ids
                    FROM interactions i
                    JOIN entities s ON s.entity_id = i.subject_entity_id
                    JOIN entities o ON o.entity_id = i.object_entity_id{where}
                    GROUP BY s.display_name, o.display_name, i.interaction_type
                    ORDER BY records DESC, counted DESC, subject, object
                    LIMIT ?""",
                [*parameters, max(1, min(int(limit or 25), 60))],
            )]
            totals = connection.execute(
                f"""SELECT COUNT(*) AS rows_count,
                           COUNT(DISTINCT i.subject_entity_id || '|' || i.object_entity_id)
                             AS pairs,
                           COUNT(DISTINCT i.subject_entity_id) AS subjects,
                           COUNT(DISTINCT i.object_entity_id) AS objects
                    FROM interactions i{where}""",
                parameters,
            ).fetchone()
            titles = {
                row["source_id"]: row["title"] for row in connection.execute(
                    "SELECT source_id,title FROM sources"
                )
            }
        pairs = [{
            "subject": row["subject"],
            "object": row["object"],
            "relation": _clean(row["interaction_type"]).replace("_", " "),
            "records": int(row["records"]),
            "counted": (
                int(row["counted"]) if row["counted"] and float(row["counted"]).is_integer()
                else row["counted"] or None
            ),
            "years": (
                f"{int(row['first_year'])}–{int(row['last_year'])}"
                if row["first_year"] and row["last_year"] != row["first_year"]
                else (str(int(row["first_year"])) if row["first_year"] else None)
            ),
            "sources": [
                titles.get(item, item)
                for item in str(row["source_ids"] or "").split(",") if item
            ][:3],
        } for row in rows]
        return {
            "pairs": pairs,
            "totals": {
                "rows": int(totals["rows_count"] or 0),
                "named_pairs": int(totals["pairs"] or 0),
                "distinct_subjects": int(totals["subjects"] or 0),
                "distinct_objects": int(totals["objects"] or 0),
            },
        }

    def interaction_pairs_result(
        self, request_id: str, interaction_type: str = "", entity: str = "",
        other: str = "", limit: int = 25, question: str = "",
    ) -> dict[str, Any]:
        """One envelope naming the recorded pairs, with a network and a ranked table."""
        found = self.named_pairs(interaction_type, entity, other, limit)
        pairs, totals = found["pairs"], found["totals"]
        request_id = _clean(request_id)[:200] or "pairs-" + _digest(found).split(":", 1)[1][:12]
        bindings = {
            "interaction_type": interaction_type or None, "entity": entity or None,
            "object": other or None, "limit": limit,
        }
        original = _clean(question) or "Which things were recorded with which, and how often?"
        result_id = "result-pairs-" + _digest({
            "site": self.site.get("site_id"), "pack": self.pack_digest,
            "request_id": request_id, **bindings,
        }).split(":", 1)[1][:20]
        with self.connect() as connection:
            source_ids = {
                row[0] for row in connection.execute(
                    "SELECT DISTINCT source_id FROM interactions"
                )
            }
            source_versions = self._source_versions(connection, source_ids)
        if not pairs:
            result = self._base(
                result_id, request_id, "interaction-pairs", original,
                "Name the recorded subject-object pairs.", bindings,
                "No recorded pairs match that request.", ["missing"], "blocked", source_versions,
            )
            result["limitations"].append(self._limitation(
                "no-pairs-recorded",
                (
                    "No stored row pairs those two together. That is a gap in what was written "
                    "down, not evidence that it does not happen."
                ),
                severity="error", affects=["answer"],
            ))
            return self._write(result, {})

        top = pairs[0]
        headline = (
            f"{totals['named_pairs']:,} named pairs recorded, across "
            f"{totals['rows']:,} rows. The most recorded is {top['subject']} with "
            f"{top['object']} ({top['records']:,} records)."
        )
        result = self._base(
            result_id, request_id, "interaction-pairs", original,
            "Recorded subject-object pairs, ranked by how often each was written down.",
            bindings, headline, ["observed"], "complete", source_versions,
        )
        result["answer"]["detail"] = "; ".join(
            f"{item['subject']} with {item['object']} ({item['records']:,})"
            for item in pairs[:6]
        ) + "."
        network = {
            "nodes": sorted(
                {item["subject"] for item in pairs} | {item["object"] for item in pairs}
            ),
            "edges": [{
                "source": item["subject"], "target": item["object"],
                "relation": item["relation"], "weight": item["records"],
            } for item in pairs],
        }
        pairs_ref = self._data_ref("interaction-pairs", "application/json", pairs)
        network_ref = self._data_ref("interaction-network", "application/json", network)
        limitations = [
            self._limitation(
                "recorded-not-demonstrated",
                (
                    "Each pair is what a source wrote down — an animal seen at or on a plant, or "
                    "detected at an experiment. It is a record of being seen together, not proof "
                    "that seed was moved, eaten or dispersed."
                ),
                severity="warning", affects=["answer", "interaction-pairs"],
            ),
            self._limitation(
                "ranked-by-recording",
                (
                    "The ranking is by how often each pair was recorded, which follows watching "
                    "effort as well as behaviour: a heavily watched tree will out-rank a rarely "
                    "visited one."
                ),
                severity="warning", affects=["interaction-pairs"],
            ),
        ]
        result["limitations"].extend(limitations)
        result["visuals"] = [
            {
                "visual_id": "interaction-pairs",
                "visual_type": "table",
                "view": "interaction-pairs",
                "title": "Who was recorded with what, most recorded first",
                "priority": "primary",
                "status": "ready",
                "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
                "layers": [{
                    "layer_id": "interaction-pairs", "evidence_class": "observed",
                    "geometry_type": "table", "data_ref": pairs_ref,
                    "legend": {"label": f"{len(pairs)} named pairs"},
                    "style_hint": {"palette_role": "observed"},
                }],
                "summary": {
                    "headline": headline,
                    "denominators": {
                        "pairs_shown": len(pairs), "named_pairs": totals["named_pairs"],
                        "rows": totals["rows"], "subjects": totals["distinct_subjects"],
                        "objects": totals["distinct_objects"],
                    },
                },
                "drilldowns": [],
                "limitations": limitations,
            },
            {
                "visual_id": "interaction-network",
                "visual_type": "network",
                "view": "interaction-network",
                "title": "The recorded network",
                "priority": "supporting",
                "status": "ready",
                "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
                "layers": [{
                    "layer_id": "interaction-network", "evidence_class": "observed",
                    "geometry_type": "graph", "data_ref": network_ref,
                    "legend": {"label": "Recorded together"},
                    "style_hint": {"palette_role": "observed"},
                }],
                "summary": {
                    "headline": headline,
                    "denominators": {
                        "nodes": len(network["nodes"]), "edges": len(network["edges"]),
                    },
                },
                "drilldowns": [],
                "limitations": limitations[:1],
            },
        ]
        for item in pairs[:3]:
            result["actions"].append({
                "action_id": f"map-{_key(item['object']).replace(' ', '-')[:40]}",
                "kind": "run_capability",
                "label": f"Map where {item['object']} is recorded",
                "capability_id": "entity-record-map",
                "arguments": {"entity": item["object"]},
                "requires_confirmation": True,
            })
        result["audit"]["interaction_pairs"] = {
            "totals": totals, "pairs_shown": len(pairs), "bindings": bindings,
        }
        return self._write(result, {
            "interaction-pairs": ("application/json", pairs),
            "interaction-network": ("application/json", network),
        })

    def _partners(
        self, connection: sqlite3.Connection, subject: dict[str, Any],
        squares: dict[str, dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """The subjects sharing the most squares with this one — the same engine, top five."""
        if not squares:
            return []
        cells = ",".join("?" * len(squares))
        excluded, excluded_parameters = self._selector(subject, "e")
        rows = connection.execute(
            f"""SELECT en.display_name AS label, COUNT(DISTINCT e.cell_id) AS shared,
                       COUNT(*) AS records
                FROM events e JOIN entities en ON en.entity_id = e.entity_id
                WHERE e.cell_id IN ({cells}) AND NOT ({excluded})
                GROUP BY en.display_name
                ORDER BY shared DESC, records DESC, label
                LIMIT {MAX_PROFILE_PARTNERS}""",
            [*squares, *excluded_parameters],
        )
        return [{
            "label": row["label"], "shared_squares": int(row["shared"]),
            "records": int(row["records"]),
        } for row in rows]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--subject", action="append", default=[])
    parser.add_argument("--profile")
    parser.add_argument("--same-year", action="store_true")
    args = parser.parse_args(argv)
    service = CooccurrenceService(args.site_pack, args.index, args.state)
    if args.profile:
        envelope = service.activity_profile("cli", entity=args.profile)
    else:
        envelope = service.co_occurrence_map("cli", args.subject, same_year=args.same_year)
    print(json.dumps(envelope, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
