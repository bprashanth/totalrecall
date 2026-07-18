# EBTL Kavya drill-down — SQ9C9-D

compiler=qwen9b@lora9b responder=deterministic round=selector_probe_v1

## Turn 1 — OPEN — map EBTL for a new conservation colleague: strongest local facts and major unknowns.

### Kavya

What can the available data honestly say about fire at EBTL—observed fire history versus present or future risk? Give the measured scale and the missing fuel or weather data.

### Algebra

```json
{
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
```

schema_valid=True status=answer label=proxy compile_execute_s=16.43

### Answer

Proxy result: 1 evidence records. Source: SITE_EBTL.json + origin fire.py → MODIS/061/MOD14A1 via Earth Engine. 0 historical 2020-2025 MODIS active-fire locations inside the exact AOI; point exposure also measured within 5 km; pixel-fire-days are a pressure proxy, not fire probability or burned area.

audit_passed=False fallback=False render_s=0.0

## Turn 2 — WILDLIFE BASELINE — what groups were actually surveyed, when, and what “recorded” means.

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

schema_valid=True status=data_request label=None compile_execute_s=5.505

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?proxy

audit_passed=True fallback=False render_s=0.0

