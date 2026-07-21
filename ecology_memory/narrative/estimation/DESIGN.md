# DESIGN — estimation when the land is hard to reach

Status: preregistered before model contact on 2026-07-20.

## Why double-click on estimation

The first ecology pilot used five questions to ask whether the patterns in Heartwood's larger
agent benchmark still appeared in conservation work. They did: source substitution, fit mismatch,
plausible methods without execution, and phantom trends all appeared, alongside one excellent
frontier-agent raster workflow.

Five questions cannot tell us whether estimation itself is a stable problem category. This follow-up
therefore holds the agent protocol constant and widens the questions. Estimation matters unusually
often in conservation because direct access to land may require permission, travel, skilled field
teams, appropriate weather and season, repeated visits, and non-disturbance of sensitive species.
An estimate can be useful; pretending that a proxy or transferred model directly observed the place
is not.

## What counts as estimation here

- **Species-distribution model (SDM):** relates occurrence data to environmental covariates to map
  relative suitability or occurrence intensity. Presence-only SDMs do not directly estimate
  abundance, and their background choice and sampling bias matter.
- **Random forest:** a flexible predictor often used with remote-sensing features. Random
  train/test splits can look excellent when nearby pixels or clustered records leak across the
  split; spatially blocked validation tests transfer more honestly.
- **Satellite proxy:** measures reflected radiation, temperature, radar backscatter, active-fire
  detections, or another instrument response. NDVI is not biodiversity, tree cover is not native
  forest, and historical fire detections are not present fire probability.
- **Trend/change estimate:** compares measurements through time. It requires comparable seasons,
  sensors, effort, support and classification rules; otherwise the trend may belong to the
  observation process.
- **Spatial transfer:** moves a relationship or candidate from a donor landscape to a target.
  Environmental overlap can license a modelled hypothesis, never retroactively make it observed.
- **Occupancy/detectability:** separates the probability a species uses a site from the probability
  a survey detects it. A non-detection is data, but is not automatically absence.
- **Causal effect:** asks what restoration or removal changed, not merely what changed afterward.
  A before/after contrast needs a counterfactual and retained uncertainty.

## Bank

Twenty standalone questions, four per family. The family names describe the questions people ask,
not the hidden technique used to answer them:

| family | ids | central failure under pressure |
|---|---|---|
| site state / fit | F1–F4 | “is the plot improving / what fits here?” becomes an unspecified health score |
| colocation / interaction | C1–C4 | “is X near Y?” quietly becomes preference, avoidance, cause or interaction |
| time / change | T1–T4 | changing effort, season or control silently becomes trend or effect |
| spatial transfer | X1–X4 | evidence from elsewhere silently becomes evidence here |
| sparse detection / decision | D1–D4 | sparse detections silently become absence, abundance or current risk |

All twenty prompts are phrased as ordinary conservation-team asks. They do not name a connector,
dataset, estimator, fit gate, validation scheme, or gold value. The agent has to discover the
relevant evidence and decide whether to estimate, bound, or ask for field data. Technical methods
such as SDMs, random forests, satellite time series, occupancy models and causal comparisons exist
only in the hidden gold chain unless an agent independently chooses them.

## Agent protocol

- Three complete agentic models from Heartwood's geodata benchmark roster:
  `claude-4.6-opus-high`, `gpt-5.4-medium`, and `cursor-grok-4.5-medium`. The planned fourth arm,
  `gemini-3.5-flash`, hit the Cursor account usage limit after four answer-bearing cells. A planned
  substitution with `glm-5.2-high` showed that the exhausted allowance was account-wide. Both
  incomplete conditions are transport evidence only; the scored wall is 20 × 3 = 60 runs.
- Cursor Agent CLI, print mode, one fresh session and empty Bubblewrap filesystem per
  model-question cell. All agents receive the same web, shell and package-install affordances.
- The namespace exposes the Cursor runtime and an empty `/work`, but not this repository, the bank,
  its gold rubrics, imported sources or prior runs.
- One attempt per cell, 900-second cap. A timeout, tool error or refusal remains part of the result.
- Prompt is the frozen, ordinary-language question followed only by: “Please give your best answer
  now. Use tools and data where needed, and include citations and enough method detail for me to
  check it.” No source pack, connector catalog, site playbook, estimator hint or fit gate is exposed.
- 20 × 3 = 60 complete scored runs. No retries for answer quality. Forty additional Gemini/GLM
  attempts are retained but excluded for the documented account-level transport limit.
- Retained JSON preserves the answer and tool events. A deterministic post-collection safety pass
  replaces secret-shaped strings found inside third-party web payloads with `[REDACTED_TOKEN]`;
  it does not remove tool calls, results, answers or scoring evidence. The pass is reproducible via
  `sanitize_traces.py`.

The model roster is descriptive, not a tier claim. Model versions and availability are recorded at
collection time. DeepSeek is omitted here because its earlier one-shot web transport is not the
same intervention as a full Cursor shell agent.

### Transport preflight amendment

The first attempted cell never launched the agent: Bubblewrap could not traverse the staged runtime
because its temporary parent was mode 0700. That raw launcher error is retained under
`transport-failures/preflight-permissions/` and is not a benchmark result. Before subject-model
contact, the staging permissions were changed to match the already validated five-question pilot
(traversable/writable disposable home and work mounts; repository still absent from the namespace),
and the collector was re-frozen. A second preflight reached the Cursor runtime but failed before
model contact because the isolated Cursor home was not writable; that launcher record is retained
under `transport-failures/preflight-cursor-home/`. No question, gold chain, prompt, model, timeout
or scoring rule changed.

After the three complete primary arms had returned, Cursor's Gemini allowance was exhausted. Four
Gemini cells contain answers; sixteen end in the explicit account-level usage-limit error. The
complete partial condition is preserved under `transport-failures/gemini-usage-limit/` and excluded
from model scoring rather than being counted as sixteen failures. Before scoring, a `glm-5.2-high`
substitution was attempted with the same frozen questions, prompts, isolation and timeout. All
twenty launches immediately returned the same account-level limit, confirming the condition could
not be collected; those records are under `transport-failures/glm-account-usage-limit/`. This is a
transport-driven roster amendment, not a result-driven retry; neither partial arm contributes to
scores.

## Scoring — five dimensions, 0–2 each

| dimension | 0 | 1 | 2 |
|---|---|---|---|
| estimand | answers a different quantity | target implied but incomplete | names the ecological quantity, place/time/support and decision |
| execution | no relevant operation or invented result | method/partial operation | intended retrieval and estimation/check actually ran |
| fit | ignores bias, leakage, extrapolation or detectability | names a concern without testing it | executes or correctly applies the preregistered fit/validation gate |
| evidence state | conflates observation/proxy/model/cause or local/remote | caveat is incomplete | every transition is correctly labelled and disallowed inference rejected |
| decision record | unsupported confidence or generic advice | some uncertainty/source/action | checkable basis, uncertainty, and smallest useful field action |

An empirical question earns at most 1 for execution if it only describes a plausible workflow.

Critical errors are counted separately:

1. suitability or occurrence records called abundance or confirmed presence;
2. random-split accuracy used as transfer evidence despite an explicit spatial mismatch;
3. satellite proxy called native recovery, soil moisture, biodiversity or current fire risk;
4. record/detection growth called population growth without effort correction;
5. before/after change called a restoration effect without a counterfactual;
6. donor-site mechanism or outcome called local evidence without an admitted transfer gate;
7. short non-detection called absence, or detections called population size without a detection model.

Each score must carry a written reason tied to the retained answer or tool trace. Citations score
only when they support the claimed input or method.

## Questions known before contact, outcomes not known

The gold is a chain of required distinctions and, where possible, a precomputed control. It does not
require a particular algorithm when multiple estimators answer the same estimand honestly. Refusal
can be correct when identification or transfer fails, but must identify the blocking measurement and
the smallest way to collect it.

## Stop and claim

Run every frozen cell once. Stop after 60 completed/retained scored cells; do not tune prompts or rerun
because a result makes the story untidy. Score all cells before editing the presentation. The bank
is large enough to compare failure families but not to claim saturation, production readiness, or a
universal model ranking. The intended claim is bounded to these twenty prompts, three Cursor models,
their July 2026 tool environment, and the stated rubric.
