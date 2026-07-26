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

## Reading an open subject name

Typed operations accept entity ids, exact registered names or source-declared hierarchy groups.
People also ask for open groups that no source has declared: a phrase such as “raptors” may refer
to several recorded names whose rows contain no common hierarchy at all. That semantic judgement
does not belong in SQL, and a guessed taxonomy must not become a source-backed fact.

`subject_resolver.py` keeps that boundary explicit:

1. It resolves a unique registered alias after conservative singular/plural widening.
2. If that is insufficient, it returns the complete entity catalogue for the pinned index. The
   dialogue model chooses only entity ids from this bounded list. The bridge transports the large
   catalogue as compact `[entity_id, recorded_name]` rows with explicit column names; this is a
   wire optimisation, not a different evidence set.
3. It rejects any id outside the supplied catalogue, records the selector model and prompt
   version, and writes an immutable binding under the visual-result state directory.
4. The cache key includes the catalogue digest, original phrase, model and prompt version. A pack
   rebuild or selector change cannot silently reuse an old interpretation.
5. The result carries `member_labels`, `resolution_method`, `selector` and `binding_id` in
   `question.bindings.subjects`. A `model-selected-subject-group` limitation distinguishes that
   interpretation from a group declared by a source.

Taxonomy is used only after selection to say, for example, that every selected member shares a
family. It never chooses the members. The correction action reopens the bounded catalogue and
creates a new immutable binding; it does not mutate the earlier audit record. The resolver itself
calls no model. In the current deployment the outer Codex turn performs the semantic choice and
retries the same typed capability with verified ids.

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

When no `layer` is supplied, the layer is chosen rather than defaulted. A map draws its context
first — the declared study boundary, one polygon with nothing to count — so taking the visual's
first layer answered a click that landed squarely inside a density square with "0 source rows
contributed there", while the same coordinate resolved perfectly against the density layer drawn
on top of it. Every layer is now checked against the mark that was given: the layer whose own
stored geometry contains that point (or whose features carry that mark id) wins, preferring one
that carries countable values. `layer.auto_selected`, `layer.chosen_because` and
`layer.alternatives` report the choice, and when the chosen layer has nothing there but another
layer would have answered, `suggestion` says so, so a caller retries instead of reporting a dead
end.

## Naming a grid square to a person

`cell_language.py` turns a square into words. The grid labels each square by its south-west
corner, so a point at 10.305 N belongs to `g0.010:10.3000:76.9900` — arithmetically exact, and to
a user indistinguishable from the system having quietly changed the coordinates they gave. So an
id never appears in a sentence. `describe_cell` returns the extent instead — *"the 1.1 km square
covering your point (10.305 N, 76.995 E), spanning 10.300–10.310 N and 76.990–77.000 E"* —
computed from the square's own stored geometry (the `cells` row, or the polygon the layer
actually drew), never from an assumed resolution: a pack gridded at 0.05° describes itself as a
5.5 km square with nothing to change here. The id stays in `mark.id`, the audit and the layer
payloads, where the map and the audit trail need it. `estimate_service` carries the same phrase
through `question.resolved`, `answer.headline`, every limitation and every improvement, and the
bridge relays it as `cell_description`.

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

The catalogue also carries `places`: every named location in the index with its coordinates. A
person who says "the square just below Kadamparai" has already given the location, and asking
them to type it back as `at:<lat>:<lon>` is asking them to do our arithmetic — which is exactly
how one bench conversation spent all four turns clarifying and never produced a number.
`capability_vocabulary` does the same job for the result capabilities: the values their declared
arguments will actually accept here (which metrics can be plotted, which subjects mapped, which
ranks and groups exist, which source carries which category property). An argument's *name* does
not tell a caller which call to make; a question like "which village has the most survey visits?"
bounced off the orientation map because the data was there and the argument values were not.

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

## Requirements live in the data, not in the prompt

Four benchmark rounds settled an architectural question. Every rule added to the dialogue prompt
displaced one already there: adding the join rule took the confidence statement from 92% to 50%;
cutting sentences to 14 words took the alternative and the join rule; restoring those cost the
sentence length again. The graded dimensions took turns failing while the prompt grew. The only
fixes that never regressed were the ones that changed the data the model was given.

`answer_contract.py` moves the requirements onto the results. A result declares what must be said
about it — `required_statements: [{id, statement, why, audience}]` — and each statement is the
producing capability's own sentence, promoted from a limitation it already declared. `audience`
is `reader` for a sentence safe to show beside the visual and `model` for an instruction that
belongs only in the answer check. A shared-square map
carries its join rule; an estimate carries its confidence basis and that it is modelled; a
priority ranking carries "this is where the data is thinnest, not where the ecology is richest";
any result with figures carries the surveys they came from. They are attached to the model-safe
summary and served on the result itself, so the renderer can show reader statements verbatim
(proposal TR-VIS-0002).

`review_answer` then enforces, on the way out, the invariants that need no judgement: it
substitutes wording that belongs to the plumbing, splits an over-long sentence at a join already
present in the text, and reports a missing required statement or a missing next step. It never
writes prose — a missing statement is reported, because supplying it would be authorship. The
bridge records the result as an `answer_check` audit event and emits it for the interface.

The prompt shrank as this grew: the banned-phrase list, the square-id rule, the "every figure
names its survey" rule, the join-rule reminder and the sentence-length guidance were all deleted
from the global text once the data or the outgoing check carried them.

## A route that cannot express something is not a site that lacks it

The round-1 fix taught the system to stop saying "your word does not exist here". Round 2 found
the same refusal in new clothes: *"this site does not have compatible site-and-effort structure
for the plant community structure survey, so I cannot give a defensible count"* — said about a
summary's shape, and heard as a statement about the landscape. One turn was a straight
regression: round 1 answered "how many plant community plots?" with a real number attributed to
the wrong survey, and round 2 fixed the attribution by withdrawing the number.

Three bridge-side changes. `source_facts` in `target_catalogue.py` counts what one survey holds —
records, named plots or sites, documented visits, years — finding each survey's own sampling-unit
field, because this pack alone uses `Site_ID`, `PlotID`, `P_ID` and `plot_no` across four studies.
The plant community survey has 110 plots; the restoration-opportunities survey has 132. Both
numbers are now available, each attached to the survey it came from. A blocked or partial result
carries `route_note` and `what_this_source_holds`, and the skill text says to resolve the argument
and retry rather than narrate the failure.

`_visual_breakdown` forwards the per-category rows a capability already computed. The flagship
"does restoration work" question — 23 restored, 23 unrestored and 23 benchmark plots, visited
154, 154 and 152 times, at 24.3, 18.5 and 27.4 detections per visit — was computed on every run
and stopped one layer below the summary the model could see, which is why the honest answer was
"this result does not expose the per-type plot counts". Same starvation as the frugivory pairs,
same fix.

Explain now ranks a layer whose own mark IS the thing asked about above one that merely carries it
as a property: asking about "Benchmark" matched both the 69 tagged survey sites and the three-row
category table, and only the table can say how Benchmark compares. A mark that resolves to a
computed summary row rather than an index row is explained from that row instead of being reported
as unresolved.

## Looking the name up before refusing it

A field ecologist asked whether the site held anything at all on lantana and was told it did not.
The pack holds `Lantana camara` in 36 records across three surveys, and the assistant typed the
correct binomial in its own next sentence — as somewhere else to look. The same failure hit
`mammal` while `Mammalia` sat in the index as a class with 30 members and three dedicated sources.

Neither was a data problem. The accepted-value lists printed into the skill text were cut
**alphabetically** and the text called them exhaustive, so `Magnoliopsida` (575 entities, the
largest group in the pack) and every metric after `adult_m…` were invisible, and absence from a
printed sample became a statement about the world. Two changes: `capability_vocabulary` now orders
every list by how much data each value has and reports its own total beside the sample, and
`name_resolver.py` runs a real lookup before any refusal — exact alias, then genus or first word
(`Lantana` → `Lantana camara`), then shared words (`grey hornbill` → `Malabar Grey Hornbill`),
then hierarchy groups at any rank (`mammal` → class `Mammalia`), then metrics and kinds of record.

The bridge calls it before the capability, rewrites the call when the index files the name
differently, and hands the reading back as `name_resolution` so the answer opens by saying which
reading it took. An empty result means the lookup ran and found nothing — the only honest basis
for saying a name is not recorded here.

## Naming the pairs, not counting the relations

The index holds 5,622 source-linked interaction rows with named subjects and objects, and the
question they exist to answer — which trees get their seed moved, and by which animals — came back
as "no recorded source-linked rows for seed movement". `interaction-pairs` returns the pairs
themselves, ranked by how often each was written down, with a table and a network view: *Yellow-
browed Bulbul on Persea macrantha, 629 records*. Every result says that a pair is a record of
being seen together, not proof that seed was moved, and that the ranking follows watching effort
as well as behaviour. `interaction-map` keeps working and now carries `named_pairs` alongside its
relation totals.

## Where to survey next

Asked to rank the top five places for next season's effort, the assistant argued coverage-gap
logic for six turns and then ranked by record density — where we have already looked — naming each
square by its latitude band. `survey_priority.py` computes the ranking instead: squares score on
the gap between what is recorded in them and how much documented survey work stands behind that
recording, and each is resolved to the nearest place the pack itself names, with the distance. The
result says in its own limitations that it ranks where the data is thinnest and **not** where the
ecology is richest.

## Two subjects in the same square

"Show me where both hornbills and elephants occur" had no answer here at all. `interaction-map`
maps only the associations a source explicitly declared, so it came back blocked, while the index
held elephant in about a hundred squares, hornbills in thirty-one, and twenty squares with both.

`cooccurrence_service.py` adds two bridge-side capabilities, neither tied to any kind of subject.
`co-occurrence-map` intersects the squares each subject's own records fall in; the shared squares
are the answer, so they are the first and only filled layer, and each subject keeps its own
outline layer so a reader can see which side of the overlap is thin. A subject may be a
registered name, a hierarchy group (`{"kind": "group", "value": "Bucerotidae"}`, whose rank is
found rather than demanded, which is how "all hornbills together" resolves) or a kind of record —
"public works" and "people leaving" are event types, not entities, and the question is the same.
`entity-activity-profile` answers "what else is X doing" from the same engine: kinds of record,
surveys, years, what was measured where X was seen, and the subjects sharing most of its squares.

The honesty is in the envelope, not left to the model. Every result carries, in words: that both
being recorded in one square is **not** an interaction, an association or contact — with the size
of the square stated; that the records may come from different surveys, methods, amounts of effort
and years, so an overlap partly shows where people looked; that no overlap is not evidence of
separation; and how many of the shared squares hold records from the same year, with an action to
show only those.

```bash
python3 dss/visual_index/cooccurrence_service.py \
  --site-pack dss/sites/valparai \
  --index /tmp/valparai-index/site_index.sqlite \
  --state /tmp/valparai-results \
  --subject elephant --subject Bucerotidae
```

## Headline statistics for a context rail

`site_stats.py` answers "what is known about this place" in three to five numbers a programme
manager already uses. A rail that says "1,145 entities across 302 cells" is describing our
database; these describe the site. Nothing about any sector is written down in the module: each
stat is derived from the pack's own event types, declared count columns, metric registry, effort
methods and entity hierarchies, and the wording is recovered from the pack's own human-written
strings — which is how `mgnrega_work` prints its capitals from a source title, and how a count
column that only says "how many of them" (`individualCount`, `num`) is kept out of the label and
put in the detail instead. Entities become "Species recorded" only when the pack's own hierarchy
gives them a biological rank. `GET /v1/site/headline-stats` serves it, cached per process.

```bash
python3 dss/visual_index/site_stats.py \
  --site-pack dss/sites/valparai_livelihoods \
  --index /tmp/valparai-livelihoods-index/site_index.sqlite \
  --state /tmp/valparai-livelihoods-results
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
