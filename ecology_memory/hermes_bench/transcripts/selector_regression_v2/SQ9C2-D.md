# EBTL Kavya drill-down — SQ9C2-D

compiler=qwen9b@qwen2b responder=deterministic round=selector_regression_v2

## Turn 1 — OPEN — map EBTL for a new conservation colleague: strongest local facts and major unknowns.

### Kavya

I work with a conservation NGO around Elephants by the Lake. Map EBTL for a new field colleague: what are the strongest facts we actually have, and what are the important gaps?

### Algebra

```json
{
  "op": "ANNOTATE",
  "source": {
    "op": "SELECT",
    "entity": "elephant",
    "region": {
      "op": "REGION",
      "place": "Lake",
      "time": null
    }
  },
  "layer": "ebtl"
}
```

schema_valid=False status=data_request label=None compile_execute_s=4.017

### Answer

I cannot answer this from the available evidence yet (invalid_ir). DATA REQUEST: root.source: SELECT missing required field 'time'; root.source.region: REGION has unknown field(s) ['time'] — wrong op composed?

audit_passed=True fallback=False render_s=0.0

## Turn 2 — WILDLIFE BASELINE — what groups were actually surveyed, when, and what “recorded” means.

### Kavya

That is useful, but what was actually surveyed on the property in 2024? Give me the wildlife groups, dates and effort, and separate animals seen in that survey from older or indirect records.

### Algebra

```json
{
  "op": "ANNOTATE",
  "source": {
    "op": "SELECT",
    "entity": "ebtl",
    "layer": "wildlife_inventory",
    "region": {
      "op": "REGION",
      "place": "Lake, Kenya"
    },
    "time": {
      "start": "2024",
      "end": "2024"
    }
  },
  "layer": "ebtl"
}
```

schema_valid=False status=data_request label=None compile_execute_s=8.843

### Answer

I cannot answer this from the available evidence yet (invalid_ir). DATA REQUEST: root.source: SELECT has unknown field(s) ['layer'] — wrong op composed?

audit_passed=True fallback=False render_s=0.0

## Turn 3 — BIODIVERSITY COVERAGE — what important groups or seasons are missing; why inventory is not richness.

### Kavya

For the bird list specifically, can it tell us year-round richness or monsoon and winter migrants, or is it only a seasonal snapshot? Tell me exactly what repeated survey would close that gap.

### Algebra

```json
{
  "op": "ESTIMATE",
  "method": "feature",
  "target": {
    "op": "REGION",
    "place": "Lake, Kenya"
  },
  "source": {
    "op": "SELECT",
    "entity": "ebtl",
    "layer": "bird_inventory",
    "region": {
      "op": "REGION",
      "place": "Lake, Kenya"
    },
    "time": {
      "start": "2024",
      "end": "2024"
    }
  }
}
```

schema_valid=False status=data_request label=None compile_execute_s=7.027

### Answer

I cannot answer this from the available evidence yet (invalid_ir). DATA REQUEST: root.source: SELECT has unknown field(s) ['layer'] — wrong op composed?

audit_passed=True fallback=False render_s=0.0

## Turn 4 — INVASIVES — what is locally documented versus public-bbox or regional evidence.

### Kavya

Now invasives: what is documented locally at EBTL, and what comes only from regional literature, satellite proxies or public records? Please keep those evidence levels separate.

### Algebra

```json
{
  "op": "ANNOTATE",
  "source": {
    "op": "SELECT",
    "entity": "invasive evidence",
    "layer": "local management documentation",
    "region": {
      "op": "REGION",
      "place": "Elephants by the Lake"
    },
    "time": null
  },
  "layer": "ebtl"
}
```

schema_valid=False status=data_request label=None compile_execute_s=8.202

### Answer

I cannot answer this from the available evidence yet (invalid_ir). DATA REQUEST: root.source: SELECT has unknown field(s) ['layer'] — wrong op composed?

audit_passed=True fallback=False render_s=0.0

## Turn 5 — SCARCE-1: INVASIVE REBOUND — whether Lantana or other invasives are returning after removal; expect unknown + concrete repeated-map DATA REQUEST.

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
      "entity": "ebtl",
      "region": {
        "op": "REGION",
        "place": "Elephants by the Lake"
      },
      "time": null
    },
    "right": {
      "op": "SELECT",
      "entity": "fire",
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

schema_valid=True status=data_request label=None compile_execute_s=8.374

### Answer

I cannot answer this from the available evidence yet (no_connector). DATA REQUEST: no data source maps this entity; add a connector or refine the term

audit_passed=True fallback=False render_s=0.0

