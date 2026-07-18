# EBTL Kavya drill-down — C2-D

compiler=qwen2b responder=deterministic round=curriculum_probe_v1

## Turn 1 — OPEN — map EBTL for a new conservation colleague: strongest local facts and major unknowns.

### Kavya

What can the available data honestly say about fire at EBTL—observed fire history versus present or future risk? Give the measured scale and the missing fuel or weather data.

### Algebra

```json
{
  "op": "AGGREGATE",
  "by": "space",
  "metric": "count",
  "source": {
    "op": "RELATE",
    "left": {
      "op": "SELECT",
      "entity": "tree",
      "region": {
        "op": "REGION",
        "place": "Elephants by the Lake"
      },
      "time": null
    },
    "right": {
      "op": "SELECT",
      "entity": "tree",
      "region": {
        "op": "REGION",
        "place": "Elephants by the Lake"
      },
      "time": null
    },
    "relation": "within"
  }
}
```

schema_valid=True status=data_request label=None compile_execute_s=10.385

### Answer

I cannot answer this from the available evidence yet (no_connector). DATA REQUEST: no data source maps this entity; add a connector or refine the term

audit_passed=True fallback=False render_s=0.0

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

schema_valid=True status=data_request label=None compile_execute_s=1.778

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?proxy

audit_passed=True fallback=False render_s=0.0

