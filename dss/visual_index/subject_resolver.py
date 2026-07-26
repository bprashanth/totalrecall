#!/usr/bin/env python3
"""Resolve a person's collective word against one bounded site catalogue.

This module deliberately does not know what a raptor, wage worker, clinic, tree or elephant is.
It knows only what the derived index contains. A unique registered alias may be resolved after a
small singular/plural widening. Everything else becomes a bounded choice over entity ids from the
site catalogue. The dialogue model may make that semantic choice, but this module verifies every
returned id, records how the choice was made, and caches it against the exact catalogue version.

The split is important:

* deterministic code establishes which ids exist and which rows they address;
* the outer language model interprets an open phrase such as "raptors";
* the analytical service accepts only verified ids and reports the interpretation in its audit.

No model is called from this module and no taxonomy is used to manufacture a group. Shared
hierarchy is presentation metadata after member selection, not the selection mechanism.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import sqlite3
import tempfile
from typing import Any


RESOLVER_VERSION = "site-subject-resolver/1"
DEFAULT_PROMPT_VERSION = "site-subject-selection/1"


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split())


def _key(value: Any) -> str:
    return _clean(value).casefold()


def _digest(value: Any) -> str:
    serialised = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(serialised.encode("utf-8")).hexdigest()


def _word_key(value: Any) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", _key(value)))


def name_variants(value: Any) -> list[str]:
    """Return the typed name and one conservative last-word number variant.

    This is intentionally small. It fixes `elephants` → `elephant` without pretending that an
    English inflector can decide arbitrary scientific or local names. Ambiguous widening remains
    a choice rather than an automatic match.
    """
    original = _word_key(value)
    if not original:
        return []
    words = original.split()
    last = words[-1]
    endings: list[str] = []
    if len(last) > 4 and last.endswith("ies"):
        endings.append(last[:-3] + "y")
    elif len(last) > 4 and last.endswith(("ches", "shes", "xes", "zes")):
        endings.append(last[:-2])
    elif len(last) > 3 and last.endswith("s") and not last.endswith(("ss", "us", "is")):
        endings.append(last[:-1])
    else:
        endings.append(last + "s")
    variants = [original]
    for ending in endings:
        candidate = " ".join([*words[:-1], ending])
        if candidate and candidate not in variants:
            variants.append(candidate)
    return variants


def catalogue_digest(connection: sqlite3.Connection) -> str:
    """Version a binding by the exact admitted sources and entity catalogue it was chosen from."""
    sources = [
        tuple(row) for row in connection.execute(
            "SELECT source_id,content_sha256 FROM sources ORDER BY source_id"
        )
    ]
    entities = [
        tuple(row) for row in connection.execute(
            "SELECT entity_id,canonical_name,display_name,hierarchy_json "
            "FROM entities ORDER BY entity_id"
        )
    ]
    return _digest({"sources": sources, "entities": entities})


def entity_catalogue(connection: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return the complete bounded entity choice set, with compact evidence and trait context."""
    aliases: dict[str, list[str]] = {}
    for row in connection.execute(
        "SELECT entity_id,alias FROM entity_aliases ORDER BY entity_id,alias"
    ):
        aliases.setdefault(str(row["entity_id"]), []).append(str(row["alias"]))
    counts = {
        str(row["entity_id"]): int(row["records"])
        for row in connection.execute(
            "SELECT entity_id,COUNT(*) AS records FROM events "
            "WHERE entity_id IS NOT NULL GROUP BY entity_id"
        )
    }
    result: list[dict[str, Any]] = []
    for row in connection.execute(
        "SELECT entity_id,canonical_name,display_name,hierarchy_json "
        "FROM entities ORDER BY display_name,entity_id"
    ):
        try:
            hierarchy = json.loads(row["hierarchy_json"] or "{}")
        except (TypeError, ValueError):
            hierarchy = {}
        entry = {
            "entity_id": str(row["entity_id"]),
            "name": _clean(row["display_name"]),
            "canonical_name": _clean(row["canonical_name"]),
            "records": counts.get(str(row["entity_id"]), 0),
        }
        other_names = [
            alias for alias in aliases.get(str(row["entity_id"]), [])
            if _key(alias) not in {_key(entry["name"]), _key(entry["canonical_name"])}
        ]
        if other_names:
            entry["other_names"] = other_names[:6]
        if isinstance(hierarchy, dict) and hierarchy:
            entry["attributes"] = {
                str(key): value for key, value in hierarchy.items()
                if value not in (None, "", "NA")
            }
        result.append(entry)
    return result


def _catalogue_by_id(catalogue: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["entity_id"]): item for item in catalogue}


def _shared_hierarchy(members: list[dict[str, Any]]) -> dict[str, str]:
    """Hierarchy shared by every selected member, for description only."""
    if not members:
        return {}
    shared = dict(members[0].get("attributes") or {})
    for member in members[1:]:
        attributes = member.get("attributes") or {}
        shared = {
            rank: value for rank, value in shared.items()
            if attributes.get(rank) == value
        }
    return {str(rank): str(value) for rank, value in shared.items() if value not in ("", "NA")}


class SubjectResolver:
    """Inspect, verify and version collective-name bindings for one derived site index."""

    def __init__(self, connection: sqlite3.Connection, state_root: pathlib.Path):
        self.connection = connection
        self.state_root = pathlib.Path(state_root).resolve()
        self.catalogue = entity_catalogue(connection)
        self.by_id = _catalogue_by_id(self.catalogue)
        self.catalogue_digest = catalogue_digest(connection)

    def _cache_key(self, requested: str, selector: dict[str, str]) -> str:
        return _digest({
            "catalogue": self.catalogue_digest,
            "requested": _key(requested),
            "model": _clean(selector.get("model")),
            "prompt_version": _clean(selector.get("prompt_version"))
            or DEFAULT_PROMPT_VERSION,
            "resolver_version": RESOLVER_VERSION,
        }).split(":", 1)[1]

    def _cache_path(self, requested: str, selector: dict[str, str]) -> pathlib.Path:
        return self.state_root / "subject-bindings" / "cache" / (
            self._cache_key(requested, selector) + ".json"
        )

    @staticmethod
    def _atomic_replace(path: pathlib.Path, value: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(value, stream, sort_keys=True, ensure_ascii=False)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def _read_cache(
        self, requested: str, selector: dict[str, str]
    ) -> dict[str, Any] | None:
        path = self._cache_path(requested, selector)
        try:
            cached = json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return None
        ids = cached.get("entity_ids") if isinstance(cached, dict) else None
        if (
            cached.get("catalogue_digest") != self.catalogue_digest
            or not isinstance(ids, list)
            or not ids
            or any(str(entity_id) not in self.by_id for entity_id in ids)
        ):
            return None
        cached = dict(cached)
        cached["resolution_method"] = "cached_model_selection"
        return cached

    def inspect(self, requested: Any, selector: dict[str, str] | None = None) -> dict[str, Any]:
        """Resolve a unique alias or return the bounded evidence needed for a semantic choice."""
        requested = _clean(requested)
        if not requested:
            raise ValueError("a subject name is required")
        selector = dict(selector or {})
        if selector:
            cached = self._read_cache(requested, selector)
            if cached is not None:
                return {"status": "resolved", "binding": cached}

        variants = set(name_variants(requested))
        exact_ids: set[str] = set()
        substring_ids: set[str] = set()
        for item in self.catalogue:
            names = [
                item.get("name"), item.get("canonical_name"), *(item.get("other_names") or [])
            ]
            keys = {_word_key(name) for name in names if _word_key(name)}
            if keys & variants:
                exact_ids.add(str(item["entity_id"]))
            if any(
                variant in candidate or candidate in variant
                for variant in variants for candidate in keys
                if len(variant) >= 4 and len(candidate) >= 4
            ):
                substring_ids.add(str(item["entity_id"]))
        if len(exact_ids) == 1:
            entity_id = next(iter(exact_ids))
            member = self.by_id[entity_id]
            return {
                "status": "resolved",
                "binding": {
                    "requested": requested,
                    "kind": "entity",
                    "rank": None,
                    "label": member["name"],
                    "entity_ids": [entity_id],
                    "event_types": [],
                    "members": 1,
                    "member_labels": [member["name"]],
                    "resolved": True,
                    "resolution_method": (
                        "exact_alias" if _word_key(requested) in variants
                        and _word_key(requested) in {
                            _word_key(member.get("name")),
                            _word_key(member.get("canonical_name")),
                            *[_word_key(name) for name in member.get("other_names") or []],
                        } else "number_variant"
                    ),
                    "catalogue_digest": self.catalogue_digest,
                    "resolver_version": RESOLVER_VERSION,
                },
            }
        candidates = [
            self.by_id[entity_id] for entity_id in sorted(exact_ids or substring_ids)
        ]
        return {
            "status": "selection_required",
            "requested": requested,
            "reason": "ambiguous_name" if candidates else "open_group_or_unknown_name",
            "candidates": candidates,
            "catalogue": self.catalogue,
            "catalogue_digest": self.catalogue_digest,
            "instruction": (
                "Choose only entity_id values from catalogue that the user's phrase denotes. "
                "Return the choice by calling the capability again with "
                "{\"requested\": <original phrase>, \"entity_ids\": [<verified ids>]}. "
                "Do not add an id that is absent from this catalogue. If the phrase is genuinely "
                "unclear, ask one short question instead."
            ),
        }

    def verify(
        self, requested: Any, entity_ids: Any, selector: dict[str, str],
        label: Any = "", replace_cache: bool = False,
    ) -> dict[str, Any]:
        """Verify a model-selected member set and persist an auditable, versioned binding."""
        requested = _clean(requested)
        if not requested:
            raise ValueError("a model-selected subject needs its original requested phrase")
        if not isinstance(entity_ids, list) or not entity_ids:
            raise ValueError("a model-selected subject needs a non-empty entity_ids list")
        selected = list(dict.fromkeys(_clean(item) for item in entity_ids if _clean(item)))
        unknown = [entity_id for entity_id in selected if entity_id not in self.by_id]
        if unknown:
            raise ValueError(
                "subject selection contains ids outside the supplied site catalogue: "
                + ", ".join(unknown)
            )
        model = _clean(selector.get("model"))
        prompt_version = _clean(selector.get("prompt_version")) or DEFAULT_PROMPT_VERSION
        if not model:
            raise ValueError("a model-selected subject must record the selector model")
        members = [self.by_id[entity_id] for entity_id in selected]
        shared = _shared_hierarchy(members)
        presentation_rank = ""
        presentation_value = ""
        for rank in ("family", "order", "class", "genus", "division", "category", "type"):
            if shared.get(rank):
                presentation_rank, presentation_value = rank, shared[rank]
                break
        binding = {
            "requested": requested,
            "kind": "entity" if len(selected) == 1 else "selected_group",
            "rank": presentation_rank or None,
            "label": _clean(label) or (
                members[0]["name"] if len(members) == 1 else requested
            ),
            "entity_ids": selected,
            "event_types": [],
            "members": len(selected),
            "member_labels": [member["name"] for member in members],
            "resolved": True,
            "resolution_method": "model_selected",
            "selector": {"model": model, "prompt_version": prompt_version},
            "catalogue_digest": self.catalogue_digest,
            "resolver_version": RESOLVER_VERSION,
        }
        if presentation_rank:
            binding["shared_hierarchy"] = {
                "rank": presentation_rank, "value": presentation_value,
            }
        binding_id = "binding-" + _digest(binding).split(":", 1)[1][:20]
        binding["binding_id"] = binding_id
        immutable = self.state_root / "subject-bindings" / "bindings" / f"{binding_id}.json"
        immutable.parent.mkdir(parents=True, exist_ok=True)
        if not immutable.exists():
            immutable.write_text(
                json.dumps(binding, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        cache_path = self._cache_path(requested, binding["selector"])
        if replace_cache or not cache_path.exists():
            self._atomic_replace(cache_path, binding)
        return binding

