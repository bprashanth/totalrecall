"""Deterministic ecology connectors used by the frozen place-memory algebra.

The imported origin had useful production connectors but heterogeneous return types and lossy
CSV hand-offs.  This module keeps the benchmark self-contained and normalizes every admitted
source to ``rows/kind/source/note/label`` while retaining record URL, time, quality and license.

Source families currently admitted:
  - GBIF + iNaturalist -> licensed taxon occurrence records
  - eBird              -> recent bird observations (API-key connector; bbox post-filtered)
  - Earth Engine       -> MODIS NDVI series and point raster annotations
  - Zenodo 10077040    -> the published Anamalai vegetation *survey* sites
  - Nominatim          -> place name to bbox/centroid (REGION support)

Occurrence records establish documented presence, not abundance.  The executor uses the grain
and ``count_admissible`` metadata returned here to prevent record counts becoming animal counts.
"""
import csv
import calendar
import collections
import concurrent.futures
import datetime as dt
import json
import hashlib
import http.client
import math
import os
import time
import urllib.parse
import urllib.request
import urllib.error

import origin_adapters as ORIGIN

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "data")
DATA = os.path.join(HERE, "data")
os.makedirs(CACHE, exist_ok=True)

UA = "ecology-memory-algebra-benchmark/0.1 (research; contact prashanthseven@gmail.com)"

EBTL_ALIASES = {
    "ebtl", "elephants by the lake", "elephants by the lake (ebtl)",
    "ebtl analysis bbox", "our site", "the site", "restoration site",
}
EBTL_REGION = {
    "name": "Elephants by the Lake (EBTL), Chinnathamandrapalli, Krishnagiri, Tamil Nadu",
    "bbox": [12.721, 12.747, 78.170, 78.197],  # harness order: south, north, west, east
    "lat": 12.73394,
    "lon": 78.18344,
    "orig": "EBTL",
    "source": "SITE_EBTL.json",
}
DONOR_ALIASES = {
    "dry-deccan donor belt", "dry deccan donor belt", "ebtl donor belt",
    "eastern ghats donor belt", "regional donor belt",
}
DONOR_REGION = {
    "name": "dry-Deccan donor belt",
    "bbox": [11.0, 13.6, 76.0, 79.5],
    "lat": 12.3,
    "lon": 77.75,
    "orig": "dry-Deccan donor belt",
    "source": "declared-donor-belt",
}


def _cache_get(key):
    p = os.path.join(CACHE, hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")
    if os.path.exists(p):
        with open(p) as f:
            return json.load(f)
    return None


def _cache_put(key, val):
    p = os.path.join(CACHE, hashlib.sha256(key.encode()).hexdigest()[:32] + ".json")
    with open(p, "w") as f:
        json.dump(val, f)


def _get(url, headers=None, timeout=45, retries=3, is_json=True, data=None, method=None):
    key = f"{method or ('POST' if data else 'GET')} {url} {data or ''}"
    c = _cache_get(key)
    if c is not None:
        return c
    h = {"User-Agent": UA}
    if headers:
        h.update(headers)
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url, headers=h,
                data=(data.encode() if isinstance(data, str) else data),
                method=method)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode(errors="ignore")
            val = json.loads(raw) if is_json else raw
            _cache_put(key, val)
            return val
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                http.client.HTTPException, ConnectionError, OSError,
                json.JSONDecodeError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed {url}: {last}")


# ---------------------------------------------------------------- REGION resolver (Nominatim)
def resolve_region(place, min_span_deg=0.03):
    """place name -> {name, bbox:[s,n,w,e], lat, lon, orig}. Cached; polite to Nominatim.

    Picks the highest-importance candidate that has a REAL areal bounding box, not the first
    hit (which is often a tiny street/POI sharing the name). A too-small bbox (a point feature)
    is padded to `min_span_deg` so downstream point queries have an area to search."""
    normalized = " ".join(str(place).lower().split()).strip(" .,;:")
    if normalized in EBTL_ALIASES:
        return dict(EBTL_REGION)
    if normalized in DONOR_ALIASES:
        return dict(DONOR_REGION)

    # dedupe repeated comma segments ("Brazil, Brazil" → "Brazil"): a redundant segment sent
    # Nominatim to an unrelated same-named hamlet in another country (tick-009)
    segs, seen = [], set()
    for p in [p.strip() for p in place.split(",")]:
        if p.lower() not in seen and p:
            segs.append(p)
            seen.add(p.lower())
    place = ", ".join(segs)
    q = urllib.parse.urlencode({"q": place, "format": "json", "limit": 10})
    url = f"https://nominatim.openstreetmap.org/search?{q}"
    d = _get(url)
    if not d:
        raise RuntimeError(f"region not found: {place!r}")

    def bbox_of(r):
        bb = r["boundingbox"]
        return [float(bb[0]), float(bb[1]), float(bb[2]), float(bb[3])]  # s,n,w,e

    def span(bb):
        return min(bb[1] - bb[0], bb[3] - bb[2])

    areal_classes = {"boundary", "place", "landuse"}
    cands = sorted(d, key=lambda r: (r.get("class") in areal_classes, float(r.get("importance", 0))),
                   reverse=True)
    r = next((c for c in cands if span(bbox_of(c)) >= min_span_deg), cands[0])
    s, n, w, e = bbox_of(r)
    if (n - s) < min_span_deg:
        c = (n + s) / 2
        s, n = c - min_span_deg / 2, c + min_span_deg / 2
    if (e - w) < min_span_deg:
        c = (e + w) / 2
        w, e = c - min_span_deg / 2, c + min_span_deg / 2
    return {"name": r.get("display_name", place), "bbox": [s, n, w, e],
            "lat": float(r["lat"]), "lon": float(r["lon"]), "orig": place,
            "osm_class": r.get("class"), "osm_type": r.get("type")}


def buffer_region(region, radius_km):
    """Return a deterministic bbox expansion around a resolved region.

    This is a search extent, not a proximity threshold. RELATE.threshold_km remains the distance
    used to compare returned points. The approximation is conservative and transparent at the
    small/regional radii used by the harness.
    """
    radius = float(radius_km)
    if radius <= 0:
        raise ValueError("buffer radius must be positive")
    s, n, w, e = region["bbox"]
    mid_lat = (s + n) / 2
    lat_delta = radius / 111.32
    lon_scale = max(0.05, math.cos(math.radians(mid_lat)))
    lon_delta = radius / (111.32 * lon_scale)
    bbox = [s - lat_delta, n + lat_delta, w - lon_delta, e + lon_delta]
    if bbox[0] <= -90 or bbox[1] >= 90 or bbox[2] <= -180 or bbox[3] >= 180:
        raise ValueError("bbox buffer crosses a polar or dateline boundary; exact geometry required")
    return {
        "name": f"{radius:g} km buffer around {region['name']}",
        "bbox": bbox,
        "lat": region.get("lat", (s + n) / 2),
        "lon": region.get("lon", (w + e) / 2),
        "orig": region.get("orig") or region.get("name"),
        "source": "derived-latitude-adjusted-bbox-expansion",
        "method": "bbox-approx",
        "approximate": True,
        "support_type": "analysis-search-bbox",
        "parent_region": region,
        "buffer_km": radius,
    }


# ---------------------------------------------------------------- ecology entity resolver
# These aliases are an explicit language boundary, not a substitute for taxonomy. Every mapped
# scientific name is still verified against GBIF before a live occurrence query is issued.
TAXON_ALIASES = {
    "lantana": "Lantana camara", "lantana camara": "Lantana camara",
    "teak": "Tectona grandis", "neem": "Azadirachta indica",
    "jamun": "Syzygium cumini", "java plum": "Syzygium cumini",
    "tamarind": "Tamarindus indica", "karonda": "Carissa carandas",
    "green cat snake": "Boiga cyanea", "gaur": "Bos gaurus",
    "indian bison": "Bos gaurus", "sambar": "Rusa unicolor",
    "sambar deer": "Rusa unicolor", "asian elephant": "Elephas maximus",
    "elephant": "Elephas maximus", "elephants": "Elephas maximus",
    "chital": "Axis axis", "spotted deer": "Axis axis",
    "nilgai": "Boselaphus tragocamelus", "blue bull": "Boselaphus tragocamelus",
    "tiger": "Panthera tigris", "tigers": "Panthera tigris",
    "leopard": "Panthera pardus", "leopards": "Panthera pardus",
    "indian peafowl": "Pavo cristatus", "peafowl": "Pavo cristatus",
}

RECORD_WORDS = {"record", "records", "observation", "observations", "occurrence",
                "occurrences", "sighting", "sightings", "presence", "locations", "points"}
UNSUPPORTED_MEASURES = {"abundance", "population", "biomass", "occupancy", "richness"}
ECOLOGY_SERIES = {
    "ndvi": "ndvi", "greenness": "ndvi", "vegetation index": "ndvi",
    "vegetation greenness": "ndvi", "vegetation recovery": "ndvi",
    "vegetation ndvi": "ndvi",
}
SOIL_PROXY_ENTITIES = {
    "ebtl soil wetness proxy", "soil wetness proxy", "nasa power soil wetness proxy",
    "merra 2 soil wetness proxy",
}
BIRD_ENTITIES = {"bird", "birds", "bird observation", "bird observations",
                 "bird sighting", "bird sightings", "recent birds",
                 "recent bird observations"}
BIRD_ENTITIES |= {"bird observation record", "bird observation records"}
SITE_ENTITIES = {"anamalai survey site", "anamalai survey sites", "vegetation survey site",
                 "vegetation survey sites", "forest survey site", "forest survey sites"}
SITE_ENTITIES |= {"survey site", "survey sites"}
SITE_ENTITIES |= {"published vegetation survey site", "published vegetation survey sites"}
SITE_POINT_ENTITIES = {
    "ebtl restoration site", "ebtl site center point", "restoration site", "site center point",
}
SNAKE_GROUP_ENTITIES = {
    "snake", "snakes", "snake species", "all snakes", "snake records",
    "snake species records", "recorded snakes", "serpentes",
}
TAXON_GROUP_ENTITIES = {
    "arachnid": "Arachnida", "arachnids": "Arachnida",
    "arachnid species": "Arachnida", "arachnid records": "Arachnida",
    "arachnid occurrence records": "Arachnida",
    "spider": "Araneae", "spiders": "Araneae", "spider records": "Araneae",
    "spider occurrence records": "Araneae",
}
TAXON_TRANSFER_ENTITIES = {
    "ebtl arachnid regional evidence": "Arachnida",
    "ebtl arachnid transfer evidence": "Arachnida",
    "ebtl arachnid donor evidence": "Arachnida",
}
LOCAL_EVIDENCE_ENTITIES = {
    "ebtl wildlife inventory": "wildlife_inventory",
    "documented ebtl wildlife inventory": "wildlife_inventory",
    "ebtl fauna inventory": "wildlife_inventory",
    "ebtl bird inventory": "bird_inventory",
    "ebtl faunal survey bird inventory": "bird_inventory",
    "ebtl snake habitat requirements": "snake_habitat_requirements",
    "ebtl snake tree requirements": "snake_habitat_requirements",
    "documented ebtl cobra inventory": "cobra_inventory",
    "ebtl cobra inventory": "cobra_inventory",
    "documented ebtl venomous snake inventory": "venomous_snake_inventory",
    "ebtl venomous snake inventory": "venomous_snake_inventory",
    "ebtl elephant evidence": "elephant_evidence",
    "documented ebtl elephant evidence": "elephant_evidence",
    "ebtl nursery inventory": "nursery_inventory",
    "documented ebtl nursery inventory": "nursery_inventory",
    "ebtl invasive evidence": "invasive_evidence",
    "ebtl non native plant management": "invasive_evidence",
    "ebtl invasive literature": "invasive_literature",
    "ebtl lantana literature": "invasive_literature",
    "ebtl soil dryness evidence": "soil_evidence",
    "ebtl soil and drought evidence": "soil_evidence",
    "ebtl bird lantana transfer evidence": "bird_lantana_transfer",
    "ebtl evidence summary": "evidence_summary",
}

# Machine-readable connector surface for LLM compilation. This is capability metadata, not an
# intent router: the compiler still chooses and composes algebra, while the executor verifies the
# selected leaf/layer and fails closed when it cannot supply the requested measurement.
CAPABILITY_CATALOG = (
    {"entity": "EBTL evidence summary", "kind": "SELECT",
     "description": "orientation ledger limited to bird/snake counts, indirect elephant passage, nursery snapshot, Eucalyptus removal, and gaps explicitly named in those source cards",
     "grain": "mixed page-addressed site evidence", "evidence": "observed/reported/indirect",
     "scope": "declared EBTL site", "excludes": ["treatment comparison or outcome", "human behavior or livelihoods",
                  "absence claims for topics not named in the ledger"]},
    {"entity": "EBTL wildlife inventory", "kind": "SELECT",
     "description": "local 2024 butterfly, odonate, bird and herpetofauna survey summaries",
     "grain": "survey-period group inventory", "evidence": "observed + older property records",
     "scope": "declared EBTL site"},
    {"entity": "EBTL bird inventory", "kind": "SELECT",
     "description": "complete local 2024 bird checklist with survey method",
     "grain": "published site species record", "evidence": "observed", "scope": "declared EBTL site"},
    {"entity": "snakes", "kind": "SELECT",
     "description": "complete documented EBTL snake inventory; executor separates 2024 VES from older records and marks the declared medically venomous subset",
     "grain": "published site species record", "evidence": "observed/previously recorded",
     "scope": "declared EBTL site",
     "includes": ["EBTL venomous snake inventory"]},
    {"entity": "EBTL cobra inventory", "kind": "SELECT",
     "description": "cobra-only subset of the documented site snake inventory, including which cobra taxa are not listed",
     "grain": "published site species record", "evidence": "previous property record", "scope": "declared EBTL site"},
    {"entity": "EBTL venomous snake inventory", "kind": "SELECT",
     "description": "medically venomous subset of the documented site snake inventory",
     "grain": "published site species record", "evidence": "previous property record", "scope": "declared EBTL site"},
    {"entity": "EBTL elephant evidence", "kind": "SELECT",
     "description": "page-addressed local passage evidence; not abundance or frequency",
     "grain": "site event", "evidence": "indirect", "scope": "declared EBTL site"},
    {"entity": "EBTL nursery inventory", "kind": "SELECT",
     "description": "reported nursery snapshots and published named taxa; not survival outcomes",
     "grain": "site report/taxon", "evidence": "reported", "scope": "declared EBTL site"},
    {"entity": "EBTL invasive evidence", "kind": "SELECT",
     "description": "local management documentation, public occurrence records in the analysis bbox, regional semantic literature leads, and an explicit satellite-extent evidence gap",
     "grain": "site report + bbox occurrence + regional document lead", "evidence": "reported/observed/retrieval lead"},
    {"entity": "EBTL Lantana literature", "kind": "SELECT",
     "description": "semantic paper/dataset discovery for Lantana mechanisms; regional, not local",
     "grain": "document card", "evidence": "retrieval lead"},
    {"entity": "EBTL bird Lantana transfer evidence", "kind": "SELECT",
     "description": "local bird-list overlap with a regional Lantana fruit-use dataset",
     "grain": "cross-dataset transfer hypothesis", "evidence": "modelled/transfer"},
    {"entity": "EBTL soil dryness evidence", "kind": "SELECT",
     "description": "qualitative local drought/topsoil reports and missing direct measurements",
     "grain": "site report", "evidence": "reported"},
    {"entity": "NASA POWER soil wetness proxy", "kind": "SELECT",
     "description": "coarse 2024 MERRA-2 wetness series at the containing grid cell",
     "grain": "0.5 by 0.625 degree grid cell", "evidence": "proxy"},
    {"entity": "EBTL snake habitat requirements", "kind": "SELECT",
     "description": "local snake inventory as habitat basis and explicit absence of measured tree dependencies",
     "grain": "published site species record", "evidence": "observed + DataRequest"},
    {"entity": "arachnids", "kind": "SELECT",
     "description": "higher-taxon public occurrence lookup in the EBTL analysis bbox",
     "grain": "bbox occurrence record", "evidence": "observed public record"},
    {"entity": "EBTL arachnid transfer evidence", "kind": "SELECT",
     "description": "dynamic regional candidate discovery with feature and climate gate audit",
     "grain": "local/bbox/regional gate assessment", "evidence": "observed + modelled gate",
     "includes": ["arachnids"]},
    {"entity": "EBTL restoration site", "kind": "SELECT",
     "description": "declared site-centre point used only as an input to raster ANNOTATE",
     "grain": "declared point", "evidence": "site metadata"},
    {"entity": "land cover", "kind": "ANNOTATE layer",
     "source_entity": "EBTL restoration site",
     "description": "WorldCover centre class plus analysis-bbox class areas; annotate EBTL restoration site",
     "grain": "10 m modelled raster / analysis bbox", "evidence": "modelled"},
    {"entity": "historical fire exposure", "kind": "ANNOTATE layer",
     "source_entity": "EBTL restoration site",
     "description": "MODIS exact-AOI active-fire history and separate 5 km exposure; annotate site point",
     "grain": "AOI + 5 km buffer", "evidence": "proxy"},
    {"entity": "greenness trend", "kind": "ANNOTATE layer",
     "source_entity": "EBTL restoration site",
     "description": "MODIS annual NDVI trend at declared centre; annotate site point",
     "grain": "250 m pixel", "evidence": "proxy"},
    {"entity": "taxon occurrence records", "kind": "SELECT",
     "description": "bounded GBIF + iNaturalist point merger for a named taxon and requested region; semantic paper discovery is a separate operation",
     "grain": "public occurrence point", "evidence": "observed record, not abundance",
     "binding": "compiler_entity", "scope": "requested region"},
    {"entity": "spatial relation between occurrence records", "kind": "RELATE operator",
     "description": "derive nearest distance, within, beyond, or cooccurrence-proxy results from two georeferenced occurrence sets; proximity is not interaction or simultaneous observation",
     "grain": "pairwise occurrence proximity", "evidence": "derived proxy",
     "binding": "operator", "ops": ["RELATE"],
     "requires": ["taxon occurrence records"]},
    {"entity": "regional-to-target occurrence transfer", "kind": "ESTIMATE operator",
     "description": "apply an explicit environmental or interpolation gate to occurrence records from a donor region before estimating at a target; rejection remains a data request",
     "grain": "taxon-specific gated transfer", "evidence": "modelled",
     "binding": "operator", "ops": ["ESTIMATE"],
     "requires": ["taxon occurrence records"]},
    {"entity": "buffered search region", "kind": "REGION operator",
     "description": "expand a named search region by an explicit radius; this controls retrieval extent and is distinct from a RELATE distance threshold",
     "grain": "derived search bbox", "evidence": "declared geometry",
     "binding": "operator", "ops": ["BUFFER"],
     "scope_policy": "compiler_must_write_each_operand_support"},
    {"entity": "declared EBTL donor belt", "kind": "REGION support",
     "description": "declared dry-Deccan donor belt used for regional evidence around the target site; bbox south 11.0 north 13.6 west 76.0 east 79.5",
     "grain": "declared regional search bbox", "evidence": "declared geometry",
     "binding": "region", "place": "dry-Deccan donor belt"},
)


def capability_catalog():
    """Return connector metadata suitable for compiler prompting or UI generation."""
    return [dict(item) for item in CAPABILITY_CATALOG]


def _clean_entity(entity):
    e = " ".join(str(entity).lower().replace("_", " ").replace("-", " ").split())
    words = [w.strip(".,;:()[]") for w in e.split()]
    core = [w for w in words if w not in RECORD_WORDS and w not in {"documented", "recorded"}]
    return e, " ".join(core).strip()


def _gbif_taxon_match(name):
    q = urllib.parse.urlencode({"name": name, "strict": "true", "verbose": "true"})
    d = _get(f"https://api.gbif.org/v1/species/match?{q}")
    if d.get("matchType") in (None, "NONE"):
        return None
    return {"scientific": d.get("canonicalName") or d.get("scientificName"),
            "rank": (d.get("rank") or "").upper(), "match": d.get("matchType"),
            "confidence": d.get("confidence"), "usage_key": d.get("usageKey"),
            "alternatives": d.get("alternatives") or []}


def _inat_exact_taxa(name):
    q = urllib.parse.urlencode({"q": name, "per_page": 10, "locale": "en"})
    d = _get(f"https://api.inaturalist.org/v1/taxa?{q}")
    key = name.casefold()
    hits = []
    for t in d.get("results", []):
        sci = (t.get("name") or "").casefold()
        common = (t.get("preferred_common_name") or "").casefold()
        matched = (t.get("matched_term") or "").casefold()
        if key in {sci, common, matched}:
            hits.append({"id": t.get("id"), "scientific": t.get("name"),
                         "common": t.get("preferred_common_name"),
                         "rank": (t.get("rank") or "").upper()})
    return hits


def resolve_ecology_entity(entity):
    """Resolve an ecology SELECT entity without silently turning a proxy into a measure.

    Returns a tagged resolution. ``ambiguous`` and ``unsupported_measure`` are deliberate
    fail-closed results consumed by the executor as DataRequests.
    """
    e, core = _clean_entity(entity)
    local_key = LOCAL_EVIDENCE_ENTITIES.get(e) or LOCAL_EVIDENCE_ENTITIES.get(core)
    if local_key:
        return {"kind": "published_site_evidence", "canonical": local_key,
                "input": entity}
    if e in ECOLOGY_SERIES:
        return {"kind": "series", "canonical": ECOLOGY_SERIES[e], "input": entity}
    if e in SOIL_PROXY_ENTITIES or core in SOIL_PROXY_ENTITIES:
        return {"kind": "soil_wetness_proxy", "canonical": "NASA POWER soil wetness",
                "input": entity}
    if e in BIRD_ENTITIES:
        return {"kind": "ebird", "canonical": "recent bird observations", "input": entity}
    if e in SITE_ENTITIES:
        return {"kind": "survey_sites", "canonical": "Anamalai vegetation survey sites",
                "input": entity}
    if e in SITE_POINT_ENTITIES:
        return {"kind": "site_point", "canonical": "EBTL site center", "input": entity}
    if e in SNAKE_GROUP_ENTITIES or core in SNAKE_GROUP_ENTITIES:
        return {"kind": "taxon_inventory", "canonical": "Snakes (Serpentes)",
                "taxon": "Serpentes", "input": entity}
    transfer_group = TAXON_TRANSFER_ENTITIES.get(e) or TAXON_TRANSFER_ENTITIES.get(core)
    if transfer_group:
        return {"kind": "taxon_group_transfer", "canonical": transfer_group,
                "taxon": transfer_group, "input": entity}
    group = TAXON_GROUP_ENTITIES.get(e) or TAXON_GROUP_ENTITIES.get(core)
    if group:
        return {"kind": "taxon_group", "canonical": group, "taxon": group,
                "input": entity, "count_admissible": bool(set(e.split()) & RECORD_WORDS)}
    if set(e.split()) & UNSUPPORTED_MEASURES:
        return {"kind": "unsupported_measure", "input": entity,
                "note": "occurrence sources cannot measure abundance, population, biomass, "
                        "occupancy, or species richness without a survey design"}

    candidate = TAXON_ALIASES.get(core) or TAXON_ALIASES.get(e)
    looks_scientific = (len(core.split()) == 2 and core[:1].isupper())
    # The parser normally lowercases copied entities, so also accept a two-word GBIF exact match.
    if candidate:
        match = _gbif_taxon_match(candidate)
        if not match or match["rank"] not in {"SPECIES", "SUBSPECIES"} \
                or match["match"] != "EXACT":
            return {"kind": "unverified_taxon", "input": entity, "candidate": candidate}
        return {"kind": "taxon", "canonical": match["scientific"],
                "usage_key": match["usage_key"], "input": entity,
                "count_admissible": bool(set(e.split()) & RECORD_WORDS), "match": match}

    # Scientific names are admitted only on an exact species-level GBIF match. For common names,
    # exact iNaturalist vernacular matches may nominate a taxon, but multiple species fail closed.
    match = _gbif_taxon_match(core) if core else None
    if match and match["match"] == "EXACT" and match["rank"] in {"SPECIES", "SUBSPECIES"}:
        return {"kind": "taxon", "canonical": match["scientific"],
                "usage_key": match["usage_key"], "input": entity,
                "count_admissible": bool(set(e.split()) & RECORD_WORDS), "match": match}
    exact = _inat_exact_taxa(core) if core else []
    species = {x["scientific"]: x for x in exact if x["rank"] in {"SPECIES", "SUBSPECIES"}}
    if len(species) == 1:
        x = next(iter(species.values()))
        verified = _gbif_taxon_match(x["scientific"])
        if verified and verified["match"] == "EXACT" and verified["rank"] in {"SPECIES", "SUBSPECIES"}:
            return {"kind": "taxon", "canonical": verified["scientific"],
                    "usage_key": verified["usage_key"], "inat_taxon_id": x["id"],
                    "common": x.get("common"), "input": entity,
                    "count_admissible": bool(set(e.split()) & RECORD_WORDS), "match": verified}
    if len(species) > 1:
        return {"kind": "ambiguous", "input": entity,
                "candidates": sorted(species)[:6]}
    return None


def _time_window(time_value):
    if not isinstance(time_value, dict):
        return None, None
    start, end = time_value.get("start"), time_value.get("end")
    return (str(start) if start else None), (str(end) if end else None)


def _redistributable_license(license_value):
    v = (license_value or "").lower()
    return ("publicdomain/zero" in v or "creativecommons.org/licenses/by/4.0" in v
            or "creativecommons.org/licenses/by-sa/4.0" in v or v in {"cc0", "cc-by", "cc-by-sa"})


def gbif_occurrences(resolution, region, time_value=None, limit=200):
    s, n, w, e = region["bbox"]
    start, end = _time_window(time_value)
    params = {"taxon_key": resolution["usage_key"], "has_coordinate": "true",
              "has_geospatial_issue": "false", "decimalLatitude": f"{s},{n}",
              "decimalLongitude": f"{w},{e}", "limit": min(int(limit), 300)}
    if start or end:
        sy = (start or end)[:4]
        ey = (end or start)[:4]
        params["year"] = f"{sy},{ey}" if sy != ey else sy
    d = _get("https://api.gbif.org/v1/occurrence/search?" + urllib.parse.urlencode(params))
    rows, blocked = [], 0
    for o in d.get("results", []):
        lic = o.get("license")
        if not _redistributable_license(lic):
            blocked += 1
            continue
        lat, lon = o.get("decimalLatitude"), o.get("decimalLongitude")
        if lat is None or lon is None:
            continue
        key = o.get("key")
        rows.append({"id": f"gbif:{key}", "lat": float(lat), "lon": float(lon),
                     "name": resolution["canonical"],
                     "scientific_name": o.get("scientificName") or resolution["canonical"],
                     "time": o.get("eventDate") or o.get("year"), "source": "GBIF",
                     "source_record": f"https://www.gbif.org/occurrence/{key}",
                     "dataset_key": o.get("datasetKey"), "basis": o.get("basisOfRecord"),
                     "quality_issues": o.get("issues") or [], "license": lic})
    return rows, blocked, int(d.get("count") or len(d.get("results", [])))


def inat_occurrences(resolution, region, time_value=None, limit=200):
    s, n, w, e = region["bbox"]
    start, end = _time_window(time_value)
    params = {"taxon_name": resolution["canonical"], "swlat": s, "swlng": w,
              "nelat": n, "nelng": e, "quality_grade": "research", "geo": "true",
              "license": "cc0,cc-by,cc-by-sa", "per_page": min(int(limit), 200),
              "order_by": "observed_on", "order": "desc"}
    if start:
        params["d1"] = start if len(start) > 4 else f"{start}-01-01"
    if end:
        params["d2"] = end if len(end) > 4 else f"{end}-12-31"
    d = _get("https://api.inaturalist.org/v1/observations?" + urllib.parse.urlencode(params))
    rows = []
    for o in d.get("results", []):
        coords = (o.get("geojson") or {}).get("coordinates")
        if not coords or len(coords) < 2 or not _redistributable_license(o.get("license_code")):
            continue
        tax = o.get("taxon") or {}
        oid = o.get("id")
        rows.append({"id": f"inat:{oid}", "lat": float(coords[1]), "lon": float(coords[0]),
                     "name": resolution["canonical"],
                     "scientific_name": tax.get("name") or resolution["canonical"],
                     "common_name": tax.get("preferred_common_name"),
                     "time": o.get("observed_on") or o.get("time_observed_at"),
                     "source": "iNaturalist", "quality_grade": o.get("quality_grade"),
                     "source_record": o.get("uri") or f"https://www.inaturalist.org/observations/{oid}",
                     "license": o.get("license_code")})
    return rows, int(d.get("total_results") or len(rows))


def taxon_occurrences(entity, region, time_value=None, limit=200):
    resolution = resolve_ecology_entity(entity)
    if not resolution or resolution.get("kind") != "taxon":
        return {"rows": [], "kind": "records", "source": "GBIF+iNaturalist",
                "label": "observed", "resolution": resolution,
                "note": f"taxon not safely resolved for {entity!r}"}
    out = ORIGIN.points_occurrences(resolution, region, time_value, limit)
    if not out.get("rows") and not out.get("unsupported_time"):
        # Empty local records trigger evidence discovery, exactly as the production Hermes playbook
        # does. Ranked cards are leads, not observations, so they stay outside ``rows``.
        query = f"{entity} {resolution['canonical']} {region['name']} occurrence habitat survey"
        try:
            found = ORIGIN.semantic_discovery(query, k=5, points_only=True)
            out["evidence_discovery"] = found.get("results") or []
            out.setdefault("connector_events", []).extend(found["connector_events"])
            out["note"] += (
                f"; semantic discovery returned {len(out['evidence_discovery'])} candidate "
                "datasets, which are not local occurrence evidence until extracted and spatially checked"
            )
        except Exception as exc:
            out["discovery_unavailable"] = f"{type(exc).__name__}: {str(exc)[:160]}"
    return out


def taxon_group_occurrences(resolution, region, time_value=None, limit=300):
    """Discover records by declared higher taxon instead of a model-picked species shortlist."""
    match = _gbif_taxon_match(resolution["taxon"])
    admitted_ranks = {"CLASS", "ORDER", "FAMILY", "GENUS"}
    if not match or match.get("rank") not in admitted_ranks:
        return {"rows": [], "kind": "records", "source": "GBIF+iNaturalist",
                "label": "observed", "note": "higher taxon could not be verified"}
    verified = {**resolution, "usage_key": match["usage_key"],
                "canonical": match["scientific"], "count_admissible": True}
    gbif_rows, blocked, gbif_total = gbif_occurrences(verified, region, time_value, limit)
    inat_rows, inat_total = inat_occurrences(verified, region, time_value, min(limit, 200))
    seen, rows = set(), []
    for row in gbif_rows + inat_rows:
        key = (round(row["lat"], 5), round(row["lon"], 5),
               (row.get("scientific_name") or "").lower())
        if key not in seen:
            seen.add(key)
            rows.append(row)
    query = (f"{resolution['taxon']} spider arachnid survey Eastern Ghats Krishnagiri "
             "Tamil Nadu species occurrence dataset")
    discovered, events = [], []
    try:
        found = ORIGIN.semantic_discovery(query, k=5, points_only=True)
        candidates = found.get("results") or []
        # Embedding similarity is discovery, not admission. Retain only cards whose title names
        # the requested group; a high-scoring bird/amphibian card is not arachnid evidence.
        group_terms = ("spider", "arachnid") if resolution["taxon"] == "Arachnida" else ("spider",)
        discovered = [card for card in candidates if any(
            term in str(card.get("title", "")).lower() for term in group_terms)]
        events = found.get("connector_events") or []
    except Exception as exc:
        discovery_error = f"{type(exc).__name__}: {str(exc)[:160]}"
    species = sorted({r.get("scientific_name") for r in rows if r.get("scientific_name")})
    source_events = [
        {"tool": "gbif.occurrence.search", "parameters": {
            "higher_taxon": resolution["taxon"], "bbox": region["bbox"],
            "limit": min(int(limit), 300)}, "output_rows": len(gbif_rows),
         "api_total": gbif_total, "blocked_license_rows": blocked},
        {"tool": "inat.observations", "parameters": {
            "higher_taxon": resolution["taxon"], "bbox": region["bbox"],
            "limit": min(int(limit), 200)}, "output_rows": len(inat_rows),
         "api_total": inat_total},
    ]
    return {
        "rows": rows, "kind": "records", "source": "GBIF+iNaturalist higher-taxon query",
        "label": "observed", "grain": "public-occurrence-record", "count_admissible": True,
        "region": region, "query_time": time_value, "query_semantics": "taxon_group_inventory",
        "inventory": {"taxon": resolution["taxon"], "deduplicated_records": len(rows),
                      "returned_record_count": len(rows), "named_taxa_count": len(species),
                      "named_species": species, "gbif_api_total": gbif_total,
                      "inat_api_total": inat_total, "blocked_license_rows": blocked},
        "evidence_discovery": discovered, "connector_events": source_events + events,
        "discovery_error": locals().get("discovery_error"),
        "note": (f"{len(rows)} coordinate/species-deduplicated public occurrence records for the "
                 f"verified higher taxon {resolution['taxon']} in the analysis bbox; "
                 f"{len(species)} named taxa in returned rows; semantic discovery produced "
                 f"{len(discovered)} dataset leads; this is not a complete site inventory"),
    }


def arachnid_transfer_evidence(region):
    """Widen a sparse local higher-taxon query, then test species-level transfer gates.

    Candidate species are discovered from the returned licensed regional sample, not supplied by
    a language model.  Climate and local-feature gates are both reported.  A candidate is not
    admitted as a site expectation unless both pass; a species already observed locally remains
    observed rather than being relabelled as an estimate.
    """
    donor = dict(DONOR_REGION)
    local = taxon_group_occurrences({"taxon": "Arachnida"}, region, limit=300)
    regional = taxon_group_occurrences({"taxon": "Arachnida"}, donor, limit=300)
    counts = collections.Counter(
        row.get("scientific_name") for row in regional.get("rows", [])
        if row.get("scientific_name")
    )
    local_names = (local.get("inventory") or {}).get("named_species") or []
    # The regional query is capped and license-filtered, so this is a transparent shortlist from
    # the returned evidence, not an ecological ranking or an exhaustive expected-species list.
    regional_names = [name for name, _ in counts.most_common(3)]
    selected = []
    for name in local_names[:1] + regional_names:
        canonical = " ".join(str(name).split()[:2])
        if canonical and canonical not in selected:
            selected.append(canonical)

    def assess(species):
        points = taxon_occurrences(species, donor, limit=300)
        donor_source = {**points, "grain": "occurrence"}
        feature = transfer_gate(donor_source, region, "feature")
        envelope = transfer_gate(donor_source, region, "envelope")
        if feature.get("pass") is False and feature.get("strength") == "AlphaEarth-NN-analog":
            feature["ask"] = (
                "collect local target observations to test presence directly; this does not "
                "change or retroactively pass the failed environmental analog gate")
        return {
            "species": species,
            "donor_records": len(points.get("rows") or []),
            "locally_observed": any(str(name).startswith(species) for name in local_names),
            "feature_gate": feature,
            "climate_gate": envelope,
            "transfer_admissible": bool(
                not any(str(name).startswith(species) for name in local_names)
                and feature.get("pass") and envelope.get("pass")
            ),
            "connector_events": points.get("connector_events") or [],
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(selected))) as pool:
        assessments = list(pool.map(assess, selected))
    events = list(local.get("connector_events") or []) + list(
        regional.get("connector_events") or [])
    for assessment in assessments:
        events.extend(assessment.pop("connector_events"))
        for method, gate in (("feature", assessment["feature_gate"]),
                             ("envelope", assessment["climate_gate"])):
            events.append({
                "tool": f"typed.transfer_gate.{method}",
                "parameters": {"species": assessment["species"],
                               "target_bbox": region["bbox"]},
                "output_rows": 1,
                "passed": bool(gate.get("pass")),
                "strength": gate.get("strength"),
            })
    admitted = [x["species"] for x in assessments if x["transfer_admissible"]]
    assessment_counts = {
        "species_audited": len(assessments),
        "locally_observed": sum(bool(x.get("locally_observed")) for x in assessments),
        "regional_not_locally_observed": sum(
            not bool(x.get("locally_observed")) for x in assessments),
        "transfer_admitted": len(admitted),
    }
    discovery = {}
    for card in ((local.get("evidence_discovery") or []) +
                 (regional.get("evidence_discovery") or [])):
        key = card.get("doi") or card.get("title")
        if key:
            discovery[key] = card
    return {
        "rows": local.get("rows") or [],
        "kind": "records",
        "source": "GBIF+iNaturalist + exact origin points + typed environmental gates",
        "label": "observed",
        "grain": "local-occurrences-plus-regional-transfer-audit",
        "region": region,
        "query_semantics": "taxon_group_transfer_audit",
        "local_inventory": local.get("inventory") or {},
        "regional_inventory": regional.get("inventory") or {},
        "regional_returned_sample_counts": dict(counts),
        "assessments": assessments,
        "assessment_counts": assessment_counts,
        "gate_contract": {
            "feature": (
                "For each target cell, AlphaEarth cosine similarity must meet that candidate's "
                "analog_floor; the candidate passes only when target_analog_fraction is at least "
                "0.5."),
            "climate": (
                "The candidate passes only when target_in_envelope_fraction is at least 0.8 "
                "inside the donor WorldClim envelope."),
            "admission": (
                "A not-locally-observed candidate is transfer-admissible only if both gates pass; "
                "a local observation remains observed rather than becoming a transfer estimate."),
        },
        "admitted_transfer_candidates": admitted,
        "evidence_discovery": list(discovery.values()),
        "connector_events": events,
        "note": (
            "dynamic higher-taxon discovery widened the sparse local query to a declared donor "
            "belt, nominated three species from the returned licensed sample, then ran exact "
            "species point queries and separate AlphaEarth feature and WorldClim envelope gates; "
            "no failed gate is converted into a site expectation"
        ),
    }


def nasa_power_soil_wetness(region, year=2024):
    """Coarse MERRA-2 wetness proxy; explicitly not a site soil sensor measurement."""
    start, end = f"{int(year)}0101", f"{int(year)}1231"
    params = {
        "parameters": "GWETTOP,GWETROOT,PRECTOTCORR", "community": "AG",
        "longitude": region["lon"], "latitude": region["lat"],
        "start": start, "end": end, "format": "JSON",
    }
    url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urllib.parse.urlencode(params)
    data = _get(url, timeout=60)
    values = data["properties"]["parameter"]

    def valid(name):
        return {day: float(value) for day, value in values[name].items()
                if value is not None and float(value) > -900}

    top, root, rain = valid("GWETTOP"), valid("GWETROOT"), valid("PRECTOTCORR")

    def mean(items):
        vals = list(items)
        return round(sum(vals) / len(vals), 3) if vals else None

    dry_days = [day for day in top if day[4:6] in {"01", "02", "03", "04"}]
    wet_days = [day for day in top if day[4:6] in {"06", "07", "08", "09", "10"}]
    driest_day = min(top, key=top.get) if top else None
    row = {
        "id": f"nasa-power-merra2-soil-wetness:{year}", "year": int(year),
        "surface_wetness_mean": mean(top.values()),
        "root_zone_wetness_mean": mean(root.values()),
        "jan_apr_surface_wetness_mean": mean(top[d] for d in dry_days),
        "jun_oct_surface_wetness_mean": mean(top[d] for d in wet_days),
        "minimum_surface_wetness": top.get(driest_day),
        "minimum_date": (f"{driest_day[:4]}-{driest_day[4:6]}-{driest_day[6:]}"
                         if driest_day else None),
        "annual_precipitation_mm": round(sum(rain.values()), 1),
        "source": "NASA POWER Daily API v2.9.4 / MERRA-2",
        "source_record": url, "units": {"wetness": "unitless 0–1", "rain": "mm/day"},
    }
    return {
        "rows": [row], "kind": "records", "source": row["source"], "label": "proxy",
        "grain": "MERRA-2-native-grid-cell-at-site-coordinate", "count_admissible": False,
        "region": region, "query_time": {"start": str(year), "end": str(year)},
        "query_semantics": "soil_wetness_proxy",
        "source_metadata": {"native_resolution": "0.5° latitude × 0.625° longitude",
                            "time_standard": data.get("header", {}).get("time_standard"),
                            "parameters": data.get("parameters")},
        "note": ("daily MERRA-2 unitless surface/root-zone wetness at the NASA POWER native grid "
                 "cell containing the site; roughly tens of kilometres, not a property sensor, "
                 "soil-depth profile, or volumetric water-content measurement"),
    }


def published_taxon_inventory(resolution, region, time_value=None):
    """Load a declared group inventory instead of sampling model-selected species.

    Only a source that explicitly inventories the requested taxon at the selected site is
    admissible. Other site/taxon pairs return no result so transfer remains an explicit algebraic
    operation rather than a hidden connector substitution.
    """
    if resolution.get("taxon") != "Serpentes" or region.get("source") != "SITE_EBTL.json":
        return None
    path = os.path.join(DATA, "ebtl_faunal_survey_2024.json")
    with open(path, encoding="utf-8") as f:
        source = json.load(f)
    rows = []
    for i, item in enumerate(source["records"], 1):
        rows.append({
            "id": f"{source['source_id']}:snake:{i}",
            **item,
            "medically_venomous": item["family"] in {"Elapidae", "Viperidae"},
            "site": source["site"],
            "survey_dates": source["survey_dates"],
            "method": source["method"],
            "source": source["title"],
            "source_record": f"{source['source_file']}#page={item['page']}",
        })
    during = sum(r["record_status"] == "observed_during_survey" for r in rows)
    previous = len(rows) - during
    return {
        "rows": rows,
        "kind": "records",
        "source": source["title"],
        "label": "observed",
        "grain": "published-site-species-record",
        "count_admissible": True,
        "query_time": time_value,
        "region": region,
        "query_semantics": "taxon_inventory",
        "inventory": {
            "taxon": resolution["taxon"],
            "species": len(rows),
            "observed_during_survey": during,
            "previous_property_records_not_observed_during_survey": previous,
        },
        "source_metadata": {k: source[k] for k in (
            "source_id", "title", "author", "source_file", "source_sha256",
            "survey_dates", "method", "pages")},
        "note": (
            f"published site inventory: {len(rows)} snake species; {during} encountered during "
            f"the September 2024 VES and {previous} previously recorded on the property but not "
            "encountered during that three-day survey"
        ),
    }


def _primary_evidence():
    with open(os.path.join(DATA, "ebtl_primary_evidence.json"), encoding="utf-8") as f:
        return json.load(f)


def _snake_inventory_source():
    with open(os.path.join(DATA, "ebtl_faunal_survey_2024.json"), encoding="utf-8") as f:
        return json.load(f)


def published_site_evidence(resolution, region, time_value=None):
    """Return page-addressable site evidence imported from primary EBTL documents.

    This connector intentionally outranks empty public-API searches for questions answered by a
    declared local survey or site report. Indirect signs remain labelled indirect; a newsletter
    never becomes a direct animal observation, and a regional interaction study never becomes a
    local association.
    """
    if region.get("source") != "SITE_EBTL.json":
        return None
    key = resolution.get("canonical")
    data = _primary_evidence()
    sources = data["sources"]
    label = "observed"
    rows = []
    note = ""
    metadata = {}
    connector_events = []

    if key == "wildlife_inventory":
        summary = data["wildlife_survey_summary"]
        src = sources[summary["source_id"]]
        rows = [{
            "id": f"faunal-survey-2024:group:{item['group']}", **item,
            "record_status": "survey_summary",
            "source": src["title"],
            "source_record": f"{src['source_file']}#page={item['pages'][0]}",
        } for item in summary["groups"]]
        metadata = {
            "survey_dates": summary["survey_dates"],
            "limitation": summary["limitation"],
            "indirect_elephant_passage_events": len(data["elephant_evidence"]),
        }
        note = (
            "published local survey summaries for butterflies, odonates, birds and herpetofauna; "
            "the herpetofauna total separates 2024 VES detections from earlier property records; "
            "elephant evidence comes from two separate indirect passage reports"
        )
    elif key == "bird_inventory":
        inventory = data["bird_inventory"]
        src = sources[inventory["source_id"]]
        rows = [{
            "id": f"faunal-survey-2024:bird:{i}",
            "group": "Bird", "common_name": common, "scientific_name": scientific,
            "record_status": "recorded_during_2024_site_survey",
            "source": src["title"], "source_record": f"{src['source_file']}#page=18",
        } for i, (common, scientific) in enumerate(inventory["records"], 1)]
        metadata = {"method": inventory["method"], "survey_period": inventory["survey_period"],
                    "pages": inventory["pages"],
                    "frequent_checklist_species": inventory["frequent_checklist_species"]}
        note = (f"complete published site inventory of {len(rows)} bird species; seen-or-heard "
                "transit survey with morning/evening effort and 30-minute eBird checklists")
    elif key == "snake_habitat_requirements":
        source = _snake_inventory_source()
        rows = [{
            "id": f"{source['source_id']}:snake-habitat-basis:{i}", **item,
            "site": source["site"], "survey_dates": source["survey_dates"],
            "source": source["title"],
            "source_record": f"{source['source_file']}#page={item['page']}",
        } for i, item in enumerate(source["records"], 1)]
        metadata = {
            "method": source["method"], "inventory_species": len(rows),
            "tree_dependency_evidence": "not measured or reported in the source tables",
            "required_field_covariates": [
                "canopy and shrub cover", "leaf-litter depth and ground cover",
                "rock, termite-mound, log and refuge availability", "water and hydroperiod",
                "prey indicators", "ground temperature and moisture",
                "repeat VES effort by habitat stratum and time of day",
            ],
        }
        note = (
            "the local source supports a 14-species snake basis and survey status, but reports no "
            "snake-by-tree use, host-tree requirement, vegetation selection, or planting outcome"
        )
    elif key in {"cobra_inventory", "venomous_snake_inventory"}:
        source = _snake_inventory_source()
        records = source["records"]
        if key == "cobra_inventory":
            records = [r for r in records if "cobra" in r["common_name"].lower()]
            note = ("the published property inventory contains Spectacled Cobra; King Cobra is "
                    "not listed, which is inventory non-detection rather than proof of site absence")
            metadata["not_listed_in_inventory"] = ["King Cobra (Ophiophagus hannah)"]
        else:
            records = [r for r in records if r["family"] in {"Elapidae", "Viperidae"}]
            note = (f"{len(records)} medically venomous species in the documented 14-species "
                    "property inventory; all are earlier property records not encountered in the "
                    "three-day September 2024 VES")
        rows = [{
            "id": f"{source['source_id']}:{key}:{i}", **item,
            "site": source["site"], "survey_dates": source["survey_dates"],
            "source": source["title"],
            "source_record": f"{source['source_file']}#page={item['page']}",
        } for i, item in enumerate(records, 1)]
        metadata.update({"method": source["method"], "inventory_species": 14})
    elif key == "elephant_evidence":
        for i, item in enumerate(data["elephant_evidence"], 1):
            src = sources[item["source_id"]]
            rows.append({"id": f"ebtl-elephant-evidence:{i}", **item,
                         "source": src["title"],
                         "source_record": f"{src['source_file']}#page={item['pdf_page']}"})
        note = ("two site passage events documented from physical signs and damage; neither was a "
                "camera-trap or direct survey detection, so they establish indirect use evidence, "
                "not abundance or frequency")
    elif key == "nursery_inventory":
        nursery = data["nursery"]
        for i, (taxon, source_id, page) in enumerate(nursery["named_taxa"], 1):
            src = sources[source_id]
            rows.append({"id": f"ebtl-nursery-taxon:{i}", "scientific_name": taxon,
                         "record_status": "named_in_site_nursery_report", "source": src["title"],
                         "source_record": f"{src['source_file']}#page={page}"})
        metadata = {"snapshots": nursery["snapshots"], "limitation": nursery["limitation"]}
        note = (f"{len(rows)} taxa are named in imported newsletters; the July 2024 snapshot reports "
                "110 propagated species and 15,000 saplings, but the complete roster and survival "
                "data are not published")
    elif key == "invasive_evidence":
        items = [x for x in data["site_condition_evidence"]
                 if x["topic"] == "invasive_or_non_native_management"]
        for i, item in enumerate(items, 1):
            src = sources[item["source_id"]]
            rows.append({"id": f"ebtl-invasive-evidence:{i}", **item,
                         "source": src["title"],
                         "source_record": f"{src['source_file']}#page={item['pdf_page']}"})
        plants = ("Lantana camara", "Jatropha gossypiifolia", "Dichrostachys cinerea",
                  "Abrus precatorius")

        def invasive_count(name):
            out = ORIGIN.points_occurrences(
                {"canonical": name, "count_admissible": True}, region, None, 300)
            return name, len(out.get("rows") or []), out.get("connector_events") or []

        point_counts = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            for name, count, events in pool.map(invasive_count, plants):
                point_counts[name] = count
                connector_events.extend(events)
        metadata["site_bbox_public_point_records"] = point_counts
        discovery_query = "Lantana camara seed dispersal frugivorous birds India invasive plant diet"
        found = ORIGIN.semantic_discovery(discovery_query, k=5, points_only=False)
        connector_events.extend(found.get("connector_events") or [])
        leads = [card for card in found.get("results") or []
                 if "lantana camara" in str(card.get("title", "")).lower() and
                 "plant-disperser" in str(card.get("title", "")).lower()]
        metadata["regional_semantic_literature_leads"] = [{
            "title": card.get("title"), "doi": card.get("doi"),
            "scope": "regional literature lead; not EBTL evidence",
        } for card in leads]
        metadata["satellite_invasive_extent"] = (
            "no admitted site-scale satellite invasive-extent measurement")
        label = "mixed"
        note = ("site documentation names a roughly one-acre Eucalyptus monocrop removal; public "
                "occurrence points add candidate taxa inside the analysis bbox, which is not the "
                "70-acre property boundary; Lantana returns zero bbox points; semantic discovery "
                "adds regional document leads only, and no admitted satellite invasive-extent "
                "measurement is available")
    elif key == "invasive_literature":
        query = "Lantana camara seed dispersal frugivorous birds India invasive plant diet"
        found = ORIGIN.semantic_discovery(query, k=5, points_only=False)
        connector_events.extend(found.get("connector_events") or [])
        cards = [card for card in found.get("results") or []
                 if "lantana camara" in str(card.get("title", "")).lower() and
                 "plant-disperser" in str(card.get("title", "")).lower()]
        rows = [{"id": f"invasive-literature:{i}", **card,
                 "source": "origin semantic discovery",
                 "source_record": f"doi:{card.get('doi')}"}
                for i, card in enumerate(cards, 1)]
        label = "modelled"
        metadata = {"query": query, "source_scope": "regional literature; not EBTL"}
        note = ("semantic embedding discovery surfaced a Lantana plant-disperser dataset with a "
                "codebook; it has no EBTL-local points, so it supports mechanism discovery only")
    elif key == "soil_evidence":
        items = [x for x in data["site_condition_evidence"] if x["topic"] == "soil_and_drought"]
        for i, item in enumerate(items, 1):
            src = sources[item["source_id"]]
            rows.append({"id": f"ebtl-soil-evidence:{i}", **item,
                         "source": src["title"],
                         "source_record": f"{src['source_file']}#page={item['pdf_page']}"})
        note = ("qualitative site drought and degradation evidence only; no calibrated soil-water "
                "measurement, sampling depth, seasonal series, or direct dryness value is available")
    elif key == "bird_lantana_transfer":
        with open(os.path.join(DATA, "lantana_bird_transfer.json"), encoding="utf-8") as f:
            study = json.load(f)
        bird_scientific = {common: scientific for common, scientific
                           in data["bird_inventory"]["records"]}
        candidates = [("bird", item["common_name"], bird_scientific[item["common_name"]])
                      for item in study["locally_recorded_bird_overlap"]]
        candidates += [("plant", name, name) for name in (
            "Lantana camara", "Jatropha gossypiifolia", "Dichrostachys cinerea",
            "Abrus precatorius")]

        def point_count(candidate):
            group, display, scientific = candidate
            out = ORIGIN.points_occurrences(
                {"canonical": scientific, "count_admissible": True}, region, None, 300)
            return group, display, scientific, len(out.get("rows") or []), \
                out.get("connector_events") or []

        counts, connector_events = {}, []
        # The unchanged origin points connector is I/O bound and each taxon query is independent.
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            for group, display, scientific, count, events in pool.map(point_count, candidates):
                counts[scientific] = count
                connector_events.extend(events)
        rows = [{"id": f"{study['source_id']}:overlap:{i}", **item,
                 "scientific_name": bird_scientific[item["common_name"]],
                 "site_bbox_public_point_records": counts[bird_scientific[item["common_name"]]],
                 "source": study["title"], "source_record": f"doi:{study['doi']}"}
                for i, item in enumerate(study["locally_recorded_bird_overlap"], 1)]
        label = "modelled"
        metadata = {"doi": study["doi"], "method": study["method"],
                    "source_scope": study["source_scope"], "lantana_rows": study["lantana_rows"],
                    "local_interaction_admissible": False,
                    "local_interaction_status": (
                        "unknown; regional feeding overlap is not a local bird-plant interaction"),
                    "site_bbox_public_plant_points": {
                        name: counts[name] for name in (
                            "Lantana camara", "Jatropha gossypiifolia",
                            "Dichrostachys cinerea", "Abrus precatorius")}}
        note = study["interpretation_gate"]
    elif key == "evidence_summary":
        rows = [
            {"id": "ebtl-summary:birds", "topic": "birds", "finding": "67 species in a local 2024 transit survey", "label": "observed"},
            {"id": "ebtl-summary:snakes", "topic": "snakes", "finding": "14 documented property species; 3 encountered in the three-day 2024 VES", "label": "observed"},
            {"id": "ebtl-summary:elephants", "topic": "elephants", "finding": "two passage events supported by indirect physical signs", "label": "indirect"},
            {"id": "ebtl-summary:nursery", "topic": "nursery", "finding": "110-species/15,000-sapling July 2024 snapshot; 23 taxa named in imported issues", "label": "reported"},
            {"id": "ebtl-summary:invasives", "topic": "non-native management", "finding": "roughly one acre of Eucalyptus removal documented; no local Lantana confirmation", "label": "reported"},
        ]
        note = ("local evidence summary; satellite layers and regional literature are separate "
                "proxy/modelled evidence and are not promoted to local observations")
    else:
        return None

    return {
        "rows": rows, "kind": "records", "source": "Imported EBTL primary evidence",
        "label": label, "grain": "published-evidence-record", "count_admissible": True,
        "query_time": time_value, "region": region, "query_semantics": key,
        "source_metadata": metadata, "note": note,
        "connector_events": connector_events,
    }


# ---------------------------------------------------------------- eBird recent observations
def _ebird_key():
    if os.environ.get("EBIRD_API_KEY"):
        return os.environ["EBIRD_API_KEY"]
    for path in (os.path.expanduser("~/.hermes/secrets/ebird.json"),
                 os.path.expanduser("~/.config/idlisseus/ebird.json")):
        try:
            with open(path) as f:
                key = json.load(f).get("api_key")
            if key:
                return key
        except (OSError, ValueError, AttributeError):
            pass
    return None


def ebird_recent(region, time_value=None, limit=1000):
    key = _ebird_key()
    if not key:
        return {"rows": [], "kind": "records", "source": "eBird", "label": "observed",
                "unavailable": "missing eBird API key", "note": "eBird connector not configured"}
    start, end = _time_window(time_value)
    today = dt.date.today()

    def parse_date(value, end_of_period=False):
        if not value:
            return None
        value = str(value)
        if len(value) == 4:
            return dt.date(int(value), 12 if end_of_period else 1, 31 if end_of_period else 1)
        if len(value) == 7:
            year, month = map(int, value.split("-"))
            day = calendar.monthrange(year, month)[1] if end_of_period else 1
            return dt.date(year, month, day)
        return dt.date.fromisoformat(value[:10])

    if end:
        try:
            end_date = parse_date(end, end_of_period=True)
        except ValueError:
            end_date = today
        if (today - end_date).days > 30:
            return {"rows": [], "kind": "records", "source": "eBird", "label": "observed",
                    "unsupported_time": True,
                    "note": "eBird recent endpoint supports only the preceding 1-30 days"}
    back = 30
    if start:
        try:
            start_date = parse_date(start)
            back = max(1, min(30, (today - start_date).days + 1))
        except ValueError:
            pass
    s, n, w, e = region["bbox"]
    lat, lon = (s + n) / 2, (w + e) / 2
    half_diag_km = 111.0 * math.sqrt(((n - s) / 2) ** 2 +
                                     (((e - w) / 2) * math.cos(math.radians(lat))) ** 2)
    dist = max(1, min(50, int(math.ceil(half_diag_km))))
    params = {"lat": round(lat, 4), "lng": round(lon, 4), "dist": dist,
              "back": back, "maxResults": min(int(limit), 10000), "detail": "simple"}
    raw = _get("https://api.ebird.org/v2/data/obs/geo/recent?" + urllib.parse.urlencode(params),
               headers={"X-eBirdApiToken": key})
    rows = []
    for o in raw:
        olat, olon = o.get("lat"), o.get("lng")
        # The API is radial; SELECT is rectangular. Post-filtering is mandatory.
        if olat is None or olon is None or not (s <= olat <= n and w <= olon <= e):
            continue
        oid = ":".join(str(x) for x in (o.get("subId"), o.get("speciesCode"), o.get("locId"),
                                         o.get("obsDt")))
        rows.append({"id": f"ebird:{oid}", "lat": float(olat), "lon": float(olon),
                     "name": o.get("comName") or o.get("sciName"),
                     "scientific_name": o.get("sciName"), "species_code": o.get("speciesCode"),
                     "count": o.get("howMany"), "time": o.get("obsDt"), "source": "eBird",
                     "location_id": o.get("locId"), "source_record": None,
                     "license": "eBird API Terms of Use"})
    partial = half_diag_km > 50
    return {"rows": rows, "kind": "records", "source": "eBird", "grain": "checklist-observation",
            "label": "proxy" if partial else "observed", "count_admissible": True,
            "region": region, "query_time": time_value,
            "note": f"{len(rows)} recent bird observations after bbox post-filter; {back}-day window"
                    + ("; bbox exceeds the 50 km API radius, so coverage is partial" if partial else "")}


# ---------------------------------------------------------------- admitted published site corpus
def anamalai_survey_sites(region):
    path = os.path.abspath(os.path.join(HERE, "..", "data", "imported", "restoration_sites.csv"))
    s, n, w, e = region["bbox"]
    rows = []
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            lat, lon = float(r["lat"]), float(r["lon"])
            if s <= lat <= n and w <= lon <= e:
                rows.append({"id": f"zenodo10077040:{r['id']}", "lat": lat, "lon": lon,
                             "name": r["id"], "habitat": r["habitat"], "time": None,
                             "source": "Zenodo 10077040/01_sites.csv",
                             "source_record": "https://doi.org/10.5281/zenodo.10077040",
                             "license": "CC-BY-4.0"})
    return {"rows": rows, "kind": "records", "source": "Zenodo 10077040",
            "label": "observed", "grain": "published-survey-site", "count_admissible": True,
            "region": region,
            "note": f"{len(rows)} published vegetation survey sites; these are not restoration interventions"}


def site_center(region):
    """One declared sampling point for site-level raster lookups, never a whole-AOI observation."""
    row = {"id": "site:ebtl-center", "lat": region["lat"], "lon": region["lon"],
           "name": "EBTL site center", "time": None, "source": "SITE_EBTL.json",
           "source_record": None, "license": "project metadata"}
    return {"rows": [row], "kind": "records", "source": "SITE_EBTL.json", "label": "proxy",
            "grain": "declared-site-center", "count_admissible": False, "region": region,
            "note": "1 declared site-center point; raster value is a point proxy, not AOI coverage"}


# ---------------------------------------------------------------- Earth Engine series and point annotations
LANDCOVER_CLASSES = {10: "tree cover", 20: "shrubland", 30: "grassland", 40: "cropland",
                     50: "built-up", 60: "bare or sparse vegetation", 70: "snow and ice",
                     80: "permanent water", 90: "herbaceous wetland", 95: "mangroves",
                     100: "moss and lichen"}
LAYER_ALIASES = {
    "elevation": "elevation", "altitude": "elevation",
    "slope": "slope", "terrain slope": "slope",
    "landcover": "landcover", "land cover": "landcover", "land cover class": "landcover",
    "habitat class": "landcover",
    "ndvi": "ndvi", "greenness": "ndvi", "vegetation index": "ndvi",
    "surface water occurrence": "surface_water_occurrence", "water occurrence": "surface_water_occurrence",
    "ecoregion": "ecoregion", "biome": "ecoregion",
    "fire exposure": "fire_exposure", "historical fire exposure": "fire_exposure",
    "fire risk": "fire_exposure", "risk of fire": "fire_exposure",
    "greenness trend": "greenness_trend", "vegetation recovery": "greenness_trend",
    "restoration progress": "greenness_trend", "restoration change": "greenness_trend",
}


def resolve_layer(layer):
    return LAYER_ALIASES.get(" ".join(str(layer).lower().replace("_", " ").replace("-", " ").split()))


def _init_ee():
    import ee
    ee.Initialize(project=os.environ.get("EE_PROJECT", "plantwars"))
    return ee


def ee_ndvi_series(region, time_value=None):
    cache_key = "ee-ndvi-series " + json.dumps({"bbox": region["bbox"], "time": time_value}, sort_keys=True)
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    ee = _init_ee()
    start, end = _time_window(time_value)
    start = start or "2000-02-01"
    # Avoid a partial current year unless the question explicitly requests it.
    end = end or f"{dt.date.today().year}-01-01"
    if len(start) == 4:
        start += "-01-01"
    if len(end) == 4:
        end += "-12-31"
    s, n, w, e = region["bbox"]
    geom = ee.Geometry.Rectangle([w, s, e, n], geodesic=False)
    coll = ee.ImageCollection("MODIS/061/MOD13A3").filterDate(start, end)

    def sample(img):
        good = img.select("NDVI").updateMask(img.select("SummaryQA").lte(1)).multiply(0.0001)
        value = good.reduceRegion(ee.Reducer.mean(), geom, 1000, maxPixels=1e9).get("NDVI")
        return ee.Feature(None, {"t": img.date().format("YYYY-MM"), "value": value})

    features = coll.map(sample).getInfo().get("features", [])
    years = {}
    for f in features:
        p = f.get("properties") or {}
        if p.get("value") is not None:
            years.setdefault(str(p["t"])[:4], []).append(float(p["value"]))
    rows = [{"t": y, "value": round(sum(v) / len(v), 6)} for y, v in sorted(years.items())]
    out = {"rows": rows, "kind": "series", "source": "MODIS/061/MOD13A3 via Earth Engine",
           "label": "proxy", "unit": "NDVI", "grain": "annual-bbox-mean",
           "query_time": time_value, "region": region,
           "note": f"{len(rows)} annual QA-masked NDVI means over the geocoder bbox; bbox mean is a place proxy"}
    _cache_put(cache_key, out)
    return out


def _annotation_image(ee, canonical, year):
    if canonical in {"elevation", "slope"}:
        dem = ee.Image("NASA/NASADEM_HGT/001").select("elevation")
        return (dem if canonical == "elevation" else ee.Terrain.slope(dem)).rename(canonical)
    if canonical == "landcover":
        return ee.ImageCollection("ESA/WorldCover/v200").first().select("Map").rename(canonical)
    if canonical == "surface_water_occurrence":
        # JRC masks pixels where water was never detected; for an occurrence percentage that
        # state is a measured zero, not missing data.
        return (ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence")
                .unmask(0).rename(canonical))
    if canonical == "ndvi":
        coll = ee.ImageCollection("MODIS/061/MOD13A3").filterDate(f"{year}-01-01", f"{year + 1}-01-01")
        return (coll.select("NDVI").mean().multiply(0.0001).rename(canonical))
    return None


def ee_fire_exposure(records, region, query_time=None, radius_km=5):
    """Typed wrapper over the exact locked origin fire connector."""
    start, end = _time_window(query_time)
    start_year = int((start or "2020")[:4])
    end_year = int((end or "2025")[:4])
    if region is None:
        raise RuntimeError("fire exposure requires an explicit region for exact-AOI comparison")
    return ORIGIN.fire_exposure(records, region, start_year, end_year, radius_km)


def annotate_records(records, layer, query_time=None, region=None):
    canonical = resolve_layer(layer)
    if not canonical:
        return {"rows": records, "kind": "records", "source": "none", "label": "observed",
                "unsupported_layer": True, "note": f"no admitted ecology layer for {layer!r}"}
    if not records:
        return {"rows": [], "kind": "records", "source": "Earth Engine", "label": "observed",
                "measure_field": canonical, "note": "no records to annotate"}
    if canonical == "fire_exposure":
        return ee_fire_exposure(records, region, query_time)
    if canonical == "landcover" and region and all(
            record.get("id") == "site:ebtl-center" for record in records):
        return ORIGIN.landcover_summary(records, region)
    if canonical == "greenness_trend":
        start, end = _time_window(query_time)
        return ORIGIN.greenness_trend(records, int((start or "2019")[:4]),
                                      int((end or "2024")[:4]))
    cache_key = "ee-annotate-v2 " + hashlib.sha256(json.dumps({"records": records, "layer": canonical,
                                                             "time": query_time}, sort_keys=True,
                                                            default=str).encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    ee = _init_ee()
    start, end = _time_window(query_time)
    year = int((end or start or str(dt.date.today().year - 1))[:4])
    if canonical == "ecoregion":
        eco = ee.FeatureCollection("RESOLVE/ECOREGIONS/2017")
        feats = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([r["lon"], r["lat"]]), {"_i": i})
            for i, r in enumerate(records) if r.get("lat") is not None and r.get("lon") is not None])

        def add_ecoregion(f):
            hit = ee.Feature(eco.filterBounds(f.geometry()).first())
            return f.set({"ecoregion": hit.get("ECO_NAME"), "biome": hit.get("BIOME_NAME")})

        got = feats.map(add_ecoregion).getInfo().get("features", [])
        by_i = {int(f["properties"]["_i"]): f["properties"] for f in got}
        rows = [{**r, "ecoregion": by_i.get(i, {}).get("ecoregion"),
                 "biome": by_i.get(i, {}).get("biome")} for i, r in enumerate(records)]
        unit, measure = None, None
    else:
        image = _annotation_image(ee, canonical, year)
        feats = ee.FeatureCollection([
            ee.Feature(ee.Geometry.Point([r["lon"], r["lat"]]), {"_i": i})
            for i, r in enumerate(records) if r.get("lat") is not None and r.get("lon") is not None])
        scale = {"landcover": 10, "elevation": 30, "slope": 30,
                 "surface_water_occurrence": 30, "ndvi": 1000}[canonical]
        got = image.sampleRegions(feats, scale=scale, geometries=False).getInfo().get("features", [])
        by_i = {int(f["properties"]["_i"]): f["properties"].get(canonical) for f in got}
        rows = []
        for i, r in enumerate(records):
            value = by_i.get(i)
            if canonical == "landcover" and value is not None:
                value = LANDCOVER_CLASSES.get(int(value), f"class {int(value)}")
            rows.append({**r, canonical: value})
        unit = {"elevation": "m", "slope": "degree", "ndvi": "NDVI",
                "surface_water_occurrence": "%", "landcover": None}[canonical]
        measure = canonical if canonical != "landcover" else None
    layer_label = "observed" if canonical in {"elevation", "ndvi"} else "modelled"
    out = {"rows": rows, "kind": "records", "source": {
               "elevation": "NASA/NASADEM_HGT/001", "slope": "NASADEM+ee.Terrain.slope",
               "landcover": "ESA/WorldCover/v200", "surface_water_occurrence": "JRC/GSW1_4",
               "ndvi": "MODIS/061/MOD13A3", "ecoregion": "RESOLVE/ECOREGIONS/2017"}[canonical],
           "label": layer_label, "measure_field": measure, "unit": unit,
           "layer": canonical, "layer_year": year if canonical == "ndvi" else None,
           "note": f"annotated {len(rows)} records with {canonical}"}
    _cache_put(cache_key, out)
    return out


# ---------------------------------------------------------------- transfer gates and estimates
TRANSFER_ABSENCE_ASK = ("provide designed presence/absence survey points; the admitted model uses "
                        "deterministic background points as pseudo-absence")


def transfer_gate(src, target, method, min_occurrences=20):
    """Method-specific ESTIMATE admissibility, adapted from the origin's dual gate.

    ``feature`` is local AlphaEarth nearest-neighbour analogy. ``envelope`` is WorldClim
    multivariate range coverage (MESS-style). ``interpolate`` is only for an actual numeric
    measurement sampled at points. Geographic containment is reported, but never impersonates an
    environmental envelope.
    """
    rows = [r for r in src.get("rows", [])
            if isinstance(r.get("lat"), (int, float)) and isinstance(r.get("lon"), (int, float))]
    if method == "interpolate":
        field = src.get("measure_field")
        numeric = [r for r in rows if isinstance(r.get(field), (int, float))] if field else []
        if len(numeric) < 5:
            return {"pass": False, "strength": "numeric-support",
                    "reason": f"interpolation needs >=5 point measurements; found {len(numeric)}",
                    "ask": "provide georeferenced numeric measurements and units"}
        s, n, w, e = target["bbox"]
        inside = all(min(r["lat"] for r in numeric) <= x <= max(r["lat"] for r in numeric)
                     for x in (s, n)) and all(
                     min(r["lon"] for r in numeric) <= x <= max(r["lon"] for r in numeric)
                     for x in (w, e))
        return {"pass": inside, "strength": "interpolation-support",
                "reason": "target is inside numeric donor support" if inside else
                          "target is outside numeric donor support; interpolation would extrapolate",
                "ask": None if inside else "collect measurements that bracket the target"}

    if src.get("grain") != "occurrence":
        return {"pass": False, "strength": "type",
                "reason": f"{method} presence transfer requires occurrence-grain donor records",
                "ask": "provide georeferenced species occurrence records"}
    if len(rows) < min_occurrences:
        return {"pass": False, "strength": "sample-size",
                "reason": f"only {len(rows)} usable donor occurrences; require >={min_occurrences}",
                "ask": f"collect at least {min_occurrences} donor occurrences plus absence surveys"}

    # If direct donor observations already cover the AOI, SELECT is more honest than a model.
    s, n, w, e = target["bbox"]
    overlap = sum(1 for r in rows if s <= r["lat"] <= n and w <= r["lon"] <= e) / len(rows)
    if overlap >= 0.3:
        return {"pass": False, "strength": "observed-overlap", "overlap_fraction": round(overlap, 3),
                "reason": "donor observations already substantially overlap the target",
                "ask": "use observed records for the target instead of ESTIMATE"}

    start, end = _time_window(src.get("query_time"))
    year = int((end or start or "2023")[:4])
    cache_key = "origin-predict-gate-v1 " + hashlib.sha256(json.dumps({
        "method": method, "year": year, "target": target["bbox"],
        "rows": [[round(r["lat"], 5), round(r["lon"], 5)] for r in rows]
    }, sort_keys=True).encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        if cached.get("strength") == "AlphaEarth-NN-analog":
            cached.setdefault("target_analog_fraction_threshold", 0.5)
        elif cached.get("strength") == "WorldClim-MESS-envelope":
            cached.setdefault("target_in_envelope_fraction_threshold", 0.8)
        return cached

    if method not in {"feature", "envelope"}:
        out = {"pass": False, "strength": "method", "reason": f"unsupported transfer method {method}",
               "ask": "choose feature, envelope, or interpolate"}
    else:
        raw = ORIGIN.predict_gate(rows, target, year=year)
        if method == "feature":
            frac = raw.get("frac_aoi_analog") or 0
            passed = raw.get("verdict") == "transfer_rf" and frac >= 0.5
            out = {"pass": passed, "strength": "AlphaEarth-NN-analog",
                   "year": year, "analog_floor": raw.get("emb_analog_floor"),
                   "mean_nearest_cosine": raw.get("emb_nn_cosine_mean"),
                   "target_analog_fraction": frac,
                   "target_analog_fraction_threshold": 0.5,
                   "reason": raw.get("why"),
                   "ask": None if passed else "collect local target observations",
                   "origin_verdict": raw.get("verdict")}
        else:
            frac = raw.get("climate_mess_frac_in_envelope") or 0
            passed = frac >= 0.8
            out = {"pass": passed, "strength": "WorldClim-MESS-envelope",
                   "year": year, "target_in_envelope_fraction": frac,
                   "target_in_envelope_fraction_threshold": 0.8,
                   "reason": raw.get("why"),
                   "ask": None if passed else
                          "collect local data; climate projection would extrapolate",
                   "origin_verdict": raw.get("verdict")}
    _cache_put(cache_key, out)
    return out


def _presence_model(src, target, method, gate):
    """Normalize the locked origin predictor after a successful environmental gate."""
    rows = [r for r in src["rows"] if "lat" in r and "lon" in r]
    start, end = _time_window(src.get("query_time"))
    year = int((end or start or "2023")[:4])
    cache_key = "origin-presence-model-v1 " + hashlib.sha256(json.dumps({
        "method": method, "year": year, "target": target["bbox"],
        "rows": [[round(r["lat"], 5), round(r["lon"], 5)] for r in rows]
    }, sort_keys=True).encode()).hexdigest()
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached
    raw = (ORIGIN.predict_presence(rows, target, year=year) if method == "feature" else
           ORIGIN.predict_sdm(rows, target, year=year))
    fraction = (raw.get("modelled_present_fraction") if method == "feature" else
                raw.get("modelled_suitable_fraction"))
    accuracy = raw.get("test_accuracy")
    row = {"lat": target["lat"], "lon": target["lon"],
           "target": target.get("name"), "suitability_fraction": round(float(fraction), 4),
           "test_accuracy": accuracy,
           "method": "origin AlphaEarth RF" if method == "feature" else "origin WorldClim RF",
           "model_year": year,
           "top_feature_bands": raw.get("top_feature_bands"),
           "modelled": True}
    out = {"rows": [row], "kind": "field", "source": row["method"], "label": "modelled",
           "grain": "target-bbox-suitability-fraction", "measure_field": "suitability_fraction",
           "unit": "fraction", "gate": gate,
           "note": (f"MODELLED presence suitability using the locked {row['method']} connector "
                    f"after its gate passed; model year {year}; "
                    f"{TRANSFER_ABSENCE_ASK}; occurrence bias, spatial autocorrelation, land-use, "
                    "biotic interactions and dispersal remain limitations")}
    _cache_put(cache_key, out)
    return out


def estimate_transfer(src, target, method):
    gate = transfer_gate(src, target, method)
    if not gate.get("pass"):
        return {"gate": gate, "unavailable": "gate_failed"}
    if method in {"feature", "envelope"}:
        return _presence_model(src, target, method, gate)
    # Deterministic inverse-distance interpolation at the target centroid. Gate ensures the target
    # is bracketed and there are at least five numeric source measurements.
    field = src["measure_field"]
    weighted, weights = 0.0, 0.0
    for r in src["rows"]:
        if not isinstance(r.get(field), (int, float)):
            continue
        d = max(0.001, math.sqrt((r["lat"] - target["lat"]) ** 2 +
                                 (r["lon"] - target["lon"]) ** 2))
        weight = 1.0 / (d * d)
        weighted += weight * r[field]
        weights += weight
    value = weighted / weights
    return {"rows": [{"lat": target["lat"], "lon": target["lon"], field: value,
                      "target": target.get("name"), "modelled": True}],
            "kind": "field", "source": "inverse-distance interpolation", "label": "modelled",
            "grain": "target-centroid", "measure_field": field, "unit": src.get("unit"),
            "gate": gate, "note": "MODELLED inverse-distance interpolation inside donor support"}


# ---------------------------------------------------------------- OSM Overpass (point entities)
# Map lay entity words -> OSM tag filters. The resolver's job (capabilities.md): normalize the
# spoken name, flag ambiguity, don't guess silently.
OSM_TAGS = {
    "clinic": '["amenity"~"clinic|doctors"]', "hospital": '["amenity"="hospital"]',
    "pharmacy": '["amenity"="pharmacy"]', "doctor": '["amenity"~"clinic|doctors"]',
    "health": '["amenity"~"clinic|doctors|hospital|pharmacy"]',
    "school": '["amenity"="school"]', "university": '["amenity"="university"]',
    "college": '["amenity"="college"]', "kindergarten": '["amenity"="kindergarten"]',
    "library": '["amenity"="library"]',
    "restaurant": '["amenity"="restaurant"]', "cafe": '["amenity"="cafe"]',
    "market": '["amenity"="marketplace"]', "shop": '["shop"]',
    "supermarket": '["shop"="supermarket"]', "bank": '["amenity"="bank"]',
    "atm": '["amenity"="atm"]', "hotel": '["tourism"="hotel"]', "fuel": '["amenity"="fuel"]',
    "water_point": '["amenity"="drinking_water"]', "toilet": '["amenity"="toilets"]',
    "bus_stop": '["highway"="bus_stop"]', "bus": '["highway"="bus_stop"]',
    "bus_station": '["amenity"="bus_station"]',
    "park": '["leisure"="park"]',
    "playground": '["leisure"="playground"]', "post_office": '["amenity"="post_office"]',
    "police": '["amenity"="police"]', "place_of_worship": '["amenity"="place_of_worship"]',
    "community_centre": '["amenity"="community_centre"]',
}


def _tokens(s):
    """lowercase word-tokens, underscore/space-insensitive, naive singular."""
    words = s.lower().replace("_", " ").replace("-", " ").split()
    return {w.rstrip("s") if len(w) > 3 else w for w in words} - {"of", "to", "the", "a", "an", "in"}


def _tok_eq(a, b):
    """prefix-tolerant token equality: 'use'~'user', 'enrol'~'enrollment'."""
    return a == b or (len(a) >= 3 and b.startswith(a)) or (len(b) >= 3 and a.startswith(b))


def _key_covered(key, entity_tokens):
    """ALL of the key's tokens appear (prefix-tolerantly) in the entity. DIRECTIONAL on purpose:
    entity⊆key matching let bare 'school' hit 'school enrollment' and silently route an amenity
    count to an indicator series — wrong-source answers that score green (tick-008 finding)."""
    return all(any(_tok_eq(kt, et) for et in entity_tokens) for kt in _tokens(key))


def osm_resolve_tag(entity):
    """Return (tag_filter, canonical, ambiguous_alternatives).

    Token-based: 'bus stop' matches 'bus_stop', 'health clinics' matches 'clinic'. Every
    language boundary needs normalization, not exact/substring matching (tick-004-ds finding)."""
    e = entity.lower().strip()
    for k, tag in OSM_TAGS.items():
        if k == e or k == e.rstrip("s"):
            return tag, k, []
    et = _tokens(entity)
    # exact token-set match first, then DIRECTIONAL coverage (all key tokens in the entity)
    exact = [k for k in OSM_TAGS if _tokens(k) == et]
    if exact:
        return OSM_TAGS[exact[0]], exact[0], []
    hits = [k for k in OSM_TAGS if _key_covered(k, et)]
    if len(hits) == 1:
        return OSM_TAGS[hits[0]], hits[0], []
    if len(hits) > 1:
        best = max(hits, key=lambda k: len(_tokens(k) & et))
        return OSM_TAGS[best], best, hits  # ambiguous: pick best-overlap but flag
    return None, None, []


def osm_select(entity, region, limit=200):
    tag, canon, ambig = osm_resolve_tag(entity)
    if not tag:
        return {"rows": [], "kind": "records", "source": "osm",
                "note": f"no OSM tag mapping for {entity!r}", "resolved": None, "ambiguous": []}
    s, n, w, e = region["bbox"]
    bbox = f"{s},{w},{n},{e}"
    ql = f'[out:json][timeout:40];(node{tag}({bbox});way{tag}({bbox}););out center {limit};'
    d = _get("https://overpass-api.de/api/interpreter", data="data=" + urllib.parse.quote(ql),
             method="POST")
    rows = []
    for el in d.get("elements", []):
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None:
            continue
        rows.append({"id": el.get("id"), "lat": lat, "lon": lon,
                     "name": (el.get("tags") or {}).get("name"), "time": None})
    return {"rows": rows, "kind": "records", "source": "osm-overpass",
            "resolved": canon, "ambiguous": ambig,
            "note": f"{len(rows)} {canon} in bbox" + (f"; AMBIGUOUS among {ambig}" if ambig else "")}


# ---------------------------------------------------------------- World Bank (indicator series)
# lay phrase -> WB indicator code (curated; resolver flags when unmapped).
WB_INDICATORS = {
    "gdp per capita": "NY.GDP.PCAP.CD", "gdp": "NY.GDP.MKTP.CD",
    "population": "SP.POP.TOTL", "urban population": "SP.URB.TOTL.IN.ZS",
    "unemployment": "SL.UEM.TOTL.ZS", "poverty": "SI.POV.DDAY",
    "internet users": "IT.NET.USER.ZS", "internet use": "IT.NET.USER.ZS",
    "internet": "IT.NET.USER.ZS",
    "mobile subscriptions": "IT.CEL.SETS.P2", "mobile": "IT.CEL.SETS.P2",
    "electricity access": "EG.ELC.ACCS.ZS",
    "school enrollment": "SE.PRM.ENRR", "secondary enrollment": "SE.SEC.ENRR",
    "electricity": "EG.ELC.ACCS.ZS",
    "literacy": "SE.ADT.LITR.ZS", "inflation": "FP.CPI.TOTL.ZG",
    "labor force": "SL.TLF.TOTL.IN", "trade": "NE.TRD.GNFS.ZS",
    "life expectancy": "SP.DYN.LE00.IN", "tourism arrivals": "ST.INT.ARVL",
    "health expenditure": "SH.XPD.CHEX.GD.ZS", "gdp growth": "NY.GDP.MKTP.KD.ZG",
}


def wb_resolve_indicator(entity):
    """Token-based like osm_resolve_tag: 'access to electricity' matches 'electricity access',
    'the inflation rate' matches 'inflation'. DIRECTIONAL: all key tokens must appear in the
    entity — bare 'school' must NOT hit 'school enrollment' (that mis-routed amenity counts
    to indicator series with green scores; tick-008)."""
    e = entity.lower().strip()
    if e in WB_INDICATORS:
        return WB_INDICATORS[e], e, []
    hits = [k for k in WB_INDICATORS if k in e]  # key phrase inside entity phrase only
    if hits:
        best = max(hits, key=len)
        return WB_INDICATORS[best], best, (hits if len(hits) > 1 else [])
    et = _tokens(entity) - {"rate", "level", "number", "total"}
    tok_hits = [k for k in WB_INDICATORS if _key_covered(k, et)]
    if tok_hits:
        best = max(tok_hits, key=lambda k: len(_tokens(k) & et))
        return WB_INDICATORS[best], best, (tok_hits if len(tok_hits) > 1 else [])
    return None, None, []


def _wb_country_list():
    return _get("https://api.worldbank.org/v2/country?format=json&per_page=400")


def _norm(s):
    return "".join(ch for ch in s.lower() if ch.isalnum())


def wb_resolve_iso(region):
    """Resolve to a World Bank 3-letter ISO code. Prefer the ORIGINAL user place string and the
    English display name (not the localized Nominatim name, which broke URLs earlier).
    Compares on alphanumerics only so 'Vietnam' matches WB's 'Viet Nam'."""
    candidates = []
    for key in ("orig", "country", "iso2"):
        if region.get(key):
            candidates.append(region[key])
    if region.get("name"):
        parts = [p.strip() for p in region["name"].split(",")]
        candidates += [parts[-1], parts[0]]
    cc = _wb_country_list()
    if isinstance(cc, list) and len(cc) > 1:
        rows = [(c.get("name", ""), c.get("id", "")) for c in cc[1] if c.get("region", {}).get("id") != "NA"]
        norm_names = {_norm(nm): iso for nm, iso in rows}
        norm_ids = {_norm(iso): iso for _, iso in rows}
        for cand in candidates:
            cn = _norm(cand)
            if cn in norm_ids:
                return norm_ids[cn]
            if cn in norm_names:
                return norm_names[cn]
            for nm, iso in norm_names.items():
                if cn and (cn == nm or (len(cn) > 3 and cn in nm)):
                    return iso
    return None


# indicators whose WB series are UPSTREAM-MODELED (ILO modeled estimates etc) — spec v2.2:
# a connector must declare when its "observations" are themselves model outputs (livelihoods
# sector finding: modeled stats entering SELECT were falsely tainted observed).
WB_MODELED = {"SL.UEM.TOTL.ZS", "SL.TLF.TOTL.IN", "SI.POV.DDAY"}


def wb_series(entity, region, time=None):
    code, canon, ambig = wb_resolve_indicator(entity)
    if not code:
        return {"rows": [], "kind": "series", "source": "worldbank",
                "note": f"no WB indicator for {entity!r}", "resolved": None}
    iso = wb_resolve_iso(region)
    if not iso:
        return {"rows": [], "kind": "series", "source": "worldbank", "resolved": canon,
                "note": f"could not resolve country for {region.get('orig') or region.get('name')!r}"}
    url = (f"https://api.worldbank.org/v2/country/{urllib.parse.quote(iso)}/indicator/{code}"
           f"?format=json&per_page=300")
    d = _get(url)
    rows = []
    if isinstance(d, list) and len(d) > 1 and d[1]:
        for r in d[1]:
            if r.get("value") is None:
                continue
            rows.append({"t": r["date"], "value": r["value"]})
    rows.sort(key=lambda x: x["t"])
    note_extra = ""
    if time and isinstance(time, dict):
        s, e = time.get("start", "")[:4], time.get("end", "")[:4]
        windowed = [r for r in rows if (not s or r["t"] >= s) and (not e or r["t"] <= e)]
        # nearest-year fallback: a single-year window on a SPARSE yearly series (UNESCO-style
        # gaps) must not read as "no data at this place" — take the nearest year within ±3 and
        # SAY SO in provenance (tick-008 breakers: 3x enrollment CHANGE golds died on this).
        if not windowed and s and e and s == e and rows:
            target = int(s)
            near = min(rows, key=lambda r: abs(int(r["t"]) - target))
            if abs(int(near["t"]) - target) <= 3:
                windowed = [near]
                note_extra = f" (no {s} value; nearest year {near['t']} used)"
        rows = windowed
    lbl = "modelled" if code in WB_MODELED else "observed"
    return {"rows": rows, "kind": "series", "source": "worldbank", "label": lbl,
            "resolved": canon, "ambiguous": ambig, "indicator": code, "iso": iso,
            "note": f"{len(rows)} yearly points of {canon} for {iso}{note_extra}"
                    + (" (upstream ILO/WB modeled estimate)" if lbl == "modelled" else "")}


if __name__ == "__main__":
    import sys
    fn = sys.argv[1]
    reg = resolve_region(sys.argv[2])
    ent = sys.argv[3] if len(sys.argv) > 3 else "clinic"
    out = {"osm": osm_select, "wb": wb_series}[fn](ent, reg)
    print(json.dumps({**out, "rows": out["rows"][:3], "n": len(out["rows"])}, indent=2, default=str))
