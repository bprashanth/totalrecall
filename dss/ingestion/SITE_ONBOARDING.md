# Onboarding a site

Status: current manual workflow and future admission-service contract.

Use this guide when creating a new place or organisation pack. For adding a source to an existing
pack, use [DATASET_ONBOARDING.md](DATASET_ONBOARDING.md).

## 1. Establish identity and governance

Before acquiring data, record:

- a stable `site_id` that will not be reused;
- organisation identity and the people authorised to approve sources;
- names and aliases that users actually use for the place;
- data-access, privacy, coordinate-sensitivity and redistribution rules;
- the declared purpose of the pack; and
- who owns source, adapter, capability and deployment changes.

Do not make a site ID depend on one project, model, interface or temporary deployment.

## 2. Establish geometry

Create `dss/sites/<site-id>/site.json` using `visual-site-pack/0.1`.

At minimum, distinguish:

- `target_aoi`: the place about which results may be stated;
- `context_aoi`: a wider envelope used for discovery, donor data and modelling;
- `geometry_role`: what the geometry actually represents; and
- `limitations`: uncertainty, approximation and access constraints.

Preserve an organisation-supplied KML, GeoJSON or shapefile as an immutable source. The v0.1
builder currently reads inline GeoJSON for `target_aoi` and uses its bounding box for point
membership. Do not call a published study envelope a property boundary.

## 3. Start with questions, not tables

Write a small initial `questions.json` in the language staff use. Include orientation, comparison,
coverage, trend, drill-down and known difficult questions. For each question record:

- the intended first visual;
- the capability that should answer it;
- the required factual planes; and
- whether the expected state is ready, partial or blocked.

These questions guide acquisition. They are not prompts that permit the model to invent missing
data.

## 4. Inventory source families

Build a source inventory before downloading indiscriminately. Typical families include:

- organisation-supplied tables and databases;
- boundaries and named-place files;
- repository or DOI datasets;
- APIs and regularly refreshed feeds;
- reports, papers and codebooks;
- rasters and model products; and
- media with associated metadata.

For each candidate record authority, version, rights, expected grain, update frequency, sensitive
fields, likely join keys and the questions it could support. Discovery is not admission.

## 5. Create the pack skeleton

```text
dss/sites/<site-id>/
├── site.json
├── sources.json
├── capabilities.json
├── questions.json
├── README.md
├── raw/
│   └── <source-id>/
└── derived/
    └── <versioned-product-id>/
```

Use these schema versions:

- `site.json`: `visual-site-pack/0.1`;
- `sources.json`: `visual-source-registry/0.1`;
- `capabilities.json`: `visual-capability-registry/0.1`; and
- `questions.json`: `visual-question-probes/0.1`.

`raw/` contains immutable acquired versions. A correction or refresh creates a new source version;
it does not edit previously admitted bytes. `derived/` products need their own recipe, inputs,
parameters, evidence class and version.

## 6. Admit the first datasets

Follow [DATASET_ONBOARDING.md](DATASET_ONBOARDING.md) for every source version. A useful first pack
usually needs:

- authoritative geometry or named locations;
- at least one event or measurement source;
- the effort or exposure needed to interpret it;
- entity aliases or crosswalks where names vary; and
- source rights and row-access rules.

Do not declare a capability merely because a file exists. Declare it when admitted adapters
produce the required planes and its gates can be evaluated.

## 7. Declare analysis capabilities

`capabilities.json` describes site-agnostic operations, not user-interface components. Each
capability declares:

- stable `capability_id` and semantic version;
- typed arguments;
- required and optional factual planes;
- output views;
- evidence classes and limitations;
- latency class; and
- `ready`, `partial` or `blocked` availability.

A new site normally reuses existing capabilities with different readiness. Add a capability only
when the analytical operation itself is genuinely new.

## 8. Build and probe

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/<site-id> \
  --output /tmp/<site-id>-index
```

Acceptance requires more than SQLite integrity:

- every admitted file has provenance, rights and a checksum;
- adapter sample rows and rejected rows have been reviewed;
- source-row lineage survives;
- units and denominators are explicit;
- stable identifiers do not collide;
- counts independently match expected source totals;
- question probes produce the expected state and first visual;
- empty and partial results remain honest;
- sensitive rows and coordinates are protected before serving; and
- another pack cannot leak into this deployment.

## 9. Register and deploy

Register the pack in `dss/sites/registry.json` only after it builds. Give it its own state
directory, port and model/endpoint label. Deploy using
[../SITE_PACK_DEPLOYMENT.md](../SITE_PACK_DEPLOYMENT.md).

The user interface consumes `idli-result/1`; it must not know the site's raw tables or adapter
field names.

## When this guide requires a schema update

Site onboarding alone should not change the canonical SQL schema. Update:

- `site.json` when identity, AOI roles or named places change;
- `sources.json` when source versions, rights, adapters or crosswalks change;
- `capabilities.json` when operation readiness or method versions change;
- `questions.json` when representative user needs change; and
- the generic canonical schema only when a recurring fact cannot be represented without semantic
  loss.

See [SCHEMA_EVOLUTION.md](SCHEMA_EVOLUTION.md) before changing a generic schema.
