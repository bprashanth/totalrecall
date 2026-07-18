# EBTL Kavya drill-down — CQ9-D

compiler=qwen9b responder=deterministic round=curriculum_probe_v1

## Turn 1 — OPEN — map EBTL for a new conservation colleague: strongest local facts and major unknowns.

### Kavya

What can the available data honestly say about fire at EBTL—observed fire history versus present or future risk? Give the measured scale and the missing fuel or weather data.

### Algebra

```json
{
  "op": "RELATE",
  "relation": "beyond",
  "threshold_km": 5.0,
  "left": {
    "op": "SELECT",
    "entity": "EBTL restoration site",
    "region": {
      "op": "REGION",
      "place": "Elephants by the Lake"
    },
    "time": null
  },
  "right": {
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
}
```

schema_valid=True status=answer label=proxy compile_execute_s=14.13

### Answer

Proxy result: 0 evidence records. Source: relate. 1 x 1 -> 0.

audit_passed=True fallback=False render_s=0.0

## Turn 2 — WILDLIFE BASELINE — what groups were actually surveyed, when, and what “recorded” means.

### Kavya

We also work with neighbouring communities. What evidence do we have on grazing, fuelwood collection, restoration jobs, crop loss or coexistence around EBTL? If none, propose an ethical household and resource-use data request without inventing percentages.

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

schema_valid=True status=answer label=observed compile_execute_s=5.804

### Answer

Mixed-evidence result: 5 evidence records: [observed] 67 species in a local 2024 transit survey, [observed] 14 documented property species; 3 encountered in the three-day 2024 VES, [indirect] two passage events supported by indirect physical signs, [reported] 110-species/15,000-sapling July 2024 snapshot; 23 taxa named in imported issues, [reported] roughly one acre of Eucalyptus removal documented; no local Lantana confirmation. Source: Imported EBTL primary evidence. local evidence summary; satellite layers and regional literature are separate proxy/modelled evidence and are not promoted to local observations.

audit_passed=True fallback=False render_s=0.0

