#!/usr/bin/env python3
"""Ingest a user-supplied CSV or multi-sheet workbook as a session-scoped visual source.

A user attachment is not a registered source. It has no admitted provenance, no licence, no
version and no place in the site pack's source registry, so it must never be silently mixed into
the pack's evidence. This module keeps it separate and honest:

- the file is stored immutably, by content hash, under one session's own upload namespace;
- each sheet is profiled deterministically (columns, inferred types, dates, coordinates,
  candidate entity-name columns) without a model;
- two query paths emit ordinary `idli-result/1` envelopes so the existing renderer, proxy and
  audit surface work unchanged: a standalone profile of the file itself, and a cross-join of its
  candidate entity names against the pinned pack's entity aliases; and
- every uploaded row is `reported` evidence, every result carries a "user-supplied, not yet
  verified" limitation, and every result id and audit record is bound to the uploading session.

A name that does not match the pack is reported explicitly. Non-match is not absence.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import pathlib
import re
import sqlite3
import zipfile
from typing import Any
from xml.etree import ElementTree

try:
    from dss.visual_index.result_service import (
        SAFE_HANDLE, _atomic_write_once, _digest, _key, _stable_json,
    )
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/upload_service.py
    from result_service import (  # type: ignore[no-redef]
        SAFE_HANDLE, _atomic_write_once, _digest, _key, _stable_json,
    )

try:  # Optional: present in some interpreters, absent in the bridge venv.
    import openpyxl  # type: ignore
except Exception:  # pragma: no cover - depends on the host interpreter
    openpyxl = None


MAX_SHEETS = 25
MAX_ROWS = 200_000
MAX_COLUMNS = 200
MAX_SAMPLE_ROWS = 20
MAX_POINTS = 2_000
MAX_UNMATCHED = 200
SAFE_SEGMENT = re.compile(r"[^A-Za-z0-9_.-]+")
SPREADSHEET_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"
DOCUMENT_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
EXCEL_EPOCH = dt.date(1899, 12, 30)
DATE_FORMAT_IDS = set(range(14, 23)) | {27, 30, 36, 45, 46, 47, 50, 57, 58}
DATE_PATTERNS = (
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$"),
    re.compile(r"^\d{4}/\d{1,2}/\d{1,2}$"),
    re.compile(r"^\d{1,2}[-/]\d{1,2}[-/]\d{4}$"),
    re.compile(r"^\d{4}-\d{1,2}$"),
    re.compile(r"^\d{4}-\d{1,2}-\d{1,2}[T ]\d{1,2}:\d{2}"),
)
ENTITY_NAME_HINT = re.compile(
    r"(?i)\b(name|entity|estate|village|hamlet|site|location|place|unit|ward|panchayat|"
    r"habitation|block|division|scheme|household|holder|taxon|species|organisation|"
    r"organization|facility|farm|plot)\b"
)
LATITUDE_HINT = re.compile(r"(?i)^(lat|latitude|y_?coord|ycoord|lat_dd)$")
LONGITUDE_HINT = re.compile(r"(?i)^(lon|long|lng|longitude|x_?coord|xcoord|lon_dd)$")
DATE_NAME_HINT = re.compile(r"(?i)\b(date|month|year|period|time|timestamp|visited|recorded)\b")


UPLOAD_CAPABILITIES: list[dict[str, Any]] = [
    {
        "capability_id": "upload-profile",
        "version": "1.0.0",
        "label": "Profile and visualise a user-supplied table",
        "input_schema": {
            "type": "object",
            "properties": {
                "upload_id": {"type": "string"},
                "sheet": {"type": "string"},
            },
            "required": [],
        },
        "output_views": [
            "upload-sample-table", "upload-metric-series", "upload-observed-points",
            "upload-stat-tiles",
        ],
        "required_planes": ["upload"],
        "optional_planes": [],
        "latency_class": "interactive",
        "evidence_classes": ["reported", "derived"],
        "availability": "ready",
        "scope": "session",
        "reason": "Session-scoped: only the session that uploaded the file may run it.",
    },
    {
        "capability_id": "upload-cross-join",
        "version": "1.0.0",
        "label": "Match user-supplied names against the pack's registered entities",
        "input_schema": {
            "type": "object",
            "properties": {
                "upload_id": {"type": "string"},
                "sheet": {"type": "string"},
                "column": {"type": "string"},
            },
            "required": [],
        },
        "output_views": [
            "upload-match-rates", "upload-matched-entities", "upload-unmatched-names",
        ],
        "required_planes": ["upload", "entity_aliases"],
        "optional_planes": ["events"],
        "latency_class": "interactive",
        "evidence_classes": ["reported", "derived", "missing"],
        "availability": "ready",
        "scope": "session",
        "reason": "Session-scoped: only the session that uploaded the file may run it.",
    },
]


def _segment(value: str, limit: int = 64) -> str:
    cleaned = SAFE_SEGMENT.sub("-", str(value or "").strip()).strip(".-")
    return (cleaned or "anonymous")[:limit]


def _text(value: Any) -> str:
    return " ".join(str(value if value is not None else "").split())


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text(value).replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _header_key(name: str) -> str:
    """Normalise a column header so word-boundary hints survive snake_case and CamelCase."""
    return _key(re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", str(name or "")))


def _looks_like_date(value: Any) -> bool:
    if isinstance(value, (dt.date, dt.datetime)):
        return True
    text = _text(value)
    return bool(text) and any(pattern.match(text) for pattern in DATE_PATTERNS)


def _date_bucket(value: Any) -> str | None:
    if isinstance(value, dt.datetime):
        return f"{value.year:04d}-{value.month:02d}"
    if isinstance(value, dt.date):
        return f"{value.year:04d}-{value.month:02d}"
    text = _text(value)
    match = re.match(r"^(\d{4})[-/](\d{1,2})", text)
    if match:
        return f"{int(match.group(1)):04d}-{int(match.group(2)):02d}"
    match = re.match(r"^(\d{1,2})[-/](\d{1,2})[-/](\d{4})$", text)
    if match:
        return f"{int(match.group(3)):04d}-{int(match.group(2)):02d}"
    return None


# ---------------------------------------------------------------------------- readers


def _read_csv(raw: bytes, name: str) -> list[dict[str, Any]]:
    text = raw.decode("utf-8-sig", errors="replace")
    sample = text[:8192]
    delimiter = ","
    try:
        delimiter = csv.Sniffer().sniff(sample, delimiters=",;\t|").delimiter
    except Exception:
        delimiter = "\t" if name.lower().endswith(".tsv") else ","
    rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
    rows = [row for row in rows if any(_text(cell) for cell in row)]
    if not rows:
        return [{"sheet": pathlib.Path(name).stem or "sheet1", "header": [], "rows": []}]
    header = [_text(cell) for cell in rows[0]][:MAX_COLUMNS]
    body = [row[:MAX_COLUMNS] for row in rows[1:MAX_ROWS + 1]]
    return [{"sheet": pathlib.Path(name).stem or "sheet1", "header": header, "rows": body}]


def _column_index(reference: str) -> int:
    letters = "".join(character for character in reference if character.isalpha())
    index = 0
    for character in letters.upper():
        index = index * 26 + (ord(character) - 64)
    return max(index - 1, 0)


def _serial_to_date(serial: float, with_time: bool) -> str:
    days = int(serial)
    fraction = serial - days
    value = EXCEL_EPOCH + dt.timedelta(days=days)
    if with_time and fraction:
        seconds = round(fraction * 86400)
        return (dt.datetime.combine(value, dt.time()) +
                dt.timedelta(seconds=seconds)).isoformat(sep=" ")
    return value.isoformat()


def _xlsx_date_styles(archive: zipfile.ZipFile) -> dict[int, bool]:
    """Map cell-style index -> whether the style renders a date (and whether it has a time)."""
    try:
        root = ElementTree.fromstring(archive.read("xl/styles.xml"))
    except Exception:
        return {}
    custom: dict[int, str] = {}
    for node in root.iter(f"{SPREADSHEET_NS}numFmt"):
        with_id = node.get("numFmtId")
        if with_id is not None:
            custom[int(with_id)] = node.get("formatCode") or ""
    styles: dict[int, bool] = {}
    container = root.find(f"{SPREADSHEET_NS}cellXfs")
    for index, node in enumerate(list(container) if container is not None else []):
        raw = node.get("numFmtId")
        if raw is None:
            continue
        format_id = int(raw)
        code = custom.get(format_id, "")
        stripped = re.sub(r'"[^"]*"|\[[^\]]*\]', "", code)
        is_date = format_id in DATE_FORMAT_IDS or bool(
            re.search(r"[ymd]", stripped) and not re.fullmatch(r"[#0.,%\s]*", stripped)
        )
        if is_date:
            styles[index] = bool(re.search(r"[hs]", stripped)) or format_id in {22, 45, 46, 47}
    return styles


def _read_xlsx_stdlib(path: pathlib.Path) -> list[dict[str, Any]]:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        shared: list[str] = []
        if "xl/sharedStrings.xml" in names:
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.iter(f"{SPREADSHEET_NS}si"):
                shared.append("".join(
                    node.text or "" for node in item.iter(f"{SPREADSHEET_NS}t")
                ))
        targets: dict[str, str] = {}
        if "xl/_rels/workbook.xml.rels" in names:
            root = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            for node in root.iter(f"{PACKAGE_REL_NS}Relationship"):
                target = node.get("Target") or ""
                targets[node.get("Id") or ""] = (
                    target[1:] if target.startswith("/") else "xl/" + target.lstrip("./")
                )
        date_styles = _xlsx_date_styles(archive)
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        sheets: list[dict[str, Any]] = []
        for order, node in enumerate(workbook.iter(f"{SPREADSHEET_NS}sheet")):
            if len(sheets) >= MAX_SHEETS:
                break
            name = node.get("name") or f"sheet{order + 1}"
            target = targets.get(node.get(f"{DOCUMENT_REL_NS}id") or "")
            if target not in names:
                target = f"xl/worksheets/sheet{order + 1}.xml"
            if target not in names:
                continue
            grid: list[list[Any]] = []
            root = ElementTree.fromstring(archive.read(target))
            for row_node in root.iter(f"{SPREADSHEET_NS}row"):
                if len(grid) >= MAX_ROWS + 1:
                    break
                row: list[Any] = []
                for cell in row_node.iter(f"{SPREADSHEET_NS}c"):
                    index = _column_index(cell.get("r") or "")
                    while len(row) <= index:
                        row.append("")
                    cell_type = cell.get("t") or "n"
                    style = cell.get("s")
                    value_node = cell.find(f"{SPREADSHEET_NS}v")
                    raw = value_node.text if value_node is not None else None
                    if cell_type == "s" and raw is not None:
                        value: Any = shared[int(raw)] if int(raw) < len(shared) else ""
                    elif cell_type == "inlineStr":
                        value = "".join(
                            item.text or "" for item in cell.iter(f"{SPREADSHEET_NS}t")
                        )
                    elif cell_type == "b":
                        value = bool(int(raw or 0))
                    elif cell_type in {"str", "e"}:
                        value = raw or ""
                    elif raw is None:
                        value = ""
                    else:
                        number = float(raw)
                        style_index = int(style) if style is not None else None
                        if style_index is not None and style_index in date_styles:
                            value = _serial_to_date(number, date_styles[style_index])
                        else:
                            value = int(number) if number.is_integer() else number
                    row[index] = value
                grid.append(row[:MAX_COLUMNS])
            grid = [row for row in grid if any(_text(cell) for cell in row)]
            header = [_text(cell) for cell in grid[0]] if grid else []
            sheets.append({"sheet": name, "header": header, "rows": grid[1:]})
    return sheets


def _read_xlsx_openpyxl(path: pathlib.Path) -> list[dict[str, Any]]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheets = []
    for worksheet in workbook.worksheets[:MAX_SHEETS]:
        grid: list[list[Any]] = []
        for row in worksheet.iter_rows(values_only=True):
            if len(grid) >= MAX_ROWS + 1:
                break
            values = [
                value.isoformat() if isinstance(value, (dt.date, dt.datetime)) else value
                for value in list(row)[:MAX_COLUMNS]
            ]
            if any(_text(value) for value in values):
                grid.append(values)
        header = [_text(cell) for cell in grid[0]] if grid else []
        sheets.append({"sheet": worksheet.title, "header": header, "rows": grid[1:]})
    workbook.close()
    return sheets


def read_sheets(
    path: pathlib.Path, name_hint: str | None = None
) -> tuple[list[dict[str, Any]], str]:
    """Return (sheets, reader_name). Reader choice is recorded in the upload manifest.

    `name_hint` names the single sheet of a flat CSV after the file the user actually attached,
    because the stored copy is named by content hash.
    """
    suffix = path.suffix.lower()
    if suffix in {".csv", ".tsv", ".txt"}:
        return _read_csv(path.read_bytes(), name_hint or path.name), "stdlib-csv"
    if suffix in {".xlsx", ".xlsm"}:
        if openpyxl is not None:
            return _read_xlsx_openpyxl(path), f"openpyxl-{getattr(openpyxl, '__version__', '?')}"
        return _read_xlsx_stdlib(path), "stdlib-zipfile-xml"
    raise ValueError(f"unsupported upload type: {suffix or path.name}")


# ---------------------------------------------------------------------------- profiling


def profile_sheet(sheet: dict[str, Any]) -> dict[str, Any]:
    header = [name or f"column_{index + 1}" for index, name in enumerate(sheet["header"])]
    rows = sheet["rows"]
    columns = []
    for index, name in enumerate(header):
        values = [row[index] if index < len(row) else "" for row in rows]
        present = [value for value in values if _text(value) != ""]
        numbers = [_number(value) for value in present]
        numeric = [value for value in numbers if value is not None]
        dates = [value for value in present if _looks_like_date(value)]
        distinct = {_text(value) for value in present}
        if present and len(numeric) == len(present) and not dates:
            inferred = "numeric"
        elif present and len(dates) >= max(1, int(0.8 * len(present))):
            inferred = "date"
        elif not present:
            inferred = "empty"
        else:
            inferred = "text"
        column = {
            "column": name,
            "index": index,
            "inferred_type": inferred,
            "non_null": len(present),
            "distinct": len(distinct),
            "examples": [_text(value) for value in present[:3]],
        }
        if inferred == "numeric" and numeric:
            column["minimum"] = min(numeric)
            column["maximum"] = max(numeric)
            column["mean"] = sum(numeric) / len(numeric)
        if inferred == "date" and present:
            buckets = sorted(
                bucket for bucket in (_date_bucket(value) for value in present) if bucket
            )
            column["first"] = buckets[0] if buckets else None
            column["last"] = buckets[-1] if buckets else None
        columns.append(column)
    numeric_columns = [item["column"] for item in columns if item["inferred_type"] == "numeric"]
    date_columns = [item["column"] for item in columns if item["inferred_type"] == "date"]
    date_columns += [
        item["column"] for item in columns
        if item["column"] not in date_columns
        and DATE_NAME_HINT.search(_header_key(item["column"]))
        and item["inferred_type"] != "numeric"
    ]
    latitude = longitude = None
    for item in columns:
        if item["inferred_type"] != "numeric":
            continue
        low, high = item.get("minimum"), item.get("maximum")
        hint = _header_key(item["column"]).replace(" ", "_")
        if latitude is None and LATITUDE_HINT.match(hint) and \
                low is not None and -90 <= low and high <= 90:
            latitude = item["column"]
        if longitude is None and LONGITUDE_HINT.match(hint) and \
                low is not None and -180 <= low and high <= 180:
            longitude = item["column"]
    candidates = []
    for item in columns:
        if item["inferred_type"] != "text" or item["distinct"] < 2:
            continue
        hinted = bool(ENTITY_NAME_HINT.search(_header_key(item["column"])))
        selective = item["non_null"] and item["distinct"] <= max(2, int(0.8 * item["non_null"]))
        if hinted or selective:
            candidates.append({
                "column": item["column"],
                "distinct": item["distinct"],
                "name_hint": hinted,
                "examples": item["examples"],
            })
    candidates.sort(key=lambda item: (not item["name_hint"], item["distinct"]))
    return {
        "sheet": sheet["sheet"],
        "row_count": len(rows),
        "column_count": len(header),
        "columns": columns,
        "numeric_columns": numeric_columns,
        "date_columns": date_columns,
        "latitude_column": latitude,
        "longitude_column": longitude,
        "entity_candidates": candidates[:8],
    }


class UploadService:
    """Session-scoped ingestion and two idli-result/1 query paths for user-supplied tables."""

    def __init__(
        self,
        state_root: pathlib.Path,
        index_path: pathlib.Path | None = None,
        site: dict[str, Any] | None = None,
        pack_digest: str = "",
        synthetic: bool = False,
    ):
        self.state_root = pathlib.Path(state_root).resolve()
        self.index_path = pathlib.Path(index_path).resolve() if index_path else None
        self.site = site or {"site_id": "unbound", "label": "Unbound site"}
        self.pack_digest = pack_digest
        self.synthetic = bool(synthetic)
        self.upload_root = self.state_root / "uploads"

    @classmethod
    def from_result_service(cls, service: Any) -> "UploadService":
        return cls(
            service.state_root, service.index_path, service.site, service.pack_digest,
            bool(getattr(service, "synthetic", False)),
        )

    def connect(self) -> sqlite3.Connection:
        if self.index_path is None or not self.index_path.is_file():
            raise FileNotFoundError("no site index is bound to this upload service")
        connection = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    # ------------------------------------------------------------------ ingestion

    def ingest(
        self, session_id: str, path: pathlib.Path, display_name: str | None = None
    ) -> dict[str, Any]:
        source = pathlib.Path(path)
        if not source.is_file():
            raise FileNotFoundError(f"upload not found: {source}")
        raw = source.read_bytes()
        content_sha256 = _digest(raw).split(":", 1)[1]
        upload_id = content_sha256[:16]
        session = _segment(session_id, 80)
        root = self.upload_root / session / upload_id
        existing = root / "manifest.json"
        if existing.is_file():
            # Same session, same bytes: the stored source is immutable, so re-ingesting is a
            # no-op that returns the original manifest instead of rewriting it.
            return json.loads(existing.read_text(encoding="utf-8"))
        name = _segment(display_name or source.name, 180)
        suffix = source.suffix.lower() or ".csv"
        stored = root / f"source{suffix}"
        _atomic_write_once(stored, raw)
        sheets, reader = read_sheets(stored, name)
        profiles = [profile_sheet(sheet) for sheet in sheets]
        manifest = {
            "schema_version": "visual-upload/1",
            "upload_id": upload_id,
            "session_id": session,
            "display_name": name,
            "stored_path": str(stored),
            "reader": reader,
            "content_sha256": content_sha256,
            "bytes": len(raw),
            "ingested_at": dt.datetime.now().isoformat(timespec="seconds"),
            "sheets": profiles,
            "capabilities": [item["capability_id"] for item in UPLOAD_CAPABILITIES],
            "evidence_class": "reported",
            "note": (
                "User-supplied data. It is immutable, session-scoped and not part of the site "
                "pack's registered sources."
            ),
        }
        _atomic_write_once(
            root / "manifest.json",
            (json.dumps(manifest, indent=2, ensure_ascii=False, default=str) + "\n").encode(),
        )
        return manifest

    def load_manifest(self, session_id: str, upload_id: str) -> dict[str, Any] | None:
        session = _segment(session_id, 80)
        if not SAFE_HANDLE.fullmatch(str(upload_id or "")):
            return None
        path = self.upload_root / session / upload_id / "manifest.json"
        if not path.is_file():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def list_uploads(self, session_id: str) -> list[dict[str, Any]]:
        session = _segment(session_id, 80)
        root = self.upload_root / session
        if not root.is_dir():
            return []
        listed = []
        for child in sorted(root.iterdir()):
            manifest_path = child / "manifest.json"
            if manifest_path.is_file():
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                listed.append({
                    "upload_id": manifest["upload_id"],
                    "display_name": manifest["display_name"],
                    "ingested_at": manifest["ingested_at"],
                    "sheets": [item["sheet"] for item in manifest["sheets"]],
                })
        return listed

    def _rows(self, manifest: dict[str, Any], sheet_name: str) -> tuple[
        dict[str, Any], list[dict[str, Any]]
    ]:
        sheets, _ = read_sheets(
            pathlib.Path(manifest["stored_path"]), manifest["display_name"]
        )
        wanted = next(
            (item for item in sheets if item["sheet"] == sheet_name),
            sheets[0] if sheets else None,
        )
        if wanted is None:
            raise ValueError("the uploaded file has no readable sheet")
        header = [
            name or f"column_{index + 1}" for index, name in enumerate(wanted["header"])
        ]
        records = [
            {
                header[index]: (row[index] if index < len(row) else "")
                for index in range(len(header))
            }
            for row in wanted["rows"]
        ]
        profile = next(
            (item for item in manifest["sheets"] if item["sheet"] == wanted["sheet"]),
            manifest["sheets"][0],
        )
        return profile, records

    # ------------------------------------------------------------------ envelope helpers

    def _result_id(self, session_id: str, mode: str, material: dict[str, Any]) -> str:
        session = _segment(session_id, 40)
        digest = _digest({"session": session, "mode": mode, **material}).split(":", 1)[1]
        return f"result-upl-{session}-{digest[:16]}"

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

    def _base(
        self, result_id: str, request_id: str, capability_id: str, manifest: dict[str, Any],
        original: str, resolved: str, bindings: dict[str, Any], headline: str,
        evidence_classes: list[str], status: str,
    ) -> dict[str, Any]:
        site = {
            "site_id": self.site.get("site_id"),
            "label": self.site.get("label"),
            "pack_digest": self.pack_digest,
        }
        if self.synthetic:
            site["synthetic"] = True
        descriptor = next(
            item for item in UPLOAD_CAPABILITIES if item["capability_id"] == capability_id
        )
        result = {
            "schema_version": "idli-result/1",
            "result_id": result_id,
            "request_id": request_id,
            "revision": 1,
            "status": status,
            "site": site,
            "question": {"original": original, "resolved": resolved, "bindings": bindings},
            "answer": {
                "headline": headline, "detail": "", "evidence_classes": evidence_classes,
            },
            "visuals": [],
            "limitations": [
                self._limitation(
                    "user-supplied-unverified",
                    "This is user-supplied data, not yet verified against registered sources.",
                    affects=["answer"],
                ),
            ],
            "actions": [],
            "audit": {
                "audit_id": f"{result_id}/1",
                "source_versions": [{
                    "source_id": f"upload:{manifest['upload_id']}",
                    "version": manifest["ingested_at"],
                    "digest": "sha256:" + manifest["content_sha256"],
                    "synthetic": self.synthetic,
                    "user_supplied": True,
                    "title": manifest["display_name"],
                    "reader": manifest["reader"],
                }],
                "capability_runs": [{
                    "capability_id": capability_id,
                    "version": descriptor["version"],
                    "status": "partial" if status == "partial" else (
                        "blocked" if status == "blocked" else "complete"
                    ),
                }],
                "query_hash": _digest({
                    "capability_id": capability_id,
                    "upload": manifest["content_sha256"],
                    "bindings": bindings,
                }),
                # Session binding keeps an upload-derived result inside the session that
                # produced it; other sessions must not list or reuse it as site evidence.
                "session_binding": {
                    "session_id": manifest["session_id"],
                    "upload_id": manifest["upload_id"],
                    "content_sha256": manifest["content_sha256"],
                    "scope": "session",
                },
            },
        }
        if self.synthetic:
            result["limitations"].append(self._limitation(
                "synthetic-data",
                "The pinned site pack is synthetic test data and is not evidence about a real "
                "place.",
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
            declared = [
                reference["digest"]
                for visual in result["visuals"]
                for reference in (
                    [layer["data_ref"] for layer in visual["layers"]]
                    + [item["data_ref"] for item in visual.get("drilldowns") or []]
                )
                if reference.get("handle") == handle
            ]
            if _digest(payload) not in declared:
                raise RuntimeError(f"data-ref digest mismatch: {handle}")
            _atomic_write_once(
                root / "data" / f"{handle}{suffix}", _stable_json(payload).encode()
            )
        _atomic_write_once(
            root / "result.json",
            (json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n").encode(),
        )
        return result

    # ------------------------------------------------------------------ path a: profile

    def profile_result(
        self, session_id: str, upload_id: str, request_id: str, question: str = "",
        sheet: str | None = None,
    ) -> dict[str, Any]:
        manifest = self.load_manifest(session_id, upload_id)
        if manifest is None:
            raise LookupError(f"unknown upload for this session: {upload_id}")
        profile, records = self._rows(manifest, sheet or "")
        sheet_name = profile["sheet"]
        bindings = {
            "upload_id": manifest["upload_id"], "sheet": sheet_name,
            "session_id": manifest["session_id"],
        }
        result_id = self._result_id(
            manifest["session_id"], "profile",
            {"upload": manifest["content_sha256"], "sheet": sheet_name,
             "request_id": request_id},
        )
        headline = (
            f"User-supplied file “{manifest['display_name']}” sheet “{sheet_name}”: "
            f"{profile['row_count']:,} rows and {profile['column_count']:,} columns were read "
            f"and profiled."
        )
        result = self._base(
            result_id, request_id, "upload-profile", manifest,
            question or f"Visualise {manifest['display_name']}.",
            f"Profile sheet {sheet_name} of the session's uploaded file and show what it contains.",
            bindings, headline, ["reported", "derived"], "complete",
        )
        result["answer"]["detail"] = (
            "Every row here is reported by the uploaded file itself. Nothing has been matched to "
            "a registered source, and no value was corrected, filled or modelled."
        )
        payloads: dict[str, tuple[str, Any]] = {}
        visuals: list[dict[str, Any]] = []
        scope = {"aoi_ids": ["target"], "time": {"start": None, "end": None}}
        shared_limitations = [item for item in result["limitations"]]

        sample = records[:MAX_SAMPLE_ROWS]
        sample_ref = self._data_ref("upload-sample-rows", "application/json", sample)
        schema_rows = profile["columns"]
        schema_ref = self._data_ref("upload-column-profile", "application/json", schema_rows)
        visuals.append({
            "visual_id": "upload-sample",
            "visual_type": "table",
            "view": "upload-sample-table",
            "title": f"{manifest['display_name']} · {sheet_name}",
            "priority": "primary",
            "status": "ready",
            "scope": scope,
            "layers": [{
                "layer_id": "upload-sample-rows",
                "evidence_class": "reported",
                "geometry_type": "table",
                "data_ref": sample_ref,
                "legend": {"label": "Uploaded rows (sample)"},
                "style_hint": {"palette_role": "reported"},
            }],
            "summary": {
                "headline": headline,
                "denominators": {
                    "rows": profile["row_count"], "columns": profile["column_count"],
                    "rows_shown": len(sample),
                },
            },
            "drilldowns": [{
                "action_id": "inspect-column-profile",
                "label": "Inspect inferred column types",
                "data_ref": schema_ref,
            }],
            "limitations": shared_limitations,
        })
        payloads["upload-sample-rows"] = ("application/json", sample)
        payloads["upload-column-profile"] = ("application/json", schema_rows)

        date_column = next(iter(profile["date_columns"]), None)
        value_column = next(iter(profile["numeric_columns"]), None)
        if date_column and value_column:
            buckets: dict[str, list[float]] = {}
            for record in records:
                bucket = _date_bucket(record.get(date_column))
                value = _number(record.get(value_column))
                if bucket and value is not None:
                    buckets.setdefault(bucket, []).append(value)
            series = [
                {
                    "bucket": bucket,
                    "year": int(bucket[:4]),
                    "month": int(bucket[5:7]),
                    "mean": sum(values) / len(values),
                    "sum": sum(values),
                    "rows": len(values),
                }
                for bucket, values in sorted(buckets.items())
            ]
            if series:
                series_ref = self._data_ref("upload-series", "application/json", series)
                visuals.append({
                    "visual_id": "upload-series",
                    "visual_type": "chart",
                    "view": "upload-metric-series",
                    "title": f"{value_column} by {date_column} (uploaded)",
                    "priority": "supporting",
                    "status": "ready",
                    "scope": {
                        "aoi_ids": ["target"],
                        "time": {"start": series[0]["bucket"], "end": series[-1]["bucket"]},
                    },
                    "layers": [{
                        "layer_id": "upload-series",
                        "evidence_class": "reported",
                        "geometry_type": "series",
                        "data_ref": series_ref,
                        "legend": {"label": f"{value_column} (monthly mean of uploaded rows)"},
                        "style_hint": {"palette_role": "reported"},
                    }],
                    "summary": {
                        "headline": (
                            f"{len(series):,} monthly buckets of {value_column} were derived from "
                            f"the uploaded {date_column} column."
                        ),
                        "denominators": {
                            "buckets": len(series), "rows": sum(item["rows"] for item in series),
                        },
                    },
                    "drilldowns": [],
                    "limitations": shared_limitations,
                })
                payloads["upload-series"] = ("application/json", series)

        latitude, longitude = profile["latitude_column"], profile["longitude_column"]
        if latitude and longitude:
            features = []
            for index, record in enumerate(records[:MAX_POINTS]):
                lat, lon = _number(record.get(latitude)), _number(record.get(longitude))
                if lat is None or lon is None or not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    continue
                features.append({
                    "type": "Feature",
                    "id": f"upload-row-{index + 2}",
                    "geometry": {"type": "Point", "coordinates": [lon, lat]},
                    "properties": {
                        "source_row": index + 2,
                        **{key: value for key, value in record.items()},
                    },
                })
            if features:
                points = {"type": "FeatureCollection", "features": features}
                points_ref = self._data_ref(
                    "upload-points", "application/geo+json", points
                )
                visuals.insert(0, {
                    "visual_id": "upload-points",
                    "visual_type": "map",
                    "view": "upload-observed-points",
                    "title": f"Where the uploaded rows say they are · {sheet_name}",
                    "priority": "primary",
                    "status": "ready",
                    "scope": scope,
                    "layers": [{
                        "layer_id": "upload-points",
                        "evidence_class": "reported",
                        "geometry_type": "point",
                        "data_ref": points_ref,
                        "legend": {"label": "Uploaded rows with coordinates"},
                        "style_hint": {"palette_role": "reported"},
                    }],
                    "summary": {
                        "headline": (
                            f"{len(features):,} uploaded rows carry usable "
                            f"{latitude}/{longitude} coordinates."
                        ),
                        "denominators": {
                            "points": len(features), "rows": profile["row_count"],
                        },
                    },
                    "drilldowns": [],
                    "limitations": shared_limitations,
                })
                payloads["upload-points"] = ("application/geo+json", points)
                visuals[1]["priority"] = "supporting"

        tiles = [
            {"label": "Rows", "value": profile["row_count"], "unit": "rows"},
            {"label": "Columns", "value": profile["column_count"], "unit": "columns"},
            {"label": "Sheets in file", "value": len(manifest["sheets"]), "unit": "sheets"},
            {
                "label": "Numeric columns", "value": len(profile["numeric_columns"]),
                "unit": "columns",
            },
            {
                "label": "Candidate name columns",
                "value": len(profile["entity_candidates"]), "unit": "columns",
            },
        ] + [
            {
                "label": f"{item['column']} range",
                "value": f"{item['minimum']:.4g} – {item['maximum']:.4g}",
                "unit": "reported",
            }
            for item in profile["columns"]
            if item["inferred_type"] == "numeric" and item.get("minimum") is not None
        ][:4]
        tiles_ref = self._data_ref("upload-stat-tiles", "application/json", tiles)
        visuals.append({
            "visual_id": "upload-stats",
            "visual_type": "metric",
            "view": "upload-stat-tiles",
            "title": "What the uploaded file contains",
            "priority": "supporting",
            "status": "ready",
            "scope": scope,
            "layers": [{
                "layer_id": "upload-stat-tiles",
                "evidence_class": "derived",
                "geometry_type": "table",
                "data_ref": tiles_ref,
                "legend": {"label": "Counts and ranges from the uploaded rows"},
                "style_hint": {"palette_role": "derived"},
            }],
            "summary": {"headline": headline, "denominators": {"tiles": len(tiles)}},
            "drilldowns": [],
            "limitations": shared_limitations,
        })
        payloads["upload-stat-tiles"] = ("application/json", tiles)

        result["visuals"] = visuals
        if not profile["entity_candidates"]:
            result["limitations"].append(self._limitation(
                "no-entity-name-column",
                "No column looks like an entity name, so this file cannot yet be matched against "
                "the pack's registered entities.",
                severity="info", affects=["answer"],
            ))
        else:
            result["actions"].append({
                "action_id": "cross-join-vs-pack",
                "kind": "run_capability",
                "label": "Match these names against the site's registered entities",
                "capability_id": "upload-cross-join",
                "arguments": {
                    "upload_id": manifest["upload_id"], "sheet": sheet_name,
                    "column": profile["entity_candidates"][0]["column"],
                },
                "requires_confirmation": True,
            })
        for other in manifest["sheets"]:
            if other["sheet"] != sheet_name:
                result["actions"].append({
                    "action_id": f"profile-sheet-{_segment(other['sheet'], 40)}",
                    "kind": "follow_up",
                    "label": f"Profile sheet “{other['sheet']}”",
                    "capability_id": "upload-profile",
                    "arguments": {
                        "upload_id": manifest["upload_id"], "sheet": other["sheet"],
                    },
                    "requires_confirmation": True,
                })
        return self._write(result, payloads)

    # ------------------------------------------------------------------ path b: cross join

    def cross_join_result(
        self, session_id: str, upload_id: str, request_id: str, question: str = "",
        sheet: str | None = None, column: str | None = None,
    ) -> dict[str, Any]:
        manifest = self.load_manifest(session_id, upload_id)
        if manifest is None:
            raise LookupError(f"unknown upload for this session: {upload_id}")
        profile, records = self._rows(manifest, sheet or "")
        sheet_name = profile["sheet"]
        candidates = [item["column"] for item in profile["entity_candidates"]]
        if column and column not in {item["column"] for item in profile["columns"]}:
            raise ValueError(f"sheet {sheet_name} has no column {column}")
        chosen = column or (candidates[0] if candidates else None)
        bindings = {
            "upload_id": manifest["upload_id"], "sheet": sheet_name,
            "column": chosen, "session_id": manifest["session_id"],
        }
        result_id = self._result_id(
            manifest["session_id"], "cross-join",
            {"upload": manifest["content_sha256"], "sheet": sheet_name, "column": chosen,
             "request_id": request_id},
        )
        if chosen is None:
            result = self._base(
                result_id, request_id, "upload-cross-join", manifest,
                question or f"Match {manifest['display_name']} against the site.",
                "Match user-supplied names against the pack's registered entity aliases.",
                bindings,
                "No column in this sheet looks like an entity name, so no match could be tried.",
                ["missing"], "blocked",
            )
            result["limitations"].append(self._limitation(
                "no-entity-name-column",
                "Choose a text column that holds names before matching against the pack.",
                severity="error", affects=["answer"],
            ))
            return self._write(result, {})

        # Aggregate the uploaded rows by their reported name before matching, so the match rate
        # is about distinct names and the joined values stay traceable to their own rows.
        value_column = next(iter(profile["numeric_columns"]), None)
        grouped: dict[str, dict[str, Any]] = {}
        for index, record in enumerate(records):
            # Keep the verbatim spelling the user supplied; normalisation happens in the key.
            raw = str(record.get(chosen) if record.get(chosen) is not None else "").strip()
            if not raw:
                continue
            item = grouped.setdefault(raw, {
                "uploaded_name": raw, "alias_key": _key(raw), "rows": 0,
                "source_rows": [], "values": [],
            })
            item["rows"] += 1
            if len(item["source_rows"]) < 25:
                item["source_rows"].append(index + 2)
            value = _number(record.get(value_column)) if value_column else None
            if value is not None:
                item["values"].append(value)

        with self.connect() as connection:
            aliases = {
                row["alias_key"]: {
                    "entity_id": row["entity_id"], "alias": row["alias"],
                    "canonical_name": row["canonical_name"],
                    "display_name": row["display_name"],
                }
                for row in connection.execute(
                    """SELECT a.alias_key,a.alias,a.entity_id,e.canonical_name,e.display_name
                       FROM entity_aliases a JOIN entities e ON e.entity_id=a.entity_id"""
                )
            }
            locations = {
                row["entity_id"]: {
                    "latitude": row["latitude"], "longitude": row["longitude"],
                    "records": row["records"],
                }
                for row in connection.execute(
                    """SELECT entity_id,AVG(latitude) AS latitude,AVG(longitude) AS longitude,
                              COUNT(*) AS records
                       FROM events WHERE entity_id IS NOT NULL AND latitude IS NOT NULL
                         AND longitude IS NOT NULL
                       GROUP BY entity_id"""
                )
            }
            registered_entities = connection.execute(
                "SELECT COUNT(*) FROM entities"
            ).fetchone()[0]

        matched_rows: list[dict[str, Any]] = []
        unmatched_rows: list[dict[str, Any]] = []
        for item in sorted(grouped.values(), key=lambda entry: entry["uploaded_name"]):
            alias = aliases.get(item["alias_key"])
            values = item["values"]
            summary = {
                "uploaded_name": item["uploaded_name"],
                "normalised_key": item["alias_key"],
                "uploaded_rows": item["rows"],
                "source_rows": item["source_rows"],
                "value_column": value_column,
                "value_sum": sum(values) if values else None,
                "value_mean": (sum(values) / len(values)) if values else None,
            }
            if alias:
                matched_rows.append({
                    **summary,
                    "entity_id": alias["entity_id"],
                    "matched_alias": alias["alias"],
                    "canonical_name": alias["canonical_name"],
                    "display_name": alias["display_name"],
                    "match_type": (
                        "exact" if alias["alias"] == item["uploaded_name"]
                        else "normalised"
                    ),
                })
            else:
                unmatched_rows.append(summary)

        distinct_names = len(grouped)
        matched_count = len(matched_rows)
        match_rate = (matched_count / distinct_names) if distinct_names else 0.0
        headline = (
            f"{matched_count:,} of {distinct_names:,} uploaded names in “{chosen}” matched a "
            f"registered entity ({match_rate:.0%}); {len(unmatched_rows):,} did not."
        )
        status = "partial" if unmatched_rows else "complete"
        result = self._base(
            result_id, request_id, "upload-cross-join", manifest,
            question or f"Match {manifest['display_name']} against the site.",
            (
                f"Match the uploaded {chosen} values against the pack's registered entity "
                "aliases, exactly and after case/space normalisation."
            ),
            bindings, headline, ["reported", "derived", "missing"], status,
        )
        result["answer"]["detail"] = (
            "Matching is by name only. A name that did not match may still be a real place or "
            "entity that this pack has not registered; a non-match is not absence."
        )
        shared_limitations = [
            self._limitation(
                "name-join-only",
                "Rows were joined to entities by name alone, without coordinates, dates or an "
                "admitted crosswalk.",
                affects=["upload-match-rates", "upload-matched-entities", "answer"],
            ),
            self._limitation(
                "non-match-is-not-absence",
                "Unmatched names are listed in full. A non-match means this pack has no alias "
                "for that name, not that the place or entity does not exist.",
                affects=["upload-unmatched-names", "answer"],
            ),
        ]
        result["limitations"].extend(shared_limitations)

        rates = [{
            "column": chosen,
            "sheet": sheet_name,
            "uploaded_rows": profile["row_count"],
            "distinct_names": distinct_names,
            "matched_names": matched_count,
            "unmatched_names": len(unmatched_rows),
            "match_rate": round(match_rate, 4),
            "registered_entities": registered_entities,
        }] + [{
            "column": item["column"],
            "sheet": sheet_name,
            "uploaded_rows": profile["row_count"],
            "distinct_names": item["distinct"],
            "matched_names": None,
            "unmatched_names": None,
            "match_rate": None,
            "registered_entities": registered_entities,
        } for item in profile["entity_candidates"] if item["column"] != chosen]
        rates_ref = self._data_ref("upload-match-rates", "application/json", rates)
        matched_ref = self._data_ref("upload-matched-names", "application/json", matched_rows)
        unmatched_ref = self._data_ref(
            "upload-unmatched-names", "application/json", unmatched_rows[:MAX_UNMATCHED]
        )
        scope = {"aoi_ids": ["target"], "time": {"start": None, "end": None}}
        payloads: dict[str, tuple[str, Any]] = {
            "upload-match-rates": ("application/json", rates),
            "upload-matched-names": ("application/json", matched_rows),
            "upload-unmatched-names": ("application/json", unmatched_rows[:MAX_UNMATCHED]),
        }
        visuals: list[dict[str, Any]] = []

        features = []
        for item in matched_rows:
            location = locations.get(item["entity_id"])
            if not location or location["latitude"] is None:
                continue
            features.append({
                "type": "Feature",
                "id": item["entity_id"],
                "geometry": {
                    "type": "Point",
                    "coordinates": [location["longitude"], location["latitude"]],
                },
                "properties": {
                    "uploaded_name": item["uploaded_name"],
                    "display_name": item["display_name"],
                    "canonical_name": item["canonical_name"],
                    "match_type": item["match_type"],
                    "uploaded_rows": item["uploaded_rows"],
                    "source_rows": item["source_rows"],
                    "value_column": item["value_column"],
                    "value_sum": item["value_sum"],
                    "value_mean": item["value_mean"],
                    "indexed_records": location["records"],
                },
            })
        if features:
            joined = {"type": "FeatureCollection", "features": features}
            joined_ref = self._data_ref("upload-joined-points", "application/geo+json", joined)
            visuals.append({
                "visual_id": "upload-matched-entities",
                "visual_type": "map",
                "view": "upload-matched-entities",
                "title": "Uploaded values at known entity locations",
                "priority": "primary",
                "status": "partial",
                "scope": scope,
                "layers": [{
                    "layer_id": "upload-joined-points",
                    "evidence_class": "reported",
                    "geometry_type": "point",
                    "data_ref": joined_ref,
                    "legend": {"label": "Uploaded values joined to registered entities"},
                    "style_hint": {
                        "palette_role": "reported", "size_field": "uploaded_rows",
                    },
                }],
                "summary": {
                    "headline": headline,
                    "denominators": {
                        "matched_names": matched_count,
                        "mapped_entities": len(features),
                        "distinct_names": distinct_names,
                    },
                },
                "drilldowns": [{
                    "action_id": "inspect-matched-names",
                    "label": "Inspect matched names and their uploaded rows",
                    "data_ref": matched_ref,
                }],
                "limitations": shared_limitations,
            })
            payloads["upload-joined-points"] = ("application/geo+json", joined)

        visuals.append({
            "visual_id": "upload-match-rates",
            "visual_type": "table",
            "view": "upload-match-rates",
            "title": f"Match rate: uploaded “{chosen}” versus registered entities",
            "priority": "primary" if not features else "supporting",
            "status": "ready",
            "scope": scope,
            "layers": [{
                "layer_id": "upload-match-rates",
                "evidence_class": "derived",
                "geometry_type": "table",
                "data_ref": rates_ref,
                "legend": {"label": "Name match rate by candidate column"},
                "style_hint": {"palette_role": "derived", "value_fields": ["match_rate"]},
            }],
            "summary": {
                "headline": headline,
                "denominators": {
                    "distinct_names": distinct_names, "matched_names": matched_count,
                    "registered_entities": registered_entities,
                },
            },
            "drilldowns": [{
                "action_id": "inspect-matched-names",
                "label": "Inspect matched names",
                "data_ref": matched_ref,
            }],
            "limitations": shared_limitations,
        })
        visuals.append({
            "visual_id": "upload-unmatched-names",
            "visual_type": "table",
            "view": "upload-unmatched-names",
            "title": "Uploaded names with no registered alias",
            "priority": "supporting",
            "status": "partial" if unmatched_rows else "ready",
            "scope": scope,
            "layers": [{
                "layer_id": "upload-unmatched-names",
                "evidence_class": "missing",
                "geometry_type": "table",
                "data_ref": unmatched_ref,
                "legend": {"label": "Names this pack does not register"},
                "style_hint": {"palette_role": "missing"},
            }],
            "summary": {
                "headline": (
                    f"{len(unmatched_rows):,} uploaded names have no alias in this pack."
                ),
                "denominators": {
                    "unmatched_names": len(unmatched_rows),
                    "listed": len(unmatched_rows[:MAX_UNMATCHED]),
                },
            },
            "drilldowns": [{
                "action_id": "inspect-unmatched-names",
                "label": "Inspect every unmatched name",
                "data_ref": unmatched_ref,
            }],
            "limitations": shared_limitations,
        })
        result["visuals"] = visuals
        result["actions"].append({
            "action_id": "profile-upload",
            "kind": "follow_up",
            "label": "Show the uploaded sheet on its own",
            "capability_id": "upload-profile",
            "arguments": {"upload_id": manifest["upload_id"], "sheet": sheet_name},
            "requires_confirmation": True,
        })
        return self._write(result, payloads)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path)
    parser.add_argument("--session", required=True)
    parser.add_argument("--file", type=pathlib.Path, required=True)
    parser.add_argument("--mode", choices=("profile", "cross-join", "ingest"),
                        default="profile")
    parser.add_argument("--sheet")
    parser.add_argument("--column")
    parser.add_argument("--request-id", default="upload-cli")
    args = parser.parse_args(argv)
    service = UploadService(args.state, args.index)
    manifest = service.ingest(args.session, args.file)
    if args.mode == "ingest":
        print(json.dumps(manifest, indent=2, ensure_ascii=False, default=str))
        return 0
    if args.mode == "profile":
        value = service.profile_result(
            args.session, manifest["upload_id"], args.request_id, "", args.sheet
        )
    else:
        value = service.cross_join_result(
            args.session, manifest["upload_id"], args.request_id, "", args.sheet, args.column
        )
    print(json.dumps(value, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
