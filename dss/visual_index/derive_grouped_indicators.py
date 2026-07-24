#!/usr/bin/env python3
"""Materialise source-linked grouped indicators from a declarative recipe.

The recipe declares dimensions, compatible input tables, filters, aggregations,
units and method references. The implementation contains no site or taxon names.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import pathlib
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def _safe_path(root: pathlib.Path, relative: str) -> pathlib.Path:
    path = (root / relative).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"path escapes site pack: {relative}")
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def _rows(path: pathlib.Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _sha256(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _number(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text or text.casefold() in {"na", "nan", "null", "none"}:
        return None
    try:
        result = float(text)
    except ValueError:
        return None
    return result if math.isfinite(result) else None


def _matches(row: dict[str, str], condition: dict[str, Any] | None) -> bool:
    if not condition:
        return True
    if "all" in condition:
        return all(_matches(row, child) for child in condition["all"])
    if "any" in condition:
        return any(_matches(row, child) for child in condition["any"])
    field = condition.get("field")
    if not isinstance(field, str) or not field:
        raise ValueError(f"filter condition lacks a field: {condition!r}")
    actual = str(row.get(field) or "")
    if "eq" in condition:
        return actual == str(condition["eq"])
    if "not_eq" in condition:
        return actual != str(condition["not_eq"])
    if "in" in condition:
        return actual in {str(item) for item in condition["in"]}
    if "not_in" in condition:
        return actual not in {str(item) for item in condition["not_in"]}
    raise ValueError(f"unsupported filter condition: {condition!r}")


def _aggregate(rows: list[dict[str, str]], spec: dict[str, Any]) -> float | int | None:
    eligible = [row for row in rows if _matches(row, spec.get("filter"))]
    operation = spec["operation"]
    field = spec.get("field")
    if operation == "row_count":
        value: float | int | None = len(eligible)
    elif operation == "n_distinct":
        values = {
            str(row.get(field) or "").strip()
            for row in eligible
            if str(row.get(field) or "").strip()
        }
        value = len(values)
    elif operation in {"sum", "mean"}:
        values = [_number(row.get(field)) for row in eligible]
        finite = [item for item in values if item is not None]
        if not finite:
            value = spec.get("empty_value")
        elif operation == "sum":
            value = sum(finite)
        else:
            value = sum(finite) / len(finite)
    else:
        raise ValueError(f"unsupported aggregation operation: {operation}")
    if value is not None:
        value = value * float(spec.get("scale", 1))
        if isinstance(value, float) and value.is_integer():
            value = int(value)
    return value


def derive(
    site_pack: pathlib.Path,
    recipe_path: pathlib.Path,
    output_csv: pathlib.Path,
    manifest_path: pathlib.Path,
) -> dict[str, Any]:
    site_pack = site_pack.resolve()
    recipe_path = recipe_path.resolve()
    recipe = _load_json(recipe_path)
    dimension_spec = recipe["dimensions"]
    dimension_path = _safe_path(site_pack, dimension_spec["path"])
    dimension_rows = _rows(dimension_path)
    dimension_key = dimension_spec["key"]
    inputs: dict[str, dict[str, Any]] = {}
    input_paths: dict[str, pathlib.Path] = {}
    for input_id, input_spec in recipe["inputs"].items():
        path = _safe_path(site_pack, input_spec["path"])
        input_paths[input_id] = path
        grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in _rows(path):
            grouped[str(row.get(input_spec["group_by"]) or "")].append(row)
        inputs[input_id] = {"spec": input_spec, "groups": grouped}

    fields = [item["output"] for item in dimension_spec["fields"]]
    metric_ids = [item["metric_id"] for item in recipe["rollups"]]
    if len(metric_ids) != len(set(metric_ids)):
        raise ValueError("metric_id values must be unique")
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    output_rows = []
    for dimension_row in dimension_rows:
        key = str(dimension_row.get(dimension_key) or "")
        if not key:
            raise ValueError(f"empty dimension key in {dimension_path.name}")
        output = {
            item["output"]: dimension_row.get(item["column"])
            for item in dimension_spec["fields"]
        }
        for rollup in recipe["rollups"]:
            input_id = rollup["input"]
            output[rollup["metric_id"]] = _aggregate(
                inputs[input_id]["groups"].get(key, []), rollup
            )
        output_rows.append(output)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=fields + metric_ids, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(output_rows)

    files = {
        dimension_spec["path"]: _sha256(dimension_path),
        **{
            recipe["inputs"][input_id]["path"]: _sha256(path)
            for input_id, path in input_paths.items()
        },
        str(recipe_path.relative_to(site_pack)): _sha256(recipe_path),
    }
    manifest = {
        "schema_version": "derived-indicator-manifest/0.1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "recipe_id": recipe["recipe_id"],
        "recipe_version": recipe["version"],
        "method_references": recipe.get("method_references", []),
        "input_sha256": files,
        "output": {
            "path": output_csv.name,
            "rows": len(output_rows),
            "metrics": [
                {
                    key: item[key]
                    for key in (
                        "metric_id",
                        "label",
                        "unit",
                        "evidence_class",
                        "method_id",
                    )
                }
                for item in recipe["rollups"]
            ],
            "sha256": _sha256(output_csv),
        },
    }
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--site-pack", required=True, type=pathlib.Path)
    parser.add_argument("--recipe", required=True, type=pathlib.Path)
    parser.add_argument("--output-csv", required=True, type=pathlib.Path)
    parser.add_argument("--manifest", required=True, type=pathlib.Path)
    args = parser.parse_args()
    manifest = derive(
        args.site_pack, args.recipe, args.output_csv, args.manifest
    )
    print(json.dumps({
        "recipe_id": manifest["recipe_id"],
        "rows": manifest["output"]["rows"],
        "metrics": len(manifest["output"]["metrics"]),
        "sha256": manifest["output"]["sha256"],
    }, indent=2))


if __name__ == "__main__":
    main()
