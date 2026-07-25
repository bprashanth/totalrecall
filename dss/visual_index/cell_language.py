#!/usr/bin/env python3
"""Say which square on the map we mean, in the words a person would use.

The index labels every grid square by its south-west corner: a point at 10.305 N, 76.995 E lives
in the square whose id is `g0.010:10.3000:76.9900`. That is arithmetically exact and completely
unreadable. A user who clicked at 10.305 and is answered about "cell g0.010:10.3000:76.9900" has
no way to tell whether the system understood them or silently moved their point somewhere else,
and the id itself is our plumbing leaking into their answer.

So an id is never how a square is described. A square is described by its extent — how big it is,
which point of the user's it covers, and the latitude and longitude band it spans — computed from
the geometry that square is actually stored with, never from an assumed resolution. The id stays
in the machine fields (`mark.id`, the audit, the layer payloads) where the map and the audit trail
need it.

Nothing here reads a database or a file: callers hand in the box they already hold, whether that
came from the `cells` table, a stored GeoJSON polygon or a parsed id.
"""

from __future__ import annotations

import math
import re
from typing import Any

# The builder's id convention (`dss/visual_index/build.py::_cell`): resolution, south, west.
CELL_ID = re.compile(r"^g(\d+\.\d+):(-?\d+\.\d+):(-?\d+\.\d+)$")
# The same shape found anywhere inside a sentence, for scrubbing prose that was built elsewhere.
CELL_ID_IN_TEXT = re.compile(r"\bg\d+\.\d+:-?\d+\.\d+:-?\d+\.\d+")

# Mean length of one degree of latitude, and of one degree of longitude at the equator, in km.
# Longitude is scaled by cos(latitude) at the square's own middle, so a size is honest at 10 N and
# at 60 N alike.
KM_PER_DEGREE_LATITUDE = 110.574
KM_PER_DEGREE_LONGITUDE = 111.320


def is_cell_id(value: Any) -> bool:
    return bool(CELL_ID.match(str(value or "").strip()))


def cell_box(cell_id: Any) -> tuple[float, float, float, float] | None:
    """(west, south, east, north) implied by an id, for when no stored geometry is at hand."""
    match = CELL_ID.match(str(cell_id or "").strip())
    if not match:
        return None
    resolution = float(match.group(1))
    south, west = float(match.group(2)), float(match.group(3))
    return west, south, west + resolution, south + resolution


def box_from_geometry(geometry: Any) -> tuple[float, float, float, float] | None:
    """(west, south, east, north) of any GeoJSON geometry, by walking its coordinates."""
    if not isinstance(geometry, dict):
        return None
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


def _decimals(step: float) -> int:
    """Enough decimal places to show the edges of a square this size, and no more.

    The step is rounded first: a 0.01° square subtracts to 0.009999999999990905 in binary floating
    point, which would otherwise buy a spurious extra decimal on every printed edge.
    """
    step = round(float(step), 9)
    if step <= 0:
        return 4
    places = int(math.ceil(-math.log10(step))) + 1
    return max(2, min(6, places))


def _degrees(value: float, decimals: int, positive: str, negative: str) -> str:
    return f"{abs(value):.{decimals}f} {positive if value >= 0 else negative}"


def _point(value: float, positive: str, negative: str) -> str:
    text = f"{abs(value):.5f}".rstrip("0").rstrip(".")
    return f"{text} {positive if value >= 0 else negative}"


def _size(width_km: float, height_km: float) -> str:
    """'1.1 km square' when it reads as one, otherwise the two sides."""
    def number(value: float) -> str:
        return f"{value:.1f}" if value >= 0.95 else f"{value * 1000:.0f} m"

    larger = max(width_km, height_km)
    smaller = min(width_km, height_km)
    if larger <= 0:
        return "map square"
    if smaller / larger >= 0.9:
        side = number((width_km + height_km) / 2)
        return f"{side} km square" if side[-1].isdigit() else f"{side} square"
    return f"{number(width_km)} by {number(height_km)} km block"


def describe_box(
    west: float, south: float, east: float, north: float,
    requested_lat: float | None = None, requested_lon: float | None = None,
) -> dict[str, Any]:
    """Describe one square by its extent: size, the point it covers, and the band it spans.

    Everything is derived from the box handed in — the square's own stored geometry — so a pack
    gridded at 0.05° describes itself as a 5.5 km square without anyone editing this file.
    """
    west, south, east, north = float(west), float(south), float(east), float(north)
    middle_lat = (south + north) / 2.0
    height_km = abs(north - south) * KM_PER_DEGREE_LATITUDE
    width_km = abs(east - west) * KM_PER_DEGREE_LONGITUDE * math.cos(math.radians(middle_lat))
    size = _size(width_km, height_km)
    places = _decimals(min(abs(north - south), abs(east - west)) or abs(north - south))
    span = (
        f"{abs(south):.{places}f}–{_degrees(north, places, 'N', 'S')} and "
        f"{abs(west):.{places}f}–{_degrees(east, places, 'E', 'W')}"
    )
    point_text = None
    if requested_lat is not None and requested_lon is not None:
        point_text = (
            f"{_point(float(requested_lat), 'N', 'S')}, {_point(float(requested_lon), 'E', 'W')}"
        )
    if point_text:
        phrase = f"the {size} covering your point ({point_text}), spanning {span}"
        short = f"the {size} covering {point_text}"
    else:
        phrase = f"the {size} spanning {span}"
        short = f"the {size} spanning {span}"
    return {
        # What a person reads. Never an id.
        "phrase": phrase,
        "short_phrase": short,
        "span": span,
        "size": size,
        "requested_point": point_text,
        # What a machine reads: the same square, exactly.
        "bounds": {"west": west, "south": south, "east": east, "north": north},
        "size_km": {"width": round(width_km, 3), "height": round(height_km, 3)},
        "centre": {"lat": round(middle_lat, 6), "lon": round((west + east) / 2.0, 6)},
    }


def describe_cell(
    cell_id: Any = None, box: tuple[float, float, float, float] | None = None,
    geometry: Any = None, requested_lat: float | None = None,
    requested_lon: float | None = None,
) -> dict[str, Any] | None:
    """Describe a square from whatever is known about it, preferring real stored geometry.

    Order matters: an explicit box (read from the `cells` table), then the stored polygon the user
    actually saw, and only then the id's own arithmetic. The id is carried in the result as a
    machine field so a caller never has to hold it separately.
    """
    resolved = box or box_from_geometry(geometry) or cell_box(cell_id)
    if resolved is None:
        return None
    description = describe_box(*resolved, requested_lat=requested_lat, requested_lon=requested_lon)
    if cell_id:
        description["id"] = str(cell_id)
    description["geometry_source"] = (
        "stored_box" if box else ("stored_geometry" if geometry is not None else "cell_id")
    )
    return description


def scrub_cell_ids(text: Any, replacement: str = "that map square") -> str:
    """Replace any cell id left in a sentence built elsewhere, so none reaches a reader."""
    return CELL_ID_IN_TEXT.sub(replacement, str(text or ""))
