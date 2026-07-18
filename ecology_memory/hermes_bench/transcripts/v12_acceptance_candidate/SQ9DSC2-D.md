# EBTL Kavya drill-down — SQ9DSC2-D

compiler=qwen9b>deepseekv4@qwen2b responder=deterministic round=v12_acceptance_candidate

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

schema_valid=True status=answer label=observed compile_execute_s=18.059

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

schema_valid=True status=answer label=observed compile_execute_s=26.138

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

schema_valid=True status=answer label=observed compile_execute_s=25.896

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

schema_valid=True status=error label=None compile_execute_s=130.669

### Answer

I cannot answer this from the available evidence yet (executor_crash). DATA REQUEST: UnboundLocalError: cannot access local variable 'route' where it is not associated with a value

audit_passed=True fallback=False render_s=0.0

