# Ecology dialogue and corpus audit — 2026-07-15

## Why

Turn-one ambiguity scores only prove that a parser asked something. They do not prove the holed
tree becomes the intended executable query once the user replies. The training corpus also needed
an explicit purity boundary so old development failures could not leak in through a broad run scan.

## What we found

The first five-case dialogue run revealed two latent errors. A recovery question became a spatial
mean instead of a trend, and an abstract ecosystem-health question retained a fabricated
`ecosystem health` annotation outside its indicator hole. Both looked acceptable while unbound and
failed only after mechanical substitution.

The repairs now preserve post-binding meaning: recovery is a unary trend over NDVI, and ecosystem
health is a simple SELECT with an indicator hole and the grounded place. Mechanical binding then
executed all five cases. A second model call was worse: only one of five model-bound trees executed
as intended, generally because it copied the entire reply into an entity or place. Binding remains
deterministic code.

The 270-question active wall was rerun after the change and remained 1.000 with zero answer-audit
failures. Corpus compilation now reads only an explicit verified-run manifest, requires every
honesty/behavior dimension to pass, uses only the parser's own verified tree, and admits a dialogue
row only when mechanical binding validates, preserves the skeleton, and executes correctly. The
result contains 270 parse rows and five clarification rows.
