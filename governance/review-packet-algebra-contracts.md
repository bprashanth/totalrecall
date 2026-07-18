# Fable review packet — typed data composition contracts

## Review boundary

Review only the five registered contracts named below. Evaluate whether each contract is coherent,
implementation-neutral, composable with the released typed IR, and sufficiently testable for
promotion. Do not evaluate discovery history or application-specific examples.

Return one of `accept`, `accept-partial`, `defer`, or `reject` for each proposal. An acceptance may
be conditional on a smaller semantic surface, additional invariants, or conformance tests.

## ALG-002 — typed FILTER

Proposed contract: filter a record-producing expression with typed field/operator/value predicates.
The operation must define unknown-field behavior, null/missing behavior, predicate type errors, and
provenance counts. It must not silently treat an unknown predicate as true or erase rejected-row
accounting where that accounting is required for evidence.

Review questions:

1. Is FILTER a core algebra operation or a connector query-planning capability with an equivalent
   observable contract?
2. Which predicate forms are safe in an initial release?
3. Must filtering occur before aggregation and grouping unless an explicit outer scope is given?

## ALG-003 — partitioned GROUP

Proposed contract: partition an input by one or more typed keys and calculate a declared aggregate
per partition. The result must retain its keys, measure/unit metadata, empty-partition policy, and
ordering contract. A renderer must not flatten a keyed result into an unlabeled list or scalar.

Review questions:

1. Should GROUP return a distinct keyed-result type or Records with mandatory key columns?
2. How should missing keys and empty partitions be represented?
3. Which ordering, cardinality, and nested-group guarantees belong in the core contract?

## ALG-005 — unit-tagged derived arithmetic

Proposed contract: derived arithmetic requires compatible measures, explicit units, co-scoped grain,
and declared denominator behavior. Unit or grain mismatches must fail closed rather than producing a
bare numeric scalar.

Review questions:

1. Which arithmetic forms belong in the first governed surface?
2. Is dimensional analysis mandatory at validation time, execution time, or both?
3. What result metadata is required to preserve numerator, denominator, scale, and lineage?

## ALG-007 — explicit temporal alignment and vintage

Proposed contract: operations over multiple time-indexed values must declare calendar/frequency,
join policy, missingness behavior, lag, resampling policy, and source vintage where relevant. No
implicit interpolation or nearest-period substitution is permitted.

Review questions:

1. Should alignment be an explicit operation or a mandatory contract on multi-input operations?
2. Which defaults, if any, are safe enough to standardize?
3. What certificate must accompany dropped, interpolated, or unmatched periods?

## ALG-008 — epistemic CORROBORATE or VERIFY

Proposed contract: compare independently role-labelled claims without collapsing source lineage into
a row union. The operation must represent agreement, conflict, definition incompatibility,
shared-lineage non-independence, tolerance, and uncertainty provenance.

Review questions:

1. Does this belong in the data algebra or a typed claim/evidence layer?
2. What minimum independence and measure-compatibility checks are required before agreement can be
   reported?
3. Should conflict and incomparability be values, statuses, or typed data requests?

## Cross-proposal questions

1. Are ALG-002 and ALG-003 foundational dependencies for ALG-005, ALG-007, or ALG-008?
2. Which proposal can be released independently without introducing silent coercions?
3. Which invariants belong in schema validation, executor conformance, and answer rendering?
4. What backward-compatibility or IR-version boundary is required?
5. Which proposals need more evidence before implementation even if their contracts are sound?

## Requested review output

For each proposal provide:

- disposition;
- accepted semantic core, if any;
- excluded or deferred surface;
- required invariants and conformance tests;
- dependencies and versioning implications; and
- the strongest counterexample to the proposed contract.

This packet requests review only. It does not authorize implementation or release.
