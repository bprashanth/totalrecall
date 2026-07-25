#!/usr/bin/env python3
"""Enumerate every quantity this pinned index can actually be asked to estimate.

A user does not speak the index's vocabulary. They ask about "jobs", "income", "kids in
school". The index carries `event_type=mgnrega_work` with a `persondays` count, an estate
census counting `worker_count`, out-migration counting `persons_moved`. Nothing here tries to
bridge that gap, and that is the point: the mapping from a person's word to a stored quantity
is interpretation, and interpretation belongs to the model, out loud, in front of the user.

So this module does exactly one thing: it reads the pinned index and the pack's declared
adapters and lists what exists — per event type, per measured metric, per effort method, plus
the whole-cell quantities (record density, entity richness, effort-normalised rate) the
estimator has always carried. Every entry states the raw column the pack counts, the unit that
column is in, how many cells carry a value, which sources it comes from and which record labels
appear in it. There is no keyword matching in this file, no synonym table, no scoring of a
user's phrase against a label. A caller that passes a word this catalogue does not list is told
what the catalogue does list, and is expected to choose.

The estimator then accepts only a `target_id` printed here, so the deterministic layer stays
deterministic: the model may interpret, but it interprets *into* a fixed vocabulary, and the
number that comes back is bound to the id it named.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sqlite3
from typing import Any

try:
    from dss.visual_index.result_service import _load_json
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/target_catalogue.py
    from result_service import _load_json  # type: ignore[no-redef]


CATALOGUE_VERSION = "idli-estimate-targets/1"

TARGET_CATALOGUE_CAPABILITIES: list[dict[str, Any]] = [
    {
        "capability_id": "cell-estimate-targets",
        "version": "1.0.0",
        "label": "List every quantity this pack's index can be asked to estimate for a cell",
        "input_schema": {"type": "object", "properties": {}, "required": []},
        "output_views": ["estimate-target-catalogue"],
        "required_planes": ["cells"],
        "optional_planes": ["events", "effort", "measurements", "entities"],
        "latency_class": "interactive",
        "evidence_classes": ["derived"],
        "availability": "ready",
        "scope": "site",
        "reason": (
            "Enumeration only: it reads the index and lists what exists. It never matches a "
            "user's words against a label and never returns an estimate."
        ),
    },
]

# The whole-cell quantities the estimator has always supported. They are not tied to one event
# type or one metric, so they cannot be discovered from the index the way the others are.
GENERIC_TARGETS: list[dict[str, Any]] = [
    {
        "target_id": "record_density",
        "family": "record_density",
        "label": "how many records of any kind the square holds",
        "unit": "records per map square",
        "counts": {
            "column": None,
            "aggregation": "number of records whose location falls inside the square",
        },
        "planes": ["events", "cells"],
    },
    {
        "target_id": "entity_richness",
        "family": "entity_richness",
        "label": "how many different things the square's records are about",
        "unit": "distinct subjects per map square",
        "counts": {
            "column": None,
            "aggregation": "number of distinct subjects appearing in the square's records",
        },
        "planes": ["events", "entities", "cells"],
    },
    {
        "target_id": "survey_effort",
        "family": "survey_effort",
        "label": "how much survey work is documented in the square",
        "unit": "summed effort units per map square",
        "counts": {
            "column": "effort_value",
            "aggregation": "sum of the documented survey work recorded in the square",
        },
        "planes": ["effort", "cells"],
    },
    {
        "target_id": "effort_normalised_rate",
        "family": "effort_normalised_rate",
        "label": "records per 100 units of documented survey work",
        "unit": "records per 100 effort units",
        "counts": {
            "column": None,
            "aggregation": "records divided by documented survey work, times 100",
        },
        "planes": ["events", "effort", "cells"],
    },
]


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _years(low: Any, high: Any) -> str | None:
    if low in (None, "") or high in (None, ""):
        return None
    return f"{int(low)}" if int(low) == int(high) else f"{int(low)}–{int(high)}"


def event_count_columns(site_pack: pathlib.Path) -> dict[str, str]:
    """Per source, the raw column the pack declared as its event count.

    This is the pack's own word for what a count means — `persondays`, `worker_count`,
    `persons_moved` — carried through from `sources.json` verbatim. It is the single most
    useful thing a caller can be told about an event type, and it is a declaration, not an
    inference.
    """
    columns: dict[str, str] = {}
    registry: dict[str, Any] = {}
    try:
        registry = _load_json(site_pack / "sources.json")
    except (OSError, ValueError, TypeError):
        return columns
    for source in registry.get("sources") or []:
        if not isinstance(source, dict):
            continue
        source_id = _clean(source.get("source_id"))
        for adapter in source.get("adapters") or []:
            if not isinstance(adapter, dict) or adapter.get("kind") != "event":
                continue
            column = _clean(adapter.get("count"))
            if source_id and column:
                columns.setdefault(source_id, column)
    return columns


def named_places(connection: sqlite3.Connection, limit: int = 40) -> list[dict[str, Any]]:
    """Every named place this index carries a coordinate for, deduplicated by name.

    This exists so nobody ever has to ask a user to type `at:<lat>:<lon>`. When a person says
    "the square just below Kadamparai", the name is already in the index with a point on it; the
    caller resolves it and moves on. Names are returned as stored, minus the pack's own
    "(synthetic)" suffix, which is a property of the test data and not part of the place's name.
    """
    places: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in connection.execute(
        """SELECT label,latitude,longitude,location_id,source_id FROM locations
           WHERE latitude IS NOT NULL AND longitude IS NOT NULL
           ORDER BY label,location_id"""
    ):
        name = _clean(row["label"]).replace("(synthetic)", "").strip()
        key = name.casefold()
        if not name or key in seen:
            continue
        seen.add(key)
        places.append({
            "name": name,
            "lat": round(float(row["latitude"]), 6),
            "lon": round(float(row["longitude"]), 6),
            "location_id": row["location_id"],
            "source_id": row["source_id"],
        })
        if len(places) >= limit:
            break
    return places


def capability_vocabulary(connection: sqlite3.Connection) -> dict[str, Any]:
    """The values this index will actually accept for the capabilities' declared arguments.

    A capability list that says `stratified-survey-summary` takes `source_id` and
    `category_property` tells a caller the shape of the call and nothing about which call to
    make. So a question like "which village has the most survey visits?" bounced off the
    orientation map — the data was there, the argument values were not. This enumerates them from
    the index: the metrics that can be plotted, the subjects that can be mapped, the hierarchy
    ranks and groups that exist, and, per source, the row properties that can be summarised as
    categories. It matches nothing against anybody's words; it lists what would resolve.
    """
    metrics = [{
        "metric": row["metric"], "label": row["label"], "unit": row["unit"],
    } for row in connection.execute(
        """SELECT m.metric AS metric, COALESCE(d.label, m.metric) AS label,
                  COALESCE(d.unit, m.unit) AS unit
           FROM (SELECT DISTINCT metric, unit FROM measurements WHERE value IS NOT NULL) m
           LEFT JOIN metric_definitions d ON d.metric = m.metric
           ORDER BY m.metric"""
    )]
    subjects = [{
        "entity": row["display_name"], "records": int(row["records"]),
    } for row in connection.execute(
        """SELECT en.display_name AS display_name, COUNT(*) AS records
           FROM events e JOIN entities en ON en.entity_id = e.entity_id
           GROUP BY en.display_name ORDER BY records DESC, display_name LIMIT 12"""
    )]
    ranks: dict[str, set[str]] = {}
    for row in connection.execute("SELECT hierarchy_json FROM entities"):
        try:
            hierarchy = json.loads(row[0] or "{}")
        except (TypeError, ValueError):
            continue
        for rank, group in (hierarchy or {}).items():
            if isinstance(group, str) and group:
                ranks.setdefault(str(rank), set()).add(group)
    categories: dict[str, set[str]] = {}
    for table in ("events", "effort"):
        for row in connection.execute(
            f"SELECT source_id, properties_json FROM {table}"
        ):
            try:
                properties = json.loads(row["properties_json"] or "{}")
            except (TypeError, ValueError):
                continue
            for key, value in (properties or {}).items():
                if isinstance(value, (str, int, float)) and str(value):
                    categories.setdefault(row["source_id"], set()).add(str(key))
    return {
        "metrics": metrics,
        "subjects": subjects,
        "hierarchy": [
            {"rank": rank, "groups": sorted(groups)[:8]}
            for rank, groups in sorted(ranks.items()) if groups
        ][:8],
        "event_types": [
            row[0] for row in connection.execute(
                "SELECT DISTINCT event_type FROM events ORDER BY event_type"
            )
        ][:12],
        "effort_methods": [
            row[0] for row in connection.execute(
                "SELECT DISTINCT method FROM effort ORDER BY method"
            )
        ][:8],
        "sources": [
            {"source_id": source_id, "category_properties": sorted(keys)[:10]}
            for source_id, keys in sorted(categories.items())
        ][:12],
    }


def _source_titles(connection: sqlite3.Connection) -> dict[str, str]:
    return {
        row["source_id"]: row["title"]
        for row in connection.execute("SELECT source_id,title FROM sources")
    }


def _event_groups(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Per event type: how much of it there is, where, from whom, in what years."""
    groups: dict[str, dict[str, Any]] = {}
    for row in connection.execute(
        """SELECT event_type,
                  COUNT(*) AS records,
                  COUNT(count_value) AS valued,
                  COALESCE(SUM(count_value),0) AS total,
                  COUNT(DISTINCT cell_id) AS cells,
                  COUNT(DISTINCT entity_id) AS entities,
                  MIN(year) AS first_year, MAX(year) AS last_year
           FROM events WHERE cell_id IS NOT NULL GROUP BY event_type ORDER BY event_type"""
    ):
        groups[row["event_type"]] = {
            "records": int(row["records"]),
            "valued": int(row["valued"]),
            "total": float(row["total"]),
            "cells": int(row["cells"]),
            "entities": int(row["entities"]),
            "first_year": row["first_year"],
            "last_year": row["last_year"],
            "sources": [],
            "labels": [],
        }
    for row in connection.execute(
        """SELECT event_type,source_id,COUNT(*) AS records FROM events
           WHERE cell_id IS NOT NULL GROUP BY event_type,source_id
           ORDER BY event_type,records DESC,source_id"""
    ):
        if row["event_type"] in groups:
            groups[row["event_type"]]["sources"].append(
                {"source_id": row["source_id"], "records": int(row["records"])}
            )
    for row in connection.execute(
        """SELECT events.event_type AS event_type, entities.display_name AS display_name,
                  COUNT(*) AS records
           FROM events JOIN entities ON entities.entity_id = events.entity_id
           WHERE events.cell_id IS NOT NULL
           GROUP BY events.event_type, entities.display_name
           ORDER BY events.event_type, records DESC, display_name"""
    ):
        bucket = groups.get(row["event_type"])
        if bucket is not None and len(bucket["labels"]) < 8:
            bucket["labels"].append(row["display_name"])
    return groups


def _metric_groups(connection: sqlite3.Connection) -> dict[str, dict[str, Any]]:
    """Per measured metric: its declared label and unit, and where values land."""
    definitions: dict[str, dict[str, Any]] = {}
    for row in connection.execute(
        "SELECT metric,label,unit,description,source_id FROM metric_definitions"
    ):
        definitions.setdefault(row["metric"], {
            "label": row["label"], "unit": row["unit"],
            "description": row["description"], "source_id": row["source_id"],
        })
    groups: dict[str, dict[str, Any]] = {}
    for row in connection.execute(
        """SELECT metric, COUNT(*) AS rows_count, COUNT(DISTINCT cell_id) AS cells,
                  MIN(value) AS low, MAX(value) AS high,
                  MIN(year) AS first_year, MAX(year) AS last_year, unit
           FROM measurements WHERE cell_id IS NOT NULL AND value IS NOT NULL
           GROUP BY metric ORDER BY metric"""
    ):
        declared = definitions.get(row["metric"], {})
        groups[row["metric"]] = {
            "rows": int(row["rows_count"]),
            "cells": int(row["cells"]),
            "low": row["low"], "high": row["high"],
            "first_year": row["first_year"], "last_year": row["last_year"],
            "unit": declared.get("unit") or row["unit"] or "",
            "label": declared.get("label") or row["metric"],
            "description": declared.get("description"),
            "sources": [],
        }
    for row in connection.execute(
        """SELECT metric,source_id,COUNT(*) AS rows_count FROM measurements
           WHERE cell_id IS NOT NULL GROUP BY metric,source_id
           ORDER BY metric,rows_count DESC,source_id"""
    ):
        if row["metric"] in groups:
            groups[row["metric"]]["sources"].append(
                {"source_id": row["source_id"], "records": int(row["rows_count"])}
            )
    return groups


def _effort_groups(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    return [{
        "method": row["method"],
        "unit": row["effort_unit"] or "",
        "rows": int(row["rows_count"]),
        "cells": int(row["cells"]),
        "total": float(row["total"]),
        "source_id": row["source_id"],
    } for row in connection.execute(
        """SELECT method,effort_unit,source_id,COUNT(*) AS rows_count,
                  COUNT(DISTINCT cell_id) AS cells, COALESCE(SUM(effort_value),0) AS total
           FROM effort WHERE cell_id IS NOT NULL
           GROUP BY method,effort_unit,source_id ORDER BY method,source_id"""
    )]


def _entry(
    target_id: str, family: str, label: str, unit: str, counts: dict[str, Any],
    planes: list[str], coverage: dict[str, Any], sources: list[dict[str, Any]],
    minimum_cells: int, record_labels: list[str] | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    cells = int(coverage.get("cells_with_a_value") or 0)
    entry = {
        "target_id": target_id,
        "family": family,
        "label": label,
        "unit": unit,
        "counts": counts,
        "planes": planes,
        "coverage": coverage,
        "sources": sources,
        "record_labels": record_labels or [],
        # Deterministic feasibility, stated as arithmetic rather than as a promise. A target
        # with too few surveyed cells is still listed: knowing the pack cannot support it is an
        # answer, and hiding it would make the catalogue a recommendation engine.
        "estimable": cells > minimum_cells,
        "estimable_note": (
            f"{cells} of {coverage.get('cells_indexed')} map squares carry a value for this "
            f"quantity; an estimate needs more than {minimum_cells} other squares to learn from."
        ),
    }
    if note:
        entry["note"] = note
    return entry


def build_target_catalogue(service: Any, minimum_cells: int = 8) -> dict[str, Any]:
    """List every estimable quantity in the pinned index, with its own count semantics.

    `service` is any object exposing `connect()`, `site_pack`, `site` and `pack_digest` — in
    practice the `EstimateService` bound to this pack.
    """
    columns = event_count_columns(pathlib.Path(service.site_pack))
    with service.connect() as connection:
        cells_indexed = int(
            connection.execute("SELECT COUNT(*) FROM cells").fetchone()[0] or 0
        )
        cells_with_events = int(connection.execute(
            "SELECT COUNT(DISTINCT cell_id) FROM events WHERE cell_id IS NOT NULL"
        ).fetchone()[0] or 0)
        titles = _source_titles(connection)
        places = named_places(connection)
        events = _event_groups(connection)
        metrics = _metric_groups(connection)
        effort = _effort_groups(connection)
        cells_with_effort = int(connection.execute(
            "SELECT COUNT(DISTINCT cell_id) FROM effort WHERE cell_id IS NOT NULL"
        ).fetchone()[0] or 0)

    def named(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [{
            "source_id": item["source_id"],
            "title": titles.get(item["source_id"], item["source_id"]),
            "records": item.get("records"),
        } for item in rows]

    targets: list[dict[str, Any]] = []
    for event_type, group in events.items():
        source_ids = [item["source_id"] for item in group["sources"]]
        column = next((columns[key] for key in source_ids if key in columns), "")
        years = _years(group["first_year"], group["last_year"])
        coverage = {
            "cells_indexed": cells_indexed,
            "cells_with_a_value": group["cells"],
            "records": group["records"],
            "records_carrying_a_count": group["valued"],
            "value_total": round(group["total"], 4),
            "distinct_entities": group["entities"],
            "years": years,
        }
        if group["valued"]:
            targets.append(_entry(
                f"event_total:{event_type}", "event_total",
                f"total {column or 'counted units'} recorded in the map square, "
                f"for {event_type} records",
                f"{column or 'counted units'} per cell",
                {
                    "column": column or None,
                    "aggregation": (
                        f"sum of the {column or 'count'} column over every {event_type} record "
                        "whose location falls inside the map square"
                    ),
                    "rows_carrying_a_count": group["valued"],
                },
                ["events", "cells"], coverage, named(group["sources"]), minimum_cells,
                group["labels"],
            ))
        targets.append(_entry(
            f"event_records:{event_type}", "event_records",
            f"number of {event_type} records in the map square",
            f"{event_type} records per cell",
            {
                "column": None,
                "aggregation": (
                    f"number of {event_type} records whose location falls inside the map square, "
                    "regardless of how large each one is"
                ),
            },
            ["events", "cells"], coverage, named(group["sources"]), minimum_cells,
            group["labels"],
        ))
    for metric, group in metrics.items():
        years = _years(group["first_year"], group["last_year"])
        targets.append(_entry(
            f"metric_mean:{metric}", "metric_mean",
            f"average {group['label']} in the map square ({metric})",
            group["unit"] or "measured units",
            {
                "column": metric,
                "aggregation": "mean of every measured value recorded in the map square",
                "declared_description": _clean(group["description"]) or None,
            },
            ["measurements", "cells"],
            {
                "cells_indexed": cells_indexed,
                "cells_with_a_value": group["cells"],
                "records": group["rows"],
                "observed_range": [group["low"], group["high"]],
                "years": years,
            },
            named(group["sources"]), minimum_cells,
        ))
    for descriptor in GENERIC_TARGETS:
        family = descriptor["family"]
        if family in {"survey_effort", "effort_normalised_rate"}:
            cells_with_a_value = cells_with_effort
            sources = named([
                {"source_id": item["source_id"], "records": item["rows"]} for item in effort
            ])
            note = (
                "Documented survey work here: "
                + ("; ".join(
                    f"{item['method']} measured in {item['unit'] or 'unstated units'} "
                    f"({item['rows']} rows over {item['cells']} map squares)" for item in effort
                ) or "none recorded")
            )
        else:
            cells_with_a_value = cells_with_events
            sources = named([
                {"source_id": source_id, "records": None}
                for source_id in sorted({
                    item["source_id"] for group in events.values()
                    for item in group["sources"]
                })
            ])
            note = None
        targets.append(_entry(
            descriptor["target_id"], family, descriptor["label"], descriptor["unit"],
            dict(descriptor["counts"]), list(descriptor["planes"]),
            {"cells_indexed": cells_indexed, "cells_with_a_value": cells_with_a_value},
            sources, minimum_cells, note=note,
        ))

    site = {
        "site_id": service.site.get("site_id"),
        "label": service.site.get("label"),
        "pack_digest": getattr(service, "pack_digest", ""),
    }
    if getattr(service, "synthetic", False):
        site["synthetic"] = True
    return {
        "schema_version": CATALOGUE_VERSION,
        "site": site,
        "index": {
            "cells_indexed": cells_indexed,
            "cells_with_events": cells_with_events,
            "cells_with_effort": cells_with_effort,
            "event_types": sorted(events),
            "metrics": sorted(metrics),
            "effort_methods": sorted({item["method"] for item in effort}),
        },
        "targets": targets,
        "target_ids": [item["target_id"] for item in targets],
        # Named places with their own coordinates, so a caller can turn "near Kadamparai" into a
        # point itself instead of asking the person who asked the question to do it.
        "places": places,
        "default_target_id": "record_density",
        "method": (
            "Enumerated from the pinned index and the pack's declared adapters. No word was "
            "matched against any label: this lists what exists, and the caller chooses."
        ),
    }


def catalogue_index(catalogue: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["target_id"]: item for item in catalogue.get("targets") or []}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    try:
        from dss.visual_index.estimate_service import EstimateService
    except ModuleNotFoundError:  # Direct execution
        from estimate_service import EstimateService  # type: ignore[no-redef]
    service = EstimateService(args.site_pack, args.index, args.state)
    print(json.dumps(
        build_target_catalogue(service), indent=2, ensure_ascii=False, default=str
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
