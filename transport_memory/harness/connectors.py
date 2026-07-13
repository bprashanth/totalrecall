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
    # -- transport sector (verified in FINDINGS.md census, 2026-07-12) --
    "tram_stop": '["railway"="tram_stop"]', "tram": '["railway"="tram_stop"]',
    "railway_station": '["railway"="station"]', "train_station": '["railway"="station"]',
    "train": '["railway"="station"]', "railway": '["railway"="station"]',
    "subway_entrance": '["railway"="subway_entrance"]',
    "metro_station": '["railway"="subway_entrance"]',
    "ferry_terminal": '["amenity"="ferry_terminal"]', "ferry": '["amenity"="ferry_terminal"]',
    "ferries": '["amenity"="ferry_terminal"]',
    "parking": '["amenity"="parking"]', "car_park": '["amenity"="parking"]',
    "parking_lot": '["amenity"="parking"]',
    "bicycle_rental": '["amenity"="bicycle_rental"]', "bike_rental": '["amenity"="bicycle_rental"]',
    "bike_share": '["amenity"="bicycle_rental"]',
    "charging_station": '["amenity"="charging_station"]',
    "ev_charging": '["amenity"="charging_station"]',
    "charging": '["amenity"="charging_station"]',
    "taxi": '["amenity"="taxi"]', "taxi_stand": '["amenity"="taxi"]',
    "taxi_rank": '["amenity"="taxi"]',
    "airport": '["aeroway"="aerodrome"]', "aerodrome": '["aeroway"="aerodrome"]',
    "petrol_station": '["amenity"="fuel"]', "gas_station": '["amenity"="fuel"]',
    "fuel_station": '["amenity"="fuel"]',
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


# ---------------------------------------------------------------- OSM route relations (transit LINES)
# A bus/tram/ferry LINE is an OSM *relation* (type=route), not a node/way — a different Overpass
# query shape from osm_select (transport-sector connector work, 2026-07-12). Rows carry NO
# lat/lon (fetching member geometry for hundreds of routes would hammer Overpass), so lines
# COUNT and LIST but do not RELATE spatially — that limitation is stated in the note.
OSM_ROUTES = {
    "bus_line": "bus", "bus_route": "bus", "bus_service": "bus",
    "tram_line": "tram", "tram_route": "tram",
    "train_line": "train", "rail_route": "train",
    "ferry_route": "ferry", "ferry_line": "ferry",
    "subway_line": "subway", "metro_line": "subway",
    "trolleybus_line": "trolleybus", "trolleybus_route": "trolleybus",
}


def osm_routes_resolve(entity):
    """(route_mode, canonical, ambiguous) — same DIRECTIONAL token matching as osm_resolve_tag."""
    e = entity.lower().strip()
    for k, mode in OSM_ROUTES.items():
        if k == e.replace(" ", "_") or k == e.replace(" ", "_").rstrip("s"):
            return mode, k, []
    et = _tokens(entity)
    hits = [k for k in OSM_ROUTES if _key_covered(k, et)]
    if len(hits) == 1:
        return OSM_ROUTES[hits[0]], hits[0], []
    if len(hits) > 1:
        best = max(hits, key=lambda k: len(_tokens(k) & et))
        return OSM_ROUTES[best], best, hits
    return None, None, []


def osm_routes_select(entity, region, limit=400):
    mode, canon, ambig = osm_routes_resolve(entity)
    if not mode:
        return {"rows": [], "kind": "records", "source": "osm-overpass-routes",
                "note": f"no route mapping for {entity!r}", "resolved": None, "ambiguous": []}
    s, n, w, e = region["bbox"]
    bbox = f"{s},{w},{n},{e}"
    ql = (f'[out:json][timeout:40];relation["type"="route"]["route"="{mode}"]({bbox});'
          f'out tags {limit};')
    d = _get("https://overpass-api.de/api/interpreter", data="data=" + urllib.parse.quote(ql),
             method="POST")
    els = d.get("elements", [])
    # a LINE is usually 2+ relations (one per direction): dedupe by ref when present, so the
    # row count answers "how many lines", not "how many direction-variants" (census finding)
    by_ref, no_ref = {}, []
    for el in els:
        tags = el.get("tags") or {}
        ref = tags.get("ref")
        row = {"id": el.get("id"), "name": tags.get("name") or ref,
               "ref": ref, "time": None}
        if ref:
            by_ref.setdefault(ref, row)
        else:
            no_ref.append(row)
    rows = list(by_ref.values()) + no_ref
    return {"rows": rows, "kind": "records", "source": "osm-overpass-routes",
            "resolved": canon, "ambiguous": ambig,
            "note": (f"{len(rows)} {mode} lines ({len(els)} route relations; direction variants "
                     f"deduped by ref); rows carry no geometry — countable, not spatially relatable")}


# ---------------------------------------------------------------- GTFS static feeds (Mobility Database)
# Round 2 source family: operator-PUBLISHED schedule data (stops.txt / routes.txt) fetched from
# the Mobility Database's keyless mdb-latest mirror (the catalog CSV at bit.ly/catalogs-csv is
# the public index; the v1 API needs a key and was REJECTED as a keyless family — census
# 2026-07-13). Evidence status: OBSERVED (agency-published schedule), snapshot grain per feed.
# Registry is curated: every feed below was verified to return real stop rows before adoption.
GTFS_FEEDS = {
    "winnipeg": {"mdb": 717, "provider": "Winnipeg Transit",
                 "url": "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/ca-manitoba-winnipeg-transit-gtfs-717.zip?alt=media"},
    "christchurch": {"mdb": 1313, "provider": "Metro Christchurch",
                     "url": "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/nz-christchurch-christchurch-metro-gtfs-1313.zip?alt=media"},
    "oulu": {"mdb": 869, "provider": "Waltti - Oulu",
             "url": "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/fi-pohjois-pohjanmaa-oulun-joukkoliikenne-gtfs-869.zip?alt=media"},
    "tampere": {"mdb": 866, "provider": "Tampereen joukkoliikenne (JOLI)",
                "url": "https://storage.googleapis.com/storage/v1/b/mdb-latest/o/fi-unknown-tampereen-joukkoliikenne-joli-gtfs-866.zip?alt=media"},
}

# Lay phrases -> GTFS table. DIRECTIONAL token matching (all key tokens in the entity phrase):
# "transit stops" hits, bare "bus stop" does NOT (that stays an OSM point entity — the two
# families answer different questions: mapped physical stops vs scheduled network stops).
GTFS_ENTITIES = {
    "transit_stop": "stops", "transit_stops": "stops", "scheduled_stop": "stops",
    "scheduled_transit_stop": "stops", "gtfs_stop": "stops", "timetabled_stop": "stops",
    "transit_route": "routes", "scheduled_route": "routes", "gtfs_route": "routes",
    "timetabled_route": "routes", "scheduled_service": "routes", "transit_service": "routes",
}


def _get_bytes(url, timeout=120, retries=3):
    """Binary sibling of _get for feed zips; cached on disk like everything else."""
    import base64
    key = f"BYTES {url}"
    c = _cache_get(key)
    if c is not None:
        return base64.b64decode(c["b64"])
    h = {"User-Agent": UA}
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read()
            _cache_put(key, {"b64": base64.b64encode(raw).decode()})
            return raw
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
                http.client.HTTPException, ConnectionError, OSError) as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET(bytes) failed {url}: {last}")


def _maximal_hits(hits):
    """Drop hits whose token set is a strict subset of another hit's — 'ridership' hitting
    alongside 'bus_ridership' is specificity, not ambiguity (Round-1 WB same-code lesson)."""
    toks = {k: _tokens(k) for k in hits}
    return [k for k in hits
            if not any(o != k and toks[k] < toks[o] for o in hits)]


def gtfs_resolve(entity):
    """(table, canonical, ambiguous) — table in {'stops','routes'} or (None, None, [])."""
    et = _tokens(entity)
    hits = _maximal_hits([k for k in GTFS_ENTITIES if _key_covered(k, et)])
    if not hits:
        return None, None, []
    best = max(hits, key=lambda k: len(_tokens(k) & et))
    others = sorted({GTFS_ENTITIES[h] for h in hits})
    return GTFS_ENTITIES[best], best, (hits if len(others) > 1 else [])


def gtfs_city(region):
    """Match the resolved region against the curated feed registry (alnum-normalized)."""
    cands = [region.get("orig"), region.get("name")]
    for cand in cands:
        if not cand:
            continue
        cn = _norm(cand)
        for city in GTFS_FEEDS:
            if _norm(city) in cn:
                return city
    return None


def gtfs_select(entity, region):
    """Scheduled-network records from a verified GTFS feed. Rows for stops carry lat/lon
    (spatially relatable, unlike OSM route relations); route rows carry no geometry.
    Unregistered city -> empty rows (an honest 'no registered feed' gap, NEVER a silent
    fallback to OSM points — that would be a wrong-source answer that scores green)."""
    import csv as _csv
    import io
    import zipfile
    table, canon, ambig = gtfs_resolve(entity)
    if not table:
        return {"rows": [], "kind": "records", "source": "gtfs-mobility-database",
                "note": f"no GTFS mapping for {entity!r}", "resolved": None, "ambiguous": []}
    city = gtfs_city(region)
    if not city:
        return {"rows": [], "kind": "records", "source": "gtfs-mobility-database",
                "resolved": canon, "ambiguous": ambig,
                "note": (f"no registered GTFS feed for {region.get('orig') or region.get('name')!r} "
                         f"(registered: {', '.join(sorted(GTFS_FEEDS))})")}
    feed = GTFS_FEEDS[city]
    raw = _get_bytes(feed["url"])
    z = zipfile.ZipFile(io.BytesIO(raw))
    rows = []
    if table == "stops":
        for r in _csv.DictReader(io.TextIOWrapper(z.open("stops.txt"), encoding="utf-8-sig")):
            if r.get("location_type") not in (None, "", "0"):
                continue  # count boarding stops, not parent stations/entrances
            try:
                lat, lon = float(r["stop_lat"]), float(r["stop_lon"])
            except (KeyError, TypeError, ValueError):
                continue
            rows.append({"id": r.get("stop_id"), "lat": lat, "lon": lon,
                         "name": r.get("stop_name"), "time": None})
        note = (f"{len(rows)} scheduled transit stops (GTFS stops.txt, mdb-{feed['mdb']} "
                f"{feed['provider']}; agency-published snapshot)")
    else:
        for r in _csv.DictReader(io.TextIOWrapper(z.open("routes.txt"), encoding="utf-8-sig")):
            rows.append({"id": r.get("route_id"),
                         "name": r.get("route_long_name") or r.get("route_short_name"),
                         "ref": r.get("route_short_name"), "time": None})
        note = (f"{len(rows)} scheduled routes (GTFS routes.txt, mdb-{feed['mdb']} "
                f"{feed['provider']}); rows carry no geometry — countable, not spatially relatable")
    return {"rows": rows, "kind": "records", "source": "gtfs-mobility-database",
            "resolved": f"{canon}@{city}", "ambiguous": ambig, "note": note}


# ---------------------------------------------------------------- City open-data ridership (Socrata)
# Round 2 source family: administrative ridership SERIES from city open-data portals (keyless
# Socrata endpoints). Grain: city-system/annual — a grain neither OSM (point snapshot) nor the
# World Bank (country/annual) covers. EVIDENCE STATUS IS PER-CITY and propagates as the label:
#   - Chicago CTA annual boarding totals: OBSERVED (farebox/administrative counts, 1988-).
#   - NY MTA daily ridership: upstream-MODELED — the source fields literally say
#     "subways_total_estimated_ridership"; adopted with label 'modelled' so the taint
#     propagates (the transport twin of the livelihoods run's modeled-ILO finding).
RIDERSHIP_SOURCES = {
    "chicago": {
        "provider": "Chicago Transit Authority annual boarding totals "
                    "(data.cityofchicago.org Socrata w8km-9pzd)",
        "kind": "annual", "label": "observed",
        "url": "https://data.cityofchicago.org/resource/w8km-9pzd.json?$limit=200&$order=year",
        "modes": {"bus": "bus", "rail": "rail", "train": "rail", "subway": "rail",
                  "transit": "total", "paratransit": "paratransit"},
        "unit": "unlinked boardings/year"},
    "new york": {
        "provider": "NY MTA daily ridership, aggregated to years in-query "
                    "(data.ny.gov Socrata vxuj-8kew)",
        "kind": "daily-agg", "label": "modelled",
        # values are the SoQL aliases in the in-query aggregation below; the upstream columns
        # are subways_total_estimated_ridership / buses_total_estimated_ridersip (the
        # misspelling is real, and both say ESTIMATED — hence label 'modelled')
        "modes": {"subway": "subway", "metro": "subway", "rail": "subway",
                  "train": "subway", "bus": "bus", "transit": "__sum__"},
        "unit": "estimated riders/year (MTA daily estimates summed)"},
}

RIDERSHIP_KEYS = {
    "bus_ridership": "bus", "rail_ridership": "rail", "train_ridership": "train",
    "subway_ridership": "subway", "metro_ridership": "metro",
    "transit_ridership": "transit", "public_transport_ridership": "transit",
    "public_transit_ridership": "transit", "ridership": "transit",
    "bus_boardings": "bus", "rail_boardings": "rail", "transit_boardings": "transit",
}


def ridership_resolve(entity):
    """(mode, canonical, ambiguous). 'ridership' alone reads as system total (transit)."""
    et = _tokens(entity)
    hits = _maximal_hits([k for k in RIDERSHIP_KEYS if _key_covered(k, et)])
    if not hits:
        return None, None, []
    best = max(hits, key=lambda k: len(_tokens(k) & et))
    modes = {RIDERSHIP_KEYS[h] for h in hits}
    return RIDERSHIP_KEYS[best], best, (hits if len(modes) > 1 else [])


def ridership_city(region):
    cands = [region.get("orig"), region.get("name")]
    for cand in cands:
        if not cand:
            continue
        cn = _norm(cand)
        for city in RIDERSHIP_SOURCES:
            if _norm(city) in cn:
                return city
    return None


def _ridership_window(rows, time):
    """Same window + nearest-year(±3) contract as wb_series, same provenance phrasing."""
    note_extra = ""
    if time and isinstance(time, dict):
        s, e = (time.get("start") or "")[:4], (time.get("end") or "")[:4]
        windowed = [r for r in rows if (not s or r["t"] >= s) and (not e or r["t"] <= e)]
        if not windowed and s and e and s == e and rows:
            target = int(s)
            near = min(rows, key=lambda r: abs(int(r["t"]) - target))
            if abs(int(near["t"]) - target) <= 3:
                windowed = [near]
                note_extra = f" (no {s} value; nearest year {near['t']} used)"
        rows = windowed
    return rows, note_extra


def ridership_series(entity, region, time=None):
    mode, canon, ambig = ridership_resolve(entity)
    if not mode:
        return {"rows": [], "kind": "series", "source": "city-open-data-ridership",
                "note": f"no ridership mapping for {entity!r}", "resolved": None, "label": "observed"}
    city = ridership_city(region)
    if not city:
        return {"rows": [], "kind": "series", "source": "city-open-data-ridership",
                "resolved": canon, "ambiguous": ambig, "label": "observed",
                "note": (f"no city open-data ridership source registered for "
                         f"{region.get('orig') or region.get('name')!r} "
                         f"(registered: {', '.join(sorted(RIDERSHIP_SOURCES))})")}
    src = RIDERSHIP_SOURCES[city]
    col = src["modes"].get(mode)
    if col is None:
        return {"rows": [], "kind": "series", "source": "city-open-data-ridership",
                "resolved": canon, "ambiguous": ambig, "label": src["label"],
                "note": f"{city} source has no {mode!r} mode (has: {sorted(src['modes'])})"}
    rows, dropped = [], []
    if src["kind"] == "annual":
        d = _get(src["url"])
        for r in d:
            v = r.get(col)
            if v is None:
                continue
            rows.append({"t": str(r["year"]), "value": float(v)})
    else:  # daily-agg: server-side SoQL yearly sum + day count (partial-year guard)
        sel = ("date_extract_y(date) as yr, count(date) as days, "
               "sum(subways_total_estimated_ridership) as subway, "
               "sum(buses_total_estimated_ridersip) as bus")
        url = ("https://data.ny.gov/resource/vxuj-8kew.json?$select=" +
               urllib.parse.quote(sel) + "&$group=yr&$order=yr&$limit=50")
        d = _get(url)
        for r in d:
            if int(r.get("days", 0)) < 360:
                # partial year would poison CHANGE/TREND answers (2020 has 306 days — the
                # dataset starts 2020-03-01 — and the trailing year is usually in progress)
                dropped.append(r["yr"])
                continue
            v = (float(r["subway"]) + float(r["bus"])) if col == "__sum__" else float(r[col])
            rows.append({"t": str(r["yr"]), "value": v})
    rows.sort(key=lambda x: x["t"])
    rows, note_extra = _ridership_window(rows, time)
    if dropped:
        note_extra += f" (partial year(s) {','.join(dropped)} dropped: <300 days of data)"
    return {"rows": rows, "kind": "series", "source": "city-open-data-ridership",
            "resolved": f"{mode}@{city}", "ambiguous": ambig, "label": src["label"],
            "note": (f"{len(rows)} yearly points of {mode} ridership for {city} "
                     f"[{src['unit']}; {src['provider']}; evidence: {src['label']}]"
                     f"{note_extra}")}


# ---------------------------------------------------------------- World Bank (indicator series)
# lay phrase -> WB indicator code (curated; resolver flags when unmapped).
WB_INDICATORS = {
    "gdp per capita": "NY.GDP.PCAP.CD", "gdp": "NY.GDP.MKTP.CD",
    "population": "SP.POP.TOTL", "urban population": "SP.URB.TOTL.IN.ZS",
    "unemployment": "SL.UEM.TOTL.ZS", "poverty": "SI.POV.DDAY",
    "internet users": "IT.NET.USER.ZS", "internet use": "IT.NET.USER.ZS",
    "internet": "IT.NET.USER.ZS",
    "mobile subscriptions": "IT.CEL.SETS.P2", "electricity access": "EG.ELC.ACCS.ZS",
    "school enrollment": "SE.PRM.ENRR", "secondary enrollment": "SE.SEC.ENRR",
    "electricity": "EG.ELC.ACCS.ZS",
    "literacy": "SE.ADT.LITR.ZS", "inflation": "FP.CPI.TOTL.ZG",
    "labor force": "SL.TLF.TOTL.IN", "trade": "NE.TRD.GNFS.ZS",
    "life expectancy": "SP.DYN.LE00.IN", "tourism arrivals": "ST.INT.ARVL",
    "health expenditure": "SH.XPD.CHEX.GD.ZS", "gdp growth": "NY.GDP.MKTP.KD.ZG",
    # -- transport indicators (each verified to return rows for KEN/VNM/ARG/CZE before adoption;
    #    see FINDINGS.md census 2026-07-12) --
    "air passengers": "IS.AIR.PSGR", "air passenger": "IS.AIR.PSGR",
    "aircraft departures": "IS.AIR.DPRT", "air carrier departures": "IS.AIR.DPRT",
    "rail lines": "IS.RRS.TOTL.KM",
    "railway passengers": "IS.RRS.PASG.KM", "rail passengers": "IS.RRS.PASG.KM",
    "railway goods": "IS.RRS.GOOD.MT.K6", "rail freight": "IS.RRS.GOOD.MT.K6",
    "container port traffic": "IS.SHP.GOOD.TU", "port traffic": "IS.SHP.GOOD.TU",
}

# Upstream-modeling audit (Round 2, census 2026-07-13 — the livelihoods run caught modeled ILO
# series entering as 'observed'; same audit here). These WB transport series are administrative
# compilations that INCLUDE upstream estimates for gap years; the caveat rides in provenance.
WB_EVIDENCE_NOTES = {
    "IS.AIR.PSGR": "upstream: ICAO Civil Aviation Statistics + ICAO staff estimates (partially estimated)",
    "IS.AIR.DPRT": "upstream: ICAO Civil Aviation Statistics + ICAO staff estimates (partially estimated)",
    "IS.SHP.GOOD.TU": "upstream: UNCTAD/Containerisation International derivations (partially estimated)",
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
        # aliases of the SAME indicator ("air passengers"/"air passenger") are not ambiguity —
        # only flag when hits map to DIFFERENT codes (transport census cleanup, 2026-07-12)
        return hits if len({WB_INDICATORS[h] for h in hits}) > 1 else []
    hits = [k for k in WB_INDICATORS if k in e]  # key phrase inside entity phrase only
    if hits:
        best = max(hits, key=len)
        return WB_INDICATORS[best], best, _ambig(hits)
    et = _tokens(entity) - {"rate", "level", "number", "total"}
    tok_hits = [k for k in WB_INDICATORS if _key_covered(k, et)]
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
    ev = WB_EVIDENCE_NOTES.get(code)
    return {"rows": rows, "kind": "series", "source": "worldbank",
            "resolved": canon, "ambiguous": ambig, "indicator": code, "iso": iso,
            "note": f"{len(rows)} yearly points of {canon} for {iso}{note_extra}"
                    + (f" [{ev}]" if ev else "")}


if __name__ == "__main__":
    import sys
    fn = sys.argv[1]
    reg = resolve_region(sys.argv[2])
    ent = sys.argv[3] if len(sys.argv) > 3 else "clinic"
    out = {"osm": osm_select, "wb": wb_series}[fn](ent, reg)
    print(json.dumps({**out, "rows": out["rows"][:3], "n": len(out["rows"])}, indent=2, default=str))
