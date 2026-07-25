# Ecology ANR bench - results

Run: `round2`  |  endpoint: `http://172.17.0.1:7012`  |  model: `idli-insight-valparai`  |  started: 2026-07-26T02:11:04+05:30

**46/66 turns pass (70%)**, 1/10 conversations clean, mean language score 1.31/2, median latency 20.7s (max 72.4s), 0 turns retried.

## How this number was baselined

- ROUTING EXPECTATIONS RE-BASELINED after the bridge shipped `interaction-pairs` and `survey-priority-squares` (commit 1a57eb9). The rule applied: widen an existing `capabilities_any` list only where the newly-chosen tool genuinely answers the question better; never narrow one, and never add a routing requirement to a turn that did not already have one. Where the model simply picked a worse tool, the turn was left failing.
- WIDENED (5 turns, routing is genuinely right): c5/t2 and c5/t3 now accept `interaction-pairs` -- it names the recorded tree-animal pairs, which is exactly what 'who disperses what' asks for, where `interaction-map` only maps declared association types. c5/t4 now accepts `entity-activity-profile` and `interaction-pairs` -- it answered with Heynea trijuga, 237 records in 45 squares, 2002-2022, tied to the threatened-tree records. c7/t1 and c7/t6 now accept `survey-priority-squares` -- it ranks by the records-versus-effort gap and names squares by real places, which is the question.
- LEFT FAILING (5 turns, the tool picked was worse): c1/t6 ran `stratified-survey-summary` for 'show me the rows behind the mammal counts', could not produce a row, and offered the mapped-records route in its own next sentence -- a tool that could answer was available and not used. c2/t3 and c2/t5 never called `stratified-survey-summary` with the declared `Site_type` category that holds the split being asked for. c3/t3 ran `method-catalog` for a question about canopy cover and plant-community plots. c4/t5 ran `entity-activity-profile` and then asserted there was no canopy comparison, without querying the ten canopy and structure metrics this index holds (`canopy_cover`, `canopy_openness`, `basal_area`, `tree_height` among them).
- Re-grading the bridge's own round5 transcript under these corrected expectations moves it from 27/52 to 31/52 and `right_tool` from 58% to 79%. That is the size of the harness drift, isolated from any product change.
- GRADER CALIBRATED TWICE, both times against transcripts rather than intuition. Round 1: `honest_gap` and `confidence` were widened after reading the failures showed 'there is still no recorded lantana name here' and 'I cannot call that a real plot-type effect yet' were being missed. Round 2: `join_rule_disclosed` was widened (a join is also disclosed by saying what the table actually records and how unequal the watching behind it was), and the gap checks were made conditional -- where the product now finds the data and answers with a figure, answering is better than confessing, so `honest_gap` passes on evidence and `names_alternative` binds only when absence was actually claimed. Uncorrected, round 2 scores 37/66; corrected, 46/66. Both numbers are stated here on purpose.

## Pass rate by dimension

| Check | Pass rate | n |
| --- | --- | --- |
| `rows` | 65% | 23 |
| `right_tool` | 83% | 29 |
| `has_evidence` | 85% | 34 |
| `traceable` | 91% | 33 |
| `confidence` | 94% | 18 |
| `dead_end` | 98% | 66 |
| `jargon` | 98% | 66 |
| `next_step_in_prose` | 98% | 66 |
| `brevity` | 100% | 1 |
| `gap_or_answer` | 100% | 5 |
| `general_knowledge_labelled` | 100% | 2 |
| `honest_gap` | 100% | 7 |
| `join_rule_disclosed` | 100% | 6 |
| `multi_turn` | 100% | 57 |
| `names_alternative` | 100% | 4 |
| `no_invention` | 100% | 1 |
| `no_reask` | 100% | 57 |
| `no_transport_leak` | 100% | 66 |
| `not_catch_all` | 100% | 25 |
| `place_names` | 100% | 3 |
| `questions` | 100% | 35 |
| `responded` | 100% | 66 |
| `visual_present` | 100% | 10 |

## Pass rate by conversation

| Conversation | Turn pass rate |
| --- | --- |
| c1-what-is-here - What is even here, and what can I trust for a trend | 67% |
| c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots | 57% |
| c3-lantana - Lantana keeps coming back: an honest gap and how to test it | 50% |
| c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule | 83% |
| c5-what-to-replant - What to replant for a forest that keeps itself going | 57% |
| c6-what-grows-where - What is growing where: plots on a map, then one plot in detail | 67% |
| c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots | 100% |
| c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here | 86% |
| c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs | 57% |
| c10-budget-monitoring-plan - Three years of monitoring against a real budget | 71% |

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| comparison | 57% |
| coverage-gap | 86% |
| data-request | 86% |
| denominators | 57% |
| design | 68% |
| drill-down | 67% |
| gap-honesty | 69% |
| mechanism | 83% |
| method-disclosure | 69% |
| network | 57% |
| orientation | 67% |
| place | 67% |
| relationship | 83% |
| seed-fate | 57% |
| study-design | 50% |
| traceability | 61% |
| trust | 62% |
| uncertainty | 100% |
| value-of-information | 86% |

## c1-what-is-here - What is even here, and what can I trust for a trend

Session: `ecoanr-round2-c1-what-is-here`  |  categories: orientation, trust, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have just taken over restoration monitoring for the Anamalai rainforest fragments. Before I plan anything I need to know what long-term monitoring actually exists here, and how far back it goes. | PASS | - | site-orientation, coverage-versus-effort | 1.0 | 33 | From the data this site has, long-term monitoring is not site-wide: across the restoration bird, shade-bird, frugivory, threatened-tree, herpetofauna, seed-pred... |
| t2 | Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot? | PASS | - | metric-time-series | 1.0 | 17 | From the data this site has, the trend route does not recognise “those surveys” as a single thing, so this came back as a naming gap, not evidence of absence. W... |
| t3 | Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking. | PASS | - | metric-time-series, stratified-survey-summary | 1.25 | 32 | From the data this site has, the restoration bird survey records 460 explicit visits across 449 surveyed sites, but this map and table do not split that effort ... |
| t4 | So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why? | **FAIL** | `traceable` | method-catalog | 1.0 | 29 | From the data this site has, I would stand behind change claims most for repeated plot-based forest structure measures such as aboveground carbon, basal area, c... |
| t5 | Where is the weakest link in that? Where would a reviewer poke holes? | PASS | - | visual-explain | 1.4 | 22 | From the data this site has, the weakest link is this: there is no ready, fitted effort-adjusted trend analysis yet, only a documented analysis design in the si... |
| t6 | Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like. | **FAIL** | `has_evidence` | group-record-map, local-site-evidence-search, discover-ecology-evidence, stratified-survey-summary | 0.85 | 72 | From the data this site has, this route does not expose a one-year row view for that mammal-count source: the summary check failed because this source does not ... |

### c1-what-is-here / t4

User: So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why?

- `traceable`: no survey named and no path to the rows

```
From the data this site has, I would stand behind change claims most for repeated plot-based forest structure measures such as aboveground carbon, basal area, canopy cover and adult tree counts, not raw bird or other detection totals. This table shows there is 1 documented way to adjust reporting rates for uneven looking effort, but 0 are yet specified as ready without extra implementation review, so I would not stand behind a simple “more birds in 2024 than 2015” claim from detections alone. If you want, I can pull one concrete plot-based trend and tell you whether that 2015 to 2024 claim is defensible.
```

### c1-what-is-here / t6

User: Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like.

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, this route does not expose a one-year row view for that mammal-count source: the summary check failed because this source does not keep site, effort and category fields in a way that supports a row-level year split here. So I cannot honestly show you a single mammal-count row from one year from this site view; that missing row access is itself a weak point for audit and review. If you want, I can pull one mammal record from the mapped Mammalia inventory instead, so you can at least see what a single source-linked occurrence row looks like.
```

## c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots

Session: `ecoanr-round2-c2-does-restoration-work`  |  categories: comparison, denominators, trust

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | We have been doing assisted natural regeneration in these fragments for years. Is there anything here that compares restored plots against ones we left to regrow on their own? | PASS | - | stratified-survey-summary | 1.5 | 25 | From the data this site has, yes: the restoration bird survey maps 69 surveyed sites across 3 site types, with 460 visits, and includes a category-wise comparis... |
| t2 | Good. How do the birds compare across restored, naturally regenerating and benchmark plots? | PASS | - | matrix-profile, compile-scientific-algebra-9b | 1.35 | 45 | From the data this site has, the bird recovery survey covers 69 sites and 460 visits across 3 plot types, including restored, naturally regenerating and benchma... |
| t3 | How many plots in each of those three, and how many times was each visited? | **FAIL** | `right_tool` | visual-explain | 1.5 | 34 | From the data this site has, I can confirm the three bird-survey plot types are Restored, Unrestored and Benchmark. But this result does not expose the per-type... |
| t4 | Is that difference real, or could it just be that people spent more time in the benchmark plots? | **FAIL** | `has_evidence` | visual-explain | 1.4 | 18 | From the data this site has, I cannot call that difference real. The stored explanation here defaults to the largest category because no one category was select... |
| t5 | Which bird species are driving the gap? I care about the rainforest specialists, not the generalists. | **FAIL** | `rows` | stratified-survey-summary | 1.35 | 18 | From the data this site has, I cannot identify which species are driving the gap from this bird recovery survey output. This route failed because the survey sum... |
| t6 | If I had to put one sentence in a report about whether restoration is working here, what would you let me say? | PASS | - | method-catalog | 1.35 | 14 | This site does not have an admitted claim card for this bird comparison, so I would not let you write that restoration is working here from the current bird res... |
| t7 | And what would you not let me say? | PASS | - | method-catalog | 1.5 | 12 | This site does not have a fitted restoration-effect result for this bird question. I would not let you say restoration caused higher rainforest bird richness, t... |

### c2-does-restoration-work / t3

User: How many plots in each of those three, and how many times was each visited?

- `right_tool`: ran ['visual-explain'], wanted one of ['coverage-versus-effort', 'matrix-profile', 'plot-indicator-profile', 'stratified-survey-summary']

```
From the data this site has, I can confirm the three bird-survey plot types are Restored, Unrestored and Benchmark. But this result does not expose the per-type plot counts or the per-type visit counts in a way I can quote honestly; it only shows the overall survey total of 69 sites and 460 visits, and the table here stays descriptive. If you want, I can check whether the bird survey rows themselves are available anywhere in the data this site has, so we can count plots and visits by type directly.
```

### c2-does-restoration-work / t4

User: Is that difference real, or could it just be that people spent more time in the benchmark plots?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, I cannot call that difference real. The stored explanation here defaults to the largest category because no one category was selected, and its own warning is clear: this comparison is effort-visible and descriptive, not a treatment effect, and the bird records are detections per visit, not population counts. If you want, I can check whether the vegetation surveys here give a cleaner restored-versus-unrestored comparison with less risk of effort bias.
```

### c2-does-restoration-work / t5

User: Which bird species are driving the gap? I care about the rainforest specialists, not the generalists.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, I cannot identify which species are driving the gap from this bird recovery survey output. This route failed because the survey summary here does not expose a species-level split that keeps site, plot type and visit effort aligned, so I cannot separate rainforest specialists from generalists honestly. If you want, I can check one named rainforest bird at a time in the records and see where each was recorded.
```

## c3-lantana - Lantana keeps coming back: an honest gap and how to test it

Session: `ecoanr-round2-c3-lantana`  |  categories: gap-honesty, study-design, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Why does lantana keep coming back after we weed it? | PASS | - | entity-record-map | 1.0 | 25 | I read “lantana” as *Lantana camara*, which this site has 36 records of; this map shows where those records are available, with 17 in squares inside the site bo... |
| t2 | Do you have anything at all on lantana at this site? Even just where it has been recorded? | PASS | - | local-site-evidence-search, entity-record-map | 2.0 | 13 | I read “lantana” as *Lantana camara*, which this site has 36 records of. This map shows where those records are available, and 17 of them fall in squares inside... |
| t3 | So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots. | **FAIL** | `right_tool` | entity-activity-profile | 1.5 | 19 | From the data this site has, the stronger stand-in is the plant community structure survey, because lantana is recorded there and also in regeneration inventory... |
| t4 | If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here? | **FAIL** | `rows` | method-catalog | 0.85 | 25 | From the data this site has, there is 1 source-linked canopy-response method note, but it is only a design note, not a fitted result, so this site does not yet ... |
| t5 | How many of the plant community plots could I revisit, and where are they? | **FAIL** | `has_evidence` | stratified-survey-summary | 1.5 | 26 | This site does not have compatible site-and-effort structure for the plant community structure survey, so I cannot give a defensible count of revisit-ready plot... |
| t6 | Draft the data request for me: exactly what I would ask my field team to bring back. | PASS | - | - | 1.85 | 12 | From the data this site has, ask for a revisit-based plot sheet, not just a fresh species list. The key gap is this site does not have repeat lantana measuremen... |

### c3-lantana / t3

User: So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots.

- `right_tool`: ran ['entity-activity-profile'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'plot-indicator-profile']

```
From the data this site has, the stronger stand-in is the plant community structure survey, because lantana is recorded there and also in regeneration inventory and woody regeneration measurement across 36 records in 15 squares from 2003 to 2022. I would not treat canopy cover alone as enough from this site yet; this table shows record types and surveys, but these are records of presence, not abundance, so more records can also mean more survey work. From general knowledge: canopy cover can help as one pressure variable, but lantana return usually tracks disturbance, light, repeated cutting and nearby seed sources better than canopy cover alone. If you want, I can map where lantana shares squares with *Clerodendrum infortunatum*, *Maesa indica*, or Nilgiri langur.
```

### c3-lantana / t4

User: If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, there is 1 source-linked canopy-response method note, but it is only a design note, not a fitted result, so this site does not yet have a ready answer to “does shade suppress lantana here?”. To test that, you would need repeated plot measurements of lantana itself under different shade levels: at minimum lantana presence or cover in the same plots over time, canopy cover or canopy openness above them, and the main disturbance covariates like weeding history and recent cutting; the plant community plots are the better base because they are plot data, while canopy cover alone is too weak on its own. From general knowledge: for this question, repeated before-after or repeated seasonal measurements are much stronger than one-time snapshots, because lantana responds fast to fresh disturbance and light gaps. If you want, I can pull together a short field-measurement list for a plot-based lantana shade test using what this site already has.
```

### c3-lantana / t5

User: How many of the plant community plots could I revisit, and where are they?

- `has_evidence`: no figure on a how-much / which / where question

```
This site does not have compatible site-and-effort structure for the plant community structure survey, so I cannot give a defensible count of revisit-ready plots or map their locations from this route. The table is telling us a real gap in this site’s current summarised survey structure, not that the plots never existed. If you want, I can check the recorded sites behind the lantana-linked plant community survey another way and see whether any revisit locations can still be recovered.
```

## c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule

Session: `ecoanr-round2-c4-natives-suppress`  |  categories: relationship, method-disclosure, mechanism

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Different angle. Are there native species here that turn up where lantana does not? | PASS | - | entity-activity-profile, co-occurrence-map | 1.25 | 31 | From the data this site has, yes: native species are recorded in 104 squares, while lantana is recorded in 15, and all 15 lantana squares are shared with native... |
| t2 | How exactly did you match those two things up? Same plot and same year, or just the same general area? | PASS | - | visual-explain | 1.5 | 15 | It was matched at the 1.1 km square level, not by the same plot. The map counts a square as shared when both lantana and the Native group were recorded somewher... |
| t3 | That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with? | PASS | - | local-site-evidence-search, stratified-survey-summary | 1.5 | 56 | From the data this site has, the restoration survey does have a plot framework: 132 surveyed sites or plots with 264 visits. But this site does not have a ready... |
| t4 | What is the mechanism you would bet on here - shade, leaf litter, root competition? | PASS | - | - | 1.5 | 14 | From the data this site has, I would not bet hard on any one mechanism yet. The records we used are presence records and shared plots or squares; they do not di... |
| t5 | Is there anything in the canopy or tree structure data that supports the shade story? | PASS | - | plot-indicator-profile, compile-scientific-algebra-9b | 1.5 | 28 | From the data this site has, not yet: the tree and habitat structure survey maps canopy cover for 901 plots, but this view only shows 1 `nativeAlien` category, ... |
| t6 | Give me three native species to trial as a shade crop, and say how confident you are in each one. | **FAIL** | `jargon`, `rows` | entity-activity-profile, entity-record-map | 0.85 | 31 | From the data this site has, my three trial picks would be Vateria indica, Myristica beddomei, and Machilus glaucescens. My confidence is moderate for Vateria i... |

### c4-natives-suppress / t6

User: Give me three native species to trial as a shade crop, and say how confident you are in each one.

- `jargon`: target cells
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, my three trial picks would be Vateria indica, Myristica beddomei, and Machilus glaucescens. My confidence is moderate for Vateria indica, because this site has 802 mapped records with 436 in the target cells across the restoration, bird recovery, threatened-tree, tree and habitat structure, and plant community surveys; moderate for Myristica beddomei, because it has 609 mapped records with 258 in the target cells across the restoration, frugivory, threatened-tree, tree and habitat structure, and plant community surveys; and low to moderate for Machilus glaucescens, because it has fewer records here, 182 mapped with 53 in the target cells, from the restoration, frugivory, and threatened-tree surveys. From general knowledge: these are all forest trees, so they are more plausible shade candidates than a random native, but these record maps still show where they were recorded, not whether they perform well as planted shade trees. If you want, I can compare these three against documented survey effort before you choose one for field trials.
```

## c5-what-to-replant - What to replant for a forest that keeps itself going

Session: `ecoanr-round2-c5-what-to-replant`  |  categories: design, network, seed-fate

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am putting together a planting list for a two hectare gap. I want a forest that regenerates on its own in thirty years, not a plantation. Where do I start? | PASS | - | site-orientation | 1.0 | 21 | From the data this site has, you can start here: 42,348 source-linked records covering 962 recorded plants and animals across 302 map squares, so this map is us... |
| t2 | Which trees here actually get their seed moved by animals, and by which animals? | PASS | - | interaction-pairs | 1.5 | 14 | From the data this site has, the focal-tree frugivore and seed-fate studies recorded 150 tree-animal pairs across 5,622 rows; the most recorded pair is Yellow-b... |
| t3 | Of those, which lose most of their seed to predators? I do not want to plant something that never recruits. | **FAIL** | `has_evidence` | interaction-pairs | 2.0 | 21 | From the data this site has, there is no recorded seed-predation pair matching that request, so I cannot rank these trees by seed loss here. This is a naming or... |
| t4 | Are any threatened species in that list worth including? | **FAIL** | `right_tool`, `rows` | stratified-survey-summary | 1.25 | 23 | From the data this site has, I cannot answer that cleanly from the restoration tree study: its threat-status field is there, but this site does not have the mat... |
| t5 | Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge. | PASS | - | local-site-evidence-search, interaction-pairs | 1.0 | 27 | From the data this site has, the strict site-backed core is *Persea macrantha* and *Heynea trijuga*: the focal-tree frugivore and seed-fate studies recorded 150... |
| t6 | Which of those would fail if the hornbills do not come back? | **FAIL** | `traceable` | interaction-pairs | 1.0 | 18 | From the data this site has, I cannot single out any of your shortlist as hornbill-dependent: the recorded pair table still shows the same 150 named pairs acros... |
| t7 | What should I plant first to bring the hornbills in? | PASS | - | interaction-pairs | 1.0 | 18 | From the data this site has, there is still no clear hornbill-led tree shortlist: the recorded pairs are dominated instead by *Persea macrantha* and *Heynea tri... |

### c5-what-to-replant / t3

User: Of those, which lose most of their seed to predators? I do not want to plant something that never recruits.

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, there is no recorded seed-predation pair matching that request, so I cannot rank these trees by seed loss here. This is a naming or coverage gap in the seed-predation records, not evidence that the trees escape predators or fail to recruit. Would you like me to check one tree first, starting with *Persea macrantha* or *Heynea trijuga*?
```

### c5-what-to-replant / t4

User: Are any threatened species in that list worth including?

- `right_tool`: ran ['stratified-survey-summary'], wanted one of ['entity-activity-profile', 'entity-record-map', 'group-record-map', 'interaction-pairs', 'matrix-profile', 'plot-indicator-profile']
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, I cannot answer that cleanly from the restoration tree study: its threat-status field is there, but this site does not have the matching site-level survey structure needed to summarise it here. From general knowledge: a threatened tree can be worth including only if it is local to this forest type and shows some sign of recruitment or reliable animal visitation; threat status alone is not enough for a planting list. Would you like me to map where *Persea macrantha* is recorded?
```

### c5-what-to-replant / t6

User: Which of those would fail if the hornbills do not come back?

- `traceable`: no survey named and no path to the rows

```
From the data this site has, I cannot single out any of your shortlist as hornbill-dependent: the recorded pair table still shows the same 150 named pairs across 5,622 rows, led by bulbuls, barbets and Southern Hill Myna on *Persea macrantha* and *Heynea trijuga*, not a clear hornbill-linked subset. So, on current site evidence, *Persea macrantha* and *Heynea trijuga* do not look as if they fail only when hornbills are absent; but these are records of animals seen at trees, not proof of seed movement or successful recruitment. Would you like me to map where *Heynea trijuga* is recorded?
```

## c6-what-grows-where - What is growing where: plots on a map, then one plot in detail

Session: `ecoanr-round2-c6-what-grows-where`  |  categories: place, drill-down, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Show me what is growing where across the fragments. I want to see the plots on a map. | PASS | - | site-orientation | 1.9 | 19 | From the data this site has, this map shows 42,348 source-linked records covering 962 recorded kinds of plants and animals across 302 squares inside the site bo... |
| t2 | Which plot has the highest share of rainforest species? | PASS | - | plot-indicator-profile | 1.5 | 27 | From the data this site has, I read your question as the share of rainforest bird detections, and this map shows that measure for 257 plots from the acoustic bi... |
| t3 | Tell me more about that one. What is the stem density there, and what does the canopy look like? | **FAIL** | `right_tool` | visual-explain | 1.5 | 29 | From the data this site has, the explanation I pulled is for the largest point on that map because no specific plot was identified from a click or location. Tha... |
| t4 | Where does that number come from? Show me the rows. | PASS | - | visual-explain | 1.5 | 16 | From the data this site has, that 1.0 value comes from one row only in the passive acoustic restoration monitoring data. The row is dated 12 December 2020, and ... |
| t5 | How does it compare against the benchmark plots? | **FAIL** | `right_tool` | visual-explain | 1.5 | 15 | From the data this site has, I cannot yet compare that point against benchmark plots from this stored view, because the comparison table on this map did not exp... |
| t6 | Is that plot an outlier, or is it typical of the restored ones? | PASS | - | visual-explain | 1.0 | 14 | From the data this site has, I cannot say yet whether that plot is an outlier or typical of restored plots, because this stored comparison does not expose the r... |

### c6-what-grows-where / t3

User: Tell me more about that one. What is the stem density there, and what does the canopy look like?

- `right_tool`: ran ['visual-explain'], wanted one of ['cell-feature-map', 'group-record-map', 'matrix-profile', 'metric-time-series', 'plot-indicator-profile']

```
From the data this site has, the explanation I pulled is for the largest point on that map because no specific plot was identified from a click or location. That point has a rainforest bird detection share of 1.0 in one acoustic survey row on 12 December 2020, but this readout does not yet tell me that plot’s stem density or canopy values. Would you like me to pull the exact plot you mean from the map first, so I can read its stem density and canopy measures correctly?
```

### c6-what-grows-where / t5

User: How does it compare against the benchmark plots?

- `right_tool`: ran ['visual-explain'], wanted one of ['group-record-map', 'matrix-profile', 'plot-indicator-profile', 'stratified-survey-summary']

```
From the data this site has, I cannot yet compare that point against benchmark plots from this stored view, because the comparison table on this map did not expose a recorded mark called “benchmark”. What I do have is the point value itself: one acoustic survey row on 12 December 2020 with a rainforest bird detection share of 1.0, and the benchmark side is still a data-access gap in this readout. If you want, I can pull the comparison classes that this table actually shows and match the top point against those.
```

## c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots

Session: `ecoanr-round2-c7-survey-budget`  |  categories: value-of-information, coverage-gap, uncertainty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Say I get twenty drone days next season. Where should I fly to learn the most? | PASS | - | survey-priority-squares | 1.4 | 21 | From the data this site has, 102 squares have records but only 22 have documented survey work, so this map ranks where 20 drone days should teach you the most; ... |
| t2 | What are you basing that on? Places we have never looked, or places where you think something is happening? | PASS | - | visual-explain | 1.3 | 15 | From the data this site has, this ranking is based on where records exist but the documented survey work behind them is thin, not on where the map thinks someth... |
| t3 | If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover. | PASS | - | group-record-map | 0.8 | 18 | From the data this site has, yes, the answer would likely change: for invasive cover, this map shows 1,815 records for 14 introduced kinds, with 1,154 records i... |
| t4 | And if it is just me and two field assistants for thirty days on foot? | PASS | - | coverage-versus-effort | 1.4 | 17 | From the data this site has, I would still bias the 30 walking days toward the thinly documented parts of the landscape: records occur in 302 squares, but expli... |
| t5 | Which of the three buys me the most for a restoration decision in the next two years? | PASS | - | compile-scientific-algebra-9b | 1.3 | 25 | From the data this site has, the hyperspectral option buys you the most for a restoration decision in the next two years, because it points at the problem you n... |
| t6 | Show me the gap map. Where is coverage thinnest relative to how much is going on there? | PASS | - | survey-priority-squares | 1.3 | 11 | From the data this site has, 102 squares hold records but only 22 have documented survey work, so this map shows where coverage is thinnest relative to recorded... |
| t7 | Rank the top five places, with a reason for each that I could put in a proposal. | PASS | - | survey-priority-squares | 1.8 | 15 | From the data this site has, the top five proposal priorities are: 1. Puduthottam, because it has 903 records but only 4 documented survey-work rows; 2. Sirikun... |

## c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here

Session: `ecoanr-round2-c8-monitoring-plan`  |  categories: design, data-request, gap-honesty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here. | PASS | - | site-orientation, coverage-versus-effort | 2.0 | 41 | **Three-year design** From the data this site has, use a paired comparison, not a loose before-after. Set up matched ANR and active planting plots on similar st... |
| t2 | What can I reuse as a baseline instead of starting from scratch? | PASS | - | coverage-versus-effort | 1.5 | 21 | From the data this site has, the safest baseline to reuse is the documented-effort part of the restoration trees, restoration birds, shade birds and related sur... |
| t3 | What is the minimum I have to keep collecting so the old data stays comparable? | PASS | - | method-catalog | 1.35 | 17 | From the data this site has, the minimum to keep collecting is the same core field package each round: plot identity, treatment identity, survey date and season... |
| t4 | What is missing entirely, that I would have to start measuring from zero? | PASS | - | method-catalog | 1.5 | 16 | This site does not have a ready repeated ANR-versus-planting comparison, so you would have to start measuring treatment identity, fixed plot re-visits, and repe... |
| t5 | How many plots, and how many visits a year, to have a real chance of detecting a difference? | **FAIL** | `has_evidence`, `confidence` | method-catalog | 1.85 | 30 | From the data this site has, there is no ready plot-power method here that answers “how many plots and visits” directly. So I should not invent a number yet; th... |
| t6 | Write it up as a one page plan I can hand to my team. | PASS | - | - | 1.85 | 20 | **Three-Year Monitoring Plan: ANR vs Active Planting** **Purpose** From the data this site has, we can build a fair comparison if we treat this as a matched, re... |
| t7 | And a list of the data I would need to request from the other groups working here. | PASS | - | site-orientation | 1.85 | 20 | **Data to request from other groups** From the data this site has, ask other groups for the pieces that make your ANR-versus-planting plots comparable, not just... |

### c8-monitoring-plan / t5

User: How many plots, and how many visits a year, to have a real chance of detecting a difference?

- `has_evidence`: no figure on a how-much / which / where question
- `confidence`: no plain statement of how far to trust it

```
From the data this site has, there is no ready plot-power method here that answers “how many plots and visits” directly. So I should not invent a number yet; the minimum missing choice is the main outcome to detect a difference on, because plot count for woody regeneration and plot count for canopy change will not be the same. This table came back empty for your exact filter, and only points to method notes rather than a finished sample-size result. So the data here can guide the design, but not give a safe number until we fix the response variable. Which main outcome should I size this for: woody regeneration success or canopy cover? If you want, I can then run one evidence-bound calculation for plots and visits per year.
```

## c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs

Session: `ecoanr-round2-c9-seed-dispersal-design`  |  categories: network, design, method-disclosure

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am designing the dispersal side of our planting. Who actually disperses what here? Give me the recorded tree and animal pairs, not the general story. | PASS | - | interaction-pairs | 1.0 | 20 | From the data this site has, there are 150 recorded tree-animal pairs across 5,622 rows from the focal-tree frugivore visitation study, the seed-fate study, and... |
| t2 | Which of the trees you just named have no recorded disperser at all? Those are the ones that worry me. | PASS | - | interaction-pairs | 1.0 | 24 | From the data this site has, none of the two trees just named drops to zero: *Persea macrantha* has 31 recorded animal pairs across 3,144 rows in the focal-tree... |
| t3 | How much of that is real absence, and how much is nobody having watched that tree? Tell me how the watching effort differs between trees. | PASS | - | interaction-pairs | 1.5 | 22 | From the data this site has, we cannot call any zero-pair tree a real absence from these pair tables alone, because the same studies mix behaviour with watching... |
| t4 | Of the dispersers on that list, which ones are actually recorded in the degraded fragments I would be restoring? | **FAIL** | `next_step_in_prose`, `dead_end`, `rows` | entity-activity-profile, stratified-survey-summary | 1.0 | 65 | From the data this site has, Southern Hill Myna, Malabar giant squirrel, and Malabar Grey Hornbill are recorded in the bird recovery survey that covers 69 surve... |
| t5 | So if I plant for the dispersers I already have, what does the planting list look like? | **FAIL** | `rows` | interaction-pairs | 1.25 | 28 | From the data this site has, if you plant for the dispersers already recorded in the restoration study area, the core list is *Heynea trijuga*, *Persea macranth... |
| t6 | Be straight with me. A bird recorded on a fruiting tree is not the same as that bird moving the seed. How much of this list rests on that assumption? | PASS | - | visual-explain | 1.0 | 24 | From the data this site has, all of that planting list rests on the weaker reading: the table is only “animal recorded at or on this tree”, ranked by how often ... |
| t7 | What would my team have to record next season to turn these pairs into real dispersal evidence? | **FAIL** | `rows` | method-catalog | 1.35 | 14 | This site does not have an admitted method card here for turning tree-visit pairs into a dispersal claim, so the missing piece is direct seed-fate evidence rath... |

### c9-seed-dispersal-design / t4

User: Of the dispersers on that list, which ones are actually recorded in the degraded fragments I would be restoring?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, Southern Hill Myna, Malabar giant squirrel, and Malabar Grey Hornbill are recorded in the bird recovery survey that covers 69 surveyed sites, 3 site categories, and 460 visits, so they do occur in the restoration study area. The remaining data gap is that these summaries do not yet give me a clean species-by-site-type split, so I cannot honestly say which of those three were in the degraded fragments specifically; and for Yellow-browed Bulbul, White-cheeked Barbet, Red-whiskered Bulbul, and Asian Fairy-bluebird, the name lookup in this view failed, which is a naming gap, not absence. When you say “degraded fragments”, do you want me to treat that as the naturally regenerating sites in the bird recovery study?
```

### c9-seed-dispersal-design / t5

User: So if I plant for the dispersers I already have, what does the planting list look like?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, if you plant for the dispersers already recorded in the restoration study area, the core list is *Heynea trijuga*, *Persea macrantha*, *Myristica dactyloides*, and *Canarium strictum* from the focal-tree frugivore study, seed-fate study, and seed-predation experiment. The strongest overlap is *Heynea trijuga* and *Persea macrantha*, both recorded with Southern Hill Myna, Malabar giant squirrel, and Malabar Grey Hornbill; *Myristica dactyloides* is recorded with the squirrel and hornbill, and *Canarium strictum* with the squirrel. These are recorded tree-animal pairs, not proof of seed movement, and the ranking also follows where trees were watched more. If you want, I can map where *Heynea trijuga* and *Persea macrantha* are recorded before you lock the planting mix.
```

### c9-seed-dispersal-design / t7

User: What would my team have to record next season to turn these pairs into real dispersal evidence?

- `rows`: no table, list or row language where the user asked for specifics

```
This site does not have an admitted method card here for turning tree-visit pairs into a dispersal claim, so the missing piece is direct seed-fate evidence rather than more pair counts. From general knowledge: to turn visits into real dispersal evidence, your team would need to record at least where seeds went after a visit, whether the animal removed or dropped them, and whether those seeds survived or germinated. If you want, I can turn that into a short next-season field protocol for your team.
```

## c10-budget-monitoring-plan - Three years of monitoring against a real budget

Session: `ecoanr-round2-c10-budget-monitoring-plan`  |  categories: value-of-information, design, coverage-gap

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have thirty field days and twenty drone days a year, for three years. Where do I start? Give me named places, not coordinates. | PASS | - | survey-priority-squares | 1.3 | 20 | From the data this site has, start with Puduthottam, Sirikundra, Thenmalai, Murugaali-BlackBridge and Puduthottam_Coffee; across the site, 102 squares have reco... |
| t2 | Why those places? Show me the gap between what has been recorded there and what has actually been surveyed. | PASS | - | coverage-versus-effort, visual-explain | 0.75 | 29 | For the earlier ranking, I asked for the audit trail without naming one place, so it explained the largest square on that map: it holds 903 records across 98 di... |
| t3 | Split the thirty field days across those places for year one. | PASS | - | compile-scientific-algebra-9b | 1.25 | 31 | From the data this site has, a practical year-one split is: Puduthottam 13 days, Puduthottam_Coffee 6 days, Murugaali-BlackBridge 5 days, Sirikundra 3 days, and... |
| t4 | What do the drone days add that the field days do not, given what this site already measures? | **FAIL** | `traceable` | local-site-evidence-search, method-catalog | 1.0 | 19 | From the data this site has, I cannot yet show a measured drone-versus-field gain: the table returns 9 source-linked method cards, but these are method notes, n... |
| t5 | What can I already get from the existing surveys, so that I am not paying to collect it twice? | PASS | - | method-catalog | 0.65 | 13 | From the data this site has, there are 9 source-linked method notes you can review before planning new work, but only 2 are specified without extra implementati... |
| t6 | If year one comes back and those gap squares are genuinely empty, what changes in year two? | PASS | - | survey-priority-squares | 0.8 | 25 | From the data this site has, if year one properly surveys the top gap places and they still come back empty, year two should stop spending on proving those same... |
| t7 | Write me the three year plan, year by year, and tell me what would make me abandon it. | **FAIL** | `rows` | survey-priority-squares | 0.65 | 18 | From the data this site has, a workable 3-year plan is: Year 1, clear the top five thinly documented places now on this map, starting with Puduthottam, Sirikund... |

### c10-budget-monitoring-plan / t4

User: What do the drone days add that the field days do not, given what this site already measures?

- `traceable`: no survey named and no path to the rows

```
From the data this site has, I cannot yet show a measured drone-versus-field gain: the table returns 9 source-linked method cards, but these are method notes, not worked results, and only 2 are specified without extra implementation review. The remaining data gap is that this site does not yet give a direct, quantified comparison of what one drone day adds over one field day. If you want, I can pull the method notes behind this and say which existing measurements are most likely to benefit from drone coverage.
```

### c10-budget-monitoring-plan / t7

User: Write me the three year plan, year by year, and tell me what would make me abandon it.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, a workable 3-year plan is: Year 1, clear the top five thinly documented places now on this map, starting with Puduthottam, Sirikundra, Thenmalai, Murugaali-BlackBridge and Puduthottam_Coffee; Year 2, move to the next ranked places if Year 1 effort is properly logged, especially Manamboli, Varatuparai, Selaliparai 2 and Pannimade; Year 3, only revisit Year 1 and Year 2 places that still have unresolved records, otherwise keep stepping down this ranking. I would abandon this plan if two things happen: first, your Year 1 and Year 2 work shows these priority gaps were mainly missing paperwork rather than missing field coverage; second, repeated, properly documented surveys keep returning empty in the top-ranked places, because then these are no longer the weakest information gaps and the plan should shift to the next named places instead. This map ranks where this site’s information is thinnest, not where biodiversity is richest, and documented effort is itself uneven, so the plan only holds if your new survey logs are complete and comparable. If you want, I can turn this into a one-page operational plan with field days and drone days split year by year.
```

