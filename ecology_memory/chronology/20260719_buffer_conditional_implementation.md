# 2026-07-19 — ALG-015 conditional BUFFER implementation

## Authorization and boundary

Fable reviewed ALG-015 and the reconciled decision accepted a support-only
`BUFFER(REGION, radius_km) -> REGION` contract conditionally. This run implemented that contract
without promoting it into the released framework manifest. The origin repository remained
read-only and no model/container service was changed.

## Local incompatibilities found and fixed

The sector pilot already had a useful BUFFER experiment, but it did not conform completely:

- the capability binder silently copied one operand's buffer onto the other;
- identical supports had no canonical identity and nested radii did not normalize;
- bbox approximation was a descriptive source string rather than an unerasable typed method; and
- answer audits did not require the approximation to remain visible.

The binder copy was removed. A compiler must now write support under every operand. Canonicalization
interns identical written REGION/BUFFER values and applies
`BUFFER(BUFFER(R,a),b) = BUFFER(R,a+b)` for finite concrete radii. Hole radii remain unbound.
Execution carries `method:bbox-approx`, `approximate:true`, source support, radius, and result bbox;
dateline/pole cases return a typed data request. The response audit requires “approximate bbox” or
equivalent wording.

Live typed trace: a 100 km approximate search bbox around the target with an independent 10 km
pairwise relation threshold compiled both explicit BUFFER operands, queried 253 cobra and 162
elephant occurrence records, returned 200 and 87 bidirectional matches, and passed every answer
audit in 9.186 seconds. No support was injected by execution.

## Kit implementation candidate

The released `kit/algebra/ir-spec.md` and default APIs remain v2.3.0. The new
`kit/algebra/ir-spec-v2.4.0-draft.md` is available only through explicit profile
`v2.4.0-draft`. It adds:

- version-gated schema validation and parser curriculum;
- BUFFER execution and provenance;
- nested canonicalization and support interning;
- REGION-only input typing and finite-radius validation;
- BUFFER support for SELECT.region and ESTIMATE.target;
- approximation-aware response context and scoring; and
- a neutral ten-question conformance/development corpus.

All ten golds validate and fixture-execute to their declared answer/DataRequest class. The generated
training corpus contains ten execution-verified question/tree pairs.

## Model condition remains open

The shared base Qwen 2B compiled 5/8 required canonical examples. It handled simple selection,
search-radius versus relation-threshold discrimination, a radius hole, and a buffered ESTIMATE
target, but it still dropped shared/differing support in three relation variants. The existing
merged 9B adapter scored 4/8 and made different errors, including relation/method substitutions.

These results confirm Fable's versioned-model condition rather than justify more phrase-specific
routing. The code-owned semantic audit detects the omissions and requests one model recompile but
does not construct the missing BUFFER tree. The verified gold corpus is ready for a future v2.4
training bundle; neither current model is labelled v2.4-compatible.

## Status

ALG-015 is `implemented`, not `validated` or released. Promotion remains blocked on a trained
v2.4 parser/model bundle passing the conformance wall and coordination with the ALG-002 v2.4
parser-surface bundle. This work is regression closure for the executor contract, not saturation.

The final conditional-implementation wall passed 193 sector tests, 29 canonical framework tests,
the Hermes CLI contract, governance validation, Python/JSON validation, diff integrity, and the
origin read-only check. The separate `--require-parser-perfect` promotion probe exits non-zero as
designed and names the three required base-2B rows that still differ from canonical gold.
