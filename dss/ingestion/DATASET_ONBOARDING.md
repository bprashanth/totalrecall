# Onboarding a dataset into a site

Status: current manual admission procedure and intended admission-service design.

Use this guide for a new dataset, a new immutable version of an existing source, or a
paper-associated data package. The process applies to supplied files, APIs, databases,
repositories, rasters and media.

## Admission is a state transition

```text
discovered
  -> staged
  -> profiled
  -> mapping proposed
  -> review required
  -> validated
  -> admitted
  -> indexed and published
```

`rejected` and `quarantined` are valid outcomes. A staged or profiled source is not evidence
available to shared questions.

## 1. Acquire and preserve

Acquire an exact version through a reusable connector or a supplied-file intake:

- preserve original bytes;
- record upstream identifier, URL or DOI;
- record retrieval time, publisher and version;
- compute checksums;
- record licence, consent, redistribution and sensitive-data constraints;
- preserve codebooks, README files and related assets; and
- never overwrite an admitted version.

Store the source beneath `dss/sites/<site-id>/raw/<source-id>/`, or reference approved immutable
storage when bytes cannot live in Git.

The paper workbench's `paper-source-candidate/1` queue begins this process. Its record is only a
request to acquire and profile the dataset.

## 2. Profile deterministically

Profiling describes the container before assigning analytical meaning. Its artefact should record:

- files, sheets, encodings, delimiters and media types;
- headers, inferred primitive types and representative values;
- row counts, missingness, uniqueness and duplicate candidate keys;
- numeric ranges and categorical frequencies;
- date, timezone, coordinate and unit conventions;
- codebook definitions and column descriptions;
- possible joins between sheets and associated assets;
- repeated identifiers and repeated-measure patterns;
- invalid rows and parsing failures; and
- privacy, sensitivity and rights warnings.

The profiler may say “column `FlowerScore` is numeric, ranges from 0 to 4, repeats by tree and
month, and the codebook calls it flowering score.” It should not silently decide that two
protocols measure the same construct.

`dss/visual_index/upload_service.py` already profiles session-scoped CSV/XLSX uploads for
interactive use. That is not yet the durable admission profiler: it does not approve source
rights, commit adapters or alter the shared site index.

## 3. Classify source facts

Map meanings, not file types:

| Source fact | Canonical plane |
|---|---|
| source version and rights | `sources` |
| named analytical subject | `entities`, `entity_aliases` |
| plot, station, village or facility | `locations` |
| dated occurrence or record | `events` |
| observation/exposure denominator | `effort` |
| typed value with a unit | `measurements`, `metric_definitions` |
| explicitly reported subject-object relation | `interactions` |
| spatial predictor or context surface | `cells`, `cell_features` |
| ordered two-dimensional values | `matrix_values` |
| original document, raster or media bytes | immutable asset plus document/media index |

For example, a camera-trap workbook can emit locations, deployment effort, detection events and
media references. It does not require a `camera_trap_workbook` table.

A sighting is an `event`; the number of observed individuals is its `count_value`; the number of
sightings is derived by counting events. Flowering intensity is a `measurement`. Search minutes
or trap-nights are `effort`.

## 4. Propose the adapter

The usual adapter is declarative configuration in the source's `adapters` array in
`dss/sites/<site-id>/sources.json`. See [ADAPTERS.md](ADAPTERS.md).

An LLM may draft this proposal after receiving:

- the deterministic profile;
- relevant codebook passages;
- representative and failure rows;
- the existing canonical metric/entity vocabulary;
- available adapter kinds; and
- the site's questions and capability requirements.

The proposal must explain every semantic choice. It must not execute arbitrary generated code or
admit itself.

New Python is justified only when a reusable parser or transformation is missing—for example, a
new container format, a generic projection conversion or a reusable media metadata extractor.
Source-specific column mappings still belong in the adapter.

## 5. Review semantics and identity

Review at least:

- canonical entity and metric names;
- source column, output unit and conversion;
- date and coordinate interpretation;
- record and subject identity scope;
- location joins;
- event versus measurement versus effort classification;
- aliases and ambiguous names;
- treatment of missing, zero and absence;
- evidence class;
- row-access and coordinate-sensitivity policy; and
- whether source and adapter support each declared capability.

### Metric naming

`metric_columns` maps a source heading to an admitted metric identifier:

```json
{
  "kind": "measurement",
  "path": "raw/phenology-v1/observations.csv",
  "record_id": ["plot_id", "tree_no", "visit_date"],
  "date": "visit_date",
  "metrics": {
    "flowering_intensity": "ordinal-score"
  },
  "metric_columns": {
    "flowering_intensity": "FlowerScore"
  },
  "metric_labels": {
    "flowering_intensity": "Flowering intensity"
  },
  "metric_descriptions": {
    "flowering_intensity": "Observer score from 0 to 4 under protocol P1"
  }
}
```

The current index has source-specific `metric_definitions`; it does not yet provide a complete
cross-source metric ontology. Reuse a metric identifier only when construct, unit, grain and
protocol are compatible. Similar words are not sufficient.

### Individual identity

The v0.1 schema has no first-class individual/subject plane. Some adapters retain a source-defined
tree key in `record_id`—for example `(site, plot, quadrat, tree_number)`—and every row retains
`source_id` and `source_row`. This makes the record reproducible but does not create a global tree
identity or a formal measurement-to-individual foreign key.

Do not infer an individual from GPS and time unless the source protocol defines that identity.
GPS and time normally identify an observation. Cross-source individual matching requires a
source-backed identifier or an explicitly reviewed crosswalk.

Repeated individual measurements are a known reason to add a generic `subjects` plane and
`subject_id` links. That change must be made once in the shared schema, not as phenology-specific
columns. See [SCHEMA_EVOLUTION.md](SCHEMA_EVOLUTION.md).

## 6. Validate before admission

Validation must be deterministic and source-specific:

- referenced files and columns exist;
- row counts and accepted/rejected counts are reported;
- configured keys have the expected uniqueness and scope;
- coordinates, dates, values and units are valid;
- joins have measured match rates;
- unknown entity and metric mappings are listed;
- source-row lineage is retained;
- checksum coverage matches the source manifest;
- sensitive fields do not enter public serving products;
- adapter output populates only declared planes; and
- representative capability probes succeed.

The reviewer approves a specific source checksum and adapter revision. A later source version
returns to profiling and review.

## 7. Admit, rebuild and publish

Admission updates the source entry in `sources.json`, including provenance, rights, row-access
policy, capabilities, crosswalks and adapters. Then rebuild:

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/<site-id> \
  --output /tmp/<site-id>-index
```

Compare the build with the previous admitted index. Unexpected changes in other sources, entities,
units or capabilities block publication. After probes pass, publish a new pack/index digest and
restart or refresh the site service.

## The admission service

The productised service should automate the safe mechanics while preserving review:

```text
intake API or watched queue
  -> immutable object store + source manifest
  -> container profiler and extractors
  -> adapter and crosswalk proposal
  -> validation report and quarantined rows
  -> reviewer decision
  -> registry update
  -> isolated index build
  -> capability/question probes
  -> atomic publication of a new pack digest
```

It should persist these artefacts:

- `intake.json`: submitter, site, source candidate and requested purpose;
- `manifest.json`: immutable files, hashes, rights and access policy;
- `profile.json`: deterministic container and field observations;
- `adapter.proposed.json`: model- or operator-authored proposal with rationale;
- `validation.json`: accepted/rejected rows, joins, units, identity and privacy checks;
- `review.json`: reviewer, decision and exact approved digests;
- `build_report.json`: isolated build counts and integrity;
- `probe_report.json`: question/capability outcomes; and
- `publication.json`: resulting pack and index digests.

The service may use an LLM only to propose semantics or explain ambiguity. Deterministic checks
and an authorised review decision control admission. Generated code runs only in a constrained
profiling environment and becomes reusable reviewed tooling before admission.

## What changes for common additions

| Addition | Normal change |
|---|---|
| New CSV headings for known facts | new/updated source adapter |
| New metric with compatible measurement shape | measurement adapter + metric definition |
| New entity names | adapter/crosswalk/hierarchy |
| New immutable source version | new source version + repeat admission |
| New analytical model | capability/method version, not source schema |
| New file container | reusable extractor/connector, then ordinary adapters |
| New relationship impossible to preserve in existing planes | shared schema proposal |
