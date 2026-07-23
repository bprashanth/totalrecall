"""Deterministic, self-contained field-map artefacts for audited ecology skill results."""

from __future__ import annotations

import csv
import base64
import html
import io
import json
import math
import pathlib
import re
from typing import Any


def _distance_km(a: dict, b: dict) -> float:
    lat = math.radians((a["lat"] + b["lat"]) / 2)
    dy = (a["lat"] - b["lat"]) * 111.32
    dx = (a["lon"] - b["lon"]) * 111.32 * math.cos(lat)
    return math.hypot(dx, dy)


def select_waypoints(rows: list[dict], score_field: str = "score", limit: int = 12,
                     minimum_separation_km: float = 0.16) -> list[dict]:
    """Select high-scoring, well-spaced points with stable field IDs."""
    ranked = sorted(
        (r for r in rows if isinstance(r.get("lat"), (int, float)) and
         isinstance(r.get("lon"), (int, float))),
        key=lambda row: (-float(row.get(score_field) or 0), row["lat"], row["lon"]),
    )
    chosen = []
    for row in ranked:
        if all(_distance_km(row, prior) >= minimum_separation_km for prior in chosen):
            chosen.append(dict(row))
        if len(chosen) >= max(1, min(int(limit), 30)):
            break
    for index, row in enumerate(chosen, 1):
        row["point_id"] = f"FIELD-{index:02d}"
    return chosen


def balanced_sampling_points(bbox_wsen: list[float], count: int = 9) -> list[dict]:
    """Return a declared spatially balanced collection design, never a prediction surface."""
    west, south, east, north = [float(x) for x in bbox_wsen]
    side = max(2, int(math.ceil(math.sqrt(max(4, min(int(count), 25))))))
    rows = []
    for r in range(side):
        for c in range(side):
            rows.append({
                "lat": south + (north - south) * (r + 0.5) / side,
                "lon": west + (east - west) * (c + 0.5) / side,
                "score": 0,
                "evidence_label": "designed collection point",
                "reason": "spatially balanced confirmation point; not a predicted occurrence",
            })
    return rows[:count]


def _geojson(waypoints: list[dict]) -> dict:
    return {"type": "FeatureCollection", "features": [{
        "type": "Feature",
        "properties": {k: v for k, v in row.items() if k not in {"lat", "lon"}},
        "geometry": {"type": "Point", "coordinates": [row["lon"], row["lat"]]},
    } for row in waypoints]}


def _csv(waypoints: list[dict]) -> str:
    fields = ["point_id", "lat", "lon", "score", "evidence_label", "reason"]
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(waypoints)
    return stream.getvalue()


def write_field_map(output_dir: pathlib.Path, title: str, bbox_wsen: list[float],
                    layers: list[dict], waypoints: list[dict], notes: list[str],
                    audit_id: str, map_mode: str, base_image: pathlib.Path | None = None,
                    base_bbox_wsen: list[float] | None = None) -> dict[str, Any]:
    """Write matching HTML, CSV and GeoJSON and return their paths and metadata."""
    output_dir.mkdir(parents=True, exist_ok=True)
    observed_only = str(map_mode).casefold().startswith("observed")
    geo = _geojson(waypoints)
    csv_text = _csv(waypoints)
    geo_path, csv_path, html_path = (
        output_dir / "waypoints.geojson", output_dir / "waypoints.csv", output_dir / "map.html")
    geo_path.write_text(json.dumps(geo, indent=2, ensure_ascii=False) + "\n")
    csv_path.write_text(csv_text)

    west, south, east, north = [float(x) for x in bbox_wsen]
    width, height, pad = 900, 620, 54

    def x(lon: float) -> float:
        return pad + (lon - west) / max(east - west, 1e-12) * (width - 2 * pad)

    def y(lat: float) -> float:
        return height - pad - (lat - south) / max(north - south, 1e-12) * (height - 2 * pad)

    colours = ["#2dd4bf", "#f59e0b", "#60a5fa", "#f472b6"]
    layer_svg, controls = [], []
    for index, layer in enumerate(layers):
        colour = layer.get("colour") or colours[index % len(colours)]
        layer_id = f"layer-{index}"
        controls.append(
            f'<label><input type="checkbox" data-layer="{layer_id}" checked> '
            f'{html.escape(str(layer.get("name") or f"Layer {index + 1}"))}</label>')
        marks = []
        for row in layer.get("rows") or []:
            if not isinstance(row.get("lat"), (int, float)) or not isinstance(row.get("lon"), (int, float)):
                continue
            score = float(row.get("score") or row.get("value") or 0)
            radius = 2.5 + 7 * max(0, min(score, 1))
            tip = html.escape(str(row.get("tooltip") or row.get("reason") or layer.get("name") or "point"))
            marks.append(
                f'<circle cx="{x(row["lon"]):.1f}" cy="{y(row["lat"]):.1f}" r="{radius:.1f}" '
                f'fill="{colour}" fill-opacity="0.28" stroke="{colour}" stroke-width="1.5">'
                f'<title>{tip}</title></circle>')
        layer_svg.append(f'<g id="{layer_id}">{"".join(marks)}</g>')

    waypoint_svg = []
    rows_html = []
    for row in waypoints:
        point_id = html.escape(str(row["point_id"]))
        waypoint_svg.append(
            f'<g><circle cx="{x(row["lon"]):.1f}" cy="{y(row["lat"]):.1f}" r="11" '
            'fill="#ef4444" stroke="#fff" stroke-width="2"/>'
            f'<text x="{x(row["lon"]):.1f}" y="{y(row["lat"])+4:.1f}" text-anchor="middle" '
            f'fill="#fff" font-size="9" font-weight="700">{point_id[-2:]}</text></g>')
        maps_url = f'https://www.google.com/maps/search/?api=1&query={row["lat"]:.6f},{row["lon"]:.6f}'
        rows_html.append(
            f'<tr><td data-label="ID">{point_id}</td>'
            f'<td data-label="Coordinates">{row["lat"]:.6f}, {row["lon"]:.6f}</td>'
            f'<td data-label="Score">{float(row.get("score") or 0):.3f}</td>'
            f'<td data-label="Evidence">{html.escape(str(row.get("evidence_label") or ""))}</td>'
            f'<td data-label="Why inspect">{html.escape(str(row.get("reason") or ""))}</td>'
            f'<td data-label="Navigation"><a href="{maps_url}" target="_blank" '
            'rel="noopener">navigate</a></td></tr>')

    ticks = []
    for index in range(5):
        lon = west + (east - west) * index / 4
        lat = south + (north - south) * index / 4
        ticks.append(f'<text x="{x(lon):.1f}" y="{height-pad+20}" text-anchor="middle">{lon:.4f}</text>')
        ticks.append(f'<text x="{pad-8}" y="{y(lat)+3:.1f}" text-anchor="end">{lat:.4f}</text>')

    base_svg = ""
    if base_image and base_image.is_file() and base_bbox_wsen:
        bw, bs, be, bn = [float(value) for value in base_bbox_wsen]
        encoded = base64.b64encode(base_image.read_bytes()).decode("ascii")
        bx, by = x(bw), y(bn)
        bwidth, bheight = x(be) - x(bw), y(bs) - y(bn)
        base_svg = (
            f'<image href="data:image/jpeg;base64,{encoded}" x="{bx:.1f}" y="{by:.1f}" '
            f'width="{bwidth:.1f}" height="{bheight:.1f}" preserveAspectRatio="none" opacity="0.72"/>'
            f'<rect x="{pad}" y="{pad}" width="{width-2*pad}" height="{height-2*pad}" '
            'fill="#07111d" fill-opacity="0.25"/>')

    notes_html = "".join(f"<li>{html.escape(str(note))}</li>" for note in notes)
    geo_json = json.dumps(geo, ensure_ascii=False).replace("</", "<\\/")
    csv_json = json.dumps(csv_text).replace("</", "<\\/")
    point_note = (
        "mapped points are returned observations, not predictions"
        if observed_only else
        "numbered points are field requests, not confirmed occurrences"
    )
    point_heading = "Observed records" if observed_only else "Field points"
    download_stem = "observed-records" if observed_only else "waypoints"
    document = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{{--bg:#081018;--panel:#111c28;--ink:#e6edf3;--muted:#9fb0c3;--line:#2a3a4d}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif}}
header,.body{{max-width:1120px;margin:auto;padding:18px}}h1{{font-size:22px;margin:0 0 5px}}.sub{{color:var(--muted)}}
.controls{{display:flex;gap:15px;flex-wrap:wrap;margin:12px 0}}.map{{background:#0c1622;border:1px solid var(--line);border-radius:14px;overflow:hidden}}
svg{{display:block;width:100%;height:auto}}svg text{{fill:#8ea2b7;font-size:11px}}.notes,.sheet{{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px;margin-top:14px}}
table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}}th{{color:#9fb0c3}}
a{{color:#7dd3fc}}button{{background:#173047;color:#fff;border:1px solid #31516c;border-radius:8px;padding:8px 11px;cursor:pointer}}.actions{{display:flex;gap:8px;flex-wrap:wrap}}summary{{cursor:pointer}}
@media(max-width:680px){{header,.body{{padding:12px}}h1{{font-size:18px}}
.sheet table,.sheet tbody,.sheet tr,.sheet td{{display:block;width:100%}}.sheet thead{{display:none}}
.sheet tr{{padding:8px 0;border-bottom:1px solid var(--line)}}.sheet tr:last-child{{border:0}}
.sheet td{{display:grid;grid-template-columns:92px minmax(0,1fr);gap:8px;padding:5px 0;
border:0;overflow-wrap:anywhere}}.sheet td::before{{content:attr(data-label);color:var(--muted);
font-size:11px;font-weight:700;text-transform:uppercase}}}}
</style></head><body><header><h1>{html.escape(title)}</h1>
<div class="sub">{html.escape(map_mode)} · audit {html.escape(audit_id)} · {html.escape(point_note)}</div></header>
<main class="body"><div class="controls">{''.join(controls)}</div><div class="map">
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Field evidence map"><rect width="100%" height="100%" fill="#0c1622"/>
<rect x="{pad}" y="{pad}" width="{width-2*pad}" height="{height-2*pad}" fill="#122131" stroke="#36506a"/>
{base_svg}{''.join(layer_svg)}{''.join(waypoint_svg)}{''.join(ticks)}
<text x="{pad}" y="{pad-14}" fill="#fff" font-weight="700">N ↑</text></svg></div>
<section class="notes"><b>Interpretation limits</b><ul>{notes_html}</ul><div class="actions">
<button onclick="downloadData('{download_stem}.geojson',JSON.stringify(GEO,null,2),'application/geo+json')">GeoJSON</button>
<button onclick="downloadData('{download_stem}.csv',CSV,'text/csv')">CSV</button></div></section>
<section class="sheet"><details{'' if observed_only else ' open'}><summary><b>{point_heading} ({len(waypoints)})</b></summary><table><thead><tr><th>ID</th><th>Coordinates</th><th>Score</th><th>Evidence</th><th>Source / why inspect</th><th></th></tr></thead>
<tbody>{''.join(rows_html)}</tbody></table></details></section></main>
<script>const GEO={geo_json};const CSV={csv_json};
document.querySelectorAll('[data-layer]').forEach(c=>c.addEventListener('change',()=>{{document.getElementById(c.dataset.layer).style.display=c.checked?'':'none'}}));
function downloadData(name,data,type){{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([data],{{type}}));a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}}
</script></body></html>'''
    html_path.write_text(document)
    return {
        "html": str(html_path), "geojson": str(geo_path), "csv": str(csv_path),
        "html_content": document, "waypoint_count": len(waypoints),
        "point_ids": [row["point_id"] for row in waypoints], "map_mode": map_mode,
    }


def _codebook_columns(codebook: str) -> dict[str, list[str]]:
    """Extract only explicitly quoted column names, grouped by a declared tabular file."""
    current = "codebook"
    grouped: dict[str, list[str]] = {}
    file_pattern = re.compile(r"^\s*\d+\.\s*([^:\r\n]+\.(?:csv|tsv|txt))\s*:\s*$", re.I)
    column_pattern = re.compile(r'^\s*["\u201c]([^"\u201d]{1,120})["\u201d]\s*-')
    for line in str(codebook or "").splitlines():
        file_match = file_pattern.match(line)
        if file_match:
            current = " ".join(file_match.group(1).split())
            grouped.setdefault(current, [])
            continue
        column_match = column_pattern.match(line)
        if column_match:
            column = " ".join(column_match.group(1).split())
            if column and column not in grouped.setdefault(current, []):
                grouped[current].append(column)
    return {name: columns for name, columns in grouped.items() if columns}


def write_field_protocol(output_dir: pathlib.Path, title: str, dataset: dict,
                         purpose: str, audit_id: str,
                         source_file: str | None = None) -> dict[str, Any]:
    """Create a source-linked protocol reader and blank CSV datasheet."""
    output_dir.mkdir(parents=True, exist_ok=True)
    source_columns = []
    file_rows = []
    for item in dataset.get("rows") or []:
        samples = item.get("sample") or []
        header = str(samples[0]) if samples else ""
        if header:
            try:
                dialect = csv.Sniffer().sniff(header, delimiters=",\t;|")
                parsed = next(csv.reader([header], dialect))
            except (csv.Error, StopIteration):
                parsed = [header]
            for column in parsed:
                clean = " ".join(str(column).strip().split())[:120]
                if clean and clean not in source_columns:
                    source_columns.append(clean)
        file_rows.append({"name": str(item.get("name") or ""),
                          "sample": [str(line)[:500] for line in samples[:4]]})
    reported_by_file = _codebook_columns(str(dataset.get("codebook") or ""))
    selected_source_file = None
    if reported_by_file:
        requested = " ".join(str(source_file or "").split()).casefold()
        selected_source_file = next(
            (name for name in reported_by_file if name.casefold() == requested), None)
        if selected_source_file is None and len(reported_by_file) == 1:
            selected_source_file = next(iter(reported_by_file))
        if selected_source_file:
            for column in reported_by_file[selected_source_file]:
                if column not in source_columns:
                    source_columns.append(column)
    source_columns = source_columns[:24]
    adapted_columns = ["point_id", "date", "start_time", "observer", "effort_minutes",
                       "detection_status", "notes"]
    fields = adapted_columns + [column for column in source_columns
                                if column.casefold() not in {x.casefold() for x in adapted_columns}]
    csv_stream = io.StringIO()
    writer = csv.writer(csv_stream)
    writer.writerow(fields)
    for index in range(1, 11):
        writer.writerow([f"FIELD-{index:02d}"] + [""] * (len(fields) - 1))
    csv_text = csv_stream.getvalue()
    csv_path, html_path = output_dir / "field-datasheet.csv", output_dir / "protocol.html"
    csv_path.write_text(csv_text)

    source_header = "".join(f"<th>{html.escape(column)}</th>" for column in source_columns)
    codebook = html.escape(str(dataset.get("codebook") or "No codebook text was returned."))
    files_html = "".join(
        f'<details><summary>{html.escape(row["name"])}</summary><pre>'
        f'{html.escape(chr(10).join(row["sample"]))}</pre></details>' for row in file_rows)
    csv_json = json.dumps(csv_text).replace("</", "<\\/")
    document = f'''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{{box-sizing:border-box}}body{{margin:0;background:#081018;color:#e6edf3;font:14px/1.5 system-ui,sans-serif}}main{{max-width:1050px;margin:auto;padding:20px}}h1{{font-size:22px;margin-bottom:4px}}.muted{{color:#9fb0c3}}section{{background:#111c28;border:1px solid #2a3a4d;border-radius:12px;padding:15px;margin:14px 0}}.boundary{{border-left:4px solid #f59e0b}}pre{{white-space:pre-wrap;max-height:360px;overflow:auto;background:#07111d;padding:12px;border-radius:8px}}table{{width:100%;border-collapse:collapse;font-size:12px}}th,td{{padding:7px;border-bottom:1px solid #2a3a4d;text-align:left}}.scroll{{overflow:auto}}button{{background:#173047;color:#fff;border:1px solid #31516c;border-radius:8px;padding:8px 11px;cursor:pointer}}@media(max-width:600px){{main{{padding:12px}}h1{{font-size:19px}}}}</style></head>
<body><main><h1>{html.escape(title)}</h1><div class="muted">Audit {html.escape(audit_id)} · source {html.escape(str(dataset.get("doi") or "no DOI"))}</div>
<section><b>Field purpose</b><p>{html.escape(purpose)}</p></section>
<section class="boundary"><b>Adaptation boundary</b><p>The source columns below are reported from {html.escape(selected_source_file or 'the inspected dataset material')}. <code>{html.escape(', '.join(adapted_columns))}</code> are explicit programme adaptations added for repeatable field collection; they are not claimed as the source authors' method. Review the codebook before field use.</p></section>
<section><b>Source dataset</b><p>{html.escape(str(dataset.get("title") or "Untitled dataset"))} · {html.escape(str(dataset.get("doi") or ""))}</p>{files_html}</section>
<section><b>Returned codebook material</b><pre>{codebook}</pre></section>
<section><b>Blank field datasheet</b><p><button onclick="downloadData()">Download CSV datasheet</button></p><div class="scroll"><table><thead><tr>{''.join(f'<th>{html.escape(field)}</th>' for field in fields)}</tr></thead><tbody><tr>{''.join('<td></td>' for _ in fields)}</tr></tbody></table></div>
<p class="muted">Source-only columns: </p><div class="scroll"><table><thead><tr>{source_header}</tr></thead></table></div></section></main>
<script>const CSV={csv_json};function downloadData(){{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([CSV],{{type:'text/csv'}}));a.download='field-datasheet.csv';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}}</script></body></html>'''
    html_path.write_text(document)
    return {"html": str(html_path), "csv": str(csv_path), "html_content": document,
            "source_columns": source_columns, "adapted_columns": adapted_columns,
            "datasheet_columns": fields, "blank_rows": 10,
            "reported_source_files": list(reported_by_file),
            "selected_source_file": selected_source_file}
