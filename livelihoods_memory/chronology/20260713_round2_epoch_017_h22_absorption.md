# Round 2 epoch 017 — H22 adjudication and absorption

## First-contact result and independent judgment

H22 contacted only the committed epoch-016 boundary. Ordinary scoring was 0.924, but strict
canonical audit matched 17/40. This permanently retires epoch 016 and resets the untouched-pass
counter to zero.

Independent read-only adjudication inspected all 23 mismatches and directly executed every gold.
There were no strict-audit equivalence errors and no connector defects. Every mismatch contained a
real compiler divergence, but four immutable questions were also unsafe tuning targets:

- `h22-010` says “smallest gaps,” which ordinarily means absolute difference; v2.1 has no absolute
  value and the gold silently ranks signed subtraction;
- `h22-023` and `h22-024` use “A less B,” ambiguous between subtraction and a boolean comparison;
- `h22-047` says “source name field,” ambiguous between the source's field named `name` and a
  literal field named `source_name`.

These four are registered against `(questions/holdout-022.json,id)` and remain visible in the
immutable bank. They are excluded from training and strict eligibility; the compiler was not tuned
to their wording.

## Five generalized compiler families

The 23 failing rows reduce to five families. Computed RANK planning now separates candidate
inventory from the quantity subtree, clones one complete ratio/relation/distance quantity per
candidate, and binds exact `k`. Spatial arithmetic compiles each operand locally, preserving
entity, anchor, region, polarity, threshold, density/count head, and written minus/divide order.
Requested density and mean heads no longer degrade to record lists. Unsupported median/rate/average
measures stay complete literal source gaps without invented aggregation, and compact year ranges
retain both endpoints. Transfer keeps explicit donor-set relations inside `ESTIMATE.source`.

Adjacent guards cover full-order ranks without `k`, exact one/two cardinality, ratio item count
versus operand count, mirror subtraction, simple relations without an invented reduction, record
distance versus mean distance, supported statistical SELECTs, and named versus unresolved transfer
roles. The deterministic suite grew from 92 to 104 passing tests.

## Four harness integrity defects

H22 also found failures below the compiler:

1. `AGGREGATE(by=space,metric=mean)` fell through to row count. It now averages only the declared
   `dist_km` output of `RELATE(distance)` and otherwise returns `mean_value_missing`.
2. ANNOTATE with zero non-null requested values returned a grounded-looking Answer. It now returns
   `annotation_unavailable`; the general declared-layer contract remains proposal SRC-002.
3. `ESTIMATE.target=REGION(place="?place")` escaped recursive hole detection and reached geocoding.
   The schema now walks value-or-node targets and execution stops at `unbound_holes` (BUG-004).
4. A one-point trend returned a null scalar Answer and the scorer called it grounded. It now returns
   `insufficient_series`.

The ordinary diagnostic also admitted 13 strict failures at score 1.0. Its existing op multiset
could not see rank cardinality, arithmetic mode, reduction/output head, annotation layer, or a
non-identity mean wrapper. `shape_match` now includes a compact answer contract for those fields;
strict canonical audit remains the release gate.

## Disclosed replay and next boundary

Fix1 reached strict 35/40 and exposed two final harness interactions: scalar and REGION encodings of
an ESTIMATE target hole were scored as different missing roles, and compact `2022–24` was later
erased by literal-time faithfulness. Fix2 corrects both. The final replay is strict 36/36 over
eligible rows; the only four remaining mismatches are exactly the registered defects. Ordinary
scoring is 0.981 over the immutable 40 because defective rows are intentionally not hidden.

H22 is disclosed development closure, not saturation evidence. H23 and H24 were generated
parser-blind after epoch 016 but before these repairs; because epoch 016 is retired, they may be
audited and used only as pre-freeze development pressure. They cannot count toward the next
three-bank sequence. A complete wall must pass before epoch 017 can freeze, after which entirely
new banks are required.
