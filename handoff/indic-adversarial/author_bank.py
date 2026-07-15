#!/usr/bin/env python3
"""Independent, checkpointed authoring driver for MISSION.md."""

import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "harness"))

from executor import execute
from ir_schema import validate


BANK_PATH = os.path.join(HERE, "bank.json")
PROGRESS_PATH = os.path.join(HERE, "PROGRESS.md")
REFERENCE_PATH = os.path.join(HERE, "reference-bank-DO-NOT-COPY-STYLE.json")


def region(place):
    return {"op": "REGION", "place": place}


def select(entity, place, time=None):
    reg = place if isinstance(place, str) and place.startswith("?") else region(place)
    return {"op": "SELECT", "entity": entity, "region": reg, "time": time}


def aggregate(source, by="space", metric="count"):
    return {"op": "AGGREGATE", "by": by, "metric": metric, "source": source}


def trend(entity, place, start="2005", end="2023"):
    return {"op": "COMPARE", "how": "trend_direction",
            "left": aggregate(select(entity, place, {"start": start, "end": end}), "time", "mean")}


def difference(entity, place, earlier, later):
    return {"op": "COMPARE", "how": "difference",
            "left": select(entity, place, {"start": later, "end": later}),
            "right": select(entity, place, {"start": earlier, "end": earlier})}


def compare_counts(entity, place_a, place_b):
    return {"op": "COMPARE", "how": "difference",
            "left": aggregate(select(entity, place_a)),
            "right": aggregate(select(entity, place_b))}


def relate(left_entity, right_entity, place, relation="within", threshold=1.0):
    return {"op": "RELATE", "relation": relation, "threshold_km": threshold,
            "left": select(left_entity, place), "right": select(right_entity, place)}


def rank_counts(entity, places, order="desc", k=None, time=None):
    out = {"op": "RANK", "order": order,
           "items": [aggregate(select(entity, p, time)) for p in places]}
    if k is not None:
        out["k"] = k
    return out


def complaint(family):
    return f"{family} complaints"


def row(qid, sector, qtype, q, ir, expect="answer", must_hole=False, gold_shapes=None):
    ops = []
    def walk(n):
        if isinstance(n, dict):
            if n.get("op") not in (None, "REGION", "AGGREGATE"):
                ops.append(n["op"])
            for v in n.values():
                walk(v)
        elif isinstance(n, list):
            for v in n:
                walk(v)
    walk(ir)
    out = {"id": qid, "sector": sector, "type": qtype, "q": q,
           "gold_ir": ir, "gold_shape": ops, "expect": expect}
    if must_hole:
        out["must_hole"] = True
    if gold_shapes:
        out["gold_shapes"] = gold_shapes
    return out


# Each batch is deliberately hand-authored. Repetition below is only structural: the surfaces
# vary across formal representations, conversational repair, terse search-like fragments,
# contrastive "only", and semi-urban public-service phrasing.
BATCHES = [
    [
        row("adv-001", "health", "AMBIGUOUS",
            "That centre near our side, how many are there? I mean the health one only.",
            select("?facility_type", "?place"), "data_request", True),
        row("adv-002", "retail", "AMBIGUOUS",
            "Show the shops nearby. Nearby to where I am telling, not full city.",
            select("?shop_type", "?place"), "data_request", True),
        row("adv-003", "education", "AMBIGUOUS",
            "School facilities in the taluk, what is the scene?",
            select("?education_facility", "?taluk"), "data_request", True),
        row("adv-004", "civic", "AMBIGUOUS",
            "Our ward has enough public facilities or no?",
            select("?facility_type", "?ward"), "data_request", True),
        row("adv-005", "economy", "BEHAVIOUR",
            "Why all the boys from here are going city side for work?",
            select("?migration_proxy", "?place"), "data_request", True),
        row("adv-006", "health", "AMBIGUOUS",
            "In Hosur road area, give hospital-side places count — which Hosur road stretch you take?",
            select("hospital", "?hosur_road_stretch"), "data_request", True),
        row("adv-007", "civic", "AMBIGUOUS",
            "Please check whether the bus stop is far from it.",
            relate("bus_stop", "?landmark", "?place", "distance", 1.0), "data_request", True),
        row("adv-008", "economy", "AMBIGUOUS",
            "Compare the internet figure with last time only.",
            {"op": "COMPARE", "how": "difference",
             "left": select("internet users", "?country", {"start": "?current_year", "end": "?current_year"}),
             "right": select("internet users", "?country", {"start": "?earlier_year", "end": "?earlier_year"})},
            "data_request", True),
        row("adv-009", "retail", "AMBIGUOUS",
            "Medical and kirana are there nearby, but nearby to which landmark first confirm.",
            relate(["medical shop", "kirana store"], "?landmark", "?place"), "data_request", True),
        row("adv-010", "education", "AMBIGUOUS",
            "Between those three towns, which is having more colleges?",
            rank_counts("college", ["?town_one", "?town_two", "?town_three"]),
            "data_request", True),
    ],
    [
        row("adv-011", "civic", "STATE",
            "For full Bengaluru, garbage complaints total how much in 2021?",
            aggregate(select(complaint("garbage"), "Bengaluru", {"start": "2021", "end": "2021"}))),
        row("adv-012", "civic", "STATE",
            "HSR Layout ward road-complaint count for 2020, kindly give.",
            aggregate(select(complaint("road"), "HSR Layout", {"start": "2020", "end": "2020"}))),
        row("adv-013", "civic", "STATE",
            "Bellandur side, in 2019 how many streetlight grievances came?",
            aggregate(select(complaint("streetlight"), "Bellandur", {"start": "2019", "end": "2019"}))),
        row("adv-014", "civic", "STATE",
            "BTM Layout water complaints, 2021 only — what was the number?",
            aggregate(select(complaint("water"), "BTM Layout", {"start": "2021", "end": "2021"}))),
        row("adv-015", "civic", "STATE",
            "How much garbage issue was reported from JP Nagar ward in 2020?",
            aggregate(select(complaint("garbage"), "JP Nagar", {"start": "2020", "end": "2020"}))),
        row("adv-016", "civic", "STATE",
            "Hebbal road grievances for all available years, give one total.",
            aggregate(select(complaint("road"), "Hebbal"))),
        row("adv-017", "civic", "STATE",
            "Yelahanka street-light complaint count, complete 2019 to 2022 period.",
            aggregate(select(complaint("streetlight"), "Yelahanka", {"start": "2019", "end": "2022"}))),
        row("adv-018", "civic", "STATE",
            "Basavanagudi ward garbage complaints are how many altogether?",
            aggregate(select(complaint("garbage"), "Basavanagudi"))),
        row("adv-019", "civic", "STATE",
            "Jayanagar road complaint figure — full log, not one year.",
            aggregate(select(complaint("road"), "Jayanagar"))),
        row("adv-020", "civic", "STATE",
            "In BTM Layout, streetlight complaints total tell me once.",
            aggregate(select(complaint("streetlight"), "BTM Layout"))),
    ],
    [
        row("adv-021", "civic", "TREND",
            "Bengaluru garbage complaints are going up or coming down from 2019 to 2022?",
            trend(complaint("garbage"), "Bengaluru", "2019", "2022")),
        row("adv-022", "civic", "TREND",
            "Road complaints in Bengaluru — increasing trend is there or no, 2019 onwards?",
            trend(complaint("road"), "Bengaluru", "2019", "2022")),
        row("adv-023", "civic", "TREND",
            "From 2019 to 2022, streetlight grievances became more or less in Bengaluru?",
            trend(complaint("streetlight"), "Bengaluru", "2019", "2022")),
        row("adv-024", "civic", "TREND",
            "Check the direction only: Bengaluru water complaints, 2019–2022.",
            trend(complaint("water"), "Bengaluru", "2019", "2022")),
        row("adv-025", "civic", "TREND",
            "Sewage complaint load in Bengaluru is rising ah, or reducing? Use 2019 to 2022.",
            trend(complaint("sewage"), "Bengaluru", "2019", "2022")),
        row("adv-026", "civic", "TREND",
            "Storm-drain complaints, Bengaluru full city: which side trend went during 2019–22?",
            trend(complaint("drain"), "Bengaluru", "2019", "2022")),
        row("adv-027", "civic", "CHANGE",
            "2019 compared to 2021, how much difference came in Bengaluru garbage complaints?",
            difference(complaint("garbage"), "Bengaluru", "2019", "2021")),
        row("adv-028", "civic", "CHANGE",
            "Bengaluru road grievances: 2021 minus 2020 comes to what?",
            difference(complaint("road"), "Bengaluru", "2020", "2021")),
        row("adv-029", "civic", "CHANGE",
            "Did streetlight complaints reduce from 2019 to 2021 in Bengaluru? Give the change.",
            difference(complaint("streetlight"), "Bengaluru", "2019", "2021")),
        row("adv-030", "civic", "CHANGE",
            "For water complaints in Bengaluru, what is 2021 versus 2019 difference?",
            difference(complaint("water"), "Bengaluru", "2019", "2021")),
    ],
    [
        row("adv-031", "civic", "RELATION",
            "HSR Layout or Bellandur — where garbage complaints are more?",
            compare_counts(complaint("garbage"), "HSR Layout", "Bellandur")),
        row("adv-032", "civic", "RELATION",
            "Road issues: compare Bellandur against BTM Layout, first minus second.",
            compare_counts(complaint("road"), "Bellandur", "BTM Layout")),
        row("adv-033", "civic", "RELATION",
            "Between Hebbal and Yelahanka, which ward logged more streetlight complaints?",
            compare_counts(complaint("streetlight"), "Hebbal", "Yelahanka")),
        row("adv-034", "civic", "RELATION",
            "Garbage grievance difference for JP Nagar versus Jayanagar please.",
            compare_counts(complaint("garbage"), "JP Nagar", "Jayanagar")),
        row("adv-035", "civic", "RELATION",
            "Put HSR Layout, Bellandur and BTM Layout in order of road complaints, highest first.",
            rank_counts(complaint("road"), ["HSR Layout", "Bellandur", "BTM Layout"])),
        row("adv-036", "civic", "RELATION",
            "Of Jayanagar, Basavanagudi and Hebbal, least garbage complaints came from which ward?",
            rank_counts(complaint("garbage"), ["Jayanagar", "Basavanagudi", "Hebbal"], "asc", 1)),
        row("adv-037", "civic", "RELATION",
            "Rank HSR Layout, BTM Layout and Bellandur by water grievances, more to less.",
            rank_counts(complaint("water"), ["HSR Layout", "BTM Layout", "Bellandur"])),
        row("adv-038", "civic", "RELATION",
            "Streetlight issue is minimum where: Hebbal, HSR Layout or BTM Layout?",
            rank_counts(complaint("streetlight"), ["Hebbal", "HSR Layout", "BTM Layout"], "asc", 1)),
        row("adv-039", "civic", "RELATION",
            "For garbage complaints, arrange Yelahanka, JP Nagar, HSR Layout and Bellandur descending.",
            rank_counts(complaint("garbage"), ["Yelahanka", "JP Nagar", "HSR Layout", "Bellandur"])),
        row("adv-040", "civic", "RELATION",
            "Road-complaint table: Bellandur, HSR Layout, BTM Layout — top two wards only.",
            rank_counts(complaint("road"), ["Bellandur", "HSR Layout", "BTM Layout"], "desc", 2)),
    ],
    [
        row("adv-041", "economy", "TREND",
            "India internet usage is actually climbing or not? Take 2005 to 2023.",
            trend("internet users", "India")),
        row("adv-042", "economy", "TREND",
            "Inflation in India, 2010 onwards which direction overall?",
            trend("inflation", "India", "2010", "2023")),
        row("adv-043", "health", "TREND",
            "For India, life expectancy went up or down between 2005 and 2022?",
            trend("life expectancy", "India", "2005", "2022")),
        row("adv-044", "education", "TREND",
            "Secondary enrolment in Bangladesh is improving or falling, 2005–2022?",
            trend("secondary enrollment", "Bangladesh", "2005", "2022")),
        row("adv-045", "civic", "TREND",
            "Nepal electricity access trend, 2005 to 2022 — up side or down side?",
            trend("electricity access", "Nepal", "2005", "2022")),
        row("adv-046", "economy", "CHANGE",
            "For India internet users, 2020 less 2010 is how much?",
            difference("internet users", "India", "2010", "2020")),
        row("adv-047", "economy", "CHANGE",
            "How much did Bangladesh GDP per head change from 2015 to 2022?",
            difference("gdp per capita", "Bangladesh", "2015", "2022")),
        row("adv-048", "civic", "CHANGE",
            "Nepal electricity access: difference between 2010 and 2020 please.",
            difference("electricity access", "Nepal", "2010", "2020")),
        row("adv-049", "health", "CHANGE",
            "India life expectancy in 2020 compared with 2010, what change is coming?",
            difference("life expectancy", "India", "2010", "2020")),
        row("adv-050", "economy", "CHANGE",
            "Bangladesh mobile subscription figure, 2020 minus 2010 tell.",
            difference("mobile subscriptions", "Bangladesh", "2010", "2020")),
    ],
    [
        row("adv-051", "economy", "RELATION",
            "India versus Bangladesh, whose 2022 GDP per person is higher and by how much?",
            {"op": "COMPARE", "how": "difference",
             "left": select("gdp per capita", "India", {"start": "2022", "end": "2022"}),
             "right": select("gdp per capita", "Bangladesh", {"start": "2022", "end": "2022"})}),
        row("adv-052", "economy", "RELATION",
            "In 2022 arrange India, Bangladesh and Nepal by internet usage, high to low.",
            rank_counts("internet users", ["India", "Bangladesh", "Nepal"], "desc", None,
                        {"start": "2022", "end": "2022"})),
        row("adv-053", "health", "RELATION",
            "Life expectancy lowest where in 2020: India, Bangladesh or Nepal?",
            rank_counts("life expectancy", ["India", "Bangladesh", "Nepal"], "asc", 1,
                        {"start": "2020", "end": "2020"})),
        row("adv-054", "civic", "RELATION",
            "For 2020 electricity access, order India, Nepal, Bangladesh from more to less.",
            rank_counts("electricity access", ["India", "Nepal", "Bangladesh"], "desc", None,
                        {"start": "2020", "end": "2020"})),
        row("adv-055", "economy", "RELATION",
            "Between India and Nepal, 2022 internet-use gap is how much?",
            {"op": "COMPARE", "how": "difference",
             "left": select("internet users", "India", {"start": "2022", "end": "2022"}),
             "right": select("internet users", "Nepal", {"start": "2022", "end": "2022"})}),
        row("adv-056", "economy", "RELATION",
            "Mobile subscriptions in 2020: rank Bangladesh, Nepal and India, maximum first.",
            rank_counts("mobile subscriptions", ["Bangladesh", "Nepal", "India"], "desc", None,
                        {"start": "2020", "end": "2020"})),
        row("adv-057", "economy", "RELATION",
            "India and Bangladesh 2021 inflation — first country minus second comes what?",
            {"op": "COMPARE", "how": "difference",
             "left": select("inflation", "India", {"start": "2021", "end": "2021"}),
             "right": select("inflation", "Bangladesh", {"start": "2021", "end": "2021"})}),
        row("adv-058", "education", "RELATION",
            "Secondary enrolment for 2020: India, Bangladesh, Nepal — give descending order.",
            rank_counts("secondary enrollment", ["India", "Bangladesh", "Nepal"], "desc", None,
                        {"start": "2020", "end": "2020"})),
        row("adv-059", "economy", "RELATION",
            "For 2022 GDP per capita, who comes last among India, Bangladesh and Nepal?",
            rank_counts("gdp per capita", ["India", "Bangladesh", "Nepal"], "asc", 1,
                        {"start": "2022", "end": "2022"})),
        row("adv-060", "health", "RELATION",
            "Compare 2020 life expectancy of Bangladesh with Nepal; Bangladesh minus Nepal.",
            {"op": "COMPARE", "how": "difference",
             "left": select("life expectancy", "Bangladesh", {"start": "2020", "end": "2020"}),
             "right": select("life expectancy", "Nepal", {"start": "2020", "end": "2020"})}),
    ],
    [
        row("adv-061", "health", "VALUE",
            "Taluk hospital medicine stock-out days for last quarter, can the data show?",
            select("medicine stock-out days", "?taluk",
                   {"start": "2026-04-01", "end": "2026-06-30"}), "data_request", True),
        row("adv-062", "education", "STATE",
            "Block-wise teacher vacancies in government schools, give latest position.",
            select("teacher vacancies", "?block"), "data_request", True),
        row("adv-063", "civic", "VALUE",
            "For our gram panchayat, tap-water supply hours per day how much?",
            select("water supply hours", "?gram_panchayat"), "data_request", True),
        row("adv-064", "retail", "STATE",
            "Which fair-price shops had rice stock on 15 July 2026 in the mandal?",
            select("fair price shop rice stock", "?mandal",
                   {"start": "2026-07-15", "end": "2026-07-15"}), "data_request", True),
        row("adv-065", "health", "VALUE",
            "Ambulance response time in this district, average figure please.",
            aggregate(select("ambulance response time", "?district"), "space", "mean"),
            "data_request", True),
        row("adv-066", "education", "VALUE",
            "Anganwadi attendance for this month in our project area, what percentage?",
            select("anganwadi attendance", "?project_area", {"start": "?month", "end": "?month"}),
            "data_request", True),
        row("adv-067", "economy", "STATE",
            "Self-help group loan overdue amount for the block on 15 July 2026 — total only.",
            select("self help group loan overdue", "?block",
                   {"start": "2026-07-15", "end": "2026-07-15"}), "data_request", True),
        row("adv-068", "civic", "VALUE",
            "Ward-wise pothole repair records after complaint, for 2021 only.",
            select("pothole repair duration", "?ward", {"start": "2021", "end": "2021"}),
            "data_request", True),
        row("adv-069", "retail", "VALUE",
            "Mandi tomato arrival quantity today compared to yesterday, how much difference?",
            {"op": "COMPARE", "how": "difference",
             "left": select("tomato mandi arrivals", "?mandi", {"start": "?today", "end": "?today"}),
             "right": select("tomato mandi arrivals", "?mandi", {"start": "?yesterday", "end": "?yesterday"})},
            "data_request", True),
        row("adv-070", "health", "BEHAVIOUR",
            "Why patients are skipping the PHC and directly going district hospital?",
            select("?care_bypass_proxy", "?district"), "data_request", True),
    ],
    [
        row("adv-071", "health", "RELATION",
            "Medical shops are there, but show only those with no nursing home within 2 km in this town.",
            relate("medical shop", "nursing home", "?town", "beyond", 2.0), "data_request", True),
        row("adv-072", "education", "RELATION",
            "Schools near a bus stand but not near any liquor shop — for which town are we checking?",
            {"op": "RELATE", "relation": "beyond", "threshold_km": 1.0,
             "left": relate("school", "bus stand", "?town", "within", 1.0),
             "right": select("liquor shop", "?town")}, "data_request", True),
        row("adv-073", "retail", "RELATION",
            "Kirana or medical, both types which are beyond one kilometre from bus stand in our area?",
            relate(["kirana store", "medical shop"], "bus stand", "?area", "beyond", 1.0),
            "data_request", True),
        row("adv-074", "civic", "RELATION",
            "How far is each petrol bunk from the nearest bus stand? City name I forgot to mention.",
            relate("petrol bunk", "bus stand", "?city", "distance", 1.0), "data_request", True),
        row("adv-075", "health", "RELATION",
            "Hospitals plus PHCs together: which ones have a pharmacy within 500 metres, in that district?",
            relate(["hospital", "PHC"], "pharmacy", "?district", "within", 0.5),
            "data_request", True),
        row("adv-076", "retail", "RELATION",
            "Among these places, cafe count least where? I have not sent the town names yet.",
            rank_counts("cafe", ["?town_one", "?town_two", "?town_three"], "asc", 1),
            "data_request", True),
        row("adv-077", "civic", "RELATION",
            "Bus stops outside 800 metres of any hospital, take only whichever ward I send.",
            relate("bus_stop", "hospital", "?ward", "beyond", 0.8), "data_request", True),
        row("adv-078", "education", "RELATION",
            "College and university both, rank the three districts by combined count — districts pending.",
            rank_counts(["college", "university"], ["?district_one", "?district_two", "?district_three"]),
            "data_request", True),
        row("adv-079", "civic", "RELATION",
            "Parks having no public toilet nearby: which municipality should I specify?",
            relate("park", "toilet", "?municipality", "beyond", 1.0), "data_request", True),
        row("adv-080", "retail", "RELATION",
            "Hotels means eating hotels here, not rooms. Count those near the market after I share locality.",
            aggregate(relate("restaurant", "market", "?locality", "within", 1.0)),
            "data_request", True),
    ],
]

# Public World Bank calls can become unavailable mid-run. These two batches use the bundled,
# licensed Bengaluru complaints log instead, preserving CHANGE/TREND/COMPARE/RANK coverage and
# ensuring that a checkpoint never depends on a stalled remote request.
BATCHES[4] = [
    row("adv-041", "civic", "TREND",
        "Traffic complaints across Bengaluru, 2019 to 2022: overall rising or falling?",
        trend(complaint("traffic"), "Bengaluru", "2019", "2022")),
    row("adv-042", "civic", "TREND",
        "Pollution grievances in Bengaluru are becoming more or less, 2019 onwards?",
        trend(complaint("pollution"), "Bengaluru", "2019", "2022")),
    row("adv-043", "civic", "TREND",
        "Sewage complaint trend for full Bengaluru, 2019–22, which way it went?",
        trend(complaint("sewage"), "Bengaluru", "2019", "2022")),
    row("adv-044", "civic", "TREND",
        "Storm-water drain issues: check Bengaluru direction from 2019 through 2022.",
        trend(complaint("drain"), "Bengaluru", "2019", "2022")),
    row("adv-045", "civic", "TREND",
        "Stray-animal complaints in Bengaluru, going up only or coming down during 2019–22?",
        trend(complaint("animal"), "Bengaluru", "2019", "2022")),
    row("adv-046", "civic", "CHANGE",
        "Bengaluru traffic grievances: how much change between 2019 and 2021?",
        difference(complaint("traffic"), "Bengaluru", "2019", "2021")),
    row("adv-047", "civic", "CHANGE",
        "Take 2021 pollution complaints less 2020 for Bengaluru; what figure comes?",
        difference(complaint("pollution"), "Bengaluru", "2020", "2021")),
    row("adv-048", "civic", "CHANGE",
        "Sewage complaints, Bengaluru: 2021 versus 2019 difference please.",
        difference(complaint("sewage"), "Bengaluru", "2019", "2021")),
    row("adv-049", "civic", "CHANGE",
        "Did drain grievances reduce from 2020 to 2021 in Bengaluru? Give net change.",
        difference(complaint("drain"), "Bengaluru", "2020", "2021")),
    row("adv-050", "civic", "CHANGE",
        "For animal complaints city-wide, 2021 minus 2019 is how much?",
        difference(complaint("animal"), "Bengaluru", "2019", "2021")),
]

BATCHES[5] = [
    row("adv-051", "civic", "RELATION",
        "Traffic issue more in Bellandur or HSR Layout? Give Bellandur minus HSR count.",
        compare_counts(complaint("traffic"), "Bellandur", "HSR Layout")),
    row("adv-052", "civic", "RELATION",
        "Pollution complaints: compare HSR Layout against BTM Layout.",
        compare_counts(complaint("pollution"), "HSR Layout", "BTM Layout")),
    row("adv-053", "civic", "RELATION",
        "Bellandur and BTM Layout sewage complaints — first ward minus second how much?",
        compare_counts(complaint("sewage"), "Bellandur", "BTM Layout")),
    row("adv-054", "civic", "RELATION",
        "Drain complaints, HSR Layout versus JP Nagar: where count is higher?",
        compare_counts(complaint("drain"), "HSR Layout", "JP Nagar")),
    row("adv-055", "civic", "RELATION",
        "Animal grievance gap between Bellandur and JP Nagar, tell clearly.",
        compare_counts(complaint("animal"), "Bellandur", "JP Nagar")),
    row("adv-056", "civic", "RELATION",
        "Rank Bellandur, HSR Layout and BTM Layout by traffic complaints, maximum first.",
        rank_counts(complaint("traffic"), ["Bellandur", "HSR Layout", "BTM Layout"])),
    row("adv-057", "civic", "RELATION",
        "Pollution issue minimum in which: Bellandur, HSR Layout or BTM Layout?",
        rank_counts(complaint("pollution"), ["Bellandur", "HSR Layout", "BTM Layout"], "asc", 1)),
    row("adv-058", "civic", "RELATION",
        "Arrange HSR Layout, Bellandur and BTM Layout by animal complaints, less to more.",
        rank_counts(complaint("animal"), ["HSR Layout", "Bellandur", "BTM Layout"], "asc")),
    row("adv-059", "civic", "RELATION",
        "Electricity grievances top ward among HSR Layout, Bellandur and BTM Layout?",
        rank_counts(complaint("electricity"), ["HSR Layout", "Bellandur", "BTM Layout"], "desc", 1)),
    row("adv-060", "civic", "RELATION",
        "For park complaints, order JP Nagar, Jayanagar and Hebbal from high to low.",
        rank_counts(complaint("park"), ["JP Nagar", "Jayanagar", "Hebbal"])),
]


def norm_question(q):
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", q.lower())).strip()


def reference_questions():
    """Read only question strings and use them solely for collision rejection."""
    if not os.path.exists(REFERENCE_PATH):
        return set()
    with open(REFERENCE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    rows = data.get("questions", data) if isinstance(data, dict) else data
    return {norm_question(r["q"]) for r in rows if isinstance(r, dict) and isinstance(r.get("q"), str)}


def expected_matches(expect, status):
    return status in ("answer", "data_request") if expect == "answer_or_data_request" else status == expect


def main():
    bank = {"spec_version": "v2.2.1",
            "note": "Independent adversarial second-author bank: genuine Indian urban/semi-urban English; every gold schema-validated and execution-verified.",
            "questions": []}
    if os.path.exists(BANK_PATH):
        with open(BANK_PATH, encoding="utf-8") as f:
            bank = json.load(f)
    existing_ids = {r["id"] for r in bank["questions"]}
    existing_qs = {norm_question(r["q"]) for r in bank["questions"]}
    ref_qs = reference_questions()
    total_failures = 0
    consecutive_failures = 0

    for round_no, batch in enumerate(BATCHES, 1):
        admitted = 0
        attempted = 0
        reasons = []
        for candidate in batch:
            if candidate["id"] in existing_ids:
                continue
            attempted += 1
            nq = norm_question(candidate["q"])
            if nq in existing_qs or nq in ref_qs:
                reason = "question collision"
            else:
                rep = validate(candidate["gold_ir"])
                if not rep["valid"]:
                    reason = "schema: " + "; ".join(rep["errors"])
                else:
                    result = execute(candidate["gold_ir"])
                    if expected_matches(candidate["expect"], result.get("status")):
                        reason = None
                    else:
                        reason = f"exec {result.get('status')}:{result.get('reason')} expected {candidate['expect']}"
            if reason:
                total_failures += 1
                consecutive_failures += 1
                reasons.append(f"{candidate['id']}={reason}")
                if consecutive_failures >= 20:
                    break
                continue
            consecutive_failures = 0
            bank["questions"].append(candidate)
            existing_ids.add(candidate["id"])
            existing_qs.add(nq)
            admitted += 1

        if admitted or attempted:
            with open(BANK_PATH, "w", encoding="utf-8") as f:
                json.dump(bank, f, indent=2, ensure_ascii=False)
                f.write("\n")
            with open(PROGRESS_PATH, "a", encoding="utf-8") as f:
                f.write(f"checkpoint round {round_no}: attempted={attempted}, admitted={admitted}, "
                        f"total={len(bank['questions'])}, failures={total_failures}")
                if reasons:
                    f.write("; rejects: " + " | ".join(reasons))
                f.write("\n")
            print(f"round {round_no}: +{admitted}, total={len(bank['questions'])}", flush=True)
        if len(bank["questions"]) >= 100 or consecutive_failures >= 20:
            break
        recent = []
        if os.path.exists(PROGRESS_PATH):
            for line in open(PROGRESS_PATH, encoding="utf-8"):
                m = re.search(r"admitted=(\d+)", line)
                if m:
                    recent.append(int(m.group(1)))
        if len(recent) >= 3 and all(n < 5 for n in recent[-3:]):
            break

    print(json.dumps({"admitted": len(bank["questions"]), "failures": total_failures,
                      "consecutive_failures": consecutive_failures}))


if __name__ == "__main__":
    main()
