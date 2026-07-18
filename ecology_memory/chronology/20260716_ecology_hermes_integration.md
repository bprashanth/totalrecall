# 2026-07-16 — Hermes-native comparison and site binding

## Why this run happened

The first parallel integration proved the typed pipeline but accidentally changed two variables at
once: algebra and shell. The typed branch used a generic REPL, while the production baseline used
Hermes with persistent sessions, clarification rules, site context, skills, and answer-discipline
hooks. A fair comparison requires the same conversational shell around every algebra condition.

## What changed

`integration/chat.sh` now exposes independent runtime (`typed`, `untyped`, `no-algebra`), model,
and context (`general`, `ebtl`) axes. With no flags it still executes the origin entrypoint. The
exact origin DeepSeek path remains directly selectable. New modes use a separately deployed
`dss-eval` Hermes profile and mode/context-specific workspaces; no origin file, default profile,
container, or model server was restarted or modified.

Typed execution moved into a Hermes pre-turn profile hook. It computes a deterministic typed trace
for scoped turns without exposing tools to the conversational model. This is required for the
current local vLLM, which rejects Hermes tool schemas because automatic tool choice is not enabled.
Hermes still owns the session and clarification exchange.

The optional EBTL context imports the exact site bbox and centre. A site-centre record connector was
added so raster annotations can be tested at the same seed location as the origin. Its grain is
`declared-site-center` and evidence is a proxy; it cannot stand in for full-AOI sampling. A land
cover class synonym found in the DeepSeek container trace was added to the typed layer resolver.

## What the comparison found

DeepSeek gave a good typed two-turn interaction: it clarified the broad opening, then reported the
WorldCover shrubland class at the declared point with source and limitation. Exact origin DeepSeek
also clarified well, but used tools before asking and ended with the known auxiliary local-model
alias warning. No-algebra DeepSeek introduced unsupported site attributes. Base local 2B retained
the correct categorical result but weakened evidence labels and added meta prose.

The local endpoint advertises only `qwen3.5-2b`; LoRA preflight therefore fails before chat. Hermes
also considers the base model's actual 8K context too small. A profile-only override permits short
diagnostics with a 2,048-token output cap, but it is explicitly excluded from long-context claims.

## Governance result

Fable's review was checked against the released executor. The proposed grouping representation is
not backward-compatible because `AGGREGATE by:space` currently collapses to scalar. Codex's neutral
review accepts the grouping pressure but defers representation until a keyed-result RFC. Units and
temporal alignment remain the first executor-only hardening track; FILTER follows field schemas;
corroboration waits for lineage ancestry.

## Verification and next gate

All 118 sector contracts, the Hermes shell CLI contract, and governance validation pass. The origin
worktree remains clean. This is integration smoke, not saturation. The next release-bearing step is
an untouched multi-turn comparison bank scored across clarification, follow-up binding, grounding,
evidence labels, unsupported claims, brevity, latency, tool errors, and cost. The unavailable LoRA
must be deployed by the model owner before its column can run.

## Locked-connector correction and matched wall

The initial typed harness had independently implemented several connector calculations. The
production `dss/connectors` directory was subsequently copied unchanged into the reversible
integration tree and pinned by the existing origin lock. Thin adapters now call exact production
functions for fire, land cover, greenness, occurrence merging, and semantic corpus discovery.

Typed execution is now a registered Hermes tool boundary. Because the bridge invokes that tool
programmatically before the conversational completion, Hermes correctly persists zero
*model-authored* tool calls. The shell separately prints `typed_evaluate` and each actual connector
event, removing the misleading appearance that no data work occurred.

Matched resumed sessions covered fire exposure, elephant evidence, land cover, restoration change,
and snakes. The typed arm used the same connector implementation for the first four source families
and a stronger imported primary survey for snakes. It retained exact AOI/buffer distinctions,
labelled satellite products and proxies, refused absence and causal claims, and avoided the
baseline's period/scale drift. The complete comparison is
`integration/eval/runs/20260716-origin-equivalence-wall.md`.

Exact copying also made the main incompatibility concrete: `points.py` writes a lossy common CSV
without license, record URL, quality, or full-date fields and cannot accept a typed time window.
Those constraints now fail closed or remain explicitly labelled. The five-topic wall passes 131
contracts and the shell contract, but global connector parity and LoRA superiority remain open.
