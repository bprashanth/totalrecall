#!/usr/bin/env python3
"""Build deliberate Round-2 expressiveness probes without inventing half-golds."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

FAMILIES = {
    "attribute_filter": [
        "Which mapped marketplaces in Nairobi are open on Sundays?",
        "Show coworking spaces in Bengaluru that have wheelchair access.",
        "How many craft workshops in Accra have a named operator?",
        "Which Nairobi banks lack an opening-hours tag?",
        "Find Accra marketplaces whose names contain 'community'.",
        "Which Bengaluru coworking spaces have both a website and phone number?",
    ],
    "subgroup_filter": [
        "What was France's informal-employment rate for women aged 25 to 54 in 2023?",
        "Compare weekly hours for male and female employees in Germany in 2023.",
        "What was Spain's underutilization rate among young people in 2022?",
        "Show informal employment in French agriculture for women in 2021.",
        "What share of Berlin's employed people aged 55 to 64 were women in 2024?",
        "How did Madrid unemployment among tertiary-educated women change from 2021 to 2024?",
    ],
    "group_partition": [
        "Break down Germany's average weekly hours by sex for every year since 2019.",
        "Give France's informal-employment rate by economic sector in 2023.",
        "Compare unemployment across every education level in Madrid in 2024.",
        "Count Nairobi marketplaces by operator.",
        "Group Bengaluru craft workshops by craft type.",
        "Return employment rates for every NUTS-2 region of Spain in 2024.",
    ],
    "record_set": [
        "Show all marketplaces or coworking spaces in Nairobi.",
        "Which Accra facilities are both craft workshops and shops?",
        "List Bengaluru banks and ATMs without duplicates.",
        "Which Nairobi marketplaces appear in both OSM extracts from the two dates?",
        "Show craft workshops in Accra but exclude anything also tagged as a marketplace.",
        "Find coworking spaces within 2 km of either a bank or an ATM in Bengaluru.",
    ],
    "derived_rate": [
        "What fraction of Nairobi's mapped livelihood facilities are marketplaces?",
        "How many employed people per marketplace are there in Catalonia?",
        "What is France's informal-worker count from its rate and employed population?",
        "Compute the percentage-point gender gap in German weekly hours in 2023.",
        "Normalize Accra's craft-workshop count per 10,000 residents.",
        "What is the compound annual growth rate of Spain's employed population since 2021?",
    ],
    "distribution": [
        "What is the median distance from Nairobi coworking spaces to marketplaces?",
        "Give the 90th percentile distance from Accra craft workshops to banks.",
        "Show a histogram of marketplaces per square kilometre across Bengaluru districts.",
        "What share of Nairobi marketplaces lies in the densest ten percent of grid cells?",
        "Report the interquartile range of weekly hours in France.",
        "Which Berlin employment-rate years are statistical outliers?",
    ],
    "temporal_alignment": [
        "Compare France's 2024 self-employment value with its latest available informal-employment value.",
        "Lag unemployment by one year and compare it with self-employment in Spain.",
        "Align quarterly Madrid unemployment with annual employed-person totals for 2021 to 2024.",
        "Compare Germany's labor series using only years present in both ILOSTAT and World Bank.",
        "Recompute France's trend using the data vintage published before 2024.",
        "Interpolate Kenya's missing 2020 weekly-hours value before calculating its change.",
    ],
    "uncertainty_conflict": [
        "Do ILOSTAT and World Bank agree on France's self-employment rate in 2023?",
        "Give Madrid's unemployment rate with its confidence interval.",
        "Which source is more reliable when Eurostat and a national survey disagree for Berlin?",
        "Corroborate Nairobi's marketplace count with an independent official source.",
        "Flag every French informal-employment observation marked low reliability or a series break.",
        "How sensitive is Spain's underutilization trend to choosing a different ILO survey source?",
    ],
    "multi_output": [
        "Compare marketplaces in Nairobi and Accra, and list the Nairobi ones near coworking spaces.",
        "Give France's informal-employment trend and its 2023 value.",
        "Rank the six NUTS regions by employment rate and explain each change since 2021.",
        "Count Bengaluru craft workshops, then show the five nearest to a marketplace.",
        "Report male and female German weekly hours and the ratio between them.",
        "Tell me whether Madrid unemployment fell and how many employed people it had in 2024.",
    ],
    "causal_counterfactual": [
        "Did opening more marketplaces cause household incomes to rise in Nairobi?",
        "Why did informal employment fall in France after 2021?",
        "What would Berlin's employment rate have been without the pandemic?",
        "Would adding ten coworking spaces reduce unemployment in Accra?",
        "Did lower weekly hours improve worker wellbeing in Germany?",
        "How many jobs will a new marketplace create in Bengaluru?",
    ],
}

PROPOSALS = {
    "attribute_filter": "FILTER(source,predicate)",
    "subgroup_filter": "FILTER(source,dimension predicates)",
    "group_partition": "GROUP(source,keys,metric)",
    "record_set": "SET(items,how)",
    "derived_rate": "unit-tagged DERIVE(expression)",
    "distribution": "distribution-valued AGGREGATE",
    "temporal_alignment": "ALIGN(series,calendar,join,lag,vintage)",
    "uncertainty_conflict": "epistemic CORROBORATE/VERIFY",
    "multi_output": "dialogue-layer BUNDLE/CLAUSE plan",
    "causal_counterfactual": "typed causal DataRequest or future causal claim layer",
}


def main():
    rows = []
    for family, questions in FAMILIES.items():
        for index, question in enumerate(questions, 1):
            rows.append({
                "id": f"r2-break-{family}-{index:02d}",
                "sector": "livelihoods", "type": "EXPRESSIVENESS",
                "q": question, "adversarial": True, "admission": "expressiveness_probe",
                "capability_family": family, "expected_missing": PROPOSALS[family],
                "gold_attempt": None,
                "reject_reason": ("frozen v2.1 cannot represent the full request without " +
                                  PROPOSALS[family] + "; do not shrink the gold"),
            })
    assert len(rows) == 60
    assert len({row["q"] for row in rows}) == len(rows)
    target = ROOT / "questions" / "round2-breakers.json"
    target.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps({"questions": len(rows), "families": len(FAMILIES),
                      "per_family": {key: len(value) for key, value in FAMILIES.items()}}, indent=2))


if __name__ == "__main__":
    main()
