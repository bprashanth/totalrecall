# H29 pre-contact independent audit

## Blindness statement

I audited all 100 rows of `questions/round2-h29-raw.json` before any parser contact. I read only that raw bank, `algebra/README.md`, `algebra/ir-spec.md`, `ROUND2.md`, `coverage/source-census.json`, and the boundary metadata (`schema_version`, `epoch`, `created_at`, `holdout_policy`, and `note`) from `freezes/epoch-021.json`. I did not read or execute any parser, compiler, repair, scorer, executor, connector, audit, or test implementation; any other question bank; any run, trace, or corpus; an author report; H27/H28 artifacts; failure maps; chronology; `REPORT.md`; proposals; or git history/diffs. I did not call a model or the network, and I did not execute the parser. The string-form `gold_shape` values were treated as the declared known metadata issue and were not grounds for rejection.

The epoch boundary metadata identifies `epoch-021`, created `2026-07-13T15:49:52.483238+00:00`, with the policy that any core/prompt/repair/scorer/connector change invalidates all holdouts in the epoch. Source-outcome review used only the census's four verified families: Eurostat, ILOSTAT, OSM metro, and World Bank Gini. Rows outside those demonstrated source/place/entity combinations were accepted only where `answer_or_data_request` or `data_request` made a source gap permissible.

## Accepted IDs

91 rows are accepted:

- `h29-001`–`h29-020`
- `h29-022`–`h29-029`
- `h29-031`–`h29-032`
- `h29-036`–`h29-039`
- `h29-041`–`h29-059`
- `h29-061`–`h29-088`
- `h29-090`–`h29-099`

For these rows, the gold preserves the question's stated entities, places, time windows, thresholds, methods, targets, output head, operand orientation (subject to the spec's explicit later-minus-earlier/later-over-earlier canonicalization), spatial nesting and polarity, rank candidates/order/k, and warranted holes. Their declared outcome is compatible with the source census: census-demonstrated statistical and Bengaluru-metro rows may require `answer`; unsupported spatial/layer/transfer rows permit a `DataRequest`; unsupported or unresolved claims are explicitly unbound.

## Rejected IDs and precise reasons

- `h29-021`: “at least 2.5 km” is inclusive (`>= 2.5`), while the gold uses `relation:"beyond"`. Under the spec, `beyond` is the complement of `within`; with `within 2.5 km` including its threshold, that denotes `> 2.5`, losing the equality boundary. The IR has no inclusivity qualifier, so the literal threshold semantics are not representable by this gold.
- `h29-030`: the bank itself treats unqualified “workshops” as requiring a workshop-subtype hole in `h29-085`, and the algebra's clarification rule requires a hole for an unspecified subtype. This row instead binds `entity:"workshop"` and declares no hole. The three spatial clauses, their order, thresholds, polarity, and presence head are otherwise complete.
- `h29-033`: the question asks for one mean over the 2019–2023 values. `AGGREGATE(by:"time", metric:"mean")` produces a time Series and is explicitly described by the spec as an identity over a series-producing `SELECT`; it does not reduce the window to a scalar temporal mean. The gold therefore has the wrong output head.
- `h29-034`: same defect as `h29-033`; the requested single 2022–2024 temporal mean is represented as a time Series, not a scalar mean.
- `h29-035`: same defect as `h29-033`; the requested single 2018–2022 temporal mean is represented as a time Series, not a scalar mean.
- `h29-040`: the question asks for one mean elevation across the related markets. After annotation, `AGGREGATE(by:"space", metric:"mean")` is a spatial Field under the declared type rules, not a global scalar mean. The gold changes the requested output head from one mean to a spatial field.
- `h29-060`: each operand asks for a single temporal mean over 2022–2024, but each `AGGREGATE(by:"time", metric:"mean")` remains a Series. `COMPARE` consequently denotes a series difference rather than the difference between the two requested scalar temporal means.
- `h29-089`: the question names all three candidates and the ranking measure is correctly holed, but it gives no ascending/descending direction. The gold invents `order:"desc"`. Rank order is a required, semantically observable qualifier and must be bound or clarified, not assumed.
- `h29-100`: “Bengaluru's observed coverage” does not specify count, density, presence, or another spatial coverage representation. The gold silently chooses `AGGREGATE(... metric:"density")`. That invented metric determines the observed comparison operand and result; the question only warrants the observed/modelled side labels and the named source/target/method.

## Safe pre-contact repairs

- `h29-030`: preserve the entire current tree but replace the base workshop entity with `"?workshop_subtype"`; set `expect:"data_request"`, `must_hole:true`, and `output_form:"clarification"`. This repairs the under-hole without inventing or discarding any spatial clause.
- `h29-089`: retain the shared `"?livelihood_opportunity_measure"` holes and add an order hole such as `order:"?rank_order"`; the row remains `data_request`. If the validation vocabulary cannot carry a hole in `order`, exclude the row rather than choosing a direction.
- `h29-100`: replace the invented observed `metric:"density"` with a typed hole such as `"?observed_coverage_metric"`, and set `expect:"data_request"`, `must_hole:true`, and `output_form:"clarification"`; retain `must_estimate:true`, the complete interpolated branch, both places, and the evidence-label request. If metric holes are not schema-valid, exclude the row rather than guessing a coverage metric.

The mechanical replacement of every string-form `gold_shape` with its preorder array remains safe and does not alter these admission decisions.

## Irreparable exclusions under algebra v2.1

- `h29-021` requires an inclusive/exclusive distance-boundary distinction not present in the relation IR. Changing “at least” to “more than” would create a different question, not repair this gold.
- `h29-033`, `h29-034`, `h29-035`, and `h29-060` require a global temporal reduction from a Series to one scalar mean. The documented algebra has no such reduction.
- `h29-040` requires a global reduction of annotated related records to one scalar mean rather than the documented spatial Field. The documented algebra has no explicit global scalar reduction.

These six rows should be excluded from first-contact eligibility unless the questions are replaced with newly authored, algebra-expressible questions before contact. The two conditional hole repairs (`h29-089`, `h29-100`) should also be excluded if their required typed enum/metric holes are not valid under the frozen schema.

## Aggregate counts

- Raw rows audited: **100**
- Accepted as written (apart from the declared mechanical `gold_shape` conversion): **91**
- Rejected as written: **9**
- Safely repairable before contact: **3** (`h29-030`, `h29-089`, `h29-100`)
- Irreparable under the documented algebra: **6** (`h29-021`, `h29-033`, `h29-034`, `h29-035`, `h29-040`, `h29-060`)
- Eligible after all three safe repairs, if the two conditional holes validate: **94**
- Mandatory exclusions after those repairs: **6**
