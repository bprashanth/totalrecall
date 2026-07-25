# Ecology ANR bench — findings

Round 2, 66 turns across 10 conversations, live against `insight-valparai`, 2026-07-26, after the
bridge shipped commit `1a57eb9`.

**46 of 66 turns (70%) pass every dimension, against 3 of 52 (6%) in round 1.** One conversation
(`c7`, the survey budget) is now clean end to end. Uncorrected — that is, grading round 2 with the
round-1 regexes — the score is 37/66; the difference and its justification are set out in
RESULTS.md under "How this number was baselined", and both numbers are published on purpose.

| Dimension | R1 | R2 | n |
| --- | --- | --- | --- |
| `next_step_in_prose` | 17% | **98%** | 66 |
| `dead_end` | 19% | **98%** | 66 |
| `has_evidence` | 56% | **85%** | 34 |
| `traceable` | 67% | **91%** | 33 |
| `honest_gap` | 50% | **100%** | 7 |
| `gap_or_answer` | 33% | **100%** | 5 |
| `right_tool` | 71% | **83%** | 29 |
| `rows` | 56% | 65% | 23 |
| `not_catch_all` | 95% | 100% | 25 |
| `jargon` | 96% | 98% | 66 |
| `join_rule_disclosed` | 67% | 100% | 6 |
| `place_names` | — | 100% | 3 |
| `confidence` | 92% | 94% | 18 |
| `multi_turn`, `no_reask`, `no_transport_leak`, `visual_present`, `questions`, `responded` | 100% | 100% | — |

| Conversation | Pass |
| --- | --- |
| c7 survey budget | 100% |
| c8 monitoring plan | 86% |
| c4 natives suppress | 83% |
| c10 budget monitoring plan (new) | 71% |
| c1 what is here | 67% |
| c6 what grows where | 67% |
| c2 does restoration work | 57% |
| c5 what to replant | 57% |
| c9 seed dispersal design (new) | 57% |
| c3 lantana | 50% |

## The three round-1 headline failures are fixed

**Name resolution.** The flagship failure is gone, and gone well:

> **c3/t1** — "I read "lantana" as *Lantana camara*, which this site has 36 records of; this map
> shows where those records are available, with 17 in squares inside the site boundary"

36 records, 15 squares, 2003–2022 — every figure matches the index. It now names the plant
community structure survey correctly, which also closes round-1 finding 8 (evidence attributed to
the wrong survey) on this turn.

**The frugivory network.** Round 1 said "there are no recorded source-linked rows for seed
movement itself". Round 2:

> **c9/t1** — "there are 150 recorded tree-animal pairs across 5,622 rows from the focal-tree
> frugivore visitation study, the seed-fate study, and the seed-predation experiment; the most
> recorded pair is Yellow-browed Bulbul with *Persea macrantha* at 629 records […] These are
> records of being seen together, not proof that seed was actually moved, and the ranking also
> reflects where observers spent more effort"

That is the register the product was aiming for: the number, the named pair, and the honest limit
in one breath, unprompted.

**Dead ends.** 17% → 98%. This was the cheapest fix in the list and it moved the most turns.

**Named places.** `place_names` passes 3/3. Round 1's "10.340–10.350 N, 76.890–76.900 E" is now
"Puduthottam, Sirikundra, Thenmalai, Murugaali-BlackBridge" — a list an ecologist can walk.

---

## 1. [bridge] "This route does not expose X" is told to the user as a fact about their data

**Impact: highest remaining. It is round 1's finding 1 wearing new clothes.**

The name-resolution failure was *"your word does not exist here"*. The replacement is
*"this site's data is not structured to answer that"* — said about the summary, not the survey,
and the user cannot tell the difference. Six turns, verbatim:

> **c3/t5** — *"How many of the plant community plots could I revisit, and where are they?"*
> "This site does not have compatible site-and-effort structure for the plant community structure
> survey, so I cannot give a defensible count of revisit-ready plots or map their locations"

> **c2/t5** — "This route failed because the survey summary here does not expose a species-level
> split that keeps site, plot type and visit effort aligned"

> **c5/t4** — "its threat-status field is there, but this site does not have the matching
> site-level survey structure needed to summarise it here"

> **c1/t6** — "the summary check failed because this source does not keep site, effort and
> category fields in a way that supports a row-level year split"

> **c6/t5** — "the comparison table on this map did not expose a recorded mark called "benchmark""

**c3/t5 is a straight regression.** Round 1 answered that same question with "132 plant community
plot sites are mapped, with 264 explicit visits". Round 2 refuses. The round-1 answer was
attributed to the wrong survey (finding 8) — that has been fixed by *withdrawing the number*
rather than by attributing it correctly. The user is worse off on that turn than they were before.

**Fix:** these are properties of a summary shape, not of the landscape. Say so — "I can see the
plots but this particular summary will not give me a per-year row; here is the count and the map
instead" — and fall back to the capability that does hold it. Never let a route's shape be
reported as the data's poverty.

## 2. [bridge] `visual-explain` silently answers about "the largest point" nobody asked about

**Impact: high. Round 1's finding 5 (unit substitution) survives inside a different capability.**

Five turns took this route, and each one quietly changed the subject:

> **c6/t3** — *"Tell me more about that one. What is the stem density there, and what does the
> canopy look like?"*
> "the explanation I pulled is for the largest point on that map because no specific plot was
> identified from a click or location. That point has a rainforest bird detection share of 1.0 in
> one acoustic survey row on 12 December 2020"

The user asked about stem density and canopy in a vegetation plot; they were given a bird acoustic
reading from one December day. Also `c2/t4` ("defaults to the largest category because no one
category was selected"), `c6/t5`, `c7/t2`, `c10/t2`.

To its credit it always *says* it is doing this, which is why these still pass `traceable` and
`dead_end`. But "no specific plot was identified from a click" is untrue: the plot was identified
in the previous turn, in words. The thread carries the referent (`multi_turn` is 57/57) — the
explain route just does not consume it.

**Fix:** pass the entity established in the conversation into `visual-explain` instead of
defaulting to the largest mark. When there is genuinely no referent, ask, rather than answering
about a different thing.

## 3. [bridge] Breakdowns are still refused where the category is declared

**Impact: high, and unchanged from round 1's finding 4.** `c2/t3` was my round-1 example and it
fails again for the same reason:

> **c2/t3** — "I can confirm the three bird-survey plot types are Restored, Unrestored and
> Benchmark. But this result does not expose the per-type plot counts or the per-type visit counts
> in a way I can quote honestly; it only shows the overall survey total of 69 sites and 460 visits"

It now knows the three category *names* and still cannot count them.
`stratified-survey-summary` on `dryad-rjdfn2zc3-restoration-birds` declares `Site_type`; it was
never called with it. Same shape in `c2/t5` (species-level split) and `c5/t4` (threat status).

**Fix:** when a summary returns a total and the user asked for the split, re-call the same
capability with the declared `category_property` before writing. This was fix 4 in round 1 and is
the single most repeated remaining failure.

## 4. [bridge] `rows` is the weakest dimension left, at 65%

Eight failures. The user asks for a list and gets prose about why a list is hard. `c9/t7`
("what would my team have to record next season") and `c3/t4` ("what would I have to go and
measure") both answer in paragraphs where a numbered field protocol is the deliverable — and
round 1 proved the system can write one, because round-1 `c3/t6` produced an excellent numbered
field-data request.

**Fix:** when the user asks what to record, collect or bring back, answer in a numbered list.

## 5. [ui] + [bridge] The failure panel and "target cells" — the last jargon

One jargon failure in 66 turns, and it is on the forbidden list verbatim:

> **c4/t6** — "802 mapped records with 436 in the target cells"

"target cells" was named explicitly as banned. The round-1 "site pack capability not
parameterised" panel did not recur in this run, but it was never fixed — it is triggered by
Algebra failures, which happened not to fire here. Both remain worth closing.

## 6. [bridge] The prose got denser, and the register slipped

**Impact: medium. This is the cost of the fix and it should be watched.**

Mean language score fell 1.58 → 1.31. Sentences went from 24.7 to 29.6 words, answers from 111 to
125 words. The numbers, sources and caveats that now (rightly) appear are being stacked into
single sentences:

> **c4/t6** — "My confidence is moderate for Vateria indica, because this site has 802 mapped
> records with 436 in the target cells across the restoration, bird recovery, threatened-tree,
> tree and habitat structure, and plant community surveys"

Five surveys, two counts and a confidence judgement in one sentence. Everything in it is true and
useful; it is just not how a field ecologist would say it.

**Fix:** cap sentence length in the answer guidance. The content is right — it needs breaking into
shorter sentences, which is a prompt instruction, not a capability change.

---

## What round 2 proves

The two new conversations were written to push into the territory the fixes unlocked, and they
land differently:

- **c9 (seed dispersal, 57%)** produces genuinely expert answers and then runs out of road on the
  specific sub-questions — which trees have *no* disperser, which dispersers are in the degraded
  fragments. Its best turn is a model of the register: asked how much of the pair list is really
  dispersal, it said *"all of that planting list rests on the weaker reading […] this table does
  not demonstrate dispersal, and it also folds in watching effort"* — the honest limit, unhedged,
  with a next move. It also correctly reported the watching effort skew I verified independently
  (3,144 rows on *Persea macrantha* against 805 on *Heynea trijuga*, 31 visitor species against 22).
- **c10 (budget plan, 71%)** is the strongest evidence the product now has real value: a three-year
  plan naming Puduthottam, Sirikundra, Thenmalai and Murugaali-BlackBridge, grounded in "903
  records across 98 different subjects, but only 4 rows of documented survey work", and "302
  squares with records against effort documented in only 42".

The remaining failures are no longer about trust — nothing was invented across 118 turns in two
rounds, and the system never re-asks for something it was already told. They are about **finishing
the job**: producing the split, the list, or the row once it has correctly found the data.

## Suggested order of work

1. Stop reporting a route's shape as the data's poverty (fix 1) — it is the largest remaining
   class and it re-creates the round-1 trust problem in new words.
2. Re-call with the declared category when a breakdown is asked for (fix 3) — repeated in three
   conversations, and already written down as round-1 fix 4.
3. Feed the conversation's established entity into `visual-explain` (fix 2).
4. Answer "what should I record" in a numbered list (fix 4).
5. Cap sentence length (fix 6), and close out "target cells" and the failure panel (fix 5).
