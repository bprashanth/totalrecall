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
the declared limitations that affect that mark. With no mark it explains the layer's largest mark
— the right default for a hotspot question — and says that it auto-selected it. A mark inside a
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

`PackSwapContractTest` builds the real Valparai pack and the synthetic Valparai livelihoods pack,
runs their declared typed question probes through this same service, validates both against the
shared schema and asserts that matching capabilities return identical renderer grammar.
