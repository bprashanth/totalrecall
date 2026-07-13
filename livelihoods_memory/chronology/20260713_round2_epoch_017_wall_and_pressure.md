# Round 2 epoch 017 — wall correction and H23/H24 development pressure

## Why this stage exists

H22 retired epoch 016 and changed parser, executor, schema validation, and scoring behavior. Before
another freeze, every disclosed bank had to be rerun. H23 and H24 had already been authored without
seeing parser output, but they predated the H22 repairs. They therefore cannot be post-freeze blind
evidence. This stage preserves them as development pressure while keeping the saturation counter at
zero.

## Full-wall correction

The first epoch-017 wall exposed five latent outcome expectations that the newly fail-closed
executor correctly rejected: two all-null address annotations in H5, two all-null operator
annotations in the wide Round-2 bank, and a one-point ILO trend in H15. The original immutable
questions remain registered as defects. Their disclosed development copies now expect a typed
DataRequest instead of a grounded Answer.

The corrected wall contains 1,076 rows across 25 banks. It passes 1,074/1,074 eligible rows under
both the ordinary harness and strict canonical audit. The only two overall mismatches are the
long-declared `gen-001` defects. Dialogue passes 5/5 through both the model and mechanical binders,
the source census passes 10/10, and 104 deterministic tests pass. Corpus compilation produces
1,088 parse rows and five clarification rows. This is a candidate development wall, not a freeze:
the H23/H24 pressure contacts below were deliberately run before certifying it.

## Pressure-bank admission

Two external generators produced 80 candidates each against the retired epoch-016 boundary: H23
used Cursor Agent with Grok 4.5 High, and H24 used Cursor Agent with Claude Opus 4.8 high-fast
thinking. Independent read-only review selected 40 cross-family rows from each bank. Before qwen
contact, selected gold trees were schema-validated and directly executed to the declared outcome
class. Unsupported data requests, ambiguous wording, transient source failures, and half-answer
questions were repaired or excluded at this precontact boundary. The deterministic preparation is
recorded in `harness/prepare_epoch017_pressure.py`.

Because their authoring boundary is older than the current compiler, these banks are explicitly
labelled `pressure`, not `holdout`. They may discover repair work but can never increment the
three-bank untouched counter.

## First contact

H23 scores 0.823 under the ordinary diagnostic and only 8/40 under strict canonical audit. H24
scores 0.919 ordinarily and 25/40 strictly. The pressure set therefore exposes 47 exact compiler
divergences before adjudication. The immutable contact traces and audits are preserved before any
repair.

Judge decision: do not freeze epoch 017, do not count either bank toward saturation, and do not
average the failures into the wall. Adjudicate every divergence, absorb only generalized repairs,
rerun the complete wall, and freeze only after all eligible disclosed evidence is exact. Entirely
new post-freeze banks will be needed for the eventual saturation claim.
