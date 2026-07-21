# Ecology narrative benchmark

Status: scored and frozen on 2026-07-19. Start with the new
[ecology field-notes deck](index.html), which follows the root narrative's flow and recuts the
pilot around patchy data and estimation. The earlier [benchmark summary](ecology-place-memory.html)
is retained unchanged. Use [the evidence index](evidence.html) to move from either story to every
scored answer.

This directory asks a narrow version of the Heartwood “why” question:

> If a conservation NGO already has a frontier agent, what does a place-memory stack add?

The pilot does **not** assume that frontier agents are careless. Heartwood's July 2026 runs found
the opposite at their capability ceiling. The ecology hypothesis is about the floor: a vanilla
agent may find a page or propose a sensible method, but deeper place work requires a stable chain
from a declared source, through spatial/data operations, to a claim whose evidence class survives
the trip.

The five-question frozen pilot is in `bank.json`. It compares:

- `gemini-flash-agent`: Gemini 3.5 Flash in Cursor Agent, with its normal web/shell tools and a
  fresh empty working directory per question;
- `deepseek-v4-web`: DeepSeek V4 Flash through the configured OpenRouter API with the one-shot
  web-search plugin, fresh conversation per question; and
- `ecology-stack-best`: the currently accepted ecology path (Qwen 9B semantic selector,
  DeepSeek-v4 verifier, local Qwen 2B algebra compiler, deterministic connectors/executor, Qwen 9B
  audited responder); and
- `ecology-mech-bind-lora9`: a diagnostic ceiling arm in which benchmark code supplies the frozen,
  preregistered operation, deterministic connectors execute it, and merged LoRA-9B-002 may only
  explain the audited result. It measures the value of memory/execution separately from routing.

That last arm is the best *system* demonstrated here; it is not the raw LoRA-9B. The LoRA-9B was
trained on a mixed non-ecology diet and lost the earlier ecology compiler edge test on both
quality/latency. The completed `ecology-stack-lora9` end-to-end ablation also scores 33/50 versus
34/50 for the accepted hybrid, without relabelling the accepted stack or the mech-bind ceiling.

Read `DESIGN.md` for the preregistered scoring and stop rule. Raw, unedited outputs go under
`runs/<arm>/`. Aggregate claims must always link back to those files.

## Estimation recut

[ESTIMATION_RESULTS.md](ESTIMATION_RESULTS.md) is a post-hoc secondary analysis of Q3–Q5. It does
not rescore answers or add model runs. It separates three properties that polished prose can blur:
overall workflow quality, whether the requested analysis actually executed, and whether the
evidence boundary survived. The definition is frozen in [estimation_lens.json](estimation_lens.json)
and the arithmetic is reproduced by `python3 score_estimation.py`.

## Estimation benchmark

The recut was the hint; [the larger estimation benchmark](estimation/index.html) is the independent
follow-up. It asks 20 ordinary conservation questions without exposing datasets, connectors,
estimator names or fit gates to the agents. The frozen scored wall contains 60 Cursor-agent runs
across Claude 4.6 Opus high, GPT-5.4 medium and Cursor Grok 4.5 medium.

Start with [estimation/RESULTS.md](estimation/RESULTS.md), then inspect the complete
[estimation evidence wall](estimation/evidence.html). This study is versioned separately and does
not alter the five-question pilot's scores.
