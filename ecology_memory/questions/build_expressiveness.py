#!/usr/bin/env python3
"""Create blocked probes that pressure meanings outside frozen v2.2.1."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

FAMILIES = {
    "FILTER": [
        "Show only research-grade Lantana records in Valparai.",
        "Keep elephant observations with no GBIF geospatial issue flags.",
        "List only CC0 green cat snake records in India.",
        "Which survey sites are classified as mature tropical rainforest?",
        "Keep bird observations whose checklist count is above five.",
        "Show Lantana records after 2022 that are in tree-cover pixels.",
        "Exclude occurrence records with coordinate uncertainty above one kilometre.",
        "List only survey sites above 1,100 metres elevation.",
        "Keep bird records identified to species rank, not genus.",
        "Show water-occurrence annotations greater than 20 percent.",
    ],
    "GROUP": [
        "Count recent bird observations by species in Valparai.",
        "Group Anamalai survey sites by habitat and count each group.",
        "Count Lantana records by year and data provider.",
        "Report elephant occurrence records by license class.",
        "Summarise survey-site elevation by habitat class.",
        "Count green cat snake records by Indian state.",
        "Give monthly mean NDVI for Valparai by year.",
        "Count bird observations by eBird hotspot.",
        "Group survey sites by ecoregion and habitat together.",
        "Rank species by record count within each land-cover class.",
    ],
    "ALIGN_UNITS": [
        "Compare 250 m NDVI with 10 m land cover only after aligning their pixels.",
        "Compare bird-record density per square kilometre across exact administrative polygons.",
        "How did monsoon-season NDVI change relative to the same months a year earlier?",
        "Compare 2024 NDVI with the nearest available 2024 land-cover product and state the mismatch.",
        "Give elevation in feet and metres for each survey site.",
        "Aggregate 10 m land cover to the 1 km MODIS support before relating them.",
        "Compare occurrence density using equal-area cells rather than geocoder bboxes.",
        "Align eBird's rolling 30-day window with a calendar-month fire series.",
        "Calculate distance to water from polygon edges, not raster-cell centres.",
        "Compare two trends only over years available in both series.",
    ],
    "CORROBORATE_UNCERTAINTY": [
        "Report only Lantana presences corroborated independently by GBIF and iNaturalist.",
        "Do eBird and GBIF agree that green cat snake is present in this area?",
        "Give a confidence interval for Lantana record density.",
        "Propagate coordinate uncertainty into distance-to-survey-site results.",
        "Flag where WorldCover and MODIS imply conflicting vegetation recovery.",
        "Estimate elephant occupancy and report posterior uncertainty.",
        "Separate absence from non-detection for sites with no records.",
        "Verify the NDVI trend with a second satellite product before answering.",
        "Show how sensitive the transfer result is to the climate envelope threshold.",
        "Return agreement, conflict, or insufficient evidence across three sources.",
    ],
    "DOCUMENT_CAUSAL_ARTIFACT": [
        "Find the papers supporting birds as Lantana seed dispersers and rank their evidence.",
        "Return a citable DOI card for every dataset used in this answer.",
        "Did Lantana cause the observed decline in native-tree regeneration?",
        "Would removing Lantana increase NDVI at these sites?",
        "Create both a map layer and a concise answer for this query.",
        "Explain why elephant observations cluster near survey sites.",
        "Return the answer, a verification checklist, and a field sampling plan.",
        "Which connector result changed since the previous run and why?",
        "Search the literature semantically for local names of this species.",
        "Choose and purchase the cheapest suitable satellite scene for validation.",
    ],
}

PROPOSALS = {"FILTER": "ALG-002", "GROUP": "ALG-003", "ALIGN_UNITS": "ALG-005/ALG-007",
             "CORROBORATE_UNCERTAINTY": "ALG-008 or uncertainty value semantics",
             "DOCUMENT_CAUSAL_ARTIFACT": "document/artifact/causal boundary evidence"}


def main():
    rows = []
    for family, questions in FAMILIES.items():
        for q in questions:
            rows.append({"id": f"eco-x{len(rows)+1:03d}", "sector": "ecology",
                         "family": family, "q": q, "blocked": True,
                         "proposal": PROPOSALS[family],
                         "reason": "meaning cannot be preserved by a single released v2.2.1 tree"})
    assert len(rows) == 50
    with open(os.path.join(HERE, "expressiveness.json"), "w") as f:
        json.dump({"bank": "ecology-expressiveness-v1", "questions": rows}, f, indent=2)


if __name__ == "__main__":
    main()
