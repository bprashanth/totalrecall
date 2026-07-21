# Operator checklist

This file is intentionally self-contained and domain-neutral.

## Before training

- Verify every input hash against `manifest.json`.
- Confirm the current promoted retention diet still has 3,895 rows and the recorded digest.
- Materialize the two private shards using their neutral IDs; do not inspect or transform their
  semantic content beyond the declared mechanical conversion.
- Convert chat-format rows to the trainer's `{system,q,a}` representation while preserving the
  supplied system prompt and assistant target byte-for-byte.
- Expand each clarification dialogue into one holed parse row and one bound parse row.
- Mint BUFFER/FILTER variants only through a deterministic factory.
- Validate every minted target with `validate(ir, "v2.4.0-draft")`.
- Reject any predicate with `value:null`; null-presence testing is not expressible in this bundle.
- Keep a frozen unseen bank outside the training directory before generating the final diet.

## Training

- Use the current 9B base and the established PEFT configuration unless a separately recorded
  experiment changes one variable at a time.
- Write to a fresh candidate adapter directory.
- Preserve the exact command, environment, base revision, seed, epochs, learning rate, LoRA rank,
  row counts, hashes, start/end time, and loss trace.
- Do not alter a serving alias during training.

## Evaluation order

1. Validate and fixture-execute the frozen golds.
2. Run the required parser wall with `--require-parser-perfect`.
3. Run the unseen paraphrase/adversarial wall.
4. Run every released-v2.3 regression bank under the same arm configuration as its baseline.
5. Probe a candidate endpoint with one adapter-differentiating response and one compiler-retention
   example; compiler-only probes may not distinguish two retained adapters.
6. Run the pre-registered Hermes A/B only after steps 1–5 pass.

Do not purge caches, restart services, repoint aliases, or edit the model registry until a candidate
is promoted through a separately authorized serving operation.

