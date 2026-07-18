# Ecology active wall — 2026-07-15

## Why

The imported ecology system had to be tested as a data-and-meaning pipeline, not merely as a JSON
parser. A short seed could prove the adapters work but could not pressure ambiguity, paraphrase,
source gaps, evidence labels, or answer rendering enough for a future 2B LoRA curriculum.

## What ran

Thirty hand-authored, execution-admitted seed questions were expanded through eight
semantics-preserving, parser-neutral registers to 270 unique active questions. The wall covered
state, value, relations, change, trend, ranking, transfer, composites, ambiguity, behaviour,
adversarial abundance wording, and source gaps. A separate 50-question expressiveness bank tried
requests that the frozen algebra might not preserve.

The local `qwen3.5-2b` parsed every active question. The deterministic executor used live cached
GBIF, iNaturalist, eBird and Earth Engine responses plus the admitted Zenodo survey-site snapshot.
Every run also synthesized a short answer and mechanically audited numerals, evidence labels,
source gaps, and unsupported claims.

## What we found

The seed moved from 0.947 to 1.000 over five ticks. The first full wall scored 0.970 and exposed
month-window parsing, NDVI routing, behaviour holes, taxon union loss, ecoregion annotation loss,
hyphenated layer aliases, and relation-tree absorption. After structural closure, the second wall
still had 20 answer-surface failures, including “five” for 55 and dropped `modelled` labels. A
strict audited fallback closed those unsafe cases. `active-003` is 270/270 structurally correct
with zero synthesis audit failures; 21 drafts used the explicitly recorded fallback.

The expressiveness wall found three silent-wrong witnesses. A plain SELECT ignored “CC0 only,” an
aggregate ignored “by species,” and annual NDVI silently replaced requested monthly grain. Those
cases became append-only proposals rather than local changes to the frozen IR. Document search,
causal claims, artifact export, and paid imagery were kept outside the data kernel.

## Status

This is development regression closure, not hard saturation. Transfer gates, free-form comparison
arms, corpus purity, a code freeze, and three untouched post-freeze banks remain before a stopping
claim.
