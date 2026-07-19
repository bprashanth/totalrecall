# Review packet — explicit bounded search support

## Review boundary

Review only the proposed support transformation below. Evaluate whether it is coherent,
implementation-neutral, composable with the released typed IR, and sufficiently testable for
promotion. Do not infer an application domain from the proposal.

Return one of `accept`, `accept-partial`, `defer`, or `reject`. This packet requests review only; it
does not authorize implementation or release.

## ALG-015 — BUFFER over REGION

Proposed contract:

```text
BUFFER(source: REGION, radius_km: positive finite number) -> REGION
```

`BUFFER` constructs an explicit bounded search/analysis support around an already resolved region.
It does not select data, change a measurement, or define the distance predicate of a downstream
relation. In a bbox-only reference executor, the returned support is a latitude-aware bbox
expansion and must be labelled as such; it must not be described as an exact geodesic polygon or a
surveyed administrative/property boundary.

The written tree owns support sharing. If two operands require the same buffered support, each
operand must refer to the same canonical `BUFFER` node (or an equivalent canonical value). A
compiler or connector profile may require aligned support, but execution must not silently copy one
operand's support to another.

## Required invariants

1. `radius_km` is finite and greater than zero; unknown radius remains a typed hole.
2. `source` validates as `REGION`; buffering records or scalar values is a type error.
3. The source region, radius, construction method, and resulting bbox survive in provenance.
4. A downstream spatial predicate keeps its own independent threshold and units.
5. Nested buffers have a declared canonicalization rule; no implicit flattening is assumed.
6. Dateline, pole, and unsupported-coordinate-reference cases fail closed until specified.
7. The result is a search/analysis support, not evidence that the whole support was surveyed.

## Conformance tests

- positive and non-finite radius validation;
- REGION input and non-REGION refusal;
- source/radius/result provenance;
- search radius distinct from pairwise-relation threshold;
- two operands with aligned explicit support;
- two operands with intentionally different explicit support;
- bbox label prevents exact-polygon or surveyed-boundary claims;
- dateline and polar refusal;
- nested-buffer canonicalization behavior;
- backward compatibility for trees containing only `REGION`.

## Review questions

1. Is this a core support transformation, a REGION parameter, or connector query-planning metadata?
2. Should the canonical contract require exact geometry, or may a bbox-only executor expose a
   strictly labelled approximation?
3. Should common-support requirements be schema constraints on downstream operations or remain
   explicit compiler obligations?
4. What canonical identity should nested buffers have?
5. Does parser-visible promotion require a new IR/model version even though existing trees retain
   their denotation?

## Strongest counterexample

A bbox expanded by a nominal radius can substantially over-cover the intended circular support,
especially at high latitudes, and may cross a discontinuity. If downstream users treat it as exact
geometry, the operation introduces false inclusion while appearing more precise than a named
region. Acceptance therefore requires either exact-geometry semantics or an unerasable
approximation label plus fail-closed geographic boundaries.
