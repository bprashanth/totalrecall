"""A computed map layer must be a real image, correctly placed, and honest about its origin.

The default suite runs with Earth Engine forced off, so the deterministic fallback contract is
tested hermetically and behaves identically on a machine with credentials and one without. The
real Earth Engine path costs a live request, so it is opt-in:

    IDLI_TEST_EARTH_ENGINE=1 python3 -m unittest dss.visual_index.tests.test_earth_layer_service

Both paths are held to the same structural contract: a valid PNG whose size the envelope reports
honestly, bounds equal to the AOI bbox, and an envelope that says which path produced the image.
"""

import os
import pathlib
import struct
import tempfile
import unittest
import zlib

from dss.visual_index.build import Builder
from dss.visual_index.earth_layer_service import (
    PRODUCTS, EarthLayerService, encode_png, png_size,
)
from dss.visual_index.result_service import ResultService


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"
LIVE_EARTH_ENGINE = os.environ.get("IDLI_TEST_EARTH_ENGINE", "").strip() not in {"", "0"}


def walk_png(payload: bytes) -> dict[str, object]:
    """Validate any PNG structurally: signature, chunk CRCs, IHDR. Colour type is not assumed.

    Earth Engine returns whichever encoding suits the product — RGB for a fully covered palette
    render, grey for a hillshade, RGBA where a clip masks part of the frame — so a decoder that
    insisted on RGBA would reject perfectly good imagery.
    """
    assert payload[:8] == b"\x89PNG\r\n\x1a\x0a", "not a PNG"
    offset, chunks, header = 8, [], {}
    data = b""
    while offset < len(payload):
        (length,) = struct.unpack(">I", payload[offset:offset + 4])
        kind = payload[offset + 4:offset + 8]
        body = payload[offset + 8:offset + 8 + length]
        stored = struct.unpack(">I", payload[offset + 8 + length:offset + 12 + length])[0]
        assert zlib.crc32(kind + body) & 0xFFFFFFFF == stored, f"bad CRC on {kind!r}"
        chunks.append(kind)
        if kind == b"IHDR":
            width, height, depth, colour, _, _, interlace = struct.unpack(">IIBBBBB", body[:13])
            header = {"width": width, "height": height, "depth": depth,
                      "colour": colour, "interlace": interlace}
        elif kind == b"IDAT":
            data += body
        offset += 12 + length
    assert chunks[0] == b"IHDR" and chunks[-1] == b"IEND", "malformed chunk order"
    assert data, "no image data"
    return {**header, "chunks": chunks, "raw": zlib.decompress(data)}


def read_rgba(payload: bytes) -> tuple[int, int, list[list[tuple[int, ...]]]]:
    """Decode an 8-bit RGBA, filter-0 PNG — what `encode_png` writes, nothing more."""
    info = walk_png(payload)
    assert (info["depth"], info["colour"]) == (8, 6), "expected 8-bit RGBA"
    width, height, raw = info["width"], info["height"], info["raw"]
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
        pixels = [bytes((10, 20, 30, 255) * 3), bytes((0, 0, 0, 0) * 3)]
        width, height, rows = read_rgba(encode_png(3, 2, pixels))
        self.assertEqual((width, height), (3, 2))
        self.assertEqual(rows[0][0], (10, 20, 30, 255))
        self.assertEqual(rows[1][2], (0, 0, 0, 0))

    def test_encoder_refuses_a_row_that_does_not_match_the_declared_size(self):
        with self.assertRaises(ValueError):
            encode_png(3, 1, [bytes(8)])

    def test_png_size_reads_any_header_and_rejects_non_png(self):
        self.assertEqual(png_size(encode_png(3, 2, [bytes(12), bytes(12)])), (3, 2))
        self.assertIsNone(png_size(b"not an image"))
        self.assertIsNone(png_size(b""))


class RegistryTest(unittest.TestCase):
    """The registry is the attribution. If it is vague or wrong, every envelope inherits that."""

    def test_every_product_declares_a_usable_asset_and_honest_attribution(self):
        for product in PRODUCTS:
            spec = product["earth_engine"]
            self.assertIn(spec["asset_kind"], {"image", "collection"})
            self.assertRegex(spec["asset"], r"^[A-Za-z0-9_/\-]+$")
            self.assertTrue(spec["band"])
            self.assertGreater(product["resolution_m"], 0)
            self.assertTrue(product["product_date"])
            self.assertTrue(product["publisher"])
            self.assertTrue(product["measures"], product["product_id"])
            self.assertTrue(product["fallback"]["basis"])

    def test_free_text_resolves_to_the_registry(self):
        cases = {
            "make the map a map of built-up": "built-up",
            "show me settlement here": "built-up",
            "can I see elevation for this site": "elevation",
            "terrain please": "elevation",
            "tree cover": "tree-cover",
            "tree-cover": "tree-cover",
            "what about forest": "tree-cover",
            "land cover": "tree-cover",
        }
        for text, product_id in cases.items():
            self.assertEqual(
                EarthLayerService.resolve_product(text)["product_id"], product_id, text
            )
        self.assertIsNone(EarthLayerService.resolve_product("soil moisture"))


class _ServiceCase(unittest.TestCase):
    @classmethod
    def build_service(cls):
        cls.temp = tempfile.TemporaryDirectory()
        root = pathlib.Path(cls.temp.name)
        cls.index_root = root / "index"
        cls.state_root = root / "state"
        Builder(PACK, cls.index_root).run()
        cls.result_service = ResultService(
            PACK, cls.index_root / "site_index.sqlite", cls.state_root
        )
        return EarthLayerService.from_result_service(cls.result_service)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def raster_layer(self, envelope):
        return next(
            item for item in envelope["visuals"][0]["layers"]
            if item["geometry_type"] == "raster_image"
        )

    def assert_common_contract(self, envelope):
        """Everything that must hold whether the image was retrieved or generated."""
        self.assertEqual(envelope["status"], "complete")
        layer = self.raster_layer(envelope)
        self.assertEqual(layer["data_ref"]["media_type"], "image/png")

        served = self.service.load_data(envelope["result_id"], layer["data_ref"]["handle"])
        self.assertIsNotNone(served)
        media_type, payload = served
        self.assertEqual(media_type, "image/png")
        info = walk_png(payload)
        self.assertEqual(
            [info["width"], info["height"]], envelope["audit"]["earth_layer"]["pixels"],
            "the envelope must report the size of the image that actually exists",
        )
        self.assertGreater(info["width"], 0)
        self.assertGreater(info["height"], 0)

        west, south, east, north = layer["bounds"]
        self.assertEqual([west, south, east, north], list(self.service.aoi_bbox()))
        self.assertLess(west, east)
        self.assertLess(south, north)
        self.assertTrue(-180 <= west <= 180 and -180 <= east <= 180)
        self.assertTrue(-90 <= south <= 90 and -90 <= north <= 90)
        self.assertEqual(layer["bounds"], envelope["audit"]["earth_layer"]["bounds"])

        # The renderer frames the map on vector geometry; a lone raster would have no extent.
        layers = envelope["visuals"][0]["layers"]
        self.assertEqual(layers[0]["layer_id"], "declared-aoi")
        self.assertEqual(layers[0]["geometry_type"], "polygon")
        return payload


class EarthLayerFallbackTest(_ServiceCase):
    """Earth Engine forced off: the declared fallback must still honour the whole contract."""

    @classmethod
    def setUpClass(cls):
        cls.service = cls.build_service()
        # Pin the probe cache rather than reaching for the network, so this suite behaves the
        # same with credentials and without, and never depends on a live service.
        cls.service._engine = {
            "available": False, "project": "test", "python": None,
            "reason": "forced off for the hermetic fallback suite",
        }
        cls.envelope = cls.service.build_layer("built-up", request_id="test-builtup")

    def test_fallback_honours_the_shared_contract(self):
        payload = self.assert_common_contract(self.envelope)
        # The fallback is written by our own encoder, so it is always 8-bit RGBA.
        _, _, rows = read_rgba(payload)
        self.assertGreater(len({pixel[:3] for row in rows for pixel in row}), 8,
                           "a surface with no variation is a bug, not a layer")

    def test_every_registered_product_renders(self):
        for product in PRODUCTS:
            envelope = self.service.build_layer(
                product["product_id"], request_id=f"test-{product['product_id']}"
            )
            self.assertEqual(envelope["status"], "complete", product["product_id"])
            self.assertEqual(
                envelope["audit"]["earth_layer"]["product_id"], product["product_id"]
            )
            self.assertFalse(envelope["audit"]["earth_layer"]["observed"])

    def test_raster_is_clipped_to_the_declared_aoi(self):
        """Pixels the pack makes no claim about must be transparent, not coloured."""
        service = self.service
        payload = service.load_data(
            self.envelope["result_id"], self.raster_layer(self.envelope)["data_ref"]["handle"]
        )[1]
        width, height, rows = read_rgba(payload)
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

    def test_a_generated_image_says_so_unmistakably(self):
        envelope = self.envelope
        self.assertEqual(envelope["audit"]["earth_layer"]["path"], "deterministic_fallback")
        self.assertEqual(self.raster_layer(envelope)["evidence_class"], "modelled")
        self.assertEqual(envelope["audit"]["assurance"], "generated")
        version = envelope["audit"]["source_versions"][0]
        self.assertTrue(version["synthetic"])
        self.assertTrue(version["source_id"].startswith("synthetic:"))
        synthetic = next(
            item for item in envelope["limitations"] if item["code"] == "synthetic-raster"
        )
        self.assertEqual(synthetic["severity"], "error")
        self.assertIn("SYNTHETIC", synthetic["message"])
        self.assertIn("forced off", synthetic["message"], "the reason must be carried through")
        self.assertIn("SYNTHETIC", envelope["answer"]["headline"].upper())
        self.assertTrue(
            any(item["action_id"] == "enable-earth-engine" for item in envelope["actions"])
        )

    def test_engine_probe_reports_rather_than_raises(self):
        fresh = EarthLayerService.from_result_service(self.result_service)
        status = fresh.engine_status()
        self.assertIn("available", status)
        self.assertTrue(status["reason"], "the probe must always say what it found")

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


@unittest.skipUnless(
    LIVE_EARTH_ENGINE, "set IDLI_TEST_EARTH_ENGINE=1 to exercise the live Earth Engine path"
)
class EarthLayerEngineTest(_ServiceCase):
    """The real path: a published product, retrieved and attributed to its own asset."""

    @classmethod
    def setUpClass(cls):
        cls.service = cls.build_service()
        cls.envelope = cls.service.build_layer("built-up", request_id="live-builtup")

    def test_retrieved_product_is_derived_evidence_attributed_to_its_asset(self):
        envelope = self.envelope
        audit = envelope["audit"]["earth_layer"]
        self.assertTrue(audit["observed"], f"Earth Engine was not reached: {audit.get('note')}")
        self.assertEqual(audit["path"], "earth_engine")
        self.assertEqual(envelope["audit"]["assurance"], "retrieved")
        self.assertEqual(self.raster_layer(envelope)["evidence_class"], "derived")

        product = EarthLayerService.resolve_product("built-up")
        version = envelope["audit"]["source_versions"][0]
        self.assertFalse(version["synthetic"])
        self.assertEqual(version["asset"], product["earth_engine"]["asset"])
        self.assertEqual(
            version["source_id"], f"earth-engine:{product['earth_engine']['asset']}"
        )
        self.assertEqual(version["resolution_m"], product["resolution_m"])
        self.assertEqual(version["product_date"], product["product_date"])

        limitation = next(
            item for item in envelope["limitations"]
            if item["code"] == "product-resolution-and-date"
        )
        for expected in (
            product["earth_engine"]["asset"], str(product["resolution_m"]),
            product["product_date"], product["publisher"],
        ):
            self.assertIn(expected, limitation["message"])
        self.assertNotIn(
            "synthetic-raster", {item["code"] for item in envelope["limitations"]},
            "a retrieved product must never carry the synthetic label",
        )

    def test_retrieved_image_honours_the_shared_contract(self):
        self.assert_common_contract(self.envelope)

    def test_every_registered_product_retrieves(self):
        for product in PRODUCTS:
            envelope = self.service.build_layer(
                product["product_id"], request_id=f"live-{product['product_id']}"
            )
            audit = envelope["audit"]["earth_layer"]
            self.assertTrue(audit["observed"], f"{product['product_id']}: {audit.get('note')}")
            self.assertEqual(
                envelope["audit"]["source_versions"][0]["asset"],
                product["earth_engine"]["asset"],
            )
            self.assert_common_contract(envelope)


if __name__ == "__main__":
    unittest.main()
