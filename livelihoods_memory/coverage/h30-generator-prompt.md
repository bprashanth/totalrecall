# Blind H30 candidate-author task

H30 is the first countable practical-saturation exam after the exact epoch-022 freeze commit
`65924a8`. The author is a fresh context-free subagent used only for question and gold
construction; the root agent retains admission, adjudication, parser contact, and saturation
judgment. Commit `73d4c48` confirms the freeze without changing any of its 62 hashed inputs.

The author may read only:

- `algebra/README.md`
- `algebra/ir-spec.md`
- `ROUND2.md`
- `coverage/source-census.json`
- aggregate metadata in `coverage/matrix.json`
- boundary metadata in `freezes/epoch-022.json`
- this task file

The author must not read parser, compiler, repair, scorer, executor, connector, or audit
implementations; any existing question bank; runs or traces; corpus data; H27/H28/H29 artifacts;
failure maps; chronology; reports; proposals; or git history/diffs. It must not call a model,
network service, or the parser under test.

The output is `questions/round2-h30-raw.json`: exactly 100 unique rows numbered `h30-001` through
`h30-100`, with complete frozen-v2.1 gold trees. Every row contains `id`, `sector`, `type`,
`capability_family`, `adversarial`, `q`, `expect`, `must_hole`, `must_estimate`, `output_form`,
`gold_ir`, `gold_shape`, and `notes`. The header records bank `holdout-h30-generated`, schema
`round2-holdout-v1`, epoch `epoch-022`, and `generated_after: 65924a8`.

The bank must contain at least 60 genuinely adversarial rows and broad pressure across every major
compiler and evidence family: SELECT/REGION/time; nested and conjunctive spatial RELATE; all
supported AGGREGATE heads; temporal, threshold, and cross-entity COMPARE; composite RANK candidates
with varied cardinalities; every ESTIMATE method with arbitrary Records-producing sources; typed
holes and ambiguity; exact unsupported literals; output-head fidelity; evidence honesty; and
multi-clause composition. Fixed answers use only source-census-warranted operands; unavailable
evidence declares an allowed DataRequest outcome. Nothing may appear in gold unless spoken or
uniquely entailed.

H30 must be linguistically and structurally heterogeneous rather than a paraphrase grid. Mix terse
analyst notes, polite requests, fragments, parentheticals, corrections, delayed qualifiers,
anaphora with unambiguous antecedents, negative constraints, contrastive clauses, noncanonical
clause order, and ordinary conversational wording. Include at least 35 rows combining three or
more operations and at least 20 where a modifier or relation is intentionally local to one sibling.
Do not repeat a question skeleton more than four times. Avoid using algebra operation names as the
main wording when natural language is available.

Before handoff the author validates JSON syntax, count and ID sequence, unique questions, required
fields, frozen vocabulary and child types, exact preorder shapes excluding REGION, wording/tree
agreement, literal warrant, outcome class, recursive hole and estimate declarations, family
distribution, adversarial count, composition depth, and sibling-local pressure. It also writes
`coverage/h30-author-report.md` with those counts and a record of its blindness constraints.
Neither artifact is admitted evidence until an independent blind audit and direct gold execution
complete.
