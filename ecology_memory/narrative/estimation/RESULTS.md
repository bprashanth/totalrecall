# The estimate is where the evidence changes state

Status: 60 frozen runs scored and evidence-audited on 2026-07-20.

## We started with five questions

The first ecology pilot asked five questions to see whether Heartwood's existing patterns survived
contact with conservation work. They did. We saw source substitution, fit mismatch, methods that
read like results, and phantom trends. We also saw a frontier agent complete an excellent raster
workflow from an empty directory.

That pilot left a more important question open. In conservation, access to land is expensive,
seasonal, permission-limited and sometimes unsafe. Decisions often have to be made between field
visits. So what happens when an ordinary user asks an agent to estimate?

We double-clicked on that question with 20 new prompts across five estimation families. The agents
received no connector catalog, source pack, dataset, estimator name, fit gate, benchmark files or
gold answer. They saw questions a conservation worker might actually ask: is the plot improving,
do elephants avoid Lantana, is fire pressure getting worse, could king cobra occur here, and how
many venomous snakes are present?

## The wall

Three Cursor shell agents answered every frozen prompt once, for 60 scored cells. Four cells hit the
fixed 900-second cap and returned no final answer. They remain zeroes. Gemini and GLM attempts hit an
account-wide Cursor usage limit and are retained as transport appendices, not scored as model
failures.

| condition | total | executed estimates | executed fit gates | boundaries preserved | critical-error answers |
|---|---:|---:|---:|---:|---:|
| Claude 4.6 Opus high | 71/200 (35.5%) | 1/20 | 0/20 | 6/20 | 12/20 |
| GPT-5.4 medium | 92/200 (46.0%) | 2/20 | 2/20 | 7/20 | 9/20 |
| Cursor Grok 4.5 medium | 121/200 (60.5%) | 5/20 | 3/20 | 11/20 | 6/20 |
| **all runs** | **284/600 (47.3%)** | **8/60** | **5/60** | **24/60** | **27/60** |

This is a bounded result for these prompts, versions, tools and date. It is not a universal model
ranking. Grok had the strongest aggregate here and also timed out on two adjacent time-series
questions. Opus executed only one requested estimate, but that one was a real six-year MODIS NDVI
analysis. The ceiling is high; the floor moves.

## Finding 1 — a number is cheaper than an estimand

Across all cells, agents earned 71.7% of available decision-record points and 61.7% of estimand
points. They earned 25.8% for execution and 33.3% for fit. They often supplied a confident range,
caveat and next step before establishing the quantity or running the operation that could support
it.

King-cobra answers illustrate the pattern. An agent could retrieve distant occurrences, notice
that the site sits near a broad range edge, and then state a 5–15% chance. That is a potentially
useful hypothesis. It is not an executed species-distribution model, calibrated analogue estimate,
or local occurrence probability. The percentage makes the missing model harder to see.

## Finding 2 — colocation has a verb problem

Only 1 of 12 colocation/interaction cells executed the requested estimate. Nine made a critical
error and nine used geographic transfer. “Near,” “use,” “avoid,” “disperse” and “cause” were often
treated as interchangeable.

The clean counterexample was GPT's fire–infrastructure answer. It retrieved a live VIIRS hotspot
and OpenStreetMap features, measured distance to roads, tracks and settlement edges, compared the
distances with 1,500 random background points, and concluded that one point did not justify a broad
road-patrol shift. The operation constrained the prose.

The common failure was the reverse: regional elephant–Lantana literature became local avoidance,
or a local bird list plus remote fruit-use studies became local seed dispersal. Both input facts
could be true while the relationship at EBTL remained unmeasured.

## Finding 3 — fit is usually spoken, rarely run

The agents mentioned seasonality, sampling bias, donor mismatch, detectability, spatial grain and
counterfactuals often. Only 5 of 60 cells actually executed or correctly applied the required fit,
validation or identification gate.

This mattered most in spatial transfer. Across 12 transfer questions, seven answers did useful
partial work and six preserved their evidence boundary—but none completed a validated transfer
estimate and none executed the hidden fit gate. Climate resemblance was repeatedly treated as a
transfer test. It is one feature, not proof that a donor relationship is in-domain.

An SDM, random forest or satellite model does not solve this automatically. A presence-only SDM
still needs a defensible background and sampling-bias treatment. A random forest still needs
spatially blocked validation. A satellite trend still needs comparable season, sensor, geometry
and a counterfactual before it becomes restoration effect.

## Finding 4 — phantom trends survive the caveat paragraph

The time family contained both the best analyses and the most expensive failures. Four of 12 cells
executed estimates and three ran a real fit gate; four other cells timed out.

The successful bird answers parsed public checklists, controlled for checklist effort and season,
and declined to call a rise in records a population increase. Grok's fire answer downloaded annual
FIRMS archives, compared VIIRS with MODIS, tested several radii, and found a worsening 25-kilometre
landscape signal while rejecting a parcel-level trend because the local support was sparse.

The failure mode was subtler than “forgot a caveat.” One answer acknowledged that its evidence was
regional and still assigned 70–80% confidence that fire pressure at the site had worsened. Another
substituted weather risk after a fire-history source failed. The limitation remained in the prose;
the conclusion crossed it anyway.

## Finding 5 — sometimes the best estimate is a refusal with a survey design

All three agents handled the elephant-population question comparatively well: public occurrence
records cannot estimate how many elephants use the site. A correct answer identifies the missing
repeated individual-level or detection-corrected monitoring and recommends the smallest viable
collection plan.

The snake-occupancy questions exposed the opposite. Two agents processed public points and then
called the output occupancy. Occurrence density is shaped by observer effort and accessibility;
occupancy requires repeated detections and non-detections. A real computation can still estimate
the wrong thing.

This makes refusal part of estimation, not its absence. “The transfer failed; collect these three
measurements” is more decision-useful than a precise number whose evidence state is wrong.

## What the result says about place memory

Vanilla agents can recreate sophisticated ecological workflows from public data. The successful
NDVI, bird-effort and fire-spatial runs demonstrate that clearly. But the user cannot know in
advance which question will trigger that ceiling.

A maintained ecology memory should not hardwire answers. It should preserve the parts the agents
reconstructed inconsistently:

`question → estimand → source patches → operation → fit gate → evidence transition → decision`

The language model still compiles the user's ordinary question into that algebra and synthesizes
the result. The maintained layer makes the source geometry, estimator, failed gate, and forbidden
claim inspectable. It turns a brilliant one-off analysis into a regression-tested capability—and
turns a failed estimate into a specific data request instead of a plausible paragraph.

## Audit trail

- The frozen questions and hidden distinctions are in [bank.json](bank.json).
- The isolation, prompt, roster amendments, rubric and stop condition are in [DESIGN.md](DESIGN.md).
- [scoring.json](scoring.json) contains all 60 final reviews and written reasons.
- [audit_overrides.json](audit_overrides.json) records every score changed during evidence audit.
- Run `python3 finalize_scoring.py && python3 score.py` to reproduce [summary.json](summary.json).
- The raw answers and tool events are linked from [evidence.html](evidence.html).

DeepSeek V4 performed first-pass rubric coding only. It was not a subject model and did not decide
the final scores. Twelve rubric-drift corrections and one malformed-cell manual review are recorded
explicitly in the audit ledger.
