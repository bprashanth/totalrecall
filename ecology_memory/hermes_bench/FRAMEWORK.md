# EBTL NGO drill-down — algebra compiler/responder ROI benchmark

This benchmark adapts the livelihoods Meena method to a conservation programme manager working at
EBTL and across the Eastern Ghats. It tests conversations, but preserves the typed architecture:
an LLM compiles language to the frozen algebra; deterministic code validates/executes connectors
and binds evidence labels; an optional LLM turns only that audited result into plain language.

## Factorial arms

| arm | compiler-in | responder-out |
|---|---|---|
| C2-D | base Qwen 2B | topic-neutral deterministic renderer |
| C9-D | merged LoRA-9B-002 | topic-neutral deterministic renderer |
| C2-R9 | base Qwen 2B | merged LoRA-9B-002 |
| C9-R9 | merged LoRA-9B-002 | merged LoRA-9B-002 |
| CDS-RDS | DeepSeek-v4 | DeepSeek-v4 frontier reference |

The accepted operational arm uses an additional governed split:

| accepted arm | semantic selector | verifier | last-mile compiler | executor | responder |
|---|---|---|---|---|---|
| SQ9DSC2-RQ9 | Qwen 9B | DeepSeek-v4 | base Qwen 2B | deterministic Python | Qwen 9B |

The selector chooses only from machine-readable capability metadata. The 2B compiler binds the
chosen capability to released IR, and code—not Hermes or an LLM—validates the tree, invokes pinned
connectors, applies transfer/evidence gates, and constructs the answer pack. The responder sees
that pack, never unrestricted connector output.

Within each turn, compiler pairs share the same question/history and responder pairs receive the
same executed result. Ecology semantic repair rules are disabled. The compiler sees only the
frozen algebra, generic few-shots, conversation context and machine-readable connector capability
metadata—not answers or phrase-to-route rules. Evidence labels are always executor-owned.

## Stop

The pilot may stop only when all of the following are true:

1. the frozen 14-turn NGO conversation produces the intended answer/DataRequest/history modes;
2. every final answer passes mechanical evidence audits and the blind judge reports zero critical
   errors with mean score at least 1.8/2;
3. a real Hermes multi-turn session prints and persists `typed_evaluate` records, and a resumed
   pronoun follow-up uses the audited history;
4. matched origin evidence shows a material gain in local-data completeness, evidence boundaries,
   or latency for wildlife, snakes, and fire;
5. the LoRA-9B compiler edge pilot either wins or produces enough evidence for an explicit model
   choice; and
6. unit, shell-contract, governance, syntax, and diff checks pass.

This is a practical compiler/responder pilot stop, not `SATURATION.md` practical or hard
saturation and not evidence for a training or deployment-strength claim.

## Status

- 2026-07-17: replicated livelihoods design; verified `merged-9b-002` through the running
  `:8007` SSE proxy without restarting any service. Added distinct `lora9b` compiler role.
- 2026-07-17: implemented factorial engine with semantic ecology repairs disabled, deterministic
  execution, bounded response pack, LoRA responder audit/retry/fallback, Kavya arc, GAPS and rubric.
- 2026-07-18: pilot accepted on frozen `v18_acceptance`. All 14 turns produced the intended mode,
  both rendered arms passed 14/14 mechanical audits, and neither used fallback. The blind judge
  scored `SQ9DSC2-RQ9` 1.964/2 with zero critical errors; the deterministic renderer control scored
  0.929 with one critical error. This is direct evidence that governed synthesis-out adds value.
- 2026-07-18: the 10-turn edge bank gave the LoRA-9B last-mile compiler no semantic-selection
  advantage over Qwen 2B. LoRA-9B took 492.314 s total (49.231 s mean, 31.970 s median), versus
  36.582 s (3.658 s mean, 0.819 s median) for 2B. The accepted default therefore keeps Qwen 2B as
  the capability binder and spends the larger-model budget on semantic selection and audited prose.
- 2026-07-18: post-freeze inspection found two cross-cutting audit gaps: record count could be
  restated as named-taxon count, and unknown local interaction could be restated as impossibility.
  Those acceptance artifacts remain immutable. Current tests reject both errors, and current
  targeted traces fail closed for unsupported elephant–Lantana interaction while preserving the
  declared arachnid discovery/transfer composite.
- 2026-07-18: real Hermes session `20260717_230145_735093` completed local wildlife and snake
  drill-downs, printed connector events, persisted typed tool results, resumed audited history, and
  answered a cobra follow-up without promoting an older property record to a 2024 sighting. `/why`
  displayed the executed site-evidence count from the typed provenance ledger. The
  direct bridge is fast on cached turns; the outer local-2B Hermes TUI still has variable tens-of-
  seconds to minutes orchestration latency and remains an operational optimization target.
