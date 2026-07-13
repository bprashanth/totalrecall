#!/usr/bin/env python3
"""Round-2 source census — cache-backed integrity snapshot of every adopted source family.

Every probe re-verifies, for concrete places, that the family returns real rows and that the
rows satisfy the family's own integrity contract:
  records: nonempty, unique ids, lat/lon present where the family claims geometry
  series:  nonempty, years ordered+unique, values numeric and positive-bounded
Each probe also records the family's GRAIN and upstream EVIDENCE STATUS (observed
administrative vs upstream-modeled/estimated) — the livelihoods run caught modeled ILO series
entering as 'observed'; this file is where transport's equivalent audit lives.

Rejected candidates are listed too (a census is evidence of what was NOT adopted and why).

Output: coverage/source-census.json.  Run from anywhere: python3 harness/source_census.py
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import connectors as C  # noqa: E402

OUT = os.path.join(HERE, "..", "coverage", "source-census.json")


def _records_check(out, want_geometry):
    rows = out["rows"]
    ids = [r.get("id") for r in rows]
    checks = {
        "nonempty": len(rows) > 0,
        "ids_unique": len(set(ids)) == len(ids),
        "geometry": (all(isinstance(r.get("lat"), float) and isinstance(r.get("lon"), float)
                         for r in rows) if want_geometry
                     else all("lat" not in r for r in rows)),
    }
    return checks, len(rows)


def _series_check(out):
    rows = out["rows"]
    ys = [r["t"] for r in rows]
    checks = {
        "nonempty": len(rows) > 0,
        "years_ordered_unique": ys == sorted(ys) and len(set(ys)) == len(ys),
        "numeric_bounded": all(isinstance(r["value"], (int, float)) and 0 <= r["value"] < 1e13
                               for r in rows),
    }
    return checks, len(rows)


def probe(family, place, entity, fn, kind, grain, evidence, want_geometry=True, time_arg=None):
    region = C.resolve_region(place)
    out = fn(entity, region, time_arg) if time_arg is not None or fn in (C.wb_series, C.ridership_series) \
        else fn(entity, region)
    if kind == "records":
        checks, n = _records_check(out, want_geometry)
    else:
        checks, n = _series_check(out)
    return {"family": family, "place": place, "entity": entity, "n_rows": n,
            "checks": checks, "ok": all(checks.values()),
            "grain": grain, "evidence": evidence,
            "source": out.get("source"), "note": out.get("note"),
            "label": out.get("label", "observed")}


def main():
    probes = []
    # -- family 1: OSM Overpass point tags (Round 1, re-audited) ------------------------------
    for place, ent in [("Brno, Czechia", "bus stop"), ("Rosario, Argentina", "railway station")]:
        probes.append(probe("osm-points", place, ent, C.osm_select, "records",
                            "city-bbox/point-record (current snapshot)",
                            "observed (community-mapped; coverage varies by city — structured "
                            "thinness, not randomness)"))
    # -- family 2: OSM route relations (Round 1, re-audited) ----------------------------------
    for place, ent in [("Brno, Czechia", "bus lines"), ("Da Nang, Vietnam", "bus routes")]:
        probes.append(probe("osm-routes", place, ent, C.osm_routes_select, "records",
                            "city-bbox/route-relation (lines deduped by ref; no geometry)",
                            "observed (community-mapped relations)", want_geometry=False))
    # -- family 3: World Bank transport indicators (Round 1, evidence status CORRECTED) -------
    for place, ent in [("Vietnam", "air passengers"), ("Argentina", "aircraft departures"),
                       ("Kenya", "container port traffic")]:
        probes.append(probe("world-bank", place, ent, C.wb_series, "series",
                            "country/annual-series",
                            "observed-administrative WITH upstream estimation: ICAO/UNCTAD "
                            "compilations include staff estimates for gap years (see "
                            "WB_EVIDENCE_NOTES; Round-2 audit finding)", time_arg=None))
    # -- family 4 (NEW): GTFS static feeds, Mobility Database keyless mirror ------------------
    for place, ent in [("Winnipeg, Canada", "transit stops"),
                       ("Christchurch, New Zealand", "transit stops"),
                       ("Oulu, Finland", "transit stops"),
                       ("Tampere, Finland", "scheduled routes")]:
        probes.append(probe("gtfs-mobility-database", place, ent, C.gtfs_select, "records",
                            "city-feed/stop-point (stops) or route-row (no geometry); "
                            "agency snapshot, no time axis",
                            "observed (operator-published schedule data)",
                            want_geometry=("stop" in ent)))
    # negative control: unregistered city must be an honest empty, never a fallback
    probes.append(probe("gtfs-mobility-database", "Rosario, Argentina", "transit stops",
                        C.gtfs_select, "records", "city-feed/stop-point",
                        "n/a — negative control (unregistered city -> empty -> DataRequest)",
                        want_geometry=True))
    probes[-1]["ok"] = probes[-1]["n_rows"] == 0 and not probes[-1]["checks"]["nonempty"]
    probes[-1]["checks"] = {"empty_as_expected": probes[-1]["ok"]}
    # -- family 5 (NEW): city open-data ridership series (Socrata) ----------------------------
    probes.append(probe("city-open-data-ridership", "Chicago", "bus ridership",
                        C.ridership_series, "series", "city-system/annual-series (1988-)",
                        "observed (CTA administrative boarding totals)", time_arg=None))
    probes.append(probe("city-open-data-ridership", "New York City", "subway ridership",
                        C.ridership_series, "series",
                        "city-system/annual-series (2021-; partial years dropped <360 days)",
                        "MODELLED — upstream fields are '..._total_estimated_ridership'; "
                        "label 'modelled' propagates as taint (Round-2 audit finding)",
                        time_arg=None))
    probes.append(probe("city-open-data-ridership", "Oslo, Norway", "transit ridership",
                        C.ridership_series, "series", "city-system/annual-series",
                        "n/a — negative control (unregistered city -> empty -> DataRequest)",
                        time_arg=None))
    probes[-1]["ok"] = probes[-1]["n_rows"] == 0
    probes[-1]["checks"] = {"empty_as_expected": probes[-1]["ok"]}

    rejected = [
        {"candidate": "Transitland API v2 (api.transit.land)",
         "why": "requires an api_key parameter — fails the keyless requirement"},
        {"candidate": "Mobility Database API v1 (api.mobilitydatabase.org)",
         "why": "302 to an auth flow; keyless access is via the public catalog CSV + "
                "mdb-latest GCS mirror, which is what the connector uses"},
        {"candidate": "NY MTA vxuj-8kew year 2020 (and any year with <360 days of data)",
         "why": "dataset starts 2020-03-01 (306 days) — a partial annual sum would poison "
                "CHANGE/TREND answers; dropped in-connector with a provenance note"},
        {"candidate": "IS.VEH.NVEH.P3 / IS.ROD.PAVE.ZS (World Bank)",
         "why": "Round-1 phantom rejection stands: codes look ideal, rows are dead outside "
                "Kenya/pre-2010"},
    ]
    payload = {"schema_version": "round2-source-census-v1", "ts": time.time(),
               "families_adopted": sorted({p["family"] for p in probes}),
               "all_ok": all(p["ok"] for p in probes),
               "probes": probes, "rejected": rejected}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(payload, f, indent=2)
    for p in probes:
        print(f"{'OK' if p['ok'] else 'XX'} {p['family']:26} {p['place']:28} "
              f"{p['entity']:18} n={p['n_rows']}")
    print(f"\nall_ok={payload['all_ok']} -> {OUT}")


if __name__ == "__main__":
    main()
