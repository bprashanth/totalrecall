# Reintegration plan — not part of the Fable review packet

This file is application-specific working material. Do not include it, `spec-proposals.md`,
`FINDINGS.md`, question banks, traces, source inventories, or chronology files in Fable's algebra
review context.

## Decision

Keep `/home/beeps/src/github.com/bprashanth/idlisseus/dss` unchanged as the reproducible legacy
baseline. Prepare and test a parallel typed runtime here. Export it to a new sibling directory in
the origin repository only after the benchmark reaches hard saturation and an explicit export run
is authorized.

Framework proposal review and application reintegration are related but separate gates:

- compiler/scorer fixes that preserve released operations can enter the parallel runtime after
  saturation without waiting for a new algebra release;
- connector evidence-contract fixes can enter after their source, licence, provenance, and
  conformance tests pass;
- new operations or changed denotations enter only after Fable review, reconciled governance,
  implementation in `kit/`, conformance tests, and an explicit IR version decision.

## Proposed parallel layout

During import and evaluation:

```text
totalrecall/ecology_memory/integration/
  origin-lock.json          # pinned origin commit and admitted asset hashes
  runtime/                  # typed planner/compiler/executor/synthesizer
  adapters/
    legacy.py               # preserves legacy connector return shapes
    typed.py                # Rows/Value/Evidence/DataRequest contracts
  prompts/                  # copied or adapted concise-answer behavior
  manifests/                # connector, source, licence, and model profiles
  tests/                    # legacy-vs-typed comparison matrix
```

After a separately authorized export:

```text
idlisseus/
  dss/                      # untouched legacy baseline
  dss_typed/                # exported, pinned parallel runtime
  agents/hermes/chat.sh     # later gains runtime/model selection without changing defaults
```

Do not bulk-copy every origin asset. Admit files through an allowlist and manifest. Exclude secrets,
caches, downloaded commercial artifacts, mutable ledgers, quarantined data, and files without a
clear redistribution/provenance contract.

## Runtime and model selection

Runtime selection and model selection are independent experimental variables. A model flag alone
must not silently change prompts, algebra, connector contracts, or answer rendering.

Recommended interface:

```text
chat.sh --runtime legacy --model deepseekv4
chat.sh --runtime legacy --model qwen2b
chat.sh --runtime typed  --model deepseekv4
chat.sh --runtime typed  --model qwen2b
chat.sh --runtime typed  --model qwen2b-lora
```

The existing no-argument/default path must remain byte-for-byte behaviorally compatible with the
legacy runtime. Convenience profiles may select a runtime/model pair, but the underlying axes must
remain visible in logs and traces.

## Connector sharing

Share low-level provider clients, credentials/configuration, rate limiting, caches, and raw source
responses where their contracts permit it. Do not share one untyped connector return object between
the two runtimes:

- the legacy adapter preserves the exact origin API expected by existing recipes;
- the typed adapter preserves full rows and emits declared grain, evidence label, provenance,
  licence exclusions, quality notes, and fail-closed DataRequest statuses.

The medium-term clean design is a provider-core package with two adapters. Initially, the typed
runtime may call a pinned read-only origin client through a normalization boundary. Copying the
origin connector directory wholesale would also copy heterogeneous returns, metadata loss, paid or
mutating capabilities, and poorly tested modules into the new truth path.

## Promotion sequence

1. Finish hard saturation and independent semantic trace audit.
2. Freeze hashes for the solver, corpus, connector manifests, and eligible assets.
3. Complete the neutral Fable review and reconcile any framework decisions.
4. Build the parallel integration candidate here; do not modify the origin baseline.
5. Run the full matrix with identical question banks and pinned connector/source snapshots.
6. Compare semantic fidelity, execution status, grounding, synthesis, brevity, latency, and cost.
7. Train the LoRA only from verified training rows; rerun untouched final banks against base,
   LoRA, and frontier profiles.
8. On a separately authorized export invocation, create `dss_typed` and minimally extend
   `chat.sh` while preserving its default legacy behavior.
9. Promote only after rollback, provenance, and regression checks pass.

## Asset policy

Copy or share only assets that are required by the typed runtime and listed in `origin-lock.json`.
Prefer references or adapters for large/upstream-maintained source material. Copy concise-answer
prompts, recipes, and connector cards only when their provenance is recorded and their behavior is
covered by the comparison matrix. A copied snapshot must retain its origin path, commit, hash,
licence, and adaptation note.
