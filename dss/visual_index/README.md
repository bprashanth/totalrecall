# Visual-ready AOI index prototype

This directory is the dependency-light feasibility implementation for the companion Idlisseus
design,
[`VISUAL_FIRST_AOI_DATA_DESIGN.md`](../../../idlisseus/docs/VISUAL_FIRST_AOI_DATA_DESIGN.md).
It proves the logical tables and visual-view contracts against a maintained site pack. The
deployment-pinned bridge integration is documented in
[`../SITE_PACK_DEPLOYMENT.md`](../SITE_PACK_DEPLOYMENT.md).

Build:

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/valparai \
  --output /tmp/valparai-visual-index
```

Outputs:

- `site_index.sqlite` — canonical facts and materialised aggregates;
- `visual_bundle.json` — data for the tested visual contracts;
- `preview.png` — one static feasibility preview; and
- `build_report.json` — counts, elapsed build time and integrity result.

Run the regression tests:

```bash
python3 -m unittest dss.visual_index.tests.test_build -v
```

The code intentionally uses the Python standard library and Pillow already present on this host.
It is a proof of the logical contract, not a recommendation to use SQLite as the production
warehouse.

## Typed result service

`result_service.py` translates the pinned index into browser-neutral `idli-result/1` objects. It
does not interpret free text: a conversation layer selects a declared capability and binds typed
arguments. The current producer supports site orientation, entity and canonical hierarchy-group
record maps, explicit subject-object association maps and networks, coverage versus effort and
metric time series. It can also compare source-declared survey categories while mapping every
site and retaining explicit effort denominators, and map any cell-aligned feature-year while
retaining its unit, evidence class, source asset, scale and missing support. The group operation
takes a hierarchy rank and value rather than a site-specific list, so the same result grammar can
map a taxonomic class, an occupation sector or another pack-defined hierarchy. Interaction
adapters are equally generic but stricter: a source must expose the relation or an explicit join;
proximity never creates an edge. Stratified summaries are descriptive unless a separate
inferential design is declared. Environmental features remain context or predictor inputs rather
than occurrence evidence. The transfer operation can produce a spatially gated environmental-
analogue screen from all 64 normalised AlphaEarth axes, but keeps that separate from an
effort-aware predictive model: observed donors, modelled analogues, unsupported cells and every
gate are separate result layers.

One-shot query:

```bash
python3 dss/visual_index/result_service.py \
  --site-pack dss/sites/valparai \
  --index /tmp/valparai-visual-index/site_index.sqlite \
  --state /tmp/valparai-result-state \
  --query '{"request_id":"demo-1","capability_id":"entity-record-map","arguments":{"entity":"lion-tailed macaque"},"question":"Where have lion-tailed macaques been recorded?"}'
```

Internal HTTP service:

```bash
python3 dss/visual_index/result_service.py \
  --site-pack dss/sites/valparai \
  --index /tmp/valparai-visual-index/site_index.sqlite \
  --state /tmp/valparai-result-state \
  --api-token-file /path/to/site-result-service.token \
  --host 127.0.0.1 \
  --port 7120
```

It exposes `POST /v1/results/query`, `GET /v1/results/{result_id}` and
`GET /v1/results/{result_id}/data/{handle}`. These are bridge/server endpoints, not public browser
URLs. Idlisseus should proxy authorised handles through its own same-origin API.

## Lineage for one produced value

`explain_service.py` answers "why is this value what it is" without a model. Given a stored
`result_id`, an optional `layer` and an optional `mark` (a cell, event, interaction, survey site,
entity or `YYYY-MM` bucket), it re-reads the immutable envelope and its layer payload, then
re-queries the same pinned index rows and returns `idli-explain/1`: the capability and version
that ran, the resolved question and bindings, the aggregation actually applied, the exact
contributing source rows with their ids, dates and values, the source versions with digests, and
the declared limitations that affect that mark. A mark may also be a coordinate
(`at:<lat>:<lon>`, or separate `lat`/`lon` values), resolved against the stored layer geometry:
polygon and cell layers by containment with a bounding-box fallback, point layers by the nearest
point within about 250 m — so a UI click can be explained even when the payload feature's id
never reached the browser. `mark.resolution` reports how the mark was identified (`identity`,
`coordinate`, `auto-largest`, `none`). Only with no mark of any kind does it explain the layer's
largest mark — the right default for a hotspot question — flagged `auto_selected: true` and
prefixed `AUTO-SELECTED:` in the statement; a coordinate that hits nothing returns an explicit
`no_mark_at_location` payload, never a silently substituted mark. A mark inside a
user-upload result is attributed to the uploaded rows; the site index is never consulted for it.

```bash
python3 dss/visual_index/explain_service.py \
  --site-pack dss/sites/valparai_livelihoods \
  --index /tmp/valparai-livelihoods-index/site_index.sqlite \
  --state /tmp/valparai-livelihoods-results \
  --result-id result-... --layer event-density
```

## User-supplied tables

`upload_service.py` ingests a CSV or a multi-sheet `.xlsx` that a user attached to one
conversation. The bytes are stored immutably by content hash under
`<state>/uploads/<session>/<hash>/`, each sheet is profiled deterministically (column types,
date-like and lat/lon-like and numeric columns, candidate entity-name columns), and two
capabilities emit ordinary `idli-result/1` envelopes: `upload-profile` (sample-row table, monthly
series when a date and a numeric column exist, observed-points map when coordinates exist, and
count/range tiles) and `upload-cross-join`, which matches uploaded names against two planes — the
pack's registered entity aliases and its named locations, because a household survey names
villages that a pack may register as places rather than as entities. Every match reports its own
strength: `exact`, `normalised` (case and spacing) or `normalised-suffix`, where a generic place
word such as "Village" was removed from one side; the last carries its own `relaxed-name-match`
limitation so a weaker match is never presented as an alias match. The result holds match rates
per candidate column, a map of matched names at their known locations and every unmatched name
listed in full. Uploaded rows are `reported` evidence and always
carry a `user-supplied-unverified` limitation; a non-match is reported as a gap, never as absence.
Result ids are namespaced by session and the envelope audit records the session binding, so one
conversation's upload never becomes another's evidence. Workbooks are read with `openpyxl` when it
is importable and with a standard-library zip/XML reader (including date-format decoding)
otherwise, because the bridge interpreter has no `openpyxl`.

A file does not always arrive as a staged upload: for small text files the browser inlines the
content into the user message as a `=== File: name.csv ===` block. The bridge stages those blocks
into the session's own attachment directory before the turn runs, so one convention reaches this
module either way. See `dss/sites/valparai_livelihoods/README.md` for the path convention.

## What can be estimated at all

A user asks about "jobs". No index has a column called that. The old behaviour — keyword-match the
phrase against a fixed list of quantities, and if nothing scores, answer "there is no variable
called job" — was wrong twice: it made a semantic judgement inside a deterministic service, and
when the judgement failed it reported the failure as a fact about the world.

`target_catalogue.py` replaces the keyword table with an enumeration. `build_target_catalogue`
reads the pinned index and the pack's declared adapters and returns `idli-estimate-targets/1`: one
entry per event type carrying **the raw column that pack counts**, taken verbatim from
`sources.json` (`mgnrega_work` → `persondays`, `annual_labour_census` → `worker_count`,
`out_migration` → `persons_moved`), one per measured metric with its declared label and unit, plus
documented survey effort, record density, entity richness and the effort-normalised rate. Each
entry states how many cells carry a value, which sources supply it, the years covered, the record
labels that appear in it (`Footpath repair`, `Check dam construction`) and whether there are enough
surveyed cells to fit on — a thin target is listed and marked, never hidden.

Nothing in this module matches a user's words against anything: there is no synonym list and no
scoring. The reading of "jobs" as persondays plus estate worker counts is the dialogue model's, made
with general knowledge and **stated to the user in plain language before any number**. The service's
job is to publish the vocabulary and then bind exactly: `resolve_target` accepts a catalogued
`target_id` and refuses free text, listing what would have worked. Every number still comes from
the data.

```bash
python3 dss/visual_index/estimate_service.py \
  --site-pack dss/sites/valparai_livelihoods \
  --index /tmp/valparai-livelihoods-index/site_index.sqlite \
  --state /tmp/valparai-livelihoods-results --targets
```

## Estimating a cell that has no observation

`estimate_service.py` answers "what would the value be here?" for one map cell. It is deliberately
two calls after the catalogue. `suggest_approaches(target_id, cell)` returns
`idli-estimate-menu/1`: 2-4 approach
descriptors — spatial-neighbour least-squares regression, nearest-cell analogue average,
effort-normalised rate transfer, AOI baseline mean — each with its required planes, a gate
precheck that reports **what each gate actually saw**, and `measured_skill`: the approach's own
leave-one-out R², residual spread and interval coverage on this pack. `recommended_approach_id` is
whichever supported approach measures best, so the menu cannot promise skill the run will not
deliver. On the synthetic livelihoods pack the honest answer is the baseline mean: those cells
carry no spatial structure and no spatial model beats it.

The menu carries the whole target catalogue back with it, so a caller that bound the wrong quantity
can see every other one this pack holds and correct itself inside the same turn.

`run_estimate(approach_id, target_id, cell)` emits an ordinary `idli-result/1` envelope. Three rules
hold throughout: the target cell is never in its own training set and a cell's features never
include its own value, so every prediction — including for a surveyed cell — is a leave-one-out
prediction; the interval is the model's own leave-one-out residual quantiles at level 0.8 rather
than a normality assumption; and a failed gate produces a `blocked` envelope that still draws the
observed cells and names the gate, because a model that cannot run is not a reason to hide the
data that exists. The estimated cell is a `modelled` layer with
`uncertainty {kind: interval, level, low, high, agreement}` beside `derived` training cells;
`audit.assurance` is `generated`; the limitations state the confidence basis (training n, residual
spread, held-out R²) and exactly which source versions and planes fed the features; and the
actions are concrete data requests with their expected effect on the interval. Gates: target cell
inside the AOI, at least eight training cells, non-zero feature variance, and neighbourhood
support. The least-squares fit is normal equations solved by Gaussian elimination with partial
pivoting — standard library only, on a matrix of at most seven columns.

```bash
python3 dss/visual_index/estimate_service.py \
  --site-pack dss/sites/valparai_livelihoods \
  --index /tmp/valparai-livelihoods-index/site_index.sqlite \
  --state /tmp/valparai-livelihoods-results \
  --cell at:10.30:76.94 --target event_total:mgnrega_work   # add --approach to run one
```

## Computed earth layers

`earth_layer_service.py` turns "make the map a map of built-up" into one AOI-clipped raster layer:
a keyword registry maps free text onto a published Earth Engine product, and the envelope declares
a `raster_image` layer with `bounds = [w, s, e, n]` whose `data_ref` handle serves PNG bytes. A
declared-AOI polygon travels with it because the renderer takes its extent from vector geometry.

| request words | Earth Engine asset | band | native scale | epoch |
|---|---|---|---|---|
| built-up, settlement, urban | `JRC/GHSL/P2023A/GHS_BUILT_S/2020` | `built_surface` | 100 m | 2020 |
| elevation, terrain, relief | `USGS/SRTMGL1_003` via `ee.Terrain.hillshade` | `elevation` | 30 m | Feb 2000 |
| tree cover, forest, land cover | `ESA/WorldCover/v200/2021` | `Map` | 10 m | 2021 |

Those scales were read back from Earth Engine (`projection().nominalScale()`), not assumed.
GHS-BUILT-S P2023A is a **100 m** product measuring built surface area in m² per cell (0-10,000);
it is not the 10 m variant, and the limitation text says so.

**Earth Engine runs in a child process**, under whichever interpreter actually has
`earthengine-api` (`EE_PYTHON`, else this interpreter, else `/usr/bin/python3`). The bridge venv is
shared with another site's bridge, so installing a cloud SDK into it would change a runtime this
module has no business changing — the repo already re-execs into a different interpreter for the
same reason (`integration/origin/connectors/_base.py`). The child takes one JSON request on stdin,
writes PNG bytes to a temp file and reports one JSON line, so image bytes never share a stream with
diagnostics. Credentials are a per-user file, so both interpreters authenticate identically.

Two thumbnail parameters decide whether the layer is placed correctly at all:

- **`crs: EPSG:4326` is mandatory.** A thumbnail renders in the image's native projection unless
  told otherwise, and GHSL is Mollweide — the AOI comes back as a rotated parallelogram whose pixel
  grid does not line up with the declared lat/lon bounds. Pinning EPSG:4326 makes the raster
  axis-aligned in degrees, the only form `bounds` can honestly place.
- **`format: png` is mandatory**, because the default encoding is JPEG.

Clipping to the declared polygon is what makes everything outside the AOI transparent: Earth Engine
masks it and the PNG carries the mask as alpha. Colour type varies by product (RGB for a fully
covered palette render, grey for a hillshade, RGBA where a clip masks the frame), so the envelope
reads the real size back from the returned header instead of assuming what it asked for.

When Earth Engine cannot be reached — no `earthengine-api` anywhere, no credential, or no egress —
the same capability still runs so the contract stays exercised: the surface is generated from the
pack itself (kernel density over indexed record and effort locations as a settlement proxy; an
analytic relief field for elevation), classed `modelled` with a `synthetic:` source id and an
**error**-severity `synthetic-raster` limitation naming it synthetic and giving the exact reason.
That is a labelled fallback for a genuine outage, never a default. Probe and fetch are both bounded
(`EE_INIT_TIMEOUT`, `EE_THUMBNAIL_TIMEOUT`) so a dead network cannot stall a chat turn, and the
fallback PNG is written by a minimal stdlib encoder (zlib + CRC) so the bridge needs no imaging
dependency.

```bash
python3 dss/visual_index/earth_layer_service.py \
  --site-pack dss/sites/valparai_livelihoods \
  --index /tmp/valparai-livelihoods-index/site_index.sqlite \
  --state /tmp/valparai-livelihoods-results --layer built-up
```

The default test suite forces Earth Engine off, so the fallback contract is hermetic on any
machine. Exercise the live path explicitly:

```bash
IDLI_TEST_EARTH_ENGINE=1 python3 -m unittest dss.visual_index.tests.test_earth_layer_service
```

`PackSwapContractTest` builds the real Valparai pack and the synthetic Valparai livelihoods pack,
runs their declared typed question probes through this same service, validates both against the
shared schema and asserts that matching capabilities return identical renderer grammar.
