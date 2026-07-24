# Evidence-chain maps and model requests — 2026-07-23

## Why

An Idli Insight answer could sound careful while still stopping too early: a model-generated taxon
was not always searched through admitted sources, discovered datasets were not reusable by a later
operation, a failed distribution model produced a vague request for more data, and users could not
turn a missing predictor into a structured T4GC request. The old Lantana-only literature skill also
made an arbitrary Eucalyptus question look as if it had searched the wrong subject.

The target chain was therefore explicit: a model may propose a labelled candidate, but an admitted
connector must return it before it becomes downstream input; source material then passes independent
sample and environmental gates; the system returns an estimate, source-backed protocol, or precise
field collection design with an audit trail.

## What changed

The frozen twelve-skill benchmark catalog was left unchanged. Six runtime skills were layered over
it: query-bound ecology discovery, generic two-taxon proximity, repository dataset inspection,
source-backed protocol creation, gated field-map creation, and structured T4GC model requests.
Discovery uses the locked OpenAlex, Zenodo, Dryad and local semantic connectors concurrently.
Session-scoped handles bind discovery to inspection and inspection to protocol creation. Exact
Dryad DOI matching normalises common DOI forms and makes one bounded same-query retry after a
transient empty file list.

The proximity skill was added after the frozen full-bank run exposed a real operation gap. It emits
a normal `RELATE` IR with the declared distance threshold and preserves both input denominators.
`donor belt` now deterministically resolves to the existing `dry-Deccan donor belt`; nearby records
remain explicitly distinct from interaction, shared habitat and temporal co-observation.

The field-map skill retrieves and gates taxa independently. Only an explicitly declared vegetation
entity may use the locked invasive-plant surface, and only after its estimate gate passes. When no
fine surface is admitted, the output is a spatially balanced set of stable `FIELD-XX` confirmation
points, not a fabricated overlap. The self-contained HTML includes matching CSV and GeoJSON
downloads and contextual Sentinel-2 imagery labelled as context rather than taxon evidence.

Dataset codebook columns are extracted deterministically and grouped by declared source file.
Protocol creation requires one source table when several are present, keeps those columns separate
from programme-added effort fields, and embeds the blank CSV in the authenticated Idlisseus document
panel. Model-visible skill results now expose only labelled document links and public metadata, not
local artifact paths.

T4GC requests now record the response variable, candidate predictors, labels, spatial extent and a
measurable validation target. Filing remains an explicit user action.

## Live findings

- `Eucalyptus bird seed dispersal` returned query-bound leads across OpenAlex, Zenodo, Dryad and the
  local corpus. The chat separated a Lantana plant-disperser dataset from Eucalyptus evidence instead
  of laundering it into a claim.
- Lantana had 338 donor records and no target records. Its climate envelope passed, but the
  AlphaEarth feature analogue failed. The map therefore returned nine labelled balanced
  confirmation points. It did not claim a modelled hotspot.
- Dryad DOI `10.5061/dryad.gc6dm` was discovered, inspected and converted into a protocol based on
  the declared `TWdata.csv` columns. The source warning that `NA` means “not observed” was retained.
- A live current-fire T4GC request was filed in one turn with weather, fuel and recent-fire
  predictors plus Brier score, calibration and spatial-block validation targets.
- Warm field-map turns were about 35 seconds; the first cold run was about 102 seconds. A clean
  protocol turn was about 48 seconds and the structured model-request turn about 23 seconds.

## Benchmark and claim boundary

`narrative/benchmarks/evidence-chain-map/` contains five multi-turn conversations and four declared
arms: Codex native, Codex with explicit algebra backpedalling, Codex followed by DeepSeek-V4, and
Codex followed by the observed local `lora9b004d` endpoint. The runner records complete audits,
answers, verifier decisions, latency and contract checks without starting a model server.

The smoke run is development evidence only. This work has not completed the breadth, freeze and
untouched-holdout requirements in `SATURATION.md`, so no practical or hard saturation claim is made.

The completed `overnight-001` run contains 128 scored turns: five conversations, four arms and two
unchanged passes. Native scored 0.796 mean with 75% exact replay; algebra/backpedal scored 0.692;
DeepSeek-V4 scored 0.719 with a 200.4-second end-to-end p95; local `lora9b004d` scored 0.803 but
reproduced only 50% of turn scores and had a 208.2-second p95. No arm met the less-than-0.02
pass-mean-change stop condition, so the run is reported as development evidence, not an operational
stop or saturation result.

The frozen run identified the missing generic relation operation. After adding it, the isolated
`postfix-relation-001` native replay scored all eight turns across two passes at 1.000 with 100%
exact replay. This is a narrow repair result, not a retroactive rewrite of the frozen scores. The
runner's semantic checks were also fixed for Markdown emphasis (`does **not** prove`) and for an
explicit “should not claim ... works better” outcome boundary; raw frozen scores remain preserved.

The Eucalyptus replay exposed a subtler failure that the operation-count score initially rewarded:
a general hornbill seed-dispersal dataset was used as if it linked hornbills to Eucalyptus. The
planner contract now requires a single returned source to connect the candidate, focal entity and
requested relation. A general paper is only a labelled search seed until a direct follow-up search
returns that connection. The subsequent lineage smoke correctly declined bird occurrence and
estimation when no direct Eucalyptus source was returned. This safer abstention scores lower under
the frozen rubric, so direct relation lineage must become an explicit next-bank dimension.

The same replay verified a useful failed-gate map branch. When only one admitted named taxon exists,
the field-map skill returns stable one-taxon confirmation points and states that the result is not
two-taxon overlap. Both passes emitted map, GeoJSON and CSV. A case-sensitive CSV scorer check was
fixed for future runs; frozen scores were not changed.

Browser verification caught one map-navigation integration defect: a `#map-...` click was reaching
generic session routing after the document handler. Semantic entity links now capture the click,
map hashes are excluded from session routing, and read-only map/protocol documents preserve active
Chat mode. Desktop and narrow screenshots cover current-skill activity, the compact Why panel,
map side panels and protocol side panels.

After handoff, the basic prompt “what can you tell me about elephants at EBTL” exposed a missed
routing regression: the agent ran literature discovery twice despite two local source-linked
passage records already being admitted. Connector-level tests covered the evidence but the new
multi-turn bank had no local-site-first agent test.

The first repair was species-specific and was rejected as the wrong abstraction. It was replaced by
`local-site-evidence-search`: a site- and taxon-neutral skill backed by an organisation adapter over
seeded local evidence categories. Local-site questions now use this operation before literature or
public occurrence discovery. The EBTL adapter finds the June 2023 and May 2024 elephant passage
records, but the same skill also searches seeded survey, bird, snake, nursery, soil and summary
evidence. Site aliases are runtime configuration, and a registry non-match never becomes absence.

The failed local semantic search had a separate environment cause. The bridge exported its corpus
as `CODEX_NATIVE_CORPUS`, while the discovery subprocess read only `CORPUS_CARDS`; because
`fastembed` was installed on the host, the process did not fall back to Hermes and tried the
container-only `/opt/data` corpus and cache paths. Corpus and cache are now explicitly passed into
the host subprocess. A real Idlisseus-venv search over all 256 cards completed successfully.
