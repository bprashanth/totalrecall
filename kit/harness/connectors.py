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
import math
import os
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
    """Construct the accepted ALG-015 bbox approximation around resolved REGION support.

    The returned object is deliberately difficult to mistake for exact geometry: method and
    approximate fields are part of the typed support and the executor repeats them in provenance.
    Dateline/polar cases fail closed until an exact-geometry implementation is governed.
    """
    radius = float(radius_km)
    if not math.isfinite(radius) or radius <= 0:
        raise ValueError("buffer radius must be a positive finite number")
    s, n, w, e = region["bbox"]
    mid_lat = (s + n) / 2
    lat_delta = radius / 111.32
    lon_scale = math.cos(math.radians(mid_lat))
    if abs(lon_scale) < 0.05:
        raise ValueError("bbox buffer is unsupported near a pole; exact geometry required")
    lon_delta = radius / (111.32 * lon_scale)
    bbox = [s - lat_delta, n + lat_delta, w - lon_delta, e + lon_delta]
    if bbox[0] <= -90 or bbox[1] >= 90 or bbox[2] <= -180 or bbox[3] >= 180:
        raise ValueError("bbox buffer crosses a polar or dateline boundary; exact geometry required")
    return {
        "name": f"{radius:g} km approximate bbox around {region['name']}",
        "bbox": bbox,
        "lat": region.get("lat", mid_lat),
        "lon": region.get("lon", (w + e) / 2),
        "orig": region.get("orig") or region.get("name"),
        "source": "derived-latitude-adjusted-bbox-expansion",
        "method": "bbox-approx",
        "approximate": True,
        "support_type": "analysis-search-bbox",
        "parent_region": region,
        "buffer_km": radius,
    }


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
            "measure": f"osm:{canon}:occurrence_record", "unit": "record",
            "grain": "georeferenced-point-in-request-bbox",
            "lineage": [{"source": "OpenStreetMap/Overpass", "entity": canon}],
            "fields": {"id": "identifier", "lat": "number", "lon": "number",
                       "name": "string|null", "time": "period|null"},
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

# Connector-owned semantic metadata for the released v2.3 arithmetic/alignment contract.  A
# measure id is source+method specific; sharing unit "percent" does not make two indicators
# subtractable.  World Bank rows are annual, so mixed-frequency coarsening is not requested here.
WB_UNITS = {
    "NY.GDP.PCAP.CD": "current_USD/person", "NY.GDP.MKTP.CD": "current_USD",
    "SP.POP.TOTL": "person", "SP.URB.TOTL.IN.ZS": "percent",
    "SL.UEM.TOTL.ZS": "percent", "SI.POV.DDAY": "percent",
    "IT.NET.USER.ZS": "percent", "IT.CEL.SETS.P2": "subscriptions/100_people",
    "EG.ELC.ACCS.ZS": "percent", "SE.PRM.ENRR": "percent",
    "SE.SEC.ENRR": "percent", "SE.ADT.LITR.ZS": "percent",
    "FP.CPI.TOTL.ZG": "percent/year", "SL.TLF.TOTL.IN": "person",
    "NE.TRD.GNFS.ZS": "percent_GDP", "SP.DYN.LE00.IN": "year",
    "ST.INT.ARVL": "arrival", "SH.XPD.CHEX.GD.ZS": "percent_GDP",
    "NY.GDP.MKTP.KD.ZG": "percent/year",
}


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
    vintage = d[0].get("lastupdated") if isinstance(d, list) and d and isinstance(d[0], dict) else None
    return {"rows": rows, "kind": "series", "source": "worldbank", "label": lbl,
            "resolved": canon, "ambiguous": ambig, "indicator": code, "iso": iso,
            "measure": f"worldbank:{code}", "unit": WB_UNITS.get(code, "unknown"),
            "grain": "country", "frequency": "annual", "vintage": vintage,
            "lineage": [{"source": "World Bank API", "indicator": code, "country": iso,
                         "vintage": vintage}],
            "fields": {"t": "annual_period", "value": "number"},
            "note": f"{len(rows)} yearly points of {canon} for {iso}{note_extra}"
                    + (" (upstream ILO/WB modeled estimate)" if lbl == "modelled" else "")}


if __name__ == "__main__":
    import sys
    fn = sys.argv[1]
    reg = resolve_region(sys.argv[2])
    ent = sys.argv[3] if len(sys.argv) > 3 else "clinic"
    out = {"osm": osm_select, "wb": wb_series}[fn](ent, reg)
    print(json.dumps({**out, "rows": out["rows"][:3], "n": len(out["rows"])}, indent=2, default=str))
