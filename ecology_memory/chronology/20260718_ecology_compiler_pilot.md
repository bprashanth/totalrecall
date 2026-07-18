# 2026-07-18 — compiler/executor/responder pilot closure

## Why the run resumed

The previous work stopped after a useful selector/compiler checkpoint. That was not the agreed
terminal condition: the frozen dialogue had not yet been blind-scored, the LoRA-9B edge decision
was incomplete, and a real Hermes session had not demonstrated both typed tool persistence and
resume. The run therefore resumed without changing the origin repository or restarting model
services.

## Terminal condition

The pre-declared practical pilot stop was:

1. 14/14 intended answer, DataRequest, clarification, or history-synthesis modes;
2. all rendered turns pass mechanical evidence audits;
3. blind mean at least 1.8/2 and zero critical errors for the selected arm;
4. live Hermes prints and persists typed calls and a resumed follow-up uses audited history;
5. typed materially improves the matched origin wildlife, snake, and fire evidence boundary;
6. choose 2B or LoRA-9B for last-mile compilation from measured quality/latency; and
7. all unit, CLI, governance, syntax, and diff checks pass.

This is a compiler/responder pilot. It is not sector practical saturation, hard saturation,
retraining evidence, or a deployment-strength claim.

## Runtime that was tested

```text
user -> Hermes dialogue shell -> typed_evaluate
     -> Qwen-9B semantic capability selector
     -> DeepSeek-v4 constrained verifier
     -> Qwen-2B last-mile IR compiler/binder
     -> Python schema validator and deterministic executor
     -> pinned origin adapters + admitted typed sources
     -> code-owned evidence/transfer audits
     -> Qwen-9B bounded responder
     -> Hermes/session ledger
```

Hermes does not execute algebra. Its plugin invokes the bridge and records the call. Python owns IR
validation, connector execution, transfer gates, labels, provenance, and DataRequest decisions.
The LLMs may select/compile and phrase an audited pack; they cannot promote a regional record to a
local observation or manufacture a connector.

## Evidence and connector changes

- Mirrored and hash-locked the origin production connector set at
  `efcfc77111cf30aed7d125c9c6c2fe67febf7ad3`; origin stayed read-only.
- Reused exact origin fire, points, land-cover, greenness, and bge-small semantic discovery code
  through typed adapters.
- Imported page-addressed local evidence missed by the semantic corpus: the full 2024 fauna
  summary, 67 bird taxa, 14 property snake taxa split into three direct 2024 encounters and eleven
  older records, venomous-record status, elephant signs, nursery, invasive-management, and soil
  notes.
- Added bounded regional evidence for bird–Lantana and arachnid questions. Local interactions
  remain unknown unless locally observed.
- Implemented data-derived arachnid discovery: higher-taxon occurrence queries produce candidate
  names, then exact occurrence support and declared feature/climate gates determine whether any
  regional candidate is admitted. No shortlist comes from model memory.
- Corrected fire semantics from supposed “events/risk” to pixel-fire-day sensor detections over the
  actual measurement footprint; future risk requires fuel and weather calibration.

No new IR operation was introduced. The relevant algebra gains are stricter execution contracts:
measurement grain/unit, count grain, evidence class, lineage, absence polarity, gate thresholds,
interaction boundaries, and code-owned multi-turn evidence memory.

## Frozen acceptance result

Artifacts: `hermes_bench/transcripts/v18_acceptance/`.

- 14/14 intended execution modes and statuses.
- 14/14 mechanical audits for `SQ9DSC2-D` and `SQ9DSC2-RQ9`.
- Zero fallbacks.
- Qwen-9B audited response arm: 1.964/2 blind mean, zero critical errors.
- Deterministic renderer control: 0.929/2, one critical error.
- Compile/execute: 40.289 s total, 2.878 s mean, 0.004 s median; uncached connector turns account
  for the mean/median gap.

This shows that synthesis-out has high ROI when it receives a deterministic audited evidence pack.
It does not show that a free-form larger-model agent should own connector work.

## 2B versus LoRA-9B compilation

The same 10-turn natural field edge bank was run with the same Qwen-9B selector and DeepSeek
verifier.

| last-mile compiler | total | mean | median | semantic-selector outcome |
|---|---:|---:|---:|---|
| merged LoRA-9B-002 | 492.314 s | 49.231 s | 31.970 s | no gain |
| Qwen 2B | 36.582 s | 3.658 s | 0.819 s | same |

The LoRA penalty was about 13.5× with no observed edge-bank quality advantage, so Qwen 2B remains
the binder/compiler. A post-run fault in both edge artifacts—subject-only elephant evidence
answering an elephant–Lantana interaction—was fixed cross-cuttingly: empty verifier decisions fail
closed for atomic capabilities, while explicitly declared composites can be semantically
adjudicated. Those old artifacts remain immutable and are not claimed as final acceptance.

## Post-freeze audit hardening

Inspection found two answer-level errors that a coarse audit could miss:

- 58 occurrence records had been phrased as 58 named species; the executor actually had 31 named
  taxa. Count-grain audit now distinguishes records from taxa.
- Zero local Lantana points had been phrased as birds being unable to disperse it. Interaction audit
  now requires “unknown locally” and a direct observation request rather than impossibility.

Current targeted traces also preserve the 0.5 feature-fraction and 0.8 climate-envelope thresholds
and keep locally observed arachnids separate from regional transfer candidates.

## Live Hermes proof

Session: `20260717_230145_735093` in the isolated `dss-eval` profile.

The conversation opened broadly, selected wildlife, drilled into snakes, resumed the same session,
and asked which records were direct 2024 sightings and whether cobra was among them. Hermes printed
real `typed_evaluate` and connector events. The resumed answer correctly named Common Sand Boa,
Striped Keelback, and Barred Wolf Snake as the three direct sightings and kept Spectacled Cobra as
an older property record.

The first three tool results persisted. The first resume test exposed a genuine bug: non-interactive
resume did not expose the CLI `SessionDB` to the plugin, so its new typed call was displayed but not
stored. The wrapper now passes the resume session ID; the plugin uses Hermes' own `SessionDB` API as
a fallback. The next resumed turn persisted correctly. A final resumed count question brought the
verified state to 24 messages, five typed tool results, and seven user turns. The bridge now also
translates only executed provenance into the existing `/why` ledger. The live `/why` command showed
“used 14 site evidence” for the snake answer rather than “No data steps recorded.” The outer local-
2B Hermes shell still has variable UI/orchestration latency (roughly tens of seconds, with one
multi-minute interactive render); the direct typed bridge is materially faster. That operational
issue does not change the evidence result and remains visible rather than being folded into model
quality.

## Origin comparison and boundary

Recovered origin traces are sufficient for the matched pilot decision and avoid another hour-long
production run. Origin DeepSeek used many public-search/tool calls, sometimes failed taxon
resolution, and did not retrieve the decisive local PDF through embeddings. Typed uses the same
production connector functions, adds the missing local evidence and stricter boundaries, and is
more complete and safer for wildlife, snakes, and fire.

No files in `/home/beeps/src/github.com/bprashanth/idlisseus` were changed. No back-integration was
performed. The next origin action, if authorized later, is to export this parallel candidate as a
sibling runtime and compare it without changing the legacy default.
