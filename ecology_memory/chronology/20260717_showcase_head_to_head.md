# 2026-07-17 — repaired showcase head-to-head

## Why

The user's live typed chat answered an explicit fire request with a generic site clarification and
then a `no connector` error. Earlier 2B turns fabricated snake taxa and false absences. The origin
Hermes shell was visibly calling production tools and often produced a better conversational
answer. The required outcome was therefore not another unit test: it was a real, resumed,
multi-topic Hermes comparison that first reached origin equivalence and then surpassed it with
stronger evidence boundaries.

## Failure sequence and repairs

The first integration had reimplemented connector behavior and did not place execution inside the
Hermes path. Production connectors were copied unchanged into the reversible integration tree,
pinned by SHA, and wrapped rather than rewritten. Typed dispatch now prints every governed
connector execution. Hermes's final `0 tool calls` remains honest: it counts model-authored calls,
while the typed runtime dispatch is programmatic because the shared local vLLM has no OpenAI tool
parser.

Broad topics were then repaired from evidence outward. Fire uses exact-origin MODIS functions and
keeps exact AOI active-fire history separate from a 5 km exposure buffer and from any future-risk
forecast. Snake, bird, elephant, nursery, and soil answers first consult imported local documents.
Regional literature and occurrence records are fallbacks or transfer evidence, never silent
substitutes for local observation. Dynamic arachnid category discovery starts at a higher taxon,
derives candidates from returned records, and applies explicit environmental gates before any site
expectation can be stated.

The fire and bird follow-ups were rerun last. “Risk of fire, same thing right?” now receives a
direct yes while distinguishing historical pressure from forecast. The bird dialogue maintains a
local 67-species survey, regional Dryad fruit-swallowing observations, and public plant bbox points
as three different evidence grains across four turns.

## Frozen comparison

Twelve conversations covered site overview, snakes/cobras, elephants/Lantana, invasive-paper
transfer, soil dryness, fire risk, nursery species, venomous snakes, arachnids, snake habitat
requirements, birds/invasives, and site evidence boundaries. Both arms used real Hermes resumed
sessions. Candidate was typed Qwen 2B; baseline was the untouched origin DeepSeek-v4 shell.

The five 0–2 dimensions were correctness, provenance/grain honesty, connector/search adequacy,
multi-turn relevance, and concise/actionable response. Critical errors were gated independently.
A read-only low-cost Cursor judge produced an advisory score, which Codex audited and mechanically
recomputed. Candidate scored 110/120 versus 69/120 (+59.4%), with zero versus nine critical errors.
Median complete-case latency was 22.548 s versus 227.714 s; total time was 299.668 s versus
3048.675 s. The exact code and trace hashes are frozen in
`integration/eval/runs/20260717-showcase-epoch.json` and can be checked with
`integration/eval/verify_showcase_epoch.py`.

## Interpretation and next state

This meets the user-approved repaired-showcase stop and is appropriate for the meeting demo. It is
not a hard-saturation claim: the questions were used during repair, so they cannot count as
untouched holdouts. The next state remains a frozen candidate facing three independent untouched
banks, broader production-connector parity, and a base/LoRA/DeepSeek comparison once the LoRA is
actually deployed. No origin file or shared model/container state was changed.
