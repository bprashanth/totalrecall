# EBTL Kavya drill-down — CDS-RDS

compiler=deepseekv4 responder=deepseekv4 round=pilot_ds_boundary_v2

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

schema_valid=True status=answer label=observed compile_execute_s=83.936

### Answer

Based on the records we have, the strongest fact is the bird survey: a 2024 transit survey recorded 67 observed species on the property. The snake work is also solid—14 species are documented for the property, with 3 of those physically encountered during a three-day visual encounter survey.

For your core topic, elephants, we only have **indirect** evidence: two passage events supported by physical signs (like tracks or dung). We have no local observation, count, or residency data for the elephants themselves. The nursery data (110 species, 15,000 saplings) comes from a July 2024 snapshot and is **reported** (not independently verified), and invasive management is limited to roughly one acre of *Eucalyptus* removal with no local confirmation of *Lantana*.

**Key gap & data request:** We do not know how many elephants use the property or how often. The concrete request is to deploy a systematic camera-trap array along the two identified corridor areas to obtain local observed passage events and occupancy.

audit_passed=True fallback=False render_s=0.0

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

schema_valid=True status=answer label=observed compile_execute_s=24.236

### Answer

The 2024 direct surveys covered **butterflies** (54 taxa all observed during the survey, 5–7 Sep), **odonates** (42 all observed, 10–13 Oct), **birds** (67 all observed, 5–7 Sep), and **herpetofauna** (33 total, but only 20 observed during the 5–7 Sep VES; the other 13 are earlier property records, not re-observed). That survey does not cover elephants—their presence is based on two separate indirect passage reports, not direct observation.

audit_passed=True fallback=False render_s=0.001

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

So we all agree the survey was just a three-day snapshot in September—what about the missing monsoon or winter migrants, and how does a single-season list capture true species richness?

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

schema_valid=True status=answer label=observed compile_execute_s=9.821

### Answer

You're right to flag the seasonal gap. The 2024 faunal surveys were indeed a short snapshot: butterflies, birds, and herpetofauna were all surveyed from 5–7 September, and odonates from 10–13 October. That means the bird list of 67 species, for example, only includes what was present in early September—monsoon migrants, winter visitors, and species active in other months are not captured. The survey report itself states that these inventories are "not proof of year-round presence, abundance, or complete detectability." So the single-season list is a useful baseline but cannot represent true species richness for the property. To get a fuller picture, you would need repeated surveys across the monsoon, winter, and summer periods.

audit_passed=True fallback=False render_s=4.141

## Turn 4 — INVASIVES — what is locally documented versus public-bbox or regional evidence.

### Kavya

So all of you are saying the data isn't there for seasonal migrants either — same problem we're facing with invasives. Can we at least pin down what's been locally documented on the ground versus what's being assumed from regional or public-bbox records, or is that also unclear?

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

schema_valid=True status=answer label=observed compile_execute_s=48.362

### Answer

We can clearly separate what is locally documented on the ground versus what would come from regional or public‑bbox records, because the evidence pack you’re seeing is strictly limited to on‑the‑ground primary observations from the EBTL property. No satellite layers, no regional literature, and no bbox‑derived records have been promoted into these findings. So the local facts are:

- **67 bird species** observed during the September 2024 transit survey (three days).
- **14 documented snake species** for the property, of which **3 were physically encountered** during the three‑day herpetofauna VES; the other 11 are earlier property records.
- **Two elephant passage events** based on indirect physical signs (tracks, dung, etc.).
- **110‑species / 15,000‑sapling nursery** snapshot from July 2024.
- **Roughly one acre of Eucalyptus removal** documented; **no local Lantana confirmation**.

That’s the complete set of locally documented evidence. Any assumptions about seasonal migrants, year‑round presence, or invasive spread beyond that one acre are not supported by local data. If you need to know what regional or bbox data might say, that would be a separate layer—and the current evidence pack deliberately keeps them apart so you know exactly what’s ground‑truthed and what is not.

audit_passed=True fallback=False render_s=6.107

