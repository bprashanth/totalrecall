# 2026-07-21 — v2.4 FILTER completion and origin-corpus handoff

## Why this run happened

Fable reported two training blockers: the coordinated BUFFER/FILTER parser surface was not frozen,
and the execution-verified origin-sector corpus had not been handed off. Inspection showed that
BUFFER was already conditionally implemented; FILTER and the explicit corpus boundary were the
remaining Codex-owned gaps. GROUP was deliberately out of scope because its keyed-result RFC is
still unresolved.

## Changes

- implemented typed Records→Records FILTER behind `v2.4.0-draft` only;
- declared typed fields on the OSM and World Bank reference connector results;
- added fail-closed unknown-field, source-schema, source-value, and literal-type behavior;
- preserved null-exclusion counts, source evidence labels, and empty true-negative semantics;
- made nested conjunctive filters canonical and profile-aware in validation, execution, parsing,
  benchmarking, and scoring;
- coordinated FILTER with BUFFER in one parser prompt, one 20-case conformance wall, and one
  development corpus containing the radius-vs-threshold discrimination class;
- packaged the existing allowlisted ecology corpus as an explicit Fable handoff without importing
  holdouts, narrative frontier traces, expressiveness probes, or raw Hermes transcripts.

## Evidence

- framework regression: 39/39 unit tests pass;
- governance validator: 47 proposals valid, 7 released (no release count change);
- gold conformance: 20/20 BUFFER/FILTER cases schema-valid and fixture-executing;
- untrained qwen2b parser baseline: 6/15 exact required cases (40%), therefore **not promotable**;
- handoff: 270 v2.3 parse rows, 5 v2.3 clarify rows, 20 v2.4 surface rows, all hashed in the
  handoff manifest.

## Ownership after this run

Codex's two named blockers are complete. Fable now owns corpus mixing and variant minting, training
the versioned v2.4 bundle, then running perfect required-case v2.4 parser conformance and the v2.3
regression wall before Hermes A/B. ALG-002 and ALG-015 remain conditional; the released manifest
is unchanged. GROUP remains with the RFC owner and must not enter this training diet yet.

## Neutral operator boundary and deferred retraining plan

The provenance-bearing corpus directory is now explicitly Codex-internal. A separate generic
operator packet was added at `handoff/v24-model-refresh/`; a lexical audit confirms that packet has
no ecology/site/taxon terminology. It exposes content hashes and the BUFFER/FILTER contract without
asking the operator to review the origin sector.

Retraining was documented but not executed. The infrastructure audit found an abandoned Heartwood
draft diet of 4,335 rows containing 18 invalid `FILTER ... ne null` targets; null predicates are
outside the frozen ALG-002 contract. Its training log ends during base-weight loading and no
adapter-9b-004 artifact or completion sentinel exists. The Codex fallback plan therefore requires
a clean rebuild, schema validation of every target, an unseen wall frozen before model contact,
and fresh candidate names. It is recorded in
`handoff/ecology-origin-corpus/RETRAIN_PLAN.md`.
