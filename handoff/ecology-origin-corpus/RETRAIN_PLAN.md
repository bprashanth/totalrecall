# Codex fallback plan — v2.4 model refresh

Use this plan if the generic operator cannot complete the model refresh. This file is deliberately
inside the provenance-bearing internal handoff; unlike the operator packet, it names the origin
sector and source paths truthfully.

Status on 2026-07-21: **planned only; do not infer that a valid adapter-004 exists**.

## Known starting state

- Current registry:
  `/home/beeps/src/github.com/bprashanth/heartwood/docs/architecture/memory/benchmarks/lora/MODELS.md`.
  It records `merged-9b-003` as the promoted 9B weights. Verify live state before any future run;
  never trust this dated statement over a current read-only probe.
- Current retention diet:
  `heartwood/docs/architecture/memory/benchmarks/lora/sft-003.jsonl`, 3,895 rows, SHA-256
  `e4b735173847f1307a6a7125423a488bea88f27cc4a499862ae7e4b748880c6d`.
- Existing trainer:
  `heartwood/docs/architecture/memory/benchmarks/harness/train_lora.py`.
- Existing draft diet builder:
  `heartwood/docs/architecture/memory/benchmarks/harness/build_diet_004.py`.
- Internal origin inputs and admission hashes are in `manifest.json` beside this plan.
- Generic contract/evidence inputs are `kit/conformance/v24_parse_v2.4.jsonl` and
  `governance/evidence/v24-qwen2b-pretrain.json`.

## Do not resume the old draft

The existing Heartwood `sft-004.jsonl` has 4,335 rows, but 18 minted FILTER rows use
`{"cmp":"ne","value":null}`. The frozen FILTER contract rejects null predicate literals. The
corresponding `train-004-9b.log` ends while loading base weights, and there is no adapter-9b-004
directory or completion sentinel. Treat both as an abandoned, contaminated attempt—not a
checkpoint.

Before training, replace or parameterize `build_diet_004.py`; do not patch its output by hand.
Questions such as “which records have a name?” must be excluded until an `is_null`/`is_not_null`
contract is separately governed. Never encode them as `ne null`.

## Phase 1 — freeze inputs and evaluation before model contact

1. Re-run `handoff/ecology-origin-corpus/build.py`; verify 270 parse rows, 5 clarification
   dialogues, 20 v2.4 rows, and every recorded digest.
2. Snapshot the current promoted model identity, trainer revision, base-model revision and all diet
   hashes. Record dirty worktrees; do not alter unrelated changes in either repository.
3. Audit the 20 v2.4 rows with the explicit draft validator and fixture executor.
4. Create an unseen 40–60 question wall before generating training variants. Cover:
   - shared and intentionally different BUFFER supports;
   - BUFFER radius versus RELATE threshold, including metres-to-kilometres conversion;
   - unknown radius holes and refusal to invent defaults;
   - FILTER `contains`, ordered numeric predicates, conjunctions and FILTER-over-RELATE;
   - declared field names versus natural-language aliases;
   - literal preservation and unsupported null/field/type cases;
   - v2.3 questions where BUFFER/FILTER must not appear.
5. Mark that wall eval-only and hash it. No agent used for minting may see it afterward.

## Phase 2 — rebuild the diet

Start from all 3,895 `sft-003` rows. Add:

- all 270 verified ecology v2.3 compiler rows once;
- each clarification dialogue as a holed row and a reply-bound row (10 rows total);
- the 20 fixture-executed v2.4 rows, upsampled only enough to survive the retention ratio; and
- neutral, correct-by-construction BUFFER/FILTER variants.

Delegate wording variation and log classification to GPT-5.4/5.3 workers or Cursor Auto, but make
code—not a model—the admission authority. For every target:

1. parse the assistant JSON;
2. validate under its declared algebra profile;
3. reject forbidden ops and holes inconsistent with the question;
4. fixture-execute generated v2.4 rows where supported;
5. canonical-deduplicate questions and IR;
6. check against all frozen eval banks; and
7. write stratum counts and hashes before deterministic shuffling.

Do not copy the old generated FILTER rows. Do not let the v2.4 system prompt leak into v2.3
retention examples. GROUP remains absent.

## Phase 3 — train a candidate, never a serving alias

Use the established manual PEFT trainer with the 9B base, initially holding the known configuration
constant: three epochs, learning rate `1e-4`, LoRA rank 16, gradient accumulation 8, BF16, and
q/k/v/o projection targets. Record any required deviation as a separate experiment.

Write to fresh names such as `adapter-9b-004-candidate-1` and `train-004-candidate-1.log`. The
Heartwood trainer's documented container command may be reused only after explicit authorization
to consume the GPU. Training is not permission to start, stop, restart or repoint inference
services.

Completion requires an adapter directory, tokenizer/config files, a terminal success marker, loss
trace, final diet hash, base revision and command. A partial log is not a checkpoint.

## Phase 4 — evaluate before merging or promotion

If an isolated candidate endpoint already exists, register a new candidate role without changing
`lora9b`. Otherwise stop with a ready-to-serve adapter and ask the service owner to expose it.

Evaluation order:

1. `python3 kit/harness/run_v24_conformance.py --model <candidate-role> --out <evidence> --require-parser-perfect`
   must retain 20/20 gold execution and reach 15/15 parser-required exact matches.
2. The unseen v2.4 wall must reach at least 95% overall and zero critical distinction failures.
3. Run the complete released-v2.3 hard, seed, Indic and cross-sector retention walls with the same
   arm configuration used for their recorded baselines. Aggregate regression must be immaterial;
   critical semantic/honesty regressions are automatic failures.
4. Use an adapter-differentiating response probe as well as compiler probes. Retained compiler
   behavior alone cannot prove that new weights are serving.
5. Only after 1–4 pass, run the pre-registered ecology Hermes multi-turn A/B with identical
   selector/compiler/responder settings, data snapshot and questions for candidate and incumbent.

## Stop and promotion rules

Promote only when all of the following hold:

- required v2.4 parser conformance 15/15;
- gold validation/execution 20/20;
- unseen wall ≥95% with zero critical failures;
- no critical v2.3 regression and no material aggregate regression;
- Hermes A/B at least matches the incumbent on correctness and grounding; and
- all artifacts are versioned, hashed and reproducible.

If the candidate fails, classify the failures before changing the diet. One correction class per
iteration; preserve every failed candidate and report. Do not lower a gate merely because training
is expensive. If serving is the only blocker, finish with a ready-to-serve artifact rather than
modifying shared infrastructure.

## Model delegation policy

- Deterministic scripts: conversion, validation, deduplication, execution, scoring and hashes.
- GPT-5.3 Codex Low: mechanical code/test work.
- GPT-5.4 Mini or Medium: variant drafting and failure clustering.
- Primary high-capability agent: admission, semantic disputes, regression interpretation and
  promotion decision.
- Cursor Auto: fallback when explicit-model quota is unavailable; detect transport/quota failure
  and switch instead of retrying repeatedly.

