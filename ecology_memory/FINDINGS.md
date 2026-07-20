# FINDINGS — ecology sector
Running log, newest at bottom. Tag each finding [HARNESS]/[CONNECTOR]/[PARSER]/[SPEC-PROPOSAL]/[SCORING].
Every equivalence decision you make as judge gets recorded here with its reasoning.

## 2026-07-15 — import boundary and stopping target

- [HARNESS] Origin is the whole read-only repository
  `/home/beeps/src/github.com/bprashanth/idlisseus`, specifically `agents/hermes`, `dss`, and
  `benchmarks`. No origin file may be changed during this run.
- [HARNESS] Hard saturation was selected before question or holdout contact because the intended
  result is a LoRA candidate for cross-sector/origin integration. The immutable lock records
  `saturation_tier: hard`.
- [HARNESS] The released framework manifest named SAT-004 while the proposal registry still said
  `proposed`. The durable Fable review and reconciled decision already authorized and implemented
  it, so the registry was corrected to `validated` before bootstrap. Governance validation then
  passed (46 proposals, 5 released).
- [HARNESS] Cursor Agent CLI is available. A low-cost `gpt-5.4-mini-low` read-only inventory was
  used only as mechanical assistance. Its output is not benchmark evidence: it inherited the
  origin workspace and made semantic mistakes (for example GROUP is not generally equivalent to
  unpartitioned AGGREGATE), confirming that all inventory and algebra decisions require local
  code verification.

## Origin runtime: what must and must not be imported

- [HARNESS] `agents/hermes/chat.sh --model deepseekv4` explicitly selects
  `deepseek/deepseek-v4-flash` with provider `openrouter`; the API key is injected into the
  persistent container. The default Hermes model is irrelevant on that path.
- [HARNESS] The origin's effective planning language is SOUL + PLAYBOOK + on-demand recipes +
  connector cards + discipline/why plugins. It is free-form tool use, not the v2.2.1 JSON IR.
  Preserve its question vocabulary, concise-answer behavior, site facts, routing lessons, and
  regression scenarios as curriculum/evaluation material; do not copy its prompt as the parser
  contract.
- [HARNESS] The totalrecall parser under test remains the local `qwen3.5-2b`. DeepSeek is a gold
  author/frontier arm only. Any final claim that the 2B beats DeepSeek must use parser-blind banks,
  executed gold, equivalent deterministic connectors, and separate synthesis/evidence audits.

## Connector inventory audit

- [CONNECTOR] The production directory has 24 connector modules, not the 25 claimed by the concept
  map. Twenty have matching Markdown cards; `discovery`, `hyperspectral`, `invasive`, and `skyfi`
  do not. Only seven have dedicated origin self-tests. Connector code compiles, but this is not
  sufficient evidence of source correctness.
- [CONNECTOR] Origin connectors do not share one return contract: outputs include lists, tuples,
  cached CSV paths, summary dictionaries, ranked cards, model verdicts, HTML, maps, orders, and
  downloaded assets. Imported benchmark adapters must return `rows/kind/source/note`, declare an
  evidence label, and translate source gaps/outages/ambiguity into DataRequest.
- [CONNECTOR] Origin `_base.read_points` retains only `id/lat/lon`; chaining through it discards
  species, time, source, quality, license, and previous annotations. Imported adapters will operate
  on in-memory full rows and must preserve all fields.
- [CONNECTOR] Paid/mutating SkyFi operations (`order`, `download`) are outside the benchmark's
  deterministic read-only connector set. Scene search/price may become evaluation probes later,
  but no purchase or external mutation is authorized.

## Resolver decision

- [CONNECTOR] `points.py` does not perform embedding semantic lookup. It combines GBIF species
  match and iNaturalist taxa search with name/lexical guards. `discovery.py` is the semantic
  bge-small content-card retriever; `embedding.py` is AlphaEarth spatial similarity. These three
  meanings of “semantic” must remain distinct.
- [CONNECTOR] Origin `points.resolve` may pick the most-observed taxon while also flagging the
  common name ambiguous, and fuzzy related candidates may still be selected. Benchmark binding
  will instead use explicit directional aliases first, verify the canonical taxon against live
  taxonomy APIs, and fail closed with a DataRequest on ambiguity/unverified fuzzy matches.

## Algebra compatibility, before evidence probes

| Origin concept | Frozen v2.2.1 treatment | Initial disposition |
|---|---|---|
| STATE / occurrence lookup | SELECT, optionally AGGREGATE | compiles |
| RELATION / proximity / containment | RELATE | proximity compiles; polygon containment needs execution evidence |
| CHANGE | binary COMPARE over aligned quantities | compiles only where connector time/grain is admissible |
| TREND | unary trend_direction over a Series | compiles; ecology adapters must emit real measurement series |
| VALUE / raster annotation | ANNOTATE | op exists, released executor is a placeholder and needs generic layer routing |
| TRANSFER | ESTIMATE with gate admissibility | partly compiles; feature≈AlphaEarth RF, envelope≈climate SDM |
| overlap / refuse | observed SELECT / DataRequest | compiles without new ops |
| multi-method agreement/conflict | claim-layer corroboration | existing ALG-008 evidence target; do not invent an op locally |
| FILTER / partitioned GROUP | not expressible generally | existing ALG-002 / ALG-003 evidence targets |
| literature cards / DOI rankings | no document/card value type | keep as discovery/source-census support until evidence forces a proposal |
| ground-truth lens / map artifact | post-evaluation verification artifact | test as answer-surface capability; possible ALG-008 evidence |
| site brain / ledger | binder and dialogue memory, not data-kernel ops | retain as origin integration requirement, outside parser IR |

Judge decision: connector functions are capabilities, not automatically algebra operations. A new
origin function is first tested as an implementation of SELECT, ANNOTATE, RELATE, or ESTIMATE. Only
an evidence-backed question that cannot preserve its meaning in the frozen tree becomes a proposal.

## Imported local assets (pending license completion)

- [CONNECTOR] `data/imported/restoration_sites.csv`: 26 point sites, site/habitat grain, source
  documented by the origin as Zenodo record 10077040. SHA-256
  `78bab6b96e592ac639b0d8a5469ad9d9927c6cf3c8497723b4afd06bb5e91862`.
- [CONNECTOR] `data/imported/lantana_occurrence.csv`: 250 occurrence rows. Origin prose calls these
  GBIF points, but the current rows identify iNaturalist research-grade observations and include
  year 2026; provenance drift must be resolved before admission. SHA-256
  `9ef7e38a26172d351567b101398795d92e2d2567c3f2b1deffd2060c532a7878`.
- [CONNECTOR] Neither copied asset is admitted as gold evidence until its upstream license,
  retrieval provenance, spatial scope, time semantics, and a live phantom check are recorded.

## 2026-07-15 — live source admission and evidence semantics

- [CONNECTOR] Five ecological source families were live-probed at Valparai, Mysuru and Bengaluru.
  Licensed 2024–2026 Lantana rows after cross-provider deduplication were 1/1/7; recent
  bbox-filtered eBird rows were 25/81/84; 2024 MODIS bbox-mean NDVI was
  0.806804/0.462235/0.413182; and the published survey snapshot correctly yielded 10/0/0 sites.
  These are phantom checks, not stable ecological facts. Full grain/licence/revision limits are in
  `data/SOURCES.md` and the machine-readable census is `coverage/source_matrix.json`.
- [CONNECTOR] Zenodo record 10077040's authoritative `01_sites.csv` matches the local four-column
  snapshot exactly and is CC-BY-4.0. Judge decision: admit the rows only as published vegetation
  survey sites. The legacy filename `restoration_sites.csv` does not establish an intervention,
  treatment, restoration date, or restoration outcome.
- [CONNECTOR] The imported Lantana CSV remains quarantined. Its rows identify iNaturalist while
  origin prose calls it GBIF, and a live GBIF check exposed mixed licences including CC-BY-NC.
  Gold execution uses live, per-record licence-filtered adapters instead.
- [SCORING] Occurrence/search rows are documented-presence evidence, never organism abundance,
  population, biomass, occupancy, or richness. A record count is admissible only when the user
  explicitly asks for records/observations/sightings. `eco-s020` exposed the unsafe alternative:
  a structurally valid count had answered “How many elephants” with API rows. The executor now
  fails that request closed as `unsupported_measure`.
- [CONNECTOR] eBird's nearby endpoint is radial while REGION is a rectangle, so every response is
  post-filtered to the bbox. A bbox beyond the endpoint's 50 km radius is explicitly partial/proxy;
  a date older than its recent-data window becomes `unsupported_time`. `YYYY-MM` endpoints use
  the actual first/last day of the month, fixing an active-wall historical-window misclassification.
- [CONNECTOR] JRC surface-water occurrence masks pixels where water was never detected. Judge
  decision: for an occurrence percentage this is a measured zero, not missingness; unmask to zero
  before point sampling and retain JRC's upstream evidence label.

## 2026-07-15 — active-wall repair decisions

- [PARSER] Exactly 15 few-shots remain in rotation. Mechanical semantic repairs are admitted only
  where the user's literal wording supplies the missing meaning: explicit trend/change endpoints,
  explicit taxon unions, named raster annotations, relation thresholds, and a RELATE tree that a
  model incorrectly absorbed into AGGREGATE. Each repair is stamped in the trace.
- [PARSER] Abstract “ecosystem health” has no canonical measurement and becomes `?indicator`;
  motive/behaviour questions become a proxy/place clarification rather than an ecological fact.
  Place-level NDVI questions do not inherit a hallucinated survey-site ANNOTATE stage.
- [SCORING] Synthesized prose initially converted 55 to “five” and sometimes omitted `modelled`.
  The synthesis auditor now rejects unsupported numerals and missing evidence labels. When the 2B
  draft fails a mechanical audit, deterministic rendering emits only the executed value/status,
  source, label and limitation. On `active-003`, 21/270 drafts used this safe fallback (12 label,
  5 value/count, 4 data-gap failures); this is recorded intervention, not hidden model success.
- [HARNESS] Development trajectory: seed ticks 0.947 → 0.958 → 0.992 → 0.981 → 1.000;
  `active-001` scored 0.970; `active-002` reached structural 1.000 but failed 20 synthesis audits;
  `active-003` reached structural 1.000 with 0 synthesis audit failures over 270 questions.
- [HARNESS] Low-cost Cursor dialect-generation jobs stalled and were terminated without admitting
  any generated question or gold. The active bank was expanded deterministically from the
  hand-audited 30-question seed across eight neutral registers, preserving the same semantics.

## 2026-07-15 — expressiveness wall

- [SPEC-PROPOSAL] Fifty deliberate probes covered FILTER, GROUP/time grain, alignment/units,
  corroboration/uncertainty, and document/causal/artifact boundaries. Most correctly became data
  requests, but three closest-tree encodings executed to silent wrong answers:
  `eco-x003` dropped “CC0 only”; `eco-x011` dropped “by species”; `eco-x017` dropped monthly grain
  and returned an annual series. These are evidence for ALG-002/003/005/007, not parser repairs.
- [SPEC-PROPOSAL] A union of records is not independent corroboration: it loses provider roles,
  agreement rules and uncertainty semantics. `eco-x031`–`eco-x040` extend ALG-008 evidence.
- [SPEC-PROPOSAL] Literature discovery, causal attribution, exportable maps, and commercial imagery
  acquisition remain separately governed capabilities. They need document/causal/artifact types or
  external authorization and must not be smuggled into SELECT/ESTIMATE merely because the origin
  agent can call such tools.

## 2026-07-15 — transfer algebra import

- [CONNECTOR] The bootstrap ESTIMATE gate was incompatible with the origin concept: it called a
  latitude/longitude donor bounding box an “envelope” and, after passing, copied donor rows into a
  target field. Judge decision: this was neither the origin's environmental gate nor a valid
  estimate and could not remain as a benchmark truth path.
- [CONNECTOR] `feature` now means nearest-neighbour analogy in the 64-band annual AlphaEarth
  embedding; `envelope` means target coverage inside the donor ranges of 19 WorldClim bioclimatic
  variables; `interpolate` requires at least five numeric point measurements and refuses targets
  outside their spatial support. Feature/climate transfer requires at least 20 donor occurrences,
  and substantial target overlap refuses modelling in favor of direct observations.
- [CONNECTOR] A passed environmental gate now runs a presence-vs-deterministic-background random
  forest in the same feature family and returns a target-bbox suitability fraction labelled
  `modelled`. Every output asks for designed absence surveys and names occurrence bias, spatial
  autocorrelation, land use, biotic interactions, and dispersal as limitations. It never presents
  pseudo-absence accuracy as ground truth.
- [HARNESS] Refusal probe: Valparai Lantana → Delhi via WorldClim had 0.0 target-envelope coverage
  and remained `gate_failed`. Success probe: a held-out micro-AOI around one donor environment had
  AlphaEarth analog fraction 0.8 and WorldClim envelope fraction 1.0; both produced modelled fields.
  The purpose of this probe was branch/runtime verification, not a biological Lantana claim.
- [HARNESS] After the connector/executor change, `active-004` again passed all 270 questions at
  structural 1.000 with zero synthesis-audit failures. Eight deterministic ecology contract tests
  cover abundance refusal, occurrence wording, empty spatial relations, licence directionality,
  minimum donor evidence, observed-overlap refusal, and interpolation/extrapolation behavior.

## 2026-07-15 — dialogue binding audit

- [PARSER] The first ecology multiturn run exposed two development-bank failures hidden behind an
  unbound hole. “Is NDVI recovering around here?” had been reduced to a spatial mean, so binding a
  place produced an incompatible-grain DataRequest instead of a trend. “How healthy is the
  ecosystem in Valparai?” correctly holed the indicator but retained invented outer
  AGGREGATE/ANNOTATE nodes, so binding NDVI still could not execute. The ambiguity scorer had
  accepted any SELECT-containing shape, making turn-one scores look green.
- [PARSER] Judge decision: a semantic repair must leave a tree that remains meaningful after its
  holes are bound. Recovery wording now restores unary trend_direction over the named NDVI series;
  an abstract health request is reduced to the grounded SELECT context plus `?indicator`, with no
  invented measurement layer. Ten unit tests now include both post-binding invariants.
- [HARNESS] On `active-005-mt`, deterministic binding filled and executed all 5/5 ecology cases.
  Model binding remained unreliable (1/5 executed correctly, plus one unbound reply), confirming
  the architecture decision that binding is code rather than a second generative parse. The full
  post-fix `active-005` wall again passed 270/270 with zero synthesis-audit failures.
- [HARNESS] Corpus compilation now requires an explicit verified-run allowlist and every structural,
  hole, estimate, execution-class, and grounding dimension to be true. It never substitutes a gold
  tree for a failed parser output. Clarification rows require green deterministic binding,
  skeleton preservation, and execution. Current corpus: 270 parse rows + 5 clarification rows.

## 2026-07-16 — untouched-bank failure taxonomy and response boundary

- [HARNESS] Epochs 029–034 were invalidated rather than counted toward saturation. The failures
  clustered into: dropped entities/unions; relation polarity, anchor, threshold, or output-grain
  loss; comparison endpoint/direction/aggregation-grain loss; place text leaking into an entity or
  failing to bind; unsupported abundance weakened to occurrence evidence; typed-hole loss; ranking
  cardinality/order/grain loss; and synthesis that returned a scalar without the requested winner.
- [PARSER] The response to those failures was to compile more surface forms faithfully into the
  already-released operations: SELECT, RELATE, AGGREGATE, COMPARE, ANNOTATE, ESTIMATE, and RANK.
  Repairs now cover compound/negated relations, explicit distances, co-occurrence record-set grain,
  taxon unions, time endpoint changes, unary trends, two-place means, three-place rankings, nominal
  dataset requests, and record-set versus count wording. These are compiler improvements, not new
  algebra operations.
- [SCORING] The initial structural scorer allowed executable but semantically wrong trees. It now
  compares entity multiplicity, places, relation signatures and thresholds, aggregate grain and
  metric, literal time endpoints, comparison method, annotation layer, estimate method, and rank
  order/cardinality. Comparison synthesis must state the compared sides and winner. Independent
  trace audit remains mandatory because solver and scorer can share a blind spot.
- [SPEC-PROPOSAL] No epoch-029–034 failure justified expanding the frozen IR schema. FILTER,
  partitioned GROUP, explicit alignment/units, corroboration/uncertainty, document values, causal
  claims, and artifact outputs remain separate evidence-backed proposals. They must not be patched
  in as parser heuristics merely to make an expressiveness question executable.
- [CONNECTOR] The untouched-bank parser failures did not add a new source family. Connector/source
  expansion came from the earlier import audit: GBIF+iNaturalist licensed occurrence resolution and
  dedupe, eBird bbox/time enforcement, Earth Engine raster routes, Zenodo survey-site admission,
  Nominatim place resolution, and AlphaEarth/WorldClim/interpolation transfer gates. Abundance
  refusal, licence filtering, evidence labels, provenance preservation, and fail-closed DataRequest
  behavior were strengthened in response to execution probes, not paraphrase coverage alone.
- [CONNECTOR] Current source boundaries remain intentional: the 250-row Lantana snapshot is
  quarantined; Zenodo points are survey sites rather than restoration outcomes; occurrence records
  are not population abundance; and unsupported document/causal/commercial capabilities do not
  become SELECT merely because the origin agent exposes a tool.

### Open follow-up backlog

- [HARNESS][OPEN-001] Reach hard saturation: one frozen epoch must survive three consecutive,
  unique, untouched banks of at least 40 questions from at least two independent families, followed
  by an independent semantic trace audit. Any solver change resets the counter.
- [HARNESS][OPEN-002] Make holdout generation resumable by checkpointing accepted slots and their
  author provenance. Do not weaken literal-equivalence, executable-gold, uniqueness, or parser-blind
  admission checks. High rejection counts currently waste author calls near 39/40 completion.
- [HARNESS][OPEN-003] Expand question discovery beyond paraphrases with independently golded
  connector-contract mutations, algebra-composition templates, dialogue/binding cases, and
  production short-answer probes. Keep generated questions separate from training rows until their
  gold and execution traces are audited.
- [HARNESS][OPEN-004] Run the final frozen bank against the Hermes DeepSeek-v4 path and the local 2B
  under identical connector snapshots, execution, synthesis, latency, brevity, grounding, and
  semantic auditing. Current green 2B runs do not yet establish a cross-model win.
- [HARNESS][OPEN-005] Train and evaluate the intended 2B LoRA only from the verified corpus; report
  base-versus-LoRA-versus-DeepSeek results and prevent final holdout leakage into training.
- [CONNECTOR][OPEN-006] Resolve or permanently reject the quarantined Lantana snapshot provenance
  and licence drift. Increase dedicated contract tests for origin connectors that currently have no
  cards or self-tests before proposing their admission.
- [SPEC-PROPOSAL][OPEN-007] Continue evidence collection for ALG-002/003/005/007/008 rather than
  changing the ecology-local frozen schema. Fable/framework review owns any eventual release.
- [HARNESS][OPEN-008] Design the later export/back-integration into origin `dss/`: retain concise
  production answers, connector richness, evidence labels, refusal behavior, and chat.sh ergonomics
  while exporting only audited algebra/compiler/connector findings. This import run must not modify
  the origin repository.

## 2026-07-16 — parallel chat integration prototype

- [HARNESS] A reversible integration candidate now lives under `integration/`. Its `chat.sh` keeps
  runtime and model as independent axes. With no flags it delegates to the unmodified origin
  `agents/hermes/chat.sh` with no added argument; `--runtime typed` invokes the local compile,
  validate, deterministic execute, and audited synthesis pipeline. The origin worktree remained
  clean throughout the smoke test.
- [HARNESS] The origin-facing allowlist locks 62 prompt/connector/card/data files at clean commit
  `efcfc77111cf30aed7d125c9c6c2fe67febf7ad3`. This is a reference manifest, not a bulk copy.
  Secrets, caches, mutable ledgers, commercial artifacts, and unadmitted files are excluded.
- [HARNESS] Same-model DeepSeek smoke evidence on an unsupported population request: both legacy
  and typed runtimes refused to invent a population number. Typed returned the precise
  unsupported-measure DataRequest in about 4.8 seconds. Legacy exhausted a three-turn cap in about
  45 seconds, called `points.py` with an unsupported `--out` argument, included explicitly unrelated
  corridor facts, and emitted an auxiliary-model warning. This is one diagnostic case, not a global
  model/runtime ranking. Full details are in `integration/runs/20260716-smoke.md`.
- [HARNESS] The local 2B typed path produced the same fail-closed population contract and a second
  smoke correctly executed a two-place 2024 NDVI comparison, named the winner, and retained the
  proxy label. Legacy 2B is intentionally unavailable until Hermes explicitly registers that model;
  the wrapper refuses to substitute its existing 122B alias. The 2B-LoRA profile is reserved but
  was not called because no LoRA is deployed.
- [HARNESS] Export remains a separate gate. The intended origin layout preserves `dss/` as the
  exact baseline and adds a sibling `dss_typed/`; only a later authorized export may minimally
  extend origin `chat.sh`, with its no-argument legacy behavior unchanged.

## 2026-07-16 — Hermes-native correction and EBTL binding

- [HARNESS] The first typed integration was the wrong shell: it used a generic Python REPL and
  therefore lost Hermes session history, the clarification gate, site persona, and short-answer
  discipline. It has been replaced. Normal typed, untyped, and no-algebra comparisons now use
  Hermes; only the explicit `--trace-json` diagnostic calls the typed pipeline directly.
- [HARNESS] Runtime, model, and context are independent axes. `untyped + ebtl + deepseekv4`
  delegates exactly to origin `chat.sh`; typed/no-algebra use an isolated `dss-eval` profile with a
  neutral SOUL and separate sessions. `--context ebtl` is explicit, while broad typed holdouts
  default to `general`, preventing site leakage into the general question bank.
- [CONNECTOR] The imported EBTL context now binds the exact source AOI
  `[78.170, 12.721, 78.197, 12.747]` and declared centre `(12.73394, 78.18344)` without geocoding.
  A new site-centre record adapter enables typed raster annotation but is obligatorily labelled a
  point proxy, never whole-AOI evidence. WorldCover v200 returned modelled `shrubland` at that one
  point; this does not establish the restoration site's complete land-cover composition.
- [HARNESS] DeepSeek typed multi-turn quality passed the smoke: opening `tell me about ebtl` asked a
  four-way clarification with zero tools; resumed choice `1` named shrubland, WorldCover v200, the
  coordinate, one supporting point, and the point-versus-AOI limitation. Exact origin untyped also
  clarified well but loaded skill/playbook tools first and retained its auxiliary `qwen` alias 404.
  No-algebra fabricated “private grassland” and promised observed numbers without sources.
- [MODEL] Base local 2B reached the correct shrubland finding after clarification, but mislabeled a
  modelled result as partly observed and emitted a stray meta sentence. This is retained as a LoRA
  training/evaluation target rather than hidden by deterministic post-editing. The local endpoint's
  actual context is 8K and it has no automatic tool parser; short Hermes diagnostics use an
  isolated 64K compatibility declaration, 2,048-token output cap, and zero model-visible tools.
  This is not a long-context compatibility claim.
- [MODEL] `qwen2b-lora` now fails preflight before a shell or retry loop starts. The endpoint lists
  only `qwen3.5-2b`; requested `qwen3.5-2b-lora` is not deployed.
- [GOVERNANCE] Independent Codex review agrees that executor-only unit/grain metadata and temporal
  alignment should precede parser-surface growth; restricted FILTER remains coherent after typed
  field declarations; CORROBORATE remains deferred pending ancestry metadata. Dissent: the proposed
  GROUP representation assumes an existing keyed Field, but released `AGGREGATE by:space` returns a
  scalar. The grouping need is accepted; syntax waits for a keyed-result RFC and downstream matrix.
  The review packet and both independent reviews are sector-neutral.

## 2026-07-16 — matched snake dialogue and primary-source import

- [HARNESS][FIXED] Earlier `typed` Hermes sessions were not typed: the bridge lived under the
  isolated profile, but Hermes plugin discovery still used the default home. The launcher now sets
  the isolated `HERMES_HOME`, and an execution middleware persists the audited typed result before
  provider streaming can expose an ungrounded paraphrase.
- [SOURCE] The origin repository contained a stronger source than either chat found: pages 23–24 of
  `Faunal survey 2024.pdf` document 14 site snake species, separating three September 2024 VES
  encounters from eleven earlier property records not encountered in that survey. The typed import
  preserves rows, status, method, dates, pages, author, and source SHA-256.
- [EVALUATION] On identical four-turn real Hermes sessions, typed Qwen 2B and typed DeepSeek both
  returned the complete, correctly distinguished inventory in 21.243 s and 25.084 s respectively.
  Origin DeepSeek took 555.973 s, initially converted a GBIF taxon-key mistake into 1,658 supposed
  local snake records, later identified them as peanut worms, and never found the local survey.
  See `integration/eval/runs/20260716-snake-head-to-head.md`.
- [CONNECTOR] Origin semantic discovery genuinely uses bge-small embeddings, but the matched query
  returned irrelevant corpus cards because the decisive local document was not indexed. The
  original trace's likely-species list came from model memory; regional counts were later observed,
  but an environmental transfer gate was not executed.
- [ALGEBRA][OPEN-009] The released typed system can gate an estimate for one named taxon, but cannot
  yet represent category discovery → grouping by species → ranking candidates → one gated transfer
  per candidate. This is concrete pressure for ALG-003's keyed-result contract. Until governance
  resolves it, exhaustive unrecorded-species requests must fail closed rather than masquerade as a
  typed shortlist.
- [HARNESS][OPEN-010] Surface typed bridge provenance through Hermes `/why`, score the transfer
  dialogue after the keyed-result decision, and add the primary source to an exported semantic
  corpus only in the later authorized `dss_typed/` path.

## 2026-07-16 — locked production connectors and five-topic equivalence wall

- [CONNECTOR][FIXED] The origin connector directory is now mechanically mirrored under
  `integration/origin/connectors` (65 non-cache files). Typed implementations no longer reproduce
  the fire, land-cover, or greenness calculations: thin adapters verify the origin-lock SHA and
  call exact `fire.py`, `landcover.py`, and `greenness.py` functions. The origin repository remains
  unchanged.
- [CONNECTOR][FIXED] Taxon occurrence selection now delegates to exact origin `points.get`, which
  merges GBIF, iNaturalist, and paper-data points. An empty local result invokes exact origin
  `discovery.search`; the ranked bge-small card matches are retained as candidate datasets and are
  never relabelled local observations without extraction and a spatial check.
- [CONNECTOR][INCOMPATIBILITY] Exact reuse exposed a production schema loss: the `points.py` common
  CSV omits record URLs, licenses, quality flags, and full dates. The typed adapter therefore no
  longer claims returned records are license-filtered. `points.get` also cannot enforce a time
  window, so time-bounded typed requests fail closed. Back-integration should enrich the production
  point schema or hydrate candidates through an evidence-preserving layer.
- [HARNESS][FIXED] Typed Hermes registers and programmatically dispatches `typed_evaluate`; each
  governed connector execution is printed as a `🔌` event. Hermes's footer remains `0 tool calls`
  because it counts model-authored calls, not the runtime dispatch. Falsifying session rows solely
  to change that counter was rejected.
- [HARNESS][FIXED] `--trace-json` previously ran on the host and could omit semantic discovery
  because the production embedding environment lives in the container. The diagnostic now runs
  against the same deployed runtime; its elephant trace contains both `origin.points.get` and
  `origin.discovery.search` and five unadmitted discovery leads, matching conversational chat.
- [EVALUATION] Literal origin DeepSeek and typed Qwen 2B completed matched resumed sessions for
  fire, elephants, land cover, restoration change, and snakes. Fire/occurrence/discovery/
  landcover/greenness use the same production functions; snakes deliberately use the stronger
  page-addressed local survey. Typed was faster in all five diagnostics and materially safer on
  period, scale, evidence class, and causal claims. Origin remained more capable at open-ended
  exploration but incurred tool retries and unsupported synthesis. Full judgments and artifact
  links are in `integration/eval/runs/20260716-origin-equivalence-wall.md`.
- [HARNESS][OPEN-011] This is a five-topic slice, not global connector parity. Add thin typed
  adapters plus matched dialogue cases for terrain, water, eBird, paper extraction, prediction,
  and other admitted production connectors before claiming system-wide equivalence.
- [HARNESS][OPEN-012] Complete dynamic category discovery as an evidence pipeline: semantic card
  retrieval → typed extraction → spatial/source validation → keyed candidate result → one explicit
  transfer gate per candidate. The current frozen algebra safely supports discovery leads but not
  the full category-to-ranked-transfer composition.

## 2026-07-17 — repaired showcase stop and dynamic sparse-evidence routing

- [CONNECTOR][FIXED] Dynamic arachnid discovery no longer asks the model to invent a shortlist.
  It queries the higher taxon locally and in a declared dry-Deccan donor region, derives named
  candidates from returned GBIF rows, checks exact-origin occurrence support, then executes one
  explicit climate and AlphaEarth gate per candidate. One taxon was already locally observed;
  three regional candidates failed the feature gate and were not promoted to EBTL expectations.
- [SOURCE] The typed site ledger now joins page-addressed local primary evidence (14 snakes,
  67 birds, two indirect elephant passage events, nursery snapshots, and qualitative soil notes),
  exact-origin production connectors, a regional Dryad Lantana frugivory dataset
  (`10.5061/dryad.gc6dm`), a regional arachnid semantic lead (`10.5281/zenodo.10596480`), and a
  coarse NASA POWER/MERRA-2 soil-wetness proxy. Every response retains local, bbox, regional,
  proxy, or transfer grain rather than flattening these into “at the site.”
- [SCORING] A frozen 12-case repaired showcase compared real resumed Hermes sessions: typed Qwen
  2B scored 110/120 versus origin DeepSeek-v4 at 69/120 (+59.4% relative), with zero versus nine
  critical errors. Median complete-case latency was 22.548 s versus 227.714 s. Cursor
  `gpt-5.3-codex-low-fast` supplied a read-only advisory rubric score; hashes, mechanical sums,
  latencies, and Codex's critical-error audit are frozen in
  `integration/eval/runs/20260717-showcase-epoch.json`.
- [SCORING] Origin failures were substantive rather than merely stylistic: false absence for
  locally documented snakes, venomous snakes, and elephant passage; bbox/property conflation;
  unsupported bird–invasive, snake–tree/prey, and nursery-function links; and an unsupported
  arachnid measurement. Typed answers instead reported absence of public records as sampling
  absence, bounded transfer as a hypothesis, and requested property-scale measurements where the
  evidence did not support a claim.
- [HARNESS] The showcase stop is passed, but it is explicitly not SATURATION.md closure. These
  cases drove repairs and therefore are not untouched post-freeze holdouts. Hard saturation still
  requires the existing three consecutive independent holdout protocol, followed by semantic
  audit; LoRA comparison remains blocked because `qwen3.5-2b-lora` is not deployed.
- [MODEL] A larger model is most useful after deterministic evidence assembly as an offline
  question author, advisory judge, or verifier. In the matched production traces, putting a large
  free-form planner before connector work increased retries and unsupported synthesis without
  finding the decisive local sources. This does not preclude a later governed planner experiment,
  but connector execution and evidence gates remain deterministic.

## 2026-07-17 — basic clarification-choice regression

- [HARNESS][FAILURE] The repaired showcase asked for birds and snakes directly but never selected
  the generic “wildlife” branch offered by the opening menu. Consequently, “wildlife, what is seen
  there” canonicalized to `wildlife species` and fell through to `no_connector`. The prior score
  was valid for its frozen questions but was not evidence that the menu itself worked end to end.
- [SOURCE] Re-reading the complete local `Faunal survey 2024.pdf` exposed another import omission.
  It reports 54 butterfly taxa, 42 odonates, 67 birds, and 33 documented herpetofauna taxa. Of the
  herpetofauna, 20 were encountered in the 2024 VES (7 frogs, 9 lizards, 3 snakes, 1 turtle) and
  13 were earlier property records not encountered then (2 lizards, 11 snakes). Two elephant
  passage events remain separate indirect newsletter evidence.
- [CONNECTOR][FIXED] Generic EBTL wildlife/fauna/animal requests now resolve to a page-addressed
  `wildlife_inventory` local-evidence entity. The answer preserves survey group, method/date,
  2024 detection versus older-property status, indirect elephant evidence, and the fact that taxa
  or checklist counts are not population estimates.
- [PARSER][FIXED] Natural replies for every opening-menu branch are deterministic: vegetation,
  wildlife/fauna/animals, fire, and restoration, as well as numeric choices 1–4. Persisted fire
  context now binds follow-ups phrased as “what years?” or “is that a forecast?”; this repaired a
  second basic failure found by the new menu audit.
- [HARNESS] `integration/eval/basic_clarification_cases.json` is now a separate regression bank.
  Real resumed typed-Qwen sessions pass wildlife, vegetation, fire, and restoration choices plus
  evidence-boundary follow-ups. After the fixes, all 12 previous showcase cases reran on current
  code with zero failed turns and normalized answers identical to their scored frozen artifacts.
  This is regression closure, not SATURATION.md holdout credit.
- [EVALUATION] On the exact four-turn wildlife conversation, typed Qwen completed in 24.859 s and
  used the local faunal survey. Untouched origin DeepSeek took 241.713 s, repeated the previously
  diagnosed 1,658-record unresolved-taxon failure, called the analysis AOI the site, then asserted
  an unsupported 271-record 2024 breakdown and named-species counts. Its final distinction between
  observation uploads and population was sound, but it did not repair the earlier fabricated
  measurement or spatial conflation. Artifacts: `20260717-092145-basic_wildlife_choice.json` and
  `20260717-093126-basic_wildlife_choice.json`.

## 2026-07-18 — general compiler/executor/responder pilot accepted

- [PROCESS] Work previously stopped at a selector milestone even though the full pilot stop had
  not been checked. That was premature. The stop is now explicit in `hermes_bench/FRAMEWORK.md` and
  requires frozen conversation quality, evidence audits, live Hermes persistence/resume, an origin
  comparison, an evidence-based 2B-versus-LoRA compiler decision, and green repository checks.
- [ARCHITECTURE] Hermes is the conversation shell, not the algebra executor. On each typed turn its
  plugin dispatches a real `typed_evaluate` call. A semantic selector chooses from declared
  capability metadata; Qwen 2B emits/binds the smallest released IR; Python validates the IR,
  invokes pinned connectors, applies units/grain/lineage and transfer gates, and builds an audited
  evidence pack; Qwen 9B turns only that pack into plain language. No ecology phrase regex or
  topic-specific canned answer was added to the live plugin.
- [ALGEBRA] The pilot did not add an unreviewed operation. It strengthened execution contracts
  around count grain, measurement scope, absence polarity, declared thresholds, evidence labels,
  interaction boundaries, and audited dialogue history. Dynamic category discovery is represented
  as a governed connector composite: local higher-taxon query, regional candidate derivation from
  returned records, exact occurrence checks, and one feature/climate gate per candidate. The
  composite returns ordinary released IR values plus provenance; it is not a hidden new algebra op.
- [SOURCE][CONNECTOR] The typed runtime uses a hash-pinned mirror of the origin production
  connectors at commit `efcfc77111cf30aed7d125c9c6c2fe67febf7ad3` and leaves the origin tree
  untouched. It adds page-addressed local EBTL evidence omitted from semantic search: 67 birds,
  14 property snake records with three direct 2024 VES encounters, four venomous property records,
  two indirect elephant-passage reports, nursery snapshots, invasive-management notes, and soil
  observations. It also adds regional bird–Lantana and arachnid evidence, while keeping public-bbox,
  regional, proxy, modelled, indirect, and local grains distinct.
- [CONNECTOR] Exact origin adapters remain the provider path for fire, points, land cover,
  greenness, and semantic discovery. Fire output is now described as sensor-detected pixel-fire
  days over its actual analysis footprint, not events or calibrated future risk. Occurrence zeros
  never prove absence. Transfer candidates require the declared 0.5 feature-fraction and 0.8
  climate-envelope thresholds, and rejected candidates remain rejected.
- [SCORING] The immutable `v18_acceptance` 14-turn bank produced the intended statuses/modes on all
  14 turns and 14/14 passing audits for both answer arms, with zero fallbacks. Blind scoring gave
  the selected Qwen-9B audited responder arm 1.964/2 and zero critical errors; the deterministic
  renderer control scored 0.929 and one critical error. This isolates the value of synthesis-out
  after deterministic evidence assembly.
- [MODEL] The LoRA-9B binder/compiler edge run took 492.314 s for 10 turns (49.231 s mean,
  31.970 s median), with no semantic-selection advantage over the Qwen-2B run at 36.582 s total
  (3.658 s mean, 0.819 s median). The pilot therefore keeps Qwen 2B for last-mile algebra binding,
  Qwen 9B for semantic selection and response, and DeepSeek-v4 only as the selector verifier. A
  larger free-form model is not permitted to execute connectors or rewrite evidence classes.
- [AUDIT] Development epochs before `v18` were invalidated when they exposed real semantic faults.
  A later inspection of `v18` found a non-critical “58 named species” wording error and the edge
  bank exposed subject-only evidence being used for an unsupported elephant–Lantana relation. The
  frozen artifacts were not rewritten. Current code distinguishes 58 occurrence records from 31
  named taxa, rejects unknown local interaction as impossibility, fails closed on atomic selector/
  verifier disagreement, and still admits explicitly declared composites such as arachnid transfer.
- [HERMES][FIXED] This supersedes the earlier note that Hermes must show `0 tool calls`. Typed calls
  now create real assistant/tool ledger records through Hermes' own `SessionDB`. Resume paths lacked
  a CLI database reference, so the session ID is now handed to the plugin and it falls back to the
  same Hermes storage API. Live session `20260717_230145_735093` persisted five typed tool results,
  resumed with 24 total messages, and correctly kept Spectacled Cobra as an older property record,
  not one of the three direct September 2024 sightings. The bridge also translates only executed
  provenance into the origin `/why` ledger; the live command now reports 14 site-evidence rows for
  the last snake answer instead of “No data steps recorded.”
- [EVALUATION] The practical comparison is already decisive on the matched failure classes. Origin
  DeepSeek did not find the page-addressed local fauna evidence through embeddings, spent many tool
  calls/minutes on broad public searches, and at times conflated bbox records with the property.
  Typed reuses those production connectors but adds the missing local corpus and evidence gates;
  it is materially more complete and safer for wildlife/snakes/fire. No new hour-long origin run
  was launched, and `/home/beeps/src/github.com/bprashanth/idlisseus` was not modified.
- [STOP] The compiler/responder pilot stop is met. This is not `SATURATION.md` practical or hard
  saturation, does not authorize LoRA retraining or deployment claims, and does not export changes
  into origin `dss/`. Back-integration remains a separately reviewed, explicitly authorized step;
  the current parallel runtime is the reproducible candidate.

## 2026-07-18 — composed relation and independently gated transfer

- [HARNESS][ROOT CAUSE] `RELATE` and `ESTIMATE` failures were caused by atomic capability
  selection and destructive leaf binding, not simply by missing connectors. The compiler could
  produce a composed tree, but the routing boundary replaced it with one selected dataset.
- [HARNESS][FIXED] Capability retrieval now selects the minimal operator/data/support ingredients;
  the contract binder fills declared slots, removes non-schema metadata, aligns only explicitly
  declared supports, and never changes a valid composed root.
- [ALGEBRA] Occurrence `RELATE` returns bidirectional denominators and match rates under an explicit
  threshold and is permanently labelled a spatial record proxy. `ESTIMATE` of that relational
  grain fails closed; each taxon must instead pass an independent donor-to-target gate.
- [CONNECTOR] Transfer now calls the locked origin `predict.py` through a thin typed adapter. A
  locally reproduced predictor that returned 0.4337 against production's 0.039 was discarded.
  Typed and origin now both return the 2023 elephant suitability fraction 0.039 on the shared path.
- [ANSWER AUDIT] A suitability fraction is the fraction of target analysis cells classified
  suitable, not calibrated occurrence probability, occupancy, abundance, or prevalence. The
  audit now rejects “low fraction means limited presence” and falls back to measurement-faithful
  prose.
- [EVALUATION] Real resumed session `20260718_185102_333e6c` completed the four-turn relation,
  interpretation challenge, elephant estimate, and independent Little Cormorant estimate in
  79.571 s. The matched origin DeepSeek-v4 run took 326.205 s and added unsupported shared-habitat
  and acreage interpretations. Typed preserves the origin numerical estimator while improving the
  evidence boundary.
- [GOVERNANCE] Arbitrary bounded search support is a genuine algebra gap because search radius and
  relation threshold are independent. The local experimental `BUFFER` node is recorded as ALG-015
  with a domain-neutral review packet; it is not promoted to `kit/` or a released manifest.
- [STOP] The narrow RELATE/ESTIMATE composition stop is met. The final wall passes 190 ecology
  tests, 18 framework tests, the Hermes CLI contract, governance validation, syntax/JSON checks,
  diff integrity, and origin read-only status. This is not ecology saturation: generic
  open-category discovery, systematic literature expansion, remaining ALG-015 geographic/canonical
  semantics, and untouched holdouts remain open.

## 2026-07-19 — reviewed BUFFER contract implemented conditionally

- [GOVERNANCE] Fable accepted the ALG-015 semantic core conditionally. The kit candidate is now
  version-gated as `v2.4.0-draft`; default v2.3 behavior and the release manifest are unchanged.
- [HARNESS][FIXED] Removed silent cross-operand buffer copying. Identical explicitly written
  supports canonicalize to one value, intentionally different supports remain different, and
  nested concrete radii add.
- [EVIDENCE] `method:bbox-approx`, approximation status, source support, radius, and result bbox
  now survive execution. Dateline/pole cases fail closed and response audits require approximate
  search-extent wording.
- [LIVE] A natural Qwen-2B typed query preserved a 100 km search bbox separately from a 10 km
  relation threshold, executed both point connectors, returned both denominators/directions, and
  passed the response audit in 9.186 s.
- [CORPUS] Ten neutral ALG-015 golds validate and fixture-execute 10/10; their generated training
  rows are isolated from holdouts in `kit/conformance/buffer_parse_v2.4.jsonl`.
- [MODEL][OPEN] The untrained base 2B matches 5/8 required canonical parses; the existing merged
  9B adapter matches 4/8. More prompt-specific routing was rejected. A trained v2.4 model bundle
  and green parser wall remain release conditions, so ALG-015 is implemented but not validated.
- [REGRESSION] The implementation wall passes 193 sector tests, 29 framework tests, Hermes CLI,
  governance, syntax/JSON, diff integrity, and origin read-only checks. The explicit parser-perfect
  promotion command fails as intended; the released manifest remains at algebra v2.3.0.
