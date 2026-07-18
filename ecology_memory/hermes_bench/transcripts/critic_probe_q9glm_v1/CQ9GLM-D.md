# EBTL Kavya drill-down — CQ9GLM-D

compiler=qwen9b+glm responder=deterministic round=critic_probe_q9glm_v1

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

schema_valid=True status=answer label=proxy compile_execute_s=77.688

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
  "entity": "?proxy",
  "region": {
    "op": "REGION",
    "place": "Elephants by the Lake"
  },
  "time": null
}
```

schema_valid=True status=data_request label=None compile_execute_s=4.37

### Answer

I cannot answer this from the available evidence yet (unbound_holes). DATA REQUEST: clarify: ?proxy

audit_passed=True fallback=False render_s=0.0

