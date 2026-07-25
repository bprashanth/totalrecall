"""A computed map layer must be a real image, correctly placed, and honest about its origin.

Earth Engine is not reachable from the test environment, so these checks exercise the fallback
path deliberately: the contract has to hold whether the surface was retrieved or generated, and
the generated case has to be unmistakably labelled as such.
"""

import pathlib
import struct
import tempfile
import unittest
import zlib

from dss.visual_index.build import Builder
from dss.visual_index.earth_layer_service import (
    PRODUCTS, EarthLayerService, encode_png,
)
from dss.visual_index.result_service import ResultService


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"


def read_png(payload: bytes) -> tuple[int, int, list[list[tuple[int, int, int, int]]]]:
    """Decode an 8-bit RGBA, filter-0 PNG — exactly what `encode_png` writes, nothing more."""
    assert payload[:8] == b"\x89PNG\r\n\x1a\x0a", "not a PNG"
    offset = 8
    width = height = 0
    data = b""
    while offset < len(payload):
        (length,) = struct.unpack(">I", payload[offset:offset + 4])
        kind = payload[offset + 4:offset + 8]
        body = payload[offset + 8:offset + 8 + length]
        stored = struct.unpack(">I", payload[offset + 8 + length:offset + 12 + length])[0]
        assert zlib.crc32(kind + body) & 0xFFFFFFFF == stored, f"bad CRC on {kind!r}"
        if kind == b"IHDR":
            width, height, depth, colour = struct.unpack(">IIBB", body[:10])
            assert (depth, colour) == (8, 6), "expected 8-bit RGBA"
        elif kind == b"IDAT":
            data += body
        offset += 12 + length
    raw = zlib.decompress(data)
    stride = width * 4
    rows = []
    for y in range(height):
        start = y * (stride + 1)
        assert raw[start] == 0, "expected filter type 0"
        line = raw[start + 1:start + 1 + stride]
        rows.append([tuple(line[x * 4:x * 4 + 4]) for x in range(width)])
    return width, height, rows


class EncodePngTest(unittest.TestCase):
    def test_encoder_round_trips_exact_pixels(self):
        pixels = [
            bytes((10, 20, 30, 255) * 3),
            bytes((0, 0, 0, 0) * 3),
        ]
        width, height, rows = read_png(encode_png(3, 2, pixels))
        self.assertEqual((width, height), (3, 2))
        self.assertEqual(rows[0][0], (10, 20, 30, 255))
        self.assertEqual(rows[1][2], (0, 0, 0, 0))

    def test_encoder_refuses_a_row_that_does_not_match_the_declared_size(self):
        with self.assertRaises(ValueError):
            encode_png(3, 1, [bytes(8)])


class EarthLayerServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        cls.index_root = root / "index"
        cls.state_root = root / "state"
        Builder(PACK, cls.index_root).run()
        cls.result_service = ResultService(
            PACK, cls.index_root / "site_index.sqlite", cls.state_root
        )
        cls.service = EarthLayerService.from_result_service(cls.result_service)
        cls.envelope = cls.service.build_layer("built-up", request_id="test-builtup")

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def _raster_layer(self, envelope=None):
        envelope = envelope or self.envelope
        return next(
            item for item in envelope["visuals"][0]["layers"]
            if item["geometry_type"] == "raster_image"
        )

    # ------------------------------------------------------------------ words to products

    def test_free_text_resolves_to_the_registry(self):
        cases = {
            "make the map a map of built-up": "built-up",
            "show me settlement here": "built-up",
            "can I see elevation for this site": "elevation",
            "terrain please": "elevation",
            "tree cover": "tree-cover",
            "what about forest": "tree-cover",
        }
        for text, product_id in cases.items():
            self.assertEqual(
                EarthLayerService.resolve_product(text)["product_id"], product_id, text
            )
        self.assertIsNone(EarthLayerService.resolve_product("soil moisture"))

    def test_every_registered_product_renders(self):
        for product in PRODUCTS:
            envelope = self.service.build_layer(
                product["product_id"], request_id=f"test-{product['product_id']}"
            )
            self.assertEqual(envelope["status"], "complete", product["product_id"])
            self.assertEqual(
                envelope["audit"]["earth_layer"]["product_id"], product["product_id"]
            )

    # ------------------------------------------------------------------ the image itself

    def test_stored_payload_is_a_valid_png_of_the_declared_size(self):
        layer = self._raster_layer()
        self.assertEqual(layer["data_ref"]["media_type"], "image/png")
        served = self.service.load_data(self.envelope["result_id"], layer["data_ref"]["handle"])
        self.assertIsNotNone(served)
        media_type, payload = served
        self.assertEqual(media_type, "image/png")
        width, height, rows = read_png(payload)
        declared = self.envelope["audit"]["earth_layer"]["pixels"]
        self.assertEqual([width, height], declared)
        self.assertEqual(len(rows), height)
        self.assertTrue(all(len(row) == width for row in rows))
        # A surface with no variation is a bug, not a layer.
        self.assertGreater(len({pixel[:3] for row in rows for pixel in row}), 8)

    def test_raster_is_clipped_to_the_declared_aoi(self):
        """Pixels the pack makes no claim about must be transparent, not coloured."""
        service = self.service
        width, height, rows = read_png(
            service.load_data(
                self.envelope["result_id"], self._raster_layer()["data_ref"]["handle"]
            )[1]
        )
        west, south, east, north = service.aoi_bbox()
        ring = service.aoi_ring()
        for y in (0, height // 2, height - 1):
            lat = north - (north - south) * (y + 0.5) / height
            for x in (0, width // 2, width - 1):
                lon = west + (east - west) * (x + 0.5) / width
                inside = service._inside_ring(lon, lat, ring)
                alpha = rows[y][x][3]
                self.assertEqual(
                    alpha > 0, inside,
                    f"pixel ({x},{y}) at {lat:.4f},{lon:.4f} inside={inside} alpha={alpha}",
                )

    def test_bounds_are_the_aoi_bbox_and_are_sane(self):
        layer = self._raster_layer()
        west, south, east, north = layer["bounds"]
        self.assertEqual([west, south, east, north], list(self.service.aoi_bbox()))
        self.assertLess(west, east)
        self.assertLess(south, north)
        self.assertTrue(-180 <= west <= 180 and -180 <= east <= 180)
        self.assertTrue(-90 <= south <= 90 and -90 <= north <= 90)
        self.assertEqual(layer["bounds"], self.envelope["audit"]["earth_layer"]["bounds"])

    def test_a_vector_layer_accompanies_the_raster(self):
        """The renderer frames the map on vector geometry; a lone raster would have no extent."""
        layers = self.envelope["visuals"][0]["layers"]
        self.assertEqual(layers[0]["layer_id"], "declared-aoi")
        self.assertEqual(layers[0]["geometry_type"], "polygon")
        self.assertEqual(layers[0]["data_ref"]["media_type"], "application/geo+json")

    # ------------------------------------------------------------------ provenance

    def test_the_envelope_says_which_path_produced_the_image(self):
        audit = self.envelope["audit"]["earth_layer"]
        self.assertIn(audit["path"], {"earth_engine", "deterministic_fallback"})
        self.assertEqual(audit["observed"], audit["path"] == "earth_engine")
        version = self.envelope["audit"]["source_versions"][0]
        codes = {item["code"] for item in self.envelope["limitations"]}
        if audit["observed"]:
            self.assertEqual(self._raster_layer()["evidence_class"], "derived")
            self.assertFalse(version["synthetic"])
            self.assertIn("product-resolution-and-date", codes)
            self.assertTrue(version["resolution_m"])
            self.assertTrue(version["product_date"])
            self.assertEqual(self.envelope["audit"]["assurance"], "retrieved")
        else:
            # No credential, no network: the layer must announce itself as generated.
            self.assertEqual(self._raster_layer()["evidence_class"], "modelled")
            self.assertTrue(version["synthetic"])
            self.assertIn("synthetic-raster", codes)
            self.assertEqual(self.envelope["audit"]["assurance"], "generated")
            synthetic = next(
                item for item in self.envelope["limitations"]
                if item["code"] == "synthetic-raster"
            )
            self.assertEqual(synthetic["severity"], "error")
            self.assertIn("SYNTHETIC", synthetic["message"])
            self.assertIn("SYNTHETIC", self.envelope["answer"]["headline"].upper())
            self.assertTrue(
                any(item["action_id"] == "enable-earth-engine"
                    for item in self.envelope["actions"])
            )

    def test_engine_probe_reports_rather_than_raises(self):
        status = self.service.engine_status()
        self.assertIn("available", status)
        self.assertTrue(status["reason"], "an unavailable engine must say why")

    # ------------------------------------------------------------------ unknown layers

    def test_unregistered_layer_is_blocked_and_lists_what_exists(self):
        envelope = self.service.build_layer("soil moisture", request_id="test-unknown")
        self.assertEqual(envelope["status"], "blocked")
        self.assertEqual(envelope["answer"]["evidence_classes"], ["missing"])
        limitation = next(
            item for item in envelope["limitations"]
            if item["code"] == "earth-layer-not-registered"
        )
        self.assertEqual(limitation["severity"], "error")
        for product in PRODUCTS:
            self.assertIn(product["label"], limitation["message"])
        self.assertFalse(
            any(item["geometry_type"] == "raster_image"
                for item in envelope["visuals"][0]["layers"]),
            "a blocked layer must not ship an image",
        )


if __name__ == "__main__":
    unittest.main()
