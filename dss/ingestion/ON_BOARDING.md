# Data ingestion and onboarding

Status: entry point for site-pack onboarding and source admission.

Last checked: 2026-07-26.

This directory explains how a place and its source material become an auditable site pack. Start
here when creating a pack, adding a dataset, reviewing an adapter, or deciding whether a schema
must change.

## Choose the relevant guide

| Task | Guide |
|---|---|
| Create a new place or organisation pack | [SITE_ONBOARDING.md](SITE_ONBOARDING.md) |
| Add or update one dataset in an existing pack | [DATASET_ONBOARDING.md](DATASET_ONBOARDING.md) |
| Understand where adapters live and how they execute | [ADAPTERS.md](ADAPTERS.md) |
| Decide whether to reuse or change a schema | [SCHEMA_EVOLUTION.md](SCHEMA_EVOLUTION.md) |
| Author every site-pack file | [../SITE_PACK_AUTHORING.md](../SITE_PACK_AUTHORING.md) |
| Build and operate a deployed pack | [../SITE_PACK_DEPLOYMENT.md](../SITE_PACK_DEPLOYMENT.md) |

The Valparai pack is the real worked example:
[`../sites/valparai/`](../sites/valparai/). The synthetic, sector-neutral compatibility fixture is
[`../sites/valparai_livelihoods/`](../sites/valparai_livelihoods/).

## The invariant

```text
source bytes
  -> immutable source version and rights record
  -> deterministic profile
  -> proposed, reviewed adapter
  -> canonical factual planes
  -> registered analytical capability
  -> idli-result/1
```

An agent or language model may help inspect a source, explain a codebook, suggest canonical names
and draft an adapter. It cannot silently admit evidence. Admission is the reviewed transition
that makes a source version available to shared capabilities.

## Current implementation versus intended service

Today, source admission is an agent-assisted repository workflow:

1. Codex or another operator acquires and profiles a source.
2. It proposes mappings after reading the source, codebook and representative rows.
3. The mappings are reviewed and stored under the source's `adapters` array in
   `dss/sites/<site-id>/sources.json`.
4. `dss/visual_index/build.py` executes those adapters deterministically.
5. Tests and question probes decide whether the changed pack is acceptable.

The build and query paths do not invoke an LLM. What is not yet implemented as one service is the
workflow around them: durable intake, profiling artefacts, proposed mappings, review decisions,
quarantine, admission and incremental publication.

The intended admission service is described in
[DATASET_ONBOARDING.md](DATASET_ONBOARDING.md#the-admission-service). Until it exists, agents must
produce the same artefacts in the repository and must not skip its review boundaries.

## Schemas at a glance

| Layer | Current schema or contract | Owned by |
|---|---|---|
| Site identity and AOI | `visual-site-pack/0.1` in `site.json` | site pack |
| Immutable source registry and adapters | `visual-source-registry/0.1` in `sources.json` | site pack |
| Analysis operations and readiness | `visual-capability-registry/0.1` in `capabilities.json` | site pack/data service |
| Representative question probes | `visual-question-probes/0.1` in `questions.json` | site pack |
| Canonical factual index | SQL schema in `dss/visual_index/build.py` | generic data service |
| User-facing result | `idli-result/1` | producer-consumer contract |
| Paper intake candidate | `paper-source-candidate/1` | intake queue; not admission |

The site-pack schemas are currently versioned prose and implementation contracts, not complete
machine-readable JSON Schemas. Do not interpret the version string as proof that a file has been
validated. Build checks, adapter tests and question probes remain required.

## Three changes that must remain separate

1. **A new source layout** changes a source-specific adapter.
2. **A new scientific or operational calculation** changes or adds a capability.
3. **A new kind of fact that cannot be represented faithfully** changes the canonical schema.

Most new datasets should require only the first. A new column name, metric, file type or site does
not by itself justify a new canonical table.
