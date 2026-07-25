#!/usr/bin/env python3
"""Where should the next survey go — ranked by what we do not know, not by what we already have.

Asked to rank the top five places to send survey effort, the assistant argued coverage-gap logic
for six turns ("records exist in 302 squares but effort is documented in only 42; prioritise
squares with records and little effort") and then ranked by record density — the exact inverse —
and said so in the same breath. It also named the squares by latitude band. No ecologist puts
"10.340–10.350 N, 76.890–76.900 E" in a proposal, and this pack holds 205 named places.

So the ranking is computed here rather than left to prose. A square scores on the gap between how
much is recorded in it and how much documented effort stands behind that recording, with the
squares nobody has ever worked in ranked as unknown rather than as empty. Each one is resolved to
the nearest named place the pack itself holds, with the distance, so the answer reads as a place a
person can drive to.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sqlite3
from typing import Any

try:
    from dss.visual_index.cell_language import describe_box
    from dss.visual_index.result_service import (
        _atomic_write_once, _digest, _load_json, _stable_json,
    )
except ModuleNotFoundError:  # Direct execution
    from cell_language import describe_box  # type: ignore[no-redef]
    from result_service import (  # type: ignore[no-redef]
        _atomic_write_once, _digest, _load_json, _stable_json,
    )


KM_PER_DEGREE = 110.574

SURVEY_PRIORITY_CAPABILITIES: list[dict[str, Any]] = [
    {
        "capability_id": "survey-priority-squares",
        "version": "1.0.0",
        "label": "Rank where to survey next by the gap between records and documented effort",
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 25},
                "scope": {"type": "string", "enum": ["target", "all_indexed"]},
            },
            "required": [],
        },
        "output_views": ["survey-priority-map", "survey-priority-table"],
        "required_planes": ["cells", "events"],
        "optional_planes": ["effort", "locations"],
        "latency_class": "interactive",
        "evidence_classes": ["derived"],
        "availability": "ready",
        "scope": "site",
        "reason": (
            "Ranks by missing information, not by record count. It is a statement about where "
            "this pack is thin, never about where the ecology is richest."
        ),
    },
]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


class SurveyPriorityService:
    """Rank squares by how little is known about them, and name them as places."""

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

    @classmethod
    def from_result_service(cls, service: Any) -> "SurveyPriorityService":
        return cls(service.site_pack, service.index_path, service.state_root)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    def places(self, connection: sqlite3.Connection) -> list[dict[str, Any]]:
        """Every named place this pack holds a coordinate for — all of them, not a sample."""
        seen: set[str] = set()
        found: list[dict[str, Any]] = []
        for row in connection.execute(
            """SELECT label, latitude, longitude FROM locations
               WHERE latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY label"""
        ):
            name = _clean(row["label"]).replace("(synthetic)", "").strip()
            if not name or name.casefold() in seen:
                continue
            seen.add(name.casefold())
            found.append({
                "name": name, "lat": float(row["latitude"]), "lon": float(row["longitude"]),
            })
        return found

    @staticmethod
    def nearest_place(
        places: list[dict[str, Any]], lat: float, lon: float
    ) -> dict[str, Any] | None:
        """The named place closest to a square's middle, with how far away it is."""
        if not places:
            return None
        scale = max(math.cos(math.radians(lat)), 0.01)
        best = min(
            places,
            key=lambda place: math.hypot(
                (place["lon"] - lon) * scale, place["lat"] - lat
            ),
        )
        distance = math.hypot(
            (best["lon"] - lon) * scale, best["lat"] - lat
        ) * KM_PER_DEGREE
        return {"name": best["name"], "km": round(distance, 1)}

    def rank(self, limit: int = 5, scope: str = "target") -> dict[str, Any]:
        """Squares ranked by how much is recorded with how little effort behind it."""
        with self.connect() as connection:
            places = self.places(connection)
            clause = "WHERE c.target_role = 'target'" if scope == "target" else ""
            rows = [dict(row) for row in connection.execute(
                f"""SELECT c.cell_id AS cell_id, c.west, c.south, c.east, c.north,
                           c.center_lat AS lat, c.center_lon AS lon,
                           COALESCE(e.records, 0) AS records,
                           COALESCE(e.entities, 0) AS entities,
                           COALESCE(f.effort_rows, 0) AS effort_rows,
                           COALESCE(f.effort_value, 0) AS effort_value,
                           e.last_year AS last_year
                    FROM cells c
                    LEFT JOIN (
                        SELECT cell_id, COUNT(*) AS records,
                               COUNT(DISTINCT entity_id) AS entities, MAX(year) AS last_year
                        FROM events WHERE cell_id IS NOT NULL GROUP BY cell_id
                    ) e ON e.cell_id = c.cell_id
                    LEFT JOIN (
                        SELECT cell_id, COUNT(*) AS effort_rows,
                               COALESCE(SUM(effort_value),0) AS effort_value
                        FROM effort WHERE cell_id IS NOT NULL GROUP BY cell_id
                    ) f ON f.cell_id = c.cell_id
                    {clause}"""
            )]
            source_ids = {
                row[0] for row in connection.execute("SELECT DISTINCT source_id FROM events")
            }
        if not rows:
            return {"ranked": [], "totals": {}, "places": len(places)}

        busiest = max((row["records"] for row in rows), default=0) or 1
        scored = []
        for row in rows:
            records = int(row["records"])
            effort_rows = int(row["effort_rows"])
            # Records already collected with no documented effort behind them are the strongest
            # signal: something is there, and nobody can say how hard anyone looked. A square
            # with no records and no effort is unknown, which is a weaker but real claim.
            if effort_rows:
                gap = records / (1.0 + float(row["effort_value"] or 0.0))
                reason = "records here, but the survey work behind them is thinly documented"
                kind = "under-documented"
            elif records:
                gap = 1.5 * (records / busiest) + 1.0
                reason = "records here with no documented survey work at all behind them"
                kind = "no-effort-recorded"
            else:
                gap = 0.5
                reason = "nothing recorded here yet, so nothing is known either way"
                kind = "never-surveyed"
            extent = describe_box(row["west"], row["south"], row["east"], row["north"])
            scored.append({
                "cell_id": row["cell_id"],
                "square": extent["short_phrase"],
                "place": self.nearest_place(places, float(row["lat"]), float(row["lon"])),
                "records": records,
                "distinct_subjects": int(row["entities"]),
                "documented_effort_rows": effort_rows,
                "last_recorded_year": row["last_year"],
                "gap_score": round(gap, 4),
                "gap_kind": kind,
                "why": reason,
                "bounds": extent["bounds"],
            })
        scored.sort(key=lambda item: (-item["gap_score"], -item["records"], item["cell_id"]))
        ranked = scored[:max(1, min(int(limit or 5), 25))]
        for position, item in enumerate(ranked, 1):
            place = item["place"]
            where = (
                f"near {place['name']} ({place['km']} km away)" if place else item["square"]
            )
            item["rank"] = position
            item["headline"] = (
                f"{position}. {where} — {item['records']:,} records, "
                + (
                    f"{item['documented_effort_rows']} row"
                    + ("s" if item["documented_effort_rows"] != 1 else "")
                    + " of documented survey work"
                    if item["documented_effort_rows"] else "no documented survey work"
                )
                + f": {item['why']}."
            )
        return {
            "ranked": ranked,
            "totals": {
                "squares": len(rows),
                "squares_with_records": sum(1 for row in rows if row["records"]),
                "squares_with_documented_effort": sum(
                    1 for row in rows if row["effort_rows"]
                ),
                "named_places_available": len(places),
                "sources": len(source_ids),
            },
            "method": (
                "Ranked by the gap between what is recorded and how much documented survey work "
                "stands behind it, so the top of this list is where the pack is least able to "
                "say what is there. It is not a ranking of ecological importance."
            ),
        }


    def rank_result(
        self, request_id: str, limit: int = 5, scope: str = "target", question: str = "",
    ) -> dict[str, Any]:
        """The same ranking as one idli-result/1 envelope: a gap map and a ranked table."""
        ranked = self.rank(limit, scope)
        rows, totals = ranked["ranked"], ranked["totals"]
        bindings = {"limit": limit, "scope": scope}
        request_id = _clean(request_id)[:200] or "priority-" + _digest(bindings).split(
            ":", 1)[1][:12]
        result_id = "result-gap-" + _digest({
            "site": self.site.get("site_id"), "pack": self.pack_digest,
            "request_id": request_id, **bindings,
        }).split(":", 1)[1][:20]
        original = _clean(question) or "Where should the next survey go?"
        site = {
            "site_id": self.site.get("site_id"), "label": self.site.get("label"),
            "pack_digest": self.pack_digest,
        }
        if self.synthetic:
            site["synthetic"] = True
        limitations = [{
            "code": "ranked-by-missing-information", "severity": "warning",
            "message": (
                "This ranks where this site's data is thinnest — where a survey would tell us "
                "most — and NOT where the ecology is richest. A square near the top may be "
                "ordinary ground that nobody has documented properly."
            ),
            "affects": ["answer", "survey-priority"], "details_ref": None,
        }, {
            "code": "effort-recording-is-uneven", "severity": "info",
            "message": (
                "Documented survey work is itself patchily recorded: a square can have been "
                "walked without anyone writing down the effort. Missing effort means missing "
                "paperwork as often as it means missing fieldwork."
            ),
            "affects": ["answer"], "details_ref": None,
        }]
        headline = (
            f"{totals.get('squares_with_records', 0):,} squares hold records but only "
            f"{totals.get('squares_with_documented_effort', 0):,} have documented survey work. "
            + (f"The widest gap is {rows[0]['place']['name']}." if rows and rows[0].get("place")
               else "")
        ).strip()
        features = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "id": item["cell_id"],
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[
                        [item["bounds"]["west"], item["bounds"]["south"]],
                        [item["bounds"]["east"], item["bounds"]["south"]],
                        [item["bounds"]["east"], item["bounds"]["north"]],
                        [item["bounds"]["west"], item["bounds"]["north"]],
                        [item["bounds"]["west"], item["bounds"]["south"]],
                    ]],
                },
                "properties": {
                    "rank": item["rank"],
                    "place": (item["place"] or {}).get("name"),
                    "value": item["gap_score"],
                    "records": item["records"],
                    "documented_effort_rows": item["documented_effort_rows"],
                    "why": item["why"],
                },
            } for item in rows],
        }
        table = [{
            "rank": item["rank"], "place": (item["place"] or {}).get("name") or item["square"],
            "records": item["records"],
            "documented_effort_rows": item["documented_effort_rows"],
            "why": item["why"],
        } for item in rows]
        map_ref = {
            "kind": "result_data", "handle": "survey-priority",
            "media_type": "application/geo+json", "digest": _digest(features),
        }
        table_ref = {
            "kind": "result_data", "handle": "survey-priority-table",
            "media_type": "application/json", "digest": _digest(table),
        }
        result = {
            "schema_version": "idli-result/1",
            "result_id": result_id,
            "request_id": request_id,
            "revision": 1,
            "status": "complete" if rows else "partial",
            "site": site,
            "question": {
                "original": original,
                "resolved": (
                    "Squares ranked by the gap between what is recorded and how much documented "
                    "survey work stands behind it, each named by its nearest recorded place."
                ),
                "bindings": bindings,
            },
            "answer": {
                "headline": headline,
                "detail": " ".join(item["headline"] for item in rows),
                "evidence_classes": ["derived"],
            },
            "visuals": [{
                "visual_id": "survey-priority",
                "visual_type": "map",
                "view": "survey-priority-map",
                "title": "Where a survey would tell us most",
                "priority": "primary",
                "status": "ready" if rows else "partial",
                "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
                "layers": [{
                    "layer_id": "survey-priority", "evidence_class": "derived",
                    "geometry_type": "cell", "data_ref": map_ref,
                    "legend": {"label": "Widest gap first"},
                    "style_hint": {"palette_role": "derived", "render": "fill"},
                }, {
                    "layer_id": "survey-priority-table", "evidence_class": "derived",
                    "geometry_type": "table", "data_ref": table_ref,
                    "legend": {"label": "Ranked places"},
                    "style_hint": {"palette_role": "derived"},
                }],
                "summary": {"headline": headline, "denominators": totals},
                "drilldowns": [],
                "limitations": limitations,
            }],
            "limitations": limitations,
            "actions": [{
                "action_id": "map-coverage-versus-effort",
                "kind": "run_capability",
                "label": "Show the whole coverage-versus-effort map behind this ranking",
                "capability_id": "coverage-versus-effort",
                "arguments": {},
                "requires_confirmation": True,
            }],
            "audit": {
                "audit_id": f"{result_id}/1",
                "source_versions": [],
                "capability_runs": [{
                    "capability_id": "survey-priority-squares", "version": "1.0.0",
                    "status": "complete" if rows else "partial",
                }],
                "query_hash": _digest(bindings),
                "assurance": "derived",
                "survey_priority": {"ranked": rows, "totals": totals, "method": ranked["method"]},
            },
        }
        root = self.state_root / "results" / result_id
        _atomic_write_once(root / "data" / "survey-priority.geojson", _stable_json(features).encode())
        _atomic_write_once(
            root / "data" / "survey-priority-table.json", _stable_json(table).encode())
        _atomic_write_once(
            root / "result.json",
            (json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n").encode(),
        )
        return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
    args = parser.parse_args(argv)
    service = SurveyPriorityService(args.site_pack, args.index, args.state)
    print(json.dumps(service.rank(args.limit), indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
