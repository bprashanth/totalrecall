# Ecology origin-import corpus handoff

> Codex-internal provenance boundary. Do not give this directory to the generic model-training
> operator. The domain-neutral operator packet is `handoff/v24-model-refresh/`.

Status: ready for Fable's next mixed adapter diet.

This is the file boundary required by the two-agent import → retrain → Hermes A/B protocol. It
does not ask Fable to rediscover which ecology rows are trainable.

## Files

- `parse-v2.3.jsonl`: the ecology sector's execution-verified compiler rows. Admission is inherited
  from `ecology_memory/corpus/verified-runs.json`; only the allowlisted active wall is present.
- `clarify-v2.3.jsonl`: mechanically verified hole → clarification → bound-tree dialogue rows.
- `v24-surface.jsonl`: execution-verified development curriculum for the coordinated ALG-002
  FILTER + ALG-015 BUFFER draft surface. It includes the radius-vs-pairwise-threshold
  discrimination class. This is development/training material, never holdout material.
- `manifest.json`: counts, operation distribution, source/output hashes, algebra profiles and
  admission statements.
- `build.py`: deterministic validator/packager. Run it from this directory or repository root.

## Diet rule

Keep the two profiles distinct while assembling the diet:

1. fold `parse-v2.3.jsonl` into compiler retention/origin-sector coverage;
2. fold `v24-surface.jsonl` into the v2.4 surface stratum and add Fable's separately minted
   BUFFER/FILTER discrimination variants;
3. do not rewrite the v2.3 system prompts to mention new operations;
4. never include ecology holdouts, narrative frontier runs, expressiveness probes, or raw Hermes
   transcripts merely because they exist in the repository.

The trained bundle must carry algebra version `v2.4.0`. Promotion still requires
`run_v24_conformance.py --require-parser-perfect` plus the released-v2.3 regression wall. GROUP is
not in this corpus and remains blocked on its keyed-result RFC.

## Hermes A/B sequencing

This handoff satisfies the origin-corpus prerequisite. It does not authorize an A/B against an old
adapter. Fable first folds these rows into the next diet, trains the versioned bundle, and checks
compiler retention and v2.4 conformance. Only then should the pre-registered ecology Hermes A/B run.
