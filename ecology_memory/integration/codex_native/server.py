#!/usr/bin/env python3
"""OpenAI-compatible bridge from Idlisseus to Codex CLI + native skills.

The bridge keeps one resumable Codex thread per caller-supplied session id.  Codex receives the
same progressive-disclosure skill bundle used by the winning benchmark arm.  Skill calls cross an
allowlisted in-process gateway; model-authored shell commands never choose connector code paths.

Two transports are exposed:

* POST /v1/chat/completions -- OpenAI-compatible, for an Idlisseus model endpoint.
* POST /v1/audit/chat       -- structured SSE, for the step/live audit client.

The OpenAI-compatible transport keeps the answer separate from Idlisseus-native audit events, so
the browser can render a concise chat bubble plus a collapsible ``Why`` trace.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import contextlib
import datetime as dt
import hashlib
import http.server
import json
import math
import os
import pathlib
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from typing import Any, Callable, Iterator


HERE = pathlib.Path(__file__).resolve().parent
MEMORY = HERE.parents[1]
REPO = MEMORY.parent
BENCH = MEMORY / "narrative" / "benchmarks" / "late-bound-skills"
HARNESS = MEMORY / "harness"
HERMES_BENCH = MEMORY / "hermes_bench"
sys.path[:0] = [str(HERE), str(HARNESS), str(HERMES_BENCH)]

import engine as E  # noqa: E402
import executor as X  # noqa: E402
import ir_schema as IR  # noqa: E402
import connectors as C  # noqa: E402
import origin_adapters as ORIGIN  # noqa: E402
import ecology_artifacts as ARTIFACTS  # noqa: E402


MODEL = os.environ.get("CODEX_NATIVE_MODEL", "gpt-5.4")
REASONING = os.environ.get("CODEX_NATIVE_REASONING", "low")
PUBLIC_MODEL = os.environ.get("CODEX_NATIVE_PUBLIC_MODEL", "idli-insight").strip() or "idli-insight"
CODEX = pathlib.Path(os.environ.get("CODEX_NATIVE_CODEX", str(pathlib.Path.home() / ".local/bin/codex")))
AUTH_SOURCE = pathlib.Path(os.environ.get("CODEX_NATIVE_AUTH", str(pathlib.Path.home() / ".codex/auth.json")))
STATE_ROOT = pathlib.Path(os.environ.get("CODEX_NATIVE_STATE_DIR", str(HERE / "runs")))
SKILLS_PATH = pathlib.Path(os.environ.get("CODEX_NATIVE_SKILLS", str(BENCH / "skills.json")))
_TOKEN_FILE = os.environ.get("CODEX_NATIVE_API_TOKEN_FILE", "").strip()
API_TOKEN = os.environ.get("CODEX_NATIVE_API_TOKEN", "").strip()
if not API_TOKEN and _TOKEN_FILE:
    with contextlib.suppress(OSError):
        API_TOKEN = pathlib.Path(_TOKEN_FILE).read_text().strip()
SANDBOX = os.environ.get("CODEX_NATIVE_SANDBOX", "workspace-write").strip()
RUNNER = os.environ.get("CODEX_NATIVE_RUNNER", "hermes-exec").strip()
HERMES_CONTAINER = os.environ.get("CODEX_NATIVE_HERMES_CONTAINER", "hermes-live").strip()
IDLISSEUS_ROOT = pathlib.Path(os.environ.get(
    "CODEX_NATIVE_IDLISSEUS_ROOT",
    "/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus",
))
UPLOAD_ROOT = pathlib.Path(os.environ.get(
    "CODEX_NATIVE_UPLOAD_ROOT", str(IDLISSEUS_ROOT / "data" / "uploads")
))
RESEARCH_ROOT = pathlib.Path(os.environ.get(
    "CODEX_NATIVE_RESEARCH_ROOT", str(IDLISSEUS_ROOT / "data" / "deep_research")
))
REPORT_URL_PREFIX = os.environ.get(
    "CODEX_NATIVE_REPORT_URL_PREFIX", "/api/research/report/"
).rstrip("/") + "/"
MAP_BASE_IMAGE = pathlib.Path(os.environ.get(
    "CODEX_NATIVE_MAP_BASE_IMAGE",
    "/home/beeps/src/github.com/bprashanth/idlisseus/agents/hermes/gt/region_base.jpg",
))
MAP_BASE_BBOX = [78.09, 12.66, 78.25, 12.80]
SITE_PROFILE_PATH = pathlib.Path(os.environ.get(
    "CODEX_NATIVE_SITE_PROFILE",
    str(MEMORY / "integration" / "origin" / "connectors" / "SITE_EBTL.json"),
))
ALGEBRA_9B_URL = os.environ.get(
    "CODEX_NATIVE_ALGEBRA_9B_URL",
    "http://172.17.0.1:8012/v1/chat/completions",
).strip()
ALGEBRA_9B_MODEL = os.environ.get("CODEX_NATIVE_ALGEBRA_9B_MODEL", "lora9b").strip()
ALGEBRA_9B_TIMEOUT = int(os.environ.get("CODEX_NATIVE_ALGEBRA_9B_TIMEOUT", "180"))
MAX_ALGEBRA_PASSES = 3
MAX_ALGEBRA_PLAN_STEPS = 3
CONTAINER_ROOT = pathlib.PurePosixPath("/tmp/codex-native")
MAX_REQUEST_BYTES = 128 * 1024
MAX_ATTACHMENTS = 12
MAX_ATTACHMENT_BYTES = 64 * 1024 * 1024
MAX_REPORT_CHARS = 250_000
ANSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")
SAFE_ID = re.compile(r"[^A-Za-z0-9_.-]+")
SKILL_COMMAND = re.compile(r"skill_call\.py\s+([A-Za-z0-9_.-]+)")
READ_SKILL = re.compile(r"/skills/([A-Za-z0-9_.-]+)/SKILL\.md")
EMBEDDED_TOKEN = re.compile(r"(?i)(\bTOKEN\s*=\s*['\"])[A-Za-z0-9._~-]+(['\"])")
BEARER_TOKEN = re.compile(r"(?i)(\bBearer\s+)[A-Za-z0-9._~-]+")


def _stable_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                      separators=(",", ":"))


def _sha256(value: Any) -> str:
    raw = value if isinstance(value, bytes) else (
        value.encode() if isinstance(value, str) else _stable_json(value).encode()
    )
    return hashlib.sha256(raw).hexdigest()


def _atomic_json(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str) + "\n")
    os.replace(tmp, path)


def _redact_audit(value: Any) -> Any:
    """Remove credentials while preserving the structure needed for a useful audit."""
    if isinstance(value, dict):
        return {
            key: ("[redacted]" if str(key).lower() in {"token", "gateway_token"}
                  else _redact_audit(item))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_audit(item) for item in value]
    if isinstance(value, str):
        return BEARER_TOKEN.sub(r"\1[redacted]", EMBEDDED_TOKEN.sub(r"\1[redacted]\2", value))
    return value


def _safe_id(value: str | None) -> str:
    cleaned = SAFE_ID.sub("-", str(value or "").strip()).strip(".-")
    return (cleaned or secrets.token_hex(12))[:120]


def _inside(root: pathlib.Path, path: pathlib.Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _safe_display_name(value: str | None, fallback: str) -> str:
    name = pathlib.Path(str(value or fallback)).name.strip()
    cleaned = SAFE_ID.sub("-", name).strip(".-")
    return (cleaned or fallback)[:180]


OPERATIONAL_SKILLS = [{
    "id": "compile-scientific-algebra-9b",
    "description": (
        "Compile one explicit scientific question into the frozen ecology Algebra with the local "
        "9B-004d model, bind its leaves to admitted resources, and execute the validated tree."
    ),
    "use_for": ["a source-backed state, relation, trend, comparison or transfer question",
                "turn an explicit scientific sub-question into executable Algebra"],
    "exclude": ["literature discovery", "site orientation", "general background",
                "inventing a taxon, region, dataset or measurement"],
    "supports_ops": ["SELECT", "ANNOTATE", "RELATE", "AGGREGATE", "COMPARE",
                     "ESTIMATE", "RANK"],
    "returns": "Scientific Algebra + bound execution", "georeferenced": True,
    "binding": {"mode": "scientific_algebra"},
    "instructions": (
        "Use only after local/public discovery or the user has established the scientific "
        "entities and scope. Pass one short `scientific_question`; do not pass skills, connector "
        "arguments, coordinates, paths or a hand-written IR. The server supplies the original "
        "question, admitted resource symbols, connector capabilities and the frozen Algebra "
        "grammar. Algebra 9B emits the IR; the controller validates, binds and executes it. "
        "If the returned tree contains a hole, ask that clarification instead of repairing the "
        "tree yourself.\n\n"
        "```bash\npython3 {skill_call} compile-scientific-algebra-9b "
        "'{\"scientific_question\":\"Estimate where source-backed Hanuman langur records from "
        "the approved donor region indicate useful survey locations inside EBTL\"}'\n```"
    ),
}, {
    "id": "site-overview",
    "description": (
        "Build a runtime site snapshot from the onboarded organisation profile, registered "
        "geometry, local evidence partitions, configured data capabilities and explicit gaps."
    ),
    "use_for": ["tell me about the site", "what data do we have for this property",
                "summarise an onboarded conservation site before a narrower question"],
    "exclude": ["semantic searching for the literal words in a site name",
                "treating a site alias as a taxon", "inventing a missing property boundary"],
    "supports_ops": [], "returns": "Site snapshot", "georeferenced": True,
    "binding": {"mode": "site_overview"},
    "instructions": (
        "Pass the declared `site_id` or site alias. This operation inventories registered "
        "resources; it is not an entity search. Keep declared profile facts, reported/observed "
        "local evidence, configured capabilities and gaps separate.\n\n"
        "```bash\npython3 {skill_call} site-overview "
        "'{\"site_id\":\"EBTL\"}'\n```"
    ),
}, {
    "id": "request-model-from-t4gc",
    "description": (
        "Record an explicit user request for a missing ecological model or predictor in the "
        "durable T4GC model-request queue."
    ),
    "use_for": ["submit a missing model request",
                "ask T4GC to build an unsupported ecological predictor"],
    "exclude": ["silently filing requests", "running a model", "ordinary data gaps"],
    "supports_ops": ["REQUEST_MODEL"], "returns": "Request", "georeferenced": False,
    "binding": {"mode": "model_request"},
}, {
    "id": "local-site-evidence-search",
    "description": (
        "Search the organisation's seeded, source-linked local evidence for any entity or topic "
        "before using external literature or public occurrence sources."
    ),
    "use_for": ["what is locally known about a taxon or topic",
                "site evidence seeded by an ecology organisation", "local reports and surveys"],
    "exclude": ["external literature reviews", "regional public occurrence searches",
                "treating a local registry non-match as proof of absence"],
    "supports_ops": ["SELECT"], "returns": "Records", "georeferenced": False,
    "binding": {"mode": "local_evidence_search"},
    "instructions": (
        "Pass the user's focal `query` or `entity` and the declared `region`. Preserve every "
        "returned evidence type and limitation. A registry non-match is not absence. Use external "
        "discovery only after reporting the local result or when the user explicitly asks for it. "
        "Use `--pairs` for names containing apostrophes so the shell cannot alter the query.\n\n"
        "```bash\npython3 {skill_call} local-site-evidence-search "
        "--pairs query=\"Russell's viper\" region=EBTL\n```"
    ),
}, {
    "id": "discover-ecology-evidence",
    "description": (
        "Run the user's actual ecology query across admitted local semantic, OpenAlex, Zenodo "
        "and Dryad connectors and return source-identified discovery leads."
    ),
    "use_for": ["discover papers or datasets for a named ecological question",
                "discover satellite or field datasets", "turn a model hypothesis into a search"],
    "exclude": ["treating a search lead as an observation", "hard-coded Lantana searches"],
    "supports_ops": ["DISCOVER"], "returns": "Evidence leads", "georeferenced": False,
    "binding": {"mode": "evidence_discovery"},
    "instructions": (
        "Pass the complete, query-bound search text as `query`; never replace it with a memorised "
        "example. Internal knowledge may add a candidate term only when you label it as a query "
        "seed. A general source that names the candidate is not enough to connect it to the user's "
        "focal entity or relation. Search candidate + focal entity + relation and promote the "
        "candidate downstream only when one returned source directly contains that connection. "
        "Cite returned DOI/dataset IDs. A returned lead is not an observation.\n\n"
        "```bash\npython3 {skill_call} discover-ecology-evidence "
        "'{\"query\":\"Eucalyptus bird seed dispersal\",\"limit\":8}'\n```"
    ),
}, {
    "id": "relate-taxon-occurrences",
    "description": (
        "Retrieve two named taxa in one admitted region and calculate observation pairs within "
        "a declared distance, retaining both input denominators."
    ),
    "use_for": ["compare whether two taxa have nearby occurrence records",
                "report both occurrence denominators and a distance threshold"],
    "exclude": ["claiming nearby records prove interaction, shared habitat or co-observation",
                "using an unnamed or model-only candidate"],
    "supports_ops": ["SELECT", "RELATE"], "returns": "Related occurrence records",
    "georeferenced": True, "binding": {"mode": "occurrence_relate"},
    "instructions": (
        "Pass two source-backed taxon names, one admitted region and `threshold_km`. Report "
        "`matched_left_count` and `matched_right_count` even when no pair is returned. Nearby "
        "records show spatial proximity only, not shared habitat, interaction or the same time.\n\n"
        "```bash\npython3 {skill_call} relate-taxon-occurrences "
        "'{\"left_entity\":\"Elephas maximus\",\"right_entity\":\"Microcarbo niger\","
        "\"region\":\"donor belt\",\"threshold_km\":5}'\n```"
    ),
}, {
    "id": "inspect-evidence-dataset",
    "description": (
        "Inspect files, headers, sample rows and codebook text for a Zenodo or Dryad dataset "
        "returned by discover-ecology-evidence."
    ),
    "use_for": ["verify what a discovered dataset contains", "derive a source-backed protocol",
                "prepare a datasheet from real columns"],
    "exclude": ["inventing a protocol", "inspecting an unreturned dataset"],
    "supports_ops": ["INSPECT"], "returns": "Dataset material", "georeferenced": False,
    "binding": {"mode": "dataset_inspect"},
    "instructions": (
        "Use the `result_id` returned by discover-ecology-evidence and select a repository dataset "
        "by its DOI. Summarise only returned codebook/headers, and explicitly label adaptations.\n\n"
        "```bash\npython3 {skill_call} inspect-evidence-dataset "
        "'{\"result_id\":\"evidence-...\",\"doi\":\"10....\"}'\n```"
    ),
}, {
    "id": "build-source-backed-field-protocol",
    "description": (
        "Turn an inspected repository dataset into a source-linked field protocol reader and a "
        "blank CSV datasheet with every programme adaptation labelled."
    ),
    "use_for": ["provide a protocol from a returned dataset", "make a printable field datasheet"],
    "exclude": ["inventing a method", "using a discovery lead that was not inspected"],
    "supports_ops": ["PROTOCOL"], "returns": "Protocol artefact", "georeferenced": False,
    "binding": {"mode": "field_protocol"},
    "instructions": (
        "Pass the `result_id` returned by inspect-evidence-dataset and the field `purpose`. The "
        "artefact keeps returned source columns separate from programme-added effort fields. If "
        "the codebook describes multiple files, pass the relevant declared filename as "
        "`source_file`; do not merge unrelated source tables. "
        "Include the returned Open field protocol link.\n\n"
        "```bash\npython3 {skill_call} build-source-backed-field-protocol "
        "'{\"result_id\":\"dataset-...\",\"purpose\":\"test bird contact with Eucalyptus fruits\"}'\n```"
    ),
}, {
    "id": "build-ecology-field-map",
    "description": (
        "Apply independent occurrence and environmental gates, then create an auditable HTML "
        "field map with matching GeoJSON/CSV confirmation points."
    ),
    "use_for": ["map a gated species estimate", "map evidence overlap",
                "give precise field collection points instead of a vague DataRequest"],
    "exclude": ["claiming map overlap proves interaction", "mapping invented coordinates",
                "using an invasive-plant surface for an animal"],
    "supports_ops": ["SELECT", "ESTIMATE", "MAP"], "returns": "Map artefact",
    "georeferenced": True, "binding": {"mode": "field_map"},
    "instructions": (
        "Pass `entities` (one or two named taxa). Use `map_mode: observed` with `source_region` "
        "for a raw occurrence map; that mode never runs an estimate or creates suggested field "
        "points. Use `map_mode: modelled` only when the user has explicitly asked for modelling "
        "or selected that guided action. Add `vegetation_entities` only for invasive or "
        "woody plants eligible for the locked Sentinel-2 plant surface. Each entity is gated "
        "independently. The skill backpedals to observed points or a labelled sampling design when "
        "a surface is unavailable. If one requested partner has no admitted named candidate, pass "
        "only the admitted named taxon and use the returned points as a one-taxon collection "
        "design; do not invent the missing partner or call it overlap. Include the returned "
        "`[Open field map](#map-...)` link.\n\n"
        "```bash\npython3 {skill_call} build-ecology-field-map "
        "'{\"entities\":[\"Eucalyptus globulus\",\"candidate bird\"],"
        "\"vegetation_entities\":[\"Eucalyptus globulus\"],\"region\":\"EBTL\","
        "\"map_mode\":\"modelled\"}'\n```"
    ),
}]


def _load_skills() -> list[dict]:
    with SKILLS_PATH.open(encoding="utf-8") as stream:
        payload = json.load(stream)
    frozen = json.loads(json.dumps(payload.get("skills") or []))
    for skill in frozen:
        if skill.get("id") == "semantic-literature-discovery":
            # Preserve the frozen binding for reproducibility, but make its production scope
            # explicit so an arbitrary Eucalyptus query does not silently become Lantana.
            skill["description"] = (
                "Legacy Lantana-only semantic search over the admitted local card corpus; use "
                "discover-ecology-evidence for every arbitrary or live literature query."
            )
            skill["use_for"] = ["the fixed EBTL Lantana literature benchmark question"]
            skill["exclude"] = ["Eucalyptus", "arbitrary taxa", "live repository discovery",
                                "queries whose entity is not Lantana camara"]
    return frozen + OPERATIONAL_SKILLS


SKILLS = _load_skills()
SKILLS_BY_ID = {item["id"]: item for item in SKILLS}
MODEL_REQUESTS_PATH = STATE_ROOT / "model_requests.jsonl"
_MODEL_REQUESTS_LOCK = threading.Lock()

PLANNER_SKILL_ARGUMENTS = {
    "site-overview": {"site_id": "declared site id or alias"},
    "local-site-evidence-search": {
        "query": "focal entity or topic", "region": "declared site"},
    "local-site-fauna-summary": {"region": "declared site"},
    "local-snake-inventory": {"region": "declared site"},
    "local-bird-inventory": {"region": "declared site"},
    "local-invasive-management-evidence": {"region": "declared site"},
    "merged-taxon-occurrence-search": {
        "entity": "named taxon", "region": "site or declared donor region"},
    "discover-ecology-evidence": {
        "query": "complete query-bound search",
        "query_variants": (
            "optional list of up to 3 additional complete searches; related taxa from model "
            "background are untrusted query seeds, not evidence"),
        "region": "optional declared site whose onboarded discovery context bounds the variants",
        "limit": "1 to 20"},
    "relate-taxon-occurrences": {
        "left_entity": "named taxon", "right_entity": "named taxon",
        "region": "declared region", "threshold_km": "positive distance"},
    "inspect-evidence-dataset": {
        "result_id": "prior discovery handle", "doi": "returned DOI"},
    "build-source-backed-field-protocol": {
        "result_id": "prior inspected-dataset handle", "purpose": "field purpose",
        "source_file": "one declared source table when required"},
    "gated-species-presence-transfer": {
        "entity": "source-backed named taxon", "donor_region": "declared donor region",
        "target": "declared target site"},
    "build-ecology-field-map": {
        "entities": "one or two source-backed named taxa", "region": "declared target site",
        "source_region": "region holding observed points",
        "map_mode": "observed or modelled"},
    "vegetation-greenness-trend": {"region": "declared site"},
    "historical-fire-exposure": {"region": "declared site"},
    "published-vegetation-survey-sites": {"region": "declared site or context region"},
    "local-bird-lantana-overlap": {"region": "declared site"},
}
PLANNER_FORBIDDEN_SKILLS = {
    "plan-data-with-algebra-9b", "request-model-from-t4gc", "publish-report",
    # This frozen skill is intentionally tied to one old Lantana benchmark query.
    "semantic-literature-discovery",
}


def _bind_context(ir: dict | None) -> dict | None:
    return IR.canonicalize(E._bind_context(json.loads(json.dumps(ir)), "ebtl")) if ir else None


def _normalise_region_name(value: object) -> str:
    name = " ".join(str(value or "EBTL").split())
    aliases = {
        "donor belt": "dry-Deccan donor belt",
        "dry deccan donor belt": "dry-Deccan donor belt",
        "dry-deccan donor belt": "dry-Deccan donor belt",
    }
    return aliases.get(name.casefold(), name)


def _load_site_profile() -> dict:
    try:
        value = json.loads(SITE_PROFILE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        value = {}
    return value if isinstance(value, dict) else {}


def _site_overview(args: dict, session: "Session | None") -> dict:
    """Compile the onboarded site resources into one labelled runtime snapshot."""
    site_id = " ".join(str(args.get("site_id") or args.get("region") or "EBTL").split())
    try:
        region = C.resolve_region(site_id)
    except Exception as exc:
        return {
            "status": "data_request", "reason": "unknown_site",
            "detail": {"site_id": site_id, "error": f"{type(exc).__name__}: {exc}"},
            "provenance": [],
        }
    profile = _load_site_profile()
    profile_site = str(profile.get("site") or region.get("name") or site_id)
    description = str(profile.get("where") or "").strip()
    bbox = profile.get("site_bbox_wsen")
    if not isinstance(bbox, list) or len(bbox) != 4:
        south, north, west, east = region["bbox"]
        bbox = [west, south, east, north]
    centre = profile.get("site_center_latlon")
    if not isinstance(centre, dict):
        centre = {"lat": region.get("lat"), "lon": region.get("lon")}

    rows: list[dict] = [{
        "id": "site-profile:identity",
        "section": "identity",
        "finding": profile_site,
        "detail": description or "No narrative site description is registered.",
        "evidence_label": "declared profile",
        "source": "Onboarded organisation profile",
        "source_record": SITE_PROFILE_PATH.name,
    }, {
        "id": "site-profile:geometry",
        "section": "geometry",
        "finding": "A site analysis boundary and centre are registered.",
        "bbox_wsen": bbox,
        "centre": centre,
        "detail": str(profile.get("site_bbox_note") or
                      "Registered analysis geometry; verify whether this is the legal parcel."),
        "evidence_label": "declared geometry",
        "source": "Onboarded organisation profile",
        "source_record": SITE_PROFILE_PATH.name,
    }]

    summary = C.published_site_evidence(
        {"kind": "published_site_evidence", "canonical": "evidence_summary",
         "input": site_id}, region, None)
    for item in (summary or {}).get("rows") or []:
        if not isinstance(item, dict):
            continue
        rows.append({
            "id": str(item.get("id") or f"site-summary:{len(rows)}"),
            "section": "local evidence",
            "topic": item.get("topic"),
            "finding": item.get("finding"),
            "evidence_label": item.get("label") or "reported",
            "source": (summary or {}).get("source") or "Imported local evidence",
        })

    partitions = [
        ("wildlife_inventory", "wildlife survey groups"),
        ("bird_inventory", "bird inventory"),
        ("snake_habitat_requirements", "snake inventory and habitat fields"),
        ("elephant_evidence", "elephant passage evidence"),
        ("nursery_inventory", "nursery records"),
        ("soil_evidence", "soil and drought evidence"),
    ]
    partition_rows = []
    for key, label in partitions:
        with contextlib.suppress(Exception):
            result = C.published_site_evidence(
                {"kind": "published_site_evidence", "canonical": key,
                 "input": site_id}, region, None)
            if result:
                partition_rows.append({
                    "partition": key, "label": label,
                    "records": len(result.get("rows") or []),
                    "evidence_label": result.get("label") or "reported",
                    "source": result.get("source"),
                })
    rows.append({
        "id": "site-profile:resource-census",
        "section": "resource census",
        "finding": f"{len(partition_rows)} local evidence partitions are registered.",
        "partitions": partition_rows,
        "evidence_label": "computed inventory",
        "source": "Idli Insight site-profile compiler",
    })

    geometry_files = []
    if session is not None:
        geometry_files = [
            item.get("name") for item in session.attachments
            if str(item.get("name") or "").lower().endswith((
                ".kml", ".kmz", ".geojson", ".json", ".gpkg", ".shp"))
        ]
    if geometry_files:
        rows.append({
            "id": "site-profile:uploaded-geometry",
            "section": "geometry",
            "finding": f"{len(geometry_files)} uploaded geometry asset(s) are available.",
            "assets": geometry_files,
            "evidence_label": "user-provided asset",
            "source": "Current Idlisseus session",
        })
    else:
        rows.append({
            "id": "site-profile:geometry-gap",
            "section": "gap",
            "finding": (
                "No property KML, GeoJSON or other parcel file is registered in this session; "
                "the configured analysis bbox must not be presented as a legal property boundary."
            ),
            "evidence_label": "data gap",
            "source": "Idli Insight site-profile compiler",
        })

    capability_ids = [
        skill_id for skill_id in (
            "vegetation-greenness-trend", "historical-fire-exposure",
            "merged-taxon-occurrence-search", "gated-species-presence-transfer",
            "build-ecology-field-map", "discover-ecology-evidence")
        if skill_id in SKILLS_BY_ID
    ]
    rows.append({
        "id": "site-profile:capabilities",
        "section": "configured capabilities",
        "finding": "Data and modelling operations currently available for this site.",
        "skills": capability_ids,
        "evidence_label": "runtime capability",
        "source": "Idli Insight capability registry",
    })
    value = {
        "kind": "records", "rows": rows,
        "source": "Onboarded profile + imported local evidence + capability registry",
        "label": "mixed", "site_id": site_id,
        "region": region, "partitions": partition_rows,
        "note": (
            "Runtime site snapshot. Declared profile facts, local evidence, capabilities and "
            "gaps remain separately labelled; no web result or model-memory claim is included."
        ),
    }
    if session is not None:
        value["result_id"] = session.store_result("site_overview", value)
    return {
        "status": "answer", "label": "mixed", "value": value,
        "provenance": [{
            "op": "SITE_PROFILE", "site_id": site_id,
            "profile": SITE_PROFILE_PATH.name,
            "partitions": [item["partition"] for item in partition_rows],
        }],
    }


def _extract_first_json_object(text: str) -> dict | None:
    decoder = json.JSONDecoder()
    for index, character in enumerate(str(text or "")):
        if character != "{":
            continue
        with contextlib.suppress(json.JSONDecodeError):
            value, _ = decoder.raw_decode(text[index:])
            if isinstance(value, dict):
                return value
    return None


def _planner_catalog(session: "Session") -> list[dict]:
    allowed = set(SKILLS_BY_ID) - PLANNER_FORBIDDEN_SKILLS
    if session.guided_allowed_skills is not None:
        allowed &= set(session.guided_allowed_skills)
    catalog = []
    for skill_id in sorted(allowed):
        skill = SKILLS_BY_ID[skill_id]
        catalog.append({
            "id": skill_id,
            "description": skill.get("description"),
            "arguments": PLANNER_SKILL_ARGUMENTS.get(skill_id, {
                "entity": "named entity when required", "region": "declared site or region"}),
        })
    return catalog


def _map_intent(question: object) -> str | None:
    """Return the requested map mode without inferring a map from a generic ecology question."""
    text = _normalise_match_text(question)
    if not text:
        return None
    asks_for_map = bool(re.search(
        r"\b(map|mapped|mapping|waypoints?|field points?|sampling points?|"
        r"(?:raw |observed )?(?:occurrence|observation) points?|"
        r"where (?:should|can|could|would) (?:we|i) (?:collect|sample|survey|check))\b",
        text,
    ) or re.search(
        r"\bwhere (?:on|within|inside) (?:the |this |our )?"
        r"(?:site|property|aoi)\b", text,
    ) or re.search(
        r"\b(?:build|create|make|produce|run|give|show|model) .{0,40}"
        r"(?:distribution|habitat suitability|site screening|screening suitability)\b", text,
    ) or re.search(
        r"\bwhere .{0,80}\b(?:expect|find|collect|sample|survey|check)\b"
        r".{0,80}\bdata\b", text,
    ) or re.search(
        r"\bdata\b.{0,80}\bwhere .{0,60}\b(?:collect|sample|survey|check)\b", text,
    ))
    if not asks_for_map:
        return None
    if re.search(
            r"\b(raw|observed|observation|occurrence|recorded) "
            r"(?:data )?(?:points?|records?)\b", text) or re.search(
                r"\bwhere .{0,40}\b(?:observed|recorded|seen|sighted)\b", text):
        return "observed"
    return "modelled"


def _clean_plan_args(value: Any, depth: int = 0) -> Any:
    if depth > 4:
        raise ValueError("plan arguments are too deeply nested")
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return " ".join(value.split())[:1000]
    if isinstance(value, list):
        return [_clean_plan_args(item, depth + 1) for item in value[:12]]
    if isinstance(value, dict):
        cleaned = {}
        for key, item in list(value.items())[:24]:
            safe_key = str(key)[:80]
            if safe_key.casefold() in {
                "token", "api_key", "authorization", "command", "path", "shell"}:
                raise ValueError(f"forbidden plan argument: {safe_key}")
            cleaned[safe_key] = _clean_plan_args(item, depth + 1)
        return cleaned
    raise ValueError(f"unsupported plan argument type: {type(value).__name__}")


def _validate_algebra_plan(raw: dict, catalog: list[dict],
                           required_map_mode: str | None = None) -> dict:
    allowed = {item["id"] for item in catalog}
    raw_steps = raw.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ValueError("planner must return a non-empty steps array")
    # Some small planners pad a fixed-size array with a completely empty object. Discard only
    # that inert suffix; a populated unknown or malformed step must still fail closed below.
    raw_steps = [
        item for item in raw_steps
        if not (isinstance(item, dict) and not item.get("skill")
                and not item.get("args") and not item.get("purpose"))
    ]
    if not raw_steps:
        raise ValueError("planner returned only empty steps")
    steps = []
    for index, item in enumerate(raw_steps[:MAX_ALGEBRA_PLAN_STEPS], 1):
        if not isinstance(item, dict):
            raise ValueError(f"plan step {index} must be an object")
        skill_id = str(item.get("skill") or "").strip()
        if skill_id not in allowed:
            raise ValueError(f"plan step {index} uses unavailable skill: {skill_id}")
        args = item.get("args") if isinstance(item.get("args"), dict) else {}
        if skill_id == "build-ecology-field-map" and isinstance(args.get("entities"), str):
            args = dict(args)
            args["entities"] = [args["entities"]]
        steps.append({
            "step_id": f"step-{index}",
            "skill": skill_id,
            "args": _clean_plan_args(args),
            "purpose": " ".join(str(item.get("purpose") or "").split())[:300],
            "status": "pending",
        })
    if required_map_mode:
        map_steps = [step for step in steps if step["skill"] == "build-ecology-field-map"]
        if not map_steps:
            raise ValueError(
                "explicit map request requires build-ecology-field-map as the final step")
        if len(steps) != 1 or steps[0]["skill"] != "build-ecology-field-map":
            raise ValueError(
                "explicit map request must use the self-contained build-ecology-field-map step")
        planned_mode = str(map_steps[-1]["args"].get("map_mode") or "").casefold()
        if planned_mode != required_map_mode:
            raise ValueError(
                f"explicit map request requires map_mode={required_map_mode}")
        entities = map_steps[-1]["args"].get("entities")
        if not isinstance(entities, list) or not any(str(item).strip() for item in entities):
            raise ValueError("explicit map request requires at least one focal entity")
    update = " ".join(str(raw.get("user_update") or "").split())[:300]
    if not update:
        update = "I have a data plan and will run its audited steps now."
    return {
        "status": "plan", "user_update": update, "steps": steps,
        "success_criteria": [
            " ".join(str(item).split())[:240]
            for item in (raw.get("success_criteria") or [])[:6]
            if str(item).strip()
        ],
    }


def _call_algebra_9b(prompt: str) -> dict:
    payload = {
        "model": ALGEBRA_9B_MODEL, "temperature": 0, "max_tokens": 1600,
        "messages": [
            {"role": "system", "content": (
                "You are Algebra 9B-004d acting only as a typed ecology skill planner. "
                "Return one complete JSON object and no prose. Do not answer the ecology "
                "question. Do not invent skill ids, data, result handles, taxa or coordinates.")},
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        ALGEBRA_9B_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=ALGEBRA_9B_TIMEOUT) as response:
        body = json.load(response)
    text = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    parsed = _extract_first_json_object(text)
    if parsed is None:
        raise ValueError("Algebra 9B did not return a JSON plan")
    return {"parsed": parsed, "raw": str(text)[:6000], "usage": body.get("usage") or {}}


def _plan_with_algebra_9b(args: dict, session: "Session") -> dict:
    if session.algebra_planner_calls >= MAX_ALGEBRA_PASSES:
        return {
            "status": "data_request", "reason": "planner_pass_limit",
            "detail": {"max_passes": MAX_ALGEBRA_PASSES,
                       "ask": "ask the user to narrow the next data step"},
            "provenance": [],
        }
    catalog = _planner_catalog(session)
    if not catalog:
        return {
            "status": "data_request", "reason": "no_authorized_data_skills",
            "detail": {"ask": "the selected action has no permitted data capability"},
            "provenance": [],
        }
    session.algebra_planner_calls += 1
    pass_number = session.algebra_planner_calls
    feedback = session.algebra_plan_feedback()
    required_map_mode = _map_intent(session.current_data_question)
    prior_data_request = any(
        step.get("execution_status") == "data_request"
        for prior_plan in feedback for step in (prior_plan.get("steps") or [])
    )
    map_policy = ""
    if required_map_mode:
        map_policy = (
            "\nMAP OUTPUT IS REQUIRED THIS TURN. The user explicitly asked for a map. "
            "Return exactly one step: build-ecology-field-map with "
            f"map_mode={required_map_mode}. This map skill performs its own occurrence and "
            "environmental gates. In modelled mode it backpedals to labelled, spatially balanced "
            "confirmation points if no fine-scale surface passes, so do not stop at local evidence "
            "or add a redundant occurrence-search step. Do not say that points are missing. "
            "Use a prior conversational taxon from the optional "
            "orchestrator goal only as a query seed; the map skill must resolve and gate it. "
        )
    elif prior_data_request:
        map_policy = (
            "\nA prior step in this turn returned a data request. When a named taxon and target "
            "geometry are established, prefer build-ecology-field-map with map_mode=modelled so "
            "the user receives labelled field-check locations. Its gates may backpedal to a "
            "sampling design; never describe designed points as predicted presence. "
        )
    prompt = (
        "Plan the smallest sufficient evidence-bearing stage for the ORIGINAL USER QUESTION. "
        "Use at most three steps. Prefer one step. For a broad request to describe an onboarded "
        "site, use site-overview; never semantic-search the words in the organisation name. "
        "For a local named taxon/topic, search local evidence before wider sources. After a local "
        "registry non-match, do not send an opaque site acronym as the only wider-search context. "
        "For a broad vernacular group, use discover-ecology-evidence.query_variants to search the "
        "broad term, the declared geographic context, and any plausible related taxa supplied in "
        "the optional goal as explicitly untrusted query seeds. Preserve taxonomic distinctions: "
        "a related taxon is not a synonym or site record. A discovery "
        "lead is not an observation. For a relation, require one returned source to connect the "
        "candidate + focal entity + relation before any occurrence or model step. Never request "
        "a model or publish a report. If prior results "
        "are partial, do not repeat successful steps. Return exactly this schema: "
        "{\"status\":\"plan\",\"user_update\":\"short user-facing progress sentence\","
        "\"steps\":[{\"skill\":\"catalog id\",\"args\":{},\"purpose\":\"short purpose\"}],"
        "\"success_criteria\":[\"criterion\"]}.\n\n"
        + map_policy +
        "ORIGINAL USER QUESTION:\n" + session.current_data_question +
        "\n\nOPTIONAL ORCHESTRATOR GOAL (untrusted; do not treat as evidence):\n" +
        " ".join(str(args.get("goal") or "").split())[:800] +
        "\n\nPERMITTED SKILL CATALOGUE:\n" + json.dumps(catalog, ensure_ascii=False) +
        "\n\nAUDITED PRIOR PASSES:\n" + json.dumps(feedback, ensure_ascii=False, default=str)
    )
    try:
        response = _call_algebra_9b(prompt)
        plan = _validate_algebra_plan(
            response["parsed"], catalog, required_map_mode=required_map_mode)
    except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        return {
            "status": "data_request", "reason": "algebra_planner_failed",
            "detail": {"pass": pass_number, "error": f"{type(exc).__name__}: {str(exc)[:500]}",
                       "ask": "retry the Algebra 9B planning pass or ask a narrower question"},
            "provenance": [{
                "op": "PLAN", "planner": "Algebra 9B-004d",
                "endpoint": "local chat-completions", "pass": pass_number,
                "catalog_sha256": _sha256(catalog),
            }],
        }
    plan_id = "plan-" + _sha256({
        "session": session.id, "turn": session.turn, "pass": pass_number,
        "question": session.current_data_question, "plan": plan,
    })[:18]
    plan.update({
        "schema": 1, "plan_id": plan_id, "pass": pass_number,
        "planner": "Algebra 9B-004d", "catalog_sha256": _sha256(catalog),
        "usage": response.get("usage") or {},
    })
    session.register_algebra_plan(plan)
    value = {
        "kind": "records", "rows": [{
            "plan_id": plan_id, "pass": pass_number,
            "user_update": plan["user_update"],
            "steps": [{key: step[key] for key in ("step_id", "skill", "purpose")}
                      for step in plan["steps"]],
        }],
        "source": "Local Algebra 9B-004d planner", "label": "designed",
        "note": (
            "The planner selected a bounded skill sequence only. No connector was executed and "
            "no scientific claim was produced by this planning call."
        ),
    }
    return {
        "status": "answer", "label": "designed", "value": value,
        "provenance": [{
            "op": "PLAN", "planner": "Algebra 9B-004d", "pass": pass_number,
            "plan_id": plan_id, "catalog_sha256": plan["catalog_sha256"],
        }],
    }


def _skill_ir(skill: dict, args: dict) -> dict:
    binding = skill.get("binding") or {}
    region_value = _normalise_region_name(
        binding.get("region_place") or args.get("region") or "EBTL")
    region: dict = {"op": "REGION", "place": region_value}
    if args.get("radius_km") and binding.get("mode") == "compiler_entity":
        region = {"op": "BUFFER", "radius_km": float(args["radius_km"]), "source": region}
    time_value = args.get("time")
    if binding.get("mode") == "exact_select":
        return {"op": "SELECT", "entity": binding["entity"], "region": region,
                "time": time_value}
    if binding.get("mode") == "compiler_entity":
        entity = str(args.get("entity") or args.get("taxon") or "?taxon")
        for alias, canonical in (skill.get("aliases") or {}).items():
            if alias in entity.lower():
                entity = canonical
                break
        return {"op": "SELECT", "entity": entity, "region": region, "time": time_value}
    if binding.get("mode") == "annotate":
        return {
            "op": "ANNOTATE", "layer": binding["layer"],
            "source": {"op": "SELECT", "entity": binding["source_entity"],
                       "region": region, "time": time_value},
        }
    if binding.get("mode") == "operator" and binding.get("op") == "ESTIMATE":
        entity = str(args.get("entity") or args.get("taxon") or "?taxon")
        for alias, canonical in (skill.get("aliases") or {}).items():
            if alias in entity.lower():
                entity = canonical
                break
        donor = {"op": "REGION", "place": args.get("donor_region") or "dry-Deccan donor belt"}
        return {
            "op": "ESTIMATE", "method": args.get("method") or "feature",
            "source": {"op": "SELECT", "entity": entity, "region": donor, "time": None},
            "target": {"op": "REGION", "place": args.get("target") or "EBTL"},
        }
    raise ValueError("skill has no executable binding")


def _occurrence_relate_ir(args: dict) -> dict:
    left = " ".join(str(args.get("left_entity") or args.get("left") or "").split())
    right = " ".join(str(args.get("right_entity") or args.get("right") or "").split())
    if not left or not right:
        raise ValueError("left_entity and right_entity are required")
    threshold = float(args.get("threshold_km") or 5.0)
    if not 0 < threshold <= 500:
        raise ValueError("threshold_km must be greater than 0 and at most 500")
    region = {"op": "REGION", "place": _normalise_region_name(args.get("region") or "EBTL")}
    return {
        "op": "RELATE", "relation": "within", "threshold_km": threshold,
        "left": {"op": "SELECT", "entity": left, "region": region, "time": args.get("time")},
        "right": {"op": "SELECT", "entity": right, "region": region, "time": args.get("time")},
    }


def _record_model_request(args: dict, session: "Session | None" = None) -> dict:
    request_text = str(args.get("request") or args.get("model") or "").strip()
    if not request_text:
        return {"status": "data_request", "reason": "missing_request",
                "detail": {"ask": "describe the model or predictor being requested"},
                "provenance": []}
    request_text = request_text[:2000]
    region = str(args.get("region") or "")[:240]
    reason = str(args.get("reason") or args.get("evidence_gap") or "")[:2000]
    response_variable = str(args.get("response_variable") or args.get("response") or "")[:500]
    labels = str(args.get("labels") or args.get("ground_truth") or "")[:1200]
    spatial_extent = str(args.get("spatial_extent") or region)[:500]
    validation_target = str(args.get("validation_target") or args.get("validation") or "")[:1200]
    predictors_value = args.get("predictors") or []
    if isinstance(predictors_value, str):
        predictors = [item.strip() for item in predictors_value.split(",") if item.strip()]
    elif isinstance(predictors_value, list):
        predictors = [str(item).strip()[:240] for item in predictors_value if str(item).strip()]
    else:
        predictors = []
    predictors = predictors[:24]
    audit_id = f"{session.id}/{session.turn}" if session else ""
    digest = hashlib.sha256(f"{audit_id}\n{request_text}\n{region}".encode()).hexdigest()[:12]
    request_id = f"t4gc-{digest}"
    record = {
        "id": request_id, "status": "requested", "request": request_text,
        "region": region, "reason": reason, "audit_id": audit_id,
        "response_variable": response_variable, "predictors": predictors,
        "labels": labels, "spatial_extent": spatial_extent,
        "validation_target": validation_target,
        "session_id": session.id if session else "", "turn": session.turn if session else None,
        "owner": session.owner if session else "", "created_at": dt.datetime.now().isoformat(),
    }
    MODEL_REQUESTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _MODEL_REQUESTS_LOCK:
        existing = ""
        with contextlib.suppress(OSError):
            existing = MODEL_REQUESTS_PATH.read_text(encoding="utf-8")
        known_request_ids = set()
        for line in existing.splitlines():
            with contextlib.suppress(json.JSONDecodeError, AttributeError):
                known_request_ids.add(json.loads(line).get("id"))
        if request_id not in known_request_ids:
            with MODEL_REQUESTS_PATH.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            os.chmod(MODEL_REQUESTS_PATH, 0o600)
    return {
        "status": "answer", "label": "reported",
        "value": {"kind": "records", "rows": [{
            "request_id": request_id, "status": "requested", "request": request_text,
            "region": region, "audit_id": audit_id,
            "response_variable": response_variable, "predictors": predictors,
            "labels": labels, "spatial_extent": spatial_extent,
            "validation_target": validation_target,
        }], "source": "T4GC model request queue", "label": "reported",
                  "note": f"Recorded model request {request_id} for T4GC review."},
        "provenance": [{"op": "REQUEST_MODEL", "request_id": request_id,
                        "queue": "local:t4gc-model-requests"}],
    }


def _publish_html_document(session: "Session", title: str, content: str,
                           link_kind: str = "map", label: str = "Open field map") -> dict:
    """Publish a self-contained HTML artefact into Idlisseus's existing document side panel."""
    if str(IDLISSEUS_ROOT) not in sys.path:
        sys.path.insert(0, str(IDLISSEUS_ROOT))
    from core.database import (Document, DocumentVersion, Session as DbSession,
                               SessionLocal)  # type: ignore

    digest = _sha256({"session": session.id, "turn": session.turn, "content": content})[:20]
    document_id = f"idli-map-{digest}"
    db = SessionLocal()
    try:
        existing = db.query(Document).filter(Document.id == document_id).first()
        if existing is None:
            chat_session = db.query(DbSession).filter(DbSession.id == session.id).first()
            linked_session = chat_session.id if chat_session is not None else None
            owner = session.owner or (chat_session.owner if chat_session is not None else None)
            db.add(Document(
                id=document_id, session_id=linked_session, title=title, language="html",
                current_content=content, version_count=1, is_active=True, owner=owner,
            ))
            db.add(DocumentVersion(
                id=str(uuid.uuid4()), document_id=document_id, version_number=1,
                content=content, summary="Audited ecology field map", source="ai",
            ))
            db.commit()
        return {"document_id": document_id, "url": f"#{_safe_id(link_kind)}-{document_id}",
                "label": label}
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _call_algebra_9b_messages(messages: list[dict]) -> dict:
    """Run the Algebra-trained 9B against its native frozen-IR output contract."""
    payload = {
        "model": ALGEBRA_9B_MODEL, "temperature": 0, "max_tokens": 2600,
        "messages": messages,
    }
    request = urllib.request.Request(
        ALGEBRA_9B_URL, data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=ALGEBRA_9B_TIMEOUT) as response:
        body = json.load(response)
    text = (((body.get("choices") or [{}])[0].get("message") or {}).get("content") or "")
    ir = E.P.extract_json(str(text))
    if not isinstance(ir, dict):
        raise ValueError("Algebra 9B did not return one JSON expression tree")
    return {"ir": ir, "raw": str(text)[:12000], "usage": body.get("usage") or {}}


def _manifest_entity_candidates(value: Any) -> list[tuple[str, str]]:
    """Extract taxon/entity symbols only from typed connector fields, never paper titles."""
    found: list[tuple[str, str]] = []
    if isinstance(value, list):
        for item in value[:500]:
            found.extend(_manifest_entity_candidates(item))
        return found
    if not isinstance(value, dict):
        return found
    for key in (
        "scientific_name", "common_name", "canonical", "resolved_entity",
        "donor_entity", "left_entity", "right_entity", "taxon",
    ):
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate.strip():
            found.append((" ".join(candidate.split())[:240], key))
    resolution = value.get("resolution")
    if isinstance(resolution, dict):
        candidate = resolution.get("canonical")
        if isinstance(candidate, str) and candidate.strip():
            found.append((" ".join(candidate.split())[:240], "resolution.canonical"))
    for key in ("rows", "estimates", "value", "payload", "execution", "result"):
        if key in value:
            found.extend(_manifest_entity_candidates(value[key]))
    return found


def _scientific_resource_manifest(session: "Session") -> dict:
    """Build the code-owned symbol table supplied to Algebra 9B and its binder."""
    profile = _load_site_profile()
    regions: dict[str, dict] = {}

    def add_region(symbol: object, source: str) -> None:
        name = " ".join(str(symbol or "").split()).strip()
        if not name:
            return
        with contextlib.suppress(Exception):
            resolved = C.resolve_region(_normalise_region_name(name))
            symbol = _normalise_region_name(name)
            regions[symbol.casefold()] = {
                "symbol": symbol, "input": name,
                "resolved_name": str(resolved.get("name") or symbol), "source": source,
                "geometry_source": resolved.get("source"),
                "bbox": resolved.get("bbox"),
            }

    add_region("EBTL", f"organisation profile:{SITE_PROFILE_PATH.name}")
    add_region("dry-Deccan donor belt", f"organisation profile:{SITE_PROFILE_PATH.name}")
    for call in session.turn_skill_calls[-20:]:
        for key in ("region", "source_region", "donor_region", "target", "target_region"):
            add_region((call.get("args") or {}).get(key), f"audited skill:{call.get('skill')}")

    entities: dict[str, dict] = {}
    entity_resolution_cache: dict[str, dict | None] = {}

    def add_entity(symbol: object, source: str, field: str) -> None:
        name = " ".join(str(symbol or "").split()).strip()
        if not name:
            return
        key = name.casefold()
        if key in entity_resolution_cache:
            resolution = entity_resolution_cache[key]
        else:
            resolution = None
            with contextlib.suppress(Exception):
                resolution = C.resolve_ecology_entity(name)
            entity_resolution_cache[key] = resolution
        if not isinstance(resolution, dict) or resolution.get("kind") in {
            "ambiguous", "unverified_taxon", "unsupported_measure",
        }:
            return
        canonical = str(resolution.get("canonical") or name)
        entities[canonical.casefold()] = {
            "symbol": canonical, "input": name, "kind": resolution.get("kind"),
            "source": source, "source_field": field,
        }

    result_summaries = []
    result_paths = sorted(
        session.results.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True
    )[:24]
    for path in result_paths:
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError):
            continue
        if stored.get("session_id") != session.id:
            continue
        payload = stored.get("payload") if isinstance(stored.get("payload"), dict) else {}
        for candidate, field in _manifest_entity_candidates(payload):
            add_entity(candidate, f"audited result:{stored.get('result_id')}", field)
        rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        result_summaries.append({
            "result_id": stored.get("result_id"), "kind": stored.get("kind"),
            "label": payload.get("label"), "source": payload.get("source"),
            "row_count": len(rows), "region": (
                (payload.get("region") or {}).get("name")
                if isinstance(payload.get("region"), dict) else payload.get("region")),
        })
    for call in session.turn_skill_calls[-20:]:
        result = call.get("result") if isinstance(call.get("result"), dict) else {}
        for candidate, field in _manifest_entity_candidates(result):
            add_entity(candidate, f"audited skill:{call.get('skill')}", field)
        args = call.get("args") if isinstance(call.get("args"), dict) else {}
        for key in ("entity", "left_entity", "right_entity"):
            if args.get(key):
                add_entity(args[key], f"audited skill argument:{call.get('skill')}", key)
        for item in args.get("entities") or []:
            add_entity(item, f"audited skill argument:{call.get('skill')}", "entities")

    # Exact connector entities and raster layers are registered capabilities, not observations.
    capabilities = C.capability_catalog()
    layers = [{
        "symbol": item["entity"], "source_entity": item.get("source_entity"),
        "grain": item.get("grain"), "evidence": item.get("evidence"),
    } for item in capabilities if str(item.get("kind") or "").startswith("ANNOTATE")]
    capability_entities = [{
        "symbol": item["entity"], "kind": item.get("kind"),
        "description": item.get("description"), "binding": item.get("binding"),
    } for item in capabilities if item.get("entity")]
    return {
        "site": {
            "name": profile.get("site"), "description": profile.get("where"),
            "profile": SITE_PROFILE_PATH.name,
        },
        "regions": list(regions.values()),
        "entities": list(entities.values()),
        "layers": layers,
        "capabilities": capability_entities,
        "audited_results": result_summaries[:12],
    }


def _iter_ir_nodes(value: Any) -> Iterator[dict]:
    if isinstance(value, dict):
        if value.get("op"):
            yield value
        for item in value.values():
            yield from _iter_ir_nodes(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_ir_nodes(item)


def _bind_scientific_symbols(ir: dict, manifest: dict) -> tuple[dict, list[dict]]:
    """Canonicalise harmless 9B surface forms only when they match an admitted symbol."""
    bound = json.loads(json.dumps(ir))
    bindings: list[dict] = []
    entity_aliases: dict[str, str] = {}
    for item in manifest.get("entities") or []:
        canonical = str(item.get("symbol") or "").strip()
        if not canonical:
            continue
        for alias in (canonical, item.get("input")):
            key = _normalise_match_text(alias)
            if key:
                entity_aliases[key] = canonical
    region_aliases: dict[str, str] = {}
    for item in manifest.get("regions") or []:
        canonical = str(item.get("symbol") or "").strip()
        if not canonical:
            continue
        for alias in (canonical, item.get("input"), item.get("resolved_name")):
            key = _normalise_match_text(alias)
            if key:
                region_aliases[key] = canonical
    for alias in ("EBTL", "Elephants by the Lake"):
        key = _normalise_match_text(alias)
        if key:
            region_aliases.setdefault(
                key, next((
                    str(item.get("symbol")) for item in manifest.get("regions") or []
                    if "elephants by the lake" in _normalise_match_text(
                        item.get("resolved_name") or item.get("symbol"))
                ), alias))

    def bind_entity(value: object) -> object:
        if not isinstance(value, str) or value.startswith("?"):
            return value
        key = _normalise_match_text(value)
        canonical = entity_aliases.get(key)
        if canonical is None:
            # The trained compiler sometimes appends a source-kind label to the copied taxon.
            # Strip only this small, non-scientific suffix set and only accept an exact admitted
            # match after stripping. Population/abundance/occupancy terms remain untouched.
            core = re.sub(
                r"\s+(?:(?:taxon\s+)?occurrence\s+records?|"
                r"occurrences?|observations?|records?)$", "", key,
            ).strip()
            canonical = entity_aliases.get(core)
        if canonical and canonical != value:
            bindings.append({
                "kind": "entity", "model_text": value, "bound_symbol": canonical,
                "rule": "exact admitted symbol or admitted symbol plus record-kind suffix",
            })
            return canonical
        return value

    for node in _iter_ir_nodes(bound):
        if node.get("op") == "SELECT":
            entity = node.get("entity")
            if isinstance(entity, list):
                node["entity"] = [bind_entity(item) for item in entity]
            else:
                node["entity"] = bind_entity(entity)
        elif node.get("op") == "REGION":
            value = node.get("place")
            if isinstance(value, str) and not value.startswith("?"):
                canonical = region_aliases.get(_normalise_match_text(value))
                if canonical and canonical != value:
                    bindings.append({
                        "kind": "region", "model_text": value, "bound_symbol": canonical,
                        "rule": "exact admitted region alias",
                    })
                    node["place"] = canonical
    return bound, bindings


def _validate_scientific_symbols(ir: dict, manifest: dict,
                                 original_question: str) -> list[str]:
    """Reject model-authored scientific symbols not admitted by resources or the user."""
    allowed_entities = {
        _normalise_match_text(item.get("symbol"))
        for item in (manifest.get("entities") or []) + (manifest.get("capabilities") or [])
        if item.get("symbol")
    }
    allowed_regions = {
        _normalise_match_text(item.get("symbol"))
        for item in manifest.get("regions") or [] if item.get("symbol")
    }
    allowed_regions.update({"ebtl", "elephants by the lake", "dry deccan donor belt"})
    allowed_layers = {
        _normalise_match_text(item.get("symbol"))
        for item in manifest.get("layers") or [] if item.get("symbol")
    }
    original = _normalise_match_text(original_question)
    errors = []
    for node in _iter_ir_nodes(ir):
        op = node.get("op")
        if op == "SELECT":
            raw_entities = node.get("entity")
            values = raw_entities if isinstance(raw_entities, list) else [raw_entities]
            for value in values:
                if not isinstance(value, str) or value.startswith("?"):
                    continue
                key = _normalise_match_text(value)
                user_named = bool(key and key in original)
                if key not in allowed_entities and not user_named:
                    errors.append(
                        f"SELECT entity {value!r} was not user-named or admitted by a resource")
        elif op == "REGION":
            value = node.get("place")
            if not isinstance(value, str) or value.startswith("?"):
                continue
            key = _normalise_match_text(value)
            user_named = bool(key and key in original)
            if key not in allowed_regions and not user_named:
                errors.append(
                    f"REGION {value!r} was not user-named or admitted by the organisation profile")
        elif op == "ANNOTATE":
            value = node.get("layer")
            if isinstance(value, str) and not value.startswith("?"):
                if _normalise_match_text(value) not in allowed_layers:
                    errors.append(f"ANNOTATE layer {value!r} is not a registered layer")
    return errors


def _format_ir_human(ir: dict) -> str:
    op = str(ir.get("op") or "unknown")
    if op == "REGION":
        return str(ir.get("place") or "unspecified region")
    if op == "SELECT":
        entity = ir.get("entity")
        region = ir.get("region")
        where = _format_ir_human(region) if isinstance(region, dict) else str(region)
        return f"Select {entity!r} records in {where}"
    if op == "ESTIMATE":
        return (
            f"Estimate at {_format_ir_human(ir.get('target') or {})} from "
            f"{_format_ir_human(ir.get('source') or {})} using the {ir.get('method')} gate"
        )
    if op == "RELATE":
        threshold = (
            f" within {ir.get('threshold_km')} km" if ir.get("threshold_km") is not None else ""
        )
        return (
            f"Relate {_format_ir_human(ir.get('left') or {})} to "
            f"{_format_ir_human(ir.get('right') or {})} by {ir.get('relation')}{threshold}"
        )
    if op == "ANNOTATE":
        return f"Add {ir.get('layer')!r} to {_format_ir_human(ir.get('source') or {})}"
    if op == "AGGREGATE":
        return (
            f"Aggregate {_format_ir_human(ir.get('source') or {})} by {ir.get('by')} "
            f"using {ir.get('metric')}"
        )
    if op == "COMPARE":
        right = (
            f" against {_format_ir_human(ir.get('right') or {})}" if ir.get("right") else ""
        )
        return f"Compare {_format_ir_human(ir.get('left') or {})}{right} by {ir.get('how')}"
    if op == "RANK":
        return f"Rank {len(ir.get('items') or [])} Algebra results in {ir.get('order')} order"
    return op


def _compile_scientific_algebra(args: dict, session: "Session") -> dict:
    scientific_question = " ".join(
        str(args.get("scientific_question") or args.get("question") or "").split()
    ).strip()[:1600]
    if not scientific_question:
        return {
            "status": "data_request", "reason": "missing_scientific_question",
            "detail": {"ask": "state the one scientific measurement or estimate to compile"},
            "provenance": [],
        }
    manifest = _scientific_resource_manifest(session)
    messages = E.P.build_messages(
        scientific_question, fewshot=E.GENERIC_FEWSHOT,
        capabilities=C.capability_catalog(),
    )
    messages[0]["content"] += (
        "\n\nSCIENTIFIC COMPILATION BOUNDARY:\n"
        "Compile the SCIENTIFIC QUESTION below, while retaining the ORIGINAL USER QUESTION as "
        "intent context. Emit the frozen Algebra tree only. Use a concrete SELECT entity only "
        "when it appears in the original user question, the admitted entity symbols, or the "
        "declared connector capability entities. Use only admitted REGION and ANNOTATE symbols. "
        "A candidate from model memory is not an admitted symbol. If a required entity, region, "
        "measurement, donor or threshold is missing, emit an appropriate ?hole. Do not emit "
        "skill names, plans, prose, result ids, paths, coordinates, sources or evidence claims.\n\n"
        "ORIGINAL USER QUESTION:\n" + session.current_data_question +
        "\n\nADMITTED RESOURCE SYMBOLS:\n" +
        json.dumps(manifest, ensure_ascii=False, default=str)[:24000]
    )
    try:
        response = _call_algebra_9b_messages(messages)
    except (OSError, ValueError, urllib.error.URLError, TimeoutError) as exc:
        return {
            "status": "data_request", "reason": "algebra_compiler_failed",
            "detail": {"error": f"{type(exc).__name__}: {str(exc)[:500]}"},
            "provenance": [],
        }
    ir = _bind_context(response["ir"])
    ir, symbol_bindings = _bind_scientific_symbols(ir, manifest)
    schema = IR.validate(ir)
    symbol_errors = _validate_scientific_symbols(
        ir, manifest, session.current_data_question)
    if not schema["valid"] or symbol_errors:
        execution = {
            "status": "data_request", "reason": "scientific_ir_rejected",
            "detail": {"schema_errors": schema["errors"], "binding_errors": symbol_errors,
                       "ask": "clarify the scientific entity, region or measurement"},
            "provenance": [],
        }
    else:
        execution = X.execute(ir)
    value = {
        "kind": "scientific_algebra", "scientific_question": scientific_question,
        "ir": ir, "human_reading": _format_ir_human(ir),
        "schema": schema, "execution": execution,
        "compiler": "Algebra 9B-004d", "usage": response.get("usage") or {},
        "symbol_bindings": symbol_bindings,
        "resource_manifest": {
            "regions": manifest.get("regions") or [],
            "entities": manifest.get("entities") or [],
            "layers": manifest.get("layers") or [],
            "audited_results": manifest.get("audited_results") or [],
        },
    }
    result_id = session.store_result("scientific_algebra", value)
    value["result_id"] = result_id
    session.append_audit({
        "type": "scientific_algebra", "scientific_question": scientific_question,
        "compiler": "Algebra 9B-004d", "ir": ir, "schema": schema,
        "symbol_bindings": symbol_bindings, "binding_errors": symbol_errors,
        "execution_status": execution.get("status"),
        "execution_reason": execution.get("reason"), "result_id": result_id,
    })
    return {
        "status": execution.get("status") or "data_request",
        "label": execution.get("label"),
        "value": value,
        "reason": execution.get("reason"),
        "detail": execution.get("detail"),
        "provenance": [{
            "op": "COMPILE_ALGEBRA", "compiler": "Algebra 9B-004d",
            "result_id": result_id, "ir_ops": schema.get("ops") or [],
        }] + list(execution.get("provenance") or []),
    }


def _site_discovery_context(query: str, region: object = None) -> str:
    aliases = [
        item.strip() for item in os.environ.get(
            "CODEX_NATIVE_SITE_ALIASES", "EBTL|Elephants by the Lake").split("|")
        if item.strip()
    ]
    combined = f"{query} {region or ''}"
    if not any(re.search(rf"\b{re.escape(alias)}\b", combined, flags=re.IGNORECASE)
               for alias in aliases):
        return ""
    profile = _load_site_profile()
    return " ".join(str(
        profile.get("discovery_context") or profile.get("where") or ""
    ).split()).strip(" ,.;:-")


def _site_discovery_queries(query: str, region: object = None) -> list[dict]:
    """Derive portable topic/region searches when a question contains a local site alias.

    Literature repositories rarely contain an organisation's acronym. Keep the user's exact
    wording for audit, but also search the topic without the alias and with the onboarded
    biogeographic context. This is a query rewrite only: it does not promote a taxon or claim that
    any returned work is site evidence.
    """
    aliases = [
        item.strip() for item in os.environ.get(
            "CODEX_NATIVE_SITE_ALIASES", "EBTL|Elephants by the Lake").split("|")
        if item.strip()
    ]
    context = _site_discovery_context(query, region)
    if not context:
        return []
    topic = query
    for alias in sorted(aliases, key=len, reverse=True):
        topic = re.sub(rf"\b{re.escape(alias)}\b", " ", topic, flags=re.IGNORECASE)
    topic = " ".join(topic.split()).strip(" ,.;:-")
    topic = re.sub(r"\b(?:at|in|near|around|within|inside)\s*$", "", topic,
                   flags=re.IGNORECASE).strip()
    if not topic:
        return []
    rows = [{"query": topic, "role": "topic_without_site_alias"}]
    if context:
        rows.insert(0, {
            "query": f"{topic} {context}"[:1000],
            "role": "topic_with_onboarded_geographic_context",
        })
    return rows


def _discovery_query_set(args: dict) -> list[dict]:
    primary = " ".join(str(args.get("query") or args.get("entity") or "").split()).strip()
    if not primary:
        return []
    supplied = args.get("query_variants")
    variants = supplied if isinstance(supplied, list) else []
    region = args.get("region")
    context = _site_discovery_context(primary, region)
    context_terms = {
        token for token in re.findall(r"[a-z0-9]+", context.casefold()) if len(token) >= 4
    }
    candidates = []
    for item in variants[:3]:
        variant = " ".join(str(item).split()).strip()
        if not variant:
            continue
        variant_terms = {
            token for token in re.findall(r"[a-z0-9]+", variant.casefold()) if len(token) >= 4
        }
        has_context = bool(context_terms and len(context_terms & variant_terms) >= 2)
        if context and not has_context:
            variant = f"{variant} {context}"[:1000]
            role = "planner_query_seed_with_onboarded_geographic_context"
        else:
            role = "planner_query_seed"
        candidates.append({"query": variant, "role": role})
    candidates.extend(_site_discovery_queries(primary, region))
    unique: list[dict] = []
    seen: set[str] = set()
    for item in candidates:
        key = item["query"].casefold()
        if not key or key == primary.casefold() or key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= 3:
            break
    unique.append({"query": primary, "role": "exact_user_bound_query"})
    return unique


def _discovery_row_key(row: dict) -> tuple[str, str]:
    identifier = str(row.get("doi") or row.get("url") or "").strip().casefold()
    if identifier:
        return ("identifier", identifier.removeprefix("doi:"))
    return (
        str(row.get("source_connector") or "").strip().casefold(),
        str(row.get("title") or "").strip().casefold(),
    )


def _discover_evidence(args: dict, session: "Session") -> dict:
    queries = _discovery_query_set(args)
    if not queries:
        return {"status": "data_request", "reason": "missing_query",
                "detail": {"ask": "provide the ecology question or dataset search terms"},
                "provenance": []}
    limit = max(1, min(int(args.get("limit") or 8), 20))
    found_by_query: dict[str, dict] = {}
    failures: dict[str, str] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(queries))) as pool:
        futures = {
            pool.submit(ORIGIN.evidence_discovery, item["query"], k=limit): item
            for item in queries
        }
        for future, item in futures.items():
            try:
                found_by_query[item["query"]] = future.result()
            except Exception as exc:
                failures[item["query"]] = f"{type(exc).__name__}: {str(exc)[:300]}"
    if not found_by_query:
        return {"status": "data_request", "reason": "source_unavailable",
                "detail": {"queries": queries, "errors": failures},
                "provenance": []}
    rows_by_query: list[list[dict]] = []
    connector_events: list[dict] = []
    connector_errors: dict[str, Any] = {}
    for item in queries:
        query = item["query"]
        found = found_by_query.get(query)
        if not found:
            continue
        query_rows = []
        for row in found.get("rows") or []:
            if not isinstance(row, dict):
                continue
            query_rows.append({
                **row, "matched_query": query, "query_role": item["role"],
            })
        # Keep buried semantic-card matches available, but show title-confirmed leads before
        # geographically coincidental or embedding-only results within each query branch.
        query_rows.sort(key=lambda row: not _discovery_title_matches(
            query, str(row.get("title") or "")))
        rows_by_query.append(query_rows)
        connector_events.extend(found.get("connector_events") or [])
        for name, error in (found.get("errors") or {}).items():
            connector_errors[f"{query}::{name}"] = error
    # Interleave variants so a high-volume first query cannot suppress every result from the
    # exact, topical or geographic branches. Deduplicate only after assigning query provenance;
    # the first branch that surfaced a lead remains visible in the audit.
    rows: list[dict] = []
    seen_rows: set[tuple[str, str]] = set()
    result_limit = max(limit, 8)
    for index in range(max((len(items) for items in rows_by_query), default=0)):
        for query_rows in rows_by_query:
            if index >= len(query_rows):
                continue
            row = query_rows[index]
            key = _discovery_row_key(row)
            if key in seen_rows:
                continue
            seen_rows.add(key)
            rows.append(row)
            if len(rows) >= result_limit:
                break
        if len(rows) >= result_limit:
            break
    primary = queries[-1]["query"]
    value = {
        "kind": "records", "rows": rows, "source": (
            "OpenAlex + Zenodo + Dryad + admitted local semantic corpus"),
        "label": "reported", "query": primary, "queries": queries,
        "errors": {**connector_errors, **failures},
        "note": (
            "Query-bound discovery leads from admitted metadata, repository and local-corpus "
            "connectors. Site aliases may be removed or replaced with onboarded geographic "
            "context for recall. Planner-supplied related taxa remain query seeds, not site "
            "records. A lead is not a biological observation or causal finding; inspect and "
            "extract its dataset before using it as model input."
        ),
        "connector_events": connector_events,
    }
    result_id = session.store_result("evidence", value)
    value["result_id"] = result_id
    return {"status": "answer", "label": "reported", "value": value,
            "provenance": [{"op": "DISCOVER", "query": primary,
                            "queries": queries,
                            "result_id": result_id,
                            "connectors": [event["tool"]
                                           for event in connector_events]}]}


def _inspect_dataset(args: dict, session: "Session") -> dict:
    result_id = str(args.get("result_id") or "").strip()
    doi = (str(args.get("doi") or "").strip().lower()
           .removeprefix("https://doi.org/").removeprefix("doi:"))
    stored = session.load_result(result_id) if result_id else None
    if not stored:
        return {"status": "data_request", "reason": "unknown_result",
                "detail": {"ask": "use a result_id returned by discover-ecology-evidence"},
                "provenance": []}
    rows = (stored.get("payload") or {}).get("rows") or []
    repository_rows = [row for row in rows if row.get("files") and
                       row.get("evidence_kind") == "archived_dataset"]
    selected = next((row for row in repository_rows
                     if str(row.get("doi") or "").lower()
                     .removeprefix("https://doi.org/").removeprefix("doi:") == doi), None)
    if selected is None and len(repository_rows) == 1 and not doi:
        selected = repository_rows[0]
    if selected is None:
        return {"status": "data_request", "reason": "dataset_not_in_result",
                "detail": {"result_id": result_id,
                           "available": [{"doi": row.get("doi"), "title": row.get("title")}
                                         for row in repository_rows[:12]],
                           "ask": "choose one returned Zenodo or Dryad dataset DOI"},
                "provenance": []}
    try:
        material = ORIGIN.inspect_evidence_dataset(selected)
    except Exception as exc:
        return {"status": "data_request", "reason": "source_unavailable",
                "detail": {"doi": selected.get("doi"),
                           "error": f"{type(exc).__name__}: {str(exc)[:300]}"},
                "provenance": []}
    material["codebook"] = str(material.get("codebook") or "")[:16000]
    value = {"kind": "records", "rows": material.get("files") or [],
             "source": selected.get("source_connector"), "label": "reported",
             "title": selected.get("title"), "doi": selected.get("doi"),
             "codebook": material["codebook"], "note": material["note"],
             "connector_events": material["connector_events"],
             "source_result_id": result_id}
    inspected_id = session.store_result("dataset", value)
    value["result_id"] = inspected_id
    return {"status": "answer", "label": "reported", "value": value,
            "provenance": [{"op": "INSPECT", "doi": selected.get("doi"),
                            "source_result_id": result_id, "result_id": inspected_id}]}


def _build_protocol(args: dict, session: "Session") -> dict:
    result_id = str(args.get("result_id") or "").strip()
    stored = session.load_result(result_id) if result_id else None
    if not stored or stored.get("kind") != "dataset":
        return {"status": "data_request", "reason": "unknown_inspected_dataset",
                "detail": {"ask": "inspect a returned Zenodo or Dryad dataset first, then pass its result_id"},
                "provenance": []}
    dataset = stored.get("payload") or {}
    purpose = " ".join(str(args.get("purpose") or "field confirmation").split())[:1000]
    audit_id = f"{session.id}/{session.turn}"
    title = str(args.get("title") or f"Field protocol: {dataset.get('title') or purpose}")[:180]
    artifact_dir = session.output / "artifacts" / f"turn-{session.turn:04d}-protocol"
    artifact = ARTIFACTS.write_field_protocol(
        artifact_dir, title, dataset, purpose, audit_id,
        source_file=str(args.get("source_file") or "").strip() or None)
    published = _publish_html_document(
        session, title, artifact.pop("html_content"), link_kind="document",
        label="Open field protocol")
    public_artifact = {
        key: artifact[key] for key in (
            "source_columns", "adapted_columns", "datasheet_columns", "blank_rows",
            "reported_source_files", "selected_source_file")
        if key in artifact
    }
    public_artifact["downloads"] = ["CSV datasheet"]
    value = {
        "kind": "records", "rows": [{"doi": dataset.get("doi"),
                                      "source_result_id": result_id,
                                      "datasheet_columns": artifact["datasheet_columns"]}],
        "source": dataset.get("source"), "label": "reported",
        "artifact": {**public_artifact, **published},
        "note": ("Created a source-linked protocol reader and blank CSV field datasheet. "
                 "Returned source columns and programme-added fields are explicitly separated."),
    }
    protocol_id = session.store_result("protocol", value)
    value["result_id"] = protocol_id
    return {"status": "answer", "label": "reported", "value": value,
            "provenance": [{"op": "PROTOCOL", "result_id": protocol_id,
                            "source_result_id": result_id, "doi": dataset.get("doi"),
                            "document_id": published["document_id"]}]}


def _taxon_execution(entity: str, region: str, estimate: bool, method: str = "feature") -> dict:
    if estimate:
        ir = {"op": "ESTIMATE", "method": method,
              "source": {"op": "SELECT", "entity": entity,
                         "region": {"op": "REGION", "place": "dry-Deccan donor belt"},
                         "time": None},
              "target": {"op": "REGION", "place": region}}
    else:
        ir = {"op": "SELECT", "entity": entity,
              "region": {"op": "REGION", "place": region}, "time": None}
    return X.execute(_bind_context(ir))


def _build_field_map(args: dict, session: "Session") -> dict:
    raw_entities = args.get("entities")
    if not isinstance(raw_entities, list):
        raw_entities = [args.get("entity"), args.get("second_entity")]
    entities = []
    for item in raw_entities:
        value = " ".join(str(item or "").split()).strip()
        if value and value.casefold() not in {x.casefold() for x in entities}:
            entities.append(value)
    entities = entities[:2]
    if not entities:
        return {"status": "data_request", "reason": "missing_entity",
                "detail": {"ask": "provide one or two named taxa to map"}, "provenance": []}
    region_name = str(args.get("region") or "EBTL")
    map_mode = str(args.get("map_mode") or "modelled").strip().casefold()
    if map_mode not in {"observed", "modelled"}:
        return {"status": "data_request", "reason": "invalid_map_mode",
                "detail": {"ask": "map_mode must be observed or modelled"},
                "provenance": []}
    source_region_name = (
        "dry-Deccan donor belt" if map_mode == "modelled"
        else str(args.get("source_region") or region_name)
    )
    method = str(args.get("method") or "feature")
    target = C.resolve_region(source_region_name if map_mode == "observed" else region_name)
    west_south_east_north = [target["bbox"][2], target["bbox"][0],
                             target["bbox"][3], target["bbox"][1]]
    vegetation = {str(x).casefold() for x in (args.get("vegetation_entities") or [])}
    estimates, local_rows, local_evidence, surfaces, provenance = {}, {}, {}, {}, []
    for entity in entities:
        resolved_entity = entity
        if region_name.casefold() in {"ebtl", "elephants by the lake", "the site"}:
            try:
                seeded = C.local_site_evidence_search(entity, C.resolve_region("EBTL"), None, 50)
                seeded_rows = seeded.get("rows") or []
                matched_name = _matched_local_taxon(entity, seeded_rows)
                if matched_name:
                    resolved_entity = matched_name
                    local_evidence[entity] = {
                        "matched_taxon": matched_name,
                        "rows": [{
                            key: row.get(key) for key in (
                                "common_name", "scientific_name", "record_status",
                                "individuals_observed", "survey_dates", "source", "source_record",
                            ) if row.get(key) is not None
                        } for row in seeded_rows[:12]],
                        "source": seeded.get("source"),
                        "query_semantics": seeded.get("query_semantics"),
                    }
                    provenance.append({
                        "op": "LOCAL_EVIDENCE", "entity": entity,
                        "matched_taxon": matched_name,
                        "query_semantics": seeded.get("query_semantics"),
                    })
            except Exception as exc:
                local_evidence[entity] = {
                    "status": "unavailable",
                    "reason": f"{type(exc).__name__}: {str(exc)[:240]}",
                }
        observed = _taxon_execution(
            resolved_entity,
            source_region_name if map_mode == "observed" else region_name, False)
        estimated = (
            _taxon_execution(resolved_entity, region_name, True, method)
            if map_mode == "modelled" else
            {"status": "not_run", "reason": "observed_only_map", "provenance": []}
        )
        rows = ((observed.get("value") or {}).get("rows") or []) \
            if observed.get("status") == "answer" else []
        local_rows[entity] = rows
        estimates[entity] = {
            "resolved_entity": resolved_entity,
            "status": estimated.get("status"), "reason": estimated.get("reason"),
            "gate": ((estimated.get("value") or {}).get("gate") or
                     (estimated.get("detail") or {}).get("reason")),
            "value": ((estimated.get("value") or {}).get("rows") or [])[:3],
        }
        provenance.extend(observed.get("provenance") or [])
        provenance.extend(estimated.get("provenance") or [])
        if (map_mode == "modelled" and entity.casefold() in vegetation
                and estimated.get("status") == "answer"):
            try:
                surfaces[entity] = ORIGIN.invasive_surface(
                    entity, int(args.get("year") or 2024), int(args.get("grid_n") or 20))
            except Exception as exc:
                estimates[entity]["surface_error"] = f"{type(exc).__name__}: {str(exc)[:240]}"

    layers = []
    for entity, rows in local_rows.items():
        if rows:
            layers.append({"name": f"Observed {entity}", "rows": [
                {"lat": row["lat"], "lon": row["lon"], "score": 1,
                 "tooltip": f"Observed record · {row.get('source') or 'source in audit'}"}
                for row in rows if "lat" in row and "lon" in row]})
    surface_rows = {}
    for entity, surface in surfaces.items():
        rows = [{"lat": row["lat"], "lon": row["lon"],
                 "score": float(row.get("likelihood") or 0),
                 "tooltip": f"{entity} modelled likelihood {row.get('likelihood')}"}
                for row in surface.get("grid") or []]
        surface_rows[entity] = rows
        layers.append({"name": f"Modelled {entity}", "rows": rows})

    mode = ("observed occurrence map" if map_mode == "observed"
            else "spatially balanced confirmation design")
    candidates = []
    if map_mode == "observed":
        candidates = []
    elif len(surface_rows) == 2:
        left, right = (surface_rows[entity] for entity in entities)
        by_coord = {(round(row["lat"], 6), round(row["lon"], 6)): row for row in right}
        for row in left:
            other = by_coord.get((round(row["lat"], 6), round(row["lon"], 6)))
            if other:
                candidates.append({**row, "score": math.sqrt(row["score"] * other["score"]),
                                   "evidence_label": "modelled surface overlap",
                                   "reason": (f"confirm both {entities[0]} and {entities[1]}; "
                                              "spatial overlap is not interaction evidence")})
        mode = "modelled surface-overlap confirmation map"
    elif surface_rows:
        entity, candidates = next(iter(surface_rows.items()))
        partner = next((x for x in entities if x != entity), None)
        for row in candidates:
            row["evidence_label"] = f"modelled {entity} likelihood"
            row["reason"] = (f"confirm {entity} model hotspot" +
                             (f" and run a paired {partner} observation; the {partner} estimate "
                              "does not provide a fine-scale surface" if partner else ""))
        mode = "model hotspot and paired-confirmation map"
    else:
        candidates = ARTIFACTS.balanced_sampling_points(west_south_east_north, 9)
        passed = [
            (entity, estimate) for entity, estimate in estimates.items()
            if isinstance(estimate.get("gate"), dict) and estimate["gate"].get("pass") is True
        ]
        if passed:
            entity, estimate = passed[0]
            fraction = next((
                row.get("suitability_fraction") for row in (estimate.get("value") or [])
                if isinstance(row, dict) and
                isinstance(row.get("suitability_fraction"), (int, float))
            ), None)
            qualifier = (
                f" (AOI-wide suitability fraction {fraction:.3f})"
                if isinstance(fraction, (int, float)) else ""
            )
            reason = (
                f"{entity} transfer gate passed{qualifier}, but returned no within-AOI ranking "
                "surface; this spatially balanced point reduces site-wide location uncertainty"
            )
        else:
            failed = next((
                estimate.get("gate") or estimate.get("reason")
                for estimate in estimates.values()
                if estimate.get("gate") or estimate.get("reason")
            ), None)
            failure = (
                str(failed.get("reason") or "") if isinstance(failed, dict) else str(failed or "")
            )
            reason = (
                "No fine-scale transfer surface passed; this spatially balanced point helps "
                "collect local evidence across the target area" +
                (f" ({failure})" if failure else "")
            )
        for row in candidates:
            row["reason"] = reason[:500]

    if map_mode == "observed":
        waypoints = []
        for entity, rows in local_rows.items():
            for row in rows:
                if not isinstance(row.get("lat"), (int, float)) or not isinstance(
                        row.get("lon"), (int, float)):
                    continue
                waypoints.append({
                    "lat": row["lat"], "lon": row["lon"], "score": 1,
                    "evidence_label": f"observed {entity}",
                    "reason": str(row.get("source") or "source retained in audit"),
                })
                if len(waypoints) >= 1000:
                    break
            if len(waypoints) >= 1000:
                break
        for index, row in enumerate(waypoints, 1):
            row["point_id"] = f"OBS-{index:04d}"
    else:
        waypoints = ARTIFACTS.select_waypoints(
            candidates, limit=int(args.get("points") or 9))
    notes = [
        "Observed points, modelled surfaces and designed collection points are separate layers.",
        "Spatial overlap or proximity does not establish seed dispersal, avoidance, shared habitat or temporal co-observation.",
        "The EBTL geometry is the declared analysis bbox, not a surveyed legal property boundary.",
    ]
    use_base_image = MAP_BASE_IMAGE.is_file() and (
        source_region_name if map_mode == "observed" else region_name
    ).casefold() in {"ebtl", "elephants by the lake"}
    if use_base_image:
        notes.append("The background is contextual dry-season Sentinel-2 imagery; it is not evidence for the mapped taxon.")
    if map_mode == "observed":
        notes.append(
            f"This view contains returned occurrence records from {source_region_name}; "
            "it is not a prediction.")
    if not surfaces:
        if map_mode != "observed":
            notes.append(
                "No admitted fine-scale ranking surface ran; numbered points are a sampling "
                "design, not predicted presence or overlap.")
    title = str(args.get("title") or ("Field check: " + " × ".join(entities)))[:180]
    audit_id = f"{session.id}/{session.turn}"
    artifact_dir = session.output / "artifacts" / f"turn-{session.turn:04d}"
    artifact = ARTIFACTS.write_field_map(
        artifact_dir, title, west_south_east_north, layers, waypoints, notes, audit_id, mode,
        base_image=MAP_BASE_IMAGE if use_base_image else None,
        base_bbox_wsen=MAP_BASE_BBOX)
    published = _publish_html_document(session, title, artifact.pop("html_content"))
    public_artifact = {
        key: artifact[key] for key in ("waypoint_count", "point_ids", "map_mode")
        if key in artifact
    }
    public_artifact["downloads"] = ["GeoJSON", "CSV field sheet"]
    evidence_label = (
        "observed" if map_mode == "observed"
        else ("modelled" if surfaces else "designed")
    )
    value = {
        "kind": "records", "rows": waypoints, "source": "audited ecology field-map renderer",
        "label": evidence_label, "entities": entities,
        "local_evidence": local_evidence, "estimates": estimates,
        "artifact": {**public_artifact, **published},
        "note": (
            f"Created {mode} with {len(waypoints)} "
            f"{'returned observation points' if map_mode == 'observed' else 'stable field points'}. "
            "Use the side-panel map; overlap remains a confirmation hypothesis, not an interaction."
        ),
    }
    result_id = session.store_result("map", value)
    value["result_id"] = result_id
    provenance.append({"op": "MAP", "result_id": result_id, "audit_id": audit_id,
                       "entities": entities, "mode": mode,
                       "point_ids": artifact["point_ids"], "document_id": published["document_id"]})
    return {"status": "answer", "label": value["label"], "value": value,
            "provenance": provenance}


def _execute_skill(skill_id: str, args: dict, session: "Session | None" = None) -> dict:
    if skill_id not in SKILLS_BY_ID:
        raise KeyError(f"unknown skill: {skill_id}")
    mode = (SKILLS_BY_ID[skill_id].get("binding") or {}).get("mode")
    if mode == "algebra_9b_planner":
        if session is None:
            raise ValueError(f"{skill_id} requires a session")
        execution = _plan_with_algebra_9b(args, session)
        return {
            "skill": skill_id, "plan": execution.get("value"),
            "schema": {"valid": execution.get("status") == "answer",
                       "errors": [], "holes": [], "ops": [],
                       "has_estimate": False, "unbound": False,
                       "note": "dialogue planner envelope; frozen scientific Algebra unchanged"},
            "execution": execution,
        }
    if mode == "site_overview":
        execution = _site_overview(args, session)
        return {
            "skill": skill_id,
            "site_profile": {"site_id": args.get("site_id") or args.get("region") or "EBTL"},
            "schema": {"valid": execution.get("status") == "answer",
                       "errors": [], "holes": [], "ops": [],
                       "has_estimate": False, "unbound": False,
                       "note": "runtime onboarding profile; frozen scientific Algebra unchanged"},
            "execution": execution,
        }
    if mode == "local_evidence_search":
        query = " ".join(str(args.get("query") or args.get("entity") or "").split()).strip()
        region_name = _normalise_region_name(args.get("region") or "EBTL")
        try:
            region = C.resolve_region(region_name)
            value = C.local_site_evidence_search(
                query, region, args.get("time"), int(args.get("limit") or 200))
            status = "answer" if value.get("rows") else "data_request"
            execution = {
                "status": status, "label": value.get("label") or "reported", "value": value,
                "reason": None if status == "answer" else "no_local_evidence_match",
                "provenance": [{"op": "SELECT", "route": "local-site-evidence-search",
                                "query": query, "region": region_name,
                                "query_semantics": value.get("query_semantics")}],
            }
            if session is not None:
                result_id = session.store_result("local_evidence", value)
                value["result_id"] = result_id
        except (TypeError, ValueError, RuntimeError) as exc:
            execution = {"status": "data_request", "reason": "invalid_local_evidence_query",
                         "detail": {"error": str(exc)}, "provenance": []}
        return {
            "skill": skill_id,
            "ir": {"op": "SELECT", "entity": query,
                   "region": {"op": "REGION", "place": region_name}},
            "schema": {"valid": bool(query), "errors": [] if query else ["query is required"],
                       "holes": [], "ops": ["SELECT"], "has_estimate": False,
                       "unbound": False},
            "execution": execution,
        }
    if mode == "occurrence_relate":
        try:
            ir = _bind_context(_occurrence_relate_ir(args))
            schema = IR.validate(ir)
            execution = X.execute(ir) if schema["valid"] else {
                "status": "data_request", "reason": "invalid_ir",
                "detail": {"errors": schema["errors"]}, "provenance": [],
            }
        except (TypeError, ValueError) as exc:
            ir = {"op": "RELATE", "args": _redact_audit(args)}
            schema = {"valid": False, "errors": [str(exc)], "holes": [],
                      "ops": ["RELATE"], "has_estimate": False, "unbound": False}
            execution = {"status": "data_request", "reason": "invalid_relation_request",
                         "detail": {"errors": [str(exc)]}, "provenance": []}
        return {"skill": skill_id, "ir": ir, "schema": schema, "execution": execution}
    if mode == "model_request":
        execution = _record_model_request(args, session)
        return {
            "skill": skill_id,
            "ir": {"op": "REQUEST_MODEL", "request": args.get("request"),
                   "region": args.get("region"), "reason": args.get("reason")},
            "schema": {"valid": True, "errors": [], "holes": [],
                       "ops": ["REQUEST_MODEL"], "has_estimate": False, "unbound": False},
            "execution": execution,
        }
    if mode == "scientific_algebra":
        if session is None:
            raise ValueError(f"{skill_id} requires a session")
        execution = _compile_scientific_algebra(args, session)
        value = execution.get("value") if isinstance(execution.get("value"), dict) else {}
        return {
            "skill": skill_id,
            "scientific_question": value.get("scientific_question"),
            "algebra": {
                "compiler": value.get("compiler"), "ir": value.get("ir"),
                "human_reading": value.get("human_reading"),
            },
            "schema": value.get("schema") or {
                "valid": False, "errors": ["compiler did not return an Algebra tree"],
                "holes": [], "ops": [], "has_estimate": False, "unbound": True,
            },
            "execution": execution,
        }
    if mode in {"evidence_discovery", "dataset_inspect", "field_protocol", "field_map"}:
        if session is None:
            raise ValueError(f"{skill_id} requires a session")
        if mode == "evidence_discovery":
            execution = _discover_evidence(args, session)
            op = "DISCOVER"
        elif mode == "dataset_inspect":
            execution = _inspect_dataset(args, session)
            op = "INSPECT"
        elif mode == "field_protocol":
            execution = _build_protocol(args, session)
            op = "PROTOCOL"
        else:
            execution = _build_field_map(args, session)
            op = "MAP"
        return {"skill": skill_id,
                "ir": {"op": op, "args": _redact_audit(args)},
                "schema": {"valid": True, "errors": [], "holes": [], "ops": [op],
                           "has_estimate": op == "MAP", "unbound": False},
                "execution": execution}
    ir = _bind_context(_skill_ir(SKILLS_BY_ID[skill_id], args))
    schema = IR.validate(ir)
    if not schema["valid"]:
        execution = {"status": "data_request", "reason": "invalid_ir",
                     "detail": {"errors": schema["errors"]}, "provenance": []}
    else:
        execution = X.execute(ir)
    return {"skill": skill_id, "ir": ir, "schema": schema, "execution": execution}


def _summary(result: dict) -> str:
    execution = result.get("execution") or {}
    status = execution.get("status") or "unknown"
    if status != "answer":
        reason = execution.get("reason") or "unspecified"
        return f"{status}: {reason}"
    value = execution.get("value") or {}
    rows = value.get("rows") if isinstance(value, dict) else None
    row_count = len(rows) if isinstance(rows, list) else None
    label = execution.get("label") or (value.get("label") if isinstance(value, dict) else None)
    source = value.get("source") if isinstance(value, dict) else None
    parts = ["answer"]
    if row_count is not None:
        parts.append(f"{row_count} rows")
    if label:
        parts.append(str(label))
    if source:
        parts.append(str(source))
    note = value.get("note") if isinstance(value, dict) else None
    if note:
        compact_note = " ".join(str(note).split())
        parts.append(compact_note[:220] + ("..." if len(compact_note) > 220 else ""))
    return " · ".join(parts)


GUIDED_OPERATION_SKILLS = {
    "explore_site_wildlife": {"local-site-fauna-summary"},
    "explore_site_vegetation": {"local-invasive-management-evidence"},
    "explore_site_fire": {"historical-fire-exposure"},
    "search_wider_occurrences": {"merged-taxon-occurrence-search"},
    "search_wider_evidence": {"discover-ecology-evidence"},
    "show_observed_map": {"build-ecology-field-map"},
    "test_transfer": {
        "compile-scientific-algebra-9b", "gated-species-presence-transfer"},
    "build_model_map": {
        "compile-scientific-algebra-9b", "build-ecology-field-map"},
    "inspect_dataset": {"inspect-evidence-dataset"},
    "build_protocol": {"build-source-backed-field-protocol"},
}


def _guided_value(value: Any) -> Any:
    """Keep only small scalar/list values in durable guided-action state."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return " ".join(value.split())[:500]
    if isinstance(value, list):
        return [_guided_value(item) for item in value[:6]
                if isinstance(item, (str, int, float, bool))]
    return None


def _guided_action(label: str, operation: str, description: str, **args: Any) -> dict:
    clean_args = {}
    for key, value in args.items():
        clean = _guided_value(value)
        if clean is not None and clean != "" and clean != []:
            clean_args[key] = clean
    return {
        "id": _safe_id(operation + "-" + label.casefold())[:80],
        "label": " ".join(label.split())[:60],
        "description": " ".join(description.split())[:180],
        "operation": operation,
        "args": clean_args,
    }


def _execution_value(call: dict) -> dict:
    result = call.get("result") if isinstance(call, dict) else {}
    execution = result.get("execution") if isinstance(result, dict) else {}
    value = execution.get("value") if isinstance(execution, dict) else {}
    return value if isinstance(value, dict) else {}


def _normalise_match_text(value: object) -> str:
    return " ".join(str(value or "").translate(str.maketrans({
        "\u2018": "'", "\u2019": "'", "\u02bc": "'", "\uff07": "'",
    })).casefold().split())


def _matched_local_taxon(query: str, rows: list[dict]) -> str:
    """Return one unambiguous local taxon, preferring its source-reported scientific name."""
    key = lambda value: re.sub(r"[^a-z0-9]+", "", _normalise_match_text(value))
    focal = key(query)
    focal_tokens = {
        token for token in re.findall(r"[a-z0-9]+", _normalise_match_text(query))
        if len(token) > 2
    }
    matches = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        candidates = [
            row.get("common_name"), row.get("scientific_name"),
            row.get("taxon"), row.get("species"),
        ]
        examples = row.get("examples")
        if isinstance(examples, list):
            candidates.extend(examples[:100])
        matched = next((
            candidate for candidate in candidates if candidate and (
                (focal and key(candidate) == focal) or
                (lambda tokens: tokens and focal_tokens and (
                    tokens <= focal_tokens or focal_tokens <= tokens
                ))({
                    token for token in re.findall(
                        r"[a-z0-9]+", _normalise_match_text(candidate))
                    if len(token) > 2
                })
            )
        ), None)
        if matched is None:
            continue
        resolved = str(row.get("scientific_name") or row.get("common_name") or matched)
        matches[key(resolved)] = resolved
    return next(iter(matches.values())) if len(matches) == 1 else ""


def _discovery_title_matches(query: str, title: str) -> bool:
    stop = {
        "search", "dataset", "data", "evidence", "occurrence", "occurrences", "public",
        "region", "belt", "donor", "ebtl", "deccan", "dry", "eastern", "ghats",
    }
    terms = {
        re.sub(r"[^a-z0-9]+", "", token)
        for token in _normalise_match_text(query).split()
        if len(re.sub(r"[^a-z0-9]+", "", token)) >= 4
    } - stop
    title_terms = {
        re.sub(r"[^a-z0-9]+", "", token)
        for token in _normalise_match_text(title).split()
    }
    return bool(terms & title_terms)


def _derive_guidance(session: "Session") -> dict | None:
    """Derive the next valid investigation operations from completed skills.

    This is a capability graph, not a species script: taxa, regions and result handles are
    carried from the audited skill arguments/results. Codex explains the finding; code decides
    which operations may follow it.
    """
    calls = list(session.turn_skill_calls)
    if not calls:
        return None
    last = calls[-1]
    skill = str(last.get("skill") or "")
    args = last.get("args") if isinstance(last.get("args"), dict) else {}
    value = _execution_value(last)
    execution = (last.get("result") or {}).get("execution") or {}
    status = str(execution.get("status") or "")
    reason = str(execution.get("reason") or "")
    returned_rows = value.get("rows") if isinstance(value.get("rows"), list) else []
    raw_entities = args.get("entities")
    first_entity = raw_entities[0] if isinstance(raw_entities, list) and raw_entities else ""
    entity = " ".join(str(
        args.get("entity") or args.get("query") or
        first_entity
    ).split())
    region = _normalise_region_name(args.get("region") or "EBTL")
    actions: list[dict] = []
    question = "What should I do next?"

    if skill == "site-overview":
        question = "What would you like to know more about?"
        actions.extend([
            _guided_action(
                "Explore local wildlife", "explore_site_wildlife",
                "Summarise the registered local fauna evidence.", region=region),
            _guided_action(
                "Explore invasive management", "explore_site_vegetation",
                "Review registered invasive and non-native plant management evidence.",
                region=region),
            _guided_action(
                "Explore fire history", "explore_site_fire",
                "Check the configured historical fire-exposure layer.", region=region),
        ])
    elif skill in {
        "local-site-evidence-search", "local-site-fauna-summary",
        "local-snake-inventory", "local-bird-inventory",
    }:
        question = "Where should I look for the most useful next data?"
        if entity:
            named_taxon = _matched_local_taxon(entity, returned_rows)
            if named_taxon:
                actions.extend([
                    _guided_action(
                        "Search wider records", "search_wider_occurrences",
                        "Resolve the taxon and retrieve admitted georeferenced occurrences.",
                        entity=named_taxon, target_region=region,
                        region="dry-Deccan donor belt"),
                    _guided_action(
                        "Map field-check locations", "build_model_map",
                        "Run the transfer gate; map model hotspots or honest collection points.",
                        entity=named_taxon, region=region,
                        source_region="dry-Deccan donor belt", map_mode="modelled"),
                ])
            else:
                actions.append(_guided_action(
                    "Search wider sources", "search_wider_evidence",
                    "Look for admitted public datasets or literature outside the site.",
                    query=entity, target_region=region, region="dry-Deccan donor belt"))
    elif skill == "merged-taxon-occurrence-search":
        if status != "answer" or not returned_rows:
            # A failed/empty retrieval cannot authorize mapping or transfer. The concise answer
            # carries the connector's requested clarification or data gap.
            actions = []
        elif region.casefold() in {"ebtl", "elephants by the lake"}:
            question = "Continue beyond the site?"
            actions.append(_guided_action(
                "Search a wider region", "search_wider_occurrences",
                "Retrieve admitted records from the declared donor region.",
                entity=entity, target_region=region, region="dry-Deccan donor belt"))
        else:
            question = "How should I use these records?"
            actions.extend([
                _guided_action(
                    "Show the raw points", "show_observed_map",
                    "Map returned observations only; do not run a prediction.",
                    entity=entity, region=region, source_region=region, map_mode="observed"),
                _guided_action(
                    "Test transfer to the site", "test_transfer",
                    "Check whether donor records can support an environmental estimate at the site.",
                    entity=entity, donor_region=region,
                    target=args.get("target_region") or "EBTL"),
                _guided_action(
                    "Map model and collection points", "build_model_map",
                    "Run the gate and map model hotspots or labelled field-check locations.",
                    entity=entity, region=args.get("target_region") or "EBTL",
                    source_region=region, map_mode="modelled"),
            ])
    elif skill == "gated-species-presence-transfer":
        question = "Would a field map help?"
        actions.append(_guided_action(
            "Build a modelled field map", "build_model_map",
            "Render the estimate if its gate passes, otherwise produce confirmation sites.",
            entity=entity, region=args.get("target") or "EBTL", map_mode="modelled"))
    elif (skill == "build-ecology-field-map"
          and str(args.get("map_mode") or "").casefold() == "modelled"
          and status == "answer"):
        estimates = value.get("estimates") if isinstance(value.get("estimates"), dict) else {}
        supported = next((
            estimate for estimate in estimates.values()
            if isinstance(estimate, dict) and estimate.get("status") == "answer"
            and estimate.get("resolved_entity")
        ), None)
        if supported:
            question = "Would you like to inspect the supporting observations?"
            actions.append(_guided_action(
                "Show supporting occurrence points", "show_observed_map",
                "Map the admitted donor observations without the prediction layer.",
                entity=supported["resolved_entity"], region="dry-Deccan donor belt",
                source_region="dry-Deccan donor belt", map_mode="observed"))
    elif (skill == "build-ecology-field-map"
          and str(args.get("map_mode") or "").casefold() == "observed"
          and status == "answer" and returned_rows):
        question = "Continue from observations to an estimate?"
        actions.append(_guided_action(
            "Test environmental transfer", "test_transfer",
            "Check whether these donor observations can support an estimate at the site.",
            entity=entity, donor_region=args.get("source_region") or region,
            target=args.get("target_region") or "EBTL"))
    elif skill == "discover-ecology-evidence":
        result_id = str(value.get("result_id") or "")
        for row in (value.get("rows") or [])[:3]:
            if not isinstance(row, dict):
                continue
            doi = str(row.get("doi") or "").strip()
            if (not doi or not result_id or not _discovery_title_matches(
                    str(args.get("query") or ""), str(row.get("title") or ""))):
                continue
            title = " ".join(str(row.get("title") or doi).split())
            actions.append(_guided_action(
                f"Inspect {title[:36]}", "inspect_dataset",
                f"Open returned dataset material for {doi}.",
                result_id=result_id, doi=doi))
        if actions:
            question = "Which returned dataset should I inspect?"
    elif skill == "inspect-evidence-dataset":
        result_id = str(value.get("result_id") or "")
        if result_id:
            question = "Turn this source into field material?"
            actions.append(_guided_action(
                "Build a field datasheet", "build_protocol",
                "Use only the inspected source columns and label programme-added fields.",
                result_id=result_id, purpose="repeat the inspected observations at the site"))

    if (status == "data_request" and entity
            and skill in {"merged-taxon-occurrence-search",
                          "gated-species-presence-transfer"}
            and reason not in {
                "no_connector", "unresolved_taxon", "ambiguous_taxon", "missing_entity",
            }
            and not any(action["operation"] == "build_model_map" for action in actions)):
        question = "Where would new field data be most useful?"
        actions.append(_guided_action(
            "Map field-check locations", "build_model_map",
            "Map model-supported locations or a labelled spatial collection design.",
            entity=entity, region=args.get("target") or args.get("target_region") or "EBTL",
            source_region=args.get("donor_region") or args.get("region") or
            "dry-Deccan donor belt", map_mode="modelled"))

    actions = [action for action in actions
               if action["operation"] in GUIDED_OPERATION_SKILLS][:3]
    if not actions:
        return None
    state_id = _sha256({
        "session": session.id, "turn": session.turn,
        "skills": [call.get("skill") for call in calls], "actions": actions,
    })[:16]
    return {
        "schema": 1, "state_id": state_id, "audit_id": f"{session.id}/{session.turn}",
        "question": question, "options": actions, "multi": False,
    }


def _guided_directive(action: dict) -> str:
    operation = action["operation"]
    args = action.get("args") or {}
    allowed = sorted(GUIDED_OPERATION_SKILLS[operation])
    return (
        "The user selected the guided investigation action "
        f"{action['label']!r}. Perform exactly one investigation stage. "
        f"Authorized skill set for this stage: {', '.join(allowed)}. "
        f"Use these controller-bound arguments: {_stable_json(args)}. "
        "Do not silently continue to another stage; report the useful result briefly and stop "
        "so the controller can offer the next valid actions."
    )


class Session:
    def __init__(self, session_id: str):
        self.id = _safe_id(session_id)
        self.root = STATE_ROOT / self.id
        self.home = self.root / "home"
        self.work = self.root / "work"
        self.input = self.root / "input"
        self.output = self.root / "output"
        self.results = self.root / "results"
        self.state_path = self.root / "state.json"
        self.audit_path = self.root / "audit.jsonl"
        self.raw_path = self.root / "codex-events.jsonl"
        self.lock = threading.Lock()
        self.gateway_token = secrets.token_urlsafe(24)
        self.thread_id: str | None = None
        self.owner = ""
        self.attachments: list[dict] = []
        self.pending_guidance: dict | None = None
        self.investigation_history: list[dict] = []
        self.turn_skill_calls: list[dict] = []
        self.guided_action: dict | None = None
        self.guided_allowed_skills: set[str] | None = None
        self.current_data_question = ""
        self.algebra_planner_calls = 0
        self.algebra_plans: list[dict] = []
        self.active_algebra_plan: dict | None = None
        self.turn = 0
        self._load()
        self._prepare()

    def _load(self) -> None:
        try:
            state = json.loads(self.state_path.read_text())
        except Exception:
            state = {}
        self.thread_id = state.get("thread_id")
        self.owner = str(state.get("owner") or "")[:200]
        self.attachments = list(state.get("attachments") or [])
        pending = state.get("pending_guidance")
        self.pending_guidance = pending if isinstance(pending, dict) else None
        self.investigation_history = list(state.get("investigation_history") or [])[-30:]
        self.turn = int(state.get("turn") or 0)
        # Gateway credentials are process-scoped. Never reload them from durable session state.

    def _save(self) -> None:
        _atomic_json(self.state_path, {
            "schema": 2, "session_id": self.id, "thread_id": self.thread_id,
            "turn": self.turn, "pending_guidance": self.pending_guidance,
            "investigation_history": self.investigation_history[-30:],
            "owner": self.owner, "attachments": self.attachments,
            "model": MODEL, "reasoning": REASONING,
            "skills_sha256": _sha256(SKILLS), "updated_at": dt.datetime.now().isoformat(),
        })

    def _prepare(self) -> None:
        for path in (self.home, self.work, self.input, self.output, self.results):
            path.mkdir(parents=True, exist_ok=True)
        auth_target = self.home / "auth.json"
        if not auth_target.exists():
            if not AUTH_SOURCE.exists():
                raise FileNotFoundError(f"Codex auth file not found: {AUTH_SOURCE}")
            shutil.copy2(AUTH_SOURCE, auth_target)
            os.chmod(auth_target, 0o600)
        invocation_root = (
            CONTAINER_ROOT / "sessions" / self.id / "input"
            if RUNNER == "hermes-exec" else self.input
        )
        index_lines = ["# Available conservation skills", "",
                       "Read the relevant SKILL.md, then invoke exactly as documented.", ""]
        for skill in SKILLS:
            index_lines.append(f"- `{skill['id']}` — {skill['description']}")
            skill_dir = self.input / "skills" / skill["id"]
            skill_dir.mkdir(parents=True, exist_ok=True)
            mode = (skill.get("binding") or {}).get("mode")
            if mode == "model_request":
                md = (
                    f"# {skill['id']}\n\n{skill['description']}\n\n"
                    "Use only after the user explicitly asks to submit or record the missing-model "
                    "request. Invoke with a concise request, region, and evidence gap:\n\n```bash\n"
                    "python3 " + str(invocation_root / "skill_call.py") + " " + skill["id"] +
                    " '{\"request\":\"current fire-risk model\",\"region\":\"EBTL\","
                    "\"reason\":\"historical exposure is not current probability\","
                    "\"response_variable\":\"fire probability in the next 7 days\","
                    "\"predictors\":[\"weather\",\"fuel moisture\",\"fuel load\"],"
                    "\"labels\":\"dated ignition/non-ignition outcomes\","
                    "\"spatial_extent\":\"declared EBTL analysis bbox\","
                    "\"validation_target\":\"held-out Brier score and calibration curve\"}'\n```\n"
                    "Return the request id to the user.\n"
                )
            elif skill.get("instructions"):
                md = (
                    f"# {skill['id']}\n\n{skill['description']}\n\n" +
                    str(skill["instructions"]).replace(
                        "{skill_call}", str(invocation_root / "skill_call.py")) +
                    "\n\nThe command returns audited JSON.\n"
                )
            else:
                md = (
                f"# {skill['id']}\n\n{skill['description']}\n\nUse for:\n" +
                "\n".join(f"- {x}" for x in skill.get("use_for") or []) +
                "\n\nDo not use for:\n" +
                "\n".join(f"- {x}" for x in skill.get("exclude") or []) +
                "\n\nInvoke:\n\n```bash\npython3 " + str(invocation_root / "skill_call.py") +
                " " + skill["id"] + " '{\"region\":\"EBTL\"}'\n```\n" +
                "For a named-taxon skill add `entity`; add `radius_km` only when the user "
                "explicitly asks to widen a search. Only include arguments the question supplies "
                "or the conversation has established. The command returns audited JSON.\n"
                )
            (skill_dir / "SKILL.md").write_text(md)
        index_lines.extend([
            "",
            "# Presentation skill",
            "",
            "- `publish-report` — Publish a polished, shareable Idlisseus report only when the "
            "user explicitly asks for a report or dashboard.",
        ])
        (self.input / "SKILLS_INDEX.md").write_text("\n".join(index_lines) + "\n")
        wrapper = (
            "#!/usr/bin/env python3\nimport json,sys,urllib.request\n"
            f"URL='http://127.0.0.1:{SERVER_PORT}/internal/skill-call'\n"
            f"TOKEN={self.gateway_token!r}\nSESSION={self.id!r}\n"
            "def parse_args():\n"
            " if len(sys.argv)<3:return {}\n"
            " if sys.argv[2]!='--pairs':return json.loads(sys.argv[2])\n"
            " out={}\n"
            " for item in sys.argv[3:]:\n"
            "  key,sep,raw=item.partition('=')\n"
            "  if not sep or not key:raise ValueError('pair arguments must be key=value')\n"
            "  try:value=json.loads(raw)\n"
            "  except json.JSONDecodeError:value=raw\n"
            "  out[key]=value\n"
            " return out\n"
            "payload={'session':SESSION,'skill':sys.argv[1],'args':parse_args()}\n"
            "req=urllib.request.Request(URL,data=json.dumps(payload).encode(),"
            "headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKEN})\n"
            "print(urllib.request.urlopen(req,timeout=300).read().decode())\n"
        )
        wrapper_path = self.input / "skill_call.py"
        wrapper_path.write_text(wrapper)
        os.chmod(wrapper_path, 0o700)
        report_wrapper = (
            "#!/usr/bin/env python3\nimport json,sys,urllib.request\n"
            f"URL='http://127.0.0.1:{SERVER_PORT}/internal/publish-report'\n"
            f"TOKEN={self.gateway_token!r}\nSESSION={self.id!r}\n"
            "args=json.load(sys.stdin) if len(sys.argv)<2 else json.loads(sys.argv[1])\n"
            "payload={'session':SESSION,'args':args}\n"
            "req=urllib.request.Request(URL,data=json.dumps(payload).encode(),"
            "headers={'Content-Type':'application/json','Authorization':'Bearer '+TOKEN})\n"
            "print(urllib.request.urlopen(req,timeout=30).read().decode())\n"
        )
        report_path = self.input / "publish_report.py"
        report_path.write_text(report_wrapper)
        os.chmod(report_path, 0o700)
        report_skill = self.input / "skills" / "publish-report"
        report_skill.mkdir(parents=True, exist_ok=True)
        (report_skill / "SKILL.md").write_text(
            "# publish-report\n\n"
            "Use only when the user explicitly asks for a report or dashboard. Analyze and verify "
            "the data first, then publish the final presentation through Idlisseus. Do not write "
            "HTML or report files directly.\n\n"
            "Invoke with one JSON object containing `title`, `markdown`, and optional `sources`:\n\n"
            "```bash\npython3 " + str(invocation_root / "publish_report.py") +
            " '{\"title\":\"Site birds\",\"markdown\":\"# Site birds\\n...\",\"sources\":[]}'\n```\n"
            "The result returns the authenticated browser URL and report id. Include that URL in "
            "the final answer. Keep observed facts, proxies, reports, and estimates labelled.\n"
        )
        self._save()

    def begin_turn(self, display_message: str) -> tuple[str, dict | None]:
        """Resolve an exact button/label choice and invalidate stale unselected actions."""
        selected = None
        normal = " ".join(str(display_message or "").casefold().split())
        pending = self.pending_guidance if isinstance(self.pending_guidance, dict) else None
        if pending:
            for option in pending.get("options") or []:
                if not isinstance(option, dict):
                    continue
                labels = {
                    " ".join(str(option.get("label") or "").casefold().split()),
                    " ".join(str(option.get("id") or "").casefold().split()),
                }
                if normal in labels:
                    selected = option
                    break
        self.pending_guidance = None
        self.guided_action = selected
        self.guided_allowed_skills = (
            set(GUIDED_OPERATION_SKILLS.get(str(selected.get("operation")), set()))
            if selected else None
        )
        if selected:
            self.investigation_history.append({
                "state_id": pending.get("state_id") if pending else "",
                "selected": selected.get("id"), "label": selected.get("label"),
                "operation": selected.get("operation"),
                "selected_at": dt.datetime.now().isoformat(),
            })
            message = _guided_directive(selected)
        else:
            message = display_message
        self.current_data_question = str(message or "")[:8000]
        self.algebra_planner_calls = 0
        self.algebra_plans = []
        self.active_algebra_plan = None
        self._save()
        return message, selected

    def algebra_plan_feedback(self) -> list[dict]:
        """Return compact server-owned outcomes from earlier 9B plans in this turn."""
        feedback = []
        for plan in self.algebra_plans[-MAX_ALGEBRA_PASSES:]:
            feedback.append({
                "plan_id": plan.get("plan_id"), "pass": plan.get("pass"),
                "steps": [{
                    "skill": step.get("skill"), "args": step.get("args"),
                    "purpose": step.get("purpose"), "status": step.get("status"),
                    "execution_status": step.get("execution_status"),
                    "reason": step.get("reason"), "summary": step.get("summary"),
                } for step in plan.get("steps") or []],
            })
        return feedback

    def register_algebra_plan(self, plan: dict) -> None:
        if self.active_algebra_plan is not None:
            for step in self.active_algebra_plan.get("steps") or []:
                if step.get("status") == "pending":
                    step["status"] = "superseded"
        self.algebra_plans.append(plan)
        self.active_algebra_plan = plan
        self.append_audit({
            "type": "algebra_plan", "turn": self.turn,
            "plan_id": plan.get("plan_id"), "pass": plan.get("pass"),
            "planner": plan.get("planner"), "catalog_sha256": plan.get("catalog_sha256"),
            "user_update": plan.get("user_update"),
            "steps": [{key: step.get(key) for key in
                       ("step_id", "skill", "args", "purpose", "status")}
                      for step in plan.get("steps") or []],
        })

    def bind_scientific_skill_args(self, skill_id: str, supplied: dict) -> dict:
        """Keep outer evidence calls direct; constrain the one model-authored scientific input."""
        if skill_id == "compile-scientific-algebra-9b":
            return {
                "scientific_question": " ".join(str(
                    supplied.get("scientific_question") or supplied.get("question") or ""
                ).split())[:1600],
            }
        return _clean_plan_args(supplied)

    def complete_algebra_step(self, skill_id: str, result: dict,
                              error: str | None = None) -> None:
        plan = self.active_algebra_plan
        if not isinstance(plan, dict):
            return
        step = next((
            item for item in plan.get("steps") or []
            if item.get("skill") == skill_id and item.get("status") == "running"
        ), None)
        if not isinstance(step, dict):
            return
        if error:
            step.update({
                "status": "failed", "execution_status": "error",
                "reason": error[:500], "summary": error[:500],
                "completed_at": dt.datetime.now().isoformat(),
            })
        else:
            execution = result.get("execution") if isinstance(result, dict) else {}
            execution = execution if isinstance(execution, dict) else {}
            step.update({
                "status": "completed",
                "execution_status": execution.get("status") or "unknown",
                "reason": execution.get("reason"),
                "summary": _summary(result),
                "completed_at": dt.datetime.now().isoformat(),
            })
        self.append_audit({
            "type": "algebra_plan_step", "turn": self.turn,
            "plan_id": plan.get("plan_id"), "pass": plan.get("pass"),
            "step": {key: step.get(key) for key in (
                "step_id", "skill", "args", "purpose", "status",
                "execution_status", "reason", "summary")},
        })

    def bind_guided_skill_args(self, skill_id: str, supplied: dict) -> dict:
        """Apply controller-owned arguments for an explicitly selected action."""
        action = self.guided_action
        if not action:
            return supplied
        if skill_id == "compile-scientific-algebra-9b":
            return supplied
        if self.guided_allowed_skills is not None and skill_id not in self.guided_allowed_skills:
            raise PermissionError(
                f"guided action {action.get('operation')} does not authorize {skill_id}")
        bound = dict(action.get("args") or {})
        entity = str(bound.get("entity") or "").strip()
        operation = str(action.get("operation") or "")
        if operation == "search_wider_evidence":
            return {
                "query": " ".join(
                    x for x in [str(bound.get("query") or entity),
                                str(bound.get("region") or "")] if x),
                "limit": 8,
            }
        if operation == "search_wider_occurrences":
            return {"entity": entity, "region": bound.get("region") or "dry-Deccan donor belt"}
        if operation in {"show_observed_map", "build_model_map"}:
            entities = bound.get("entities") or ([entity] if entity else [])
            return {
                "entities": entities, "region": bound.get("region") or "EBTL",
                "source_region": bound.get("source_region") or bound.get("region") or "EBTL",
                "map_mode": "observed" if operation == "show_observed_map" else "modelled",
            }
        if operation == "test_transfer":
            return {
                "entity": entity,
                "donor_region": bound.get("donor_region") or "dry-Deccan donor belt",
                "target": bound.get("target") or "EBTL",
            }
        if operation in {"inspect_dataset", "build_protocol"}:
            return bound
        if operation in {
            "explore_site_wildlife", "explore_site_vegetation", "explore_site_fire",
        }:
            return {"region": bound.get("region") or "EBTL"}
        return supplied

    def record_skill_call(self, skill_id: str, args: dict, result: dict) -> None:
        self.turn_skill_calls.append({
            "skill": skill_id, "args": _redact_audit(args), "result": result,
        })

    def finish_guided_turn(self) -> dict | None:
        guidance = _derive_guidance(self)
        self.pending_guidance = guidance
        self.guided_action = None
        self.guided_allowed_skills = None
        if guidance:
            self.investigation_history.append({
                "state_id": guidance["state_id"], "offered_at": dt.datetime.now().isoformat(),
                "audit_id": guidance["audit_id"],
                "operations": [option["operation"] for option in guidance["options"]],
            })
        self._save()
        return guidance

    def store_result(self, kind: str, payload: dict) -> str:
        digest = _sha256({"session": self.id, "turn": self.turn, "kind": kind,
                          "payload": payload})[:18]
        result_id = f"{_safe_id(kind)}-{digest}"
        _atomic_json(self.results / f"{result_id}.json", {
            "schema": 1, "result_id": result_id, "kind": kind,
            "session_id": self.id, "turn": self.turn,
            "created_at": dt.datetime.now().isoformat(), "payload": payload,
        })
        return result_id

    def load_result(self, result_id: str) -> dict | None:
        safe = _safe_id(result_id)
        if safe != result_id or not safe:
            return None
        path = self.results / f"{safe}.json"
        if not path.is_file() or not _inside(self.results.resolve(), path.resolve()):
            return None
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return value if value.get("session_id") == self.id else None

    def append_audit(self, event: dict) -> None:
        event = _redact_audit({"at": dt.datetime.now().isoformat(), "session_id": self.id,
                               "turn": self.turn, **event})
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")


_SESSIONS: dict[str, Session] = {}
_SESSIONS_LOCK = threading.Lock()


def get_session(session_id: str) -> Session:
    key = _safe_id(session_id)
    with _SESSIONS_LOCK:
        if key not in _SESSIONS:
            _SESSIONS[key] = Session(key)
        return _SESSIONS[key]


def _stage_attachments(session: Session, manifest: Any) -> list[dict]:
    """Copy Idlisseus-authorized uploads into the bounded session input directory.

    Idlisseus performs the owner check before constructing the manifest. The bridge independently
    enforces that every source is a regular file beneath the configured upload root and never
    exposes the original host path to Codex.
    """
    if not isinstance(manifest, list):
        return session.attachments
    if len(manifest) > MAX_ATTACHMENTS:
        raise ValueError(f"at most {MAX_ATTACHMENTS} attachments are allowed")
    upload_root = UPLOAD_ROOT.resolve()
    target_root = session.input / "attachments"
    target_root.mkdir(parents=True, exist_ok=True)
    staged_by_id = {str(item.get("id")): item for item in session.attachments}
    for raw in manifest:
        if not isinstance(raw, dict):
            raise ValueError("attachment manifest entries must be objects")
        upload_id = str(raw.get("id") or "").strip()
        source_text = str(raw.get("path") or "").strip()
        if not upload_id or not source_text:
            raise ValueError("attachment id and path are required")
        source = pathlib.Path(source_text).resolve(strict=True)
        if not source.is_file() or not _inside(upload_root, source):
            raise ValueError(f"attachment {upload_id!r} is outside the upload root")
        size = source.stat().st_size
        if size > MAX_ATTACHMENT_BYTES:
            raise ValueError(f"attachment {upload_id!r} exceeds {MAX_ATTACHMENT_BYTES} bytes")
        fallback = _safe_display_name(source.name, "attachment")
        display_name = _safe_display_name(raw.get("name"), fallback)
        stored_name = f"{_safe_id(upload_id)[:48]}-{display_name}"
        target = target_root / stored_name
        shutil.copy2(source, target)
        staged_by_id[upload_id] = {
            "id": upload_id,
            "name": display_name,
            "mime": str(raw.get("mime") or "application/octet-stream")[:120],
            "size": size,
            "path": f"attachments/{stored_name}",
            "sha256": _sha256(target.read_bytes()),
        }
    session.attachments = list(staged_by_id.values())
    _atomic_json(session.input / "ATTACHMENTS.json", {
        "schema": 1, "session_id": session.id, "attachments": session.attachments,
    })
    session._save()
    return session.attachments


def _publish_report(session: Session, args: Any) -> dict:
    """Persist a bounded Idlisseus visual-report bundle for the current chat owner."""
    if not isinstance(args, dict):
        raise ValueError("report arguments must be an object")
    title = str(args.get("title") or "Idli insight report").strip()[:160]
    markdown = str(args.get("markdown") or "").strip()
    if not markdown:
        raise ValueError("report markdown is required")
    if len(markdown) > MAX_REPORT_CHARS:
        raise ValueError(f"report exceeds {MAX_REPORT_CHARS} characters")
    if not markdown.lstrip().startswith("#"):
        markdown = f"# {title}\n\n{markdown}"
    sources = []
    for raw in args.get("sources") or []:
        if not isinstance(raw, dict):
            continue
        url = str(raw.get("url") or "").strip()
        if url and not url.startswith(("https://", "http://")):
            continue
        sources.append({
            "url": url,
            "title": str(raw.get("title") or url or "Source")[:300],
        })
        if len(sources) >= 100:
            break
    report_id = _safe_id(f"idli-{session.id}-{session.turn}-{secrets.token_hex(4)}")
    now = time.time()
    bundle = {
        "query": title,
        "status": "done",
        "result": markdown,
        "raw_report": markdown,
        "sources": sources,
        "raw_findings": [],
        "stats": args.get("stats") if isinstance(args.get("stats"), dict) else {},
        "category": str(args.get("category") or "data")[:80],
        "started_at": now,
        "completed_at": now,
        "owner": session.owner,
        "codex_audit": {"session_id": session.id, "turn": session.turn},
    }
    _atomic_json(RESEARCH_ROOT / f"{report_id}.json", bundle)
    result = {
        "report_id": report_id,
        "url": REPORT_URL_PREFIX + report_id,
        "audit_id": f"{session.id}/{session.turn}",
    }
    session.append_audit({"type": "report_published", **result})
    return result


def _native_prompt(message: str, session: Session) -> str:
    input_root = (
        CONTAINER_ROOT / "sessions" / session.id / "input"
        if RUNNER == "hermes-exec" else session.input
    )
    attachment_note = ""
    if session.attachments:
        attachment_lines = [
            f"- {item['name']}: {input_root / item['path']} ({item['mime']}, {item['size']} bytes)"
            for item in session.attachments
        ]
        attachment_note = (
            "\n\nAuthorized attachments available in this session:\n" +
            "\n".join(attachment_lines) +
            "\nInspect the raw attached files when the question depends on them."
        )
    normalised_message = " ".join(message.casefold().split())
    routing_note = ""
    site_aliases = [item.strip().casefold() for item in os.environ.get(
        "CODEX_NATIVE_SITE_ALIASES", "EBTL|Elephants by the Lake").split("|") if item.strip()]
    mentions_site = any(alias in normalised_message for alias in site_aliases)
    broad_site_request = bool(re.fullmatch(
        r"(?:please )?(?:tell me about|describe|give me an overview of|"
        r"give me a summary of|what is|what do we know about) "
        r"(?:the |this |our )?(?:site|property|aoi|ebtl|elephants by the lake)[?.! ]*",
        normalised_message))
    asks_external = bool(re.search(
        r"\b(literature|papers?|public datasets?|external sources?|openalex|zenodo|dryad)\b",
        normalised_message))
    requested_map_mode = _map_intent(message)
    if requested_map_mode and not getattr(session, "guided_action", None):
        routing_note = (
            "\n\nROUTING REQUIREMENT: The user explicitly requested a map. Discover or retrieve "
            "the relevant admitted evidence first. If a scientific estimate is required, state "
            "one precise scientific question and invoke `compile-scientific-algebra-9b`. Then use "
            f"`build-ecology-field-map` in `{requested_map_mode}` mode with the returned evidence. "
            "If a fine-scale model gate fails, return the labelled observation or field-check "
            "points and map link. Do not substitute prose instructions for the requested map."
        )
    elif broad_site_request and not getattr(session, "guided_action", None):
        routing_note = (
            "\n\nROUTING REQUIREMENT: This is a broad site-overview request. Invoke "
            "`site-overview` directly. Do not invoke scientific Algebra unless the user then asks "
            "a measurable ecological question. Do not turn words in the organisation or site "
            "name into a taxon search, and do not use external literature as a substitute for the "
            "onboarded site profile."
        )
    elif mentions_site and not asks_external and not getattr(session, "guided_action", None):
        routing_note = (
            "\n\nROUTING REQUIREMENT: This is a local-site question. Begin with "
            "`local-site-evidence-search` for the focal entity or topic. A local registry "
            "non-match is not proof of absence. Offer a concise clarification or wider search "
            "when that is the most useful next step; invoke scientific Algebra only once there "
            "is an explicit scientific question to compute."
        )
    compiler = SKILLS_BY_ID["compile-scientific-algebra-9b"]
    invocation_root = (
        CONTAINER_ROOT / "sessions" / session.id / "input"
        if RUNNER == "hermes-exec" else session.input
    )
    compiler_skill_path = invocation_root / "skills" / compiler["id"] / "SKILL.md"
    compiler_command = (
        f"python3 {invocation_root / 'skill_call.py'} {compiler['id']} "
        '--pairs scientific_question="State one precise evidence-bound scientific question here"'
    )
    return (
        "You are helping staff at a conservation NGO. Use short, direct Indian English. This is "
        "a guided, evidence-bound investigation. Keep each answer concise and ask one useful "
        "follow-up when the scientific scope is genuinely ambiguous.\n\n"
        "OUTER DIALOGUE AND DISCOVERY. You own the conversation, clarification, site orientation "
        "and evidence discovery. You may give 2-4 sentences of general ecological background from "
        "model knowledge. Present it naturally as `General ecological context:` rather than using "
        "square-bracket labels. When a native web-search tool is actually available, you may use "
        "it and cite exact URLs; never invent a search result. General knowledge may suggest "
        "untrusted query seeds, but it is not site evidence and cannot fill a data gap. Use the "
        "candidate + focal entity + relation as the discovery query when testing a proposed "
        "ecological link, and do not promote it unless a returned source supports that "
        "link. Use the "
        "command-backed ecology skills for onboarded assets and connectors. Read only a relevant "
        "skill's SKILL.md, invoke it through the supplied Python wrapper, and briefly tell the user "
        "what evidence is being checked. Do not list skill directories or inspect skill_call.py.\n\n"
        "SCIENTIFIC ALGEBRA. The local 9B model is a scientific compiler, not a skill planner. Do "
        "not give it a skill list and do not ask it to choose connectors. First use admitted local "
        "or public evidence to establish the entity, region, layer or comparison when needed. "
        "Then, for an explicit state, relationship, trend, comparison, ranking or transfer "
        "calculation, formulate one short scientific question and invoke "
        "`compile-scientific-algebra-9b`. Pass only `scientific_question`. The server gives 9B the "
        "frozen Algebra grammar and admitted resource symbols; 9B emits the Algebra, while the "
        "controller validates, binds and executes it. Never author, rewrite, repair or silently "
        "replace the Algebra yourself. If the compiled result exposes a hole or data request, ask "
        "the corresponding short clarification. You may invoke the compiler again after new "
        "evidence or clarification, up to three times. Do not invoke it for a broad site overview, "
        "a literature-only question, or simple source inspection.\n\n"
        "FINAL FORMAT. Use short descriptive headings only where helpful. Say `From the onboarded "
        "site records, ...`, `From public occurrence data, ...`, `The modelled estimate suggests "
        "...`, or `The remaining data gap is ...`; never prefix claims with bracketed provenance "
        "tags. Keep observations, reports, search leads, proxies, estimates and designed field "
        "points distinct. Include returned map or protocol links, never local paths. Do not call "
        "a SELECT occurrence search modelled; reserve `modelled` for an executed ESTIMATE. When "
        "a shell argument contains an apostrophe, use the documented `--pairs` form instead of "
        "single-quoted JSON. Do not "
        "manually reproduce the scientific question, Algebra 9B response, raw IR or bound "
        "execution: the controller appends those in a consistent, auditable scientific-analysis "
        "panel after your concise answer. Do not mention internal model identifiers. Do not add a "
        "prose menu; the controller renders valid next actions as buttons. Never read credentials "
        "or environment files." +
        routing_note +
        "\n\nOPTIONAL SCIENTIFIC COMPILER:\n- " + compiler["id"] + ": " +
        compiler["description"] +
        "\n- Compiler instructions: " + str(compiler_skill_path) +
        "\n- Example invocation (only when scientific computation is needed): `" +
        compiler_command + "`" +
        attachment_note +
        "\n\nUSER:\n" + message
    )


def _command_kind(command: str) -> tuple[str, str]:
    if "publish_report.py" in command:
        return "skill", "publish-report"
    match = SKILL_COMMAND.search(command)
    if match:
        return "skill", match.group(1)
    match = READ_SKILL.search(command)
    if match:
        return "read_skill", match.group(1)
    if "SKILLS_INDEX.md" in command or "/skills" in command and "find " in command:
        return "discover_skills", "skill index"
    if "python" in command:
        return "calculation", "transparent calculation"
    return "command", "inspection"


def _audit_from_codex(event: dict) -> list[dict]:
    item = event.get("item") or {}
    item_type = item.get("type")
    status = item.get("status")
    if event.get("type") == "thread.started":
        return [{"type": "thread", "thread_id": event.get("thread_id")}]
    if item_type == "command_execution":
        command = item.get("command") or ""
        kind, label = _command_kind(command)
        if event.get("type") == "item.started":
            return [{"type": "tool_start", "kind": kind, "tool": label,
                     "command": command}]
        if event.get("type") == "item.completed" or status in {"completed", "failed"}:
            output = item.get("aggregated_output") or ""
            compact = output.strip()
            if kind == "skill":
                with contextlib.suppress(Exception):
                    compact = _summary(json.loads(compact))
            if len(compact) > 800:
                compact = compact[:797] + "..."
            return [{"type": "tool_output", "kind": kind, "tool": label,
                     "command": command, "output": compact,
                     "exit_code": item.get("exit_code")}]
    if item_type == "agent_message" and event.get("type") == "item.completed":
        return [{"type": "agent_message", "text": item.get("text") or ""}]
    if event.get("type") == "turn.completed":
        return [{"type": "usage", "usage": event.get("usage") or {}}]
    if event.get("type") == "turn.failed":
        return [{"type": "error", "error": event.get("error") or "Codex turn failed"}]
    return []


def _prepare_hermes_session(session: Session) -> tuple[str, str, str, str]:
    """Copy one bounded session into the already-running Hermes container.

    Repository policy forbids starting or restarting containers, so this runner uses ``docker
    exec``. Codex runs as uid/gid 65534, which cannot traverse the Hermes data mount; its private
    state is confined to a uniquely named directory below /tmp.
    """
    root = CONTAINER_ROOT / "sessions" / session.id
    home = str(root / "home")
    work = str(root / "work")
    input_root = str(root / "input")
    output = str(root / "output")
    binary = str(CONTAINER_ROOT / "bin" / "codex")
    subprocess.run([
        "docker", "exec", "-u", "0:0", HERMES_CONTAINER, "sh", "-lc",
        "mkdir -p /tmp/codex-native/bin "
        f"{home} {work} {input_root} {output} && "
        f"rm -rf {input_root} && mkdir -p {input_root}",
    ], check=True, capture_output=True, text=True)
    subprocess.run(["docker", "cp", str(CODEX), f"{HERMES_CONTAINER}:{binary}"],
                   check=True, capture_output=True, text=True)
    subprocess.run(["docker", "cp", str(session.input) + "/.",
                    f"{HERMES_CONTAINER}:{input_root}"],
                   check=True, capture_output=True, text=True)
    subprocess.run(["docker", "cp", str(session.home / "auth.json"),
                    f"{HERMES_CONTAINER}:{home}/auth.json"],
                   check=True, capture_output=True, text=True)
    subprocess.run([
        "docker", "exec", "-u", "0:0", HERMES_CONTAINER, "sh", "-lc",
        f"chmod 755 {binary} && chown -R 65534:65534 {root} && chmod 700 {home}",
    ], check=True, capture_output=True, text=True)
    return home, work, output, binary


def _execution_plain_text(execution: dict) -> str:
    status = str(execution.get("status") or "unknown")
    if status == "answer":
        value = execution.get("value") if isinstance(execution.get("value"), dict) else {}
        kind = str(value.get("kind") or "result")
        rows = value.get("rows") if isinstance(value.get("rows"), list) else None
        source = str(value.get("source") or "").strip()
        label = str(execution.get("label") or value.get("label") or "").strip()
        if rows is not None:
            text = f"Execution returned {len(rows)} {kind} row{'s' if len(rows) != 1 else ''}"
        elif "value" in value:
            text = f"Execution returned {value.get('value')}"
        else:
            text = "Execution completed"
        qualifiers = [item for item in (label, source) if item]
        return text + (f" ({'; '.join(qualifiers)})." if qualifiers else ".")
    reason = str(execution.get("reason") or status).replace("_", " ")
    detail = execution.get("detail") if isinstance(execution.get("detail"), dict) else {}
    ask = str(detail.get("ask") or "").strip()
    if execution.get("reason") == "empty_select":
        return (
            "The bound occurrence search returned no records in the selected region. "
            "This is a data gap, not evidence of absence."
        )
    return (
        f"Execution stopped with {reason}." +
        (f" The next required input is: {ask}." if ask else "")
    )


def _scientific_response_block(session: Session) -> str:
    calls = [
        call for call in session.turn_skill_calls
        if call.get("skill") == "compile-scientific-algebra-9b"
    ]
    if not calls:
        return ""
    sections = []
    for call in calls[-2:]:
        result = call.get("result") if isinstance(call.get("result"), dict) else {}
        outer = result.get("execution") if isinstance(result.get("execution"), dict) else {}
        value = outer.get("value") if isinstance(outer.get("value"), dict) else {}
        question = str(
            value.get("scientific_question") or result.get("scientific_question") or
            (call.get("args") or {}).get("scientific_question") or ""
        ).strip()
        ir = value.get("ir") if isinstance(value.get("ir"), dict) else (
            (result.get("algebra") or {}).get("ir")
            if isinstance(result.get("algebra"), dict) else None
        )
        actual = value.get("execution") if isinstance(value.get("execution"), dict) else outer
        human = str(value.get("human_reading") or (
            _format_ir_human(ir) if isinstance(ir, dict) else "No valid Algebra tree was returned."
        ))
        raw = json.dumps(ir, indent=2, ensure_ascii=False) if isinstance(ir, dict) else "{}"
        sections.append(
            "**Scientific question sent to 9B**\n\n"
            f"> {question or 'No scientific question was supplied.'}\n\n"
            "**How 9B expressed the question scientifically**\n\n"
            f"{human}.\n\n"
            "**What Idli Insight executed**\n\n" + _execution_plain_text(actual) +
            "\n\n<details><summary>Audit the exact compiled Algebra</summary>\n\n"
            "```json\n" + raw + "\n```\n\n</details>"
        )
    return "\n\n### Scientific analysis\n\n" + "\n\n---\n\n".join(sections)


def _replace_provenance_brackets(text: str) -> str:
    replacements = {
        "Model background": "General ecological context:",
        "Web": "From the web:",
        "Local asset": "From local records:",
        "Public connector": "From public data:",
        "Modelled": "Modelled result:",
        "Designed": "Survey design:",
        "Data gap": "What is still unknown:",
    }
    for label, replacement in replacements.items():
        text = re.sub(
            rf"(?m)^(\s*(?:[-*]\s+)?)\[{re.escape(label)}\]\s*",
            rf"\1{replacement} ", text,
        )
    return text


def run_turn(session: Session, message: str, emit: Callable[[dict], None]) -> dict:
    with session.lock:
        display_message = message
        message, selected_action = session.begin_turn(display_message)
        session.turn_skill_calls = []
        session.turn += 1
        turn = session.turn
        prompt = _native_prompt(message, session)
        final_path = session.output / f"{turn:04d}-final.txt"
        env = os.environ.copy()
        env.update({
            "HOME": str(session.home), "CODEX_HOME": str(session.home),
            "POINTS_CACHE": str(STATE_ROOT / "cache" / "points"),
            "DISCOVERY_CACHE": str(STATE_ROOT / "cache" / "discovery"),
        })
        corpus = os.environ.get("CODEX_NATIVE_CORPUS", "").strip()
        if corpus:
            env["CORPUS_CARDS"] = corpus
        container_final: str | None = None
        if RUNNER == "hermes-exec":
            home, work, output, binary = _prepare_hermes_session(session)
            container_final = f"{output}/{final_path.name}"
            base = [
                "docker", "exec", "-i", "-u", "65534:65534",
                "-e", f"HOME={home}", "-e", f"CODEX_HOME={home}",
                "-w", work, HERMES_CONTAINER, binary, "exec",
            ]
            requested_sandbox = "container-boundary"
        else:
            base = [str(CODEX), "exec"]
            requested_sandbox = SANDBOX
        common = ["--json", "-m", MODEL, "-c", f'model_reasoning_effort="{REASONING}"',
                  "--ignore-user-config", "--ignore-rules", "--skip-git-repo-check",
                  "-o", container_final or str(final_path)]
        if RUNNER == "hermes-exec":
            common.append("--dangerously-bypass-approvals-and-sandbox")
        elif SANDBOX == "dangerously-bypass":
            common.append("--dangerously-bypass-approvals-and-sandbox")
        else:
            common.extend(["-s", SANDBOX])
        if session.thread_id:
            # ``exec resume`` has a smaller option surface than ``exec``: the working directory is
            # inherited from docker exec / Popen, and options must precede the session id.
            command = base + ["resume"] + common + [session.thread_id, "-"]
        else:
            command = base + common + ["-C", work if RUNNER == "hermes-exec"
                                        else str(session.work), "-"]
        request = {
            "type": "request", "turn": turn, "message": display_message,
            "resolved_message": message if selected_action else None,
            "guided_action": selected_action,
            "model": MODEL,
            "reasoning": REASONING, "prompt_sha256": _sha256(prompt),
            "skills_sha256": _sha256(SKILLS), "sandbox": requested_sandbox,
            "runner": RUNNER,
        }
        session.append_audit(request)
        emit({"type": "turn_start", "turn": turn, "model": MODEL,
              "reasoning": REASONING, "audit_path": str(session.audit_path)})
        started = time.time()
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, bufsize=1, env=env,
        )
        assert process.stdin is not None and process.stdout is not None
        process.stdin.write(prompt)
        process.stdin.close()
        pending_message: str | None = None
        usage: dict = {}
        for raw_line in process.stdout:
            clean = ANSI.sub("", raw_line).replace("\r", "")
            with session.raw_path.open("a", encoding="utf-8") as raw_stream:
                raw_stream.write(clean)
            try:
                event = json.loads(clean)
            except json.JSONDecodeError:
                continue
            for audit in _audit_from_codex(event):
                if audit["type"] == "thread":
                    session.thread_id = audit.get("thread_id") or session.thread_id
                    session._save()
                    continue
                if audit["type"] == "agent_message":
                    if pending_message:
                        status_event = {"type": "status", "text": pending_message}
                        session.append_audit(status_event)
                        emit(status_event)
                    pending_message = audit.get("text") or ""
                    continue
                if pending_message:
                    status_event = {"type": "status", "text": pending_message}
                    session.append_audit(status_event)
                    emit(status_event)
                    pending_message = None
                if audit["type"] == "usage":
                    usage = audit.get("usage") or {}
                session.append_audit(audit)
                emit(audit)
        stderr = process.stderr.read() if process.stderr is not None else ""
        return_code = process.wait()
        if container_final:
            copied = subprocess.run([
                "docker", "cp", f"{HERMES_CONTAINER}:{container_final}", str(final_path)
            ], capture_output=True, text=True)
            if copied.returncode != 0 and return_code == 0:
                stderr += "\nCould not copy final answer: " + copied.stderr
        final = final_path.read_text().strip() if final_path.exists() else (pending_message or "")
        final = _replace_provenance_brackets(final)
        scientific_block = _scientific_response_block(session)
        if scientific_block and "### Scientific analysis" not in final:
            final = final.rstrip() + scientific_block
        elapsed = round(time.time() - started, 3)
        if return_code != 0:
            error = {"type": "error", "error": stderr.strip()[-1000:] or
                     f"Codex exited {return_code}", "exit_code": return_code}
            session.append_audit(error)
            emit(error)
        guidance = session.finish_guided_turn()
        if guidance:
            guidance_event = {"type": "insight_actions", **guidance}
            session.append_audit(guidance_event)
            emit(guidance_event)
        result = {
            "type": "final", "answer": final, "thread_id": session.thread_id,
            "session_id": session.id, "turn": turn, "usage": usage,
            "latency_s": elapsed, "exit_code": return_code,
            "audit_path": str(session.audit_path), "insight_actions": guidance,
        }
        session.append_audit(result)
        session._save()
        emit(result)
        return result


def _trace_markdown(event: dict) -> str:
    event_type = event.get("type")
    if event_type == "turn_start":
        return (
            "<details open><summary>Codex CLI · native skill trace</summary>\n\n"
            f"`{event.get('model')}` · reasoning `{event.get('reasoning')}`\n\n"
        )
    if event_type == "status":
        return f"- **Codex:** {event.get('text', '').strip()}\n"
    if event_type == "tool_start":
        kind = event.get("kind")
        if kind == "skill":
            return f"- **Invoke skill:** `{event.get('tool')}`\n"
        if kind == "read_skill":
            return f"- **Read skill:** `{event.get('tool')}`\n"
        if kind == "discover_skills":
            return "- **Discover skills:** inspect the frozen skill index\n"
        if kind == "calculation":
            return "- **Calculate:** transparent Python check\n"
        return "- **Inspect:** bounded session input\n"
    if event_type == "tool_output":
        output = str(event.get("output") or "").strip()
        if output:
            safe_output = output.replace("`", "'")
            return f"  - Result: `{safe_output}`\n"
    if event_type == "error":
        return f"- **Error:** {event.get('error')}\n"
    if event_type == "final":
        return (
            f"\nAudit id: `{event.get('session_id')}/{event.get('turn')}` · "
            f"{event.get('latency_s')}s\n\n</details>\n\n{event.get('answer', '')}"
        )
    return ""


def _idlisseus_event(event: dict, session: Session) -> dict | None:
    """Reduce the private Codex trace to the small audit surface the chat needs.

    Full commands, outputs, skill reads, discovery and progress commentary stay in the JSONL
    audit.  The browser receives only actual skill invocations, their terminal state and the
    stable audit id.  This keeps the answer readable without making skill use invisible.
    """
    event_type = event.get("type")
    if event_type == "insight_actions":
        options = []
        for option in (event.get("options") or [])[:3]:
            if not isinstance(option, dict):
                continue
            label = " ".join(str(option.get("label") or "").split())[:60]
            if not label:
                continue
            options.append({
                "id": str(option.get("id") or "")[:80],
                "label": label,
                "description": " ".join(
                    str(option.get("description") or "").split())[:180],
            })
        if len(options) < 1:
            return None
        return {
            "type": "insight_actions",
            "state_id": str(event.get("state_id") or "")[:80],
            "audit_id": str(event.get("audit_id") or "")[:160],
            "question": " ".join(str(event.get("question") or
                                        "What should I do next?").split())[:180],
            "options": options, "multi": False,
        }
    if event_type == "turn_start":
        return {"type": "insight_progress", "phase": "select",
                "label": "Selecting skills"}
    if event_type == "tool_start" and event.get("kind") == "discover_skills":
        return {"type": "insight_progress", "phase": "select",
                "label": "Checking available skills"}
    if event_type == "tool_start" and event.get("kind") == "read_skill":
        skill = str(event.get("tool") or "").strip()
        if skill:
            return {"type": "insight_progress", "phase": "read",
                    "label": f"Reading {skill}"}
    if event_type not in {"tool_start", "tool_output"} or event.get("kind") != "skill":
        return None
    skill = str(event.get("tool") or "").strip()
    if not skill:
        return None
    browser_event = {
        "type": "insight_skill",
        "skill": skill,
        "status": "running" if event_type == "tool_start" else "done",
        "audit_id": f"{session.id}/{session.turn}",
    }
    if event_type == "tool_output" and event.get("exit_code") not in {0, None}:
        browser_event["status"] = "failed"
    if event_type == "tool_output" and event.get("output"):
        browser_event["summary"] = " ".join(str(event["output"]).split())[:500]
    return browser_event


def _compat_skill_marker(event: dict, session: Session) -> str:
    """Invisible content marker for Idlisseus builds without native event forwarding."""
    browser_event = _idlisseus_event(event, session)
    if not browser_event or browser_event.get("type") != "insight_skill":
        return ""
    payload = {
        "skill": browser_event["skill"], "status": browser_event["status"],
        "audit_id": browser_event["audit_id"],
    }
    if browser_event.get("summary"):
        payload["summary"] = browser_event["summary"]
    return "<!--idli-skill:" + json.dumps(payload, separators=(",", ":")) + "-->"


def _compat_progress_marker(event: dict, session: Session) -> str:
    """Invisible safe-milestone marker for older Idlisseus transports."""
    browser_event = _idlisseus_event(event, session)
    if not browser_event or browser_event.get("type") != "insight_progress":
        return ""
    payload = {"phase": browser_event["phase"], "label": browser_event["label"]}
    return "<!--idli-progress:" + json.dumps(payload, separators=(",", ":")) + "-->"


def _compat_actions_marker(event: dict, session: Session | None) -> str:
    """Invisible guided-choice marker for older Idlisseus transports."""
    browser_event = _idlisseus_event(event, session)
    if not browser_event or browser_event.get("type") != "insight_actions":
        return ""
    return "<!--idli-actions:" + json.dumps(
        {key: browser_event[key] for key in (
            "state_id", "audit_id", "question", "options", "multi")},
        separators=(",", ":"),
    ) + "-->"


def _compact_compat_answer(final_event: dict, events: list[dict]) -> str:
    """Embed an invisible audit envelope for older OpenAI-compatible clients.

    New Idlisseus builds consume ``insight_skill`` events. Older builds ignore custom SSE events,
    so they receive a small HTML comment instead. An updated frontend lifts it into the same
    native panel; an older frontend renders only the answer, never literal trace markup.
    """
    answer = str(final_event.get("answer") or "")
    skills: list[str] = []
    for event in events:
        if event.get("type") not in {"tool_start", "tool_output"}:
            continue
        if event.get("kind") != "skill":
            continue
        name = str(event.get("tool") or "").strip()
        if name and name not in skills:
            skills.append(name)
    actions_marker = next((
        _compat_actions_marker(event, None)
        for event in reversed(events) if event.get("type") == "insight_actions"
    ), "")
    audit_id = f"{final_event.get('session_id')}/{final_event.get('turn')}"
    skill_marker = ""
    if skills:
        envelope = json.dumps({"skills": skills, "audit_id": audit_id}, separators=(",", ":"))
        skill_marker = f"<!--idli-insight:{envelope}-->"
    markers = "\n".join(marker for marker in (skill_marker, actions_marker) if marker)
    return f"{markers}\n{answer}".strip() if markers else answer


def _answer_with_actions_marker(final_event: dict, events: list[dict],
                                session: Session | None) -> str:
    """Keep guided actions usable through Idlisseus builds that drop custom SSE events.

    Native Idlisseus transports receive ``insight_actions`` while a turn is running.
    Some deployed route versions do not forward that event, however, so the final
    answer also carries the safe public action envelope. Updated frontends lift the
    comment into the same action card and remove it from the visible answer.
    """
    answer = str(final_event.get("answer") or "")
    actions_marker = next((
        _compat_actions_marker(event, session)
        for event in reversed(events) if event.get("type") == "insight_actions"
    ), "")
    return f"{actions_marker}\n{answer}".strip() if actions_marker else answer


SERVER_PORT = int(os.environ.get("CODEX_NATIVE_PORT", "7011"))


class Handler(http.server.BaseHTTPRequestHandler):
    server_version = "CodexNativeSkills/0.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))

    def _json_body(self) -> dict:
        length = int(self.headers.get("Content-Length") or "0")
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValueError("invalid request size")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("JSON object required")
        return payload

    def _authorized(self, internal_token: str | None = None) -> bool:
        expected = internal_token if internal_token is not None else API_TOKEN
        if not expected:
            return self.client_address[0] in {"127.0.0.1", "::1"}
        return self.headers.get("Authorization") == "Bearer " + expected

    def _send_json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _sse(self, payload: Any) -> None:
        raw = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, default=str)
        self.wfile.write(f"data: {raw}\n\n".encode())
        self.wfile.flush()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path in {"/health", "/v1/models"}:
            if parsed.path == "/health":
                self._send_json(200, {"status": "ok", "model": MODEL,
                                      "skills": len(SKILLS), "codex": str(CODEX),
                                      "runner": RUNNER, "container": HERMES_CONTAINER})
            else:
                if not self._authorized():
                    self._send_json(401, {"error": {"message": "unauthorized"}})
                    return
                self._send_json(200, {"object": "list", "data": [{
                    "id": PUBLIC_MODEL, "object": "model",
                    "owned_by": "idli", "actual_model": MODEL,
                }]})
            return
        if parsed.path.startswith("/v1/audit/"):
            if not self._authorized():
                self._send_json(401, {"error": "unauthorized"})
                return
            audit_parts = [urllib.parse.unquote(part) for part in
                           parsed.path[len("/v1/audit/"):].strip("/").split("/") if part]
            if not audit_parts or len(audit_parts) > 2:
                self._send_json(400, {"error": "audit id must be session-id or session-id/turn"})
                return
            session_id = _safe_id(audit_parts[0])
            requested_turn = None
            if len(audit_parts) == 2:
                try:
                    requested_turn = int(audit_parts[1])
                except ValueError:
                    self._send_json(400, {"error": "audit turn must be an integer"})
                    return
            session = get_session(session_id)
            rows = []
            if session.audit_path.exists():
                for line in session.audit_path.read_text().splitlines():
                    with contextlib.suppress(json.JSONDecodeError):
                        event = json.loads(line)
                        if requested_turn is None or event.get("turn") == requested_turn:
                            rows.append(_redact_audit(event))
            self._send_json(200, {"session_id": session_id, "turn": requested_turn,
                                  "events": rows,
                                  "audit_path": str(session.audit_path)})
            return
        self._send_json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        try:
            body = self._json_body()
        except Exception as exc:
            self._send_json(400, {"error": str(exc)})
            return
        if parsed.path == "/internal/skill-call":
            session = get_session(str(body.get("session") or ""))
            if not self._authorized(session.gateway_token):
                self._send_json(403, {"error": "unauthorized"})
                return
            try:
                skill_id = str(body.get("skill") or "")
                args = body.get("args") if isinstance(body.get("args"), dict) else {}
                args = session.bind_guided_skill_args(skill_id, args)
                args = session.bind_scientific_skill_args(skill_id, args)
                result = _execute_skill(skill_id, args, session)
                session.record_skill_call(skill_id, args, result)
                session.append_audit({"type": "skill_call", "skill": skill_id,
                                      "args": args, "result": result})
                self._send_json(200, result)
            except Exception as exc:
                session.append_audit({"type": "skill_error", "skill": body.get("skill"),
                                      "error": f"{type(exc).__name__}: {exc}"})
                self._send_json(400, {"error": f"{type(exc).__name__}: {exc}"})
            return
        if parsed.path == "/internal/publish-report":
            session = get_session(str(body.get("session") or ""))
            if not self._authorized(session.gateway_token):
                self._send_json(403, {"error": "unauthorized"})
                return
            try:
                self._send_json(200, _publish_report(session, body.get("args")))
            except Exception as exc:
                session.append_audit({"type": "report_error",
                                      "error": f"{type(exc).__name__}: {exc}"})
                self._send_json(400, {"error": f"{type(exc).__name__}: {exc}"})
            return
        if parsed.path not in {"/v1/chat/completions", "/v1/audit/chat"}:
            self._send_json(404, {"error": "not found"})
            return
        if not self._authorized():
            self._send_json(401, {"error": {"message": "unauthorized"}})
            return
        messages = body.get("messages") if isinstance(body.get("messages"), list) else []
        message = ""
        for item in reversed(messages):
            if item.get("role") == "user":
                content = item.get("content")
                message = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
                break
        message = str(body.get("message") or message).strip()
        if not message:
            self._send_json(400, {"error": {"message": "user message required"}})
            return
        session_id = _safe_id(str(body.get("session_id") or body.get("session") or ""))
        session = get_session(session_id)
        idlisseus_context = body.get("idlisseus_context")
        native_browser_events = isinstance(idlisseus_context, dict)
        if isinstance(idlisseus_context, dict):
            context_session = str(idlisseus_context.get("session_id") or "").strip()
            if context_session and _safe_id(context_session) != session.id:
                self._send_json(400, {"error": {"message": "session context mismatch"}})
                return
            session.owner = str(idlisseus_context.get("owner") or "")[:200]
        try:
            _stage_attachments(session, body.get("attachments"))
        except Exception as exc:
            self._send_json(400, {"error": {"message": f"Invalid attachments: {exc}"}})
            return
        session._save()
        structured = parsed.path == "/v1/audit/chat"
        stream = bool(body.get("stream")) or structured
        events: list[dict] = []
        if stream:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            def emit(event: dict) -> None:
                events.append(event)
                if structured:
                    self._sse(event)
                    return
                event_type = event.get("type")
                if event_type == "final":
                    delta = (
                        _answer_with_actions_marker(event, events, session)
                        if native_browser_events
                        else _compact_compat_answer(event, events)
                    )
                    if not delta:
                        return
                    chunk = {
                        "id": f"chatcmpl-{session.id}", "object": "chat.completion.chunk",
                        "model": PUBLIC_MODEL,
                        "choices": [{"index": 0, "delta": {"content": delta},
                                     "finish_reason": None}],
                    }
                    self._sse(chunk)
                    return
                browser_event = _idlisseus_event(event, session) if native_browser_events else None
                if browser_event:
                    self._sse({"id": f"chatcmpl-{session.id}",
                               "object": "chat.completion.chunk", "model": PUBLIC_MODEL,
                               "choices": [], "idlisseus_event": browser_event})
                    return
                if not native_browser_events:
                    marker = (_compat_skill_marker(event, session)
                              or _compat_progress_marker(event, session)
                              or _compat_actions_marker(event, session))
                    if marker:
                        self._sse({
                            "id": f"chatcmpl-{session.id}",
                            "object": "chat.completion.chunk",
                            "model": PUBLIC_MODEL,
                            "choices": [{"index": 0, "delta": {"content": marker},
                                         "finish_reason": None}],
                        })

            try:
                result = run_turn(session, message, emit)
                if structured:
                    self._sse("[DONE]")
                else:
                    self._sse({
                        "id": f"chatcmpl-{session.id}", "object": "chat.completion.chunk",
                        "model": PUBLIC_MODEL,
                        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                        "usage": result.get("usage") or {},
                    })
                    self._sse("[DONE]")
            except (BrokenPipeError, ConnectionResetError):
                return
            except Exception as exc:
                error = {"type": "error", "error": f"{type(exc).__name__}: {exc}"}
                with contextlib.suppress(Exception):
                    self._sse(error if structured else {
                        "error": {"message": error["error"], "type": "bridge_error"}
                    })
            return
        try:
            result = run_turn(session, message, events.append)
        except Exception as exc:
            self._send_json(500, {"error": {"message": f"{type(exc).__name__}: {exc}"}})
            return
        self._send_json(200, {
            "id": f"chatcmpl-{session.id}", "object": "chat.completion",
            "model": PUBLIC_MODEL,
            "choices": [{"index": 0, "message": {"role": "assistant",
                         "content": result.get("answer") or ""},
                         "finish_reason": "stop"}],
            "usage": result.get("usage") or {},
            "codex_audit": {"session_id": session.id, "turn": result.get("turn"),
                            "path": result.get("audit_path")},
        })


def main(argv: list[str] | None = None) -> int:
    global SERVER_PORT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default=os.environ.get("CODEX_NATIVE_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=SERVER_PORT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    if args.check:
        missing = [str(path) for path in (CODEX, AUTH_SOURCE, SKILLS_PATH) if not path.exists()]
        payload = {"ok": not missing, "missing": missing, "model": MODEL,
                   "reasoning": REASONING, "sandbox": SANDBOX, "skills": len(SKILLS),
                   "runner": RUNNER, "container": HERMES_CONTAINER,
                   "state_root": str(STATE_ROOT)}
        print(json.dumps(payload, indent=2))
        return 0 if not missing else 1
    SERVER_PORT = args.port
    STATE_ROOT.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer((args.host, args.port), Handler)
    print(json.dumps({"status": "listening", "host": args.host, "port": args.port,
                      "model": MODEL, "skills": len(SKILLS), "sandbox": SANDBOX,
                      "runner": RUNNER, "container": HERMES_CONTAINER}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
