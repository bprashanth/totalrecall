# H26 first-contact independent mismatch audit

## Scope and adjudication standard

This audit covers the union of:

- all 28 rows whose ordinary mechanical score was below 1.0; and
- all 33 strict canonical mismatches.

The union contains 33 rows. The five strict-only rows are h26-014, h26-020,
h26-053, h26-054, and h26-070.

Classes below are primary-cause classifications:

1. valid general compiler/binder gap;
2. harmless canonical-equivalence/audit normalization gap;
3. benchmark/gold defect;
4. executor/synthesis/evidence defect;
5. source volatility only.

A permitted `answer_or_data_request` outcome does not make a semantically
wrong plan correct. Conversely, a source truncation or missing observation
does not become the primary cause when the compiled tree already fails to
represent the question.

## Row-by-row audit

| ID | Class | Adjudication and smallest general rule |
|---|---:|---|
| h26-008 | 1 | The distance relation and its metro-station right operand were dropped and replaced by a mean over coworking records. Preserve an explicit binary distance request as `RELATE(distance, left records, right records)`; never infer a distance field from an unannotated record set. The prose is faithful to the resulting typed failure, not to the question. |
| h26-011 | 1 | The spatial relation is correct, but the yes/no answer head was lost: records were returned instead of `AGGREGATE(..., presence)`. Preserve answer-head semantics after constructing the record-set predicate. “Found 27 matching records” is faithful to execution but is not the requested boolean surface. |
| h26-014 | 2 | `Dubai, UAE` and `Dubai, United Arab Emirates` identify the same place, and execution resolved the intended Dubai scope. Canonical comparison should use resolved place identity or a general place-alias normalization, not raw surface strings. |
| h26-020 | 1 | The 2,000-metre threshold became `0.0`. Normalize distance units before binding and preserve every explicit threshold on the relation. The current 46 records happen to have displayed examples above 2 km, but that accidental result agreement does not make the zero-threshold plan equivalent. |
| h26-024 | 1 | The inner market–metro co-occurrence was replaced by an invented facility hole, even though all roles were stated. Preserve nested relation output as the left input of the enclosing relation; do not replace a fully specified composed source with a hole. The clarification prose is faithful to the wrong tree. |
| h26-025 | 1 | Both operands must be complete, independently scoped Rome and Athens related-count plans. The actual plan compares Rome's total metro count with Rome's related count and omits Athens. For cross-place comparisons, clone the complete predicate/aggregation skeleton per named place and bind all leaves in that operand to that place. The prose reports the typed scalar but also omits the operand names required for place comparisons, so it does not expose the scope error. |
| h26-026 | 1 | Only Prague's related density survived; Vienna and the outer comparison were dropped. A two-place comparison must close the full semantic subtree for each place before forming `COMPARE`. Prague's retrieval cap is real execution evidence, but it is secondary and does not excuse the missing Vienna operand. |
| h26-027 | 1 | Both proximity predicates and both count heads were dropped, leaving a ratio of raw metro and market record counts. Build each ratio operand from the full noun phrase, including relation, threshold, answer head, and distinct subject entity. |
| h26-028 | 1 | The compiler produced an ill-typed cross-place relation rather than two related counts under `COMPARE`. “Either A or B: which has more …” requires one complete scalar plan per candidate and a comparison of those scalars. The trace prose correctly calls this a compiler failure; the separate synthesis-audit label `compiler_failure_called_data_gap` is a stale/normalization false positive. |
| h26-031 | 1 | The year was absorbed into the entity, the temporal bound disappeared, and a leading determiner contaminated the place. Bind temporal expressions before entity extraction, and strip discourse determiners from place spans while retaining the named indicator. This is not a source gap: the gold execution established the regional series. |
| h26-044 | 1 | “Weekly hours” failed to bind to the configured average-weekly-hours indicator. Indicator binding needs a general, unambiguous head alias from the elliptical noun phrase to the canonical measure; explicit years remain endpoint anchors. Identity mean-by-time wrappers are harmless, but the unresolved indicator is not. |
| h26-046 | 1 | The unambiguous domain abbreviation “Gini” was left literal and therefore missed the World Bank indicator. Bind standard measure aliases to the same indicator independent of whether “coefficient” is present. The prose is faithful to the misbound tree but incorrectly presents the compiler miss as source coverage. |
| h26-047 | 1 | As in h26-046, “Gini” was not bound to the configured indicator. The trend structure and time range are otherwise present. Apply indicator alias binding recursively inside trend operands before connector routing. |
| h26-048 | 1 | “Madrid region unemployment” was bound to the national World Bank unemployment indicator rather than the regional Eurostat unemployment-rate series. Provider selection must jointly respect indicator meaning and geographic grain; a regional place must not be routed to a country-only provider when a verified regional mapping exists. |
| h26-051 | 1 | The operands are correctly scoped, but the winner question was answered with a ratio rather than a comparison suitable for identifying the larger value. Preserve the answer head “which was larger” and compile it to a signed comparison/winner interpretation, not an arbitrary ratio. The prose states the ratio and therefore fails the requested winner surface while remaining faithful to typed execution. |
| h26-053 | 1 | The discourse label “snapshot” was incorrectly included in the Kenya place span. Temporal/reporting cue words must be excluded from place extraction; each mixed-source operand then retains its own place, indicator, and year. The allowed DataRequest class hides this semantic error in ordinary scoring. |
| h26-054 | 1 | The right operand inherited Brazil and a generic employment-rate binding instead of France's informal-employment rate. In coordinated mixed-source comparisons, bind provider, entity, place, and time independently for every operand; never propagate the first operand's place or provider into the second. |
| h26-056 | 1 | “Gini” again remained literal. The requested country order and ratio structure are present, so the smallest rule is the same general Gini-indicator alias normalization. Mean-by-space over a statistical series is not the specified identity normalization and should not be relied on. |
| h26-058 | 1 | The plan merged Seoul and Busan into one cross-city relation, changed `beyond 3 km` to unthresholded `within`, omitted Busan's complete predicate, and compared the result with Seoul marketplaces. Cross-place closure must duplicate the entire related-count plan per city while preserving polarity and threshold. The `-145` prose is faithful to the wrong execution but does not name the compared operands. |
| h26-066 | 1 | The explicit numerator/denominator ratio became an ill-typed nested aggregate and lost the coworking `beyond 5 km` denominator. Construct both scalar count operands completely before applying `COMPARE(ratio)`. The trace prose correctly identifies compiler failure; the synthesis-audit `compiler_failure_called_data_gap` flag is a false positive. |
| h26-069 | 1 | A three-candidate winner was degraded to a two-item binary difference, dropping Warsaw. Three or more named candidates require `RANK`; preserve every candidate, direction `desc`, and winner cardinality `k=1`. The fail-closed prose correctly refuses to present the scalar as the requested ranking, so it does not contradict typed execution. Its missing-source-label audit flag is inapplicable because no factual result is delivered. |
| h26-070 | 1 | The `RANK` shell and ascending direction are correct, but Andalusia was lost and Madrid was duplicated; execution and prose expose the duplicate. Ranking construction must establish a one-to-one candidate ledger from the question and bind exactly one item per distinct named candidate. |
| h26-071 | 1 | The ranking cardinality and direction are correct, but Gini was misbound to literal income counts. Candidate-wide entity binding must resolve the shared metric once and apply it consistently to every ranking item. |
| h26-074 | 1 | The compiler ranked three-year employment levels instead of 2024-minus-2022 changes and omitted winner cardinality `k=1`. Ranking over change requires each item to be the complete endpoint `COMPARE`, followed by ranking those derived scalars with the requested direction and cardinality. The prose is faithful to level ranking, not the question. |
| h26-075 | 1 | The outer ranking and two candidates were dropped, leaving only Brazil's change. Build a complete per-candidate endpoint-change item, preserve all three candidates, and apply ascending full ranking. The Gini alias miss is an additional binder manifestation of the same general indicator-alias family. |
| h26-076 | 1 | The compiler ranked multi-year weekly-hour levels rather than 2021-to-2019 ratios. Temporal phrases of the form “A-to-B ratios” denote a two-snapshot `COMPARE(ratio)` inside every rank item, not a range-valued SELECT/identity aggregate. Candidate count and descending direction must remain unchanged. |
| h26-077 | 1 | Generation truncated before producing a complete IR. A ranking compiler must emit a syntactically complete item for every candidate within the output budget and fail closed if it cannot; repair must be structural and general, not candidate-specific. The error prose is accurate. |
| h26-078 | 1 | Candidate count, `k=2`, direction, and density heads survive, but every “within 0.8 km of bus stops” relation was dropped. Shared ranking modifiers must be copied into every candidate subtree before scalarization. The returned top two are densities of all metro stations, so the factual prose answers a different question. |
| h26-089 | 1 | The unresolved facility role was concretized as literal `facility`, and the explicit interpolation method became envelope. Unresolved semantic roles must remain typed holes even when a generic noun is present, while explicit transfer methods are copied exactly. The resulting source-gap prose should instead have requested the facility type. |
| h26-091 | 1 | The annotated source composition collapsed into a SELECT for `wheelchair`. Treat attributive phrases such as “wheelchair-annotated metro-station records” as `ANNOTATE(SELECT(records), layer)`, and preserve that records-producing subtree as the ESTIMATE source. |
| h26-092 | 1 | The related Salvador source is correct, but the ESTIMATE wrapper, Recife target, method, and modelled evidence path were all dropped. Transfer language requires `ESTIMATE` around the complete source composition; returning observed source records is not equivalent to estimating the target. The prose is faithful to the observed source execution and therefore visibly answers Salvador rather than Recife. |
| h26-093 | 1 | The unresolved pronoun anchor and relation were dropped, producing a plain station count. A pronoun in a required relation role must create a hole at that exact role while preserving the enclosing relation, threshold, and answer head; it must not be treated as optional. |
| h26-096 | 1 | A causal motive question was converted into a quantitative commuter/metro ratio with no hole. Behavioural “because” questions require an unresolved evidence/proxy role and must not infer motive from facility or population counts. The source-gap prose is faithful to the wrong tree but misses the required clarification. |

## Cross-cutting prose, execution, and evidence findings

- No audited row is primarily an executor, synthesis, or evidence defect. Where
  execution reached an answer, it followed the compiled tree. The substantive
  failures are upstream semantic-plan failures.
- h26-028 and h26-066 are explicitly described in their trace prose as compiler
  failures, contrary to the synthesis-audit labels that say they were called
  data gaps.
- h26-069 deliberately fails closed because the typed scalar is not the
  requested complete ranking. That is safer than verbalizing the scalar. A
  provider label is not required for a non-factual refusal.
- Several factual surfaces are faithful to the wrong typed tree while
  contradicting the question: notably h26-011, h26-025, h26-051, h26-058,
  h26-070, h26-074, h26-076, h26-078, h26-092, and h26-093. This is not a
  synthesis hallucination, but it shows why execution-class success cannot
  substitute for semantic-plan correctness.
- Place-to-place scalar prose such as h26-025 and h26-058 says only
  “left-minus-right.” The v2.1 surface contract says place operands must be
  named. That is a secondary synthesis shortcoming, but correcting it would
  expose rather than repair the wrong compiler scopes.
- The Prague source truncation in h26-026 is genuine execution evidence, but no
  row is class 5: every audited source event either accompanies a prior
  compiler error or is an expected, correctly typed DataRequest.

## Counts by primary class

| Class | Count |
|---|---:|
| 1. Valid general compiler/binder gap | 32 |
| 2. Harmless canonical-equivalence/audit normalization gap | 1 |
| 3. Benchmark/gold defect | 0 |
| 4. Executor/synthesis/evidence defect | 0 |
| 5. Source volatility only | 0 |
| **Total** | **33** |

## Deduplicated discovery families

1. **Answer-head preservation.** Presence, winner, count, density, difference,
   and ratio semantics must survive after the record predicate is built.
2. **Complete relation composition.** Preserve nested relations, polarity,
   explicit thresholds and unit conversion, and the distinct subject/anchor
   roles.
3. **Cross-place operand closure.** Build one complete, independently scoped
   subtree per named place; do not bleed entities, providers, places, or
   relation anchors across operands.
4. **Indicator, temporal, provider, and geographic binding.** Resolve
   unambiguous aliases such as Gini and weekly hours, separate reporting cues
   such as “snapshot” from places, and select providers compatible with the
   requested geographic grain.
5. **Ranking candidate and derived-value closure.** Preserve every distinct
   candidate, direction, `k`, and whether the ranked scalar is a level, count,
   density, endpoint difference, or endpoint ratio.
6. **Typed unresolved roles.** Anaphoric anchors, generic facility roles, and
   behavioural motive/proxy roles remain holes at their semantic position;
   they are not dropped or converted to unsupported literals.
7. **Transfer source composition.** Preserve ESTIMATE, target, explicit method,
   and composed records sources such as RELATE and ANNOTATE.
8. **Canonical place identity.** Compare resolved geography or normalized
   aliases such as UAE/United Arab Emirates rather than literal place strings.
9. **Complete bounded serialization.** Large repeated plans must either produce
   a complete valid tree or fail closed without exposing a truncated IR.

## Saturation eligibility

H26 cannot count toward saturation. Epoch 018 had already been retired before
this first parser contact, so this run is diagnostic evidence only, not an
eligible unseen-bank saturation observation.
