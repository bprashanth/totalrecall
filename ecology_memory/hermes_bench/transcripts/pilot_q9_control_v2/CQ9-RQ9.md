# EBTL Kavya drill-down — CQ9-RQ9

compiler=qwen9b responder=qwen9b round=pilot_q9_control_v2

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

schema_valid=True status=answer label=observed compile_execute_s=0.001

### Answer

The strongest confirmed facts for Elephants by the Lake (EBTL) come from direct observations in 2024: a local survey recorded 67 bird species, and a three-day Vertebrate Encounter Survey documented 3 of the 14 known snake species. Additionally, there are two recorded elephant passage events supported by indirect physical signs, though no direct elephant sightings were made.

Significant gaps exist regarding invasive species and elephant activity. While roughly one acre of Eucalyptus removal is documented, there is no local confirmation of Lantana presence. Furthermore, the indirect signs for elephants do not constitute a direct observation, and the data relies heavily on a single July 2024 snapshot for the nursery area, leaving current population trends and specific invasive threats unverified.

To address these gaps, the NGO should conduct a targeted search for Lantana across the site and increase direct elephant monitoring efforts to verify the passage events indicated by physical signs. A follow-up survey in the nursery area beyond the July 2024 snapshot would also help clarify the status of the 110 species and 15,000 saplings reported.

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

schema_valid=True status=answer label=observed compile_execute_s=3.589

### Answer

The 2024 wildlife baseline consists of direct observations for butterflies (54 taxa), odonates (42 taxa), and birds (67 taxa), all recorded during September 5–7, 2024. For herpetofauna, the survey documented 20 taxa directly observed between September 5–7, 2024, while an additional 13 taxa (including 11 snake species and 2 lizard species) are earlier property records not seen during this specific survey period.

Regarding elephants, there are no direct sightings in the 2024 data; instead, the record includes two indirect passage events supported by physical signs. The "recorded" counts for the other groups represent species confirmed during the specific survey windows listed above, not year-round presence or abundance.

To clarify the full baseline, a data request is needed to verify if the 13 herpetofauna taxa from earlier records are still present on-site and to conduct targeted searches for elephants to confirm or refute the indirect passage signs.

audit_passed=True fallback=False render_s=0.001

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

So we all agree the survey was just a three-day snapshot in September—what about the missing monsoon or winter migrants, and how does a single-season list capture true species richness?

### Algebra

```json
{
  "op": "COMPARE",
  "how": "difference",
  "left": {
    "op": "AGGREGATE",
    "by": "time",
    "metric": "count",
    "source": {
      "op": "SELECT",
      "entity": "bird",
      "region": {
        "op": "REGION",
        "place": "Elephants by the Lake"
      },
      "time": {
        "start": "2024",
        "end": "2024"
      }
    }
  },
  "right": {
    "op": "AGGREGATE",
    "by": "time",
    "metric": "count",
    "source": {
      "op": "SELECT",
      "entity": "bird",
      "region": {
        "op": "REGION",
        "place": "Elephants by the Lake"
      },
      "time": null
    }
  }
}
```

schema_valid=True status=data_request label=None compile_execute_s=2.451

### Answer

The current data does not support claims about monsoon or winter migrants because the only available bird records come from a single three-day survey. The eBird source for these records is technically limited to observations from the preceding 1 to 30 days, meaning it cannot provide a year-round baseline or capture seasonal movements outside that specific window.

Consequently, a single-season list cannot accurately reflect true species richness for the site, as it misses potential arrivals during other seasons. To address this gap, a concrete data request is needed to conduct targeted bird surveys during the monsoon and winter periods to verify if additional migratory species are present beyond the taxa recorded in the September survey.

audit_passed=True fallback=False render_s=8.326

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

schema_valid=True status=answer label=observed compile_execute_s=1.712

### Answer

The only wildlife groups with confirmed local ground documentation are birds (67 species), snakes (3 encountered), and elephants (two passage events supported by indirect physical signs), all recorded during specific 2024 surveys. In contrast, the 110 species and 15,000 saplings in the nursery area, along with the 23 taxa listed in imported issues, are reported from a July 2024 snapshot and do not represent direct local observation.

Regarding invasives, there is no local confirmation of Lantana presence, though roughly one acre of Eucalyptus removal is documented. The data explicitly distinguishes between these local observations and external sources, noting that satellite layers and regional literature are separate proxy or modelled evidence and are not promoted to local observations.

To clarify the baseline, a data request is needed to conduct targeted searches for Lantana across the site and to verify if the 23 taxa from imported issues are actually present on the ground. Additionally, a follow-up survey beyond the July 2024 snapshot is required to confirm the status of the nursery species and saplings.

audit_passed=True fallback=False render_s=7.333

