# H29 parser-blind author report

## Boundary and result

H29 contains 100 unique, post-epoch-021 livelihoods questions (`h29-001` through `h29-100`) under bank
`holdout-h29-generated`, schema `round2-holdout-v1`, and `generated_after: e4cfca9`. All rows have a complete
metadata header and a frozen IR v2.1 expression tree. JSON parsing, ID continuity, unique IDs, unique question
surfaces, recursive hole flags, recursive ESTIMATE flags, required row keys, RANK cardinality/order, COMPARE
arity, and RELATE enums were checked locally without parser contact.

The bank has 77 adversarial rows and 23 non-adversarial rows. It is intended as one 100-row practical-
saturation exam, not as evidence for the hard three-holdout protocol before it is evaluated.

## Counts

Question family (`type`):

| Family | Count |
|---|---:|
| STATE | 21 |
| RELATION | 9 |
| CHANGE | 14 |
| TREND | 3 |
| VALUE | 2 |
| TRANSFER | 9 |
| RANKING | 12 |
| AMBIGUOUS | 10 |
| BEHAVIOUR | 5 |
| COMPOSITE | 15 |

Expected outcome:

| Outcome | Count |
|---|---:|
| `answer` | 36 |
| `answer_or_data_request` | 49 |
| `data_request` | 15 |

Top-level gold shape:

| Root op | Count |
|---|---:|
| SELECT | 17 |
| RELATE | 16 |
| AGGREGATE | 21 |
| COMPARE | 20 |
| RANK | 13 |
| ESTIMATE | 11 |
| ANNOTATE | 2 |

Nested operator occurrences are SELECT 206, REGION 220, RELATE 54, AGGREGATE 53, COMPARE 26, ESTIMATE 14,
RANK 13, and ANNOTATE 5. This includes unary trend trees; time- and place-oriented differences and ratios;
positive, negative, distance, and co-occurrence relations; nested two- and three-anchor relations; complete
three- and four-candidate rankings; and ESTIMATE sources built from SELECT, RELATE, and ANNOTATE.

There are 15 rows with recursively detectable typed holes and 13 rows requiring ESTIMATE (14 ESTIMATE nodes,
because one comparison has two modelled branches). Expected `data_request` is used for all hole rows. Transfer
rows use `answer_or_data_request` because gate failure or source emptiness is an admissible result.

Output forms are deliberately varied: records 13, clarification 15, modelled fields 9, full rankings 6,
counts/count-only 6, values 5, booleans 5, ratios 5, means 4, density maps 4, directions 3, series 3, winners 3,
top-k lists 3, annotated records 2, and one each of records-with-distance, distance matrix, difference field,
modelled difference field, difference-and-direction, and difference-with-evidence-labels. Ordinary scalar
differences account for another 8 rows.

Capability-family frequency is intentionally long-tailed. The repeated families are: `spatial_composition` 4;
`ambiguity` and `endpoint_change` 3 each; and 2 each for `anaphoric_relation_anchor`, `annotate`,
`beyond_relation`, `bounded_trend`, `cooccur_beyond_composition`, `distance_relation`, `endpoint_ratio`,
`estimate_annotated_source`, `estimate_feature`, `estimate_interpolate`, `estimate_related_source`,
`eurostat_level`, `gini_level`, `ilostat_level`, `independent_relation_operands`, `point_count`, `point_density`,
`point_presence`, `rank_level_full`, `rank_level_intermediate_k`, `related_density`, `two_anchor_conjunction`,
`window_select`, and `within_relation`. The remaining 40 named capability families occur once each, preventing
one paraphrase family from dominating the exam.

## Coverage choices

Rows 1-10 establish basic region/time/SELECT behavior; 11-30 apply spatial pressure; 31-43 exercise count,
density, presence, mean, annotation, and aggregate output heads; 44-60 cover temporal and cross-entity
difference, ratio, trend direction, and operand orientation; 61-72 cover RANK with complete candidates,
ascending/descending order, full/winner/intermediate-k outputs, and composite candidates; 73-82 cover explicit
interpolate/feature/envelope transfer from arbitrary Records-producing sources; 83-92 cover entity, place,
nested-value, source-role, and anaphoric holes; 93-100 cover unsupported causal/universal claims, evidence
boundaries, output-head honesty, mixed-polarity composition, and observed-versus-modelled labeling.

Source-census-warranted exact-answer rows use only documented combinations such as Bengaluru metro stations;
France informal employment rate; Germany female average weekly hours; Spain labour underutilization; Kenya
average weekly hours; the enumerated Eurostat regions and measures; and Brazil/India/Kenya gini. Other OSM-like
entities and transfer gates are labeled `answer_or_data_request`. Unsupported causal, preference, universal,
error-free-measurement, and equality-of-opportunity claims are not weakened into available proxy series.

## Independence

The authoring pass used only `ROUND2.md`, `algebra/README.md`, `algebra/ir-spec.md`, aggregate metadata from
`coverage/matrix.json`, source facts from `coverage/source-census.json`, and boundary metadata from
`freezes/epoch-021.json`. No parser/compiler/repair implementation, question bank, run, trace, corpus, prior
H27/H28 artifact, failure map, chronology, report, network/model call, or git history/diff was consulted.
Questions were written fresh from the frozen algebra and the source census, so neither surfaces nor gold trees
were adapted to observed parser behavior.

## Schema uncertainty

The allowed IR spec defines the expression-tree schema but does not define enums for benchmark metadata fields
such as `output_form`, `gold_shape`, `capability_family`, `generator`, `register`, or `policy`. This bank follows
the supplied row/header contract and uses descriptive strings for those fields. The spec describes
`ESTIMATE.target` as a place while its typed design uses Region values; the bank consistently encodes targets
as REGION nodes. No multi-output tuple op exists in v2.1, so the bank avoids pretending that RANK is a tuple:
multi-clause rows use a single executable head, while unsupported compound claims become typed-hole
DataRequests.
