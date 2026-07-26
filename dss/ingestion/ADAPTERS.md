# Source adapters

Status: contract for the adapters implemented by `visual-site-pack/0.1`.

## What an adapter is

An adapter is a reviewed, source-specific mapping from immutable source fields to canonical
factual planes. It is not:

- an LLM call at build or query time;
- one adapter per SQL column;
- a user-facing skill or visual;
- a scientific model; or
- permission to admit a source.

One source commonly has several adapters because one workbook or repository can contain
locations, events, effort and measurements.

## Where adapters are stored

Adapters currently live inline in:

```text
dss/sites/<site-id>/sources.json
  -> sources[]
     -> source entry
        -> adapters[]
```

Source-level `crosswalks` and `hierarchy` declarations sit beside `adapters`. Immutable input files
and codebooks live beneath that pack's `raw/<source-id>/`.

Example:

```json
{
  "source_id": "survey-v1",
  "local_metadata": "raw/survey-v1/README.txt",
  "capabilities": ["inspectable", "has_events", "has_measurements"],
  "adapters": [
    {
      "kind": "event",
      "path": "raw/survey-v1/observations.csv",
      "record_id": "observation_id",
      "date": "observed_on",
      "entity": "scientific_name",
      "entity_alias": "local_name",
      "count": "individual_count"
    },
    {
      "kind": "measurement",
      "path": "raw/survey-v1/observations.csv",
      "record_id": "observation_id",
      "date": "observed_on",
      "metrics": {"canopy_cover": "percent"},
      "metric_columns": {"canopy_cover": "canopy_pct"}
    }
  ]
}
```

There is no separate adapter registry in v0.1. Moving large adapters to referenced files would be
an additive format change requiring builder support and conformance tests; do not invent a private
include convention inside one pack.

## How adapters execute

`dss/visual_index/build.py` loads `sources.json` and dispatches each adapter by `kind` to generic
Python:

```text
location     -> _ingest_location
event        -> _ingest_event
effort       -> _ingest_effort
interaction  -> _ingest_interaction
measurement  -> _ingest_measurement
cell_feature -> _ingest_cell_feature
matrix       -> _ingest_matrix
```

The execution is deterministic. IDs are stable hashes of declared source, adapter, source record,
metric and/or row components. Every output retains `source_id` and `source_row`.

The builder does not ask a language model what a field means. If an adapter maps
`FlowerScore` to `flowering_intensity`, that decision was made during profiling and review and is
now explicit configuration.

## Shared adapter fields

Common fields include:

| Field | Purpose |
|---|---|
| `kind` | exact generic ingest operation |
| `adapter_id` | stable identity when path alone is insufficient |
| `path` | immutable delimited source file, relative to pack |
| `delimiter` | defaults to CSV; use `"\\t"` for tabular archives |
| `record_id` | source column or composite columns defining a record |
| `date`, `date_value`, `date_parts` | source time binding |
| `latitude`, `longitude`, `uncertainty_m` | inline spatial fields |
| `location_lookup` | reviewed join to a location table |
| `properties` | source fields preserved for drill-down, not promoted to schema |
| `evidence_class` | observed, reported, modelled or another admitted class |

`properties` is not an escape hatch for relationships required by generic analysis. A value may
stay there when it is useful for audit or display but not yet part of a shared analytical
operation. If repeated capabilities must filter, join or validate it, assess whether it belongs in
a canonical field or plane.

## Adapter kinds

### `location`

Maps named or coded places. Requires `location_id`, `label`, latitude and longitude fields.
Locations are source-scoped in v0.1: the SQL key is `(location_id, source_id)`.

### `event`

Maps a dated source record or occurrence. It can bind an entity, status, event type, count,
coordinates and source properties. Entity lookup, hierarchy and aliases may be supplied by
source-level crosswalks or adapter lookups.

An event's `count_value` is the magnitude reported in that event. The number of events is a
derived count of rows.

### `effort`

Maps observation or exposure denominators such as survey minutes, trap-nights, sampled area,
eligible population or person-time. Effort must not be inferred from the number of event rows.

### `interaction`

Maps an explicit source-reported subject-object relation. Spatial or temporal proximity never
creates an interaction adapter row.

### `measurement`

Maps one source row to one or more long-form metric rows:

```text
source row
  -> metric, value, unit, time, location, source lineage
```

`metrics` declares canonical identifiers and units. `metric_columns` maps each identifier to its
source heading. `metric_labels`, `metric_descriptions` and `metric_methods` provide source-level
meaning.

Adding a metric does not add a SQL column. A site without that metric simply has no matching rows.

### `cell_feature`

Maps cell-aligned predictors or context surfaces. It preserves feature identifier, unit, evidence
class, source asset, aggregation and scale. A model product remains modelled evidence.

### `matrix`

Maps values over two dimensions such as hour by frequency band. The adapter declares matrix,
series, axes, value and unit; the UI receives a generic matrix result, not source-specific sound
columns.

## LLM-assisted authoring

An LLM can be useful for:

- connecting codebook definitions to source headings;
- suggesting event/measurement/effort classification;
- proposing canonical metric and entity names;
- finding likely composite keys and joins;
- identifying ambiguous zero, missing and absence semantics; and
- drafting adapter JSON and explanations.

Its proposal must be grounded in the profile and codebook. Review and deterministic validation
must check every referenced column, unit, key, join and representative output row. The approved
adapter is then committed; the LLM is no longer involved in execution.

## When to update an adapter

Update or add an adapter when:

- an immutable source version has a different layout;
- a codebook correction changes a field's admitted meaning;
- an identifier, unit, date, coordinate or join mapping was wrong;
- additional source fields can populate an existing canonical plane; or
- a new generic adapter feature becomes available.

Create a new source version instead of rewriting admitted source bytes. Version the adapter or use
a stable `adapter_id` when changing its identity would otherwise change derived IDs unexpectedly.

Do not update a source adapter to implement a new statistical method, renderer or conversational
synonym. Those belong to capabilities, result contracts or agent binding.

## Current limitations

- Adapter configuration has prose and implementation validation, but no complete machine-readable
  JSON Schema.
- The v0.1 measurement plane lacks first-class `entity_id`, `event_id` and `subject_id` links.
- Metric definitions are source-specific; cross-source construct compatibility is reviewed rather
  than enforced by a global ontology.
- Source-scoped locations need explicit reconciliation when two sources name the same place.
- The generic builder currently reads delimited text; other containers need a reviewed extraction
  step before these adapters run.
