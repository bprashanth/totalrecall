# Valparai Livelihoods — SYNTHETIC proof-of-concept site pack

**Everything in this pack is fully synthetic.** No file here contains real,
observed, surveyed or published data. It exists solely to test that the generic
`visual-site-pack/0.1` contract and `dss/visual_index/build.py` can carry a
non-ecological (livelihoods / socio-economic) domain without builder changes.

Do not cite it, publish it, or treat any number, place name or boundary in it as
evidence about Valparai or any real community, estate or scheme.

## Why Fable should use this pack

This is the safe UX-development twin of the real `dss/sites/valparai/` pack. Both packs declare
the same versioned capability interfaces and are served by the same
`dss/visual_index/result_service.py` implementation:

- `site-orientation`;
- `entity-record-map`;
- `coverage-versus-effort`;
- `metric-time-series`; and
- `gated-transfer` (currently an explicit blocked/partial capability in both packs).

The entities, metrics, sources and values differ, but the `idli-result/1` visual grammar does not.
For example, `daily_wage` produces the same chart/layer/drill-down structure as the real pack's
`rainfall`, and `Karumalai Estate` records produce the same map structure as real entity records.

Every result from this pack carries `site.synthetic: true`, synthetic source-version flags and a
`synthetic-data` limitation. Fable should render that as a persistent test-data notice. Switching
the configured pack to `dss/sites/valparai/` removes the notice automatically; no component,
route, capability or layout changes are allowed.

## What is synthetic here

- **Geometry** — the AOI polygon (~10.245-10.385N, 76.88-77.015E) and all named
  places were hand-authored in `raw/geometry/valparai_livelihoods_aoi.kml`. The
  estates and villages (Karumalai, Nedumparai, Ambalam, Pannimedu, Sirukundra,
  Thonimalai, Perumpallam, Kadamparai) are **fictional**. Only the plateau's
  approximate location and the town-centre point are realistic.
- **Sources** — five machine-generated CSV sets under `raw/`, licensed CC0-1.0
  and flagged with a `synthetic` capability:
  | source_id | plane | rows |
  |---|---|---|
  | `syn-estate-labour` | locations + events (annual worker headcounts, 2015-2024) + entity hierarchy | 50 events, 5 estates |
  | `syn-wages` | measurements (daily wage, overtime rate, paid days), 2017-2024 monthly | 96 rows → 288 measurements |
  | `syn-mgnrega` | events (public works, persondays), 2019-2024 | 72 |
  | `syn-migration` | events (out-migration by occupation) + occupation crosswalk | 42 |
  | `syn-household-survey` | effort (households visited, enumerator hours, population denominator) + locations | 48 |

## Entities

Estates (5, carrying a `sector → division → ownership_type → estate_unit`
hierarchy), scheme work types (4), and occupations (4, reached through a
verbatim→canonical crosswalk).

## Build

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/valparai_livelihoods \
  --output /tmp/valparai-livelihoods-index
```

Run the typed wage example:

```bash
python3 dss/visual_index/result_service.py \
  --site-pack dss/sites/valparai_livelihoods \
  --index /tmp/valparai-livelihoods-index/site_index.sqlite \
  --state /tmp/valparai-livelihoods-results \
  --query '{"request_id":"wage-demo","capability_id":"metric-time-series","arguments":{"metric":"daily_wage"},"question":"How have daily wages changed?"}'
```

The dual-pack conformance tests build and query both packs:

```bash
python3 -m unittest dss.visual_index.tests.test_result_service.PackSwapContractTest -v
```

## Known contract note

`build.py` reads the AOI from the inline GeoJSON in `site.json`; it has no KML
reader. The KML is kept in `raw/geometry/` as the immutable authored original
and is mirrored into `site.json` by hand (`target_aoi.source_geometry_file`
records the link).

## OPERATIONS — live Idlisseus endpoint (port 7013)

This pack is served through the benchmark-owned launcher
`ecology_memory/integration/codex_native/setup_idlisseus.py`, in its own state
directory, on its own port, with its own public model id. It never shares state
with the EBTL endpoint on 7011.

```bash
export PY=/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus/venv/bin/python
export TR=/home/beeps/src/github.com/bprashanth/totalrecall
export SITE_LAUNCHER="$TR/ecology_memory/integration/codex_native/setup_idlisseus.py"
export SITE_PACK="$TR/dss/sites/valparai_livelihoods"
export SITE_STATE="$TR/runs/insight-valparai-livelihoods"
```

Start (builds/refreshes the derived index, starts the bridge, registers the endpoint):

```bash
cd "$TR"
"$PY" "$SITE_LAUNCHER" start \
  --idlisseus /home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus \
  --site-pack "$SITE_PACK" \
  --state "$SITE_STATE" \
  --host 172.17.0.1 --port 7013 \
  --public-model idli-insight-valparai-livelihoods \
  --endpoint-name "Idli Insight — Valparai Livelihoods"
```

Status, health and logs:

```bash
"$PY" "$SITE_LAUNCHER" status --state "$SITE_STATE" --port 7013
curl -fsS http://172.17.0.1:7013/health
tail -f "$SITE_STATE/server.stdout.log"
tail -f "$SITE_STATE/server.stderr.log"
```

Stop only this site (does not touch 7011, hermes-live, or the Idlisseus UI):

```bash
"$PY" "$SITE_LAUNCHER" stop --state "$SITE_STATE"
```

Direct smoke test:

```bash
TOK=$(cat "$SITE_STATE/.api-token")
curl -sS http://172.17.0.1:7013/v1/chat/completions \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"model":"idli-insight-valparai-livelihoods","messages":[{"role":"user","content":"Tell me about this site"}]}'
```

### Visual results on the same port

The bridge also serves this pack's typed `idli-result/1` transport, using the same bearer token
as the chat routes and the same `ResultService` implementation
(`dss/visual_index/result_service.py`) bound to `$SITE_STATE/visual-index/site_index.sqlite`;
immutable results are written under `$SITE_STATE/visual-results/results/<result_id>/`.
`GET /v1/capabilities` returns the pack's registered capability descriptors plus its site id and
pack digest; `POST /v1/results/query` (`{request_id?, capability_id, arguments, question}`) runs
one capability and returns the result envelope; `GET /v1/results/<result_id>` and
`GET /v1/results/<result_id>/data/<handle>` return the stored envelope and its immutable data
payloads (`Cache-Control: private, immutable`). The Codex agent reaches the same path through the
`visual-result` skill, which returns only a short summary (`result_id`, headline, status,
limitations) and requires the answer to carry `<!-- idli-result:{"result_id":"..."} -->` on its
own line instead of pasting result data into prose.

```bash
TOK=$(cat "$SITE_STATE/.api-token")
curl -sS -X POST http://172.17.0.1:7013/v1/results/query \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"capability_id":"site-orientation","arguments":{},"question":"Show me where records are available"}'
curl -fsS -H "Authorization: Bearer $TOK" http://172.17.0.1:7013/v1/results/<result_id>
curl -fsS -H "Authorization: Bearer $TOK" http://172.17.0.1:7013/v1/results/<result_id>/data/declared-aoi
```

Registered endpoint row in the Idlisseus DB:

```text
Endpoint: Idli Insight — Valparai Livelihoods
Model:    idli-insight-valparai-livelihoods
URL:      http://host.docker.internal:7013/v1
```

### Lineage and user uploads on the same port

`GET /v1/results/<result_id>/explain?layer=&mark=` returns the deterministic `idli-explain/1`
lineage of one mark in a stored result (same bearer token as the other result routes): the
capability that ran, the resolved question and bindings, the aggregation applied, the exact
contributing source rows, the source versions with digests and the limitations that affect that
mark. The mark may be a feature id, a time bucket (`2021-03`), or a **coordinate** — either
`mark=at:<lat>:<lon>` or `lat=&lon=` query parameters — resolved against the stored layer
geometry itself: polygon/cell layers by containment (bounding-box fallback), point layers by the
nearest point within about 250 m. `mark.resolution` reports how the mark was identified
(`identity`, `coordinate`, `auto-largest`, `none`). Only when no mark of any kind is supplied
does the service explain the layer's largest mark, flagged `mark.auto_selected: true` and
prefixed `AUTO-SELECTED:` in the statement; a coordinate that hits nothing returns an explicit
`no_mark_at_location` payload instead of a substituted mark. `GET /v1/capabilities` also
lists the two session-scoped upload capabilities (`upload-profile`, `upload-cross-join`).

```bash
TOK=$(cat "$SITE_STATE/.api-token")
curl -fsS -H "Authorization: Bearer $TOK" \
  "http://172.17.0.1:7013/v1/results/<result_id>/explain?layer=event-density&mark=at:10.255:76.965"
```

The Codex agent reaches the same paths through two skills beside `visual-result`:

- `visual-explain` (`{result_id, layer?, mark?}`; `mark` accepts `at:<lat>:<lon>`, and `lat`/
  `lon` arguments also work) for why/how questions. Its answer must repeat the marker of the
  ORIGINAL result id so the UI keeps that chapter in focus, must say when the lineage is for the
  auto-selected largest mark, and must report a coordinate miss as a miss.
- `visual-upload` (`{path | upload_id, mode: profile|cross-join, sheet?, column?}`) for a table
  the user attached. **Attachment path convention — two ways a file arrives:**
  1. *Staged upload.* Idlisseus posts an attachment manifest with the chat request;
     `_stage_attachments` copies each authorised file into
     `<state>/sessions/<session id>/input/attachments/<upload id>-<file name>` and records the
     relative path `attachments/<upload id>-<file name>`.
  2. *Inlined text file.* For small text files the browser stages nothing and pastes the file
     into the user message as `=== File: name.csv ===`, an optional
     `[Type: csv, Lines: N, Size: M bytes]` line, then the raw content. The bridge parses those
     blocks (`_inline_file_blocks`) and stages them itself before the turn runs
     (`_stage_inline_files`) as `attachments/inline-<content hash>-<file name>`, registered in
     `ATTACHMENTS.json` exactly like a staged upload, so both paths behave identically for
     routing, the prompt and the skill.

  The system prompt shows Codex the full path under its container mount
  `/tmp/codex-native/sessions/<session id>/input/`. The skill accepts the container path, the
  host path, the relative form or the attachment's display name, falls back to the session's
  newest table when the path is missing or wrong, and refuses anything resolving outside that
  session's own input directory. Uploads and their results are session-scoped: the bytes live
  under `<state>/visual-results/uploads/<session>/<content hash>/`, result ids are namespaced
  `result-upl-<session>-<hash>` and the envelope audit carries a `session_binding`.

### Estimates and computed earth layers on the same port

Two further bridge-side capabilities are served here. They are declared by the bridge modules
rather than by this pack's `capabilities.json`, because they are properties of the serving bridge
rather than of the pinned data; `GET /v1/capabilities` lists them alongside the pack's own.

`POST /v1/estimate/targets` (no body) returns `idli-estimate-targets/1`: every quantity this pack's
index can be asked to estimate, each with the **raw column the pack counts** taken verbatim from
`sources.json` — `event_total:mgnrega_work` counts `persondays`, `event_total:annual_labour_census`
counts `worker_count`, `event_total:out_migration` counts `persons_moved` — plus a per-record-count
variant of each, a `metric_mean:<metric>` entry per measured metric (`daily_wage` in INR/day,
`overtime_rate`, `paid_days_per_month`), and the whole-cell quantities `record_density`,
`entity_richness`, `survey_effort`, `effort_normalised_rate`. Each entry carries how many cells hold
a value, the sources, the years, the record labels that appear in it (`Footpath repair`, `Check dam
construction`) and whether there are enough surveyed cells to fit on.

Nothing in that endpoint matches a user's words against anything. This is deliberate: a user asks
about "jobs", and this pack has no such column. **Reading the user's word onto a catalogued target
is the model's job, done with general knowledge and stated to the user in plain language before any
number** — "I'll read 'jobs' as MGNREGA work-days plus estate employment, since those are the
employment data this site actually has". The service then binds exactly: suggest and run accept a
catalogued `target_id` and refuse free text, returning the ids that would have worked. Answering "no
variable called job" is a failure to interpret, never a finding.

`POST /v1/estimate/suggest` (`{cell, target?, purpose?}`) returns an `idli-estimate-menu/1` object:
the approaches this pack's data can support for one cell, each with its required planes, its gate
precheck **and what each gate actually saw**, and its `measured_skill` — leave-one-out R², residual
spread and interval coverage computed on this pack, not assumed. `recommended_approach_id` is the
supported approach with the best measured held-out skill. On the synthetic pack that is normally
`aoi-baseline-mean`: the synthetic cells carry no spatial structure, so no spatial model beats the
mean, and the menu says so instead of flattering the regression.

`POST /v1/estimate/run` (`{approach_id, cell, target?, purpose?, request_id?}`) emits an ordinary
`idli-result/1` envelope. The estimated cell is a `modelled` layer carrying
`uncertainty {kind: interval, level: 0.8, ...}` derived from the model's own leave-one-out residual
quantiles, beside the observed training cells as `derived`. `audit.assurance` is `generated`,
`audit.estimate` records the fit, and the limitations state the basis of the confidence claim
(training n, residual spread, held-out R²). **The target cell is never in its own training set**, so
running it on a surveyed cell is a genuine leave-one-out check — which is exactly how the tests
verify that the published interval covers held-out truth. A failed gate returns a `blocked`
envelope that keeps the observed map and names the gate; it never substitutes a number.

`cell` accepts `at:<lat>:<lon>` (the same coordinate convention `explain` uses for a map click) or
a cell id. `target` must be one of the ids `/v1/estimate/targets` prints; the menu carries the whole
catalogue back with it, so a wrong binding can be corrected in the same turn.

`POST /v1/earth-layer` (`{layer}`) renders one AOI-clipped raster from a real Earth Engine
product: "built-up" → `JRC/GHSL/P2023A/GHS_BUILT_S/2020` (100 m, 2020), "elevation"/"terrain" →
`USGS/SRTMGL1_003` hillshaded (30 m, Feb 2000), "tree cover"/"land cover" →
`ESA/WorldCover/v200/2021` (10 m, 2021). The envelope carries a `raster_image` layer with
`bounds = [w, s, e, n]` and a `data_ref` handle serving PNG bytes from
`GET /v1/results/<id>/data/<handle>`, beside the declared AOI polygon that gives the renderer its
extent. See `dss/visual_index/README.md` for why the thumbnail must pin `crs: EPSG:4326` and
`format: png`.

**Earth Engine on this box: live and in use.** `earthengine-api` (v1.7.33) is installed for the
*system* interpreter, with an authorised-user credential at `~/.config/earthengine/credentials`
(project `plantwars`). It is deliberately **not** installed in the bridge venv, which is shared
with the 7011 EBTL bridge; the service runs Earth Engine as a child process under the interpreter
that has it (`EE_PYTHON` overrides the search). Retrieved layers are `derived` evidence with
`assurance: retrieved`, the asset id in `audit.source_versions`, and a limitation carrying the
product's real resolution and epoch. The synthetic surface remains only as a labelled fallback for
a genuine outage — never the default — and when it runs the envelope says so with an
error-severity `synthetic-raster` limitation naming the exact reason.

```bash
TOK=$(cat "$SITE_STATE/.api-token")
curl -sS -X POST http://172.17.0.1:7013/v1/estimate/targets \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' -d '{}'
curl -sS -X POST http://172.17.0.1:7013/v1/estimate/suggest \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"cell":"at:10.30:76.94","target":"event_total:mgnrega_work"}'
curl -sS -X POST http://172.17.0.1:7013/v1/estimate/run \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' \
  -d '{"cell":"at:10.30:76.94","target":"event_total:mgnrega_work",
       "approach_id":"aoi-baseline-mean"}'
curl -sS -X POST http://172.17.0.1:7013/v1/earth-layer \
  -H "Authorization: Bearer $TOK" -H 'Content-Type: application/json' -d '{"layer":"built-up"}'
```

Codex reaches both through two more skills:

- `visual-estimate` (`{mode: targets|suggest|run, cell, target?, approach_id?, purpose?}`). When the
  user names the quantity in their own words, `targets` comes first: the model reads that word onto
  a catalogued target with general knowledge, says the reading out loud, then suggests and runs. The
  menu must be relayed with which approaches this data supports and, for those it does not, which
  check failed and what it saw; the run's answer must give the range, how solid it is **and why**,
  which data went in, and the top improvements.
- `visual-earth-layer` (`{layer}`). When the response reports `observed: false`, the answer must
  say plainly that the image is a synthetic stand-in and give the reason.

Every one of these answers is written for a programme manager, not for us. The words *pack*, *gate*,
*capability*, *skill*, *envelope*, *result service*, *evidence class*, *plane* and every internal id
are banned from the answer prose — they belong to the audit trail and the machine markers, which
already carry them. Esoteric column names from the data get translated on first use ("persondays —
days of paid work"). An answer that has to be decoded is not an answer.

A turn that carries a table and asks to profile, visualise or check it is routed
deterministically: `_required_first_skill` returns `visual-upload` and the controller prefetches
the profile — or the cross-join, when the turn asks to match names against the site — before the
model deliberates. That outranks `local-site-evidence-search`, because a search over the pack
cannot answer a question about the user's own file. An unrelated site question asked later in the
same conversation is unaffected: the table only claims the turn when the request actually refers
to it.

The bridge binds to `172.17.0.1:7013` (Docker bridge only, same convention as
vLLM/ds4 — never `0.0.0.0`), so the odysseus container reaches it via
`host.docker.internal:7013` while nothing is exposed publicly.
