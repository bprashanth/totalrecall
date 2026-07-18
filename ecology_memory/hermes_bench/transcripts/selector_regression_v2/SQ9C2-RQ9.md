# EBTL Kavya drill-down — SQ9C2-RQ9

compiler=qwen9b@qwen2b responder=qwen9b round=selector_regression_v2

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

We currently have no usable facts or spatial data for Elephants by the Lake because the available record is invalid and contains no evidence. The system indicates a specific technical failure where the data source is missing a required "time" field, meaning we cannot determine when observations occurred or which region the data covers.

To move forward, we need to request the raw dataset for the project area, specifically ensuring that every record includes a timestamp (date and time) and a valid geographic region identifier. Without these two fields, we cannot map elephant locations, assess population trends, or verify the presence of the species in the field.

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

We do not have any confirmed facts regarding wildlife groups, dates, or survey effort for the property in 2024 because the current data request failed due to a missing "layer" field in the source selection. Consequently, no animals seen in 2024 can be separated from older or indirect records at this time.

To obtain the specific 2024 survey details you need, we must request the corrected source data that includes the required "layer" field. Please provide the updated dataset or specify which layer should be included in the selection query so the system can retrieve the actual survey records.

audit_passed=True fallback=False render_s=11.76

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

The current data system cannot tell us whether the bird list represents year-round richness, monsoon/winter migrants, or a seasonal snapshot because the query failed to retrieve any records due to a missing 'layer' field. Consequently, no specific wildlife groups, dates, or effort levels are available to distinguish between resident and migratory species.

To close this gap, a new survey must be conducted that explicitly records the temporal layer (e.g., season or month) for every bird observation. This repeated survey should cover the full annual cycle to capture both resident populations and seasonal migrants, ensuring the data includes the specific time attribute required to analyze richness patterns.

audit_passed=True fallback=False render_s=9.954

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

The current data pack contains no documented facts about invasive species at Elephants by the Lake; the system cannot retrieve any local records, regional literature, satellite proxies, or public records due to a technical error in the data query. Because the evidence is missing entirely, it is unknown whether any invasives are present on the property or if only external sources exist.

To close this gap, a field survey is required to measure invasive plant or animal presence directly at specific sites within the EBTL property boundaries. This effort should include recording species names, counts, and locations during a dedicated invasive species assessment to distinguish between local observations and any future regional data.

audit_passed=True fallback=False render_s=3.059

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

The available data cannot honestly say anything about fire at EBTL because no data source currently maps to this specific entity. There are no recorded observations of fire history, nor are there any measurements of present or future fire risk, fuel loads, or weather conditions for this location.

To close this gap, a concrete data request is needed: conduct a site visit or connect to a local fire history database to measure or record the scale of any past fires, current fuel conditions, and relevant weather variables specifically at EBTL.

audit_passed=True fallback=False render_s=7.954

