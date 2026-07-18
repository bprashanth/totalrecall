# EBTL Kavya drill-down — C2-RDS

compiler=qwen2b responder=deepseekv4 round=pilot_ds_boundary_v2

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

Based on the records we have, the strongest fact is the bird survey: a 2024 transit survey recorded 67 observed species on the property. The snake work is also solid—14 species are documented for the property, with 3 of those physically encountered during a three-day visual encounter survey.

For your core topic, elephants, we only have **indirect** evidence: two passage events supported by physical signs (like tracks or dung). We have no local observation, count, or residency data for the elephants themselves. The nursery data (110 species, 15,000 saplings) comes from a July 2024 snapshot and is **reported** (not independently verified), and invasive management is limited to roughly one acre of *Eucalyptus* removal with no local confirmation of *Lantana*.

**Key gap & data request:** We do not know how many elephants use the property or how often. The concrete request is to deploy a systematic camera-trap array along the two identified corridor areas to obtain local observed passage events and occupancy.

audit_passed=True fallback=False render_s=0.001

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

schema_valid=True status=answer label=observed compile_execute_s=0.001

### Answer

The 2024 direct surveys covered **butterflies** (54 taxa all observed during the survey, 5–7 Sep), **odonates** (42 all observed, 10–13 Oct), **birds** (67 all observed, 5–7 Sep), and **herpetofauna** (33 total, but only 20 observed during the 5–7 Sep VES; the other 13 are earlier property records, not re-observed). That survey does not cover elephants—their presence is based on two separate indirect passage reports, not direct observation.

audit_passed=True fallback=False render_s=14.702

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

schema_valid=True status=data_request label=None compile_execute_s=0.001

### Answer

You're right to flag the seasonal gap. The 2024 surveys were a three-day snapshot in September (butterflies, birds, herpetofauna) and a four-day session in October (odonates). That single-season window cannot capture monsoon migrants, winter visitors, or species that are active only in other months. The current evidence is a list of what was seen during those specific days, not a complete inventory of the property's year-round fauna. There is no data on seasonal turnover, breeding residents, or passage migrants.

To assess true species richness, we would need georeferenced occurrence records collected across multiple seasons—ideally covering pre-monsoon, monsoon, post-monsoon, and winter periods with repeated visits. Without such records, any estimate of total richness or seasonal composition would be a guess. The concrete data request is: **conduct multi-season field surveys (e.g., quarterly or monthly) that produce georeferenced species occurrence records for all target groups, with consistent effort and method, so that seasonal patterns and completeness can be evaluated.**

audit_passed=True fallback=False render_s=10.296

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

schema_valid=True status=data_request label=None compile_execute_s=0.001

### Answer

Yes, we can distinguish what’s locally documented from what’s assumed. The 2024 faunal survey provides direct, on-the-ground observations for four groups: butterflies (54 species), odonates (42), birds (67), and herpetofauna (20 species seen during the survey, plus 13 earlier property records). Elephant presence is supported by two indirect physical signs. All of these are local evidence, not regional or public‑bbox assumptions.

For invasives, the only local documentation is a reported removal of roughly one acre of Eucalyptus; there is no local confirmation of Lantana. Seasonal migrants were not assessed because the system lacked the georeferenced occurrence records needed to transfer presence from regional data. So the picture is clear for the surveyed groups, but for invasives and seasonal migrants we have only reported or unknown status. The system is currently asking for clarification on which invasive type you want to focus on, which would help narrow that gap.

audit_passed=True fallback=False render_s=15.283

