#!/usr/bin/env python3
"""Deterministically build and execute the broad Round-2 development bank."""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path

from executor import execute
from ir_schema import validate

ROOT = Path(__file__).resolve().parent.parent
ROWS = []


def region(place): return {"op": "REGION", "place": place}
def sel(entity, place, start=None, end=None):
    time = None if start is None else {"start": str(start), "end": str(end if end is not None else start)}
    return {"op": "SELECT", "entity": entity, "region": region(place), "time": time}
def agg(source, metric="mean", by="time"):
    return {"op": "AGGREGATE", "by": by, "metric": metric, "source": source}
def comp(left, right=None, how="difference"):
    out = {"op": "COMPARE", "how": how, "left": left}
    if right is not None: out["right"] = right
    return out
def change(entity, place, early, late): return comp(sel(entity, place, late), sel(entity, place, early))
def trend(entity, place, start=None, end=None):
    return comp(agg(sel(entity, place, start, end)), how="trend_direction")
def ranking(entity, places, year, order="desc", k=None, spatial=False):
    items = [agg(sel(entity, p, year), "count", "space") if spatial else sel(entity, p, year)
             for p in places]
    out = {"op": "RANK", "items": items, "order": order}
    if k is not None: out["k"] = k
    return out


def preorder(node):
    out = []
    if isinstance(node, dict):
        if node.get("op") and node["op"] != "REGION": out.append(node["op"])
        for key in ("source", "left", "right", "target"):
            if key in node: out += preorder(node[key])
        for item in node.get("items", []): out += preorder(item)
    return out


def add(prefix, qtype, question, ir, source, grain, family, expect="answer", **meta):
    ROWS.append({"id": f"r2-{prefix}-{len(ROWS)+1:03d}", "sector": "livelihoods",
                 "type": qtype, "q": question, "expect": expect, "gold_ir": ir,
                 "gold_shape": preorder(ir), "source_family": source, "grain": grain,
                 "capability_family": family, **meta})


def build_ilo():
    grain = "country/annual-survey-series"
    point_cases = [
        ("France", "informal employment rate", 2022), ("Spain", "informal employment rate", 2021),
        ("Germany", "informal employment rate", 2022), ("France", "female informal employment rate", 2023),
        ("France", "male informal employment rate", 2023), ("Spain", "informal employment rate in agriculture", 2022),
        ("Germany", "average weekly hours worked", 2023), ("Germany", "female average weekly hours worked", 2023),
        ("Germany", "male average weekly hours worked", 2023), ("France", "average weekly hours worked", 2022),
        ("Spain", "labour underutilization rate", 2023), ("France", "labor underutilization rate", 2022),
        ("Germany", "time related underemployment rate", 2023), ("Spain", "time related underemployment rate", 2022),
        ("Kenya", "average weekly hours worked", 2021), ("Ghana", "average weekly hours worked", 2017),
    ]
    for i, (place, entity, year) in enumerate(point_cases):
        forms = [f"What was {entity} in {place} in {year}?",
                 f"For {year}, report {place}'s {entity}.",
                 f"I need the {year} value of {entity} for {place}."]
        add("ilo", "STATE", forms[i % 3], sel(entity, place, year), "ilostat", grain, "point_select")
    windows = [
        ("France", "informal employment rate", 2018, 2023), ("Spain", "informal employment rate", 2017, 2022),
        ("Germany", "average weekly hours worked", 2018, 2023), ("France", "female average weekly hours worked", 2019, 2023),
        ("Spain", "male average weekly hours worked", 2016, 2021), ("France", "labour underutilization rate", 2018, 2023),
        ("Germany", "labor underutilization rate", 2017, 2022), ("Spain", "time related underemployment rate", 2019, 2023),
        ("Kenya", "average weekly hours worked", 2019, 2021), ("Ghana", "average weekly hours worked", 2015, 2022),
    ]
    for i, (place, entity, start, end) in enumerate(windows):
        add("ilo", "STATE", f"Show {place}'s {entity} from {start} through {end}.",
            sel(entity, place, start, end), "ilostat", grain, "window_select")
    changes = [
        ("France","informal employment rate",2018,2023),("Spain","informal employment rate",2017,2022),
        ("France","female informal employment rate",2018,2023),("Spain","male informal employment rate",2017,2022),
        ("Germany","average weekly hours worked",2018,2023),("France","average weekly hours worked",2017,2022),
        ("Spain","average weekly hours worked",2016,2021),("Germany","female average weekly hours worked",2018,2023),
        ("France","male average weekly hours worked",2017,2022),("Spain","female average weekly hours worked",2016,2021),
        ("France","labour underutilization rate",2018,2023),("Germany","labor underutilization rate",2017,2022),
        ("Spain","labour underutilization rate",2018,2023),("France","time related underemployment rate",2018,2023),
        ("Germany","time related underemployment rate",2017,2022),("Spain","time related underemployment rate",2018,2023),
    ]
    for place, entity, early, late in changes:
        add("ilo", "CHANGE", f"By how much did {place}'s {entity} change from {early} to {late}?",
            change(entity, place, early, late), "ilostat", grain, "endpoint_change")
    trends = [
        ("France","informal employment rate",2015,2023),("Spain","informal employment rate",2015,2023),
        ("France","female informal employment rate",2015,2023),("Germany","average weekly hours worked",2015,2023),
        ("France","average weekly hours worked",2015,2023),("Spain","average weekly hours worked",2015,2023),
        ("Germany","female average weekly hours worked",2015,2023),("France","male average weekly hours worked",2015,2023),
        ("Spain","labour underutilization rate",2015,2023),("France","labor underutilization rate",2015,2023),
        ("Germany","time related underemployment rate",2015,2023),("Spain","time related underemployment rate",2015,2023),
    ]
    for i,(place,entity,start,end) in enumerate(trends):
        verb = "rising or falling" if i%2 == 0 else "increasing or decreasing"
        add("ilo", "TREND", f"Was {place}'s {entity} {verb} between {start} and {end}?",
            trend(entity,place,start,end), "ilostat", grain, "bounded_trend")
    comparisons = [
        ("average weekly hours worked","France","Germany",2023),
        ("average weekly hours worked","France","Spain",2022),
        ("female average weekly hours worked","Germany","France",2023),
        ("male average weekly hours worked","Germany","Spain",2022),
        ("informal employment rate","France","Spain",2022),
        ("female informal employment rate","France","Spain",2022),
        ("labour underutilization rate","France","Spain",2023),
        ("labor underutilization rate","Germany","France",2022),
        ("time related underemployment rate","Germany","Spain",2023),
        ("time related underemployment rate","France","Germany",2022),
    ]
    for entity,a,b,year in comparisons:
        add("ilo", "COMPOSITE", f"What was the {entity} gap between {a} and {b} in {year}?",
            comp(sel(entity,a,year),sel(entity,b,year)), "ilostat", grain, "place_compare")
    ratios = [
        ("Germany","female average weekly hours worked","male average weekly hours worked",2023),
        ("France","female average weekly hours worked","male average weekly hours worked",2022),
        ("Spain","female average weekly hours worked","male average weekly hours worked",2021),
        ("France","informal employment rate","informal employment rate in agriculture",2022),
        ("Spain","informal employment rate","informal employment rate in agriculture",2022),
        ("Germany","labour underutilization rate","time related underemployment rate",2022),
    ]
    for place,left,right,year in ratios:
        add("ilo", "COMPOSITE", f"In {place} in {year}, what was the ratio of {left} to {right}?",
            comp(sel(left,place,year),sel(right,place,year),"ratio"), "ilostat", grain, "same_unit_ratio")
    ranks = [
        ("average weekly hours worked",["France","Germany","Spain","Kenya"],2021,"desc",2,"highest"),
        ("average weekly hours worked",["France","Germany","Spain","Kenya"],2021,"asc",None,"lowest to highest"),
        ("informal employment rate",["France","Germany","Spain","Italy"],2022,"desc",None,"highest to lowest"),
        ("labour underutilization rate",["France","Germany","Spain","Kenya"],2021,"asc",2,"lowest"),
    ]
    for entity,places,year,order,k,word in ranks:
        suffix = (f"return only the {k} {'highest' if order=='desc' else 'lowest'}" if k else word)
        text = f"Rank {', '.join(places[:-1])}, and {places[-1]} by {entity} in {year}, {suffix}."
        add("ilo","RANKING",text,ranking(entity,places,year,order,k),"ilostat",grain,
            "top_k_rank" if k else "nary_rank")


def build_euro():
    grain="nuts2/annual-survey-series"
    places=["Ile de France","Berlin","Madrid region","Catalonia","Lombardy","Warsaw capital region"]
    points=[]
    for i,p in enumerate(places):
        points += [(p,"employment rate",2024),(p,"unemployment rate",2023)]
    for i,(p,e,y) in enumerate(points):
        add("euro","STATE",f"What was the {e} in {p} in {y}?",sel(e,p,y),"eurostat",grain,"point_select")
    windows=[(places[i%6], "female employment rate" if i%2 else "employed persons", 2021,2024) for i in range(8)]
    for i,(p,e,s,t) in enumerate(windows):
        q = (f"Show {p}'s {e} for {s} to {t}." if i < 6 else
             f"Return the complete {s}–{t} {e} series for {p}.")
        add("euro","STATE",q,sel(e,p,s,t),"eurostat",grain,"window_select")
    change_entities=["employment rate","unemployment rate","female employment rate","male employment rate"]
    for i in range(16):
        p,e=places[i%6],change_entities[i%4]
        q = (f"How much did {e} in {p} change between 2021 and 2024?" if i < 12 else
             f"Calculate the 2024-minus-2021 change in {p}'s {e}.")
        add("euro","CHANGE",q,
            change(e,p,2021,2024),"eurostat",grain,"endpoint_change")
    for i in range(10):
        p,e=places[i%6],("employment rate" if i%2==0 else "unemployment rate")
        q = (f"Was {p}'s {e} rising or falling from 2021 through 2024?" if i < 6 else
             f"What direction did {p}'s {e} take over 2021–2024?")
        add("euro","TREND",q,
            trend(e,p,2021,2024),"eurostat",grain,"bounded_trend")
    pairs=[(places[i%6],places[(i+1)%6]) for i in range(10)]
    for i,(a,b) in enumerate(pairs):
        e="employment rate" if i%2==0 else "unemployment rate"
        q = (f"In 2024, what was the {e} difference between {a} and {b}?" if i < 6 else
             f"Subtract {b}'s 2024 {e} from {a}'s.")
        add("euro","COMPOSITE",q,
            comp(sel(e,a,2024),sel(e,b,2024)),"eurostat",grain,"place_compare")
    for i,p in enumerate(places):
        add("euro","COMPOSITE",f"What was the female-to-male employment-rate ratio in {p} in 2024?",
            comp(sel("female employment rate",p,2024),sel("male employment rate",p,2024),"ratio"),
            "eurostat",grain,"same_unit_ratio")
    for i in range(10):
        e="employment rate" if i<5 else "unemployment rate"
        order="desc" if i%2==0 else "asc"; k=2 if i in (2,3,8,9) else None
        wording="highest first" if order=="desc" else "lowest first"
        if k: wording=f"return only the {k} {'highest' if order=='desc' else 'lowest'}"
        register = "Order" if i >= 6 else "Sort" if i >= 4 else "Rank"
        add("euro","RANKING",f"{register} {', '.join(places[:-1])}, and {places[-1]} by 2024 {e}; {wording}.",
            ranking(e,places,2024,order,k),"eurostat",grain,"top_k_rank" if k else "nary_rank")


def build_wb():
    grain="country/annual-series"
    countries=["India","Kenya","Ghana","France","Germany","Spain"]
    entities=["self employment","vulnerable employment","labor force participation","youth unemployment",
              "wage and salaried workers","employment in services","employment in agriculture","unemployment"]
    for i,e in enumerate(entities):
        p=countries[i%6]
        add("wb","STATE",f"Show {e} in {p} from 2016 through 2022.",sel(e,p,2016,2022),
            "world-bank",grain,"window_select")
    for i,e in enumerate(entities):
        p=countries[(i+2)%6]
        add("wb","CHANGE",f"By how much did {p}'s {e} change from 2015 to 2022?",change(e,p,2015,2022),
            "world-bank",grain,"endpoint_change")
    for i in range(6):
        e=entities[i];p=countries[i]
        add("wb","TREND",f"Between 2012 and 2022, was {e} in {p} rising or falling?",trend(e,p,2012,2022),
            "world-bank",grain,"bounded_trend")
    for i in range(8):
        e=entities[i]; order="asc" if i%2 else "desc"; k=2 if i>=4 else None
        ps=countries[:4+(i%2)]
        add("wb","RANKING",f"Rank {', '.join(ps[:-1])}, and {ps[-1]} by {e} in 2022, "
            f"{'lowest' if order=='asc' else 'highest'} first"+(f", keeping {k}" if k else "")+".",
            ranking(e,ps,2022,order,k),"world-bank",grain,"top_k_rank" if k else "nary_rank")
    mixed=[
        ("France","self employment","informal employment rate",2022,"world-bank","ilostat"),
        ("Spain","self employment","informal employment rate",2022,"world-bank","ilostat"),
        ("France","labor force participation","labour underutilization rate",2022,"world-bank","ilostat"),
        ("Germany","labor force participation","labor underutilization rate",2022,"world-bank","ilostat"),
        ("France","labor force participation","employment rate",2022,"world-bank","eurostat","Ile de France"),
        ("Germany","labor force participation","employment rate",2022,"world-bank","eurostat","Berlin"),
        ("Spain","labor force participation","employment rate",2022,"world-bank","eurostat","Madrid region"),
        ("Spain","unemployment","unemployment rate",2022,"world-bank","eurostat","Catalonia"),
    ]
    for item in mixed:
        country,left,right,year,s1,s2,*override=item; rp=override[0] if override else country
        add("mix","COMPOSITE",f"What was the numerical percentage-point gap between {left} in {country} "
            f"and {right} in {rp} in {year}?",comp(sel(left,country,year),sel(right,rp,year)),
            [s1,s2],["country/annual-series", "nuts2/annual-survey-series" if s2=="eurostat" else
                     "country/annual-survey-series"],"mixed_source_compare")


def build_osm():
    grain="city-bbox/point-record"; places=["Bengaluru, India","Nairobi, Kenya","Accra, Ghana"]
    entities=["marketplace","coworking space","craft workshop"]
    for i in range(6):
        p,e=places[i%3],entities[(i//2)%3]
        ir=agg(sel(e,p),"presence","space")
        add("osm","STATE",f"Is at least one mapped {e} present in {p}?",ir,"osm-overpass",grain,"presence")
    pairs=[("marketplace","coworking space"),("craft workshop","marketplace"),
           ("coworking space","craft workshop")]
    for i in range(6):
        p=places[i%3];a,b=pairs[i%3]
        ir={"op":"RELATE","relation":"cooccur","threshold_km":5.0,"left":sel(a,p),"right":sel(b,p)}
        q = (f"Which mapped {a}s in {p} co-occur within 5 km of a {b}?" if i < 3 else
             f"Find {p}'s mapped {a}s sharing a 5 km neighbourhood with a {b}.")
        add("osm","RELATION",q,ir,
            "osm-overpass",grain,"cooccur")
    layers=["name","opening_hours","operator","name","opening_hours","operator"]
    for i,layer in enumerate(layers):
        p,e=places[i%3],entities[i%3]
        ir={"op":"ANNOTATE","source":sel(e,p),"layer":layer}
        q = (f"Show mapped {e}s in {p} annotated with their {layer.replace('_',' ')} attribute." if i < 3 else
             f"Attach the {layer.replace('_',' ')} field to every mapped {e} in {p}.")
        add("osm","VALUE",q,
            ir,"osm-overpass",grain,"annotate")


def build_gaps():
    def hole_sel(entity, place):
        return {"op":"SELECT","entity":entity,"region":place,"time":None}
    cases=[
        ("AMBIGUOUS","What is the informal-employment rate around here?",hole_sel("informal employment rate","?place"),"?place"),
        ("AMBIGUOUS","Show the employment rate in this region.",hole_sel("employment rate","?place"),"?place"),
        ("AMBIGUOUS","How have livelihood conditions changed in France?",trend("?indicator","France"),"?indicator"),
        ("AMBIGUOUS","What was the employment rate in the area I mentioned?",hole_sel("employment rate","?place"),"?place"),
        ("AMBIGUOUS","Which livelihood facilities are mapped in Berlin?",sel("?facility_type","Berlin"),"?facility_type"),
        ("AMBIGUOUS","How many of those workplaces are nearby?",
         agg(hole_sel("?workplace_type","?place"),"count","space"),"?workplace_type"),
        ("BEHAVIOUR","Why do workers in France choose informal jobs?",sel("?proxy","France"),"?proxy"),
        ("BEHAVIOUR","Do residents in Berlin prefer shorter working weeks?",sel("?proxy","Berlin"),"?proxy"),
        ("BEHAVIOUR","Would people here rather be self-employed?",hole_sel("?proxy","?place"),"?proxy"),
        ("BEHAVIOUR","Why are young people in Madrid avoiding formal work?",sel("?proxy","Madrid"),"?proxy"),
        ("STATE","Where are today's job vacancies in Berlin?",sel("job vacancies","Berlin"),None),
        ("STATE","Show household income surveys for Accra in 2024.",sel("household income survey","Accra, Ghana",2024),None),
    ]
    for typ,q,ir,hole in cases:
        add("gap",typ,q,ir,"hole" if hole else "none","unresolved" if hole else "unsupported",
            "ambiguity" if hole else "source_gap",expect="data_request",must_hole=bool(hole),
            behaviour=typ=="BEHAVIOUR")


def main():
    build_ilo(); build_euro(); build_wb(); build_osm(); build_gaps()
    assert len(ROWS)==214, len(ROWS)
    assert len({r["id"] for r in ROWS})==len(ROWS)
    assert len({r["q"] for r in ROWS})==len(ROWS)
    failures=[]
    for index,row in enumerate(ROWS,1):
        print(f"gold {index:03d}/{len(ROWS)} {row['id']} {row['source_family']}", flush=True)
        rep=validate(row["gold_ir"])
        if not rep["valid"]: failures.append((row["id"],"schema",rep["errors"])); continue
        if bool(rep["holes"]) != bool(row.get("must_hole")): failures.append((row["id"],"holes",rep["holes"])); continue
        try: result=execute(row["gold_ir"])
        except Exception as exc: failures.append((row["id"],"crash",repr(exc))); continue
        if result.get("status") != row["expect"]: failures.append((row["id"],"execution",result));
    if failures:
        print(json.dumps(failures[:30],indent=2,default=str)); raise SystemExit(f"{len(failures)} gold failures")
    payload={"spec_version":"v2.1","note":"deterministic Round-2 breadth development bank; every gold schema-validated and executed before write","questions":ROWS}
    target=ROOT/"questions"/"round2-dev.json"; target.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps({"questions":len(ROWS),"sources":Counter(str(r["source_family"]) for r in ROWS),
                      "types":Counter(r["type"] for r in ROWS),"families":Counter(r["capability_family"] for r in ROWS)},
                     indent=2,default=dict))


if __name__=="__main__": main()
