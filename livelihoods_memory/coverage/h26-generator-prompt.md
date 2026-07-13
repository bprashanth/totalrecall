# Blind H26 candidate-author task

You are the parser-blind question and gold author for the first countable post-epoch-018 livelihoods
holdout. Work in `/home/beeps/src/github.com/bprashanth/totalrecall/livelihoods_memory`.

Read ONLY:

- `algebra/ir-spec.md`
- `algebra/README.md`
- `ROUND2.md`
- `coverage/source-census.json`
- `coverage/matrix.json`
- `freezes/epoch-018.json`

Do NOT read or search parser/scorer/executor/connector/audit/test implementations, any question bank,
run, corpus, report, finding, chronology, proposal, prompt for another holdout, or git history. Do not
call qwen or another model, execute gold trees, access the network, or run tests. Do not edit existing
files.

Create exactly `questions/holdout-h26-generated.json`, containing 96 unique single-clause candidates
with complete frozen-v2.1 gold trees and IDs `h26-001` through `h26-096`. Use this header:

```json
{
  "bank": "holdout-h26-generated",
  "schema_version": "round2-holdout-v1",
  "epoch": "epoch-018",
  "generated_after": "3661348",
  "generator": "Cursor Agent / GPT-5.6 Sol High",
  "register": "operational briefs, dashboard fragments, field notes, and natural analyst questions",
  "policy": "parser-blind post-freeze raw candidates; no qwen contact; frozen IR v2.1",
  "questions": []
}
```

Every row must contain `id`, `sector`, `type`, `capability_family`, `adversarial`, `q`, `expect`,
`must_hole`, `must_estimate`, `output_form`, `gold_ir`, `gold_shape`, and `notes`, following the
semantics in the frozen spec. Gold shapes are exact preorder op traversals excluding REGION.

This bank must be meaningfully cross-family, not paraphrases of one pattern. Cover all four verified
source families and grains, and balance at least these stress groups:

- point records/count/presence/density; within/beyond/distance/cooccur; metres, decimal kilometres,
  written fractions, and nested two-anchor constraints;
- exact levels, bounded trends, endpoint differences, and same-unit ratios across World Bank,
  ILOSTAT, Eurostat, and Gini, with correct later-minus-earlier or explicitly requested orientation;
- complete multi-place RANK plans over levels, endpoint differences/ratios, spatial related counts,
  ascending/descending, winner `k=1`, intermediate k, and full rankings;
- cross-source same-unit comparisons whose operands remain independently scoped;
- explicit envelope/feature/interpolate ESTIMATE source and target roles, including safe source/gate
  DataRequests and a few genuinely unresolved typed roles;
- anaphora/deixis where exactly the unresolved role becomes a hole, behavior/preference motives that
  require honest proxy holes, and literal unsupported entities or non-curated statistical regions
  that remain source gaps without holes;
- answer-head contrasts: records versus count/presence/density, level versus trend/change, yes/no
  versus either/or winner, full list versus examples, and annotation fields supported by frozen
  ANNOTATE semantics;
- evidence-boundary pressure that remains expressible: division by a potentially zero observed
  denominator, partial annotation coverage, long series whose endpoints matter, unnamed spatial
  records, choice comparisons, and subnational indicator scope. Gold stays algebraic; never encode
  prose or trace policy into the IR.

Use at least 28 ordinary controls and at least 40 challenging but natural compositions. Include at
least 10 honest source-gap/ambiguity/behavior rows without letting refusals dominate. Vary geography,
years, syntax, punctuation, and premise order. Prefer stable named places and exact census-backed
measures. Do not repeat the same place/entity/year combination.

Hard exclusions: no new ops/fields/vocabularies; no independent multi-question conjunction; no
UNION/OR, arbitrary filters, unsupported subgroup dimensions, quantiles, optimization, causality,
all-pairs distance, grouping, or multi-output asks. Every SELECT region and ESTIMATE target is a
REGION node. ESTIMATE source type must be legal. `expect=data_request` source gaps have
`must_hole=false`; genuine unresolved semantics have `must_hole=true`; TRANSFER has
`must_estimate=true`. Facilities never prove jobs, income, demand, motives, or quality.

Before finishing, validate JSON syntax, exact count/ID sequence, unique questions, required fields,
frozen vocabulary, exact gold shapes, and agreement among wording, tree, outcome, holes, estimate
flag, and output form. Create no other file and give no explanation outside the requested file.
