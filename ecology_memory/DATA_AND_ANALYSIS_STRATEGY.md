# Data and analysis strategy for place-based evidence

Status: working architecture and critique document.

Last checked: 2026-07-25.

This document explains how an organisation's heterogeneous source material becomes queryable,
auditable analysis and visual results. It is deliberately end to end: acquisition, immutable
storage, ingestion, canonical facts, document and media retrieval, analytical operations, agent
invocation, presentation, and the places where the current proof of concept is still hardcoded.

The central distinction is between two planes:

1. the **data plane**, which preserves and indexes what sources actually contain; and
2. the **analysis plane**, which declares the operations that may legally be performed over those
   facts.

These are architectural planes, not two database tables. A source may populate several factual
tables, and one analytical operation may use several factual tables.

## 1. The complete flow

```text
files, APIs, databases, papers, rasters, audio, images and video
                              |
                    source acquisition connector
                              |
        immutable source version + manifest + rights + checksums
                              |
             profiling, extraction and reviewed source adapter
                              |
          +-------------------+--------------------+
          |                                        |
 canonical factual index                  document/media indexes
 SQL-sized facts and joins                text chunks, binaries, rasters,
                                          embeddings and asset metadata
          +-------------------+--------------------+
                              |
                registered analytical capability
                  typed arguments + required facts
                  method + gates + claim limits
                              |
                     idli-result/1 envelope
                  + immutable payload handles
                              |
                 generic map/chart/table/dashboard
                              |
            agent explanation, audit and next question
```

Language reasoning appears at two bounded points:

- before execution, to interpret the user's intent and bind it to a registered operation and
  canonical arguments; and
- after execution, to explain the deterministic result in the user's language.

It does not replace source admission, deterministic computation, evidence labelling, failed gates
or result lineage.

## 2. Source containers are not analytical meanings

CSV, Excel, JSON, PDF, GeoTIFF, KML, WAV, JPEG and MP4 describe containers. They do not tell us
what the records mean.

An Excel workbook might contain:

- camera locations;
- camera deployment periods;
- animal detections;
- vegetation measurements;
- a codebook; and
- filenames of associated photographs.

Those sheets should not be forced into one `camera_trap_excel` table. Their contents map to
reusable factual shapes.

The main canonical shapes currently used by the visual index are:

| Factual shape | Meaning | Examples |
|---|---|---|
| `sources` | immutable source identity and rights | DOI snapshot, repository commit, field workbook |
| `entities` and `entity_aliases` | stable things people ask about | taxon, habitat class, programme, indicator |
| `locations` | named or coded places | estate, plot, recorder station, camera station |
| `events` | dated source-linked occurrences | detection, point-count record, regeneration record |
| `effort` | how much observation or exposure occurred | trap-nights, point-count minutes, plot area |
| `measurements` | tidy values with units | rainfall, canopy cover, richness estimate |
| `interactions` | source-declared subject-object relation | visitor–tree observation, seed-experiment association |
| `cells` and `cell_features` | spatial support and predictors | NDVI, elevation, AlphaEarth axes |
| `matrix_values` | a numeric value over two ordered dimensions | hour × frequency acoustic-space use |

These shapes are primitives, not an exhaustive list of user questions. A small set of faithful
primitives can support a much larger set of compositions.

Two additional indexes are part of the intended strategy but are not yet first-class tables in
the current POC:

- a **document index** for paper sections, reports, methods, codebooks and their source locations;
  and
- a **media index** for audio, images and video, including time, place, linked event, derived
  annotations, access policy and immutable asset handle.

Until those indexes exist, document method cards live as source-linked JSON and media filenames
can only survive as source metadata or event properties. That is a current implementation gap,
not a reason to place large binaries inside SQLite.

## 3. What belongs in SQL

SQL is the serving index for facts that benefit from filtering, joining, grouping and lineage:

- stable identifiers;
- source and source-row references;
- canonical entity and alias mappings;
- dates and time buckets;
- coordinates, cells and uncertainty;
- numeric values and units;
- explicit denominators;
- categorical properties needed for declared comparisons;
- links between events, places, media and sources; and
- compact materialised aggregates used repeatedly by visuals.

SQL should not become the only archive. The following remain outside it and are addressed through
immutable references:

- original workbooks and delimited files;
- PDFs and complete paper text;
- WAV, JPEG, TIFF and MP4 assets;
- large rasters and tile pyramids;
- model weights;
- executable notebooks and method implementations; and
- large result payloads such as GeoJSON point sets.

SQLite is sufficient for the current feasibility implementation. The logical contract does not
depend on SQLite: a later build can use DuckDB, PostgreSQL/PostGIS, GeoParquet, an object store,
a vector index or a tile service while preserving the same factual meanings and result contract.

### Immutable originals and mutable indexes

The original source version is immutable. A changed upstream dataset is a new admitted version
with a new manifest and digest.

The serving index is disposable and reproducible. It may be rebuilt whenever adapters,
capabilities or admitted source versions change. Every result records the pack/build identity and
the source versions it used.

## 4. Ingesting a new source

Ingestion has nine stages.

1. **Acquire.** A connector downloads or snapshots the exact source version. It handles protocol,
   authentication, pagination, retry, rate limits and upstream versioning.
2. **Preserve.** Store the unmodified bytes, source URL or DOI, licence, retrieval time, checksum
   and any access restrictions.
3. **Profile.** Inspect sheets/files, columns, types, missingness, sample values, units, coordinate
   candidates, dates, identifiers and referenced assets.
4. **Propose meanings.** A semantic matcher or language model may propose that `SpeciesName`
   identifies an entity, `CamID` identifies a location and `TrapNights` is effort.
5. **Validate.** Check those proposals against codebooks, units, ranges, joins, duplicates and
   representative rows. Ambiguous mappings remain unresolved.
6. **Persist an adapter.** Record the accepted column-to-plane mapping as versioned configuration
   or reusable code. Do not ask a model to rediscover it on every query.
7. **Build.** Populate canonical facts and derived indexes while retaining source row lineage.
8. **Quarantine.** Invalid rows, failed joins and unit conflicts must be counted and reported;
   they must not disappear or be silently coerced.
9. **Probe.** Run representative questions and capability tests before claiming that the source
   supports an operation.

Models are useful during profiling and mapping because source schemas vary. Their proposals become
trusted only after validation and persistence. This makes ingestion flexible without making every
answer depend on an improvised parser.

### Example: camera-trap Excel

Assume the workbook contains these columns:

```text
Camera_ID, Latitude, Longitude, Deployment_Start, Deployment_End,
Trap_Nights, Scientific_Name, Detection_Time, Count, Media_File
```

A reviewed adapter would produce:

```text
Camera_ID + coordinates                    -> locations
deployment dates + Trap_Nights             -> effort
Scientific_Name + Detection_Time + Count   -> events
Media_File                                 -> media asset linked to the event
original workbook                          -> immutable source object
```

The acquisition method remains `camera trap` in source and effort metadata. It does not require a
camera-specific map table.

If the workbook is merely attached to a conversation, the upload service first stores and
profiles it. It does not silently promote user data into the shared admitted index. Formal
admission requires the source process above.

### Example: Valparai acoustic material

The admitted acoustic source contains site coordinates and a table whose natural shape is:

```text
recorder site × hour × frequency bin -> within-site acoustic-space-use value
```

The site metadata becomes `locations`; aggregate detections and richness values become
`measurements`; the two-dimensional numeric surface becomes `matrix_values`. The source's
restoration category is retained as source metadata. No raw WAV file was present in the admitted
snapshot, so the pack does not claim that audio can be played.

The choice of a matrix was based on the shape of the supplied values, not on a hardcoded rule that
all sound is a matrix. A future WAV collection would enter the media index, while derived
spectrogram bins or acoustic indices could enter matrices or measurements.

### Example: satellite and other raster products

The original raster or provider asset remains outside SQL. Values sampled or aggregated to the
pack's declared cells enter `cell_features` with:

- feature identifier and human label;
- cell and year;
- value and unit;
- evidence class;
- source asset;
- aggregation and scale; and
- missing-support information.

This allows a generic cell-feature map while retaining the raster lineage. It does not turn a
remote-sensing predictor into an occurrence record.

### Example: papers and protocols

A paper can contribute several distinct products:

- bibliographic and searchable text chunks in a document index;
- downloadable or structured supplementary data through an ordinary source adapter;
- a method card describing inputs, formulae, gates, uncertainty and claim limits; and
- an implementation reference or tested reusable analytical operation.

A paper mentioning a species does not become a local occurrence. A method described in a paper
does not become an executable capability until its input contract and implementation have been
tested.

## 5. The analysis plane

A capability is a site-agnostic, typed analytical operation over admitted facts. It declares:

- a stable capability id and semantic version;
- an input schema;
- required and optional factual planes;
- output view grammar;
- evidence classes;
- latency class;
- availability: ready, partial or blocked;
- method and implementation identity where relevant; and
- gates, limitations and legal claims.

Examples from the Valparai pack include:

```text
entity-record-map(entity)
coverage-versus-effort()
group-record-map(rank, group)
metric-time-series(metric)
interaction-map(interaction_type, entity?)
cell-feature-map(feature_id, year, scope)
matrix-profile(source_id, matrix_id, category_property?)
seasonal-surface-profile(series_id, year, scope)
gated-transfer(entity, donor_scope, target_scope)
```

Capabilities are not buckets containing every possible sentence. They are reusable computations.
Many questions become a capability plus bound arguments:

```text
"Where have lion-tailed macaques been recorded?"
    -> entity-record-map(entity="Macaca silenus")

"Where did people actually survey, and where are there only no records?"
    -> coverage-versus-effort()

"How does greenness vary through the year?"
    -> seasonal-surface-profile(
         series_id="sentinel2-ndvi-monthly", year=2024, scope="context")
```

One question may require several capability runs. For example, "Could the surrounding records
help us decide where to survey this site?" may first run an observed record map, then coverage
versus effort, then a gated transfer. The agent owns that dialogue and composition; each factual
result remains separately auditable.

### Presence map or camera-trap capability?

A camera detection is an event collected by a camera-trap method. Mapping it normally uses the
generic `entity-record-map`, optionally filtered by method or source.

A new specialised operation is justified when the analytical method changes:

- detection rate per trap-night needs events plus effort;
- activity distribution needs timestamps plus observation support;
- occupancy modelling needs repeated sampling occasions and detection histories;
- capture–recapture needs defensible individual identity.

Those should be generic method capabilities such as `detection-history-occupancy`, not
`valparai-camera-map`. They should refuse to run when their required design is absent.

## 6. When new data requires code

Use this decision sequence.

### A. Is it only a new container?

An unfamiliar Excel layout, another CSV spelling, a new API response or a GeoPackage does not
automatically require a new factual plane or capability.

Write or configure:

- an acquisition connector if retrieval mechanics are new; and
- an adapter if source fields need a new mapping into existing facts.

No UI change should be needed.

### B. Is it the same meaning but a new source vocabulary?

Map source vocabulary to canonical concepts through a reviewed crosswalk or concept catalogue.
Retain the source's verbatim value. Do not enumerate every phrase a user might say.

At query time, language or semantic retrieval resolves the user's phrase to a canonical concept.
After resolution, deterministic code uses the canonical identifier. If two candidates remain
plausible, the agent asks.

### C. Is it a genuinely new factual relationship?

Add or extend a canonical plane only if existing facts would lose essential semantics. Video is
not itself a new analytical plane; it is a media container. A temporally bounded annotated segment
linked to several detected entities may require generic media, segment and annotation facts.

A new factual plane requires:

- schema and lineage design;
- a generic adapter contract;
- quarantine and integrity tests;
- at least two plausible source shapes where possible; and
- a clear account of why existing planes cannot represent it faithfully.

### D. Is it a new computation?

Add a capability when users need a materially different reproducible operation, not for every
wording or entity.

A new capability requires:

- typed arguments;
- required factual planes;
- deterministic implementation or a versioned model;
- test fixtures;
- evidence labels and limitations;
- gates and failure behaviour;
- output using an existing visual grammar where possible; and
- representative natural-language probes.

### E. Is it only a new visual form?

First try an existing generic grammar: map, time series, matrix, distribution, network, table,
dashboard or document/media viewer. A new consumer renderer requires a producer-to-consumer
proposal and a shared fixture. Sector or species names must not enter Idlisseus dispatch code.

## 7. Skill versus capability

The terms overlap in ordinary language but have different responsibilities here.

### Capability

A capability is the stable computation and result contract. It should be callable without a
conversation model:

```json
{
  "capability_id": "entity-record-map",
  "arguments": {"entity": "lion-tailed macaque"}
}
```

The result service validates arguments, runs a fixed implementation against a pinned index and
stores the result.

### Skill

A skill is an agent-facing instruction/tool surface. It explains:

- when the capability is appropriate;
- which arguments must be resolved;
- what must not be inferred;
- how to relay its evidence and limitations;
- what follow-up to offer; and
- how to recover from an ambiguity or failed gate.

A skill may wrap one capability, compose several capabilities, call a connector, inspect a
document or record a model request. The analytical truth still comes from capabilities and
source-bound computations.

Do not create one skill per species, site or spreadsheet. Prefer generic skills such as:

- inspect admitted local evidence;
- map records for a resolved entity;
- compare observation coverage with effort;
- inspect an analysis method;
- run a gated transfer;
- map a data request; and
- publish selected audited results as a dashboard.

## 8. How the agent invokes the analysis plane

The intended dialogue path is:

1. The outer agent understands the user's ordinary language and the current conversation.
2. It consults the pinned site's capability catalogue and concept/entity catalogue.
3. It resolves phrases such as "macaques", "rain", "camera records" or "our site" into candidate
   typed bindings.
4. It asks a short clarification if the binding would materially change the answer.
5. It invokes one registered skill or capability with explicit arguments.
6. Deterministic code validates the argument schema and required factual planes.
7. The operation either returns a result, a partial result, a failed gate or a structured gap.
8. The agent explains that result and offers a bounded next action.

The result service deliberately does not interpret free text. This prevents an unreviewed phrase
from becoming arbitrary SQL. It receives only registered capability ids and typed arguments.

The outer agent may use model knowledge to:

- understand intent;
- propose search terms;
- rank candidate canonical concepts;
- explain a returned result; and
- decide which explicit follow-up to offer.

Model knowledge alone may not create:

- a local record;
- a source relation;
- a measurement;
- an absence claim;
- a passed model gate; or
- a trend.

## 9. `idli-result/1` and immutable payload handles

`idli-result/1` is the boundary between analysis producers and the Idlisseus presentation layer.
It contains:

- stable result, request, revision and audit ids;
- the original question, resolved question and typed bindings;
- a concise answer;
- evidence classes;
- visual specifications;
- limitations and failed gates;
- valid next actions;
- source versions and capability runs; and
- references to large result data.

Large point collections, chart rows, GeoJSON, raster images and drill-down tables are stored
separately. A result layer carries a handle, media type and digest:

```json
{
  "data_ref": {
    "kind": "result_data",
    "handle": "observed-points",
    "media_type": "application/geo+json",
    "digest": "sha256..."
  }
}
```

The browser retrieves the authorised handle through Idlisseus. The digest detects silent
mutation. A new source or computation produces a new stored result identity rather than changing
the points behind an old audit.

This contract keeps the browser independent of producer storage. A map layer can originate from
SQLite rows, GeoParquet, a raster service or a model, while the UI still receives the same
evidence and visual grammar.

## 10. Current hardcoded edges

The architecture is more general than the current POC. Another agent evaluating it should inspect
these explicit rigidity points.

### In Totalrecall

1. `dss/visual_index/build.py` contains a literal SQLite schema.
2. Adapter dispatch is implemented as `_ingest_<kind>` methods. An unknown adapter kind cannot be
   admitted through configuration alone.
3. Several planes support delimited text directly; arbitrary workbook, media, document and raster
   admission is not yet uniform.
4. Quarantine and adapter-quality reports are not yet uniform across all source types.
5. Entity and metric resolution use finite aliases and normalisation in important paths. A full
   producer-owned semantic concept catalogue and ambiguity threshold are still needed.
6. `dss/visual_index/result_service.py` uses a fixed capability-to-function dispatch table.
   `capabilities.json` declares an operation, but a ready operation still needs a generic
   implementation in code.
7. Some capability implementations know current table/property conventions. Those conventions
   need tests proving that a second sector or source can use them without special names.
8. SQLite and JSON payload state are local-process POC choices, not a production authorisation or
   multi-tenant design.

### In the Codex-native bridge

1. `ecology_memory/integration/codex_native/server.py` builds a runtime skill catalogue from
   static descriptions plus the pinned pack's capability registry.
2. Some broad-intent routes use deterministic phrase checks—for example site orientation and
   uploaded-file handling—so important safety flows do not depend entirely on model compliance.
3. For most detailed questions, Codex selects a skill and binds arguments from the catalogue.
4. The bridge refuses legacy site-bound skills when a visual site pack is pinned unless they have
   been explicitly parameterised.
5. Algebra/9B is available for scientific compilation, but it does not own site selection or
   silently retrieve arbitrary data. Codex owns dialogue, explicit data discovery and retries.
6. The bridge currently combines older ecology operational skills and the newer typed result
   capabilities. This is useful for migration but should not become two competing truth paths.

### In Idlisseus

1. Idlisseus registers a separate endpoint per site pack in the current POC.
2. It proxies capability, result, payload and explain requests to the selected endpoint.
3. It recognizes model ids beginning with `idli-insight-` as site bridge sessions.
4. Renderers are generic by result view and style metadata. A new visual grammar still requires a
   versioned fixture and consumer implementation.
5. Source data and pack-specific vocabulary must not be copied into Idlisseus.

These hardcoded edges are acceptable only when they implement stable contracts or safety checks.
They are defects when they encode one site's names, one species, one source's column spellings or
one benchmark question.

## 11. End-to-end ecology examples

### "Where have lion-tailed macaques been recorded?"

```text
agent resolves common/scientific entity
  -> entity-record-map
  -> entity_aliases + events + cells
  -> observed point GeoJSON + source rows
  -> idli-result/1 observed-points map
```

No modelled distribution is implied.

### "There are no venomous snake records here. Where is there data?"

```text
local entity-record-map
  -> explicit empty target result, not absence
agent offers wider authorised scope
  -> wider occurrence connector or indexed donor data
  -> observed donor map + coverage/effort
optional gated-transfer
  -> observed donors, supported target cells, unsupported cells and failed/passed gates
```

Collecting local data is not the only fallback. The first useful fallback may be to show where
trusted data already exists and test whether it transfers.

### "Are these restoration plots recovering?"

```text
agent resolves which outcome the user means
  -> plot-indicator-profile for a declared metric
  -> measurements + metric definition + locations + source category
  -> map + category distribution + method/denominator
optional time-series capability if repeated measurements exist
```

A difference between source categories remains descriptive unless an admitted inferential design
supports a treatment-effect claim.

### "When is acoustic activity strongest?"

```text
matrix-profile(source, acoustic-space-use matrix)
  -> matrix_values + recorder locations
  -> hour × frequency matrix + site coverage map
```

The answer is about the source's acoustic-space-use index. It is not automatically a bird
abundance result and cannot offer raw audio when none was admitted.

### "Where should we collect the next observations?"

```text
observed records + effort + spatial features
  -> uncertainty or transfer operation
  -> gate checks
  -> value-of-information operation only if uncertainty and action costs exist
  -> designed collection points on a map
```

Without a versioned uncertainty surface and action-cost layer, the system should return a blocked
capability or a clearly labelled spatially balanced design—not pretend to maximise return on
investment.

## 12. Ownership and change protocol

Totalrecall owns:

- source acquisition and immutable data;
- adapters and canonical meanings;
- indexes and concept catalogues;
- analytical implementations and method cards;
- evidence labels, gates, limitations and payloads; and
- `idli-result/1` production.

Idlisseus owns:

- endpoint selection and session transport;
- activity and audit presentation;
- maps, charts, tables, dashboards and media viewers;
- responsive, partial and empty states; and
- authorised proxy access to payload handles.

Producer changes that stay inside an existing result contract need no Idlisseus change. A new
renderer grammar, contract field or payload interaction is proposed through
`dss/integration/proposals/`; Idlisseus records its response in its own repository.

## 13. Questions for architectural review

The next design review should test these issues explicitly:

1. Which minimal additional factual planes are needed for documents, media, sampling occasions,
   interventions and model runs?
2. Can the same camera-trap, household-survey and facility-inspection fixtures use the proposed
   media/annotation plane without sector-specific fields?
3. What confidence and ambiguity contract should the producer-owned concept resolver expose to
   the agent?
4. Which current `result_service.py` operations are genuinely generic, and which still encode a
   Valparai source convention?
5. Where should capability composition live: agent plan, a typed workflow layer, or both?
6. How are access policy and coordinate sensitivity enforced before payload handles reach the
   browser?
7. What minimum quarantine report makes a source build auditable?
8. When is deterministic phrase routing a safety boundary, and when is it unnecessary rigidity?
9. How do document/media search results become evidence inputs without being mistaken for local
   observations?
10. What production storage changes can occur without changing `idli-result/1`?

## 14. Files that define the current implementation

- `dss/SITE_PACK_AUTHORING.md` — source-pack and producer/consumer contract.
- `dss/sites/valparai/` — real pack, source adapters, capability declarations and probes.
- `dss/visual_index/build.py` — current canonical schema and ingestion implementations.
- `dss/visual_index/result_service.py` — typed capability execution and immutable results.
- `dss/visual_index/explain_service.py` — deterministic mark-to-source lineage.
- `dss/visual_index/upload_service.py` — conversation-scoped Excel/CSV profiling.
- `dss/integration/README.md` — producer-to-consumer proposal exchange.
- `ecology_memory/integration/codex_native/server.py` — agent-facing bridge and skill catalogue.
- `ecology_memory/integration/codex_native/setup_idlisseus.py` — per-site build, bridge and endpoint
  registration.
- `idlisseus/dss/VISUAL_RESULT_CONTRACT.md` — normative browser-facing result contract.
- `idlisseus/dss/SITE_PACK_DEPLOYMENT.md` — deployment and site-isolation contract.

