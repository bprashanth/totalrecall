# DESIGN — five ecology workflows, frozen before model contact

Status: preregistered 2026-07-19; no benchmark model had seen these exact prompts when this file and
`bank.json` were written. Direct connector execution was used to verify the gold chain first.

## Claim under test

A frontier agent is sufficient for ordinary web research and can sometimes complete demanding
ecological analysis. Place memory is still useful when an answer must repeatedly satisfy all four
conditions at once:

1. reach the intended source rather than a convenient substitute;
2. execute the spatial/tabular operation, rather than merely describe how one could do it;
3. preserve scope and evidence boundaries (site vs bbox vs region; observation vs proxy vs model);
4. leave an inspectable basis that can be rerun when a source or assumption changes.

This is a reliability/auditability claim, not “small models know more ecology” and not “frontier
models hallucinate.” Q1 is the local-table control. Q2–Q5 each add one or more joins or gates.

## Protocol

- Five frozen, standalone questions; fresh context for every model-question pair.
- No benchmark files, golds, local datasets, or source hints beyond those in the question are
  exposed to the two frontier arms.
- Gemini uses the same Cursor Agent CLI pattern as Heartwood: plain prompt, normal tools, no custom
  system prompt, fresh empty directory.
- DeepSeek uses the configured OpenRouter credential and DeepSeek V4 Flash with OpenRouter web
  search. This is accurately labelled `deepseek-v4-web`; it is not an official DeepSeek
  BYOK run because no separate DeepSeek key is configured on this host.
- The ecology stack receives its normal declared connector catalog and EBTL context. This advantage
  is the intervention being measured: maintained place sources and executable operations.
- One attempt per cell. Tool failures remain in the record. No answer is repaired after scoring.
- Every arm is allowed to refuse or return a collection plan. Honest inability is preferable to a
  fabricated result and can score well on evidence boundary, but not on completed execution.

## Scoring (0–2 each; 10 points/question)

| dimension | 0 | 1 | 2 |
|---|---|---|---|
| task completion | wrong/non-answer | partially answers or only gives a method | completes requested result |
| source reach | no/irrelevant source | right family or secondary source | intended primary deposit/file/layer |
| executed analysis | invented/no operation | proposes operation or partial computation | requested join/filter/raster/gate actually executed |
| evidence boundary | materially conflates scope/class | caveat present but incomplete | observation/proxy/model and geographic scope exact |
| auditability | no checkable basis | links or broad method | source locator + parameters/operation + result trace |

Critical errors are also counted separately: site/regional conflation; absence inferred from no
public record; occurrence count treated as abundance; fire exposure called probability or current
risk; bird-list overlap called a local interaction; or an environmentally rejected taxon presented
as expected at EBTL. A critical error forces `evidence_boundary=0`.

The scorer records one sentence of justification for every dimension. “Has citations” is not a
dimension: citations only help when they contain the claimed basis.

## Trend gate and stop rule

After all three primary arms complete the five questions:

- stop at five if the ordering is stable on at least three of four deep-flow questions **and** the
  observed failure mode is already characterized (reach, execution, boundary, or auditability);
- expand to ten only if the mean gap is under 10 percentage points, the ordering flips by question,
  or a transport/tool outage makes at least two cells uninterpretable;
- run the optional LoRA-9B ablation only if the primary result depends on calling the accepted
  hybrid stack “our model,” or if it is needed to separate model quality from scaffold quality.

No saturation, deployment, or universal superiority claim is permitted from this pilot. The final
claim is bounded to these five EBTL/Western Ghats workflows, these model versions, and this date.

## Transport amendment (before scoring)

The first DeepSeek collection attempted OpenRouter's model-callable `openrouter:web_search` server
tool. On Q1/Q2/Q4/Q5, DeepSeek returned raw DSML invocation markup or `finish_reason=tool_calls`
instead of an executed server-tool result. Those five raw responses are preserved under
`runs/deepseek-v4-web/transport-failures/server-tool/`. Before any scoring, the arm was switched to
OpenRouter's documented one-shot `web` plugin and all five cells were rerun for a consistent
condition. This repairs transport only; prompts, golds, model, search-result cap, and rubric did not
change.

The initial end-to-end ecology run also exposed a useful decomposition: Q2/Q4 clarified despite a
declared composite capability, and Q5 wrapped an already-gated composite in a redundant ESTIMATE.
Those answers remain the scored `ecology-stack-best` first-contact result. A fourth, explicitly
diagnostic `ecology-mech-bind-lora9` arm was added before scoring: it executes the preregistered
plans in `plans.json` and gives only their audited result to the local LoRA-9B. This mirrors the
Heartwood mech-bind experiment and separates substrate ceiling from language-to-capability routing;
it is never described as end-to-end question answering.

After the primary scores and diagnostic ceiling were known, the optional `ecology-stack-lora9`
ablation was run because “our best model” could otherwise be misread as the raw 9B LoRA. It keeps
the same selector/verifier and deterministic substrate but uses merged LoRA-9B-002 for the compiler
and responder. It is reported as an ablation, not a fourth primary arm, and did not change the
five-question stop decision.

The first Gemini attempt used a fresh host working directory but was not filesystem-isolated. It
reproduced an internal source SHA and unpublished connector values, proving it had found host data;
fresh cwd alone was therefore invalid. Cursor's built-in sandbox was unavailable on this host, and
the ecology repository rules forbid starting an isolation container. Before scoring, all five
Gemini cells were archived under `runs/gemini-flash-agent/transport-failures/host-contaminated/`
and rerun inside a Bubblewrap mount namespace that exposes only `/usr`, runtime libraries, Cursor
auth, an empty writable home, and an empty `/work`—not `/home/beeps` or this repository. Network is
shared so normal web research remains available. Structured Cursor event streams are retained.
