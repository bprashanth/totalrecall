# EBTL Kavya drill-down — C2-D

compiler=qwen2b responder=deterministic round=v1_frozen

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

audit_passed=True fallback=False render_s=0.001

## Turn 2 — WILDLIFE BASELINE — what groups were actually surveyed, when, and what “recorded” means.

### Kavya

That is useful, but what was actually surveyed on the property in 2024? Give me the wildlife groups, dates and effort, and separate animals seen in that survey from older or indirect records.

### Algebra

```json
{
  "op": "AGGREGATE",
  "by": "time",
  "metric": "count",
  "source": {
    "op": "SELECT",
    "entity": "ebtl wildlife inventory",
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

schema_valid=True status=answer label=observed compile_execute_s=7.357

### Answer

Observed result: 0 time points. Source: Imported EBTL primary evidence. binned to 0 years.

audit_passed=True fallback=False render_s=0.0

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

For the bird list specifically, can it tell us year-round richness or monsoon and winter migrants, or is it only a seasonal snapshot? Tell me exactly what repeated survey would close that gap.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "?bird_type",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=2.672

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?bird_type

audit_passed=True fallback=False render_s=0.0

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

schema_valid=True status=answer label=observed compile_execute_s=19.464

### Answer

Observed result: 1 evidence records. Source: Imported EBTL primary evidence. site documentation names a roughly one-acre Eucalyptus monocrop removal; public occurrence points add candidate taxa inside the analysis bbox, which is not the 70-acre property boundary; Lantana returns zero points.

audit_passed=True fallback=False render_s=0.001

## Turn 5 — SCARCE-1: INVASIVE REBOUND — whether Lantana or other invasives are returning after removal; expect unknown + concrete repeated-map DATA REQUEST.

### Kavya

Do we know whether the removed invasive vegetation is returning? If the evidence cannot show rebound, design the smallest repeated field measurement that would answer it.

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
    "entity": "EBTL invasive evidence",
    "region": {
      "op": "REGION",
      "place": "Elephants by the Lake"
    },
    "time": null
  }
}
```

schema_valid=True status=data_request label=None compile_execute_s=22.662

### Answer

I cannot answer this from the available evidence yet (gate_failed). DATA REQUEST: provide georeferenced species occurrence records

audit_passed=True fallback=False render_s=0.001

## Turn 6 — FIRE — observed fire history versus present/future risk; fuels/weather/field gaps.

### Kavya

What can the available data honestly say about fire at EBTL—observed fire history versus present or future risk? Give the measured scale and the missing fuel or weather data.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "EBTL evidence",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=5.682

### Answer

I cannot answer this from the available evidence yet (no_connector). DATA REQUEST: no data source maps this entity; add a connector or refine the term

audit_passed=True fallback=False render_s=0.0

## Turn 7 — ASSISTED NATURAL REGENERATION — evidence for choosing ANR versus planting across the property; avoid recommendation without treatment/plot data.

### Kavya

The field team is choosing between assisted natural regeneration and planting across different parts of the site. Do we have evidence to choose, and if not what plot comparison should we collect before recommending one?

### Algebra

```json
{
  "op": "SELECT",
  "entity": "?regeneration_type",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=3.521

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?regeneration_type

audit_passed=True fallback=False render_s=0.0

## Turn 8 — NURSERY + PHYLOGENY — what native material is documented and whether phylogenetic/functional diversity can be assessed.

### Kavya

What native material is actually documented in the EBTL nursery? Can those records support a claim about phylogenetic or functional diversity, or what taxonomy and trait fields are missing?

### Algebra

```json
{
  "op": "SELECT",
  "entity": "?nursery_taxon",
  "region": {
    "op": "REGION",
    "place": "EBTL nursery"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=3.995

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?nursery_taxon

audit_passed=True fallback=False render_s=0.0

## Turn 9 — SNAKES — locally documented venomous/non-venomous species and survey-status boundary.

### Kavya

Let us drill into snakes. Which species are documented for the property, which were encountered in the 2024 survey, and which documented species are venomous? Do not turn non-detection into absence.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "snake",
  "region": {
    "op": "REGION",
    "place": "property"
  },
  "time": {
    "start": "2024"
  }
}
```

schema_valid=True status=data_request label=None compile_execute_s=4.794

### Answer

I cannot answer this from the available evidence yet (no_connector). DATA REQUEST: no data source maps this entity; add a connector or refine the term

audit_passed=True fallback=False render_s=0.0

## Turn 10 — ARACHNIDS — sparse local data, regional discovery, and environmental transfer gates.

### Kavya

What about arachnids at EBTL? Start with local public records, then tell me whether regional records or papers produce any defensible candidates rather than a made-up species list.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "arachnids",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=answer label=observed compile_execute_s=3.995

### Answer

Observed result: 1 evidence records: Thelacantha brevispina (Doleschall, 1857). Source: GBIF+iNaturalist higher-taxon query. 1 coordinate/species-deduplicated public occurrence records for the verified higher taxon Arachnida in the analysis bbox; 1 named taxa in returned rows; semantic discovery produced 0 dataset leads; this is not a complete site inventory.

audit_passed=True fallback=False render_s=0.001

## Turn 11 — HABITAT PROTECTION — which measured habitat features would support snake/arachnid protection; refuse invented tree dependencies.

### Kavya

For the snakes already documented at EBTL, do we know which tree species they require? Separate measured habitat evidence from a plausible but untested dependency, and tell the field team what habitat variables to record.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "snake",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": {
    "start": "2024"
  }
}
```

schema_valid=True status=answer label=observed compile_execute_s=4.151

### Answer

Observed result: 14 evidence records: Common Sand Boa, Striped Keelback, Barred Wolf Snake, Brahmini Blind Snake, Beaked Blind Snake, Rat Snake, Checkered Keelback, Olive Keelback. Source: Faunal Survey 2024 — Herpetofauna of EBTL. published site inventory: 14 snake species; 3 encountered during the September 2024 VES and 11 previously recorded on the property but not encountered during that three-day survey.

audit_passed=True fallback=False render_s=0.001

## Turn 12 — EASTERN GHATS TRANSFER — how to use surrounding regional records without presenting them as EBTL observations.

### Kavya

If we widen from EBTL to the dry Eastern Ghats donor belt, how does the system decide whether a regional species can be estimated at the site? Show me the environmental gates and reject candidates that fail them.

### Algebra

```json
{
  "op": "ESTIMATE",
  "method": "envelope",
  "target": {
    "op": "REGION",
    "place": "Dry Eastern Ghats Donor Belt"
  },
  "source": {
    "op": "SELECT",
    "entity": "regional species",
    "region": {
      "op": "REGION",
      "place": "Elephants by the Lake"
    },
    "time": null
  }
}
```

schema_valid=True status=data_request label=None compile_execute_s=8.612

### Answer

I cannot answer this from the available evidence yet (no_connector). DATA REQUEST: no data source maps this entity; add a connector or refine the term

audit_passed=True fallback=False render_s=0.001

## Turn 13 — SCARCE-2: COMMUNITIES + LIVELIHOODS — grazing, fuelwood, restoration jobs, crop loss or coexistence around the site; expect unknown + ethical household/usage DATA REQUEST.

### Kavya

We also work with neighbouring communities. What evidence do we have on grazing, fuelwood collection, restoration jobs, crop loss or coexistence around EBTL? If none, propose an ethical household and resource-use data request without inventing percentages.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "?indicator",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=3.62

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?indicator

audit_passed=True fallback=False render_s=0.001

## Turn 14 — SYNTHESIS — a short field-team brief: defensible findings, bounded estimates, immediate conservation actions, and the three highest-value data collections.

### Kavya

Give me a short field-team brief from this conversation: defensible local findings, bounded regional or modelled signals, decisions we still cannot make, and the three highest-value data collections next.

### Algebra

```json
{
  "op": "AGGREGATE",
  "by": "time",
  "metric": "count",
  "source": {
    "op": "SELECT",
    "entity": "clinic",
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

schema_valid=True status=data_request label=None compile_execute_s=6.915

### Answer

I cannot answer this from the available evidence yet (no_connector). DATA REQUEST: no data source maps this entity; add a connector or refine the term

audit_passed=True fallback=False render_s=0.0

