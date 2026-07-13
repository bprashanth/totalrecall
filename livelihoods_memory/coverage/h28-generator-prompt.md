# Blind H28 candidate-author task

You are the parser-blind question and gold author for the first countable post-epoch-020 livelihoods
holdout. Work in `/home/beeps/src/github.com/bprashanth/totalrecall/livelihoods_memory`.

Read ONLY:

- `algebra/ir-spec.md`
- `algebra/README.md`
- `ROUND2.md`
- `coverage/source-census.json`
- `coverage/matrix.json`
- `freezes/epoch-020.json`

Do NOT read or search parser/scorer/executor/connector/audit/test implementations, any question bank,
run, corpus, report, finding, chronology, proposal, prompt for another holdout, or git history. Do not
call qwen or another model, execute gold trees, access the network, or run tests. Do not edit existing
files.

Create exactly `questions/holdout-h28-generated.json`, containing 100 unique, single-output candidates
with complete frozen-v2.1 gold trees and IDs `h28-001` through `h28-100`. Use this header:

```json
{
  "bank": "holdout-h28-generated",
  "schema_version": "round2-holdout-v1",
  "epoch": "epoch-020",
  "generated_after": "1340ddd",
  "generator": "Codex parser-blind sub-agent",
  "register": "contrastive paraphrases, clause-scope stress, terse field notes, voice fragments, and typed evidence asks",
  "policy": "parser-blind post-freeze raw candidates; no qwen contact; frozen IR v2.1",
  "questions": []
}
```

Every row contains `id`, `sector`, `type`, `capability_family`, `adversarial`, `q`, `expect`,
`must_hole`, `must_estimate`, `output_form`, `gold_ir`, `gold_shape`, and `notes`. `gold_shape` is the
exact preorder operation traversal excluding REGION. Use only frozen operations/fields/enums/types.
Every fixed gold place, entity subtype, qualifier, time, threshold, direction, candidate, donor,
target, layer, and method must be literally spoken or uniquely entailed by the frozen source scope.
Never silently turn a generic station into train station, or a bare ambiguous place into one country.

H28's purpose is orthogonal **surface and clause-scope generalization**, not another dashboard bank.
Use at least 55 genuinely adversarial rows and at least 45 ordinary controls. Include at least 20
contrastive pairs whose two surfaces have the same denotation, while varying voice, word order,
punctuation, morphology, or answer-head placement. Give paired rows different places/entities/years
so they are not duplicates. Do not repeat a complete place/entity/year tuple.

Required independent strata (overlap is welcome):

1. At least 22 spatial rows: records/count/presence/density/distance; within and beyond; mixed
   positive/negative conjunctions where each threshold remains clause-local; same-left/two-anchor;
   independent two-quantity arithmetic; and cross-place cloning. Include singular/plural, hyphen,
   possessive, metric-word, decimal, comma-grouped metres, and written-fraction surfaces. Use exact
   unsupported transport subtypes only when the words say them, with `answer_or_data_request`.
2. At least 22 statistical rows: exact level, bounded direction, endpoint difference, same-unit
   temporal ratio, cross-place difference/ratio, and mixed national/NUTS operands. Each operand owns
   its indicator, subgroup qualifier, place, and time. Include negated contrasts such as “direction,
   not endpoint change” and explicit arithmetic orientation. Use only source-warranted measures.
3. At least 18 RANK rows with 3–6 complete scalar items: level, endpoint change, endpoint ratio,
   point count, related count, and related density; asc/desc, k=1, middle k, and full list. Candidate
   prose must not swallow quantity, direction, or cardinality. Every named candidate appears once.
4. At least 14 ESTIMATE rows across all three methods and SELECT/RELATE/ANNOTATE sources. Donor,
   target, method, source entity, spatial relation, layer, and unresolved roles are syntactically
   explicit. ESTIMATE target is REGION. Unsupported evidence should fail closed, not disappear.
5. At least 14 honesty rows: precise deictic holes, unresolved entity/anchor roles, unsupported fixed
   literals without holes, non-curated regions, behaviour/preference/causal asks reduced only to a
   precise `?proxy`, zero-denominator risk, partial annotation, and source gaps. Facilities never
   prove jobs, income, motives, quality, demand, or causality.
6. At least 10 annotation/output-head contrasts: canonical fields versus modifier-bearing unsupported
   layers; records versus examples/count/presence/density; punctuation separators must not change a
   literal's meaning.

Prefer sparse semantic combinations visible in `coverage/matrix.json`. Hard exclusions: no
FILTER/GROUP/SET/UNION, arbitrary predicates, unsupported subgroup dimensions, quantiles,
optimization, causal effects, all-pairs distance, multi-output bundles, provider constraints, or new
ops/fields/vocabularies. Never weaken an inexpressible request—do not author it. Every SELECT region
is REGION. Source gaps have `must_hole=false`; only genuinely missing user roles have holes.

Before finishing, validate JSON syntax, exact count and ID sequence, unique questions, required
fields, frozen vocabulary and child types, exact preorder shapes, wording/tree agreement, literal
warrant, outcome class, hole declaration, estimate declaration, required stratum counts, and pair
coverage. Create no other file and give no explanation outside the requested file.
