# Fieldnote data pipeline

## The short version

Fieldnote is not a static site and it does not ask a language model to read every source again for
every question. It has two speeds:

1. a built **field atlas** for immediate orientation and common visual queries; and
2. a **conversation and evidence path** for resolving a new question, selecting a declared
   operation, and returning an audited result.

The current Valparai proof of concept builds the atlas from 21 admitted source versions:

```text
immutable source files
    -> source-specific reviewed adapters
    -> canonical factual index (SQLite in the POC)
    -> typed analytical capabilities
    -> idli-result/1 + immutable GeoJSON/JSON handles
    -> generic Fieldnote maps and figures
```

The full, sector-neutral design is in
[`../ecology_memory/DATA_AND_ANALYSIS_STRATEGY.md`](../ecology_memory/DATA_AND_ANALYSIS_STRATEGY.md).
This note explains how that design is used by Fieldnote today.

## Four product layers

### 1. Field atlas

The opening page is built from compact, visual-ready summaries. It can orient a person before they
formulate a precise question. The public bundle contains aggregate cells, seasonal surfaces,
plot-level indicators, acoustic matrices, source coverage and declared limitations.

This layer is sector-neutral. A livelihoods pack could open with settlements and indicators; a
health pack with facilities and coverage. Valparai happens to open with records, survey effort and
environmental surfaces.

### 2. Conversation agent

Codex runs in the existing Hermes container. It interprets ordinary language, resolves the user's
subject against the site's vocabulary, chooses a registered capability and asks follow-up
questions when a binding is ambiguous.

It should not calculate the answer from model memory. Its useful jobs are intent, composition,
plain-language explanation and deciding what to ask next.

### 3. Scientific evidence

Deterministic services query the pinned site index. A capability has typed arguments, required
factual planes, evidence semantics, limitations and allowed follow-up actions. For example:

```text
"Where do elephant and leopard records overlap?"
    -> co-occurrence-map(subjects=["elephant", "leopard"])
    -> observed cells + derived shared cells + source versions + limitations
```

The 9B algebra model is not used for that query. It is invoked only through
`compile-scientific-algebra-9b` when a question needs the scientific algebra path. Simple maps and
summaries should take the shorter typed-capability path.

### 4. Visual presentation

The result envelope tells Fieldnote what a visual means; large payloads are fetched by immutable
handle. Fieldnote now draws generic GeoJSON points, lines, cells and polygons, displays evidence
semantics and limitations, and executes typed result actions. R receives bounded rows for
reproducible statistical figures; it does not search or reinterpret the site index.

## What is actually stored

Containers are preserved as containers. CSV, Excel, KML, PDF, raster, audio, image and video are
not analytical meanings.

Original files remain immutable outside the serving database, with source identity, rights,
version and checksum. Small facts useful for filtering, joining and grouping enter canonical
tables:

| Canonical fact | What it holds |
|---|---|
| `sources` | version, rights, title and digest |
| `entities`, `entity_aliases` | stable named subjects and source-backed names |
| `locations` | plots, routes, stations and named places |
| `events` | dated, source-linked records or detections |
| `effort` | visits, minutes, trap-nights, area or other denominators |
| `measurements` | values, metrics and units |
| `interactions` | relations explicitly reported by a source |
| `cells`, `cell_features` | spatial support and aligned environmental features |
| `matrix_values` | values over two dimensions, such as hour by frequency band |

SQLite is an implementation choice for this POC, not the contract. Large GeoJSON, rasters, papers,
media and model artefacts stay outside SQL and are addressed by handles. A later index can use
PostGIS, DuckDB, GeoParquet, a vector store or a tile service without changing `idli-result/1`.

The present Valparai index contains, at this checkpoint:

- 21 admitted source versions;
- 45,328 events and 974 effort rows;
- 71,595 measurements and 5,622 source-reported interactions;
- 28,764 cell features and 132,096 matrix values;
- 1,145 canonical entities across 302 indexed cells.

These totals describe indexed rows, not ecological abundance.

## How a source becomes queryable

Every admitted source follows the same lifecycle:

1. **Acquire** an exact API, DOI, repository or supplied-file version.
2. **Preserve** its bytes, licence, retrieval metadata and checksum.
3. **Profile** sheets, fields, units, coordinates, dates, identifiers and missingness.
4. **Propose a mapping** from source fields to canonical facts. A model may help here.
5. **Review and validate** mappings against codebooks, representative rows, ranges and joins.
6. **Persist an adapter** in the site pack so the mapping is not rediscovered at query time.
7. **Build** facts and visual-ready summaries while retaining source-row lineage.
8. **Quarantine** invalid rows and report failures instead of silently coercing them.
9. **Probe** the resulting capabilities with representative questions.

A camera-trap workbook, for example, normally produces locations, deployment effort, detection
events and media references. It does not need a `camera_trap_excel` table. Occupancy modelling
would be a separate capability because it requires repeat occasions and detection histories.

## What is special about conservation data

The pipeline itself is general. Conservation changes the validity rules and common factual
relationships:

- a record is presence evidence, while an unrecorded cell is not absence;
- survey effort and protocol must accompany claims about coverage;
- taxonomy, common names and ranks need source-backed resolution;
- place, date, coordinate uncertainty and spatial grain affect every join;
- co-occurrence is not interaction or contemporaneous presence;
- environmental rasters are predictors or context, not observations;
- donor-to-target models need transfer gates and visible uncertainty;
- sensitive records may require coordinate reduction or access controls; and
- acoustic, image and video assets need media indexes, but are optional modalities rather than
  the foundation of the architecture.

Another sector would keep the same source, fact, capability and result pipeline while replacing
these validity rules with its own.

## Skills used today

The bridge currently exposes a mixed catalogue of 29 skills. The verified Fieldnote overlap flow
uses only:

```text
Codex -> visual-result -> co-occurrence-map -> idli-result/1 -> Fieldnote
```

The newer `visual-*` skills are thin agent interfaces to the typed data architecture:

- `visual-result` runs a registered map, chart or summary capability;
- `visual-explain` traces one mark back to source rows;
- `visual-upload` profiles a user table without admitting it globally;
- `visual-estimate` lists valid targets and runs gated estimates;
- `visual-earth-layer` renders declared earth-observation layers.

Other existing skills remain useful for discovery and longer investigations: literature and
dataset discovery, dataset inspection, protocol generation, evidence coverage, the 9B algebra
compiler, dashboards and model requests.

The catalogue also still contains older EBTL-specific skills. They were not used in the verified
Valparai overlap result. Their presence is migration debt: site-specific skills should eventually
be supplied only by the relevant resource pack, while general connectors and capabilities remain
shared.

## How the pipeline should evolve

The interface is already dynamic, but formal pack admission is not yet an unattended service.
Adding a source currently means acquiring it, updating the source registry and adapter, rebuilding
the index, running tests, and restarting or refreshing the local bridge.

The next ingestion service should automate the safe parts:

```text
watch/API/upload
  -> immutable staging + checksum
  -> container profiling and text/table/media extraction
  -> proposed canonical mappings and entity matches
  -> deterministic validation + human review for ambiguity
  -> admitted source version
  -> incremental index/materialised visual rebuild
  -> capability probes
  -> publish new pack digest
```

Models may suggest field meanings, paper methods and entity matches. Deterministic checks and an
explicit admission decision must control what becomes shared evidence. New file layouts usually
need an adapter; a new canonical fact is warranted only when existing facts lose meaning; a new
capability is warranted only for a genuinely new reproducible analysis.

That boundary lets the system learn new sources without turning every live answer into improvised
ETL.
