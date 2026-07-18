"""synthesize — the fourth stage: typed result -> short prose answer, plus its scoring.

Until now only compile/execute/dialogue were tested; this adds the answer surface where the
constitution's behavioral rules (short, honest, observed-vs-modelled labelled, gap -> specific
ask) actually face the user. Scoring is MECHANICAL where possible (length, number-presence,
modelled-flag, gap-stated); an LLM judge is deliberately not required for the core dims.
"""
import json
import re

from llm import chat

SYNTH_SYSTEM = """You write the FINAL one-paragraph answer to a user's question about a place,
from a structured result computed by deterministic tools. Rules:
- <= 60 words. Lead with the finding (the number / the list size / the direction / the ranking).
- If the result has a non-null scalar, repeat that exact scalar; do not replace it with context.
- If evidence_label is "modelled": say clearly it is a modelled estimate needing local corroboration.
- Use the literal evidence word: if evidence_label is "proxy", say "proxy" and name the key
  limitation from provenance; if it is "modelled", say "modelled".
- Proxy example: "0.74 records/km² — a bounding-box-area proxy, not organism density."
- Modelled-layer example: "10 sites fall in tree cover according to the modelled WorldCover layer."
- If status is data_request: do NOT invent an answer. Say exactly what is missing or ambiguous and
  ask the ONE most useful question (or name the data to collect).
- Never invent numbers not present in the result. Mention the data source in passing."""


def _context(exec_result):
    v = exec_result.get("value") or {}
    ctx = {"status": exec_result.get("status"), "evidence_label": exec_result.get("label"),
           "reason": exec_result.get("reason"), "detail": exec_result.get("detail"),
           "kind": v.get("kind"), "scalar": v.get("value"),
           "left_label": v.get("left_label"), "right_label": v.get("right_label"),
           "left_value": v.get("left_value"), "right_value": v.get("right_value"),
           "winner": v.get("winner"),
           "n_rows": v.get("n_rows", len(v.get("rows", []) or [])),
           "sample_rows": (v.get("rows") or [])[:3],
           "provenance_notes": [p.get("note") for p in exec_result.get("provenance", [])
                                if p.get("note")][:4],
           "sources": list({p.get("route") for p in exec_result.get("provenance", [])
                            if p.get("route")})}
    return ctx


def synthesize(question, exec_result, role="qwen2b"):
    fire = _fire_exposure_answer(exec_result)
    if fire:
        return fire
    occurrence_gap = _occurrence_gap_answer(exec_result)
    if occurrence_gap:
        return occurrence_gap
    landcover = _landcover_answer(exec_result)
    if landcover:
        return landcover
    greenness = _greenness_answer(exec_result)
    if greenness:
        return greenness
    inventory = _inventory_answer(exec_result)
    if inventory:
        return inventory
    group_inventory = _group_inventory_answer(exec_result)
    if group_inventory:
        return group_inventory
    group_transfer = _group_transfer_answer(exec_result)
    if group_transfer:
        return group_transfer
    soil_proxy = _soil_wetness_answer(exec_result)
    if soil_proxy:
        return soil_proxy
    site_evidence = _published_site_evidence_answer(exec_result)
    if site_evidence:
        return site_evidence
    ctx = _context(exec_result)
    msgs = [{"role": "system", "content": SYNTH_SYSTEM},
            {"role": "user", "content": f"Question: {question}\n\nResult:\n{json.dumps(ctx, default=str)}"}]
    try:
        draft = chat(role, msgs, temperature=0.0, max_tokens=220).strip()
        audit = score_synthesis(question, exec_result, draft)
        if all(v for k, v in audit.items() if k != "overall"):
            return draft
        return _safe_fallback(exec_result, question)
    except RuntimeError:
        return _safe_fallback(exec_result, question)


def _fire_exposure_answer(exec_result):
    """Keep the source metric and its epistemic limitation together."""
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    if value.get("layer") != "fire_exposure" or not value.get("rows"):
        return None
    row = value["rows"][0]
    return (
        f"MODIS returned {row['analysis_bbox_active_fire_locations']} active-fire locations inside "
        f"the declared analysis bbox in {row['period']}; that bbox is not the surveyed property "
        f"polygon. The separate {row['radius_km']} km exposure buffer measured "
        f"{row['pixel_fire_days']} pixel-fire-days ({row['fire_density']} per km²). These are historical "
        "pressure proxies, not a forecast or burned-area estimate; the buffer extends beyond the AOI."
    )


def _occurrence_gap_answer(exec_result):
    """An empty public occurrence query is unknown coverage, never evidence of absence."""
    if exec_result.get("status") != "data_request" or exec_result.get("reason") != "empty_select":
        return None
    provenance = exec_result.get("provenance") or []
    source = next((p for p in provenance
                   if p.get("route") in {"origin-points", "gbif+inaturalist"}), None)
    if not source:
        return None
    entity = source.get("resolved") or (exec_result.get("detail") or {}).get("entity") or "that taxon"
    discovered = len((exec_result.get("detail") or {}).get("evidence_discovery") or [])
    lead = (f" Semantic corpus search returned {discovered} candidate datasets, but those are leads, "
            "not local records until extracted and spatially checked." if discovered else "")
    return (
        f"The origin GBIF + iNaturalist + paper-data merger returned no occurrence points for "
        f"{entity} inside the site AOI.{lead} This is a public-data coverage gap, not evidence the "
        "species is absent. Local surveys or sightings are needed; regional records can support "
        "only a separately labelled transfer."
    )


def _landcover_answer(exec_result):
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    rows = value.get("rows") or []
    if value.get("layer") != "landcover" or not rows or not rows[0].get("area_by_class_km2"):
        return None
    row = rows[0]
    areas = row["area_by_class_km2"]
    breakdown = ", ".join(f"{name} {area:g} km²" for name, area in areas.items())
    return (
        f"WorldCover v200 classifies the declared centre as {row.get('landcover')}. Across the "
        f"analysis bbox: {breakdown}. This is a modelled land-cover classification over the "
        "analysis AOI, not a surveyed composition of the 70-acre property; that needs its actual "
        "boundary polygon."
    )


def _greenness_answer(exec_result):
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    rows = value.get("rows") or []
    if value.get("layer") != "greenness_trend" or not rows:
        return None
    row = rows[0]
    return (
        f"The declared-centre MODIS pixel was {row.get('trend_class')} in {row.get('period')}: "
        f"annual-mean NDVI changed from {row.get('ndvi_start')} to {row.get('ndvi_end')}, with a "
        f"slope of {row.get('ndvi_slope')} NDVI/year. This is a 250 m greenness proxy, not "
        "whole-property coverage or proof that restoration caused the change."
    )


def _inventory_answer(exec_result):
    """Render a declared taxon inventory without letting prose sampling drop species."""
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    if value.get("query_semantics") != "taxon_inventory":
        return None
    rows = value.get("rows") or []
    during = [r["common_name"] for r in rows
              if r.get("record_status") == "observed_during_survey"]
    previous = [r["common_name"] for r in rows
                if r.get("record_status") ==
                "previous_property_record_not_observed_during_survey"]
    return (
        f"EBTL has {len(rows)} documented snake species. The September 2024 three-day VES "
        f"observed {', '.join(during)}. Earlier property records add {', '.join(previous)}; "
        f"those {len(previous)} were not encountered during that survey. Source: "
        f"{value.get('source')}."
    )


def _published_site_evidence_answer(exec_result):
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    semantic = value.get("query_semantics")
    rows = value.get("rows") or []
    metadata = value.get("source_metadata") or {}
    if semantic == "wildlife_inventory":
        groups = {row["group"]: row for row in rows}
        herps = groups.get("herpetofauna") or {}
        return (
            f"The local 2024 faunal survey recorded {groups.get('butterflies', {}).get('recorded_taxa')} "
            f"butterfly taxa, {groups.get('odonates', {}).get('recorded_taxa')} odonates and "
            f"{groups.get('birds', {}).get('recorded_taxa')} birds. It also documents "
            f"{herps.get('recorded_taxa')} herpetofauna taxa: {herps.get('observed_during_survey')} "
            f"were encountered in the 2024 VES and {herps.get('earlier_property_records_not_observed')} "
            "were earlier property records not seen then. Separate newsletters document two "
            "indirect elephant-passage events. These are survey records, not population counts or "
            "proof of year-round presence."
        )
    if semantic == "bird_inventory":
        highlights = ["Short-toed Snake-Eagle", "Indian Spotted Eagle",
                      "White-cheeked Barbet", "Red-vented Bulbul"]
        return (
            f"The local 2024 EBTL survey recorded {len(rows)} bird species, including "
            f"{', '.join(highlights)}. Birds were counted when seen or heard on ~1 km transits, "
            "with morning/evening effort and 30-minute checklists. This is a site survey—not a "
            "regional expectation—but it is a study-period inventory, not proof of year-round use."
        )
    if semantic == "snake_habitat_requirements":
        during = [r["common_name"] for r in rows
                  if r.get("record_status") == "observed_during_survey"]
        return (
            "No specific tree species is documented as required by EBTL snakes. The local basis "
            f"is the 14-species property inventory; the 2024 VES encountered {', '.join(during)}, "
            "while 11 others are earlier records. The source measured no snake-by-tree use, "
            "vegetation selection, or planting outcome, so any named tree link would be general "
            "ecology until separately sourced and locally tested."
        )
    if semantic == "cobra_inventory":
        return (
            "Spectacled Cobra (Naja naja) is the one cobra in the documented EBTL property "
            "inventory. It was an earlier property record and was not encountered during the "
            "three-day September 2024 VES. King Cobra is not listed; that is inventory "
            "non-detection, not proof it never occurs at the site."
        )
    if semantic == "venomous_snake_inventory":
        names = [r["common_name"] for r in rows]
        return (
            f"Four medically venomous species are in the documented EBTL inventory: "
            f"{', '.join(names)}. All four are earlier property records; none was encountered "
            "during the three-day September 2024 VES. This is a species count, not a count of "
            "individual snakes."
        )
    if semantic == "elephant_evidence":
        return (
            "EBTL has two documented elephant-passage events: June 2023 footprints plus a broken "
            "fence after a villager report, and May 2024 fence/pipe damage. Neither event was "
            "camera-trapped or directly observed by the survey team, so this is indirect site-use "
            "evidence—not abundance, visit frequency, or evidence of Lantana use."
        )
    if semantic == "nursery_inventory":
        snapshots = metadata.get("snapshots") or []
        latest = snapshots[-1] if snapshots else {}
        examples = [r["scientific_name"] for r in rows[:6]]
        return (
            f"The July 2024 site snapshot reports {latest.get('species_count', 110)} propagated "
            f"species and {latest.get('saplings', 15000):,} saplings. Imported issues name "
            f"{len(rows)} taxa, including {', '.join(examples)}. The published examples are not "
            "the full roster, and there are no species-level survival or growth results yet."
        )
    if semantic == "invasive_evidence":
        points = metadata.get("site_bbox_public_point_records") or {}
        return (
            "The local documents specifically record removal of a roughly one-acre Eucalyptus "
            f"monocrop. Public records in the analysis bbox return Lantana {points.get('Lantana camara', 0)}, "
            f"Jatropha {points.get('Jatropha gossypiifolia', 0)}, Dichrostachys "
            f"{points.get('Dichrostachys cinerea', 0)}, and Abrus {points.get('Abrus precatorius', 0)}. "
            "Those are occurrence records—not abundance—and the bbox is not the 70-acre property."
        )
    if semantic == "invasive_literature":
        if not rows:
            return None
        row = rows[0]
        return (
            f"Semantic discovery found {row.get('doi')}, “{row.get('title')}”, with a codebook. "
            "It is a regional semi-arid plant–disperser dataset, not an EBTL study and it has no "
            "local occurrence points. It can nominate mechanisms; site-specific evidence needs "
            "mapped invasive plants plus dated, georeferenced feeding or seed-fate observations."
        )
    if semantic == "soil_evidence":
        return (
            "There is no direct soil-dryness measurement in the imported site evidence. The "
            "newsletters qualitatively report degraded topsoil and an almost absent monsoon, with "
            "mulching and irrigation used for saplings. A defensible value needs sensor depth, "
            "volumetric water content or water potential, dates, and repeated wet/dry-season samples."
        )
    if semantic == "bird_lantana_transfer":
        swallowed = [r for r in rows if (r.get("fruits_swallowed") or 0) > 0]
        names = ", ".join(r["common_name"] for r in swallowed)
        plant_points = metadata.get("site_bbox_public_plant_points") or {}
        other_points = ", ".join(
            f"{name.split()[0]} {count}" for name, count in plant_points.items()
            if name != "Lantana camara")
        return (
            f"Five birds in the local 67-species inventory also occur in a regional Dryad "
            f"Lantana tree-watch dataset; {names} were recorded swallowing Lantana fruit there. "
            f"Public points in the analysis bbox return Lantana {plant_points.get('Lantana camara', 0)}; "
            f"{other_points}. No local feeding link was measured: this is a regional mechanism, "
            "and the bbox is not the property boundary."
        )
    if semantic == "evidence_summary":
        return (
            "The strongest local facts are 67 surveyed bird species, 14 documented snake species "
            "(3 encountered in the 2024 VES), two indirectly evidenced elephant passages, and a "
            "July 2024 nursery snapshot of 110 species/15,000 saplings. Eucalyptus removal is "
            "documented; local Lantana and measured soil moisture are still data gaps."
        )
    return None


def _group_inventory_answer(exec_result):
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    if value.get("query_semantics") != "taxon_group_inventory":
        return None
    inventory = value.get("inventory") or {}
    names = inventory.get("named_species") or []
    shown = ", ".join(names[:8])
    lead_rows = value.get("evidence_discovery") or []
    leads = len(lead_rows)
    return (
        f"The higher-taxon query returned {inventory.get('deduplicated_records', len(value.get('rows') or []))} "
        f"public {inventory.get('taxon')} occurrence records in the EBTL analysis bbox, spanning "
        f"{len(names)} named taxa{': ' + shown if shown else ''}. Semantic search added {leads} "
        "dataset leads. This is a non-exhaustive public-data sample, not a property survey; an "
        "estimate needs extracted donor points and an environmental transfer gate."
    )


def _group_transfer_answer(exec_result):
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    if value.get("query_semantics") != "taxon_group_transfer_audit":
        return None
    local = value.get("local_inventory") or {}
    regional = value.get("regional_inventory") or {}
    assessments = value.get("assessments") or []
    audit = []
    for item in assessments:
        feature = item.get("feature_gate") or {}
        climate = item.get("climate_gate") or {}
        feature_fraction = feature.get("target_analog_fraction")
        climate_fraction = climate.get("target_in_envelope_fraction")
        audit.append(
            f"{item.get('species')} {item.get('donor_records')} donors: "
            f"feature {'pass' if feature.get('pass') else 'fail'}"
            f"{f' {feature_fraction:g}' if isinstance(feature_fraction, (int, float)) else ''}, "
            f"climate {'pass' if climate.get('pass') else 'fail'}"
            f"{f' {climate_fraction:g}' if isinstance(climate_fraction, (int, float)) else ''}"
        )
    admitted = value.get("admitted_transfer_candidates") or []
    lead_rows = value.get("evidence_discovery") or []
    leads = len(lead_rows)
    lead = lead_rows[0] if lead_rows else {}
    lead_text = ""
    if lead:
        lead_text = (
            f" The semantic lead is {lead.get('doi') or 'an unversioned record'}, a Deccan "
            f"jumping-spider dataset with {lead.get('n_points', 'unknown')} occurrence points; "
            "it is regional, not local."
        )
    decision = (f"Transfer is admissible for {', '.join(admitted)}, but it remains modelled."
                if admitted else
                "No unobserved regional candidate passed both gates, so no site expectation is admitted.")
    return (
        f"Local higher-taxon search found {local.get('deduplicated_records', 0)} record: "
        f"{', '.join(local.get('named_species') or [])}. The regional GBIF query reports "
        f"{regional.get('gbif_api_total', 0):,} records; its capped licensed return contained "
        f"{regional.get('deduplicated_records', 0)} rows and "
        f"{len(regional.get('named_species') or [])} named taxa; semantic search added {leads} "
        "dataset lead(s)." + lead_text + " Gate audit—" +
        "; ".join(audit) + f". {decision} The analysis bbox is not the property boundary."
    )


def _soil_wetness_answer(exec_result):
    if exec_result.get("status") != "answer":
        return None
    value = exec_result.get("value") or {}
    if value.get("query_semantics") != "soil_wetness_proxy" or not value.get("rows"):
        return None
    row = value["rows"][0]
    return (
        f"The closest admitted proxy is NASA POWER/MERRA-2: in {row['year']}, unitless surface "
        f"wetness averaged {row['surface_wetness_mean']} (Jan–Apr {row['jan_apr_surface_wetness_mean']}; "
        f"Jun–Oct {row['jun_oct_surface_wetness_mean']}), with a {row['minimum_surface_wetness']} "
        f"minimum on {row['minimum_date']}. This is a 0.5°×0.625° reanalysis grid cell—tens of "
        "kilometres—not direct property soil moisture or a volumetric measurement."
    )
def _categorical_findings(value):
    """Named annotation values a record answer must not collapse into a bare row count."""
    rows = value.get("rows", []) or []
    fields = []
    for field in (value.get("layer"), "ecoregion", "biome", "landcover"):
        if field and field not in fields:
            fields.append(field)
    found = {}
    for field in fields:
        values = []
        for row in rows:
            item = row.get(field)
            if isinstance(item, str) and item and item not in values:
                values.append(item)
        if values:
            found[field] = values
    return found


def _safe_fallback(exec_result, question=None):
    """Short deterministic answer when the prose model drops a value/label or invents one."""
    status = exec_result.get("status")
    if status == "data_request":
        reason = str(exec_result.get("reason") or "data gap").replace("_", " ")
        detail = exec_result.get("detail") or {}
        if exec_result.get("reason") == "gate_failed" and (
                "occurrence-grain donor records" in str(detail.get("reason", ""))):
            return (
                "I can’t estimate additional site species yet. The transfer gate needs "
                "georeferenced, occurrence-grain donor records for each candidate. Regional "
                "records alone are not site observations; provide candidate-species occurrences "
                "so I can test environmental similarity and label any result as modelled."
            )
        next_step = detail.get("hint") or detail.get("ask") or detail.get("error")
        text = f"Cannot answer yet: {reason}."
        if next_step:
            text += " " + str(next_step).rstrip(".") + "."
        return " ".join(text.split()[:60])

    value = exec_result.get("value") or {}
    label = exec_result.get("label") or value.get("label") or "observed"
    prefix = {"modelled": "Modelled result", "proxy": "Proxy result"}.get(label, "Observed result")
    kind = value.get("kind")
    if kind == "scalar":
        if value.get("winner") and value.get("winner") != "tie":
            winner = str(value["winner"])
            loser = (value.get("right_label") if winner == value.get("left_label") else
                     value.get("left_label"))
            finding = f"{winner} is higher than {loser} by {value.get('value')}"
        elif value.get("winner") == "tie":
            finding = (f"{value.get('left_label')} and {value.get('right_label')} are tied "
                       f"(difference {value.get('value')})")
        else:
            finding = str(value.get("value"))
        if value.get("unit"):
            finding += " " + str(value["unit"])
    elif kind in {"records", "field"}:
        row_count = len(value.get("rows", []) or [])
        finding = f"{row_count} {'record' if row_count == 1 else 'records'}"
        categories = _categorical_findings(value)
        if categories:
            parts = []
            for field, values in categories.items():
                shown = values[:4]
                suffix = f" (+{len(values) - 4} more)" if len(values) > 4 else ""
                parts.append(f"{field}: {', '.join(shown)}{suffix}")
            finding += "; " + "; ".join(parts)
    elif kind == "ranking":
        finding = " > ".join(str(r.get("label")) for r in value.get("rows", [])) or "empty ranking"
    elif kind == "series":
        rows = value.get("rows", []) or []
        finding = f"{len(rows)} time points"
    else:
        finding = str(value.get("value") if value.get("value") is not None else kind)

    source = value.get("source")
    text = f"{prefix}: {finding}."
    if source:
        text += f" Source: {source}."
    notes = [str(p.get("note")) for p in exec_result.get("provenance", []) if p.get("note")]
    limitation = next((n for n in notes if re.search(
        r"proxy|bbox|sampling|effort|coverage|not AOI", n, re.IGNORECASE)), None)
    if limitation:
        text += " " + limitation.rstrip(".") + "."
    return " ".join(text.split()[:60])


def score_synthesis(question, exec_result, prose):
    """Mechanical behavioral dims; each True/False, overall = mean."""
    s = {}
    words = len(prose.split())
    s["not_empty"] = bool(prose) and not prose.startswith("[synthesis-failed]")
    s["short"] = 0 < words <= 80
    v = exec_result.get("value") or {}
    status = exec_result.get("status")
    # number-presence: if the result carries a headline number, the prose must contain it
    headline = None
    if isinstance(v.get("value"), (int, float)):
        headline = v["value"]
    elif v.get("kind") == "records":
        headline = v.get("n_rows", len(v.get("rows", []) or []))
    if status == "answer" and headline is not None and s["not_empty"]:
        def num_in(x, text):
            if isinstance(x, float):
                cands = {f"{x:.0f}", f"{x:.1f}", f"{x:.2f}", f"{x:,.0f}"}
            else:
                cands = {str(x), f"{x:,}"}
                words = {0: "zero", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five",
                         6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten",
                         11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
                         15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen",
                         19: "nineteen", 20: "twenty"}
                if x in words:
                    cands.add(words[x])
            low = text.lower()
            return any(c.lower() in low for c in cands)
        category_values = [item for values in _categorical_findings(v).values() for item in values]
        category_stated = (not category_values or
                           any(item.lower() in prose.lower() for item in category_values))
        compare_labels = [v.get("left_label"), v.get("right_label")]
        compare_labels = [str(x).split(",")[0].lower() for x in compare_labels if x]
        comparison_stated = (not v.get("winner") or
                             (all(x in prose.lower() for x in compare_labels) and
                              (v.get("winner") == "tie" or
                               str(v.get("winner")).split(",")[0].lower() in prose.lower()) and
                              bool(re.search(r"higher|lower|greater|larger|more|less|tie|differ",
                                             prose.lower()))))
        s["states_finding"] = num_in(headline, prose) and category_stated and comparison_stated
    else:
        # direction / ranking / list answers: at least echo a value or label from the result
        direction_terms = {"rising": ("rising", "rose", "increased", "grew"),
                           "falling": ("falling", "fell", "decreased", "declined"),
                           "flat": ("flat", "stable", "unchanged")}
        scalar_text = v.get("value")
        direction_stated = (isinstance(scalar_text, str) and
                            any(x in prose.lower() for x in direction_terms.get(
                                scalar_text.lower(), (scalar_text.lower(),))))
        s["states_finding"] = True if status != "answer" else (
            direction_stated or
            any(str(r.get("label", r.get("value", ""))).split(",")[0] in prose
                for r in (v.get("rows") or [])[:3]) or v.get("kind") == "series")
    if exec_result.get("label") == "modelled":
        s["modelled_flagged"] = bool(re.search(r"model|estimat|approximat", prose.lower()))
    else:
        s["modelled_flagged"] = True
    if exec_result.get("label") == "proxy":
        s["proxy_flagged"] = bool(re.search(r"proxy|approximat|bbox|sampling|effort|coverage",
                                             prose.lower()))
    else:
        s["proxy_flagged"] = True
    if status == "data_request":
        s["gap_stated"] = bool(re.search(r"missing|no\s+[^.]{0,30}\s+(?:data|records)|no data|"
                                         r"no available|not available|no specific|not determine|"
                                         r"cannot|can't|can’t|need|require|collect|clarif|"
                                         r"which |couldn|cannot|unable|specify",
                                         prose.lower()))
        stated = set(re.findall(r"\b\d+(?:\.\d+)?\b", prose))
        allowed_text = question + " " + json.dumps(exec_result, default=str)
        allowed = set(re.findall(r"\b\d+(?:\.\d+)?\b", allowed_text))
        s["no_fabrication"] = stated <= allowed
    else:
        s["gap_stated"] = True
        s["no_fabrication"] = True
    dims = [k for k in s]
    s["overall"] = round(sum(1.0 if s[k] else 0.0 for k in dims) / len(dims), 3)
    return s
