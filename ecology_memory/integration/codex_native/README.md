# Codex CLI + native skills in Idlisseus

This is the interactive form of the strongest `late-bound-skills` benchmark arm. Idlisseus is
the frontend and session transport; one resumable Codex CLI thread does skill discovery,
invocation, recovery and answer synthesis.

```text
Idlisseus browser/API
  -> OpenAI-compatible bridge on :7011
  -> Codex CLI, GPT-5.4 low: conversation + evidence discovery
  -> local Algebra 9B-004d: frozen scientific-Algebra compilation
  -> frozen 12-skill benchmark index + runtime operational skills
  -> allowlisted skill gateway
  -> deterministic resource binding + ecology executor/connectors
  -> concise answer + collapsible Why trace + optional visual report
```

The public model id is provider-neutral: `idli-insight`. Idlisseus sends one stable browser
session id, so follow-up turns resume one Codex thread. The chat receives the name, status, and a
bounded result summary for each skill actually invoked, plus a stable audit id. These appear in
the compact, responsive **Why** panel above the clean answer. Discovery, skill reads, commands,
paths, raw outputs, progress commentary and backend-model routing remain in the complete
server-side JSONL audit.
The history renderer also recognizes the original Markdown trace format, extracts the invoked
skill names and removes the duplicated trace from already-saved conversations.
For an older Idlisseus transport that cannot forward custom SSE events, the bridge embeds only
that same compact skill-name list before the answer; the renderer lifts it into the native panel.

While a turn is running, the wave spinner shows the current safe milestone or `Using <skill>`.
The adjacent Activity disclosure is a bounded, vertically scrolling record of completed skills and
summaries. It disappears from the prose area when answer text starts. The final Why panel is open
by default and contains only skill names, bounded summaries and the audit id—not progress comments,
commands, paths, model routing or raw rows.

Owner-authorized uploads are sent as a manifest, revalidated beneath Idlisseus's upload root,
copied into the session's bounded `input/attachments` directory, and exposed to Codex by their
safe sandbox paths. The original host path is not exposed to the model. An explicit “make a
report” request can invoke `publish-report`, which writes the existing Idlisseus research JSON
schema and returns an authenticated `/api/research/report/...` URL with the standard Open,
download, and Discuss experience.

When an answer explicitly identifies a missing model or predictor, the chat offers a **Request
this model from T4GC** button. Clicking it starts a separate audited turn and invokes the runtime
`request-model-from-t4gc` skill; no request is filed without that click. Requests are appended to
`runs/service/sessions/model_requests.jsonl` with mode `0600`, an audit id, owner, region, reason,
response variable, predictors, labels, spatial extent, validation target and stable request id.
This operational skill is layered on top of the frozen 12-skill catalog, leaving the recorded
benchmark input unchanged.

## Evidence, protocol and map chain

The frozen benchmark catalog remains 12 skills. Nine operational skills are added at runtime, for
21 visible skills in `/health`:

- `compile-scientific-algebra-9b` gives the local 9B-004d model one explicit scientific question,
  the frozen Algebra grammar, and a controller-generated manifest of admitted entity, region and
  layer symbols. It never gives 9B a skill catalogue. The controller rejects invented symbols,
  validates the returned Algebra, binds its leaves to admitted resources and executes it.
- `site-overview` inventories the onboarded profile, registered analysis geometry, local evidence
  partitions, configured capabilities and explicit geometry/data gaps. It never tokenises an
  organisation name as a taxon query.
- `local-site-evidence-search` searches the organisation's admitted, source-linked local evidence
  registry for any entity or topic. The EBTL adapter currently indexes local survey, bird, snake,
  elephant-passage, nursery, soil and evidence-summary categories. Other organisations seed the
  same operation through their own local-evidence adapter rather than adding species skills.
- `discover-ecology-evidence` sends the exact question plus up to three audited query variants to
  OpenAlex, Zenodo, Dryad and the admitted local semantic corpus concurrently. For a local site
  alias, the controller adds the topic without the acronym and the topic with the onboarded
  `discovery_context`; broad-group candidates supplied by Codex/9B remain explicitly untrusted
  query seeds. Results are interleaved across variants so one noisy branch cannot suppress the
  others. Returned items are discovery leads, never silently promoted to observations or site
  records.
- `inspect-evidence-dataset` accepts a session-scoped discovery result and one returned repository
  DOI. Bare, `doi:` and DOI-URL forms are equivalent. An exact Dryad DOI that transiently loses its
  file list gets one same-query retry; the adapter does not broaden the search.
- `relate-taxon-occurrences` retrieves two named taxa in one admitted region and calculates pairs
  within a declared distance while retaining both denominators. The conversational alias
  `donor belt` resolves to the declared `dry-Deccan donor belt`. Proximity is not interaction,
  shared habitat or temporal co-observation.
- `build-source-backed-field-protocol` creates a side-panel HTML reader and downloadable blank CSV.
  It extracts only declared source columns and labels programme-added effort fields. If the
  codebook has several tables, the caller names one returned source file.
- `build-ecology-field-map` retrieves and gates each taxon independently. A plant surface can run
  only for an explicitly declared vegetation entity after its estimate gate passes. Failed gates
  produce a labelled, spatially balanced confirmation design instead of invented overlap.
- `request-model-from-t4gc` records a structured user-authorized request when the needed model is
  absent.

Discovery and inspection results are stored as session-scoped result handles. Map and protocol
skills publish self-contained HTML into Idlisseus's existing document panel. Only the labelled
`#map-...` or `#document-...` link is model-visible; local artifact paths are not. Map CSV and
GeoJSON downloads are embedded in the HTML and use the same stable `FIELD-01...` identifiers.

The operational contract is:

```text
model proposes X as a labelled search seed
  -> admitted connectors return a source directly linking X to the focal entity/relation
  -> retrieved records/dataset material
  -> independent sample and environmental gates
  -> estimate, source-backed protocol, or precise field DataRequest
  -> plain-English answer + audit + optional side-panel map
```

Spatial overlap is a field-confirmation hypothesis, not evidence of interaction, dispersal, shared
habitat or temporal co-occurrence.

A general source about X does not pass candidate lineage for a relation question. It may be used to
form a labelled `X + focal entity + relation` search, but X is not sent to occurrence or estimation
unless a returned source directly supports that connection. If one requested map partner remains
unsupported, the map skill may return a one-taxon balanced collection design; it labels the output
as not being a two-taxon overlap.

Local-site questions route to `local-site-evidence-search` before literature or public occurrence
discovery, regardless of species. Site aliases are runtime configuration. A local registry
non-match is reported as an evidence gap, not absence; broader discovery runs when the user asks for
external papers/datasets or after the local result is made clear.

## Codex outside + Algebra 9B inside

Codex owns the short dialogue, ambiguity handling, onboarded-resource discovery, connector search
and skill invocation. General knowledge may supply clearly identified background or untrusted
search seeds; it cannot become site evidence. Broad site overviews and literature-only questions
do not invoke 9B.

When the evidence supports an explicit scientific state, relationship, trend, comparison, ranking
or transfer question, Codex invokes `compile-scientific-algebra-9b` with only that question:

```text
Codex dialogue + admitted evidence
  -> one explicit scientific question
  -> local Algebra 9B-004d emits frozen IR
  -> schema and resource-symbol validation
  -> deterministic binding and gated execution
  -> plain-English result + exact IR audit
```

Codex cannot author, repair or replace the returned IR. A model-memory taxon, region or layer that
is neither user-named nor admitted by the resource manifest is rejected before connector
execution. If the IR contains a hole or the scientific gate fails, the answer asks the short
clarifying or data-collection question needed for a later pass.

The chat formats this boundary explicitly under **Scientific analysis**:

- the exact scientific question sent to 9B;
- a plain-English reading of how 9B expressed it;
- what Idli Insight's bound executor returned; and
- a collapsed exact Algebra tree for audit.

Normal prose uses natural provenance phrases such as “From the onboarded site records” rather
than bracket tags. This is a hybrid runtime arm—Codex dialogue/discovery + 9B scientific compiler
+ deterministic execution—not evidence that 9B alone is an agent.

## Guided investigation trial

The Codex-default path now runs one evidence-bearing investigation stage per turn unless the user
explicitly asks for the complete workflow or a concrete artifact. An explicit map, screening-map,
field-point or “where on the site” request is artifact-complete in that turn: the controller
retrieves admitted evidence, asks 9B to compile the scientific estimate when one is required, then
invokes `build-ecology-field-map`. The map skill runs its own occurrence and environmental gates.
If the gate passes but only an AOI-wide score is available, or if the gate fails, it still returns
a clearly labelled spatially balanced confirmation design rather than fabricated hotspots.

A deterministic capability graph derives the next valid operations from the skill that actually
completed and its result:

```text
local evidence
  -> wider occurrences or wider source discovery
  -> raw observed-points map or environmental transfer
  -> modelled map / failed-gate confirmation design
```

The bridge stores the pending actions with the resumable session. Idlisseus renders them through
its durable choice card; selecting a label binds the stored entity and region and restricts that
turn to the corresponding skill set. A different free-text message invalidates stale actions.
Failed or empty occurrence searches do not expose map or transfer actions.

Structured local inventory rows outrank broad group summaries when a user supplies a shorter local
name. For example, `sand boa` resolves through the seeded inventory to the source-reported Common
Sand Boa / `Eryx conicus` row before any public point query. The same subset match is generic and
fails as ambiguous when several local taxa match. Taxa embedded only in a survey-summary
`examples` list remain usable only when they identify one unambiguous candidate.

This allows the generic occurrence path—and its “Show the raw points” button—to work without
hard-coding a species. A named local taxon also offers “Map field-check locations” immediately.
Wider occurrence results offer raw-points, gate-test and modelled-map actions. A recoverable
geospatial taxon `data_request` offers a field-check map even when no occurrences were returned;
unresolved or ambiguous taxa and missing connectors still fail closed. A completed modelled map
offers a button for its supporting donor observations.

Natural requests such as “where on the site…?” or “where can I find it to get data?” count as map
intent; users do not need to know the skill name or say “build a modelled map”. The map operation
rechecks seeded local evidence, promotes one unambiguous source-reported scientific name into the
public occurrence query, and records that translation in the result. Designed points explain
whether they repair a failed transfer gate or reduce within-site uncertainty after only an
AOI-wide estimate.

`build-ecology-field-map` accepts `map_mode: observed` for the raw-map stage. That mode retrieves
and exports returned observations with stable `OBS-...` ids, runs no estimate, creates no designed
field points and collapses its long record table by default. `map_mode: modelled` remains a
separate explicit stage.

The typed scientific Algebra is unchanged. Holes still represent required missing values; this
session envelope represents optional scope-expansion decisions.

The two-pass four-arm development report is in
`../../narrative/benchmarks/evidence-chain-map/runs/overnight-001/REPORT.md`. A post-run native
replay of the relation/sparse-taxa conversation scored 8/8 turns with exact replay after the
deterministic relation skill was added.

## Start and register

Use the Idlisseus virtual environment because the semantic-literature connector needs its
`fastembed` dependency:

```bash
cd /home/beeps/src/github.com/bprashanth/totalrecall

/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus/venv/bin/python \
  ecology_memory/integration/codex_native/setup_idlisseus.py start
```

The setup command starts the local bridge, generates a mode-0600 bridge token, and registers this
shared Idlisseus endpoint:

```text
Endpoint: Idli Insight
Model:    idli-insight
URL:      http://host.docker.internal:7011/v1
```

Refresh Idlisseus, make a new chat, and select that model. Keep the Idlisseus mode toggle on
**Chat**. Codex CLI is already the agent; selecting Idlisseus Agent mode merely adds an unnecessary
outer loop. It will generally still answer, but it is not the benchmarked architecture.

Codex executes inside the already-running `hermes-live` container as the unprivileged `nobody`
user. The setup does not create, stop, or restart a container. This avoids the host's broken
`bwrap` sandbox while preserving the isolated runner used by the benchmark.

Check or stop only this bridge:

```bash
/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus/venv/bin/python \
  ecology_memory/integration/codex_native/setup_idlisseus.py status

/home/beeps/src/github.com/bprashanth/idlisseus/chatbots/odysseus/venv/bin/python \
  ecology_memory/integration/codex_native/setup_idlisseus.py stop
```

This does not start, stop, or reconfigure Hermes or any model server.

## Live local audit client

For the structured stream, read the generated bridge token without printing it:

```bash
export CODEX_NATIVE_API_TOKEN="$(cat ecology_memory/integration/codex_native/runs/service/.api-token)"
python3 ecology_memory/integration/codex_native/chat.py --direct
```

The direct client prints events as Codex produces them. It does not pause Codex between internal
commands: the noninteractive Codex CLI has no safe checkpoint/resume protocol for individual tool
calls. It pauses naturally for each next user turn, and the complete event stream is retained.

One question without the REPL:

```bash
python3 ecology_memory/integration/codex_native/chat.py --direct \
  --question 'Is EBTL becoming greener since 2019?'
```

The equivalent structured curl is:

```bash
curl -N http://127.0.0.1:7011/v1/audit/chat \
  -H "Authorization: Bearer $CODEX_NATIVE_API_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"session_id":"my-ebtl-test","message":"Is EBTL becoming greener since 2019?"}'
```

Reuse the same `session_id` for follow-ups. Every SSE object is an audit event; the final object
contains the answer and the resumable Codex thread id.

An answer's audit id is directly addressable on the authenticated bridge. For example, audit id
`6ea23d10-9b83-41f9-a118-77036b491aa4/4` maps to:

```bash
curl http://127.0.0.1:7011/v1/audit/6ea23d10-9b83-41f9-a118-77036b491aa4/4 \
  -H "Authorization: Bearer $CODEX_NATIVE_API_TOKEN"
```

Omit `/4` to retrieve every turn in that session. Audit responses retain commands, results, and
provenance but redact embedded credentials.

The audit id shown in chat is therefore actionable: `<session>/<turn>` identifies exactly one
bridge audit. Operators can use the endpoint above; ordinary users can click the audit id to copy
it and use `/why` or `/audit` to reopen the latest Why panel.

## Through the remote Idlisseus API

Create/select a browser chat using the Idli Insight model and copy its session id. Generate a
normal Idlisseus API token with `chat` scope in Settings. From a laptop:

```bash
export ODYSSEUS_URL=https://chat.idli.cc
export ODYSSEUS_API_TOKEN=ody_your_scoped_token
export ODYSSEUS_SESSION=the_browser_chat_session_id

python3 ecology_memory/integration/codex_native/chat.py
```

Equivalent one-turn curl (the response is SSE):

```bash
curl -N -X POST "$ODYSSEUS_URL/api/chat_stream" \
  -H "Authorization: Bearer $ODYSSEUS_API_TOKEN" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "session=$ODYSSEUS_SESSION" \
  --data-urlencode "mode=chat" \
  --data-urlencode "message=Is EBTL becoming greener since 2019?"
```

## Security boundary

The bridge requires a bearer token and exposes only an allowlisted skill gateway. Codex gets a
private home and workspace per session and runs as uid/gid 65534 inside the existing Hermes
container; that user cannot traverse the mounted Hermes data directory. Public web search is not
enabled. Attachment paths are accepted only from the authenticated internal endpoint, must resolve
beneath the configured upload root, and are copied into the per-session input tree. Published
reports are bounded and owner-stamped, but the bridge token still represents a trusted internal
service rather than an end-user authorization boundary. The container also has outbound network
access and a general shell, and the host bridge itself can issue narrowly constructed `docker
exec` calls. Therefore this is a trusted-team POC, not a hardened public multi-tenant boundary.
Before public use, give the Idlisseus-to-bridge metadata its own service credential, move the
runner into a dedicated long-lived sandbox with an egress allowlist, and remove unrelated mounts.

## Backend routing

The browser-facing model remains `idli-insight`; `CODEX_NATIVE_MODEL` selects the underlying Codex
model and appears only in server logs and the full audit. Codex CLI also supports local Ollama/LM
Studio and custom Responses-compatible providers, so the bridge boundary can stay fixed while the
backend changes. The current service launcher is deliberately pinned to the existing
ChatGPT-authenticated Codex configuration. Add and validate a provider-specific launch profile
before routing production traffic to OpenRouter or a local model; do not put provider API keys in
report, attachment, or session state.

The frozen manual questions are in
`../../narrative/benchmarks/skills-agent-harness-v2/questions.json`.

## Evidence-chain benchmark

The open, multi-turn evidence-chain benchmark is under
`../../narrative/benchmarks/evidence-chain-map/`. Its conversations cover Eucalyptus and birds,
Lantana rebound mapping, satellite/fire discovery, sparse-taxon relations and ANR matched plots.
All arms ask the same turn-by-turn questions in direct Indian English:

```bash
python3 ecology_memory/narrative/benchmarks/evidence-chain-map/runner/run.py \
  --run overnight-001 --passes 2
```

The runner records native answers, complete bridge audits, result handles, heuristic contract
checks, verifier decisions, model endpoint observations and per-turn latency. It never starts or
reconfigures a model server. Development screenshots live beside their run. A repaired run is only
regression evidence; it is not a saturation claim under `ecology_memory/SATURATION.md`.
