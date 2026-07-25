"""A user-supplied table must stay session-scoped, reported, and honest about non-matches."""

import json
import os
import pathlib
import tempfile
import unittest
import zipfile

try:
    import jsonschema
except ImportError:  # The producer itself remains standard-library only.
    jsonschema = None

from dss.visual_index.build import Builder
from dss.visual_index.result_service import ResultService
from dss.visual_index.upload_service import (
    UPLOAD_CAPABILITIES, UploadService, _read_xlsx_stdlib, profile_sheet, read_sheets,
)


ROOT = pathlib.Path(__file__).resolve().parents[3]
PACK = ROOT / "dss" / "sites" / "valparai_livelihoods"
IDLISSEUS_SCHEMA = pathlib.Path(
    os.environ.get(
        "IDLI_RESULT_SCHEMA",
        str(ROOT.parent / "idlisseus" / "dss" / "contracts" / "idli-result.schema.json"),
    )
)

CSV_TEXT = """estate_name,survey_date,workers,latitude,longitude
Karumalai Estate,2023-01-15,120,10.31,76.94
karumalai  estate,2023-02-15,118,10.311,76.941
Nedumparai Estate,2023-01-20,90,10.33,76.95
Ghost Estate,2023-03-01,44,10.28,76.90
Nedumparai Estate,2023-02-20,95,10.331,76.951
"""


def _sheet_xml(rows):
    """Build one worksheet part. Strings are inline; the date column uses style 1."""
    body = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for column_index, value in enumerate(row):
            reference = f"{chr(65 + column_index)}{row_index}"
            if isinstance(value, tuple):  # (excel_serial, is_date)
                cells.append(f'<c r="{reference}" s="1"><v>{value[0]}</v></c>')
            elif isinstance(value, (int, float)):
                cells.append(f'<c r="{reference}"><v>{value}</v></c>')
            else:
                cells.append(
                    f'<c r="{reference}" t="inlineStr"><is><t>{value}</t></is></c>'
                )
        body.append(f'<row r="{row_index}">' + "".join(cells) + "</row>")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        "<sheetData>" + "".join(body) + "</sheetData></worksheet>"
    )


def write_two_sheet_xlsx(path: pathlib.Path) -> pathlib.Path:
    """Hand-build a minimal two-sheet workbook, including one Excel-serial date column."""
    sheet_one = [
        ["estate_name", "visit_date", "workers"],
        ["Karumalai Estate", (44941, True), 120],   # 2023-01-15
        ["Nedumparai Estate", (44946, True), 90],   # 2023-01-20
        ["Ghost Estate", (44986, True), 44],        # 2023-03-01
    ]
    sheet_two = [
        ["scheme_name", "persondays"],
        ["Pond desilting", 310],
        ["Road repair", 145],
    ]
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Default Extension="rels" ContentType='
            '"application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
            '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/worksheets/sheet2.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            '<Override PartName="/xl/styles.xml" ContentType="application/vnd.'
            'openxmlformats-officedocument.spreadsheetml.styles+xml"/></Types>',
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns='
            '"http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/workbook.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
            '<sheets><sheet name="labour" sheetId="1" r:id="rId1"/>'
            '<sheet name="schemes" sheetId="2" r:id="rId2"/></sheets></workbook>',
        )
        archive.writestr(
            "xl/_rels/workbook.xml.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns='
            '"http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/worksheet" Target="worksheets/sheet2.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/'
            '2006/relationships/styles" Target="styles.xml"/></Relationships>',
        )
        archive.writestr(
            "xl/styles.xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            '<cellXfs count="2"><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>',
        )
        archive.writestr("xl/worksheets/sheet1.xml", _sheet_xml(sheet_one))
        archive.writestr("xl/worksheets/sheet2.xml", _sheet_xml(sheet_two))
    return path


class UploadProfilingTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_csv_profile_infers_types_dates_coordinates_and_name_columns(self):
        path = self.root / "wages.csv"
        path.write_text(CSV_TEXT)
        sheets, reader = read_sheets(path)
        self.assertEqual(reader, "stdlib-csv")
        self.assertEqual(len(sheets), 1)
        profile = profile_sheet(sheets[0])
        self.assertEqual(profile["row_count"], 5)
        self.assertEqual(profile["column_count"], 5)
        types = {item["column"]: item["inferred_type"] for item in profile["columns"]}
        self.assertEqual(types["estate_name"], "text")
        self.assertEqual(types["survey_date"], "date")
        self.assertEqual(types["workers"], "numeric")
        self.assertEqual(profile["latitude_column"], "latitude")
        self.assertEqual(profile["longitude_column"], "longitude")
        self.assertEqual(profile["date_columns"][0], "survey_date")
        self.assertEqual(
            [item["column"] for item in profile["entity_candidates"]][0], "estate_name"
        )

    def test_stdlib_xlsx_reader_reads_every_sheet_and_decodes_serial_dates(self):
        path = write_two_sheet_xlsx(self.root / "book.xlsx")
        sheets = _read_xlsx_stdlib(path)
        self.assertEqual([item["sheet"] for item in sheets], ["labour", "schemes"])
        self.assertEqual(sheets[0]["header"], ["estate_name", "visit_date", "workers"])
        self.assertEqual(sheets[0]["rows"][0][1], "2023-01-15")
        self.assertEqual(sheets[1]["rows"][1], ["Road repair", 145])
        profile = profile_sheet(sheets[0])
        self.assertEqual(profile["row_count"], 3)
        self.assertEqual(
            {item["column"] for item in profile["entity_candidates"]}, {"estate_name"}
        )


class UploadResultTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = pathlib.Path(cls.temp.name)
        Builder(PACK, cls.root / "index").run()
        cls.result_service = ResultService(
            PACK, cls.root / "index" / "site_index.sqlite", cls.root / "state"
        )
        cls.service = UploadService.from_result_service(cls.result_service)
        cls.csv_path = cls.root / "wages.csv"
        cls.csv_path.write_text(CSV_TEXT)
        cls.xlsx_path = write_two_sheet_xlsx(cls.root / "book.xlsx")
        cls.schema = (
            json.loads(IDLISSEUS_SCHEMA.read_text(encoding="utf-8"))
            if jsonschema is not None and IDLISSEUS_SCHEMA.is_file() else None
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def assert_contract(self, result):
        self.assertEqual(result["schema_version"], "idli-result/1")
        for field in (
            "result_id", "request_id", "revision", "status", "site", "question", "answer",
            "visuals", "limitations", "actions", "audit",
        ):
            self.assertIn(field, result)
        if self.schema:
            jsonschema.Draft202012Validator(self.schema).validate(result)

    def test_registered_upload_capabilities_are_declared(self):
        self.assertEqual(
            [item["capability_id"] for item in UPLOAD_CAPABILITIES],
            ["upload-profile", "upload-cross-join"],
        )
        for item in UPLOAD_CAPABILITIES:
            self.assertEqual(item["availability"], "ready")
            self.assertEqual(item["scope"], "session")

    def test_ingest_is_immutable_and_content_addressed(self):
        first = self.service.ingest("sess-a", self.csv_path)
        second = self.service.ingest("sess-a", self.csv_path)
        self.assertEqual(first["upload_id"], second["upload_id"])
        self.assertEqual(first["ingested_at"], second["ingested_at"])
        stored = pathlib.Path(first["stored_path"])
        self.assertTrue(stored.is_file())
        self.assertIn("uploads", stored.parts)
        self.assertIn("sess-a", stored.parts)
        self.assertEqual(stored.read_text(), CSV_TEXT)

    def test_profile_result_is_a_reported_session_scoped_bundle(self):
        manifest = self.service.ingest("sess-b", self.csv_path)
        result = self.service.profile_result(
            "sess-b", manifest["upload_id"], "req-profile-1", "Show me my spreadsheet"
        )
        self.assert_contract(result)
        self.assertTrue(result["result_id"].startswith("result-upl-sess-b-"))
        self.assertEqual(result["status"], "complete")
        self.assertTrue(result["site"]["synthetic"])
        self.assertEqual(
            result["audit"]["session_binding"],
            {
                "session_id": "sess-b", "upload_id": manifest["upload_id"],
                "content_sha256": manifest["content_sha256"], "scope": "session",
            },
        )
        self.assertTrue(result["audit"]["source_versions"][0]["user_supplied"])
        codes = {item["code"] for item in result["limitations"]}
        self.assertIn("user-supplied-unverified", codes)
        self.assertIn("synthetic-data", codes)
        views = {item["view"] for item in result["visuals"]}
        self.assertEqual(views, {
            "upload-observed-points", "upload-sample-table", "upload-metric-series",
            "upload-stat-tiles",
        })
        for visual in result["visuals"]:
            for layer in visual["layers"]:
                self.assertIn(layer["evidence_class"], {"reported", "derived"})
        self.assertIn(
            "upload-cross-join",
            {item["capability_id"] for item in result["actions"]},
        )
        # Payload bytes are written beside the envelope and match the declared digests.
        stored = self.service.state_root / "results" / result["result_id"]
        self.assertTrue((stored / "result.json").is_file())
        points = json.loads((stored / "data" / "upload-points.geojson").read_text())
        self.assertEqual(len(points["features"]), 5)
        self.assertEqual(points["features"][0]["properties"]["estate_name"],
                         "Karumalai Estate")
        series = json.loads((stored / "data" / "upload-series.json").read_text())
        self.assertEqual([item["bucket"] for item in series],
                         ["2023-01", "2023-02", "2023-03"])
        self.assertAlmostEqual(series[0]["mean"], 105.0)

    def test_cross_join_reports_matches_and_lists_every_unmatched_name(self):
        manifest = self.service.ingest("sess-c", self.csv_path)
        result = self.service.cross_join_result(
            "sess-c", manifest["upload_id"], "req-join-1", "Do my estates exist here?"
        )
        self.assert_contract(result)
        self.assertEqual(result["status"], "partial")
        self.assertEqual(result["question"]["bindings"]["column"], "estate_name")
        stored = self.service.state_root / "results" / result["result_id"]
        rates = json.loads((stored / "data" / "upload-match-rates.json").read_text())
        self.assertEqual(rates[0]["distinct_names"], 4)
        self.assertEqual(rates[0]["matched_names"], 3)
        self.assertEqual(rates[0]["unmatched_names"], 1)
        self.assertEqual(rates[0]["match_rate"], 0.75)
        matched = json.loads((stored / "data" / "upload-matched-names.json").read_text())
        by_name = {item["uploaded_name"]: item for item in matched}
        # Case and repeated-space differences must still resolve to the same entity.
        self.assertEqual(
            by_name["Karumalai Estate"]["entity_id"],
            by_name["karumalai  estate"]["entity_id"],
        )
        self.assertEqual(by_name["Karumalai Estate"]["match_type"], "exact")
        self.assertEqual(by_name["karumalai  estate"]["match_type"], "normalised")
        self.assertEqual(by_name["Nedumparai Estate"]["uploaded_rows"], 2)
        self.assertEqual(by_name["Nedumparai Estate"]["value_sum"], 185.0)
        self.assertEqual(by_name["Nedumparai Estate"]["source_rows"], [4, 6])
        unmatched = json.loads((stored / "data" / "upload-unmatched-names.json").read_text())
        self.assertEqual([item["uploaded_name"] for item in unmatched], ["Ghost Estate"])
        codes = {item["code"] for item in result["limitations"]}
        self.assertIn("non-match-is-not-absence", codes)
        self.assertIn("name-join-only", codes)
        joined = json.loads((stored / "data" / "upload-joined-points.geojson").read_text())
        self.assertTrue(joined["features"])
        for feature in joined["features"]:
            self.assertEqual(len(feature["geometry"]["coordinates"]), 2)
            self.assertIn("uploaded_name", feature["properties"])

    def test_multi_sheet_workbook_profiles_each_sheet_separately(self):
        manifest = self.service.ingest("sess-d", self.xlsx_path)
        self.assertEqual([item["sheet"] for item in manifest["sheets"]],
                         ["labour", "schemes"])
        first = self.service.profile_result(
            "sess-d", manifest["upload_id"], "req-xlsx-1", "Show my workbook"
        )
        self.assert_contract(first)
        self.assertEqual(first["question"]["bindings"]["sheet"], "labour")
        self.assertIn(
            "profile-sheet-schemes",
            {item["action_id"] for item in first["actions"]},
        )
        second = self.service.profile_result(
            "sess-d", manifest["upload_id"], "req-xlsx-2", "Show the schemes sheet",
            sheet="schemes",
        )
        self.assert_contract(second)
        self.assertNotEqual(first["result_id"], second["result_id"])
        self.assertEqual(second["question"]["bindings"]["sheet"], "schemes")
        rows = json.loads(
            (self.service.state_root / "results" / second["result_id"] / "data"
             / "upload-sample-rows.json").read_text()
        )
        self.assertEqual(rows[0]["scheme_name"], "Pond desilting")

    def test_workbook_profiles_identically_without_openpyxl(self):
        """The bridge venv has no openpyxl; the stdlib reader must produce the same profile."""
        import dss.visual_index.upload_service as module

        manifest = self.service.ingest("sess-openpyxl", self.xlsx_path)
        original = module.openpyxl
        module.openpyxl = None
        try:
            stdlib_manifest = self.service.ingest("sess-stdlib", self.xlsx_path)
            result = self.service.profile_result(
                "sess-stdlib", stdlib_manifest["upload_id"], "req-stdlib-1", "Show it"
            )
        finally:
            module.openpyxl = original
        self.assertEqual(stdlib_manifest["reader"], "stdlib-zipfile-xml")
        self.assert_contract(result)
        self.assertEqual(
            [item["sheet"] for item in stdlib_manifest["sheets"]],
            [item["sheet"] for item in manifest["sheets"]],
        )
        self.assertEqual(
            stdlib_manifest["sheets"][0]["columns"][1]["first"],
            manifest["sheets"][0]["columns"][1]["first"],
        )

    def test_explaining_an_upload_mark_never_borrows_pack_rows(self):
        from dss.visual_index.explain_service import ExplainService

        manifest = self.service.ingest("sess-explain", self.csv_path)
        result = self.service.cross_join_result(
            "sess-explain", manifest["upload_id"], "req-explain-1", "Match these"
        )
        explain = ExplainService.from_result_service(self.result_service)
        lineage = explain.explain(
            result["result_id"], "upload-joined-points", "Nedumparai Estate"
        )
        self.assertEqual(lineage["evidence_origin"], "user_upload")
        self.assertEqual(lineage["computation"]["aggregation"], "user-supplied")
        self.assertEqual(lineage["computation"]["plane"], "upload")
        self.assertIn("user-supplied upload", lineage["computation"]["statement"])
        self.assertIn("File rows", lineage["computation"]["statement"])
        self.assertTrue(
            lineage["source_versions"][0]["source_id"].startswith("upload:")
        )

    def test_uploads_do_not_leak_across_sessions(self):
        manifest = self.service.ingest("sess-e", self.csv_path)
        self.assertIsNone(self.service.load_manifest("sess-f", manifest["upload_id"]))
        self.assertEqual(self.service.list_uploads("sess-f"), [])
        self.assertEqual(
            [item["upload_id"] for item in self.service.list_uploads("sess-e")],
            [manifest["upload_id"]],
        )
        with self.assertRaises(LookupError):
            self.service.profile_result(
                "sess-f", manifest["upload_id"], "req-leak", "Show it"
            )
        mine = self.service.profile_result(
            "sess-e", manifest["upload_id"], "req-mine", "Show it"
        )
        self.assertTrue(mine["result_id"].startswith("result-upl-sess-e-"))
        self.assertEqual(mine["audit"]["session_binding"]["session_id"], "sess-e")


if __name__ == "__main__":
    unittest.main()
