#!/usr/bin/env python3
"""Three to five headline numbers about a site, in words a programme manager already uses.

A context rail that says "1,145 entities across 302 cells" is telling the reader about our
database. They came to find out what is known about a place. So this module reads the pinned
index and the pack's declared adapters and states what is actually recorded — how many species,
how many work-days, how many households were surveyed — with the counting semantics the pack
itself declared, and never a word of our vocabulary.

Nothing about any sector is written down here. There is no list of ecology nouns and no list of
livelihoods nouns: a stat is built from the pack's own event types, count columns, metric registry,
effort methods and entity hierarchies, and the wording is recovered from the pack's own human-
written strings. Two things make that readable:

* Ugly machine tokens are humanised — `15_minute_point_count_detection` loses its protocol
  boilerplate and becomes "Point count detections"; `mgnrega_work` recovers its capitals from the
  source title that spells MGNREGA properly, because that title was written by a person.
* A column that only says "how many of them" (`count`, `individualCount`, `num`) never becomes a
  label: the label then names the thing that was counted, and the count goes in the detail.

Ordering is by how much of the record base each stat speaks for, so the rail leads with what the
site is mostly made of. Five at most; a rail is not a report.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
from typing import Any

try:
    from dss.visual_index.target_catalogue import event_count_columns
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/site_stats.py
    from target_catalogue import event_count_columns  # type: ignore[no-redef]


STATS_VERSION = "idli-site-stats/1"
MAX_STATS = 5

# Columns that only say "how many of them". They name no subject, so they never become a label.
COUNTING_WORDS = {
    "count", "counts", "counted", "individual", "individuals", "number", "numbers", "num",
    "no", "total", "totals", "value", "values", "record", "records", "qty", "quantity", "n",
}
# Units of measurement rather than things: survey work measured in these is reported as visits.
MEASURE_UNITS = {
    "minute", "minutes", "hour", "hours", "second", "seconds", "day", "days", "week", "weeks",
    "km", "kilometre", "kilometres", "kilometer", "kilometers", "m", "metre", "metres", "meter",
    "meters", "ha", "hectare", "hectares", "point-counts", "point-count", "trap-nights", "hrs",
}
# Protocol boilerplate at the front of an event type: "15 minute point count" is a point count.
TIME_WORDS = {"minute", "minutes", "min", "hour", "hours", "hr", "hrs", "second", "seconds"}
# Machine words that must never reach a label, whatever the pack calls its columns.
BANNED_LABEL_WORDS = {
    "entity", "entities", "cell", "cells", "event", "adapter", "adapters", "plane", "planes",
    "source", "sources", "id", "ids", "json", "row", "rows", "index", "indexed", "pack",
}
_TOKEN = re.compile(r"[A-Za-z0-9]+")


def _split(token: str) -> list[str]:
    """Break a machine token into words: underscores, hyphens, spaces and camelCase."""
    spaced = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(token or ""))
    return [word for word in re.split(r"[^A-Za-z0-9]+", spaced) if word]


def cased_vocabulary(connection: sqlite3.Connection) -> dict[str, str]:
    """Recover how this pack spells its own words, from the strings people wrote by hand.

    Source titles, metric labels and entity names are prose: someone typed "MGNREGA-style public
    works" and "Lion-tailed macaque". So when a machine token has to be printed, its casing can be
    taken from the pack rather than invented — which is how `mgnrega_work` prints as "MGNREGA
    work" without this file ever containing the word MGNREGA.
    """
    vocabulary: dict[str, str] = {}
    statements = (
        "SELECT title FROM sources",
        "SELECT label FROM metric_definitions",
        "SELECT display_name FROM entities",
    )
    for statement in statements:
        try:
            rows = connection.execute(statement).fetchall()
        except sqlite3.Error:
            continue
        for row in rows:
            for word in _TOKEN.findall(str(row[0] or "")):
                key = word.casefold()
                # Prefer an all-capitals spelling; otherwise keep the first one seen.
                if word.isupper() and len(word) > 1:
                    vocabulary[key] = word
                else:
                    vocabulary.setdefault(key, word)
    return vocabulary


def humanise(token: Any, vocabulary: dict[str, str] | None = None) -> str:
    """Turn a machine token into a phrase, keeping the pack's own spelling where it has one."""
    vocabulary = vocabulary or {}
    words = _split(token)
    # Drop protocol boilerplate at the front: "15 minute point count" is a point count.
    while len(words) >= 2 and words[0].isdigit() and words[1].casefold() in TIME_WORDS:
        words = words[2:]
    if not words:
        return ""
    spelled = [vocabulary.get(word.casefold(), word.casefold()) for word in words]
    text = " ".join(spelled)
    return text[0].upper() + text[1:] if text else text


def _plural(phrase: str) -> str:
    if not phrase:
        return phrase
    last = phrase.rsplit(" ", 1)[-1]
    lowered = last.casefold()
    if lowered.endswith(("s", "x", "z", "ch", "sh")):
        return phrase
    if len(lowered) > 1 and lowered.endswith("y") and lowered[-2] not in "aeiou":
        return phrase[:-1] + "ies"
    return phrase + "s"


def _is_counting_word(token: Any) -> bool:
    words = [word.casefold() for word in _split(token)]
    return bool(words) and all(word in COUNTING_WORDS for word in words)


def _is_readable_column(token: Any, vocabulary: dict[str, str]) -> bool:
    """A column may name the stat only if its own name is a word, not a field abbreviation.

    `persondays` reads; `Abun` does not, and "Abun recorded" tells a reader nothing. The test is
    the pack's own prose: a short token counts as a word only when someone wrote it out somewhere
    a person would read.
    """
    words = _split(token)
    if not words:
        return False
    if len(words) > 1:
        return True
    word = words[0]
    return len(word) >= 6 or word.casefold() in vocabulary


def _acceptable(label: str) -> bool:
    words = {word.casefold() for word in _TOKEN.findall(label)}
    return bool(label) and not (words & BANNED_LABEL_WORDS)


def _years(low: Any, high: Any) -> str:
    if low in (None, "") or high in (None, ""):
        return ""
    return f"{int(low)}" if int(low) == int(high) else f"{int(low)}–{int(high)}"


def _detail(*parts: str) -> str:
    return ", ".join(part for part in parts if part)


def _stat(
    stat_id: str, label: str, value: Any, unit: str | None, detail: str, weight: int
) -> dict[str, Any] | None:
    if not _acceptable(label) or value in (None, ""):
        return None
    return {
        "id": stat_id, "label": label,
        "value": int(value) if isinstance(value, float) and value.is_integer() else value,
        "unit": unit, "detail": detail, "_weight": weight,
    }


def _taxon_stat(connection: sqlite3.Connection, squares: int) -> dict[str, Any] | None:
    """Named subjects that carry a biological rank are species; nothing else here is.

    The rank comes from the pack's own entity hierarchy, so a pack whose subjects are occupations
    or estates simply produces no such stat instead of being described in the wrong noun.
    """
    try:
        row = connection.execute(
            """SELECT COUNT(DISTINCT e.entity_id) AS taxa, COUNT(*) AS records
               FROM events e JOIN entities en ON en.entity_id = e.entity_id
               WHERE json_extract(en.hierarchy_json,'$.kingdom') IS NOT NULL
                  OR json_extract(en.hierarchy_json,'$.genus') IS NOT NULL"""
        ).fetchone()
    except sqlite3.Error:
        return None
    if not row or not row["taxa"]:
        return None
    return _stat(
        "species_recorded", "Species recorded", int(row["taxa"]), None,
        _detail(f"in {int(row['records']):,} records",
                f"across {squares:,} grid squares" if squares else ""),
        int(row["records"]),
    )


def _event_stats(
    connection: sqlite3.Connection, columns: dict[str, str], vocabulary: dict[str, str],
) -> list[dict[str, Any]]:
    stats: list[dict[str, Any]] = []
    rows = connection.execute(
        """SELECT event_type, COUNT(*) AS records, COUNT(count_value) AS valued,
                  COALESCE(SUM(count_value),0) AS total, COUNT(DISTINCT cell_id) AS squares,
                  MIN(year) AS first_year, MAX(year) AS last_year
           FROM events GROUP BY event_type ORDER BY records DESC"""
    ).fetchall()
    for row in rows:
        event_type = str(row["event_type"] or "")
        sources = [item[0] for item in connection.execute(
            "SELECT DISTINCT source_id FROM events WHERE event_type=?", (event_type,)
        )]
        column = next((columns[key] for key in sources if key in columns), "")
        subject = _plural(humanise(event_type, vocabulary))
        years = _years(row["first_year"], row["last_year"])
        squares = f"across {int(row['squares']):,} grid squares" if row["squares"] else ""
        if (
            column and row["valued"] and not _is_counting_word(column)
            and _is_readable_column(column, vocabulary)
        ):
            # The pack declared what one record counts, and it names a thing: lead with it.
            stats.append(_stat(
                f"total:{event_type}", f"{humanise(column, vocabulary)} recorded",
                float(row["total"]), None,
                _detail(
                    f"from {int(row['records']):,} {humanise(event_type, vocabulary)} records",
                    years,
                ),
                int(row["records"]),
            ))
            continue
        counted = (
            f"{int(row['total']):,} counted" if row["valued"] and row["total"] else ""
        )
        stats.append(_stat(
            f"records:{event_type}", subject, int(row["records"]), None,
            _detail(counted, squares, years), int(row["records"]),
        ))
    return [item for item in stats if item]


def _metric_stat(
    connection: sqlite3.Connection, vocabulary: dict[str, str]
) -> dict[str, Any] | None:
    """The measured quantity with the most readings, named the way its registry names it."""
    definitions = {
        row["metric"]: row["label"] for row in connection.execute(
            "SELECT metric,label FROM metric_definitions"
        )
    }
    row = connection.execute(
        """SELECT metric, COUNT(*) AS readings, MIN(year) AS first_year, MAX(year) AS last_year,
                  COUNT(DISTINCT metric) AS kinds
           FROM measurements WHERE value IS NOT NULL
           GROUP BY metric ORDER BY readings DESC LIMIT 1"""
    ).fetchone()
    if not row or not row["readings"]:
        return None
    kinds = int(connection.execute(
        "SELECT COUNT(DISTINCT metric) FROM measurements WHERE value IS NOT NULL"
    ).fetchone()[0] or 0)
    name = definitions.get(row["metric"]) or humanise(row["metric"], vocabulary)
    others = f"one of {kinds:,} measured quantities here" if kinds > 1 else ""
    return _stat(
        f"metric:{row['metric']}", f"{name} readings", int(row["readings"]), None,
        _detail(others, _years(row["first_year"], row["last_year"])),
        int(row["readings"]),
    )


def _effort_stat(
    connection: sqlite3.Connection, vocabulary: dict[str, str]
) -> dict[str, Any] | None:
    """Survey work, reported as the thing it covered when the unit names a thing.

    Households are things and minutes are not, so a pack that measures effort in households says
    "Households surveyed" and one that measures it in minutes says "Survey visits" with the time
    in the detail. The distinction is in the unit the pack declared, not in what sector it is.
    """
    rows = connection.execute(
        """SELECT method, effort_unit, COUNT(*) AS visits, COALESCE(SUM(effort_value),0) AS total,
                  COUNT(DISTINCT cell_id) AS squares
           FROM effort GROUP BY method, effort_unit ORDER BY visits DESC"""
    ).fetchall()
    if not rows:
        return None
    visits = sum(int(row["visits"]) for row in rows)
    squares = len({row["squares"] for row in rows if row["squares"]}) and max(
        int(row["squares"]) for row in rows
    )
    leading = rows[0]
    unit = str(leading["effort_unit"] or "")
    unit_words = [word.casefold() for word in _split(unit)]
    names_a_thing = bool(unit_words) and not any(word in MEASURE_UNITS for word in unit_words)
    if names_a_thing and len(rows) == 1 and leading["total"]:
        return _stat(
            "effort_covered", f"{_plural(humanise(unit, vocabulary))} surveyed",
            float(leading["total"]), None,
            _detail(f"over {visits:,} survey visits",
                    f"in {squares:,} grid squares" if squares else ""),
            visits,
        )
    methods = _plural(humanise(leading["method"], vocabulary)).lower()
    return _stat(
        "survey_visits", "Survey visits", visits, None,
        _detail(f"mostly {methods}" if len(rows) > 1 else methods,
                f"in {squares:,} grid squares" if squares else ""),
        visits,
    )


def _place_stat(
    connection: sqlite3.Connection, vocabulary: dict[str, str]
) -> dict[str, Any] | None:
    """A column of proper names attached to survey work is the places the work covered.

    Proper names are the test: `village` holds "Kadamparai Village" and becomes "Villages
    covered", while `season` holds "monsoon" and becomes nothing. No column name is known here in
    advance.
    """
    counts: dict[str, dict[str, Any]] = {}
    try:
        rows = connection.execute("SELECT properties_json FROM effort").fetchall()
    except sqlite3.Error:
        return None
    for row in rows:
        try:
            properties = json.loads(row[0] or "{}")
        except (TypeError, ValueError):
            continue
        for key, value in (properties or {}).items():
            if len(_split(key)) != 1 or not isinstance(value, str) or not value[:1].isupper():
                continue
            bucket = counts.setdefault(key, {"values": set(), "rows": 0})
            bucket["values"].add(value)
            bucket["rows"] += 1
    best = None
    for key, bucket in sorted(counts.items()):
        # Two of anything is a distinction, not a coverage figure worth a rail slot.
        if not 2 < len(bucket["values"]) <= 50:
            continue
        if best is None or bucket["rows"] > best[1]["rows"]:
            best = (key, bucket)
    if best is None:
        return None
    key, bucket = best
    return _stat(
        f"places:{key}", f"{_plural(humanise(key, vocabulary))} covered",
        len(bucket["values"]), None,
        _detail(f"named in {int(bucket['rows']):,} survey records"), int(bucket["rows"]),
    )


def build_site_stats(service: Any, limit: int = MAX_STATS) -> dict[str, Any]:
    """Three to five plain headline numbers for one pinned site.

    `service` is anything exposing `connect()`, `site_pack` and `site` — in practice the
    `ResultService` already bound to this bridge's pack.
    """
    site = getattr(service, "site", {}) or {}
    with service.connect() as connection:
        connection.row_factory = sqlite3.Row
        squares = int(
            connection.execute("SELECT COUNT(*) FROM cells").fetchone()[0] or 0
        )
        vocabulary = cased_vocabulary(connection)
        columns = event_count_columns(pathlib.Path(service.site_pack))
        candidates: list[dict[str, Any] | None] = [
            _taxon_stat(connection, squares),
            *_event_stats(connection, columns, vocabulary),
            _metric_stat(connection, vocabulary),
            _effort_stat(connection, vocabulary),
            _place_stat(connection, vocabulary),
        ]
    stats = [item for item in candidates if item]
    stats.sort(key=lambda item: (-item["_weight"], item["label"]))
    # One stat per kind of thing: the rail should not be three flavours of the same count.
    chosen: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in stats:
        family = item["id"].split(":", 1)[0]
        if family in {"total", "records"} and family in seen and len(chosen) >= 2:
            continue
        seen.add(family)
        chosen.append({key: value for key, value in item.items() if key != "_weight"})
        if len(chosen) >= limit:
            break
    return {
        "schema_version": STATS_VERSION,
        "site_id": site.get("site_id"),
        "label": site.get("label"),
        "synthetic": bool(getattr(service, "synthetic", False)),
        "grid_squares": squares,
        "stats": chosen,
        "method": (
            "Counted from the pinned index and the pack's declared adapters. Wording is taken "
            "from the pack's own registered labels; no value was estimated."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    args = parser.parse_args(argv)
    try:
        from dss.visual_index.result_service import ResultService
    except ModuleNotFoundError:  # Direct execution
        from result_service import ResultService  # type: ignore[no-redef]
    service = ResultService(args.site_pack, args.index, args.state)
    print(json.dumps(build_site_stats(service), indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
