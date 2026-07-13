# Blind H27 candidate-author task

You are the parser-blind question and gold author for the first countable post-epoch-019 livelihoods
holdout. Work in `/home/beeps/src/github.com/bprashanth/totalrecall/livelihoods_memory`.

Read ONLY:

- `algebra/ir-spec.md`
- `algebra/README.md`
- `ROUND2.md`
- `coverage/source-census.json`
- `coverage/matrix.json`
- `freezes/epoch-019.json`

Do NOT read or search parser/scorer/executor/connector/audit/test implementations, any question bank,
run, corpus, report, finding, chronology, proposal, prompt for another holdout, or git history. Do not
call qwen or another model, execute gold trees, access the network, or run tests. Do not edit existing
files.

Create exactly `questions/holdout-h27-generated.json`, containing 100 unique, single-output
candidates with complete frozen-v2.1 gold trees and IDs `h27-001` through `h27-100`. Use this header:

```json
{
  "bank": "holdout-h27-generated",
  "schema_version": "round2-holdout-v1",
  "epoch": "epoch-019",
  "generated_after": "064c11a",
  "generator": "Cursor Agent / GPT-5.6 Sol High",
  "register": "mobile voice queries, spreadsheet labels, monitoring notes, procurement asks, and concise research requests",
  "policy": "parser-blind post-freeze raw candidates; no qwen contact; frozen IR v2.1",
  "questions": []
}
```

Every row must contain `id`, `sector`, `type`, `capability_family`, `adversarial`, `q`, `expect`,
`must_hole`, `must_estimate`, `output_form`, `gold_ir`, `gold_shape`, and `notes`. Gold shapes are
exact preorder operation traversals excluding REGION. Use only operations, fields, enums, and input
types in the frozen spec. A one-year statistical level is a SELECT, not a spatial mean.

This bank must test generalization beyond a polished dashboard register. Use natural ellipsis,
premise reordering, possessives, unit conversions, compact punctuation, and answer-form contrasts,
while keeping every question semantically determinate. Do not repeat place/entity/year tuples.

Balance these independent strata (overlap is welcome, template repetition is not):

1. At least 20 point-record tasks spanning raw records, count, presence, density, annotation,
   within/beyond/cooccur/distance, and two nested relation shapes. Mix feet-free metric surfaces:
   metres with comma grouping, decimal km, written halves/quarters, and a shared threshold stated
   once. Spatial source uncertainty should normally use `answer_or_data_request` unless the census
   directly warrants an Answer.
2. At least 24 statistical tasks spanning exact levels, bounded trends, endpoint differences,
   temporal same-unit ratios, and cross-source/cross-place same-unit comparisons. Use all verified
   World Bank, World Bank Gini, ILOSTAT, and Eurostat routes. Each operand owns its place, indicator,
   and time. Preserve later-minus-earlier and numerator/denominator order literally.
3. At least 16 RANK tasks. Include level, endpoint change, endpoint ratio, point count, related count,
   and related density items; asc/desc, winner k=1, middle k, and full lists; 3–6 explicitly named
   candidates. Every item must be present in gold and be a legal scalar-producing plan.
4. At least 12 transfer tasks across envelope, feature, and interpolate. Vary SELECT, RELATE, and
   ANNOTATE sources; keep donor/source, target, method, and unresolved roles exact. ESTIMATE target is
   always REGION and source types are legal. Use `answer_or_data_request` for evidence/gate pressure.
5. At least 12 honesty-boundary tasks: unresolved deictic roles with precise holes, literal unsupported
   entities with no holes, non-curated regions, behaviour/preference/causal-sounding motives reduced
   only to an explicit `?proxy` ask, zero denominators, partial annotation, and source unavailability.
   Facilities never prove jobs, income, demand, motives, quality, or causality.
6. At least 30 ordinary controls and at least 45 challenging natural compositions. Include records vs
   count/presence/density, point vs trend/change, difference vs ratio, list vs examples, yes/no vs
   winner, and same-left versus independently scoped relation operands.

Prefer semantic combinations that are sparse in `coverage/matrix.json`, but do not invent missing
algebra. Hard exclusions: no FILTER/GROUP/SET/UNION, arbitrary attribute predicates, unsupported
subgroup dimensions, quantiles, optimization, causal effects, all-pairs distance, multi-output
bundles, provider constraints, or new ops/fields/vocabularies. Never weaken such a request into a
smaller gold; simply do not author it. Every SELECT region is a REGION node. `expect=data_request`
source gaps have `must_hole=false`; genuinely missing user roles have `must_hole=true`.

Before finishing, validate JSON syntax, exact count and ID sequence, unique questions, required
fields, frozen vocabulary and child types, exact gold shapes, and wording/tree/outcome/hole/estimate
agreement. Create no other file and give no explanation outside the requested file.
