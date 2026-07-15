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


# ---------------------------------------------------------------- Indian-English entity aliases
# Deployment users are Indian urban/semi-urban English speakers; their lay entity vocabulary
# differs from OSM_TAGS. alias -> (canonical OSM_TAGS key, ambiguous_alternatives, provenance note).
# The note ALWAYS travels into provenance so approximations are never silent:
#   - anganwadi ~ kindergarten is the NEAREST OSM class (anganwadis are ICDS mother-and-child
#     nutrition/preschool centres; OSM has no dedicated class, many are tagged kindergarten).
#   - 'nursing home' in Indian English = a small private hospital, NOT elder care -> hospital,
#     flagged ambiguous (hospital|clinic).
#   - 'hotel' in South-Indian usage commonly means an eatery/restaurant -> flagged AMBIGUOUS
#     (hotel|restaurant); the executor proceeds with lodging-hotel but the answer must surface it.
# (lakh/crore number-word normalization is FUTURE WORK — it belongs in the semantic lint/parse
# path, not the entity resolver.)
INDIC_ALIASES = {
    "medical shop":          ("pharmacy", [], "Indian-English 'medical shop' -> pharmacy"),
    "medical store":         ("pharmacy", [], "Indian-English 'medical store' -> pharmacy"),
    "medical":               ("pharmacy", [], "colloquial bare 'medical' (as in 'go to the "
                                              "medical') -> pharmacy"),
    "medicals":              ("pharmacy", [], "colloquial 'medicals' -> pharmacy"),
    "chemist":               ("pharmacy", [], "'chemist' -> pharmacy"),
    "petrol pump":           ("fuel", [], "'petrol pump' -> fuel station"),
    "petrol bunk":           ("fuel", [], "'petrol bunk' (South India) -> fuel station"),
    "petrol station":        ("fuel", [], "'petrol station' -> fuel station"),
    "petrol":                ("fuel", [], "bare 'petrol' -> fuel station"),
    "bus stand":             ("bus_station", [], "'bus stand' -> bus_station"),
    "bus depot":             ("bus_station", [], "'bus depot' -> bus_station (depot~station approximation)"),
    "phc":                   ("clinic", [], "PHC (primary health centre) -> clinic"),
    "primary health centre": ("clinic", [], "'primary health centre' -> clinic"),
    "primary health center": ("clinic", [], "'primary health center' -> clinic"),
    "dispensary":            ("clinic", [], "'dispensary' -> clinic"),
    "anganwadi":             ("kindergarten", [],
                              "anganwadi -> kindergarten (NEAREST OSM class, approximation: "
                              "ICDS mother-and-child centre, not a private kindergarten)"),
    "kirana":                ("shop", [], "'kirana' -> shop (small neighbourhood grocery)"),
    "kirana store":          ("shop", [], "'kirana store' -> shop"),
    "general store":         ("shop", [], "'general store' -> shop"),
    "mandi":                 ("market", [], "'mandi' -> marketplace"),
    "bazaar":                ("market", [], "'bazaar' -> marketplace"),
    "bazar":                 ("market", [], "'bazar' -> marketplace"),
    "santhe":                ("market", [], "'santhe' (Kannada periodic market) -> marketplace"),
    "nursing home":          ("hospital", ["hospital", "clinic"],
                              "Indian-English 'nursing home' = small private hospital (NOT elder "
                              "care) -> hospital; flagged ambiguous"),
    "hotel":                 ("hotel", ["hotel", "restaurant"],
                              "AMBIGUOUS in Indian English: 'hotel' often means an "
                              "eatery/restaurant (South-Indian sense), not lodging; proceeding "
                              "with lodging-hotel — surface the ambiguity in the answer"),
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


# aliases that are generic modifiers in compounds ("medical college", "petrol tanker",
# "hotel management") — they match EXACTLY only, never by coverage inside longer phrases.
_WEAK_ALIASES = {"medical", "medicals", "petrol", "hotel"}


def _indic_alias(entity):
    """Return the matching INDIC_ALIASES key for this entity phrase, or None.
    Same normalization discipline as osm_resolve_tag: exact -> token-set -> DIRECTIONAL
    coverage (all alias tokens present in the entity; weak aliases excluded from coverage)."""
    e = entity.lower().strip()
    if e in INDIC_ALIASES:
        return e
    if e.rstrip("s") in INDIC_ALIASES:
        return e.rstrip("s")
    et = _tokens(entity)
    exact = [k for k in INDIC_ALIASES if _tokens(k) == et]
    if exact:
        return exact[0]
    hits = [k for k in INDIC_ALIASES if k not in _WEAK_ALIASES and _key_covered(k, et)]
    if hits:
        return max(hits, key=lambda k: len(_tokens(k) & et))
    return None


# Overpass endpoint failover (2026-07-15): overpass-api.de and kumi.systems both became
# unreachable mid-grind (errno 101 at the IP level) while the mail.ru mirror stayed up.
# Cache key is the QUERY, not the host, so cached results survive endpoint switches.
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def _overpass(ql):
    key = f"OVERPASS {ql}"
    c = _cache_get(key)
    if c is not None:
        return c
    # backward-compat: reuse entries cached under the old per-URL key (pre-failover format)
    old = _cache_get(f"POST {OVERPASS_ENDPOINTS[0]} data=" + urllib.parse.quote(ql))
    if old is not None:
        _cache_put(key, old)
        return old
    last = None
    for ep in OVERPASS_ENDPOINTS:
        for attempt in range(2):
            try:
                req = urllib.request.Request(ep, headers={"User-Agent": UA},
                                             data=("data=" + urllib.parse.quote(ql)).encode(),
                                             method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    val = json.loads(r.read().decode(errors="ignore"))
                _cache_put(key, val)
                return val
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                    http.client.HTTPException, ConnectionError, OSError,
                    json.JSONDecodeError) as e:
                last = e
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"overpass failed on all endpoints: {last}")


def osm_resolve_tag(entity):
    """Return (tag_filter, canonical, ambiguous_alternatives).

    Token-based: 'bus stop' matches 'bus_stop', 'health clinics' matches 'clinic'. Every
    language boundary needs normalization, not exact/substring matching (tick-004-ds finding).
    Indian-English aliases are checked FIRST: 'medical shop' must resolve to pharmacy, not be
    token-captured by the generic 'shop' key."""
    ak = _indic_alias(entity)
    if ak:
        canon, ambig, _ = INDIC_ALIASES[ak]
        return OSM_TAGS[canon], canon, list(ambig)
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
    d = _overpass(ql)
    rows = []
    for el in d.get("elements", []):
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        if lat is None:
            continue
        rows.append({"id": el.get("id"), "lat": lat, "lon": lon,
                     "name": (el.get("tags") or {}).get("name"), "time": None})
    ak = _indic_alias(entity)
    alias_note = f"; {INDIC_ALIASES[ak][2]}" if ak else ""
    return {"rows": rows, "kind": "records", "source": "osm-overpass",
            "resolved": canon, "ambiguous": ambig,
            "note": f"{len(rows)} {canon} in bbox"
                    + (f"; AMBIGUOUS among {ambig}" if ambig else "") + alias_note}


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


# ---------------------------------------------------------------- IChangeMyCity (Bengaluru complaints)
# Source: "I Change My City Data" — civic complaints logged on ichangemycity.com (Janaagraha),
# published by OpenCity.in, dataset id "i-change-my-city-data", resource "Complaints Log
# 2019-2022" (~16k rows: ward, category, sub-category, lat/lon, status, created_at).
# LICENSE: Creative Commons Attribution Share-Alike (CC BY-SA) — attribution: Janaagraha /
# ichangemycity.com via OpenCity.in (data.opencity.in). This notice IS the attribution and it
# also travels in every result's "source" field.
# Coverage: Bengaluru (BBMP wards) only, 2019-01 .. 2022-07. Region filter = ward name if the
# question names a ward, else all-Bengaluru. Nearest-year honesty mirrors wb_series.
ICMC_CSV = os.path.join(HERE, "data", "icmc_complaints_2019_2022.csv")

# complaint-family qualifier -> list of category_title values in the CSV (curated from the
# actual category inventory; 'Street lighting' and 'Streetlights' are BOTH real spellings).
ICMC_FAMILIES = {
    "garbage":     ["Garbage and Unsanitary Practices", "Sanitation"],
    "streetlight": ["Street lighting", "Streetlights"],
    "street light": ["Street lighting", "Streetlights"],
    "street lighting": ["Street lighting", "Streetlights"],
    "road":        ["Mobility - Roads, Footpaths and Infrastructure", "Roads and Footpaths"],
    "pothole":     ["Mobility - Roads, Footpaths and Infrastructure", "Roads and Footpaths"],
    "footpath":    ["Mobility - Roads, Footpaths and Infrastructure", "Roads and Footpaths"],
    "water":       ["Water Supply and Services", "Water Supply"],
    "traffic":     ["Traffic and Road Safety"],
    "pollution":   ["Pollution"],
    "sewage":      ["Sewerage Systems"],
    "sewerage":    ["Sewerage Systems"],
    "drain":       ["Storm Water Drains"],
    "stray animal": ["Animal Husbandry"],
    "animal":      ["Animal Husbandry"],
    "electricity": ["Electricity and Power Supply"],
    "power":       ["Electricity and Power Supply"],
    "park":        ["Parks & Recreation"],
    "tree":        ["Trees and Saplings"],
    "toilet":      ["Public Toilets"],
    "yellow spot": ["Yellow Spot"],
    "lake":        ["Lakes"],
    "encroachment": ["Community Infrastructure and Services"],
}
_COMPLAINT_WORDS = {"complaint", "grievance"}
_ICMC_ROWS = None  # lazy CSV cache


def icmc_match(entity):
    """Is this a complaint-family entity? -> (categories|None-for-all, canonical) or None.
    Requires an explicit complaint/grievance token so 'streetlights in Indiranagar' still
    routes to OSM points, not the complaints log."""
    if not isinstance(entity, str):
        return None
    et = _tokens(entity)
    if not any(any(_tok_eq(w, t) for t in et) for w in _COMPLAINT_WORDS):
        return None
    qual = {t for t in et if not any(_tok_eq(w, t) for w in _COMPLAINT_WORDS)} \
        - {"civic", "citizen", "public", "ward", "bbmp"}
    if not qual:
        return ([], "complaints (all categories)")  # empty list = no category filter
    for k in sorted(ICMC_FAMILIES, key=lambda k: -len(_tokens(k))):
        if _key_covered(k, qual):
            return (ICMC_FAMILIES[k], f"{k} complaints")
    return None  # complaint-flavoured but unknown family -> let caller surface the gap


def icmc_families():
    return sorted(set(ICMC_FAMILIES))


def _icmc_parse_time(s):
    """Two real formats in the CSV: '1-1-2019 06:33' (d-m-yyyy) and '1/13/2019 ...' (m/d/yyyy).
    Return ISO 'YYYY-MM-DD' or None."""
    s = (s or "").strip().split(" ")[0]
    try:
        if "-" in s:
            d, m, y = s.split("-")
        elif "/" in s:
            m, d, y = s.split("/")
        else:
            return None
        d, m, y = int(d), int(m), int(y)
        if m > 12:  # tolerate swapped fields
            d, m = m, d
        return f"{y:04d}-{m:02d}-{d:02d}"
    except (ValueError, TypeError):
        return None


def _icmc_load():
    global _ICMC_ROWS
    if _ICMC_ROWS is not None:
        return _ICMC_ROWS
    import csv
    rows = []
    with open(ICMC_CSV, encoding="cp1252", errors="replace") as f:
        for i, r in enumerate(csv.DictReader(f)):
            t = _icmc_parse_time(r.get("created_at"))
            if not t:
                continue
            try:
                lat, lon = float(r.get("latitude") or 0), float(r.get("longitude") or 0)
            except ValueError:
                lat, lon = None, None
            rows.append({"id": i, "time": t, "ward": (r.get("ward_title") or "").strip(),
                         "category": (r.get("category_title") or "").strip(),
                         "sub_category": (r.get("sub_category_title") or "").strip(),
                         "status": (r.get("complaint_status_title") or "").strip(),
                         "name": (r.get("title") or "").strip()[:80],
                         "lat": lat if lat else None, "lon": lon if lon else None})
    _ICMC_ROWS = rows
    return rows


_ICMC_CITY = {"bengaluru", "bangalore", "bengaluruurban", "bbmp", "blr", "bengalurukarnataka",
              "bangalorekarnataka", "bengaluruindia", "bangaloreindia", "all", "allwards", ""}


def _icmc_ward_filter(rows, place):
    """place string -> (rows, scope_note). City-level names = all wards; else fuzzy ward match
    on the FIRST comma segment ('Bellandur, Bengaluru' -> ward Bellanduru)."""
    seg = place.split(",")[0]
    for kill in ("ward", "bengaluru", "bangalore", "karnataka", "india"):
        seg = seg.lower().replace(kill, " ")
    n = _norm(seg)
    if _norm(place) in _ICMC_CITY or n in _ICMC_CITY or not n:
        return rows, "all Bengaluru wards"
    hit = [r for r in rows if _norm(r["ward"]) == n]
    if not hit:
        hit = [r for r in rows if n in _norm(r["ward"]) or _norm(r["ward"]) in n]
    if not hit:
        return [], f"ward {place.split(',')[0].strip()!r} not found in the complaints log"
    wards = sorted(set(r["ward"] for r in hit))
    return hit, f"ward {wards[0]}" if len(wards) == 1 else f"wards {wards}"


def icmc_select(entity, place, time=None, kind="records"):
    """Complaint records (or a monthly series) from the IChangeMyCity log.
    kind='records': rows with lat/lon/time/ward/category (AGGREGATE bins them).
    kind='series': monthly counts [{t:'YYYY-MM', value:n}]."""
    m = icmc_match(entity)
    if not m:
        return {"rows": [], "kind": kind, "source": "ichangemycity",
                "note": f"not a complaint-family entity: {entity!r} "
                        f"(known families: {', '.join(icmc_families())})", "resolved": None}
    cats, canon = m
    rows = _icmc_load()
    if cats:
        rows = [r for r in rows if r["category"] in cats]
    rows, scope = _icmc_ward_filter(rows, place)
    note_extra = ""
    if time and isinstance(time, dict):
        s, e = (time.get("start") or "")[:7], (time.get("end") or "")[:7]
        windowed = [r for r in rows if (not s or r["time"][:len(s)] >= s)
                    and (not e or r["time"][:len(e)] <= e)]
        # nearest-year honesty (same convention as wb_series): a single-year window outside
        # 2019-2022 coverage must not read as "no complaints" — take the nearest covered year
        # within +-3 and SAY SO.
        if not windowed and s and e and s[:4] == e[:4] and rows:
            target = int(s[:4])
            years = sorted(set(int(r["time"][:4]) for r in rows))
            near = min(years, key=lambda y: abs(y - target))
            if abs(near - target) <= 3:
                windowed = [r for r in rows if r["time"][:4] == str(near)]
                note_extra = f" (no {target} data; nearest year {near} used)"
        rows = windowed
    src = "ichangemycity (Janaagraha/OpenCity.in, CC BY-SA)"
    if kind == "series":
        bins = {}
        for r in rows:
            bins[r["time"][:7]] = bins.get(r["time"][:7], 0) + 1
        series = [{"t": k, "value": v} for k, v in sorted(bins.items())]
        return {"rows": series, "kind": "series", "source": src, "resolved": canon,
                "label": "observed",
                "note": f"{len(series)} monthly points of {canon}, {scope}, "
                        f"Bengaluru complaints log 2019-2022{note_extra}"}
    return {"rows": rows, "kind": "records", "source": src, "resolved": canon,
            "label": "observed",
            "note": f"{len(rows)} {canon}, {scope}, Bengaluru complaints log 2019-2022"
                    f"{note_extra}"}


if __name__ == "__main__":
    import sys
    fn = sys.argv[1]
    reg = resolve_region(sys.argv[2])
    ent = sys.argv[3] if len(sys.argv) > 3 else "clinic"
    out = {"osm": osm_select, "wb": wb_series}[fn](ent, reg)
    print(json.dumps({**out, "rows": out["rows"][:3], "n": len(out["rows"])}, indent=2, default=str))
