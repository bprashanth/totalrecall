# EBTL Kavya drill-down — C2-RQ9

compiler=qwen2b responder=qwen9b round=pilot_q9_repair

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

schema_valid=True status=answer label=observed compile_execute_s=3.666

### Answer

The strongest confirmed facts for Elephants by the Lake (EBTL) are direct observations of 67 bird species and 14 snake species recorded in a local 2024 survey, alongside a July 2024 snapshot of a 110-species nursery containing 15,000 saplings. Management actions are partially verified by roughly one acre of documented Eucalyptus removal, though there is no local confirmation of Lantana presence.

Important gaps exist regarding elephant activity, where only two passage events are known from indirect physical signs rather than direct sightings, and invasive species monitoring is incomplete due to the lack of local Lantana confirmation. To address these uncertainties, the team should conduct targeted ground surveys to verify elephant presence and specifically search for Lantana within the nursery and surrounding areas.

audit_passed=True fallback=False render_s=4.54

## Turn 2 — WILDLIFE BASELINE — what groups were actually surveyed, when, and what “recorded” means.

### Kavya

Okay, so the common thread is those 2024 surveys and the indirect signs, but we need to pin down the actual wildlife baseline—which groups were directly surveyed, during what period, and what exactly counts as 'recorded'?

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

schema_valid=True status=answer label=observed compile_execute_s=4.812

### Answer

The 2024 field surveys directly recorded 54 butterfly taxa, 42 odonate taxa (31 dragonflies and 11 damselflies), 67 bird taxa, and 20 herpetofauna taxa (7 frogs, 9 lizards, 3 snakes, and 1 turtle) during specific windows in September and October 2024. Butterflies were surveyed via four 30-minute transects daily over three days, while birds were recorded on approximately 1 km transits with morning/evening effort. Odonates used one-hour time-constrained VES on three transects over four days, and herpetofauna were surveyed over three days using two-hour sessions across morning, evening, and night periods.

A critical gap exists in the herpetofauna baseline: the total of 33 recorded taxa includes 13 species from earlier property records that were not actually observed during the 2024 VES sessions. Additionally, the current data represents only short-term snapshots in late 2024 and does not prove year-round presence, abundance, or complete detectability for any group. To address this, a concrete data request is needed to measure herpetofauna presence across all seasons with a standardized effort of at least 10 hours of time-constrained VES per month over a full year to distinguish transient visitors from resident populations.

audit_passed=True fallback=False render_s=4.458

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

So we all agree the survey was just a three-day snapshot in September—what about the missing monsoon or winter migrants, and how does a single-season list capture true species richness?

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

schema_valid=True status=data_request label=None compile_execute_s=7.814

### Answer

The current evidence confirms that the wildlife baseline relies on a single three-day snapshot in September 2024, meaning there is no direct data on monsoon or winter migrants, and the list cannot be assumed to represent year-round species richness or abundance. Because the existing records are survey summaries rather than individual georeferenced occurrence points, we cannot statistically model seasonal gaps or transfer regional patterns to this specific site.

To address this, we need to request georeferenced species occurrence records for the site. Specifically, we must measure individual species detections with precise coordinates across different seasons (monsoon and winter) to determine if the September snapshot captures the full local fauna or if significant migratory groups are missing.

audit_passed=True fallback=False render_s=2.382

## Turn 4 — INVASIVES — what is locally documented versus public-bbox or regional evidence.

### Kavya

So all of you are saying the data isn't there for seasonal migrants either — same problem we're facing with invasives. Can we at least pin down what's been locally documented on the ground versus what's being assumed from regional or public-bbox records, or is that also unclear?

### Algebra

```json
{
  "op": "SELECT",
  "entity": "?invasive_type",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=2.342

### Answer

The current evidence does not distinguish between species directly observed on the ground and those assumed from regional or public records; the data pack explicitly flags a gap regarding the specific type of invasive species involved. While previous records noted roughly one acre of Eucalyptus removal, there is no local confirmation for Lantana, and the system cannot currently separate local detections from broader regional assumptions without further clarification.

To resolve this uncertainty, a concrete data request is needed: you must clarify the specific invasive species types present at the site and provide evidence of their local documentation versus regional extrapolation. Until these specific invasive types are defined and verified against local ground observations, any distinction between documented and assumed presence remains unclear.

audit_passed=True fallback=False render_s=7.245

