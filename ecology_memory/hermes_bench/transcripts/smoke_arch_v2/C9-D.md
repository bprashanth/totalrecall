# EBTL Kavya drill-down — C9-D

compiler=lora9b responder=deterministic round=smoke_arch_v2

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

schema_valid=True status=answer label=observed compile_execute_s=5.634

### Answer

Observed result: 5 evidence records: 67 species in a local 2024 transit survey, 14 documented property species; 3 encountered in the three-day 2024 VES, two passage events supported by indirect physical signs, 110-species/15,000-sapling July 2024 snapshot; 23 taxa named in imported issues, roughly one acre of Eucalyptus removal documented; no local Lantana confirmation. Source: Imported EBTL primary evidence. local evidence summary; satellite layers and regional literature are separate proxy/modelled evidence and are not promoted to local observations.

audit_passed=True fallback=False render_s=0.0

