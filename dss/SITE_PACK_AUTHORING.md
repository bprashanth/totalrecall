# Authoring a site pack for a new sector

Status: contract guide for agents building a `visual-site-pack/0.1` pack.

Last checked: 2026-07-26

For the end-to-end entry point, including site onboarding, dataset admission, adapter execution
and schema-change decisions, start with
[`ingestion/ON_BOARDING.md`](ingestion/ON_BOARDING.md). This document remains the detailed
site-pack file contract.

This is the checklist an agent must follow to make a new-sector site pack (health, education,
infrastructure, conservation, livelihoods, …) build with the generic
[`dss/visual_index/build.py`](visual_index/build.py) and deploy through Idlisseus **without any
Idlisseus source change**. It was validated by the fully synthetic
[`dss/sites/valparai_livelihoods/`](sites/valparai_livelihoods/) pack, which is the reference
implementation to copy. Deployment (ports, launcher, endpoints) is in
[`SITE_PACK_DEPLOYMENT.md`](SITE_PACK_DEPLOYMENT.md); the overall data-plane design is in
`idlisseus/docs/VISUAL_FIRST_AOI_DATA_DESIGN.md`. The browser-facing boundary is the normative
`idlisseus/dss/VISUAL_RESULT_CONTRACT.md`; the builder's `visual-bundle/0.1` is an intermediate
site-index snapshot, not a UI API.

The synthetic reference and a real pack must be interchangeable at the result boundary. Develop
the UX against synthetic sources, but run the same capability/probe suite against the real pack.
Do not fork renderers, view ids or capability ids by sector. Synthetic results must set
`site.synthetic`, flag their source versions and return the `synthetic-data` limitation.

## Where the pack lives

```text
dss/sites/<site-id>/
├── site.json          identity, aliases, AOI geometry, named points
├── sources.json       source registry: versions, rights, hashes, capabilities, adapters
├── capabilities.json  site-agnostic typed operations and their per-pack readiness
├── questions.json     representative question → first-visual probes
├── README.md          what the pack is; state clearly if any data are synthetic
└── raw/               immutable source files (never edited in place)
    └── <source-id>/   one directory per source, with a README.txt
```

Rules that are not optional:

- The pack lives in this (benchmark) repository. **No site data is ever copied into the
  Idlisseus repository.**
- `raw/` files are immutable. A data update is a **new source version** with a new hash, never an
  in-place edit.
- Register the pack in [`sites/registry.json`](sites/registry.json) with a unique port, public
  model id and endpoint label (copy the `valparai_livelihoods` entry's structure).

## 1. `site.json` — schema `visual-site-pack/0.1`

Required shape (see the reference pack for a complete example):

```jsonc
{
  "schema_version": "visual-site-pack/0.1",
  "site_id": "my_site",                  // stable, snake_case, never reused
  "label": "My Site",
  "organisation_id": "org-id",
  "aliases": ["My Site", "…"],           // what users may call the place
  "target_aoi": {
    "geometry_role": "declared_study_envelope",   // be honest: envelope ≠ property boundary
    "geometry": { "type": "Polygon", "coordinates": [[[lon,lat], …]] },  // inline GeoJSON
    "limitations": ["…"]                 // declare synthetic/approximate geometry here
  },
  "context_aoi": { "geometry_role": "analysis_context", "bbox": [w,s,e,n] },
  "named_points": [
    { "location_id": "stable-id", "label": "…", "latitude": 0, "longitude": 0,
      "uncertainty_m": 100, "source_id": "which-source-claims-this" }
  ]
}
```

Known limits (v0.1 builder — do **not** patch the builder from a pack branch; report gaps):

- Only **inline GeoJSON** in `target_aoi.geometry` is parsed. If your authored original is
  KML/shapefile, keep it under `raw/geometry/` as the immutable original, mirror it inline, and
  record the link in an extra key (extra keys are ignored) — see the reference pack's
  `source_geometry_file`.
- The point-in-AOI test uses the polygon **bbox**, not true point-in-polygon.

## 2. `sources.json` — schema `visual-source-registry/0.1`

One entry per immutable source version:

```jsonc
{
  "source_id": "my-source",
  "title": "…", "doi": null, "url": "…", "publisher": "…",
  "license": "…",                       // real licence; synthetic data → CC0 + say synthetic
  "row_access": {                       // optional; omission safely means schema-only
    "policy": "allow",                  // allow | metadata_only
    "basis": "Why showing source rows is permitted",
    "attribution": "Text that must travel with displayed rows"
  },
  "capabilities": ["inspectable", "mappable", "has_events", …],
  "local_metadata": "raw/my-source/README.txt",
  "adapters": [ … ],
  "content_sha256": "…"                 // authored source-version hash (see v0.1 limit below)
}
```

- **Capabilities are declarations the UI and agent tools trust.** Use the vocabulary already in
  use: `inspectable`, `mappable`, `has_events`, `has_locations`, `has_effort`,
  `has_measurements`, `has_entity_hierarchy`, `has_entity_crosswalk`, and add `synthetic` when
  data are generated. Do not claim a capability the adapters do not deliver.
- **Record a real source-version hash**, but note the current v0.1 limitation: the builder does
  not validate the declared `content_sha256`. It independently hashes only the files referenced
  by `local_metadata`, adapters, lookups, crosswalks and hierarchy, then stores that computed
  digest in `index.sqlite`. Until manifest validation is implemented, test the declared and
  computed file sets explicitly; `integrity: "ok"` does not prove they match.
- **Declare row redistribution explicitly.** The generic `source-rows` capability reads only
  tabular files beside a source's registered local provenance record. It defaults to
  `metadata_only`, showing file names, original columns, DOI, licence and checksum but no row
  values. Set `row_access.policy` to `allow` only after checking the admitted version's terms;
  retain the basis and attribution in the source registry. Synthetic CC0 fixtures are readable
  by default. This policy is independent of whether the builder can index the source.

### Adapter kinds the builder ingests

Adapters map your delimited-text columns onto the generic planes. CSV is the default; set
`delimiter: "\\t"` for Darwin Core and other tab-delimited archives. Dispatch is literal:
`_ingest_<kind>` in `build.py`, so only these kinds exist in v0.1:

**`location`** — named places (facilities, villages, estates, plots):
`path`, `location_id`, `label`, `latitude`, `longitude`, optional `uncertainty_m`,
`properties: [cols…]`.

**`event`** — one row per dated, source-linked occurrence (a census count, a work executed, a
migration event, a case, an enrolment):
`path`, `record_id`, `date` (column) or `date_value` (constant), `entity`, optional
`entity_alias`, `event_type`,
optional `count` (the magnitude column), coordinates either inline (`latitude`/`longitude`,
optional `uncertainty_m`) **or** via `location_lookup` (`path`, `event_key`, `lookup_key`,
`latitude`, `longitude`), plus `properties`. Use `entity_hierarchy: [kingdom, phylum, class,
order, family, genus, species]` when source columns use those canonical names, or an object
mapping canonical levels to source columns. This enriches a canonical entity across sources and
enables broad-group questions without a site-specific group list.

**`effort`** — where/how much you looked; the denominator plane that makes rate and absence
claims legal: `path`, `record_id`, `date`, `method_value`, `effort_value` (column),
`effort_unit`, coordinates via `location_lookup`, `properties` (put population/eligibility
denominators here). Set `distinct_record_id: true` when a source repeats one explicit sampling
event and denominator across multiple observation rows; the first source row is retained and
duplicates of the declared `record_id` are not multiplied. v0.1 does not read inline effort
coordinates or effort `date_parts`.

**`measurement`** — tidy metric series: `path`, `record_id` (col or list of cols),
`date`, `date_value`, or `date_parts: ["year","month"]`; `metrics: {canonical_metric: "unit",
…}`; optional `metric_columns: {canonical_metric: "source_column", …}` when source headings
should not become public metric identifiers; and `properties`. A location may be fixed
(`location_id_value`/`latitude_value`/`longitude_value`) or resolved row by row through the same
`location_lookup` shape used by events. This preserves site/plot identity for generic spatial
metric views. Per-entity measurements still belong in `event` when the row represents a
countable occurrence; do not turn an occurrence into a metric merely to obtain a map.

### Entity extras (source-level, beside `adapters`)

- `hierarchy` — `{path, key, canonical, label, levels: [col, col, …]}` builds the entity tree
  (powers the sunburst view).
- `crosswalks` — `[{path, alias, canonical, label}]` maps verbatim local labels to canonical
  entities **without discarding the original label**. Always carry the source's own vocabulary.

### Choosing what is an entity

Anything users will ask about repeatedly: estates, villages, schemes, occupations, facilities,
crops, species, indicators. Give each a stable code column and a display label; the builder
resolves aliases across sources. Broad/unresolved labels stay as their own aliases — never
silently merge ambiguous names.

## 3. `questions.json` — schema `visual-question-probes/0.1`

5–8 questions **in the language the organisation's staff actually use**, each declaring the
expected `first_visual` and `required_planes`:

```jsonc
{ "id": "…", "question": "…", "first_visual": "metric_time_series",
  "capability_id": "metric-time-series", "arguments": {"metric": "daily_wage"},
  "expected_result_view": "metric-time-series",
  "required_planes": ["measurements", "metric_units", "time_buckets"] }
```

Valid `first_visual` ids (the views `build.py` materialises): `site_overview_map`,
`named_location_map`, `observed_points_map`, `entity_richness_map`, `coverage_and_effort_map`,
`seasonal_effort_normalised_chart`, `metric_time_series`, `hierarchy_sunburst`,
`donor_coverage_and_gate_map` (partial until a feature cube + gates exist),
`value_of_information_map` (blocked until model runs + cost layers exist).

These probes are the pack's acceptance test: coverage is measured against them, and they seed
the next acquisition pass. v0.1 warning: the builder does not yet evaluate `required_planes`
from `questions.json`; it inserts a fixed view-readiness list. Treat the probes as authored
requirements and test them separately until readiness is computed from actual planes.

For probes supported by the typed result service, also declare `capability_id`, JSON `arguments`
and `expected_result_view` (or `expected_status: "blocked"` for an admitted missing capability).
This allows the same acceptance runner and UX to exercise a synthetic pack and a real pack
without parsing benchmark-specific question language.

## Contract with Idlisseus

The pack and Idlisseus may evolve in parallel only across this boundary:

```text
site pack
  -> benchmark-owned index, connectors and generic capabilities
  -> idli-result/1
  -> Idlisseus renderers and interaction
```

- The pack owns source meaning, canonical identifiers, evidence classes, denominators,
  transformations, model/gate results, limitations and immutable drill-down data.
- Idlisseus owns layout, responsive behaviour, renderer libraries, loading/empty/partial states,
  evidence-class presentation and conversation controls.
- A capability is a site-agnostic analytical operation with typed arguments and typed result
  views. A source adapter supplies its inputs; it is not a UI component.
- Declare those operations in `capabilities.json` with stable `capability_id`, semantic version,
  JSON input schema, output views, required/optional planes, latency class, evidence classes and
  `ready`, `partial` or `blocked` availability. The Valparai pack is the first real example.
- The benchmark query service translates indexed products into `idli-result/1`. Do not expose
  `visual_bundle.json` directly or make the UI understand pack-specific tables.
- Large points, rows, tiles and documents stay behind immutable, authorised `data_ref` handles.
- Add a shared fixture before relying on a new result field or renderer grammar.

Fable can use synthetic fixtures to build the UX while benchmark agents add real sources and
capabilities. Most source, adapter, index, connector, embedding or model changes require no
Idlisseus change. Coordinate only for a breaking result-contract change, a new renderer grammar,
or a new access-control/reference interaction.

Producer-to-consumer changes are proposed through
[`integration/`](integration/README.md). Totalrecall writes proposals there; the Idlisseus owner
writes responses in its own repository. Do not patch consumer renderers from a pack-development
branch.

## 4. Build and verify

```bash
cd <totalrecall>
python3 dss/visual_index/build.py --site-pack dss/sites/<site-id> --output /tmp/<site-id>-index
```

`build_report.json` currently reports SQLite `PRAGMA integrity_check`, not full pack conformance.
Converged means that check is `ok`, counts and source digests match independent expectations,
adapter-level tests pass, and every question probe is supported by the planes it declares.
Then inspect `visual_bundle.json`, but do not rely on its fixed v0.1 view-readiness list as proof.
Iterate on **pack files only**. If the builder genuinely cannot express something, stop and
report the exact adapter gap — do not fork or patch `build.py` per pack; gaps are fixed once,
generically, for all packs.

Known semantic and presentation limits in v0.1 output (do not work around them in pack data):
`annual_rainfall` is a literal `metric='rainfall'` query (empty for other sectors);
`effort_by_season` labels all effort `km` regardless of declared unit; all packs receive the same
fixed readiness list; the point-in-AOI test uses a bounding box; declared source hashes and privacy
policies are not enforced; and `preview.png` carries a hardcoded title. These are generic builder
gaps to fix once, not evidence that a pack is invalid.

## 5. Register and deploy

1. Add the site to `sites/registry.json`: `status: "visual-index-poc"`, `site_pack` path, and a
   `suggested_deployment` with a **unique** port, `public_model` and `endpoint_name`.
2. Deploy per [`SITE_PACK_DEPLOYMENT.md`](SITE_PACK_DEPLOYMENT.md): one bridge process per
   site, own state directory, never share state between packs.
3. Run the deployment validation checklist there (health, alias query, drill-down, audit,
   cross-site leakage).

## What you must never do

- Copy site data into Idlisseus, or hard-code your sector's vocabulary into Idlisseus UI code.
- Edit raw files in place, or let a failed source silently substitute a different one.
- Claim capabilities the adapters don't deliver, or present synthetic/model output as observed.
- Ship rate, absence or trend claims without an effort/exposure denominator in the pack.
- Promote a study bounding box to a property boundary via `geometry_role`.
- Put people-identifying rows into serving products: livelihoods/health/education packs must
  filter restricted rows and mask sensitive coordinates **before** the serving build, not in
  browser styling.
