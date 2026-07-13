# H30 blind author report

## Artifact

- Bank: `holdout-h30-generated`
- Schema: `round2-holdout-v1`
- Epoch: `epoch-022`
- Generated after: `65924a8`
- Rows: 100, with the exact sequence `h30-001` through `h30-100`
- Unique question strings: 100

## Measured coverage

- Adversarial rows: 93
- Rows containing at least three non-`REGION` operations: 82
- Explicit sibling-local modifier/relation cases: 34
- Recursive-hole rows: 9
- Recursive-`ESTIMATE` rows: 21
- Distinct capability-family labels: 94
- Distinct exact preorder shapes, excluding `REGION`: 36
- Maximum non-`REGION` node count in one tree: 19
- Maximum operation depth, excluding `REGION`: 5

Question types are: `COMPOSITE` 38, `RANKING` 21, `TRANSFER` 12, `AMBIGUOUS` 8,
`RELATION` 6, `STATE` 6, `CHANGE` 3, `TREND` 3, and `VALUE` 3.

Expected outcomes are: `answer` 34, `data_request` 53, and
`answer_or_data_request` 13. Output forms are: records 25, scalar 16, field 20,
series 2, trend 3, ranking 15, winner 5, top-k 5, and data-request 9.

Operation occurrences are: `SELECT` 270, `REGION` 296, `AGGREGATE` 133,
`ANNOTATE` 14, `COMPARE` 43, `RELATE` 78, `RANK` 27, and `ESTIMATE` 26.

Frozen enum pressure includes:

- Relations: `within` 41, `beyond` 24, `distance` 5, `cooccur` 8.
- Aggregate metrics: `count` 23, `density` 11, `mean` 90, `presence` 9.
- Compare modes: `difference` 26, `ratio` 11, `trend_direction` 6.
- Estimate methods: `interpolate` 9, `feature` 11, `envelope` 6.
- Rank order: descending 22 and ascending 5.
- Rank cardinality: 26 three-candidate nodes and one four-candidate node; 17 full
  rankings, five winner-only nodes, and five exact top-two nodes.

## Validation record

I validated the artifact locally without importing or invoking any project harness code.
The checks passed for:

- JSON syntax, header values, row count, ID sequence, unique questions, exact required
  fields, and nonempty metadata;
- the frozen operation, relation, aggregate, comparison, estimate, and rank vocabularies;
- required child fields and recursive input types for every node, including arbitrary
  Records-producing `ESTIMATE` sources (`SELECT`, `ANNOTATE`, `RELATE`, and nested
  `RELATE` compositions);
- exact stored preorder shapes recomputed recursively while excluding `REGION`;
- recursive agreement of `must_hole` and `must_estimate` with each complete gold tree;
- hole rows resolving to `data_request`, gate-dependent estimates using an allowed
  outcome, and source gaps not being mislabeled as fixed observed answers;
- all fixed-answer `SELECT` operands against the exact source-census place/entity/time
  coverage; all other unavailable operands declare `data_request` or a gate-dependent
  allowed outcome;
- wording/tree agreement for polarity, thresholds, time anchoring, operand orientation,
  rank candidates and cardinality, local sibling modifiers, unsupported literals,
  output heads, and evidence boundaries;
- linguistic heterogeneity across terse notes, requests, fragments, corrections,
  parentheticals, delayed qualifiers, anaphora, negative constraints, contrastive clauses,
  noncanonical ordering, and conversational wording. Manual skeleton grouping found no
  repeated question frame above four uses.

The bank includes exact unsupported literals rather than substituting available proxies,
and every modeled or mixed observed/modeled request preserves the `ESTIMATE` evidence
boundary in the tree and expected outcome.

## Blindness record

I read only `coverage/h30-generator-prompt.md`, `algebra/README.md`,
`algebra/ir-spec.md`, `ROUND2.md`, `coverage/source-census.json`, aggregate metadata from
`coverage/matrix.json`, and boundary metadata from `freezes/epoch-022.json`. I did not
inspect parser, compiler, repair, scorer, executor, connector, or audit implementations;
any question bank; runs, traces, or corpus data; prior holdouts; failure maps; chronology;
reports; proposals; or git history/diffs. I did not call the parser, a model, or any network
service. Local Python was used only to validate this authored JSON and did not import or
call harness code.

These artifacts remain candidate material and are not admitted evidence until independent
blind audit and direct gold execution are complete.
