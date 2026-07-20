# ECOLOGY-WHY-1 results

## Result in one table

Scores are out of 10 per question. The last two rows are ablations, not additional frontier arms.

| workflow | Gemini agent | DeepSeek + web | ecology stack | LoRA-9B E2E | plan-bound LoRA-9B |
|---|---:|---:|---:|---:|---:|
| Q1 local snake survey | 3 | 3 | **10** | 9 | 9 |
| Q2 Zenodo → bbox → raster | **9** | 0 | 3 | 3 | 7 |
| Q3 satellite fire → risk boundary | 0 | 5 | **10** | **10** | **10** |
| Q4 local birds × raw Lantana table | 0 | **5** | **5** | **5** | 8 |
| Q5 discovery → feature + climate gates | 4 | 3 | **6** | **6** | **10** |
| **total** | **16/50** | **16/50** | **34/50** | **33/50** | **44/50** |

## What each question taught us

### Q1 — local sources are a real boundary

The local survey says three snakes were encountered during the September 2024 VES, eleven more
are older property records, and four documented taxa are medically venomous. Both web arms failed
to reach the report. Importantly, neither was penalized for refusing to invent those numbers:
both earned full evidence-boundary credit. Gemini's substitute regional list was clearly labelled
as regional, but it still could not complete the task.

The ecology stack selected the normalized survey rows, returned the exact status split and pages,
and preserved “not encountered in three days” rather than converting it to absence.

Raw: [Gemini](runs/gemini-flash-agent/Q1.json) ·
[DeepSeek](runs/deepseek-v4-web/Q1.json) ·
[ecology stack](runs/ecology-stack-best/Q1.json)

### Q2 — a frontier agent can be the best system in the room

Gemini recovered `01_sites.csv` from Zenodo record 10077040, resolved the Valparai town bbox,
filtered 26 sites to 10, found the WorldCover 2021 tile, and sampled class 10 at all ten points. Its
structured trace shows the operation actually ran. It lost one point only because the response did
not explicitly say that modelled tree cover is not evidence of floristic composition or a
restoration intervention.

The ecology stack had a declared `Zenodo vegetation sites annotated with WorldCover` capability,
but its selector asked the user to choose among irrelevant measurements. This is the cleanest
warning against overstating the current system: maintained capability is useless when routing
cannot bind an explicit request to it.

Raw: [Gemini](runs/gemini-flash-agent/Q2.json) ·
[DeepSeek timeout](runs/deepseek-v4-web/Q2.json) ·
[ecology stack](runs/ecology-stack-best/Q2.json)

### Q3 — data are not the same thing as a risk class

The ecology stack returned zero MODIS active-fire locations in the declared analysis bbox and 1.6
pixel-fire-days, or 0.021 pixel-fire-days/km², in the separate 5-km exposure calculation. It also
said exactly what those values cannot establish: the bbox is not a surveyed property polygon and
historical exposure is not today's calibrated risk without fuel and weather measurements.

DeepSeek gave a good generic explanation of active-fire products and the missing risk inputs but
did not execute the site calculation. Gemini produced no final answer within 15 minutes.

Raw: [Gemini timeout](runs/gemini-flash-agent/Q3.json) ·
[DeepSeek](runs/deepseek-v4-web/Q3.json) ·
[ecology stack](runs/ecology-stack-best/Q3.json)

### Q4 — related papers are not a joined local claim

The gold operation joins 67 locally documented birds to 35 Lantana rows in the raw Dryad table. It
returns five overlaps and raw feeding/fruit-handling counts, but still only supports a regional
mechanism hypothesis: the Dryad observations happened elsewhere.

DeepSeek found an associated article, named three plausible birds, and proposed a good minimal
field check. It did not access either raw input or run the join. The ecology stack identified its
exact combined capability but clarified instead of executing it. The plan-bound diagnostic ran the
join and named all five overlaps, though its fallback response omitted the requested raw counts.

Raw: [Gemini timeout](runs/gemini-flash-agent/Q4.json) ·
[DeepSeek](runs/deepseek-v4-web/Q4.json) ·
[ecology stack](runs/ecology-stack-best/Q4.json) ·
[diagnostic](runs/ecology-mech-bind-lora9/Q4.json)

### Q5 — ecological common sense is not a transfer gate

The frozen chain begins with one local public arachnid record, discovers candidate species in a
declared donor belt, and admits a transfer only if both AlphaEarth feature similarity and WorldClim
climate compatibility pass. In this run, three audited candidates passed climate but failed the
feature threshold, so zero nonlocal species were called expected at EBTL.

Gemini did extensive research but replaced the measured gates with narrative habitat judgements
and called three nonlocal taxa expected. DeepSeek could only reach family/guild evidence and still
called those families likely present. These are the two critical scope errors in the pilot.

The accepted ecology path retrieved 58 licensed regional occurrence rows and research leads, but
the compiler wrapped the already-gated composite in another `ESTIMATE`; the outer operator rejected
the inner record shape and returned a data request. With the frozen plan supplied, the same
connectors and LoRA-9B responder correctly kept all three transfers out. End-to-end LoRA-9B removed
the redundant operator but compiled the target region as the donor belt, showing why a larger
compiler alone is not the fix.

Raw: [Gemini](runs/gemini-flash-agent/Q5.json) ·
[DeepSeek](runs/deepseek-v4-web/Q5.json) ·
[ecology stack](runs/ecology-stack-best/Q5.json) ·
[LoRA-9B end to end](runs/ecology-stack-lora9/Q5.json) ·
[diagnostic](runs/ecology-mech-bind-lora9/Q5.json)

## Stop decision

The pilot stops at five. The accepted stack is 36 percentage points ahead of each frontier arm in
aggregate. Across the four deep-flow questions it loses Q2, ties the best primary result on Q4,
and wins Q3 and Q5; the observed differences are already explained by source reach, execution,
routing, and evidence boundaries. The two Gemini timeouts are counted as bounded agent outcomes,
not an external transport outage: the isolated agent remained active but produced no final answer
within the same declared 900-second cap. Expanding the bank would not resolve an ambiguous ordering.

## What this does and does not establish

It establishes that, on these five frozen workflows on 2026-07-19, the maintained ecology stack
had a substantially higher aggregate floor and no critical evidence-scope error. It also
establishes that the present stack leaves 20 points on the table because routing and rendering do
not expose everything its substrate can execute.

It does not establish that Gemini or DeepSeek generally cannot perform ecological analysis, that
32% is an intrinsic property of either model, that the plan-bound diagnostic is a fair end-to-end
competitor, or that five questions establish saturation. Q2 directly falsifies the strongest
version of the frontier-insufficiency claim.

## Named next repairs

1. Bind explicit source/layer language before broad semantic ambiguity: `Zenodo 10077040` plus
   `WorldCover` should resolve the composite capability directly.
2. Prefer a declared composite when the query names both of its inputs: local bird checklist plus
   Dryad Lantana data should not become a three-way clarification.
3. Treat a selected capability whose contract already includes discovery and gates as atomic; do
   not wrap it in another `ESTIMATE`.
4. Preserve target and donor as distinct typed regions. The LoRA-9B ablation's Q5 error is a
   regression case for target/donor role binding.
5. Improve fallback rendering for structured results. The diagnostic executed Q2 and Q4 but hid
   class values and raw interaction counts from the final answer.

These are proposals from a frozen benchmark. The scored runs must remain unchanged; fixes should be
evaluated as a new benchmark version against the same five regressions.
