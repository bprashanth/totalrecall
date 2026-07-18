# Codex review — typed data composition contracts

- Reviewer: Codex, 2026-07-16
- Packet: `governance/review-packet-algebra-contracts.md`
- Baseline inspected: released IR v2.2.1 schema and executor
- Scope: contract review only; this document does not authorize implementation or release

## Executive disposition

| Proposal | Disposition | Release track |
|---|---|---|
| ALG-002 typed FILTER | accept-partial | Parser-visible release after field-schema contracts and corpus coverage |
| ALG-003 partitioned GROUP | accept-partial on the need; defer the proposed representation | Keyed-result RFC first |
| ALG-005 unit-tagged arithmetic | accept-partial | Executor/result-metadata hardening first |
| ALG-007 temporal alignment and vintage | accept-partial | Executor/result-metadata hardening first |
| ALG-008 CORROBORATE / VERIFY | defer | Claim/evidence layer after lineage declarations |

The safest first release is the shared metadata substrate needed by ALG-005 and ALG-007. It adds
no parser surface and closes existing fail-open arithmetic behavior. ALG-002 is a coherent small
operation, but it should not ship before connectors declare filterable fields and their types.
ALG-003 identifies a real expressiveness gap, but its result representation is not yet settled.

## ALG-002 — typed FILTER

**Disposition: accept-partial.**

Accept a unary Records-to-Records operation with an AND-only list of predicates. Initial
comparators should be `eq`, `ne`, `lt`, `le`, `gt`, `ge`, and `contains`; operands are a declared
field and a JSON literal or typed hole. Cross-field expressions, regular expressions, nesting,
disjunction, and aggregate predicates are deferred.

FILTER is best treated as a logical operation with an executor contract. Connectors may push it
down only when pushdown is observationally equivalent. The field must resolve against the source's
declared schema. An unknown field or incompatible predicate type returns a typed DataRequest;
missing values are excluded and counted rather than treated as predicate-true.

Required conformance:

1. Empty output over a non-empty input is a legitimate negative answer.
2. Unknown fields and predicate type mismatches fail closed with the declared alternatives.
3. Provenance records `rows_in`, `rows_out`, and `null_excluded`.
4. FILTER over non-Records values is rejected during validation.
5. Nested FILTERs canonicalize to a sorted conjunction for equality and caching.
6. Evidence labels pass through unchanged.

This is a parser-visible addition and therefore requires a minor IR version, scorer support,
compile examples, and a model bundle pinned to that version.

Strongest counterexample: a predicate comparing two fields in the same row. Expanding `value` into
an expression tree would turn the initial operation into a general expression language. Such a
request must remain unsupported or be handled by a later, separately governed derived-field
contract.

## ALG-003 — partitioned GROUP

**Disposition: accept-partial on the semantic need; defer the representation proposed in the
companion review.**

Partitioned aggregation is independently useful and cannot be recovered from the current
collapse-style AGGREGATE. However, the released executor's `AGGREGATE by:space` returns a scalar
for count, presence, density, and fallback metrics. There is no existing keyed Field contract to
extend. Consequently, the proposed equivalence between `by:space` and
`by:{field:"<place column>"}` is false against v2.2.1 and cannot be a compatibility anchor.

Before promotion, a keyed-result RFC must choose and test one of:

- a distinct keyed value kind;
- Records with mandatory key and value columns; or
- a revised Field type with explicit ordered key/value entries.

The RFC must define downstream support in COMPARE, RANK, synthesis, canonical equality, and cache
keys. It must also state single-key versus multi-key behavior, missing-key representation, declared
domain zero-filling, deterministic ordering, cardinality limits, and whether grouping an already
grouped result is legal. Until then, no `by:{field}` syntax should be added.

Strongest counterexample: a two-dimensional time-by-category result. It exposes that a flat keyed
container does not state whether the result is a table, nested series, or records, and current
downstream operations cannot consume those alternatives interchangeably.

## ALG-005 — unit-tagged derived arithmetic

**Disposition: accept-partial as executor and typed-result hardening.**

Leaves should declare, and derived values should carry, stable `measure`, `unit`, `grain`, and
lineage metadata. Difference requires compatible measure, unit, and grain. Ratio forms an explicit
derived unit and retains numerator and denominator lineage; zero denominators fail closed. Grain
mismatch fails closed unless a connector declares a specific proxy substitution, in which case the
result is proxy-labelled and the substitution is surfaced. RANK must refuse heterogeneous
measures or units.

The contract needs two clarifications before implementation:

1. `unknown` metadata is not a wildcard. Two unknown tags may preserve legacy single-source
   execution, but cross-source arithmetic with unknown compatibility must fail closed.
2. Measure identity must be source- and methodology-specific enough that two unrelated unitless
   indexes do not become subtractable merely because both report unit `1`.

Required tests include compatible difference, each mismatch dimension, valid and zero-denominator
ratios, proxy opt-in, heterogeneous RANK refusal, metadata preservation, and legacy single-source
behavior. No parser change is required; use an executor/result-schema minor release.

Strongest counterexample: two methodology-incompatible unitless indexes. Dimensional equality alone
does not establish semantic comparability, so stable measure identity is load-bearing.

## ALG-007 — temporal alignment and vintage

**Disposition: accept-partial as a mandatory multi-Series executor contract.**

For two period-indexed Series, the safe default is exact-period inner join. No interpolation or
nearest-period substitution is implicit. Dropped periods produce an alignment certificate with
both available windows, the used overlap, and discarded periods. Zero overlap returns a typed
DataRequest. Mixed-frequency coarsening is permitted only when the connector declares frequency
and an aggregation semantic appropriate to the measure; otherwise it fails closed. Connector
vintages pass through and differing vintages are surfaced, but vintage selection remains deferred.

This contract explicitly excludes scalar comparisons of intentionally disjoint windows. Those
operands carry their own windows in metadata but are not period-aligned Series. It also must define
duplicate period keys and calendar identity before implementation: an inner join is not
deterministic if either side contains multiple values for one canonical period.

Required tests include full and partial overlap, zero overlap, duplicate-period refusal, no
synthetic periods, declared flow/stock coarsening, undeclared mixed-frequency refusal, orientation
regression, and metadata preservation. No parser change is required.

Strongest counterexample: pre/post scalar windows that intentionally do not overlap. Applying the
Series rule to them would reject a valid comparison, so result-kind scoping is mandatory.

## ALG-008 — epistemic CORROBORATE / VERIFY

**Disposition: defer.**

The useful object is a typed claim with measure definition, lineage ancestry, methodology, scope,
uncertainty, and evidence role—not a row set. Agreement, conflict, and incomparability should be
typed claim-result statuses. No operation should certify independence until connectors declare
ancestry and the executor can detect shared upstream sources.

Revival requires at least two connectors with lineage declarations, a demonstrated independent
same-measure comparison, a demonstrated conflict or false-consensus failure, and a decision on
whether this layer is compiler-visible or entirely executor/synthesis-side.

Strongest counterexample: two endpoints expose the same upstream estimate through different
brands. Without ancestry metadata, an apparent agreement is not corroboration.

## Recommended sequencing

1. Specify the typed result-metadata schema shared by ALG-005 and ALG-007, including typed failure
   payloads and backward-compatibility rules.
2. Implement and conformance-test those executor-only contracts as one release.
3. Standardize connector field declarations, then add the restricted ALG-002 surface with a
   compiler/scorer/model version bump.
4. Resolve ALG-003 through a keyed-result RFC and downstream-operation matrix before choosing
   syntax.
5. Keep ALG-008 parked until lineage independence is machine-checkable.

