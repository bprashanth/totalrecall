# Round 2 epoch 015 — H21 admission boundary

## Independent generation

H21 was authored after the committed epoch-015 freeze by Cursor Agent using GPT-5.6 Sol High, an
OpenAI-family generator distinct from H19's Google and H20's xAI authors. The author could read only
the frozen v2.1 spec/schema, connector vocabulary, coverage and source census, Round 2 protocol, and
epoch-015 manifest. It was forbidden from parser, scorer, audit, repair and test code; all prior
question content, runs, corpus, reports, chronology, proposals, and git history; qwen; and network
execution. It wrote exactly 80 unique, schema-valid candidates to
`questions/holdout-h21-generated.json` and touched no other file.

The main judge audited rows 1–40. An independent blind judge audited rows 41–80 under the same
parser-blind boundary. A low-effort Cursor subprocess then performed only the main judge's explicit
selection and mechanical pre-contact repairs; it had no parser or execution access.

## Pre-contact repairs and exclusions

The generator systematically wrapped point statistical Series in
`AGGREGATE(by:space, metric:mean)`, which is type-invalid. Selected statistical golds were repaired
to use point SELECT operands directly; time-series trend identities were left intact. Two uncertain
ILOSTAT expectations plus one mixed-source row were changed to `answer_or_data_request`. The
two-city `h21-050` rank was repaired to binary COMPARE under the frozen two-things rule. Every
`gold_shape` was recomputed. No user semantics were reduced.

External Overpass became unreachable for uncached spatial combinations during gold-only execution
admission. Those candidates were excluded, not relabeled as DataRequests. Two explicit unsupported
annotation-layer rows (`h21-034`, `h21-064`) were excluded because the executor currently returned
an Answer instead of a source gap, producing proposal SRC-002. `h21-035` was excluded after
prefix-tolerant resolver matching routed “gig-work platform” to craft workshops, producing BUG-003.
Ambiguous transfer deixis `h21-055` was also excluded. All forty admitted golds validate, have exact
preorder shapes, and execute to their declared class before parser contact.

## Frozen bank

The admitted `questions/holdout-021.json` contains 40 rows: 20 official-statistic, mixed-source, or
temporal questions; 11 ambiguity or explicit source-gap questions; three cached spatial
record/density controls; two partial-hole ranks/comparisons; one deictic distance; one relational
count ratio; and one transfer. The bank contains both endpoint-change ranks and an explicit bounded
trend negative control. SHA-256:
`770457ea283aab67b68f97d59d902e4f2a124cd53d1ec2ceb6d8734b0ba0b579`.

This commit is the immutable pre-contact boundary. H21 becomes untouched saturation pass 1 only if
ordinary execution, strict canonical audit, manual output/provenance checks, and independent
adjudication find no valid compiler, harness, scorer, connector, or framework repair. Any discovery
retires epoch 015 and keeps the counter at zero.
