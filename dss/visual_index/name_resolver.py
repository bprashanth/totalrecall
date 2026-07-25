#!/usr/bin/env python3
"""Try the name against the index before telling anyone their data is not here.

A user asked "do you have anything at all on lantana?" and was told there is no recorded lantana
name here. The pack holds `Lantana camara` in 36 records across three surveys. The assistant even
typed the correct binomial in its next sentence — as a suggestion for searching *elsewhere* — and
never tried it against the index it was already holding. The same failure hit `mammal`, while
`Mammalia` sat there as a class with 30 members and three dedicated sources.

Nothing was broken in the data and nothing was wrong with the capability. The lists of accepted
values printed into the skill text were cut alphabetically, and the text said anything not listed
would not resolve. So absence from a printed sample became a statement about the world.

This module is the second half of that fix: a lookup that actually runs. Given a person's word it
returns ranked candidates from the index itself — exact alias, then genus or first-word match
(`Lantana` → `Lantana camara`), then a shared-word match (`grey hornbill` → `Malabar Grey
Hornbill`), then hierarchy groups at any rank (`mammal` → class `Mammalia`), then measured metrics
and kinds of record. Each candidate says what it is, how much data stands behind it and how it was
matched, so a caller can say out loud which reading it took.

It never decides that something is absent. It returns candidates or it returns none, and "none"
means the lookup ran and found nothing — which is the only honest basis for saying so.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sqlite3
from typing import Any

MAX_CANDIDATES = 8
# Words that carry no discriminating power in a species or place name.
STOP_WORDS = {
    "the", "a", "an", "of", "and", "or", "in", "at", "on", "for", "sp", "spp", "species",
    "common", "indian", "data", "records", "record", "map", "site", "all", "any", "some",
}


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _key(value: Any) -> str:
    return _clean(value).casefold()


def _words(value: Any) -> list[str]:
    return [
        word for word in re.split(r"[^a-z0-9]+", _key(value))
        if word and word not in STOP_WORDS
    ]


def _candidate(
    kind: str, value: str, label: str, records: int, how: str, **extra: Any
) -> dict[str, Any]:
    return {
        "kind": kind, "value": value, "label": label, "records": int(records),
        "matched_how": how, **extra,
    }


def _entity_candidates(
    connection: sqlite3.Connection, text: str, limit: int
) -> list[dict[str, Any]]:
    """Registered names, by exact alias, then by first word, then by any shared word."""
    key = _key(text)
    words = _words(text)
    if not key:
        return []
    counts = {
        row["entity_id"]: int(row["records"]) for row in connection.execute(
            "SELECT entity_id, COUNT(*) AS records FROM events "
            "WHERE entity_id IS NOT NULL GROUP BY entity_id"
        )
    }
    rows = [
        dict(row) for row in connection.execute(
            """SELECT a.alias AS alias, a.alias_key AS alias_key, e.entity_id AS entity_id,
                      e.display_name AS display_name
               FROM entity_aliases a JOIN entities e ON e.entity_id = a.entity_id"""
        )
    ]
    exact, prefix, overlap = [], [], []
    for row in rows:
        alias_key = str(row["alias_key"] or "")
        alias_words = _words(alias_key)
        records = counts.get(row["entity_id"], 0)
        if alias_key == key:
            exact.append(_candidate(
                "entity", row["display_name"], row["display_name"], records, "exact name",
            ))
        elif alias_words and words and (
            alias_words[0] == words[0] or alias_key.startswith(key + " ")
        ):
            # A bare genus is the commonest way a person names a species they half-remember.
            prefix.append(_candidate(
                "entity", row["display_name"], row["display_name"], records,
                f"“{_clean(text)}” is the first part of this recorded name",
            ))
        elif alias_words and words and set(words) & set(alias_words):
            shared = ", ".join(sorted(set(words) & set(alias_words)))
            overlap.append(_candidate(
                "entity", row["display_name"], row["display_name"], records,
                f"shares “{shared}” with this recorded name",
            ))
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for bucket in (exact, prefix, overlap):
        for item in sorted(bucket, key=lambda entry: (-entry["records"], entry["value"])):
            if item["value"] not in seen:
                seen.add(item["value"])
                ordered.append(item)
    return ordered[:limit]


def _group_candidates(
    connection: sqlite3.Connection, text: str, limit: int
) -> list[dict[str, Any]]:
    """Hierarchy groups at any rank, including the everyday word for a taxonomic class.

    "mammal" is not a name in any index; `Mammalia` is. The bridge between them is that one is a
    prefix of the other, which is true for most class and family names a person will say out
    loud, and is checked against the pack's own ranks rather than against a table of taxonomy
    written down here.
    """
    words = _words(text)
    if not words:
        return []
    counts = {
        row["entity_id"]: int(row["records"]) for row in connection.execute(
            "SELECT entity_id, COUNT(*) AS records FROM events "
            "WHERE entity_id IS NOT NULL GROUP BY entity_id"
        )
    }
    members: dict[tuple[str, str], int] = {}
    records: dict[tuple[str, str], int] = {}
    for row in connection.execute("SELECT entity_id, hierarchy_json FROM entities"):
        try:
            hierarchy = json.loads(row["hierarchy_json"] or "{}")
        except (TypeError, ValueError):
            continue
        for rank, group in (hierarchy or {}).items():
            if isinstance(group, str) and group:
                signature = (str(rank), group)
                members[signature] = members.get(signature, 0) + 1
                # Ranked by records, not by how many names sit under it: a one-species genus must
                # not outrank the species itself, which is what the user actually asked about.
                records[signature] = records.get(signature, 0) + counts.get(row["entity_id"], 0)
    found: list[dict[str, Any]] = []
    for (rank, group), count in members.items():
        group_key = _key(group)
        for word in words:
            if group_key == word:
                how = "exact group name"
            elif len(word) >= 4 and group_key.startswith(word):
                how = f"“{word}” is the everyday word for this group"
            elif len(group_key) >= 4 and word.startswith(group_key):
                how = f"“{word}” contains this group name"
            else:
                continue
            found.append(_candidate(
                "group", group, f"{group} ({rank})", records.get((rank, group), 0), how,
                rank=rank, members=count,
            ))
            break
    return sorted(found, key=lambda item: (-item["records"], item["value"]))[:limit]


def _metric_candidates(
    connection: sqlite3.Connection, text: str, limit: int
) -> list[dict[str, Any]]:
    words = set(_words(text))
    if not words:
        return []
    found = []
    for row in connection.execute(
        """SELECT m.metric AS metric, COUNT(*) AS readings,
                  COALESCE(MIN(d.label), m.metric) AS label
           FROM measurements m LEFT JOIN metric_definitions d ON d.metric = m.metric
           WHERE m.value IS NOT NULL GROUP BY m.metric"""
    ):
        haystack = set(_words(row["metric"])) | set(_words(row["label"]))
        shared = words & haystack
        if shared:
            found.append(_candidate(
                "metric", row["metric"], _clean(row["label"]), int(row["readings"]),
                f"measured quantity sharing “{', '.join(sorted(shared))}”",
            ))
    return sorted(found, key=lambda item: (-item["records"], item["value"]))[:limit]


def _record_kind_candidates(
    connection: sqlite3.Connection, text: str, limit: int
) -> list[dict[str, Any]]:
    words = set(_words(text))
    if not words:
        return []
    found = []
    for row in connection.execute(
        "SELECT event_type, COUNT(*) AS records FROM events GROUP BY event_type"
    ):
        haystack = set(_words(row["event_type"]))
        shared = words & haystack
        if shared:
            found.append(_candidate(
                "record_kind", row["event_type"], _clean(row["event_type"]),
                int(row["records"]),
                f"kind of record sharing “{', '.join(sorted(shared))}”",
            ))
    return sorted(found, key=lambda item: (-item["records"], item["value"]))[:limit]


def resolve_name(
    connection: sqlite3.Connection, text: str, limit: int = MAX_CANDIDATES,
    kinds: tuple[str, ...] = ("entity", "group", "metric", "record_kind"),
) -> dict[str, Any]:
    """Look one word up in the index and return what it could be, best-supported first.

    The return is deliberately not a decision. `candidates[0]` is the most-recorded reading and is
    what a caller should try, but every candidate carries how it matched so the caller can say
    which reading it took — and an empty list means the lookup ran, which is the only thing that
    licenses saying the data is not here.
    """
    text = _clean(text)
    finders = {
        "entity": _entity_candidates,
        "group": _group_candidates,
        "metric": _metric_candidates,
        "record_kind": _record_kind_candidates,
    }
    buckets = {
        kind: finders[kind](connection, text, limit) for kind in kinds if kind in finders
    }
    exact = [
        item for bucket in buckets.values() for item in bucket
        if item["matched_how"].startswith("exact")
    ]
    ranked: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in sorted(
        [entry for bucket in buckets.values() for entry in bucket],
        key=lambda entry: (
            0 if entry["matched_how"].startswith("exact") else 1, -entry["records"],
            entry["value"],
        ),
    ):
        signature = (item["kind"], item["value"])
        if signature not in seen:
            seen.add(signature)
            ranked.append(item)
    return {
        "requested": text,
        "exact": bool(exact),
        "candidates": ranked[:limit],
        "by_kind": {kind: bucket[:limit] for kind, bucket in buckets.items() if bucket},
        "looked_up": True,
    }


def best_candidate(
    connection: sqlite3.Connection, text: str, kinds: tuple[str, ...] = ("entity",),
) -> dict[str, Any] | None:
    found = resolve_name(connection, text, kinds=kinds)
    return found["candidates"][0] if found["candidates"] else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("name")
    args = parser.parse_args(argv)
    connection = sqlite3.connect(f"file:{args.index}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    print(json.dumps(resolve_name(connection, args.name), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
