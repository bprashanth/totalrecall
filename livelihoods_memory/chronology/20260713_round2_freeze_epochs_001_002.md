# Round 2 freeze epochs 001–002 — failed blind sequences

## Epoch 001

The first freeze followed a 306-question development wall (214 broad, 40 neutral, and the 52
Round-1 questions). Holdout 001 was created only after the checksum manifest. It scored 0.965 in
the ordinary harness but only 30/40 under canonical semantic audit. The epoch was therefore
invalidated; its score is not saturation evidence.

The failures exposed answer-form loss, named behavior proxies, conjunctive spatial constraints,
comparison mode, transfer typing, and region binding. After disclosure, 39 admissible cases became
`round2-h1-dev.json`; one ambiguous/bad gold was excluded. Repairs were made and the entire active
wall rerun.

## Epoch 002

Epoch 002 froze 345 development cases. Holdout 002 was generated independently after that freeze,
pre-audited, checksummed, and run once. It scored 0.947 ordinarily and 30/40 semantically. The
epoch was again invalidated and does not count toward the required three-holdout sequence.

Seven mismatches were solver/compiler failures: employed/employment morphology, transfer envelope
typing, deictic-region invention, behavior-proxy loss, two forms of three-entity spatial
conjunction, and negated proximity. Three were gold defects: a source-confused informal-employment
question, a conditional fallback whose direct branch was available, and a two-hole comparison
whose operands were indistinguishable. The 37 admissible disclosed cases now form
`round2-h2-dev.json` and pass ordinary plus canonical audit.

## Pre-epoch-003 guard

The active wall is now 382 questions over four source families, ten question types, 17 unique
skeletons, 57 RELATE occurrences, 167 comparisons, 33 ranks, and 13 estimates. The four Round-2
development banks (330 questions) and seed/indirect legacy banks pass ordinary scoring; all
Round-2 banks pass canonical audit. Two old `gen-001` golds remain explicitly classified as gold
defects: an existential question golded as a record-returning relation, and a statistical RANK
golded with executor-invalid record aggregation. They are retained for history and ordinary
regression, not counted as strict semantic failures of the current compiler.

Epoch 003 begins only after this guard and a new manifest. Its holdouts must be untouched and no
core change may occur between them. Any failure that causes a repair resets the sequence again.
