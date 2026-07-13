# Blind H25 candidate-author task

You are the parser-blind question and gold author for a post-freeze livelihoods holdout. Work in
`/home/beeps/src/github.com/bprashanth/totalrecall/livelihoods_memory`.

Read ONLY these repository files:

- `algebra/ir-spec.md`
- `algebra/README.md`
- `ROUND2.md`
- `coverage/source-census.json`
- `coverage/matrix.json`
- `freezes/epoch-017.json`

Do NOT read or search any parser, scorer, semantic-audit, test, question-bank, run, corpus, report,
finding, chronology, proposal, git-history, cache, or connector/executor implementation file. Do
not call qwen or any other model, execute gold trees, access the network, run tests, or inspect
existing question phrasing. You are upstream of first contact. Do not edit any existing file.

Create exactly one file: `questions/holdout-h25-generated.json`. It must contain exactly 96
unique, single-clause candidate questions with complete frozen-v2.1 gold trees. Use IDs `h25-001`
through `h25-096`. This raw pool will be human-audited down to an immutable 40-row holdout.

Use this top-level structure:

```json
{
  "bank": "holdout-h25-generated",
  "schema_version": "round2-holdout-v1",
  "epoch": "epoch-017",
  "generated_after": "dbcce44",
  "generator": "Cursor Agent / GPT-5.6 Sol High",
  "register": "natural decision-support and field-analyst language, varied syntax",
  "policy": "parser-blind post-freeze raw candidates; no qwen contact; frozen IR v2.1",
  "questions": []
}
```

Each row must have:

```json
{
  "id": "h25-NNN",
  "sector": "livelihoods",
  "type": "STATE|RELATION|CHANGE|TREND|TRANSFER|AMBIGUOUS|BEHAVIOUR|COMPOSITE|RANKING",
  "capability_family": "concise_family_name",
  "adversarial": true,
  "q": "one natural-language question",
  "expect": "answer|data_request|answer_or_data_request",
  "must_hole": false,
  "must_estimate": false,
  "output_form": "brief description",
  "gold_ir": {},
  "gold_shape": ["preorder", "ops", "excluding", "REGION"],
  "notes": "why the gold answers the whole clause"
}
```

The test distribution must cross all verified source families and grains in the census and must
meaningfully mix these expressible families:

- point SELECT, count, presence, density, and direct record return;
- World Bank, ILOSTAT, Eurostat, and Gini single-year levels and bounded trends;
- endpoint differences and same-unit ratios with correct temporal orientation;
- within and beyond relations, decimals/metres/worded fractions, nested two-anchor conjunctions,
  related-set counts/presence/density, and nearest-distance annotations only where v2.1 permits;
- n-ary rank with ascending/descending order, exact candidate closure, `k=1`, intermediate k, and
  full rankings; rank scalar levels, endpoint changes, and related counts;
- cross-source same-unit comparisons and arithmetic only when the census makes units compatible;
- explicit ESTIMATE methods with source and target roles, including a few unresolved target/source
  holes that are type-valid;
- isolated anaphora/deictic questions with only the genuinely unresolved role holed;
- human motive/preference/intent questions represented honestly with proxy holes;
- literal, fully bound unsupported entities/measures and non-curated regional statistics as honest
  source-gap DataRequests, never converted to holes;
- phrasing controls that distinguish a level from change, bounded trend from endpoint change,
  count from presence, relation from comparison, full rank from winner/top-k, and source gap from
  ambiguity.

At least 24 rows should be ordinary/non-adversarial controls and at least 40 should be challenging
compositions or naturally elliptical variants. Use named places, countries, NUTS-2 regions,
years, measures, and entity types supported by the census. Include at least 10 truthful source-gap
or ambiguity/behavior rows, but do not overload the pool with refusals.

Hard semantic constraints:

- Preserve the frozen spec exactly: no new ops, fields, vocabularies, annotations, aggregation
  metrics, relation kinds, or estimate methods.
- One tree answers the entire one-clause question. No multi-output asks, AND-joined independent
  questions, record-set UNION/OR, filters/attributes, subgroup dimensions not encoded in the
  exact supported measure, quantiles, arbitrary optimization, all-pairs distance, or unexpressible
  grouping.
- For time change, gold comparison must yield later minus earlier under the v2.1 rule. For explicit
  place subtraction, preserve the requested left/right orientation.
- Every SELECT region must be a REGION node. Every ESTIMATE target must be a REGION node. ESTIMATE
  source must match its method's declared input type. Do not use spatial mean over Series.
- `expect=data_request` from a source gap has `must_hole=false`; genuine unresolved roles have
  `must_hole=true`. TRANSFER has `must_estimate=true`.
- Do not assume a facility proves jobs, income, demand, motives, quality, or economic behavior.
- Avoid obscure place names whose geocoding is likely unstable. Vary continents and do not repeat
  the same place/entity/year combination.
- Gold shapes are exact preorder op traversals with REGION nodes omitted.

Before finishing, check JSON syntax, exact row count and ID sequence, uniqueness of questions,
required fields, frozen-vocabulary compliance by reading the spec, and internal agreement among
question, gold, expected outcome, flags, output form, and gold shape. Do not create any other file
and do not explain the result outside the requested file.
