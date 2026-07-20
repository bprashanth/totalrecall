# ECOLOGY-WHY-1: a frontier agent can peak; place memory raises the floor

Status: pilot scored; frozen@2026-07-19 | five questions | isolated frontier protocol

## L1 — headline claim

On five conservation workflows, both frontier conditions scored 16/50 (32%), the accepted
end-to-end ecology stack scored 34/50 (68%), and a diagnostic with the operation supplied to the
same ecology substrate scored 44/50 (88%). The practical value of place memory here is not more
fluent prose. It is reliable access to the intended source, an executable operation, and an
evidence boundary that remains attached to the result.

The counterexample matters: isolated Gemini scored 9/10 on a Zenodo-coordinate-to-WorldCover
raster join. A frontier agent with working tools can do excellent ecological data science. What it
did not provide in this pilot was a dependable floor: two 15-minute runs produced no final answer,
and its ecological-transfer answer replaced measured gates with plausible-sounding habitat
judgements.

## L2 — the comparison

| condition | role | score | critical scope errors |
|---|---|---:|---:|
| Gemini 3.5 Flash, Cursor Agent | isolated frontier agent | 16/50 (32%) | 1 |
| DeepSeek V4 Flash + web | frontier model with web retrieval | 16/50 (32%) | 1 |
| accepted ecology stack | end-to-end selector → algebra → connectors → audited answer | 34/50 (68%) | 0 |
| LoRA-9B end to end | compiler/responder ablation | 33/50 (66%) | 0 |
| plan-bound LoRA-9B | diagnostic substrate/responder ceiling; **not end to end** | 44/50 (88%) | 0 |

The 20-point gap between the accepted stack and the diagnostic ceiling localizes the next problem.
The data and operations can answer all five questions; language-to-capability routing and response
completeness prevent that ceiling from reaching the user. Swapping the 2B compiler/responder for
LoRA-9B does not repair upstream selection: the end-to-end ablation is one point worse, not better.

## L3 — audit trail

- The question wording and gold chains were frozen before model contact in
  [bank.json](bank.json).
- Model access, filesystem isolation, one-attempt policy, rubric, and stop gate are in
  [DESIGN.md](DESIGN.md).
- Every 0–2 score has a written reason in [scoring.json](scoring.json); aggregates are reproduced by
  `python3 score.py`.
- Raw answers and structured traces are under [runs](runs/). Failed transport experiments are kept
  under each arm's `transport-failures/` directory and are not scored.
- [RESULTS.md](RESULTS.md) explains every question and the limits of the claim.

## Why this is a memory case, not merely a model benchmark

The useful unit is a maintained claim path:

`question → declared capability → typed operation → source/geometry → executed result → evidence class → answer audit`

A web agent can recreate that path from scratch. Gemini did so once, impressively. A place-memory
system makes the path named, reusable, testable, and repairable. When the ecology stack failed,
the failure was not “something went wrong”: Q2 and Q4 stopped at selector clarification, while Q5
compiled a declared composite capability inside a redundant outer `ESTIMATE`. Those are concrete
repairs with frozen regression questions.
