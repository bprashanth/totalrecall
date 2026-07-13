# Blind H29 candidate-author task

H29 is the first countable practical-saturation exam after the exact epoch-021 freeze commit
`e4cfca9`. The author is a fresh context-free subagent used only for question/gold construction;
the root agent retains admission, adjudication, and saturation judgment.

The author may read only:

- `algebra/README.md`
- `algebra/ir-spec.md`
- `ROUND2.md`
- `coverage/source-census.json`
- aggregate metadata in `coverage/matrix.json`
- boundary metadata in `freezes/epoch-021.json`

The author must not read parser, compiler, repair, scorer, executor, connector, or audit
implementations; any existing question bank; runs or traces; corpus data; H27/H28 artifacts;
failure maps; chronology; reports; proposals; or git history/diffs. It must not call a model,
network service, or the parser under test.

The output is `questions/round2-h29-raw.json`: exactly 100 unique rows numbered `h29-001` through
`h29-100`, with complete frozen-v2.1 gold trees. Every row contains `id`, `sector`, `type`,
`capability_family`, `adversarial`, `q`, `expect`, `must_hole`, `must_estimate`, `output_form`,
`gold_ir`, `gold_shape`, and `notes`. The header records bank `holdout-h29-generated`, schema
`round2-holdout-v1`, epoch `epoch-021`, and `generated_after: e4cfca9`.

The bank must include at least 55 genuinely adversarial rows and broad, reasonably even pressure
across SELECT/REGION/time, nested and conjunctive spatial RELATE, all supported AGGREGATE heads,
temporal and cross-entity COMPARE, complete composite RANK candidates with varied cardinalities,
all ESTIMATE methods with arbitrary Records-producing sources, typed holes and ambiguity, exact
unsupported literals, output-head fidelity, evidence honesty, and multi-clause composition. Fixed
answers should use source-census-warranted operands; unavailable evidence must declare an allowed
DataRequest outcome. No place, entity, qualifier, threshold, direction, candidate, layer, method,
or target may appear in gold without being spoken or uniquely entailed.

Before handoff the author validates JSON syntax, count and ID sequence, unique questions, required
fields, frozen vocabulary and child types, exact preorder shapes excluding REGION, wording/tree
agreement, literal warrant, outcome class, hole and estimate declarations, family distribution,
and adversarial count. It also writes `coverage/h29-author-report.md` with those counts and a record
of its blindness constraints. Neither artifact is admitted evidence until an independent blind
audit and direct gold execution complete.
