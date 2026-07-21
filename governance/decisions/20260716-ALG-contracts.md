# Decision — typed data composition contracts ALG-002/003/005/007/008

- Date: 2026-07-16
- Supervisor: Fable (reconciled decision; both independent reviews on file)
- Inputs: `reviews/fable/algebra-contracts.md` + `reviews/codex-algebra-contracts.md`
- Human directive: proceed per reconciliation; codex implements accepted contracts in kit/.

## Reconciliation note (the one material discrepancy)

The Fable review anchored ALG-003 on "`AGGREGATE by:space` already returns a keyed Field." Codex
challenged this, and codex is **correct at the implementation level**: the released kit executor
(`kit/harness/executor.py::_aggregate`) returns a **scalar** for all `by:space` metrics; the spec
table's "Field" output type was never realized as a keyed structure, and RANK labels come from
each item's innermost REGION, not from keyed aggregates. This is a documented spec/implementation
discrepancy in v2.2.1 itself. Consequence: ALG-003 cannot be released as a "typed extension of an
existing keyed output" — the keyed-result representation must be chosen first. The Fable review's
canonical identity (`by:{field:<place column>}` ≡ `by:"space"`) is retargeted from "compatibility
fact" to **RFC acceptance criterion**.

## Dispositions

### ALG-005 — unit-tagged derived arithmetic: **ACCEPTED** (both reviews agree)
Executor/result-metadata contract exactly as reconciled: `{measure, unit, grain, lineage}` tags
from connector declarations; `difference` requires identical (measure, unit, grain); `ratio` forms
derived units with lineage but fails closed on grain mismatch unless declared-proxy (taints to
proxy); RANK scalarization requires shared (measure, unit); `unit:"unknown"` compatible only with
itself; enforcement at execution time. No parser surface.

### ALG-007 — temporal alignment and vintage: **ACCEPTED** (both reviews agree)
Mandatory contract on multi-series operations, not an ALIGN op: exact-period inner join; no
interpolation or nearest-period substitution ever; dropped-period certificate in provenance and
answer surface; zero overlap → DataRequest naming both windows; mixed frequency only via
connector-declared flow/stock coarsening, else fail closed; vintage passthrough only.
**Scoping clause (both reviews independently required it): the contract applies to period-indexed
Series operands only; Scalar operands carrying intentionally disjoint windows (pre/post CHANGE
questions) are exempt.**

### ALG-002 — typed FILTER: **ACCEPTED — CONDITIONAL**
Semantic core as in the Fable review (Records→Records; conjunctive `where` list; `cmp ∈ eq|ne|lt|
le|gt|ge|contains`; values are literals or holes, never subtrees; unknown field → DataRequest;
null exclusion counted; FILTER→∅ over non-empty input = true negative; chain-merge canonical
form). **Condition precedent: typed connector field declarations must exist in the connector
contract and be adopted by the reference connectors before FILTER is promoted** — the op is
meaningless without the column schema it types against (matches the proposal's own declared
dependency). Parser-surface release is deferred to the v2.4.0 bundle (see versioning).

### ALG-003 — partitioned GROUP: **NEED ACCEPTED — KEYED-RESULT RFC REQUIRED**
The question class is real and both reviews accept the need. Blocked on an RFC that chooses and
tests ONE keyed-result representation:
1. a distinct keyed value kind;
2. Records with mandatory key columns; or
3. a revised Field type with explicit ordered key/value entries.
The RFC must include the downstream-operation matrix (RANK, COMPARE, renderer, scorer/skeleton,
canonical forms) and must satisfy: (a) `by:{field:<place column>}` ≡ current `by:"space"`
semantics after the representation lands (retargeted Fable identity); (b) `(unknown)` bucket
accounting; (c) zero-fill only with declared key domain; (d) single key only in v1; (e) the
renderer never flattens a keyed result to an unlabeled list or scalar. The RFC should also state
what happens to the v2.2.1 spec-table "Field" wording (fix the table to match whatever is chosen).

### ALG-008 — CORROBORATE/VERIFY: **DEFERRED** (both reviews agree)
No release surface. Revival evidence bar (recorded from the Fable review): lineage-independent
connector pair with genuine disagreement on a shared measure; demonstrated freeform-model
consensus fabrication on that class; a connector lineage/ancestry declaration schema adopted by
≥2 connectors; ALG-005 tags in production. Failing-open risk is the controlling reason.

## Versioning and sequencing

1. **v2.3.0 = ALG-005 + ALG-007** (executor + result schema + connector metadata declarations:
   units, grain, frequency, flow/stock, vintage). No parser surface; existing trees and tuned
   models remain valid. Codex may implement in kit/ now; promotion on green conformance tests;
   manifest bump + proposal states to `accepted-released` at that point.
2. **v2.4.0 = ALG-002 (+ ALG-003 if its RFC resolves in time)**: parser-visible surface. Gate:
   connector field declarations (ALG-002 condition) and the keyed-result RFC (ALG-003). Sectors
   pin v2.4.0 only when a v2.4.0-trained model bundle exists — the model carries the algebra
   version.
3. Connector owners supply: units/measure ids/grain (005), frequency + flow/stock + vintage
   (007), field schemas (002), key domains (003).

## Conformance test obligations (promotion gates)

The union of both reviews' test lists, notably: mismatched-unit difference fails closed;
ratio derived-unit lineage; grain-proxy taint both branches; RANK heterogeneous-measure failure;
overlap certificate presence/absence; zero-overlap DataRequest; no-synthetic-periods property
test; scalar-window exemption regression (pre/post CHANGE class must keep executing);
orientation-rule regression; FILTER unknown-field DataRequest; null-exclusion accounting;
chain-merge canonical equality; type error on FILTER over non-Records.

## Release record — 2026-07-17

ALG-005 and ALG-007 were implemented in `kit/` and promoted after the executor/connector/synthesis
conformance wall passed. The release is algebra **v2.3.0**, framework **2.4.0**. It adds no IR op
and requires no parser/model retraining. World Bank and OSM reference leaves now declare typed
measure/unit/grain/lineage metadata; World Bank also declares annual frequency and source vintage.

The implemented temporal surface is exactly the reconciled one: exact inner period joins,
dropped-period certificates, zero-overlap and duplicate-period DataRequests, flow+sum or
stock+mean/last declared coarsening, vintage passthrough, and the one-value pre/post exemption.
There is no outer join, interpolation, lag, or vintage selection.

ALG-002 remains `accepted-conditional` and unreleased; connector field declarations have begun but
the parser-visible FILTER surface and corpus/model bundle do not exist. ALG-003 remains
`rfc-required`; no keyed-result representation was selected or implemented. ALG-008 remains
deferred.

## Conditional implementation record — 2026-07-21

ALG-002 is now implemented behind the same explicit `v2.4.0-draft` profile as ALG-015 BUFFER.
The OSM and World Bank reference connector leaves publish typed field declarations, and FILTER
enforces conjunctive typed predicates, unknown-field/type-error DataRequests, null-exclusion
accounting, true-negative empty results, evidence-label passthrough, and canonical chain merging.
The released v2.3 profile continues to reject both parser-visible operations.

The coordinated BUFFER/FILTER conformance bank has 20/20 valid, fixture-executing gold cases,
including radius-vs-pairwise-threshold discrimination. Its deliberately untrained qwen2b baseline
matches only 6/15 parser-required cases, which confirms rather than clears the model gate. The
development corpus is in `kit/conformance/v24_parse_v2.4.jsonl`; release still requires a
versioned v2.4-trained model, perfect required-case parser conformance, and the v2.3 regression
wall. This record does not promote ALG-002 or ALG-015 and does not alter ALG-003's RFC blocker.
