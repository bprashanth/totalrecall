# Ecology ANR bench — findings, ranked by impact

Run `round1`, 52 turns across 8 conversations, live against `insight-valparai`
(`http://172.17.0.1:7012`, model `idli-insight-valparai`), 2026-07-26.

**Headline: 3 of 52 turns (6%) pass every dimension. Ignoring the two next-step dimensions,
21 of 52 (40%) pass.** No conversation is clean end to end.

The gap between those two numbers is the story. The prose is well-mannered — no transport
leakage (100%), no re-asking (100%), one clarifying question honoured (100%), thread continuity
held across all 45 turns where it was tested, and jargon was clean in 50 of 52 turns. What fails
is the ecology: the system repeatedly tells a field ecologist that data is absent when it is
sitting in the index, and it almost never tells them what to do next.

| Dimension | Pass | n |
| --- | --- | --- |
| `next_step_in_prose` | 17% | 52 |
| `dead_end` | 19% | 52 |
| `gap_or_answer` | 33% | 3 |
| `honest_gap` | 50% | 6 |
| `names_alternative` | 50% | 4 |
| `general_knowledge_labelled` | 50% | 2 |
| `has_evidence` | 56% | 27 |
| `rows` | 56% | 16 |
| `traceable` | 67% | 27 |
| `join_rule_disclosed` | 67% | 3 |
| `right_tool` | 71% | 24 |
| `confidence` | 92% | 12 |
| `not_catch_all` | 95% | 20 |
| `jargon` | 96% | 52 |
| `multi_turn`, `no_reask`, `no_transport_leak`, `questions`, `visual_present`, `responded` | 100% | — |

Mean language score 1.58/2. Median latency 18.5 s. Three turns were retried through a bridge
restart (another agent was mid-change); continuity survived it — turn 4 of `c2` correctly
referenced the bird comparison established in turn 2.

A note on grader calibration: the first pass scored `honest_gap` at 0% and `confidence` at 58%.
Reading the transcripts showed both were regex artifacts — "there is still no recorded lantana
name here" and "I cannot call that a real plot-type effect yet" are a gap and a confidence
statement in anyone's English. Both patterns were widened and the same transcript re-graded
offline. The numbers above are the calibrated ones. `dead_end` was *not* softened: it was checked
against the audit trail and got worse, not better (see fix 3).

---

## 1. [bridge] A name that does not resolve is reported as data that does not exist

**Impact: highest. This is the failure that would lose the user's trust in one sitting.**

The pack holds `Lantana camara` — 36 records across three surveys (29 in
`dryad-8kprr4xvb-restoration-opportunities`, 4 in the plant community survey `zenodo-7457732`,
3 in the threatened-tree inventory). The assistant called `entity-record-map` with
`{"entity": "Lantana"}`, the bare genus did not match the only alias (`lantana camara`), and it
reported absence:

> **c3/t2** — *"Do you have anything at all on lantana at this site? Even just where it has been
> recorded?"*
> "From the data this site has, I do not have a recorded `lantana` name or a map of its records
> here. The site search and the map both came back as a name non-match, and that is not evidence
> that lantana is absent. If you want, I can next check nearby public records for
> `Lantana camara`."

It types the correct binomial in the last sentence and never tries it against the site's own
index. It then spends four more turns designing a field campaign to collect data it already has:

> **c3/t3** — "From the data this site has, we do not yet have a recorded `lantana` name to
> calibrate any stand-in against actual lantana records here. […] Plant community plots are
> usually the better stand-in"

The plant community plots are exactly where four of the lantana records live.

The same mechanism fires on mammals. `Mammalia` is a valid class group (30 entities, three
dedicated mammal occurrence sources spanning 2015–2024), and the answer is:

> **c1/t6** — *"Show me the actual records behind the mammal counts for one year."*
> "The remaining data gap is that a plain search for "mammal" in the local records also did not
> resolve to one recorded mammal name, so I cannot yet show you a single raw row from that route."

**Root cause, and it is one line.** The accepted-value lists in `visual-result/SKILL.md` are
**truncated alphabetically**, and the skill text tells the model to treat them as exhaustive
("These values exist in this site's data and will resolve; anything else will not"). For
`rank: class` the list reads *Amphibia, Aves, Gnetopsida, Insecta, Liliopsida, Lycopodiopsida* —
six items, alphabetical, so `Magnoliopsida` (575 entities, the largest group in the index) and
`Mammalia` are both cut off. `metric-time-series` shows ten metrics, all beginning `a`, ending at
`adult_medium_large_animal_dispersed_species_richness` — every metric after "adult_m" is invisible.

**Fix, in order of cheapness:**
1. Sort the accepted-value lists by record count, not alphabetically, and raise the cap. The
   truncation is what makes the largest groups invisible.
2. Say in the skill text that the list is a sample, not the whole vocabulary, and that an
   unresolved name must be retried once against the fuller index before absence is reported.
3. Resolve genus → species and common name → binomial in `entity-record-map` before returning a
   non-match (`Lantana` → `Lantana camara`; `mammal` → `rank: class, group: Mammalia`).
4. Make the returned non-match carry the near-misses it rejected, so the model has something to
   offer instead of a denial.

## 2. [bridge] The frugivory network — the single richest thing in this pack — is reported as empty

**Impact: very high. This is the question the site's data was assembled to answer.**

The index holds 5,622 source-linked interaction rows with named subjects and objects:
`observed_visiting_focal_tree`, `focal_scan_on_fruiting_tree`, `detected_at_seed_experiment`,
`camera_detected_at_focal_seed_tree`. Concrete pairs include *Ocyceros griseus* (Malabar grey
hornbill) on *Myristica dactyloides*, 132 scans; *Ratufa indica* on *Canarium strictum*, 130;
*Gracula indica* on *Heynea trijuga*, 392.

The user asked for exactly this, and `interaction-map` ran:

> **c5/t2** — *"Which trees here actually get their seed moved by animals, and by which animals?"*
> "From the data this site has, there are no recorded source-linked rows for seed movement itself,
> so I cannot name tree-animal pairs here from this map. What the records do have for follow-up
> are four observed relation types around focal trees and seed experiments"

It has the four relation types in hand and will not descend from the type to the pairs. The
follow-up turn does the same with counts:

> **c5/t3** — "there are 745 recorded detections at seed experiments linking 37 recorded things in
> 72 pairs […] But this map does not show which tree loses the most seed"

"37 recorded things in 72 pairs" is the network, described as a shape and never named. A planting
list grounded in this site's own records was the whole point of the conversation and it never
arrives.

**Fix:** `interaction-map` should return the top named subject–object pairs with counts in its
summary, not just interaction-type totals. The model can only relay what the summary returns, and
the skill text forbids it from inventing figures — correctly. The capability is starving the
answer.

## 3. [bridge] + [ui] Four answers in five leave the user with nowhere to go

**Impact: very high, and cheap to fix.**

`next_step_in_prose` passes on 9 of 52 turns. The bridge prompt is the direct cause — it says:

> "Do not add a prose menu; the controller renders valid next actions as buttons."

**The controller rendered buttons on 2 of 52 turns.** So the model is forbidden from writing a
next step on the grounds that the interface will supply one, and the interface supplies one 4% of
the time. The user gets neither. Every one of these ends on a limitation:

> **c1/t1** — "This map is useful for seeing where monitoring was actually documented, but it does
> not show the year range, so the remaining data gap is how far back those monitored series go."

> **c2/t1** — "So yes, there is something to inspect here, but this map view alone does not yet
> show whether the comparison was actually run or what it found."

The house style has become: state the finding, then retract half of it, then stop. It reads as
careful and lands as helpless.

**Fix:**
- [bridge] Drop the "do not add a prose menu" instruction, or condition it on `actions` actually
  being non-empty. Require every answer to end on a move the user could make — the sentence the
  good turns already produce ("I can next show records against survey effort").
- [ui] Find out why `insight_actions` fires on 2 turns in 52. If buttons are the plan, they need
  to be present; if they are not reliable, prose must carry it.

## 4. [bridge] Denominators are asked for, exist, and are refused

**Impact: high — this is the "is the difference real" question, i.e. the reason to trust the tool.**

`dryad-rjdfn2zc3-restoration-birds` declares `Site_type` and `PlotID` as category properties.
The user asked for the split and got a total:

> **c2/t3** — *"How many plots in each of those three, and how many times was each visited?"*
> "the bird comparison table confirms 69 surveyed plots across the three plot types and 460 visits
> in total. The exact split by plot type is not exposed in the short summary here, and the
> follow-up count trace I tried for the per-type breakdown did not return, so I cannot state those
> three counts safely from this run alone."

69 plots and 460 visits across three types, with the per-type split withheld. The skill text
already says a counting question must carry a figure or name what came back empty — it does the
second half and stops. `stratified-survey-summary` with `category_property: Site_type` is the
answer and it was never re-run.

**Fix:** when a summary returns a total and the user asked for a breakdown, re-call the same
capability with the declared `category_property` before answering. The one-silent-retry rule
already exists in the skill text for unresolved calls; extend it to under-resolved ones.

## 5. [bridge] Drill-down collapses: no ranking → re-ask → answers about a different unit

**Impact: high. This is conversation 6's entire arc, failing in three consecutive turns.**

> **c6/t2** — *"Which plot has the highest share of rainforest species?"*
> "I cannot identify a highest-plot value for rainforest-species share from the available plot
> summaries. […] this site does not currently hold that rainforest-share table in a usable form"

> **c6/t3** — *"Tell me more about that one. What is the stem density there, and what does the
> canopy look like?"*
> "I do not yet have a specific plot to inspect. […] Which plot do you want me to open: name the
> plot, or point to it on the map?"

> **c6/t4** — *"Where does that number come from? Show me the rows."*
> "This is for the busiest square on that map, because no specific point or square was identified
> in your question. In that 1.1 km square spanning 10.360–10.370 N and 76.990–77.000 E, the number
> is a straight count of 3,300 recorded observations from the bird recovery study"

The user asked about a vegetation **plot**; the answer is about a 1.1 km **map square**, sourced
from the **bird** study, and the substitution is never flagged as a substitution. The index holds
`nativeAlien` on `zenodo-10077040` and habit/habitat-affinity groups that would rank plots
directly.

**Fix:** when a plot-level question cannot be answered at plot level, say that in those words and
name the unit actually being used. Silently changing the unit of analysis is worse than failing.

## 6. [bridge] The where-to-survey answer ranks by where we have already looked

**Impact: high, because conversation 7 is otherwise the best thread in the run.**

`c7` reasons well for six turns — "records are spread across 302 squares inside the site's
boundary, but explicit survey effort is documented in only 42 squares […] prioritise squares that
show records with little or no documented effort". That is correct value-of-information framing.
Then the final ask inverts it:

> **c7/t7** — *"Rank the top five places, with a reason for each that I could put in a proposal."*
> "1. the 1.1 km square spanning 10.360–10.370 N and 76.990–77.000 E, because it has the strongest
> recorded activity on this view; 2. […] because it is the next strongest concentration of
> records […] This ranking comes from the biggest record concentrations on the map, not from proof
> of ecological importance"

Ranked by record density — the opposite of the coverage-gap logic it argued for six turns running,
and it says so itself. Separately: the site holds **205 named places** (Andiparai, Karian-Shola,
Puduthottam, Iyerpadi). No ecologist will put "10.340–10.350 N, 76.890–76.900 E" in a proposal.

**Fix:** rank by the gap statistic (records present, effort absent) rather than raw count, and
resolve each square to its nearest named place in the summary. The names are already in the index.

## 7. [ui] A raw failure panel is appended to the user's answer, carrying the banned vocabulary

**Impact: medium-high. Both `jargon` failures in the run come from here, not from the model.**

The two longest planning answers have a "Scientific analysis / What Idli Insight executed" panel
stapled to them containing:

> "no valid Algebra tree was returned. **What Idli Insight executed** Execution stopped with site
> pack capability not parameterised. The next required input is: Parameterise this capability
> with…"

`site pack`, `capability`, `parameterise` — every one on the banned list, reaching the user
verbatim, in the two answers most likely to be shown to a funder. The model's own prose in both
turns is clean; the controller undoes it.

**Fix:** [ui] suppress the panel when the run failed, or render the failure in the same plain
English the rest of the answer uses. A user does not need to know an Algebra tree was not returned.

## 8. [bridge] Evidence is attributed to the wrong survey

**Impact: medium, but corrosive — a wrong citation is worse than none, and no regex catches it.**

> **c3/t6** — "From the data this site has, 132 plant community plot sites are mapped, with 264
> explicit visits, so these are the plots you could likely target for revisit."

The call was `stratified-survey-summary` on `dryad-8kprr4xvb-restoration-opportunities`. The plant
community survey is `zenodo-7457732`. The number is real; the survey named in prose is not the one
it came from. The user is being sent to revisit the wrong plots. The same slip appears in `c6/t5`
and `c6/t6`, where plot questions get answered from "the bird recovery study".

**Fix:** carry the source title through from the result summary into the sentence, rather than
letting the model name the survey from context.

## 9. [bridge] Numbers go missing on orientation turns

**Impact: medium.** `has_evidence` fails on 12 of 27 turns that asked how much / which / where.
The orientation result carries figures (42,348 records, 962 kinds of thing, 302 squares) and some
turns relay them well — `c6/t1` does. Others describe the same result with no figure at all:

> **c1/t1** — "monitoring is substantial and spread widely across the Anamalai fragments, with
> records in many places but explicit survey effort recorded in a much smaller subset"

"Substantial", "many", "a much smaller subset" — the numbers were in hand. `c1/t2` lists nine
metric names for a trend question without a single year range or record count.

**Fix:** require the figure the summary returned whenever one is present. This is a prompt
sentence, not a capability change.

---

## What is already good, and should not be regressed

- **Thread continuity is excellent.** 45/45 on carrying the established entity, place or word;
  0 re-asks for something the user already said. It survived a mid-run bridge restart.
- **The join rule gets disclosed well when asked.** `c4/t2`: "the default match is shared squares
  inside this site's boundary […] That does not mean same plot, same visit, or direct interaction;
  and it is not same year unless we deliberately add a same-year condition." That is exactly right
  and exactly the register wanted.
- **Non-match is not absence** is said reliably, even when — as in fix 1 — the underlying claim of
  non-match is itself wrong.
- **No invention.** Zero fabricated weeding trials, herbicide records or seed-predation results
  across 52 turns. The system fails by under-claiming, never by over-claiming.
- **Register is close.** Mean 1.58/2; "squares inside this site's boundary" is used consistently
  in preference to internal names. The remaining drag is passive voice and a habit of ending on a
  caveat.

## Suggested order of work

1. Un-truncate and re-sort the accepted-value lists (fix 1) — one change, unblocks mammals,
   Magnoliopsida and most metrics.
2. Make every answer end on a move (fix 3) — one prompt sentence plus an interface decision;
   moves 43 turns.
3. Return named pairs from `interaction-map` (fix 2) — unblocks the whole replanting line of work.
4. Retry with the declared category when a breakdown is asked for (fix 4).
5. Suppress or translate the failure panel (fix 7) — small, and it is the only jargon left.
