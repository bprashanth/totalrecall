# Visual conversation bench - findings

A Meena-style turn-by-turn bench: 7 conversations, 30 turns, plain Indian English, run against the
live livelihoods bridge at `http://172.17.0.1:7013/v1/chat/completions`. One conversation is one
session (`session_id` repeated on every POST; only the current user turn is sent, because the
bridge holds the resumable Codex thread, not the client).

```bash
cd benchmarks/visual_conversation
python3 bench.py --run-id <tag>                       # full run, 30 turns, ~11 min
python3 bench.py --only c4-estimate --run-id spot     # one conversation
python3 bench.py --grade-only runs/<tag>/transcript.json --run-id <tag>   # re-grade, no cost
```

Grading is deterministic (regex and counts, no judge model), so a rerun after a skill-text change
is directly comparable to the run before it. Per-run artefacts land in `runs/<run-id>/`.

## Baseline: run `run1-908663a` (30 turns, 2026-07-25)

**1/30 turns pass (3%).** Conversations clean: 0/7. Median latency 13.9 s, max 36.1 s. The
readability heuristic is fine (93% of turns) - sentences are short and well formed. The failures
are not fluency failures. They are vocabulary, routing and number-suppression failures.

| Category | Turn pass rate |
| --- | --- |
| orientation | 0% |
| graph_comprehension | 0% |
| vocabulary | 0% |
| drilldown | 0% |
| estimate | 0% |
| honest_limits | 25% |
| gk_usage | 0% |

| Check | Pass rate | Reading |
| --- | --- | --- |
| `visual_marker` | 100% | markers are never dropped; the transport side is healthy |
| `rows` / `brevity` / `translates` | 100% | format instructions land when they are asked for |
| `non_match_is_not_absence` | 100% | the "not recorded is not the same as not happening" habit is real |
| `numbers_attributed` | 50% | half the numeric claims are tied to neither data nor general context |
| `honest_gap` | 50% | gaps are stated, but not always in words a person recognises as "no" |
| `offers_alternative` | 50% | a gap is often stated without saying what data does exist |
| `no_keyword_refusal` | 73% | 8 of 30 turns bounce the user's own word back as an unknown name |
| `numbers` | 20% | **the answers almost never contain a figure** |
| `jargon` | 13% | **26 of 30 turns use build-side vocabulary** |

Jargon frequency across the run: `pack` 17, `indexed` 14, `onboarded` 13, `site records` 9,
`this visual` 7, `lineage` 4, `site pack` 4, `AOI` 1, `normalised` 1.

## The five failures worth fixing, ranked by impact

### 1. The registry bounce: the user's word is rejected and no menu is offered

Eight turns ended in a keyword refusal wearing a polite coat.

> I could not plot the trend yet because the indexed metric does not recognise `mnrega works` as a
> registered measure here. [...] Which one do you want: number of works, sanctioned amount,
> expenditure, or persondays?

> I cannot say increasing or decreasing yet, because the local trend registry still does not
> recognise `job work` or `works` as a valid metric here.

> I could not confirm a women-workers trend yet, because the local registry does not recognise
> `women workers` as a valid metric name here.

Two turns later the conversation is still stuck on naming, and the four options offered
(`number of works`, `sanctioned amount`, `expenditure`, `persondays`) are **invented** - the site's
actual measurement registry holds only `daily_wage`, `overtime_rate` and `paid_days_per_month`.
So the model both refused and hallucinated the menu.

The structural cause is on the server side: `result_service` already returns the real option list
in an action (`choose-metric` with `available_metrics`, `dss/visual_index/result_service.py:2576`),
but `_visual_result_summary` in `server.py:1162` does **not** forward `actions` to the dialogue
model - `_visual_upload_summary` (`server.py:1491`) does. The model cannot see the menu it is being
asked to offer, so it improvises one.

Recommendations:
- Forward `actions` (label plus the `available_*` arguments) into `_visual_result_summary`, the
  same shape the upload summary already passes.
- Skill text: on an unresolved request, never say *recognise, registered, registry, metric, match*.
  Say what is there, in the user's frame: "For wages I have the daily wage rate, the overtime rate
  and paid days per month. Which of these are you asking about?"
- Skill text: options offered to the user must come from the returned action arguments. Never
  compose a plausible list.

### 2. Nothing routes past the orientation map, so no number ever reaches the user

Only 6 of 30 turns contain any figure at all. "Which villages have the most survey visits?",
"which occupation is leaving most?", "how many works in the last few years?" - each one came back
as the same site-orientation coverage map:

> From the onboarded site records, this visual shows where record coverage exists and where
> explicit survey effort is documented. It does not support row-level village rankings from the
> summary alone, and this pack is using synthetic test data rather than a real place.

The site index holds exactly what was asked: 48 effort rows carrying `village` and
`village_population` (Thonimalai, Perumpallam, Kadamparai), 164 georeferenced events including the
MGNREGA-style public works source, and out-migration events by occupation. The capabilities exist
too - `coverage-versus-effort`, `stratified-survey-summary`, `entity-record-map`,
`group-record-map`, `metric-time-series`. The dialogue model reached for `site-orientation`, or for
`metric-time-series` with the user's raw words, and when that bounced it stopped.

The producer's headline does carry the figures - *"164 source-linked records representing 13
entities are mapped across 22 cells"* - and the model receives it, yet never speaks a number. The
current instruction ("1-3 sentences that reference the visual and keep its limitations") reads as
permission to describe the picture instead of answering the question.

Recommendations:
- Skill text: a "how many / which is most / show rows" question is never answered from the
  orientation map. Route counts of things that happened to the event and effort capabilities;
  route measured quantities to the metric series.
- Skill text: if the first capability returns unresolved, try the other route **before** writing
  anything to the user. One silent retry, then speak.
- Skill text: if the returned headline contains a figure, say that figure in the answer, in
  everyday units. An answer to a "how many" question that contains no number is a failed answer.
- The migration turns produced "no onboarded method or admitted migration analysis here" while the
  migration source is indexed with 42 interactions. Worth checking whether that capability is
  genuinely unavailable for this pack or whether the model picked the method catalog by mistake.

### 3. Every answer opens in build-side vocabulary

26 of 30 turns. The stock openers are "From the onboarded site records," and "From the available
site pack,", and the stock closer is "this pack is using synthetic test data, so it is not evidence
about a real place" - repeated on nearly every turn of every conversation, including the turn where
the user asked for one line for a monthly report.

The producer's own headline is jargon too ("source-linked records", "entities", "cells"), so a
model that faithfully quotes the headline still fails a plain-language reading.

Recommendations:
- Skill text: an explicit banned list - *pack, site pack, onboarded, indexed, lineage, registry,
  metric, capability, evidence class, denominator, normalised, AOI, cells, "this visual"* - with
  the everyday replacement beside each: *the data I have for this place, records, the map, map
  squares, the survey data*.
- Skill text: say the caveat once per conversation, when it changes the meaning of the answer, not
  on every turn. The synthetic-data warning consumed roughly a third of the words in this run.
- Consider plain-language headlines at the producer, or an explicit instruction to translate the
  headline rather than quote it.

### 4. The estimate flow asks the user to type machine syntax and silently swaps the target

> Please send the empty square as `at:<lat>:<lon>` or share the map/link with that square selected.

The user had already said "the empty square near Kadamparai", and the site holds Kadamparai Village
at 10.261, 76.966. Once coordinates were supplied, the target was swapped without a plain-language
handshake:

> Estimate menu: supported `AOI baseline mean` (recommended, LOW confidence), `nearest surveyed
> cells` (LOW), and `spatial-neighbour regression` (LOW). Not supported: `effort-normalised rate
> transfer` because the target cell has no indexed effort rows. Also, this pack did not match
> `jobs`; it defaulted to `indexed record density`.

To the user's credit-check question the system was admirably frank ("Frankly, I would trust it very
little"), but expressed it as `R^2 -0.10` and "21 training cells".

Recommendations:
- Skill text: resolve a named place plus a direction into a cell yourself; ask for coordinates only
  if the place name is genuinely unknown, and ask in words ("do you mean the square just south of
  Kadamparai village?").
- Skill text: never substitute the quantity silently. "I do not have a count of jobs for that
  square; the closest I can estimate is how many records fall there. Shall I do that?" - and that
  is the ONE clarifying question the turn is allowed.
- Skill text: method names and fit statistics are internal. Say "a rough average of the surrounding
  area" and "I would not put this in a proposal without calling it a rough guess".

### 5. General knowledge is used well, but the wall leaks when retrieval fails

The opening general-knowledge turn was the single best turn in the run - it framed Rs 10,000/month
as generally low, labelled it as general, and invented no site figure. But when the wage data
failed to resolve (failure 1 again), the donor-facing line ended up presenting the general
benchmark as the finding, with no data figure anywhere:

> From the available site pack, we do not yet have a verified wage metric for tea workers, so a
> firm evidence-based wage conclusion is not possible. On general comparison, `Rs 10,000` per month
> appears low, but this should be treated as a provisional benchmark, not a site-confirmed finding.

The site holds `daily_wage` in INR/day across 2017-2024. The honesty is real; the retrieval is what
failed.

Recommendations:
- Keep the existing general-context labelling behaviour; it works.
- Skill text: before answering a "what does the data say" turn with general knowledge, the wage
  route must have been tried by its registered name (see failure 1).
- Skill text: for donor- or report-facing lines, one sentence of data and one of context, each
  labelled. The current output labels the context but has no data sentence at all.

## What is already working, and should not regress

- The `<!-- idli-result:... -->` marker is present on every turn that warrants a visual (30/30).
- Non-match-is-not-absence framing is genuinely good: *"I am not saying school data is absent
  everywhere."*
- Brevity holds when it is asked for; the three-point team-meeting summary was three points.
- Frankness under a direct challenge ("Be frank with me") is excellent.
- Latency is not a problem: median 13.9 s per turn.

## Re-running after a skill-text change

`python3 bench.py --run-id run2-<sha>`, then diff the `check_pass_rate` block against
`runs/run1-908663a/graded.json`. Watch `jargon`, `numbers` and `no_keyword_refusal` first; they
carry most of the signal in this bench.
