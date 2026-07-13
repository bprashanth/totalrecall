"""Cross-sector connectors — the deterministic 'hands' the executor calls.

Every source here is KEYLESS and covers a different civic/economic sector, so the algebra is
tested across domains rather than one:
  - OSM Overpass    -> point entities by place (health access, retail, education, civic amenities)
  - World Bank      -> indicator series by country over time (economy / development)
  - Nominatim       -> place name -> bbox/centroid (the REGION resolver)

Contract (matches capabilities.md): points-in / points-out. A connector returns a dict:
  {"rows": [...], "kind": "records|series|scalar|field", "source": "...", "note": "..."}
Rows for records carry lat/lon/time/attrs. Series rows carry {t, value}. Everything is cached
on disk so the loop is cheap and resilient to rate limits.
"""
import json
import hashlib
import http.client
import csv
import io
import os
import re
import time
import urllib.parse
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "data")
os.makedirs(CACHE, exist_ok=True)

UA = "place-memory-algebra-benchmark/0.1 (research; contact prashanthseven@gmail.com)"


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
    # dedupe repeated comma segments ("Brazil, Brazil" → "Brazil"): a redundant segment sent
    # Nominatim to an unrelated same-named hamlet in another country (tick-009)
    segs, seen = [], set()
    for p in [p.strip() for p in place.split(",")]:
        if p.lower() not in seen and p:
            segs.append(p)
            seen.add(p.lower())
    place = ", ".join(segs)
    # Curated statistical-region names are not safe free-text geocoder queries: Nominatim has
    # returned "Berlin Region" in Ontario for the exact Eurostat alias.  Qualify these known
    # boundaries while retaining the original surface for downstream source resolvers.
    curated_queries = {
        "ile de france": "Ile-de-France, France",
        "paris region": "Ile-de-France, France",
        "berlin region": "Berlin, Germany",
        "comunidad de madrid": "Community of Madrid, Spain",
        "madrid region": "Community of Madrid, Spain",
        "catalonia": "Catalonia, Spain",
        "lombardy": "Lombardy, Italy",
        "warsaw capital region": "Warsaw metropolitan area, Poland",
    }
    query_place = curated_queries.get(_ascii_norm(place), place)
    q = urllib.parse.urlencode({"q": query_place, "format": "json", "limit": 10})
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
    "market": '["amenity"="marketplace"]', "marketplace": '["amenity"="marketplace"]',
    "shop": '["shop"]',
    "supermarket": '["shop"="supermarket"]', "bank": '["amenity"="bank"]',
    "atm": '["amenity"="atm"]', "hotel": '["tourism"="hotel"]', "fuel": '["amenity"="fuel"]',
    # -- livelihoods sector (verified across Bengaluru/Nairobi/Accra; FINDINGS.md 2026-07-12) --
    "coworking_space": '["office"="coworking"]',
    "coworking_office": '["office"="coworking"]',
    "coworking": '["office"="coworking"]',
    "co_working_space": '["office"="coworking"]', "co_working": '["office"="coworking"]',
    "craft_workshop": '["craft"]', "artisan_workshop": '["craft"]',
    # parser truncation insurance found tick-001; broad craft=* is the intended source axis
    "craft": '["craft"]', "workshop": '["craft"]',
    "water_point": '["amenity"="drinking_water"]', "toilet": '["amenity"="toilets"]',
    "bus_stop": '["highway"="bus_stop"]', "bus": '["highway"="bus_stop"]',
    "bus_station": '["amenity"="bus_station"]',
    "park": '["leisure"="park"]',
    "playground": '["leisure"="playground"]', "post_office": '["amenity"="post_office"]',
    "police": '["amenity"="police"]', "police_station": '["amenity"="police"]',
    "place_of_worship": '["amenity"="place_of_worship"]',
    "community_centre": '["amenity"="community_centre"]',
    # Verified in Bengaluru against current OSM data (81 rows, 2026-07-13).
    "metro_station": '["railway"="station"]["station"="subway"]',
    "subway_station": '["railway"="station"]["station"="subway"]',
}


def _tokens(s):
    """lowercase word-tokens, underscore/space-insensitive, naive singular."""
    words = s.lower().replace("_", " ").replace("-", " ").split()
    return {w.rstrip("s") if len(w) > 3 else w for w in words} - {"of", "to", "the", "a", "an", "in"}


def _tok_eq(a, b):
    """Token equality after `_tokens` has performed bounded plural normalization.

    Arbitrary prefixes made distinct lexemes equal (`work`/`workshop`, `bus`/`business`) and
    silently routed source gaps. Morphological and lay variants belong in declared alias maps.
    """
    return a == b


def _key_covered(key, entity_tokens):
    """A declared key covers the whole normalized entity phrase.

    The earlier one-way subset admitted semantic modifiers such as `night market`, `main
    marketplace`, and `coworking access` as the broader base entity. Exact aliases retain safe
    plural/lay forms while unknown subtypes fail closed.
    """
    key_tokens = _tokens(key)
    return (all(any(_tok_eq(kt, et) for et in entity_tokens) for kt in key_tokens) and
            all(any(_tok_eq(et, kt) for kt in key_tokens) for et in entity_tokens))


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


def osm_select(entity, region, limit=500):
    tag, canon, ambig = osm_resolve_tag(entity)
    if not tag:
        return {"rows": [], "kind": "records", "source": "osm",
                "note": f"no OSM tag mapping for {entity!r}", "resolved": None, "ambiguous": []}
    s, n, w, e = region["bbox"]
    bbox = f"{s},{w},{n},{e}"
    # Fetch one beyond the safety cap so a count of exactly `limit` is never silently presented
    # as complete (livelihoods generated-bank admission finding, 2026-07-12).
    ql = f'[out:json][timeout:40];(node{tag}({bbox});way{tag}({bbox}););out center {limit + 1};'
    d = _get("https://overpass-api.de/api/interpreter", data="data=" + urllib.parse.quote(ql),
             method="POST")
    rows = []
    for el in d.get("elements", []):
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None:
            continue
        tags = el.get("tags") or {}
        rows.append({"id": el.get("id"), "lat": lat, "lon": lon,
                     "name": tags.get("name"), "time": None, "attrs": tags})
    truncated = len(rows) > limit
    if truncated:
        rows = rows[:limit]
    return {"rows": rows, "kind": "records", "source": "osm-overpass",
            "resolved": canon, "ambiguous": ambig,
            "truncated": truncated,
            "note": ((f">={limit + 1} {canon} in bbox; source_truncated at {limit} — exact "
                      f"count/spatial coverage unavailable") if truncated else
                     f"{len(rows)} {canon} in bbox") +
                    (f"; AMBIGUOUS among {ambig}" if ambig else "")}


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
    # -- livelihoods indicators (all codes returned 1990/91–2025 rows for IND/KEN/GHA;
    #    see FINDINGS.md census 2026-07-12) --
    "self employment": "SL.EMP.SELF.ZS", "self employed": "SL.EMP.SELF.ZS",
    "self employed workers": "SL.EMP.SELF.ZS",
    "vulnerable employment": "SL.EMP.VULN.ZS",
    "labor force participation": "SL.TLF.CACT.ZS", "labour force participation": "SL.TLF.CACT.ZS",
    "youth unemployment": "SL.UEM.1524.ZS",
    "wage and salaried workers": "SL.EMP.WORK.ZS", "wage and salaried": "SL.EMP.WORK.ZS",
    "salaried workers": "SL.EMP.WORK.ZS",
    "wage and salaried workers share": "SL.EMP.WORK.ZS",
    "wage and salaried workers as a share of employment": "SL.EMP.WORK.ZS",
    "employment in services": "SL.SRV.EMPL.ZS", "service employment": "SL.SRV.EMPL.ZS",
    "employment in agriculture": "SL.AGR.EMPL.ZS", "agricultural employment": "SL.AGR.EMPL.ZS",
    # Verified through the World Bank v2 API for Brazil, India, and Kenya (40/8/8 rows).
    "gini coefficient": "SI.POV.GINI", "gini index": "SI.POV.GINI",
}


def wb_resolve_indicator(entity):
    """Token-based like osm_resolve_tag: 'access to electricity' matches 'electricity access',
    'the inflation rate' matches 'inflation'. DIRECTIONAL: all key tokens must appear in the
    entity — bare 'school' must NOT hit 'school enrollment' (that mis-routed amenity counts
    to indicator series with green scores; tick-008)."""
    e = entity.lower().strip()
    if e in WB_INDICATORS:
        return WB_INDICATORS[e], e, []
    def _ambig(hits):
        # Multiple lay aliases of one code are synonyms, not source ambiguity.
        return hits if len({WB_INDICATORS[h] for h in hits}) > 1 else []
    et = _tokens(entity) - {"rate", "level", "number", "total"}
    tok_hits = [k for k in WB_INDICATORS
                if _key_covered(k, et) or _key_covered(k, _tokens(entity))]
    if tok_hits:
        best = max(tok_hits, key=lambda k: len(_tokens(k) & et))
        return WB_INDICATORS[best], best, _ambig(tok_hits)
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
    explicit_scope = bool(candidates)
    if not explicit_scope and region.get("name"):
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
        # Never infer a national statistical scope from the country suffix of a geocoded city or
        # region.  `orig="Ile de France"` resolving to a display name ending in France must not
        # silently become a World Bank France observation.
    return None


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
    return {"rows": rows, "kind": "series", "source": "worldbank",
            "resolved": canon, "ambiguous": ambig, "indicator": code, "iso": iso,
            "note": f"{len(rows)} yearly points of {canon} for {iso}{note_extra}"}


# ---------------------------------------------------------------- ILOSTAT bulk API (survey series)
# Keep subgroup choices explicit in the lay entity. Frozen v2.1 has no FILTER node, so silently
# extracting sex/industry adjectives from arbitrary prose would manufacture missing algebra.
ILO_INDICATORS = {
    "informal employment rate": {
        "code": "SDG_0831_SEX_ECO_RT_A", "sex": "SEX_T",
        "classif1": "ECO_SECTOR_TOTAL", "unit": "percent"},
    "female informal employment rate": {
        "code": "SDG_0831_SEX_ECO_RT_A", "sex": "SEX_F",
        "classif1": "ECO_SECTOR_TOTAL", "unit": "percent"},
    "male informal employment rate": {
        "code": "SDG_0831_SEX_ECO_RT_A", "sex": "SEX_M",
        "classif1": "ECO_SECTOR_TOTAL", "unit": "percent"},
    "informal employment rate in agriculture": {
        "code": "SDG_0831_SEX_ECO_RT_A", "sex": "SEX_T",
        "classif1": "ECO_SECTOR_AGR", "unit": "percent"},
    "average weekly hours worked": {
        "code": "HOW_TEMP_SEX_NB_A", "sex": "SEX_T", "unit": "hours/week"},
    "female average weekly hours worked": {
        "code": "HOW_TEMP_SEX_NB_A", "sex": "SEX_F", "unit": "hours/week"},
    "male average weekly hours worked": {
        "code": "HOW_TEMP_SEX_NB_A", "sex": "SEX_M", "unit": "hours/week"},
    "labour underutilization rate": {
        "code": "LUU_XLU4_SEX_RT_A", "sex": "SEX_T", "unit": "percent"},
    "labor underutilization rate": {
        "code": "LUU_XLU4_SEX_RT_A", "sex": "SEX_T", "unit": "percent"},
    "time related underemployment rate": {
        "code": "EMP_XTRU_SEX_RT_A", "sex": "SEX_T", "unit": "percent"},
}

# Reviewed lay-name aliases. These omit only a conventional unit/head word; source provenance
# still reports the exact curated rate/hours slice. Source-defining modifiers remain mandatory.
for alias, canonical in {
    "informal employment": "informal employment rate",
    "informal employment in agriculture": "informal employment rate in agriculture",
    "average weekly hours": "average weekly hours worked",
    "female average weekly hours": "female average weekly hours worked",
    "male average weekly hours": "male average weekly hours worked",
    "labour underutilization": "labour underutilization rate",
    "labor underutilization": "labor underutilization rate",
}.items():
    ILO_INDICATORS[alias] = ILO_INDICATORS[canonical]


def _entity_norm(s):
    value = " ".join(s.lower().replace("-", " ").replace("_", " ").split()).rstrip(" .?")
    return re.sub(r"\s+specifically$", "", value)


def ilo_resolve_indicator(entity):
    """Return a curated ILO table/slice only for an explicit supported entity phrase."""
    key = _entity_norm(entity)
    spec = ILO_INDICATORS.get(key)
    return (spec, key, []) if spec else (None, None, [])


def _ilo_rows(code):
    # The official bulk endpoint is table-at-a-time. CSV avoids a second binary cache format and
    # remains below a few MB for the curated tables. _get supplies the research UA and disk cache.
    url = f"https://rplumber.ilo.org/data/indicator/?format=.csv&id={urllib.parse.quote(code)}"
    text = _get(url, is_json=False, timeout=90)
    return list(csv.DictReader(io.StringIO(text.lstrip("\ufeff"))))


def ilo_series(entity, region, time=None):
    spec, canon, _ = ilo_resolve_indicator(entity)
    if not spec:
        return {"rows": [], "kind": "series", "source": "ilostat",
                "note": f"no curated ILOSTAT indicator for {entity!r}", "resolved": None}
    iso = wb_resolve_iso(region)  # both sources use ISO alpha-3 for the adopted countries
    if not iso:
        return {"rows": [], "kind": "series", "source": "ilostat", "resolved": canon,
                "note": f"could not resolve country for {region.get('orig') or region.get('name')!r}"}
    candidates = []
    for row in _ilo_rows(spec["code"]):
        if row.get("ref_area") != iso or row.get("sex") != spec["sex"]:
            continue
        if spec.get("classif1") and row.get("classif1") != spec["classif1"]:
            continue
        # M is explicitly model-based extrapolation. These Round-2 mappings are an observed-source
        # stratum; modeled ILO tables require evidence-label support proposed separately.
        if row.get("obs_status") == "M" or not row.get("obs_value"):
            continue
        candidates.append(row)
    if not candidates:
        return {"rows": [], "kind": "series", "source": "ilostat", "resolved": canon,
                "indicator": spec["code"], "iso": iso, "unit": spec["unit"],
                "note": f"no non-model-extrapolated {canon} rows for {iso}"}

    # National sources can overlap. Pick one coherent source series deterministically instead of
    # mixing survey vintages. Longest distinct-year coverage wins, then latest year, then code;
    # disclose the choice and all alternatives in provenance.
    grouped = {}
    for row in candidates:
        grouped.setdefault(row["source"], []).append(row)
    chosen_source, chosen = max(
        grouped.items(),
        key=lambda item: (len({r["time"] for r in item[1]}),
                          max(r["time"] for r in item[1]), item[0]))
    by_year = {}
    conflicts = []
    for row in chosen:
        value = float(row["obs_value"])
        if row["time"] in by_year and by_year[row["time"]] != value:
            conflicts.append(row["time"])
        by_year[row["time"]] = value
    if conflicts:
        return {"rows": [], "kind": "series", "source": "ilostat", "resolved": canon,
                "indicator": spec["code"], "iso": iso, "unit": spec["unit"],
                "note": f"conflicting values within ILOSTAT source {chosen_source}: {sorted(set(conflicts))}"}
    rows = [{"t": year, "value": value} for year, value in sorted(by_year.items())]
    if time and isinstance(time, dict):
        start, end = time.get("start", "")[:4], time.get("end", "")[:4]
        rows = [r for r in rows if (not start or r["t"] >= start) and
                (not end or r["t"] <= end)]
    statuses = sorted({r.get("obs_status") or "unflagged" for r in chosen})
    alternatives = sorted(grouped)
    return {"rows": rows, "kind": "series", "source": "ilostat", "resolved": canon,
            "indicator": spec["code"], "iso": iso, "unit": spec["unit"],
            "source_code": chosen_source, "source_alternatives": alternatives,
            "note": (f"{len(rows)} annual {spec['unit']} points of {canon} for {iso}; "
                     f"ILOSTAT source {chosen_source} selected from {alternatives}; "
                     f"observation flags {statuses}; model-extrapolated rows excluded")}


# ---------------------------------------------------------------- Eurostat (NUTS-2 annual series)
# Curated names keep region resolution deterministic while Round 2 evaluates the new subnational
# grain. Codes and labels were verified against the queried dataset dimensions, not geocoded by
# proximity (which cannot distinguish a city from its statistical region).
EUROSTAT_GEOS = {
    "ile de france": "FR10", "paris region": "FR10", "fr10": "FR10",
    "berlin": "DE30", "berlin region": "DE30", "de30": "DE30",
    "comunidad de madrid": "ES30", "madrid region": "ES30", "madrid": "ES30", "es30": "ES30",
    "catalonia": "ES51", "cataluna": "ES51", "es51": "ES51",
    "lombardy": "ITC4", "lombardia": "ITC4", "itc4": "ITC4",
    "warsaw capital region": "PL91", "warszawski stoleczny": "PL91", "pl91": "PL91",
}

EUROSTAT_INDICATORS = {
    "employment rate": {"dataset": "lfst_r_lfe2emprt", "unit": "PC", "sex": "T",
                        "age": "Y20-64", "measure": "percent"},
    "female employment rate": {"dataset": "lfst_r_lfe2emprt", "unit": "PC", "sex": "F",
                               "age": "Y20-64", "measure": "percent"},
    "male employment rate": {"dataset": "lfst_r_lfe2emprt", "unit": "PC", "sex": "M",
                             "age": "Y20-64", "measure": "percent"},
    "employed persons": {"dataset": "lfst_r_lfe2emp", "unit": "THS_PER", "sex": "T",
                         "age": "Y20-64", "measure": "thousand persons"},
    "unemployment rate": {"dataset": "lfst_r_lfu3rt", "unit": "PC", "sex": "T",
                          "age": "Y15-74", "isced11": "TOTAL", "measure": "percent"},
}


def _ascii_norm(s):
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFKD", s)
                   if not unicodedata.combining(ch)).lower().strip()


def eurostat_resolve_geo(region):
    values = []
    for key in ("orig", "name"):
        if region.get(key):
            values.extend(part.strip() for part in region[key].split(","))
    for value in values:
        norm = _ascii_norm(value)
        if norm in EUROSTAT_GEOS:
            return EUROSTAT_GEOS[norm]
    return None


def eurostat_resolve_indicator(entity):
    key = _entity_norm(entity)
    spec = EUROSTAT_INDICATORS.get(key)
    return (spec, key, []) if spec else (None, None, [])


def eurostat_series(entity, region, time=None):
    spec, canon, _ = eurostat_resolve_indicator(entity)
    geo = eurostat_resolve_geo(region)
    if not spec or not geo:
        return {"rows": [], "kind": "series", "source": "eurostat", "resolved": canon,
                "note": (f"unsupported Eurostat indicator {entity!r}" if not spec else
                         f"no curated NUTS-2 region for {region.get('orig') or region.get('name')!r}")}
    query = {"lang": "EN", "geo": geo, "unit": spec["unit"], "sex": spec["sex"],
             "age": spec["age"]}
    if spec.get("isced11"):
        query["isced11"] = spec["isced11"]
    # Fetch/cache the complete fixed-dimension series, then window locally. Putting time in the
    # URL creates one public-API request per benchmark question and defeats source-level caching.
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/" +
           spec["dataset"] + "?" + urllib.parse.urlencode(query))
    data = _get(url, timeout=90)
    dims = data.get("dimension", {})
    times = dims.get("time", {}).get("category", {}).get("index", {})
    # Every non-time dimension is fixed to one category above. Refuse a response whose shape
    # violates that assumption rather than flattening an unintended subgroup into the series.
    ids, sizes = data.get("id", []), data.get("size", [])
    unexpected = {dim: size for dim, size in zip(ids, sizes) if dim != "time" and size != 1}
    if unexpected:
        return {"rows": [], "kind": "series", "source": "eurostat", "resolved": canon,
                "dataset": spec["dataset"], "geo": geo,
                "note": f"unfixed Eurostat dimensions: {unexpected}"}
    values, flags = data.get("value", {}), data.get("status", {}) or {}
    rows = []
    used_flags = set()
    for year, index in sorted(times.items()):
        value = values.get(str(index))
        if value is None:
            continue
        rows.append({"t": year, "value": value})
        if str(index) in flags:
            used_flags.add(flags[str(index)])
    if time and isinstance(time, dict):
        start, end = time.get("start", "")[:4], time.get("end", "")[:4]
        rows = [r for r in rows if (not start or r["t"] >= start) and
                (not end or r["t"] <= end)]
    geo_label = (dims.get("geo", {}).get("category", {}).get("label", {}).get(geo) or geo)
    return {"rows": rows, "kind": "series", "source": "eurostat", "resolved": canon,
            "dataset": spec["dataset"], "geo": geo, "unit": spec["measure"],
            "updated": data.get("updated"),
            "note": (f"{len(rows)} annual {spec['measure']} points of {canon} for "
                     f"{geo_label} ({geo}); Eurostat {spec['dataset']}; flags "
                     f"{sorted(used_flags) or ['unflagged']}; updated {data.get('updated')}")}


if __name__ == "__main__":
    import sys
    fn = sys.argv[1]
    reg = resolve_region(sys.argv[2])
    ent = sys.argv[3] if len(sys.argv) > 3 else "clinic"
    out = {"osm": osm_select, "wb": wb_series}[fn](ent, reg)
    print(json.dumps({**out, "rows": out["rows"][:3], "n": len(out["rows"])}, indent=2, default=str))
