#!/usr/bin/env python3
"""Turn "make the map a map of built-up" into one AOI-clipped raster layer.

The visual grammar already carries vector planes. A basemap-style question — built-up, elevation,
tree cover — is not a vector question: the answer is a continuous surface over the AOI. This
service produces that surface as a PNG, stores it as an ordinary immutable result payload, and
declares it in an `idli-result/1` envelope as a `raster_image` layer with `bounds = [w, s, e, n]`.
The renderer needs no change: it already draws a georeferenced image overlay for that layer type.

Two production paths, and the envelope always says which one ran:

1. **Earth Engine** (`derived`). A small keyword registry maps the user's words onto one published
   product — GHSL built-up surface, SRTM elevation, ESA WorldCover — and the AOI-clipped thumbnail
   is fetched server-side through `getThumbURL`. The product name, asset id and epoch go into
   `audit.source_versions`, and a limitation states the product's native resolution and date. This
   path runs only when `ee` imports, initialises and the network answers; it is never faked.
2. **Deterministic fallback** (`modelled`, flagged synthetic). When Earth Engine is unavailable the
   same capability still runs, so the contract is exercised end to end: the surface is generated
   from the pinned pack itself — a kernel density over indexed record and effort locations for a
   built-up/settlement proxy, an analytic relief field for elevation — and the envelope carries an
   error-severity limitation saying, in plain words, that the image is synthetic, that it is not
   observation of the ground, and what would be needed to make it real.

The PNG is written by a minimal stdlib encoder (zlib + CRC), so no imaging dependency is required
in the bridge interpreter. Pixels outside the declared AOI polygon are fully transparent: a
computed layer must never paint outside the area the pack declares.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import math
import os
import pathlib
import struct
import subprocess
import sys
import tempfile
import urllib.parse
import zlib
from typing import Any

try:
    from dss.visual_index.result_service import (
        SAFE_HANDLE, _atomic_write_once, _digest, _load_json, _stable_json,
    )
except ModuleNotFoundError:  # Direct execution: python dss/visual_index/earth_layer_service.py
    from result_service import (  # type: ignore[no-redef]
        SAFE_HANDLE, _atomic_write_once, _digest, _load_json, _stable_json,
    )


MAX_PIXELS = 512
MIN_PIXELS = 64
EE_PROJECT = os.environ.get("EE_PROJECT", "plantwars")
EE_TIMEOUT = int(os.environ.get("EE_THUMBNAIL_TIMEOUT", "60"))
EE_INIT_TIMEOUT = int(os.environ.get("EE_INIT_TIMEOUT", "8"))
# Earth Engine runs in whichever interpreter actually has `earthengine-api`, reached as a
# subprocess. The bridge venv is shared with another site's bridge, so installing a cloud SDK
# into it would change a runtime this module has no business changing; the repo already re-execs
# into a different interpreter for the same reason (see integration/origin/connectors/_base.py).
# Credentials are a per-user file, so both interpreters authenticate identically.
EE_PYTHON_CANDIDATES = [
    path for path in (
        os.environ.get("EE_PYTHON", "").strip(),
        sys.executable,
        "/usr/bin/python3",
        "python3",
    ) if path
]


EARTH_LAYER_CAPABILITIES: list[dict[str, Any]] = [
    {
        "capability_id": "earth-layer",
        "version": "1.0.0",
        "label": "Render one AOI-clipped earth-observation layer as a map raster",
        "input_schema": {
            "type": "object",
            "properties": {"layer": {"type": "string"}},
            "required": ["layer"],
        },
        "output_views": ["earth-layer-raster"],
        "required_planes": ["cells"],
        "optional_planes": ["events", "effort"],
        "latency_class": "interactive",
        "evidence_classes": ["reported", "derived", "modelled"],
        "availability": "ready",
        "scope": "site",
        "reason": (
            "Falls back to a declared synthetic surface when no Earth Engine credential or "
            "network is available; the envelope always states which path produced the image."
        ),
    },
]


PRODUCTS: list[dict[str, Any]] = [
    {
        "product_id": "built-up",
        "label": "Built-up surface",
        "keywords": (
            "built-up", "built up", "builtup", "built", "settlement", "settlements", "urban",
            "buildings", "impervious", "development", "developed",
        ),
        "earth_engine": {
            # Addressed as the epoch image directly: the collection carries 1975-2030 epochs, and
            # naming the one we mean is honester than mosaicking a filter and hoping.
            "asset": "JRC/GHSL/P2023A/GHS_BUILT_S/2020",
            "asset_kind": "image",
            "band": "built_surface",
            "terrain": None,
            # built_surface is square metres of built surface within each 100 m cell, so the cell
            # area is the true maximum rather than a chosen stretch.
            "vis": {"min": 0, "max": 10000,
                    "palette": ["000004", "51127c", "b63679", "fb8861", "fcfdbf"]},
        },
        "product_name": "GHSL Built-up Surface (GHS-BUILT-S), epoch 2020",
        "product_version": "P2023A",
        "publisher": "European Commission Joint Research Centre",
        "resolution_m": 100,
        "product_date": "2020",
        "measures": (
            "built-up surface area in square metres within each 100 m cell (0-10,000)"
        ),
        "fallback": {
            "kind": "density",
            "legend": "Modelled settlement proxy (record and effort density)",
            "palette": ((8, 6, 20), (81, 18, 124), (182, 54, 121), (251, 136, 97),
                        (252, 253, 191)),
            "basis": (
                "kernel density over indexed event and effort locations, used as a settlement "
                "proxy because people record where people are"
            ),
        },
    },
    {
        "product_id": "elevation",
        "label": "Elevation and relief",
        "keywords": (
            "elevation", "terrain", "relief", "topography", "height", "dem", "hillshade",
            "slope", "contour", "altitude",
        ),
        "earth_engine": {
            "asset": "USGS/SRTMGL1_003",
            "asset_kind": "image",
            "band": "elevation",
            # Relief reads as terrain only when it is shaded; ee.Terrain.hillshade does that on
            # the real DEM rather than on a stretch of raw metres.
            "terrain": "hillshade",
            "vis": {"min": 0, "max": 255},
        },
        "product_name": "SRTM Digital Elevation Model, 1 arc-second (hillshaded)",
        "product_version": "SRTMGL1 v003",
        "publisher": "NASA / USGS",
        "resolution_m": 30,
        "product_date": "2000-02 (single 11-day acquisition campaign)",
        "measures": (
            "shaded relief computed from ground elevation, lit from the north-west by convention"
        ),
        "fallback": {
            "kind": "relief",
            "legend": "Synthetic relief field (not a measured terrain surface)",
            "palette": ((11, 61, 46), (59, 122, 87), (184, 176, 106), (156, 107, 63),
                        (239, 239, 239)),
            "basis": (
                "an analytic, reproducible relief function of latitude and longitude, shaded from "
                "its own gradient; it contains no measurement of this or any terrain"
            ),
        },
    },
    {
        "product_id": "tree-cover",
        "label": "Tree cover and land cover",
        "keywords": (
            "tree cover", "trees", "forest", "canopy", "vegetation", "land cover", "landcover",
            "green", "worldcover",
        ),
        "earth_engine": {
            "asset": "ESA/WorldCover/v200/2021",
            "asset_kind": "image",
            "band": "Map",
            "terrain": None,
            # The official WorldCover class palette, in class order 10..95, so the rendered
            # colours are the product's own rather than a ramp invented here.
            "vis": {"min": 10, "max": 95,
                    "palette": ["006400", "ffbb22", "ffff4c", "f096ff", "fa0000",
                                "b4b4b4", "f0f0f0", "0064c8", "0096a0", "00cf75",
                                "fae6a0"]},
        },
        "product_name": "ESA WorldCover 10 m land cover",
        "product_version": "v200 (2021)",
        "publisher": "European Space Agency",
        "resolution_m": 10,
        "product_date": "2021",
        "measures": (
            "a discrete land-cover class per pixel (tree cover, shrubland, cropland, built-up, "
            "water and others), not a continuous tree-cover percentage"
        ),
        "fallback": {
            "kind": "inverse_density",
            "legend": "Modelled vegetation proxy (inverse of recorded activity density)",
            "palette": ((214, 217, 200), (163, 189, 140), (105, 158, 92), (46, 118, 63),
                        (12, 74, 40)),
            "basis": (
                "the complement of the same activity-density surface, used as a crude vegetation "
                "proxy; it is an inference about the pack's records, not about vegetation"
            ),
        },
    },
]


# ---------------------------------------------------------------------- PNG encoding


def encode_png(width: int, height: int, rows: list[bytes]) -> bytes:
    """Minimal RGBA PNG writer: stdlib only, so the bridge needs no imaging dependency."""
    if len(rows) != height or any(len(row) != width * 4 for row in rows):
        raise ValueError("row count or row width does not match the declared image size")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload)) + kind + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + row for row in rows)  # filter type 0 per scanline
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def png_size(payload: bytes) -> tuple[int, int] | None:
    """Width and height from a PNG header, whatever its colour type.

    Earth Engine returns whichever encoding suits the product — RGBA for a clipped palette
    image, grey+alpha for a hillshade, RGB where the render covers the whole region — so the
    envelope must read the real size back rather than assume the one it asked for.
    """
    if not payload.startswith(b"\x89PNG\r\n\x1a\n") or len(payload) < 24:
        return None
    if payload[12:16] != b"IHDR":
        return None
    width, height = struct.unpack(">II", payload[16:24])
    return int(width), int(height)


def _ee_fetch(request: dict[str, Any]) -> dict[str, Any]:
    """Child-process worker: initialise Earth Engine, render one thumbnail, save the bytes.

    This runs under whichever interpreter carries `earthengine-api`, which is generally not the
    one serving the bridge. It writes no diagnostics to stdout except its single JSON result.
    """
    import urllib.request

    import ee  # type: ignore

    ee.Initialize(project=request["project"])
    region = ee.Geometry.Polygon([request["ring"]])
    image = (
        ee.ImageCollection(request["asset"]).mosaic()
        if request.get("asset_kind") == "collection" else ee.Image(request["asset"])
    )
    image = image.select(request["band"])
    if request.get("terrain") == "hillshade":
        image = ee.Terrain.hillshade(image)
    # Clipping to the declared polygon is what makes everything outside the AOI transparent;
    # Earth Engine masks it and the PNG carries the mask as alpha.
    #
    # `crs` is not optional. A thumbnail renders in the image's native projection unless told
    # otherwise, and several of these products are not in geographic coordinates — GHSL is
    # Mollweide — so the AOI rectangle comes back as a rotated parallelogram whose pixel grid
    # does not line up with the lat/lon bounds the envelope declares. Pinning EPSG:4326 makes
    # the raster axis-aligned in degrees, which is the only form that can be honestly placed
    # with `bounds = [w, s, e, n]`.
    url = image.clip(region).getThumbURL({
        **(request.get("vis") or {}),
        "region": region,
        "dimensions": request["dimensions"],
        "crs": "EPSG:4326",
        "format": "png",
    })
    with urllib.request.urlopen(url, timeout=request.get("timeout", 60)) as response:
        payload = response.read()
    pathlib.Path(request["output"]).write_bytes(payload)
    return {"ok": True, "bytes": len(payload), "url_host": urllib.parse.urlparse(url).netloc}


def _ramp(palette: tuple[tuple[int, int, int], ...], fraction: float) -> tuple[int, int, int]:
    fraction = min(max(fraction, 0.0), 1.0)
    if len(palette) == 1:
        return palette[0]
    position = fraction * (len(palette) - 1)
    lower = min(int(position), len(palette) - 2)
    weight = position - lower
    left, right = palette[lower], palette[lower + 1]
    return tuple(  # type: ignore[return-value]
        int(round(left[index] + (right[index] - left[index]) * weight)) for index in range(3)
    )


class EarthLayerService:
    """Produce one AOI-clipped raster layer, from Earth Engine when possible and honestly not."""

    def __init__(
        self,
        site_pack: pathlib.Path,
        index_path: pathlib.Path,
        state_root: pathlib.Path,
    ):
        self.site_pack = pathlib.Path(site_pack).resolve()
        self.index_path = pathlib.Path(index_path).resolve()
        self.state_root = pathlib.Path(state_root).resolve()
        self.site = _load_json(self.site_pack / "site.json")
        registry = _load_json(self.site_pack / "sources.json")
        self.synthetic = any(
            "synthetic" in (source.get("capabilities") or [])
            for source in registry.get("sources", [])
        )
        self.pack_digest = ""
        self._engine: dict[str, Any] | None = None

    @classmethod
    def from_result_service(cls, service: Any) -> "EarthLayerService":
        layer = cls(service.site_pack, service.index_path, service.state_root)
        layer.site = service.site
        layer.pack_digest = service.pack_digest
        layer.synthetic = bool(getattr(service, "synthetic", False))
        return layer

    def connect(self):
        import sqlite3

        connection = sqlite3.connect(f"file:{self.index_path}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        return connection

    # ------------------------------------------------------------------ geography

    def aoi_geometry(self) -> dict[str, Any]:
        return self.site["target_aoi"]["geometry"]

    def aoi_ring(self) -> list[list[float]]:
        return [
            [float(point[0]), float(point[1])]
            for point in self.aoi_geometry()["coordinates"][0]
        ]

    def aoi_bbox(self) -> tuple[float, float, float, float]:
        ring = self.aoi_ring()
        xs = [point[0] for point in ring]
        ys = [point[1] for point in ring]
        return min(xs), min(ys), max(xs), max(ys)

    @staticmethod
    def _inside_ring(lon: float, lat: float, ring: list[list[float]]) -> bool:
        inside = False
        count = len(ring)
        for index in range(count):
            x1, y1 = ring[index]
            x2, y2 = ring[(index + 1) % count]
            if (y1 > lat) != (y2 > lat):
                crossing = (x2 - x1) * (lat - y1) / (y2 - y1) + x1
                if lon < crossing:
                    inside = not inside
        return inside

    # ------------------------------------------------------------------ product registry

    @staticmethod
    def resolve_product(layer_text: str) -> dict[str, Any] | None:
        """Match the user's words, however they punctuate them, against one registered product."""
        raw = " ".join(str(layer_text or "").split()).casefold()
        # "tree-cover", "tree_cover" and "tree cover" are the same request; the registry stores
        # one spelling and normalises the rest rather than listing every variant.
        text = raw.replace("-", " ").replace("_", " ").replace("/", " ")
        best, best_score = None, 0
        for product in PRODUCTS:
            if product["product_id"] in {raw, text.replace(" ", "-")}:
                return product
            score = max(
                (
                    len(word) for word in product["keywords"]
                    if word.replace("-", " ") in text
                ),
                default=0,
            )
            if score > best_score:
                best, best_score = product, score
        return best

    @staticmethod
    def supported_layers() -> list[dict[str, Any]]:
        return [
            {
                "product_id": product["product_id"],
                "label": product["label"],
                "example_words": sorted(product["keywords"])[:4],
                "product_name": product["product_name"],
                "resolution_m": product["resolution_m"],
            }
            for product in PRODUCTS
        ]

    # ------------------------------------------------------------------ earth engine

    def engine_status(self) -> dict[str, Any]:
        """Find an interpreter that carries earthengine-api. A probe never raises; it reports."""
        if self._engine is not None:
            return self._engine
        status: dict[str, Any] = {
            "available": False, "project": EE_PROJECT, "reason": "", "python": None,
        }
        tried: list[str] = []
        for candidate in EE_PYTHON_CANDIDATES:
            try:
                probe = subprocess.run(
                    [candidate, "-c", "import ee; print(ee.__version__)"],
                    capture_output=True, text=True, timeout=EE_INIT_TIMEOUT,
                )
            except (OSError, subprocess.SubprocessError) as exc:
                tried.append(f"{candidate}: {type(exc).__name__}")
                continue
            if probe.returncode == 0:
                status.update({
                    "available": True, "python": candidate,
                    "version": probe.stdout.strip(),
                    "reason": f"earthengine-api {probe.stdout.strip()} via {candidate}",
                })
                self._engine = status
                return status
            tried.append(f"{candidate}: {(probe.stderr or '').strip().splitlines()[-1:]}")
        status["reason"] = (
            "no interpreter on this host can import earthengine-api "
            f"(tried {', '.join(EE_PYTHON_CANDIDATES)}). Set EE_PYTHON to an interpreter that "
            f"has it, or install earthengine-api. Detail: {tried}"
        )
        self._engine = status
        return status

    def _earth_engine_png(
        self, product: dict[str, Any], width: int, height: int
    ) -> tuple[bytes | None, str]:
        """Fetch the AOI-clipped product thumbnail through the interpreter that has `ee`.

        The work runs in a child process because the interpreter serving this bridge is shared
        with another site's bridge and must not grow a cloud SDK. The child writes PNG bytes to a
        temporary file and reports status as one JSON line, so image bytes never share a stream
        with diagnostics.
        """
        status = self.engine_status()
        if not status["available"]:
            return None, status["reason"]
        request = {
            "project": EE_PROJECT,
            "asset": product["earth_engine"]["asset"],
            "asset_kind": product["earth_engine"]["asset_kind"],
            "band": product["earth_engine"]["band"],
            "terrain": product["earth_engine"].get("terrain"),
            "vis": product["earth_engine"]["vis"],
            "ring": self.aoi_ring(),
            "dimensions": f"{width}x{height}",
            "timeout": EE_TIMEOUT,
        }
        with tempfile.TemporaryDirectory(prefix="idli-ee-") as work:
            target = pathlib.Path(work) / "thumb.png"
            request["output"] = str(target)
            try:
                completed = subprocess.run(
                    [status["python"], str(pathlib.Path(__file__).resolve()), "--ee-fetch"],
                    input=json.dumps(request), capture_output=True, text=True,
                    timeout=EE_INIT_TIMEOUT + EE_TIMEOUT,
                )
            except subprocess.TimeoutExpired:
                return None, (
                    f"Earth Engine fetch exceeded {EE_INIT_TIMEOUT + EE_TIMEOUT}s and was "
                    "abandoned rather than stalling the request."
                )
            except (OSError, subprocess.SubprocessError) as exc:
                return None, f"Earth Engine subprocess failed: {type(exc).__name__}: {exc}"
            outcome: dict[str, Any] = {}
            for line in (completed.stdout or "").splitlines():
                with contextlib.suppress(json.JSONDecodeError):
                    parsed = json.loads(line)
                    if isinstance(parsed, dict) and "ok" in parsed:
                        outcome = parsed
            if not outcome.get("ok"):
                detail = (
                    outcome.get("error")
                    or (completed.stderr or "").strip().splitlines()[-1:] or "no output"
                )
                return None, f"Earth Engine request failed: {detail}"
            if not target.is_file():
                return None, "Earth Engine reported success but wrote no image"
            payload = target.read_bytes()
        if not payload.startswith(b"\x89PNG"):
            return None, "Earth Engine returned a non-PNG body for the thumbnail request"
        return payload, (
            f"{product['product_name']} retrieved from Earth Engine asset "
            f"{product['earth_engine']['asset']} via getThumbURL"
        )

    # ------------------------------------------------------------------ fallback surfaces

    def _activity_points(self) -> list[tuple[float, float, float]]:
        """Where the pack has recorded anything at all: (lat, lon, weight)."""
        points: list[tuple[float, float, float]] = []
        with self.connect() as connection:
            for row in connection.execute(
                """SELECT latitude,longitude,COUNT(*) AS weight FROM events
                   WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                   GROUP BY latitude,longitude"""
            ):
                points.append((float(row["latitude"]), float(row["longitude"]),
                               float(row["weight"])))
            for row in connection.execute(
                """SELECT latitude,longitude,COALESCE(SUM(effort_value),1) AS weight FROM effort
                   WHERE latitude IS NOT NULL AND longitude IS NOT NULL
                   GROUP BY latitude,longitude"""
            ):
                points.append((float(row["latitude"]), float(row["longitude"]),
                               math.sqrt(float(row["weight"]))))
            for row in connection.execute(
                "SELECT latitude,longitude FROM locations "
                "WHERE latitude IS NOT NULL AND longitude IS NOT NULL"
            ):
                points.append((float(row["latitude"]), float(row["longitude"]), 3.0))
        return points

    @staticmethod
    def _relief(lat: float, lon: float) -> float:
        """A deterministic, reproducible analytic field. It is arithmetic, not terrain."""
        return (
            0.5
            + 0.25 * math.sin((lon - 76.0) * 47.0) * math.cos((lat - 10.0) * 41.0)
            + 0.15 * math.sin((lat + lon) * 23.0)
            + 0.10 * math.cos((lon - lat) * 71.0)
        )

    def _fallback_field(
        self, product: dict[str, Any], width: int, height: int
    ) -> tuple[list[list[float | None]], dict[str, Any]]:
        """A width×height grid of values in [0,1], or None outside the AOI."""
        west, south, east, north = self.aoi_bbox()
        ring = self.aoi_ring()
        kind = product["fallback"]["kind"]
        points = self._activity_points() if kind in {"density", "inverse_density"} else []
        # A kernel wide enough to read as a surface at AOI scale, narrow enough to stay local.
        sigma = max((east - west), (north - south)) / 22.0
        grid: list[list[float | None]] = []
        raw_max = 0.0
        raw: list[list[float | None]] = []
        for y in range(height):
            lat = north - (north - south) * (y + 0.5) / height
            row: list[float | None] = []
            for x in range(width):
                lon = west + (east - west) * (x + 0.5) / width
                if not self._inside_ring(lon, lat, ring):
                    row.append(None)
                    continue
                if kind == "relief":
                    row.append(self._relief(lat, lon))
                    continue
                total = 0.0
                for plat, plon, weight in points:
                    dx = (plon - lon) * math.cos(math.radians(lat))
                    dy = plat - lat
                    total += weight * math.exp(-(dx * dx + dy * dy) / (2 * sigma * sigma))
                raw_max = max(raw_max, total)
                row.append(total)
            raw.append(row)
        if kind == "relief":
            values = [value for row in raw for value in row if value is not None]
            low, high = (min(values), max(values)) if values else (0.0, 1.0)
            span = (high - low) or 1.0
            grid = [
                [None if value is None else (value - low) / span for value in row]
                for row in raw
            ]
        else:
            scale = raw_max or 1.0
            grid = [
                [
                    None if value is None else
                    (1.0 - math.sqrt(value / scale) if kind == "inverse_density"
                     else math.sqrt(value / scale))
                    for value in row
                ]
                for row in raw
            ]
        return grid, {
            "kind": kind,
            "kernel_sigma_deg": round(sigma, 5) if kind != "relief" else None,
            "source_points": len(points),
        }

    def _fallback_png(
        self, product: dict[str, Any], width: int, height: int
    ) -> tuple[bytes, dict[str, Any]]:
        grid, detail = self._fallback_field(product, width, height)
        palette = product["fallback"]["palette"]
        shade = product["fallback"]["kind"] == "relief"
        rows: list[bytes] = []
        for y in range(height):
            row = bytearray()
            for x in range(width):
                value = grid[y][x]
                if value is None:
                    row += b"\x00\x00\x00\x00"
                    continue
                red, green, blue = _ramp(palette, value)
                if shade:
                    # Relief reads as terrain only with a light source; shade from the field's
                    # own gradient rather than inventing a second surface.
                    left = grid[y][max(x - 1, 0)] or value
                    up = grid[max(y - 1, 0)][x] or value
                    lighting = 1.0 + 1.6 * ((value - left) + (value - up))
                    lighting = min(max(lighting, 0.55), 1.45)
                    red = min(255, int(red * lighting))
                    green = min(255, int(green * lighting))
                    blue = min(255, int(blue * lighting))
                row += bytes((red, green, blue, 235))
            rows.append(bytes(row))
        return encode_png(width, height, rows), detail

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

    def _base(
        self, result_id: str, request_id: str, original: str, resolved: str,
        bindings: dict[str, Any], headline: str, evidence_classes: list[str],
        status: str, source_versions: list[dict[str, Any]], assurance: str,
    ) -> dict[str, Any]:
        site = {
            "site_id": self.site.get("site_id"), "label": self.site.get("label"),
            "pack_digest": self.pack_digest,
        }
        if self.synthetic:
            site["synthetic"] = True
        descriptor = EARTH_LAYER_CAPABILITIES[0]
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
            "limitations": [],
            "actions": [],
            "audit": {
                "audit_id": f"{result_id}/1",
                "source_versions": source_versions,
                "capability_runs": [{
                    "capability_id": descriptor["capability_id"],
                    "version": descriptor["version"],
                    "status": "blocked" if status == "blocked" else (
                        "partial" if status == "partial" else "complete"
                    ),
                }],
                "query_hash": _digest({"capability_id": "earth-layer", "bindings": bindings}),
                "assurance": assurance,
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
        """Store payloads immutably. Unlike the JSON planes, a raster payload is raw bytes."""
        root = self.state_root / "results" / result["result_id"]
        for handle, (media_type, payload) in payloads.items():
            if not SAFE_HANDLE.fullmatch(handle):
                raise ValueError(f"unsafe data handle: {handle}")
            if media_type == "image/png":
                suffix, content = ".png", payload
            elif media_type == "application/geo+json":
                suffix, content = ".geojson", _stable_json(payload).encode()
            else:
                suffix, content = ".json", _stable_json(payload).encode()
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
            _atomic_write_once(root / "data" / f"{handle}{suffix}", content)
        _atomic_write_once(
            root / "result.json",
            (json.dumps(result, indent=2, ensure_ascii=False, default=str) + "\n").encode(),
        )
        return result

    def load_data(self, result_id: str, handle: str) -> tuple[str, bytes] | None:
        """Serve a stored binary payload. JSON planes stay with the result service."""
        if not SAFE_HANDLE.fullmatch(str(result_id or "")) or not SAFE_HANDLE.fullmatch(
            str(handle or "")
        ):
            return None
        path = self.state_root / "results" / result_id / "data" / f"{handle}.png"
        if path.is_file():
            return "image/png", path.read_bytes()
        return None

    # ------------------------------------------------------------------ entry point

    def build_layer(
        self, layer_text: str, request_id: str = "", question: str = ""
    ) -> dict[str, Any]:
        """Render one requested earth layer over the pack's AOI and emit its envelope."""
        requested = " ".join(str(layer_text or "").split())[:200]
        product = self.resolve_product(requested)
        west, south, east, north = self.aoi_bbox()
        bindings = {"layer": requested, "aoi_bbox": [west, south, east, north]}
        request_id = " ".join(str(request_id or "").split())[:200] or (
            "earth-layer-" + _digest(bindings).split(":", 1)[1][:12]
        )
        original = " ".join(str(question or "").split())[:1200] or (
            f"Make the map a map of {requested or 'this site'}."
        )
        result_id = "result-earth-" + _digest({
            "site": self.site.get("site_id"), "pack": self.pack_digest,
            "request_id": request_id, **bindings,
        }).split(":", 1)[1][:20]

        if product is None:
            return self._unsupported(result_id, request_id, original, bindings, requested)

        span_x, span_y = east - west, north - south
        if span_x >= span_y:
            width = MAX_PIXELS
            height = max(MIN_PIXELS, int(round(MAX_PIXELS * span_y / span_x)))
        else:
            height = MAX_PIXELS
            width = max(MIN_PIXELS, int(round(MAX_PIXELS * span_x / span_y)))

        png, note = self._earth_engine_png(product, width, height)
        if png is not None:
            observed = True
            detail: dict[str, Any] = {"path": "earth_engine", "note": note}
        else:
            observed = False
            png, field_detail = self._fallback_png(product, width, height)
            detail = {"path": "deterministic_fallback", "note": note, **field_detail}
        # Earth Engine may return a slightly different size than requested to preserve the
        # region's aspect, so the envelope reports the image that actually exists.
        width, height = png_size(png) or (width, height)

        aoi = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "id": "target",
                "geometry": self.aoi_geometry(),
                "properties": {
                    "label": self.site.get("label"),
                    "geometry_role": self.site["target_aoi"].get("geometry_role"),
                },
            }],
        }
        aoi_ref = self._data_ref("declared-aoi", "application/geo+json", aoi)
        raster_ref = self._data_ref("earth-layer-raster", "image/png", png)

        if observed:
            source_versions = [{
                "source_id": f"earth-engine:{product['earth_engine']['asset']}",
                "version": product["product_version"],
                "digest": _digest(png),
                "synthetic": False,
                "title": product["product_name"],
                "publisher": product["publisher"],
                "asset": product["earth_engine"]["asset"],
                "band": product["earth_engine"]["band"],
                "resolution_m": product["resolution_m"],
                "product_date": product["product_date"],
                "user_supplied": False,
            }]
            evidence_class = "derived"
            evidence_classes = ["reported", "derived"]
            assurance = "retrieved"
            headline = (
                f"{product['product_name']} clipped to the declared AOI and drawn as a map layer."
            )
            legend = product["label"]
        else:
            source_versions = [{
                "source_id": "synthetic:earth-layer-fallback",
                "version": "1.0.0",
                "digest": _digest(png),
                "synthetic": True,
                "title": f"Synthetic stand-in for {product['product_name']}",
                "publisher": "Generated locally by dss/visual_index/earth_layer_service.py",
                "asset": None,
                "band": None,
                "resolution_m": None,
                "product_date": None,
                "user_supplied": False,
            }]
            evidence_class = "modelled"
            evidence_classes = ["reported", "modelled"]
            assurance = "generated"
            headline = (
                f"No {product['label'].lower()} product could be retrieved, so a SYNTHETIC "
                f"stand-in surface was generated and drawn over the AOI."
            )
            legend = product["fallback"]["legend"]

        result = self._base(
            result_id, request_id, original,
            f"Render {product['label'].lower()} over the declared AOI as a raster map layer.",
            bindings, headline, evidence_classes, "complete", source_versions, assurance,
        )
        result["answer"]["detail"] = (
            (
                f"The image is the published product clipped to the AOI bounding box "
                f"[{west:g}, {south:g}, {east:g}, {north:g}]; its native resolution is "
                f"{product['resolution_m']} m and its epoch is {product['product_date']}."
            ) if observed else (
                "The image is generated arithmetic, not observation. It exercises the layer "
                "contract so the map works, and it must not be read as information about the "
                "ground."
            )
        )

        limitations = [
            self._limitation(
                "product-resolution-and-date",
                (
                    f"{product['product_name']} ({product['product_version']}, "
                    f"{product['publisher']}, Earth Engine asset "
                    f"{product['earth_engine']['asset']}) has a native resolution of "
                    f"{product['resolution_m']} m and represents {product['product_date']}. "
                    f"It shows {product['measures']}. It is resampled to "
                    f"{width}×{height} px to fit the AOI, so pixel edges in this view are "
                    "display artefacts, not product boundaries, and nothing after its epoch is "
                    "shown — this is not a current image of the site."
                ),
                severity="info", affects=["answer", "earth-layer-raster"],
            ) if observed else self._limitation(
                "synthetic-raster",
                (
                    "SYNTHETIC IMAGE. Earth Engine was not usable, so this layer was generated "
                    f"locally from {product['fallback']['basis']}. It is not "
                    f"{product['label'].lower()}, it is not a measurement, and it must never be "
                    f"cited, exported or compared with real data. Reason Earth Engine was "
                    f"unavailable: {note}"
                ),
                severity="error", affects=["answer", "earth-layer-raster"],
            ),
            self._limitation(
                "aoi-clipped",
                (
                    "The raster is clipped to the pack's declared AOI. Everything outside the "
                    "declared boundary is transparent because the pack makes no claim there."
                ),
                severity="info", affects=["earth-layer-raster"],
            ),
        ]
        result["limitations"].extend(limitations)

        result["visuals"] = [{
            "visual_id": "earth-layer",
            "visual_type": "map",
            "view": "earth-layer-raster",
            "title": f"{product['label']} over {self.site.get('label')}",
            "priority": "primary",
            "status": "ready",
            "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
            "layers": [
                {
                    # The vector AOI is what gives the map its extent; the raster alone carries
                    # no geometry the renderer can frame on.
                    "layer_id": "declared-aoi", "evidence_class": "reported",
                    "geometry_type": "polygon", "data_ref": aoi_ref,
                    "legend": {"label": "Declared analysis area"},
                    "style_hint": {"palette_role": "reported"},
                },
                {
                    "layer_id": "earth-layer-raster",
                    "evidence_class": evidence_class,
                    "geometry_type": "raster_image",
                    "bounds": [west, south, east, north],
                    "data_ref": raster_ref,
                    "legend": {"label": legend},
                    "style_hint": {"palette_role": evidence_class, "opacity": 0.8},
                },
            ],
            "summary": {
                "headline": headline,
                "denominators": {
                    "pixels_wide": width, "pixels_high": height,
                    "bytes": len(png),
                    "resolution_m": product["resolution_m"] if observed else None,
                },
            },
            "drilldowns": [],
            "limitations": limitations,
        }]
        if not observed:
            result["actions"].append({
                "action_id": "enable-earth-engine",
                "kind": "data_request",
                "label": (
                    "Install earthengine-api in the bridge interpreter and give it network access "
                    f"to earthengine.googleapis.com, so {product['product_name']} can be "
                    "retrieved instead of generated"
                ),
                "capability_id": "earth-layer",
                "arguments": {"layer": product["product_id"]},
                "requires_confirmation": True,
                "expected_effect": (
                    "The same layer would return as observed, product-attributed evidence."
                ),
            })
        result["audit"]["earth_layer"] = {
            "product_id": product["product_id"],
            "requested": requested,
            "bounds": [west, south, east, north],
            "pixels": [width, height],
            "observed": observed,
            **detail,
        }
        return self._write(result, {
            "declared-aoi": ("application/geo+json", aoi),
            "earth-layer-raster": ("image/png", png),
        })

    def _unsupported(
        self, result_id: str, request_id: str, original: str, bindings: dict[str, Any],
        requested: str,
    ) -> dict[str, Any]:
        """The user asked for a layer this registry does not carry. Say which ones it does."""
        supported = self.supported_layers()
        headline = (
            f"No registered earth layer matches {requested!r}. This site can render: "
            + ", ".join(item["label"] for item in supported) + "."
        )
        result = self._base(
            result_id, request_id, original,
            "Match the requested earth layer against the registered product list.",
            bindings, headline, ["missing"], "blocked", [], "none",
        )
        result["answer"]["detail"] = (
            "Nothing was drawn. A layer this registry does not carry is a gap in the registry, "
            "not a statement about the site."
        )
        catalogue_ref = self._data_ref(
            "earth-layer-catalogue", "application/json", supported)
        limitation = self._limitation(
            "earth-layer-not-registered",
            (
                f"{requested!r} maps to no registered product. Registered products: "
                + "; ".join(
                    f"{item['label']} ({item['product_name']}, {item['resolution_m']} m)"
                    for item in supported
                ) + "."
            ),
            severity="error", affects=["answer"],
        )
        result["limitations"].append(limitation)
        result["visuals"] = [{
            "visual_id": "earth-layer-catalogue",
            "visual_type": "table",
            "view": "earth-layer-raster",
            "title": "Earth layers this site can render",
            "priority": "primary",
            "status": "blocked",
            "scope": {"aoi_ids": ["target"], "time": {"start": None, "end": None}},
            "layers": [{
                "layer_id": "earth-layer-catalogue", "evidence_class": "missing",
                "geometry_type": "table", "data_ref": catalogue_ref,
                "legend": {"label": "Registered earth-observation products"},
                "style_hint": {"palette_role": "missing"},
            }],
            "summary": {"headline": headline, "denominators": {"products": len(supported)}},
            "drilldowns": [],
            "limitations": [limitation],
        }]
        return self._write(result, {
            "earth-layer-catalogue": ("application/json", supported),
        })


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--ee-fetch" in argv:
        # Child mode. One JSON request on stdin, one JSON result on stdout, image bytes on disk.
        try:
            print(json.dumps(_ee_fetch(json.loads(sys.stdin.read()))), flush=True)
        except Exception as exc:
            print(
                json.dumps({"ok": False, "error": f"{type(exc).__name__}: {str(exc)[:400]}"}),
                flush=True,
            )
            return 1
        return 0
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-pack", type=pathlib.Path, required=True)
    parser.add_argument("--index", type=pathlib.Path, required=True)
    parser.add_argument("--state", type=pathlib.Path, required=True)
    parser.add_argument("--layer", required=True)
    args = parser.parse_args(argv)
    service = EarthLayerService(args.site_pack, args.index, args.state)
    print(json.dumps(
        service.build_layer(args.layer), indent=2, ensure_ascii=False, default=str
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
