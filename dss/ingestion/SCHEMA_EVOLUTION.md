# Schema ownership and evolution

Status: decision guide for changing site-pack, canonical and result schemas.

## The schemas are layered

### Pack schemas

- `visual-site-pack/0.1`: identity, aliases, AOI roles and named points.
- `visual-source-registry/0.1`: immutable source versions, rights, crosswalks and adapters.
- `visual-capability-registry/0.1`: analytical operations and per-pack readiness.
- `visual-question-probes/0.1`: representative questions and expected results.

These are owned by Totalrecall site-pack authoring.

### Canonical factual schema

The v0.1 SQL definition in `dss/visual_index/build.py` contains:

- `sources`;
- `entities`, `entity_aliases`;
- `locations`;
- `events`;
- `effort`;
- `measurements`, `metric_definitions`;
- `interactions`;
- `cells`, `cell_features`;
- `matrix_values`; and
- materialised query tables and view readiness.

It is a rebuildable serving index, not the immutable source of truth.

### Result schema

`idli-result/1` is the producer-consumer wire contract. Canonical tables must not leak through it.
Large rows, geometries and media travel through immutable `data_ref` handles.

## Do not update the canonical schema for these

- A new site.
- A differently named CSV column.
- A new metric representable as metric/value/unit rows.
- A new entity or alias.
- A new source-specific category preserved in properties.
- A new file container that can be extracted to existing facts.
- A new calculation over existing facts.
- A new visual arrangement of an existing result.

Use site configuration, an adapter, a reusable extractor, a capability or a renderer respectively.

## Consider a canonical schema update when

A recurring fact cannot be represented without losing identity, relationship, denominator,
provenance, uncertainty or access semantics.

Examples:

- repeated measurements must link formally to the same individual subject;
- media needs authorised asset identity and links to events/subjects;
- documents need section/chunk lineage and method references;
- one location must be reconciled across several source authorities;
- intervals or categorical measurements cannot be represented honestly as scalar values; or
- a relationship needs typed roles beyond a subject-object interaction.

The current individual-tree gap is a concrete candidate. A generic extension could add:

```text
subjects(
  subject_id,
  source_id,
  source_subject_key,
  entity_id,
  location_id,
  identity_scope,
  properties_json
)
```

and nullable `subject_id`/`event_id` links from measurements. The exact design needs a migration
and conformance proposal; do not add `tree_id` only to one site's measurement table.

## Change process

1. Write the fact that cannot be preserved and show representative sources from more than one
   pack or likely reuse case.
2. Demonstrate why adapters, properties and existing planes lose necessary meaning.
3. Propose the smallest generic schema and identity rules.
4. Specify source lineage, privacy, evidence-class and null behaviour.
5. Update the builder and any rebuild/migration tooling.
6. Add adapter validation and fixtures for populated, empty, partial and invalid cases.
7. Rebuild at least the real Valparai and synthetic livelihoods packs.
8. Verify existing `idli-result/1` outputs remain compatible.
9. If the wire contract must change, use the producer-consumer proposal mechanism before changing
   a UI.
10. Bump the relevant schema version when compatibility rules require it.

## Compatibility rules

- Adding an optional adapter field that old builders ignore safely is normally additive.
- Changing the meaning of an existing field is breaking even when its JSON type stays the same.
- Adding a nullable canonical column still requires all pack builds and services to be tested.
- Renaming a metric is a data migration because queries and result IDs may depend on it.
- Adding a capability is not a canonical schema change.
- Adding a result view using existing `idli-result/1` grammar is not necessarily a wire-schema
  change.
- Removing a source, field, plane or result meaning requires an explicit breaking version and
  transition plan.

## Current hardcoded edges to make visible

- Site/source/capability/question contracts do not yet have complete checked-in JSON Schemas.
- Adapter dispatch is a literal set of Python methods in `build.py`.
- Metric construct compatibility is governed by reviewed naming and units, not a global ontology.
- Locations are source-scoped; cross-source place identity is not first class.
- Individuals are represented only through source record keys and lineage.
- Documents and media are not yet first-class canonical indexes.

These are reasons to improve the shared architecture, not reasons for site-specific schema forks.
