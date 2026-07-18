# EBTL Kavya drill-down — SQ9C2-RQ9

compiler=qwen9b@qwen2b responder=qwen9b round=selector_regression_v3

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

schema_valid=True status=answer label=observed compile_execute_s=1.099

### Answer

The strongest confirmed facts for Elephants by the Lake (EBTL) are direct observations of 67 bird species and 14 snake species recorded in a local 2024 survey, alongside a July 2024 snapshot of a 110-species nursery containing 15,000 saplings. Management actions are partially verified by roughly one acre of documented Eucalyptus removal, though there is no local confirmation of Lantana presence.

Important gaps exist regarding elephant activity, where only two passage events are known from indirect physical signs rather than direct sightings, and invasive species monitoring is incomplete due to the lack of local Lantana confirmation. To address these uncertainties, the team should conduct targeted ground surveys to verify elephant presence and specifically search for Lantana within the nursery and surrounding areas.

audit_passed=True fallback=False render_s=0.001

## Turn 2 — WILDLIFE BASELINE — what groups were actually surveyed, when, and what “recorded” means.

### Kavya

That is useful, but what was actually surveyed on the property in 2024? Give me the wildlife groups, dates and effort, and separate animals seen in that survey from older or indirect records.

### Algebra

```json
{
  "op": "ANNOTATE",
  "layer": "survey",
  "source": {
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
}
```

schema_valid=True status=data_request label=None compile_execute_s=2.797

### Answer

We do not have a single, unified survey record for the property in 2024 that lists specific dates, effort, and wildlife groups together. The available evidence consists of separate summaries: a 2024 transit survey recorded 67 bird species, and a three-day 2024 VES (VES likely stands for a specific survey type) encountered 3 snake species out of 14 documented property species. Additionally, two elephant passage events in 2024 are supported only by indirect physical signs, not direct sightings.

To answer your request for a consolidated list of wildlife groups, dates, and effort, we need to measure the specific survey parameters and combine these fragmented records. Please provide the exact dates, duration, and search effort for the 2024 bird transit survey and the three-day VES, along with a clear list of all wildlife groups targeted in those specific 2024 efforts.

audit_passed=True fallback=False render_s=4.194

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

For the bird list specifically, can it tell us year-round richness or monsoon and winter migrants, or is it only a seasonal snapshot? Tell me exactly what repeated survey would close that gap.

### Algebra

```json
{
  "op": "ESTIMATE",
  "method": "feature",
  "target": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "source": {
    "op": "SELECT",
    "entity": "EBTL bird inventory",
    "region": {
      "op": "REGION",
      "place": "Elephants by the Lake"
    },
    "time": null
  }
}
```

schema_valid=True status=data_request label=None compile_execute_s=3.016

### Answer

The current evidence for birds at Elephants by the Lake is limited to a single 2024 transit survey that recorded 67 species using morning and evening effort with 30-minute eBird checklists. This data represents a seasonal snapshot of species seen or heard during that specific window and does not distinguish between year-round residents, monsoon migrants, or winter visitors.

To close this gap and determine seasonal composition, a concrete data request is needed: conduct repeated bird surveys across distinct seasons (monsoon and winter) using the same standardized 30-minute eBird checklists, while explicitly recording the date and time of each detection to separate resident populations from seasonal migrants.

audit_passed=True fallback=False render_s=2.68

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

schema_valid=True status=answer label=observed compile_execute_s=19.668

### Answer

Locally at Elephants by the Lake, the only documented invasive management action is the removal of a roughly one-acre Eucalyptus monocrop at a high catchment area prior to pond construction, as recorded in the June 2023 newsletter. This is the sole piece of direct, observed evidence regarding non-native species on the property.

All other invasive species mentioned—*Lantana camara*, *Jatropha gossypiifolia*, *Dichrostachys cinerea*, and *Abrus precatorius*—are not confirmed on-site. These names appear only in public occurrence databases (GBIF, iNaturalist, papers) within the broader analysis bounding box, which does not match the specific 70-acre property boundary. Specifically, there are zero public records for *Lantana camara* in this area, meaning no local confirmation exists for this species.

audit_passed=True fallback=False render_s=5.766

## Turn 5 — SCARCE-1: INVASIVE REBOUND — whether Lantana or other invasives are returning after removal; expect unknown + concrete repeated-map DATA REQUEST.

### Kavya

What can the available data honestly say about fire at EBTL—observed fire history versus present or future risk? Give the measured scale and the missing fuel or weather data.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "EBTL fire history",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=3.924

### Answer

The available data cannot honestly say anything about fire at EBTL because no recorded evidence exists for fire history, present risk, or future risk at this site. The system explicitly found no data source that maps to "EBTL fire history," meaning there are no measured scales of past fires, no documented fuel loads, and no weather records associated with fire events for this property.

To close this gap, a concrete data request is needed: conduct a field survey to measure local fuel continuity and load (e.g., dry grass height and woody debris density) and record recent weather conditions (temperature, humidity, wind) to establish a baseline for present fire risk.

audit_passed=True fallback=False render_s=9.485

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

schema_valid=True status=data_request label=None compile_execute_s=4.324

### Answer

The available data contains no evidence regarding grazing, fuelwood collection, restoration jobs, crop loss, or coexistence activities around Elephants by the Lake (EBTL). The current record indicates a gap where the system cannot determine if these are local observations or regional proxies, leaving the status of human-wildlife interactions in neighbouring communities completely unknown.

To close this gap, a concrete data request is needed: conduct structured household interviews and field observations within the immediate vicinity of EBTL to document specific instances of livestock grazing, fuelwood gathering, and crop damage, while simultaneously recording any active community-led restoration efforts or documented coexistence protocols.

audit_passed=True fallback=False render_s=12.803

