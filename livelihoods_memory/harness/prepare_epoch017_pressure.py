#!/usr/bin/env python3
"""Normalize independently audited H23/H24 raw banks as pre-freeze development pressure.

These banks were generated against retired epoch 016 and are never countable blind evidence.
The explicit selections and repairs below are the durable pre-qwen admission record.
"""
from __future__ import annotations

import json
from pathlib import Path

from ir_schema import validate


ROOT = Path(__file__).resolve().parent.parent
H23_IDS = """001 004 005 009 010 012 013 015 019 021 022 023 024 025 026 029 030 033 034 035
039 040 041 046 048 049 050 051 052 055 057 059 060 061 063 064 065 075 077 078""".split()
H23_IDS = ["h23-" + value for value in H23_IDS]
H24_IDS = """003 008 009 011 013 015 017 019 021 026 029 030 033 034 035 038 041 042 044 045
046 050 051 052 053 057 059 063 064 065 068 070 072 073 074 076 077 078 079 080""".split()
H24_IDS = ["h24-" + value for value in H24_IDS]


def shape(gold):
    report = validate(gold)
    assert report["valid"], report["errors"]
    return [op for op in report["ops"] if op != "REGION"]


def walk(value, visit):
    if isinstance(value, list):
        for item in value: walk(item, visit)
    elif isinstance(value, dict):
        visit(value)
        for child in value.values(): walk(child, visit)


def select(raw, ids):
    rows = {row["id"]: row for row in raw["questions"]}
    assert set(ids) <= set(rows)
    return [json.loads(json.dumps(rows[row_id])) for row_id in ids]


def prepare_h23():
    raw = json.loads((ROOT / "questions/holdout-h23-generated.json").read_text())
    rows = select(raw, H23_IDS)
    by_id = {row["id"]: row for row in rows}
    # Direct pre-qwen execution found deterministic source limits.  These remain valuable
    # composition tests, but the truthful outcome is a typed DataRequest, never a partial answer.
    for row_id in ("h23-013","h23-015","h23-033","h23-034","h23-040","h23-050","h23-075"):
        by_id[row_id]["expect"]="data_request"
    for row_id in ("h23-025", "h23-026", "h23-029", "h23-030"):
        by_id[row_id]["type"] = "COMPOSITE"
    by_id["h23-051"]["q"] = ("Compare Kenya's 2023 self-employment with the country being used "
                                "as its comparator.")
    by_id["h23-052"]["q"] = ("Count craft workshops within 1 km of a bus stop in the Indian "
                                "focus city.")
    def atomic_focus(node):
        if node.get("op") == "SELECT" and node.get("region") == "?focus_city, India":
            node["region"] = "?focus_city_in_India"
    walk(by_id["h23-052"]["gold_ir"], atomic_focus)
    by_id["h23-055"]["q"] = "Markets in Accra within 1 km of the anchor amenity under review."
    by_id["h23-063"]["q"] = ("Transfer coworking-space records from Nairobi to the target city "
                                "under review using envelope.")
    by_id["h23-064"]["q"] = ("Using feature, estimate craft-workshop coverage for the underserved "
                                "district under review from Accra observations.")
    by_id["h23-065"]["q"] = ("Interpolate the market records observed in Bengaluru onto the peer "
                                "metro under review.")
    by_id["h23-078"]["q"] = ("Order France, Kenya, Spain by 2019→2021 female average weekly hours "
                                "change; return all three ascending.")
    def endpoint_2021(node):
        if node.get("op") == "SELECT" and isinstance(node.get("time"), dict) \
                and node["time"].get("start") == "2023":
            node["time"] = {"start":"2021", "end":"2021"}
    walk(by_id["h23-078"]["gold_ir"], endpoint_2021)
    for row in rows:
        row["gold_shape"] = shape(row["gold_ir"])
    return {"spec_version":"v2.1",
            "note":"H23 pre-freeze development pressure; generated against retired epoch 016; never blind evidence",
            "source_generated":"questions/holdout-h23-generated.json",
            "questions":rows}


def prepare_h24():
    raw = json.loads((ROOT / "questions/holdout-h24-generated.json").read_text())
    source_rows = select(raw, H24_IDS)
    rows=[]
    for source in source_rows:
        row={"id":source["id"], "sector":"livelihoods", "type":source["type"],
             "q":source["question"], "expect":source["expect"],
             "gold_ir":source["gold"], "must_hole":source.get("must_hole",False),
             "must_estimate":False, "capability_family":source.get("capability_family"),
             "adversarial":source.get("adversarial",False),
             "output_form":source.get("output_form")}
        rows.append(row)
    by_id={row["id"]:row for row in rows}
    by_id["h24-003"]["type"]="STATE"
    for row_id in ("h24-011","h24-013","h24-015"):
        gold=by_id[row_id]["gold_ir"]
        gold["left"],gold["right"]=gold["right"],gold["left"]
    by_id["h24-019"]["q"]="Madrid region — over 2022 to 2024, which way is unemployment heading?"
    by_id["h24-019"]["gold_ir"]["left"]["source"]["time"]={"start":"2022","end":"2024"}
    by_id["h24-030"]["q"]="Catalonia — employed persons in thousands for 2023?"
    by_id["h24-034"]["q"]="In 2023, what is Catalonia's employment rate minus Lombardy's?"
    by_id["h24-038"]["q"]="Coworking spaces — what is Porto's count minus Valencia's?"
    by_id["h24-044"]["q"]=("For each marketplace in Mysuru, how far is its nearest bank, in km?")
    by_id["h24-044"]["output_form"]="record set with dist_km"
    for row_id in ("h24-051","h24-052","h24-053"):
        by_id[row_id]["expect"]="answer_or_data_request"
    by_id["h24-063"]["q"]=("Among France, Germany, Spain and Kenya, which 2 have the lowest average "
                               "weekly hours worked in 2021?")
    for row_id in ("h24-064","h24-068"):
        by_id[row_id]["q"]=by_id[row_id]["q"].replace("cafe","coworking-space").replace(
            "cafes","coworking spaces")
        def replace_cafe(node):
            if node.get("op") == "SELECT" and node.get("entity") == "cafe":
                node["entity"]="coworking space"
        walk(by_id[row_id]["gold_ir"],replace_cafe)
    def whole_entity_hole(node):
        if node.get("op") == "SELECT" and node.get("entity") == "?entity_subtype":
            node["entity"]="?entity"
    walk(by_id["h24-070"]["gold_ir"],whole_entity_hole)
    def region_hole_node(node):
        if node.get("op") == "SELECT" and node.get("region") == "?place":
            node["region"]={"op":"REGION","place":"?place"}
    walk(by_id["h24-074"]["gold_ir"],region_hole_node)
    for row in rows:
        report=validate(row["gold_ir"]);assert report["valid"],(row["id"],report["errors"])
        row["gold_shape"]=[op for op in report["ops"] if op!="REGION"]
        row["must_estimate"]=report["has_estimate"]
        if row["capability_family"] is None:
            row["capability_family"]="spatial_composition"
    return {"spec_version":"v2.1",
            "note":"H24 conversational pre-freeze development pressure; generated against retired epoch 016; never blind evidence",
            "source_generated":"questions/holdout-h24-generated.json",
            "questions":rows}


def main():
    targets=(("questions/round2-h23-pressure.json",prepare_h23()),
             ("questions/round2-h24-pressure.json",prepare_h24()))
    for rel,payload in targets:
        path=ROOT/rel;path.write_text(json.dumps(payload,indent=2,ensure_ascii=False)+"\n")
        print(rel,len(payload["questions"]))


if __name__ == "__main__": main()
