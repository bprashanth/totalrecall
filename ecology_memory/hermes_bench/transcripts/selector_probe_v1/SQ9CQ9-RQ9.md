# EBTL Kavya drill-down — SQ9CQ9-RQ9

compiler=qwen9b@qwen9b responder=qwen9b round=selector_probe_v1

## Turn 1 — OPEN — map EBTL for a new conservation colleague: strongest local facts and major unknowns.

### Kavya

What can the available data honestly say about fire at EBTL—observed fire history versus present or future risk? Give the measured scale and the missing fuel or weather data.

### Algebra

```json
{
  "op": "SELECT",
  "entity": "EBTL restoration site",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=answer label=proxy compile_execute_s=5.258

### Answer

The available data cannot honestly describe observed fire history or present/future fire risk at the EBTL site because no fire records exist in the audited result. The only spatial data provided is a single point proxy for the "EBTL site center" at coordinates 12.73394, 78.18344, which serves as a metadata marker rather than an area of interest or a measurement of fire activity.

Consequently, there is no measured scale of fire, nor are there any recorded fuel or weather variables to assess risk. To determine fire history or risk, a data request is needed to measure actual fire occurrences or fuel/weather conditions across the defined region (Elephants by the Lake, Chinnathamandrapalli, Krishnagiri, Tamil Nadu) with sufficient spatial coverage to move beyond a single point proxy.

audit_passed=True fallback=False render_s=0.002

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

schema_valid=True status=data_request label=None compile_execute_s=5.061

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?proxy

audit_passed=True fallback=True render_s=8.37

