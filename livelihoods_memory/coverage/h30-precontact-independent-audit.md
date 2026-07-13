# H30 independent parser-blind pre-contact gold audit

## Scope and method

I audited all 100 rows of `questions/round2-h30-raw.json` without parser or other
harness contact. I read only the files permitted by `coverage/h30-audit-protocol.md`.
I did not inspect prior banks, runs, traces, corpus rows, failure maps, implementation
code, reports outside the permitted author report, git history/diffs, or any network or
model service. The raw bank was not edited.

For every row I checked literal warrant; entity, place, time, subgroup, relation and
modifier locality; polarity and thresholds; relation operand order; binary completeness;
rank candidates, direction, cardinality and output head; estimate source/method/target
typing; holes; declared outcome; preorder shape excluding `REGION`; and recursive hole
and estimate flags.

## Disposition totals

| Disposition | Rows |
|---|---:|
| `accept` | 57 |
| `repairable-precontact` | 28 |
| `exclude` | 13 |
| `duplicate` | 2 |
| **Total** | **100** |

The 57 accepted rows are every ID not listed below. A repairable row is not accepted in
its present form; its proposed repair must be applied before checksum/admission and then
re-audited.

## Repairable before contact

| ID | Exact defect | Safe repair |
|---|---|---|
| h30-015 | `near` does not warrant the inner `0.5 km`; only the `2 km` wholesale-market threshold is spoken. | Remove `threshold_km: 0.5` from the metro `RELATE`. |
| h30-017 | Neither occurrence of `near` warrants the invented `1 km` and `0.4 km` thresholds. | Retain both `within` relations but remove both thresholds. |
| h30-020 | `near` and `away from` warrant `within` and `beyond`, but not the invented `0.7 km` and `1.5 km`. | Remove those two thresholds; keep the final threshold-free `distance` relation. |
| h30-022 | The outer `900 m` is spoken, but `metro stations near colleges` does not warrant the inner `0.2 km`. | Remove only the inner `0.2 km` threshold. |
| h30-024 | Both `near` clauses are threshold-free; `0.5 km` and `2 km` are invented. | Remove both thresholds while preserving the two independent `within` subtrees. |
| h30-025 | Both `near` predicates are threshold-free; `1 km` and `0.3 km` are invented. | Remove both thresholds; retain inner `beyond` and outer `within`. |
| h30-036 | Neither `near` clause warrants `1 km`. | Remove both `1 km` thresholds. |
| h30-041 | `2020 versus 2023` does not uniquely state a signed subtraction even though the gold declares `difference`. | Reword to “France's 2023 informal-employment rate minus its 2020 rate; each date belongs only to that operand.” |
| h30-056 | A full ordering is requested but ascending versus descending is not stated; gold invents `desc`. | Add “largest to smallest” to the question. |
| h30-057 | `near` and `far from` warrant polarity but not the invented `1 km` and `2 km`. | Remove both thresholds; retain the three candidate relations and `k:1`. |
| h30-060 | The rank direction is absent; gold invents `desc`. | Add “from strongest rise to strongest fall” (or another unambiguous descending direction). |
| h30-061 | The rank direction is absent; gold invents `desc`. | Add “largest to smallest.” |
| h30-062 | Bengaluru, rank direction, and all four thresholds are absent from the wording. | Add “In Bengaluru” and “largest first”; remove `0.5`, `1`, `0.7`, and `5 km` while retaining the spoken relation polarities. |
| h30-069 | The source place and metro subtype are unspoken, and `near` does not warrant `0.6 km`; only the airport `2 km` is spoken. | Say “from Bengaluru metro stations near markets but beyond 2 km from airports” and remove the `0.6 km` threshold. |
| h30-070 | Gold invents Bengaluru and the metro subtype for the source `stations`. | Reword the source as “Bengaluru metro stations co-occurring with commercial hubs.” |
| h30-074 | `the same stations` has no in-row antecedent; Bengaluru and metro subtype are invented. | Say “from the same Bengaluru metro stations” for both estimates. |
| h30-075 | The Hyderabad envelope's source is not stated; reusing Bengaluru stations is plausible but not unique. | Say “a Hyderabad envelope estimated from Bengaluru metro stations.” |
| h30-076 | No source is given for any estimate, and no rank direction is given. | Add “all from Bengaluru metro stations, largest first.” |
| h30-077 | Source place and metro subtype are absent, and generic `estimate` does not warrant `feature`. | Say “Annotate Bengaluru metro stations with elevation; use those records, not originals, to feature-estimate Chennai.” |
| h30-078 | Source place and metro subtype are absent. | Say “Use Bengaluru metro stations beyond 3 km from airports …”. |
| h30-081 | Gold invents Bengaluru, metro subtype, and `1 km`; the only intended ambiguity spoken is the business entity. | Say “Which Bengaluru metro stations are near those businesses?” and remove the threshold, preserving `?business_entity`. |
| h30-083 | The unnamed country correctly creates a hole, but rank direction is independently unspecified and gold invents `desc`. | Add “highest to lowest” (or make `order` a second typed hole). |
| h30-086 | The `500 m` relation is spoken, but Bengaluru is not. | Add “in Bengaluru” to the question (or use a shared place hole in both operands). |
| h30-089 | `full order` does not state direction; gold invents `desc`. | Add “highest to lowest.” |
| h30-093 | `tagged` does not identify elevation, and Bengaluru/metro source identity is unspoken. | Say “elevation-tagged Bengaluru metro stations” and “raw records from those same stations.” |
| h30-094 | The observed density's place, both estimate sources, and rank direction are absent. | Specify Bengaluru metro stations as all three sources and add “largest first.” |
| h30-095 | The common place, rank direction, and all six thresholds are absent. | Add “In Bengaluru” and “largest first”; remove all six thresholds while retaining the six spoken relation polarities. |
| h30-097 | The common place, rank direction, and all three thresholds are absent; only the facility entity is intentionally unnamed. | Add “In Bengaluru” and “largest first”; remove all three thresholds and preserve `?facility_anchor`. |

## Exclusions

| ID | Exact reason | Safe repair |
|---|---|---|
| h30-002 | “How many … in Bengaluru” requests one total scalar, but frozen v2.1 defines `AGGREGATE by:space` as a Field and has no global-total aggregate head. The declared scalar outcome is therefore not warranted by the tree. | None without changing the challenge; move to an expressiveness breaker or ask for a spatial count field. |
| h30-034 | The question compares two total set cardinalities as a scalar. Both gold branches are spatial Fields and binary `COMPARE` has no stated scalarization rule (unlike `RANK`). | None without changing the requested scalar comparison; breaker candidate. |
| h30-035 | The wording/output request one density ratio scalar, while both spatial density aggregates and their ratio are Fields. | None without changing the challenge to a mapped ratio Field. |
| h30-037 | “mean over space” requests scalar means, but both `AGGREGATE by:space` branches and their comparison are Fields; the declared scalar output is false. | None within frozen v2.1 without changing the challenge. |
| h30-042 | The requested difference is between two total counts, but the gold supplies spatial Fields and declares a scalar. | None without changing the challenge; breaker candidate. |
| h30-043 | “Do more …” requests a binary comparison of total cardinalities, but the gold compares two spatial Fields and declares a scalar. | None without changing the challenge; breaker candidate. |
| h30-046 | The requested mean-layer comparison is scalar, but the two spatial mean aggregates and their difference are Fields; thresholds are also invented. | None without materially changing the output request; breaker candidate. |
| h30-055 | All rank candidates have the same innermost region and entity, while only metric head distinguishes them. Frozen v2.1 rank labels by innermost region or entity, so it cannot faithfully identify count versus density versus presence in the result. | None without a rank-label extension or a materially different challenge. |
| h30-058 | All candidates have the same vendor entity and Bengaluru region and differ only by relation subtree. Frozen rank labeling cannot identify which predicate produced a ranked value; place and two thresholds are also invented. | None without a rank-label extension or changing candidates. |
| h30-059 | All candidates share the same station entity and Bengaluru region and differ only by annotation layer. Frozen rank labeling cannot identify elevation versus night-light versus noise; direction is also absent. | None without a rank-label extension or changing the challenge. |
| h30-063 | All three candidates share the same France region and entity and differ only by year. Frozen rank labeling cannot identify 2019 versus 2021 versus 2023. | None without a rank-label extension or changing the challenge. |
| h30-092 | All candidates share the same Bengaluru metro entity/region and differ only by metric/composition, so rank labels cannot identify them. Bengaluru is also unspoken. | None without a rank-label extension or materially different candidates. |
| h30-098 | Two candidates share the same Bengaluru metro entity/region but differ only by composition, so the requested ranking cannot be labeled faithfully. The source place, metro subtype, annotation layer, estimate method, threshold and rank direction are also unwarranted. | None narrow enough to preserve this challenge; move to breakers or redesign with frozen-distinguishable candidates. |

## Duplicates

| ID | Exact reason | Safe repair |
|---|---|---|
| h30-052 | Same candidates, year, measure, descending full-order semantics and nearly the same wording pressure as h30-047. | Drop it, or replace it with a genuinely different candidate structure/register. |
| h30-053 | Repeats h30-049's same three candidates, ascending bottom-two head and near-identical frame; changing only 2022 to 2024 does not add distinct pressure. | Drop it, or replace it with a structurally and linguistically distinct top-k challenge. |

## Structural and recursive checks

Across all 100 submitted trees:

- IDs are exactly `h30-001` through `h30-100`; all 100 question strings are unique.
- Every stored preorder shape exactly matches a fresh recursive traversal excluding `REGION`.
- Every `must_hole` flag agrees with recursive string-hole detection.
- Every `must_estimate` flag agrees with recursive `ESTIMATE` detection.
- Required binary operands, rank candidate cardinalities, estimate child types, and declared frozen enum values are structurally complete. The failures above are semantic warrant/output failures, not hidden shape mismatches.

## Bank-level quotas

As submitted, the bank has 93 adversarial rows, 82 rows with at least three non-`REGION`
operations, 34 author-marked local-modifier cases, 94 capability-family labels, 36 exact
preorder shapes, and 100 unique questions. My independent semantic audit does not admit
the author counts blindly; the admission results are:

| Measure | Accepted now | After all 28 safe repairs, excluding 13 + 2 duplicates | Requirement/result |
|---|---:|---:|---|
| Rows | 57 | 85 | At least 80: fail now; pass after repair |
| Adversarial | 51 | 79 (92.9%) | At least half: pass in both views |
| Three-or-more operations | 40 | 68 | At least 35: pass in both views |
| Independently confirmed sibling/candidate-local cases | 11 | 23 | At least 20: fail now; pass after repair |
| Distinct capability-family labels | 56 | 81 | Broad family pressure remains after repair |
| Distinct exact preorder shapes | 17 | 30 | Broad structural diversity remains after repair |

After the stated repairs, manual question-frame grouping has no repeated linguistic
skeleton above four uses. The repaired survivor also retains undisputed accepted exemplars
for every practical-saturation family: spatial (h30-011--014, h30-016), statistical
(h30-005, h30-007--010), ranking (h30-047--051), transfer/evidence boundary
(h30-064--068 and h30-096), ambiguity/hole (h30-079, h30-080, h30-082,
h30-084, h30-085), unsupported source/subgroup (h30-006, h30-087, h30-088,
h30-099, h30-100), and output-form pressure (h30-003--005, h30-048--051,
h30-090, h30-091).

## SAT-004 conclusion

**No, not as submitted.** Only 57 rows are presently undisputed accepts, so the raw bank
cannot supply an 80-row SAT-004 exam without relying on disputed rows; it also has only 11
accepted sibling-local cases.

**Conditionally yes before contact:** if all 28 narrow repairs above are applied and pass a
fresh pre-contact re-audit, the resulting 85-row bank meets the size, adversarial,
three-operation, sibling-local, family-mix and diversity quotas without relying on any of
the 13 excluded or 2 duplicate rows. Admission remains the root judge's decision.
