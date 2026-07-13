# Round 2 epoch 012 — H18 first contact

## Immutable result

H18 ran only after the admitted bank and checksum were committed at `3156e7a`. The qwen 2B
ordinary harness scored 0.900 overall on 40 rows: parse valid 0.975, schema valid 0.975, shape
0.825, holes 0.875, execution class 0.850, and grounded execution 0.950.

Strict canonical audit matched 24/40. The 16 mismatches are `h18-002`, `h18-003`, `h18-004`,
`h18-008`, `h18-011`, `h18-014`, `h18-016`, `h18-020`, `h18-021`, `h18-022`, `h18-023`,
`h18-039`, `h18-044`, `h18-045`, `h18-048`, and `h18-050`.

The frozen evidence is under `runs/epoch012-holdout-018/`. H18 is not a saturation pass. No
parser repair is permitted until this result is checkpointed and the mismatches are independently
adjudicated. If any valid compiler discovery is absorbed, epoch 012 is invalidated, the counter
remains zero, and a new full-wall certification and freeze are required.

## Independent adjudication

A second read-only judge classified 14 valid compiler discoveries and two bad golds. The valid
discoveries are `h18-002`, `003`, `008`, `011`, `014`, `016`, `020`, `021`, `022`, `023`, `039`,
`045`, `048`, and `050`. They cover annulus composition, final-clause output precedence,
year-to-year differences, ranked-region cleanup, affirmative polarity, attribute annotation,
prefixed places, nearest-distance output, malformed-tree recovery, deictic transfer targets,
explicit source gaps, and unresolved year holes.

The declared bad golds are:

- `h18-004`: the question asks for both per-city counts and their gap, but the single-root gold
  returns only the gap. Tuning to it would preserve a half-answer.
- `h18-044`: “informal employment” does not determine rate versus headcount, yet the gold silently
  chooses the ILO rate. The adjacent headcount question makes the ambiguity explicit.

Neither bad row is eligible for strict scoring or development promotion. H18 still fails as an
untouched bank because the other 14 rows are genuine discoveries.

## Disclosed absorption

Repairs were split into general deterministic rules with negative controls. Fix 1 reached 35/40
strict. Remaining eligible issues were the accented NUTS-2 alias, post-repair annotation
idempotence, and canonical omission of Slovenia as a country suffix. Fix 2 reached strict 38/38
over eligible rows; only the two declared bad golds remain mismatched. The ordinary coarse score
is 0.990 because it intentionally still sees the immutable bad rows.

Thirty-three deterministic parser/canonicalizer regressions pass. Only the 38 eligible H18 rows
may join disclosed development. Epoch 012 is retired and the saturation counter remains zero.
