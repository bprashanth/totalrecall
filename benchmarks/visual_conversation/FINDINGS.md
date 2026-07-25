# Visual conversation bench - findings

A Meena-style turn-by-turn bench: 7 conversations, 30 turns, plain Indian English, run against the
live livelihoods bridge at `http://172.17.0.1:7013/v1/chat/completions`. One conversation is one
session (`session_id` repeated on every POST; only the current user turn is sent, because the
bridge holds the resumable Codex thread, not the client).

```bash
cd benchmarks/visual_conversation
python3 bench.py --run-id <tag>                       # full run, 30 turns, ~9 min
python3 bench.py --only c4-estimate --run-id spot     # one conversation
python3 bench.py --grade-only runs/<tag>/transcript.json --run-id <tag>   # re-grade, no cost
```

Grading is deterministic (regex and counts, no judge model), so a rerun after a skill-text change
is directly comparable to the run before it. Per-run artefacts land in `runs/<run-id>/`. Both runs
below are graded by the same final grader.

## Two runs, before and after the plain-language skill rule

| | run1-908663a | run2-plainskill |
| --- | --- | --- |
| Turns passing every check | **1/30 (3%)** | **18/30 (60%)** |
| `jargon` | 13% | 73% |
| `numbers` (any figure in the answer) | 20% | 60% |
| `no_keyword_refusal` | 73% | 97% |
| `numbers_attributed` | 50% | 100% |
| `vocab` (user's own word comes back) | 80% | 100% |
| `honest_gap` / `offers_alternative` | 50% / 50% | 100% / 100% |
| `confidence_in_plain_words` | 100% | 50% |
| `visual_marker` | 100% | 100% |
| Median latency | 13.9 s | 18.0 s |

| Category | run1 | run2 |
| --- | --- | --- |
| orientation | 0% | 64% |
| graph_comprehension | 0% | 25% |
| vocabulary | 0% | 80% |
| drilldown | 0% | 67% |
| estimate | 0% | 25% |
| honest_limits | 25% | 75% |
| gk_usage | 0% | 75% |

The plain-language rule works, and it works on the axis it was aimed at. The stock opener changed
from *"From the onboarded site records, this visual shows..."* to *"This map shows the Valparai area
boundary and where the data this site holds is concentrated"*, and figures started appearing in
prose. What remains is mostly **retrieval**, not wording.

Run-2 caveat: the bridge was restarted mid-run by the concurrent skill-text work, so c1-c4 ran
against the first plain-language build and c5-c7 against the next one (`server.py` c2bdc69c9fab,
the tree that became commit eeb9cf6, "Read the user's own words onto what the index actually
holds"). Turn counts and grading are unaffected. Run 1 is commit 908663a.

## Top 5 recommendations, ranked by impact

### 1. Forward `actions` into the model-safe result summary, so a menu can be offered

`result_service` already returns the real option list in an action (`choose-metric` with
`available_metrics`, `dss/visual_index/result_service.py:2576`), but `_visual_result_summary`
(`server.py:1162`) does not forward `actions` to the dialogue model - `_visual_upload_summary`
(`server.py:1491`) does. The model cannot see the menu it is being asked to offer, so it either
refuses or invents one. Run 1:

> I could not plot the trend yet because the indexed metric does not recognise `mnrega works` as a
> registered measure here. [...] Which one do you want: number of works, sanctioned amount,
> expenditure, or persondays?

Those four options are invented; the site's measurement registry holds `daily_wage`,
`overtime_rate` and `paid_days_per_month`. Run 2 is politer but still the same dead end - the only
surviving `no_keyword_refusal` failure in the whole run:

> I could not pull a year-wise trend yet because this site does not recognise "MGNREGA works" as a
> named time-series. [...] Do you mean number of works, or persondays, meaning days of paid work?

Fix the passthrough, then add the skill rule: **options offered to the user must come from the
returned action arguments; never compose a plausible list.** And never say *recognise, registered,
registry, named time-series* to a person - say what is there: "For wages I have the daily rate,
overtime rate and paid days per month. Which of these?"

### 2. Stop answering "how many / which is most / show rows" from the orientation map

12 of 30 turns in run 2 still contain no figure, and they are the turns that most needed one:
which village was visited least, which occupation is leaving most, how many public works, what
are tea wages here.

> This map only shows where livelihood records exist across the area; it does not split people
> leaving by occupation. So, from this view, I cannot say which occupation is leaving most.

> This map can show where documented survey work is lowest, but not name the least-visited village
> from this view alone.

The data is right there: 48 effort rows carrying `village` and `village_population` (Thonimalai,
Perumpallam, Kadamparai), 164 georeferenced events including the MGNREGA-style public works source,
out-migration events by occupation, and `daily_wage` in INR/day across 2017-2024. So are the
capabilities: `coverage-versus-effort`, `stratified-survey-summary`, `entity-record-map`,
`group-record-map`, `metric-time-series`. The model reaches for `site-orientation` first and treats
its limitations as the answer's limitations.

Skill rule: a "how many / which is most / show rows" question is **never** answered from the
orientation map. Route counts of things that happened to the event and effort capabilities;
route measured quantities to the metric series. If the first capability comes back unresolved, try
the other route **before** writing anything to the user - one silent retry, then speak.

### 3. Name the two stock phrases that survived the plain-language rule

Eight run-2 turns still trip the jargon scan, and almost all of it is two phrases plus two words:
`onboarded` (6), `site records` (6), `indexed` (2), `this visual` (1). "From the onboarded site
records," is still the default opener on turns where the model is being careful.

Skill rule: name them explicitly with their replacements - *onboarded site records* -> "the data I
have for this place"; *indexed* -> "recorded"; *this visual* -> "this map" / "this chart";
*grid squares* is good and should stay. A banned list works better than a principle here, because
the model already believes it is writing plainly.

### 4. The estimate conversation now clarifies forever and never estimates

This is the one place where run 2 is worse than run 1. Run 1 produced an estimate on turn 2, with
machine wrapping. Run 2 spent all four turns asking:

> t1: To estimate jobs for that empty square, I need the exact square reference from the map.
> Please send the map click as `at:<lat>:<lon>` for that Kadamparai square [...]
>
> t2 (after the user supplied 10.255, 76.965): I can estimate it, but "jobs" has two different
> meanings in this site's data: public-works workdays, or estate payroll jobs. Which one do you
> want for `10.255, 76.965`?
>
> t3 (asked how much to trust the number): I have not given a number yet, so I cannot honestly
> rate its trust level.

Each question is individually reasonable and the estimate-semantics work is visible in it, but the
user asked once and never got a number. Two rules would fix it: (a) resolve a named place plus a
direction yourself - Kadamparai Village is in the site at 10.261, 76.966 - and never ask a person
to type `at:<lat>:<lon>`; (b) **one clarifying question per conversation, not per turn**: after
that, pick the more likely reading, say which one you picked in plain words, run it, and offer the
other as a follow-up.

### 5. Keep the general-knowledge wall standing on comparison turns

Number attribution is now perfect (100%), and the opening general-knowledge turn is the best turn
in the bench. But the comparison turn dropped its label:

> Low, from a general India tea-worker point of view. From the onboarded site records, we still
> cannot compare properly because this site does not show tea wage data [...]

"from a general India tea-worker point of view" is doing the work of a label, but a reader skimming
sees "Low" as the finding. Skill rule: on a comparison turn, the general half and the data half get
one sentence each, each labelled - and if the data half is empty, say so first, before the verdict.
Also note this turn only happened because the wage retrieval failed (see recommendation 2); the
site holds the wage series it says it cannot see.

## What is already working, and should not regress

- The `<!-- idli-result:... -->` marker is present on every turn that warrants a visual (30/30, both
  runs). The transport side is healthy.
- The user's own vocabulary comes back in run 2 on every turn that was checked for it (100%),
  including "mnrega", "job work" and "tea plucker".
- Honest gaps now offer alternatives every time (100%), and the non-match-is-not-absence framing is
  genuinely good: *"From the data this site holds, it looks like a true gap, not just a naming
  mismatch. I checked the full site records and the estimate catalogue..."*
- Brevity holds when asked for; the three-point team-meeting summary was three points.
- Latency is not a problem: median 18 s per turn.

## Re-running

`python3 bench.py --run-id run3-<tag>`, then diff the `check_pass_rate` block against
`runs/run2-plainskill/graded.json`. Watch `numbers`, `jargon` and `estimate` first; they carry most
of the remaining signal.
