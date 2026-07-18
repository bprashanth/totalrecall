# Spec proposals from this sector (append-only; do NOT edit the spec directly)
Each entry: date · the question that forced it · why the current spec cannot express/handle it ·
the proposed change · evidence (trace path). The cross-sector supervisor reconciles these.

## 2026-07-15 · FILTER as a first-class operator (ALG-002)

- Forcing question: `eco-x003`, “Which 2024–2026 Lantana records in Valparai are CC0 only?”
- Incompatibility: v2.2.1 has no row predicate. Encoding the request as `SELECT` silently discarded
  the licence condition and returned CC-BY records as well.
- Proposed change: admit `FILTER(input, predicate)` with typed field/operator/value predicates,
  explicit missing-field behavior, and provenance-preserving output.
- Evidence: `runs/expressiveness-001/traces.jsonl` (`eco-x003`). This is a demonstrated
  silent-wrong case, not merely an ergonomic omission.

## 2026-07-15 · GROUP and temporal grain (ALG-003)

- Forcing questions: `eco-x011`, bird observations by species; `eco-x017`, monthly NDVI by year.
- Incompatibility: `AGGREGATE` can reduce a whole value but cannot retain group keys or declare
  temporal grain. The closest encodings returned one total or an annual series, respectively.
- Proposed change: admit `GROUP(input, keys, aggregate)` and a typed time-grain projection. Require
  group keys and grain in the result metadata so a renderer cannot erase them.
- Evidence: `runs/expressiveness-001/traces.jsonl` (`eco-x011`, `eco-x017`). Both are
  silent-wrong witnesses.

## 2026-07-15 · Alignment and unit contracts (ALG-005, ALG-007)

- Forcing questions: `eco-x021`–`eco-x030`, including aligned bird/NDVI comparisons and area- or
  effort-normalized quantities.
- Incompatibility: v2.2.1 can compare values without specifying join keys, temporal alignment,
  resampling, denominators, or units. A structurally valid tree can therefore compare mismatched
  supports.
- Proposed change: typed `ALIGN` and `NORMALIZE` stages, or equivalent mandatory contracts on
  `COMPARE`/`RELATE`, carrying support, grain, units, missingness, and resampling policy.
- Evidence: `runs/expressiveness-001/traces.jsonl` (`eco-x021`–`eco-x030`).

## 2026-07-15 · Corroboration and uncertainty (ALG-008)

- Forcing questions: `eco-x031`–`eco-x040`, asking whether independent providers agree and what
  uncertainty accompanies a derived result.
- Incompatibility: `UNION` merges rows but cannot preserve independent-source roles, express an
  agreement rule, or carry interval/quality semantics. Two probes also produced invalid/error
  paths rather than an honest request.
- Proposed change: a provenance-aware `CORROBORATE` operator and a standard uncertainty envelope
  on all derived values. Do not equate record union with independent confirmation.
- Evidence: `runs/expressiveness-001/traces.jsonl` (`eco-x031`–`eco-x040`).

## 2026-07-15 · Keep documents, causal claims, and purchased artifacts outside core IR

- Forcing questions: `eco-x041` (literature discovery), `eco-x043` (causal attribution),
  `eco-x045` (exportable artifact), and `eco-x050` (commercial imagery purchase).
- Boundary: these require a document result type, an explicit causal design, an artifact/export
  phase, or external commercial authorization. Adding permissive ecology operators would make
  unsupported claims and side effects look algebraically valid.
- Proposed change: keep the frozen data algebra pure. Add separately governed document discovery,
  causal-estimation, artifact rendering, and authorized acquisition capabilities; bridge them with
  typed inputs/outputs and provenance rather than overloading `SELECT` or `ESTIMATE`.
- Evidence: `runs/expressiveness-001/traces.jsonl` (`eco-x041`, `eco-x043`, `eco-x045`, `eco-x050`).
