# EBTL Kavya drill-down — SQ9C2-D

compiler=qwen9b@qwen2b responder=deterministic round=selector_regression_v4

## Turn 1 — OPEN — map EBTL for a new conservation colleague: strongest local facts and major unknowns.

### Kavya

I work with a conservation NGO around Elephants by the Lake. Map EBTL for a new field colleague: what are the strongest facts we actually have, and what are the important gaps?

### Algebra

```json
{
  "op": "SELECT",
  "entity": "EBTL evidence summary",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=answer label=observed compile_execute_s=0.002

### Answer

Mixed-evidence result: 5 evidence records: [observed] 67 species in a local 2024 transit survey, [observed] 14 documented property species; 3 encountered in the three-day 2024 VES, [indirect] two passage events supported by indirect physical signs, [reported] 110-species/15,000-sapling July 2024 snapshot; 23 taxa named in imported issues, [reported] roughly one acre of Eucalyptus removal documented; no local Lantana confirmation. Source: Imported EBTL primary evidence. local evidence summary; satellite layers and regional literature are separate proxy/modelled evidence and are not promoted to local observations.

audit_passed=True fallback=False render_s=0.0

## Turn 2 — WILDLIFE BASELINE — what groups were actually surveyed, when, and what “recorded” means.

### Kavya

That is useful, but what was actually surveyed on the property in 2024? Give me the wildlife groups, dates and effort, and separate animals seen in that survey from older or indirect records.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "EBTL wildlife inventory",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": {
    "start": "2024",
    "end": "2024"
  }
}
```

schema_valid=True status=answer label=observed compile_execute_s=0.001

### Answer

Observed result: 4 evidence records. Source: Imported EBTL primary evidence. published local survey summaries for butterflies, odonates, birds and herpetofauna; the herpetofauna total separates 2024 VES detections from earlier property records; elephant evidence comes from two separate indirect passage reports.

audit_passed=True fallback=False render_s=0.0

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

For the bird list specifically, can it tell us year-round richness or monsoon and winter migrants, or is it only a seasonal snapshot? Tell me exactly what repeated survey would close that gap.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "EBTL bird inventory",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=answer label=observed compile_execute_s=4.27

### Answer

Observed result: 67 evidence records: Lesser Whistling-Duck, Indian Peafowl, Gray Junglefowl, Gray Francolin, Spotted Dove, Laughing Dove, Greater Coucal, Pied Cuckoo. Source: Imported EBTL primary evidence. complete published site inventory of 67 bird species; seen-or-heard transit survey with morning/evening effort and 30-minute eBird checklists.

audit_passed=True fallback=False render_s=0.001

## Turn 4 — INVASIVES — what is locally documented versus public-bbox or regional evidence.

### Kavya

Now invasives: what is documented locally at EBTL, and what comes only from regional literature, satellite proxies or public records? Please keep those evidence levels separate.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "EBTL invasive evidence",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=answer label=observed compile_execute_s=22.497

### Answer

Observed result: 1 evidence records. Source: Imported EBTL primary evidence. site documentation names a roughly one-acre Eucalyptus monocrop removal; public occurrence points add candidate taxa inside the analysis bbox, which is not the 70-acre property boundary; Lantana returns zero points.

audit_passed=True fallback=False render_s=0.0

## Turn 5 — SCARCE-1: INVASIVE REBOUND — whether Lantana or other invasives are returning after removal; expect unknown + concrete repeated-map DATA REQUEST.

### Kavya

What can the available data honestly say about fire at EBTL—observed fire history versus present or future risk? Give the measured scale and the missing fuel or weather data.

### Algebra

```json
{
  "op": "ANNOTATE",
  "layer": "historical fire exposure",
  "source": {
    "op": "SELECT",
    "entity": "EBTL restoration site",
    "region": {
      "op": "REGION",
      "place": "Elephants by the Lake"
    },
    "time": null
  }
}
```

schema_valid=True status=answer label=proxy compile_execute_s=19.719

### Answer

Proxy result: 1 evidence records. Source: SITE_EBTL.json + origin fire.py → MODIS/061/MOD14A1 via Earth Engine. 0 historical 2020-2025 MODIS active-fire locations inside the exact AOI; point exposure also measured within 5 km; pixel-fire-days are a pressure proxy, not fire probability or burned area.

audit_passed=True fallback=False render_s=0.001

## Turn 6 — FIRE — observed fire history versus present/future risk; fuels/weather/field gaps.

### Kavya

We also work with neighbouring communities. What evidence do we have on grazing, fuelwood collection, restoration jobs, crop loss or coexistence around EBTL? If none, propose an ethical household and resource-use data request without inventing percentages.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "?proxy",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=1.69

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?proxy

audit_passed=True fallback=False render_s=0.001

