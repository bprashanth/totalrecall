# EBTL Kavya drill-down — C2-RQ9

compiler=qwen2b responder=qwen9b round=pilot_q9_control_v2

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

The strongest confirmed facts for Elephants by the Lake (EBTL) come from direct observations in 2024: a local survey recorded 67 bird species, and a three-day Vertebrate Encounter Survey documented 3 of the 14 known snake species. Additionally, there are two recorded elephant passage events supported by indirect physical signs, though no direct elephant sightings were made.

Significant gaps exist regarding invasive species and elephant activity. While roughly one acre of Eucalyptus removal is documented, there is no local confirmation of Lantana presence. Furthermore, the indirect signs for elephants do not constitute a direct observation, and the data relies heavily on a single July 2024 snapshot for the nursery area, leaving current population trends and specific invasive threats unverified.

To address these gaps, the NGO should conduct a targeted search for Lantana across the site and increase direct elephant monitoring efforts to verify the passage events indicated by physical signs. A follow-up survey in the nursery area beyond the July 2024 snapshot would also help clarify the status of the 110 species and 15,000 saplings reported.

audit_passed=True fallback=False render_s=3.106

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

schema_valid=True status=answer label=observed compile_execute_s=4.96

### Answer

The 2024 wildlife baseline consists of direct observations for butterflies (54 taxa), odonates (42 taxa), and birds (67 taxa), all recorded during September 5–7, 2024. For herpetofauna, the survey documented 20 taxa directly observed between September 5–7, 2024, while an additional 13 taxa (including 11 snake species and 2 lizard species) are earlier property records not seen during this specific survey period.

Regarding elephants, there are no direct sightings in the 2024 data; instead, the record includes two indirect passage events supported by physical signs. The "recorded" counts for the other groups represent species confirmed during the specific survey windows listed above, not year-round presence or abundance.

To clarify the full baseline, a data request is needed to verify if the 13 herpetofauna taxa from earlier records are still present on-site and to conduct targeted searches for elephants to confirm or refute the indirect passage signs.

audit_passed=True fallback=False render_s=2.627

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

So we all agree the survey was just a three-day snapshot in September—what about the missing monsoon or winter migrants, and how does a single-season list capture true species richness?

### Algebra

```json
{
  "op": "AGGREGATE",
  "by": "space",
  "metric": "count",
  "source": {
    "op": "RELATE",
    "relation": "within",
    "left": {
      "op": "SELECT",
      "entity": "pharmacy",
      "region": {
        "op": "REGION",
        "place": "Elephants by the Lake"
      },
      "time": null
    },
    "right": {
      "op": "SELECT",
      "entity": "hospital",
      "region": {
        "op": "REGION",
        "place": "Elephants by the Lake"
      },
      "time": null
    }
  }
}
```

schema_valid=True status=data_request label=None compile_execute_s=19.507

### Answer

The current audited result contains no data regarding monsoon or winter migrants, nor does it provide information on how a single-season list captures true species richness. The available evidence is limited to a three-day survey, which recorded specific taxa for butterflies, odonates, birds, and herpetofauna, but offers no insight into seasonal variations or broader species richness.

Because the result explicitly flags a "no_connector" status for the entity "pharmacy" and provides no data source mapping to this term, the specific details about missing seasonal migrants cannot be confirmed from the current record. To address this gap, a data request is needed to measure seasonal species presence during monsoon and winter periods, specifying the exact months, locations within the site, and the survey effort required to capture potential migrants.

audit_passed=True fallback=False render_s=6.51

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

schema_valid=True status=data_request label=None compile_execute_s=2.542

### Answer

The current audited result confirms that data on seasonal migrants is missing, just as it is for invasive species. Specifically, the record contains an unbound hole for `?invasive_type`, meaning there is no local documentation to distinguish between invasive species confirmed on the ground versus those assumed from regional or public-bbox records.

Because the evidence explicitly flags this as a `data_request` with no provenance, we cannot separate local observations from external assumptions for either invasive threats or seasonal migrants. To resolve this, a concrete data request is needed to clarify the specific type of invasive species present and to conduct targeted searches to verify their local status rather than relying on regional data.

audit_passed=True fallback=False render_s=3.689

