# Ecology ANR bench - results

Run: `round5-final`  |  endpoint: `http://172.17.0.1:7012`  |  model: `idli-insight-valparai`  |  started: 2026-07-26T01:55:35+05:30

**27/52 turns pass (52%)**, 0/8 conversations clean, mean language score 1.47/2, median latency 19.9s (max 104.0s), 0 turns retried.

## Pass rate by dimension

| Check | Pass rate | n |
| --- | --- | --- |
| `names_alternative` | 50% | 4 |
| `right_tool` | 58% | 24 |
| `gap_or_answer` | 67% | 3 |
| `honest_gap` | 67% | 6 |
| `join_rule_disclosed` | 67% | 3 |
| `rows` | 69% | 16 |
| `has_evidence` | 78% | 27 |
| `confidence` | 83% | 12 |
| `traceable` | 96% | 27 |
| `multi_turn` | 98% | 45 |
| `dead_end` | 98% | 52 |
| `next_step_in_prose` | 98% | 52 |
| `brevity` | 100% | 1 |
| `general_knowledge_labelled` | 100% | 2 |
| `jargon` | 100% | 52 |
| `no_invention` | 100% | 1 |
| `no_reask` | 100% | 45 |
| `no_transport_leak` | 100% | 52 |
| `not_catch_all` | 100% | 20 |
| `questions` | 100% | 26 |
| `responded` | 100% | 52 |
| `visual_present` | 100% | 8 |

## Pass rate by conversation

| Conversation | Turn pass rate |
| --- | --- |
| c1-what-is-here - What is even here, and what can I trust for a trend | 50% |
| c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots | 57% |
| c3-lantana - Lantana keeps coming back: an honest gap and how to test it | 50% |
| c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule | 50% |
| c5-what-to-replant - What to replant for a forest that keeps itself going | 43% |
| c6-what-grows-where - What is growing where: plots on a map, then one plot in detail | 83% |
| c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots | 29% |
| c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here | 57% |

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| comparison | 57% |
| coverage-gap | 29% |
| data-request | 57% |
| denominators | 57% |
| design | 50% |
| drill-down | 83% |
| gap-honesty | 54% |
| mechanism | 50% |
| method-disclosure | 50% |
| network | 43% |
| orientation | 50% |
| place | 83% |
| relationship | 50% |
| seed-fate | 43% |
| study-design | 50% |
| traceability | 61% |
| trust | 54% |
| uncertainty | 29% |
| value-of-information | 29% |

## c1-what-is-here - What is even here, and what can I trust for a trend

Session: `ecoanr-round5-final-c1-what-is-here`  |  categories: orientation, trust, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have just taken over restoration monitoring for the Anamalai rainforest fragments. Before I plan anything I need to know what long-term monitoring actually exists here, and how far back it goes. | PASS | - | site-orientation, coverage-versus-effort | 1.0 | 26 | From the data this site has, records are spread across 302 map squares, but documented survey effort exists in only 42 squares, so the strongest repeatable moni... |
| t2 | Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot? | **FAIL** | `traceable` | metric-time-series | 1.5 | 16 | From the data this site has, the trend chart would not answer a general question like “which of those”; it needs one measured quantity, so this is still a selec... |
| t3 | Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking. | **FAIL** | `has_evidence` | metric-time-series | 1.65 | 19 | From the data this site has, there is no site-wide year-by-year survey-effort measure ready to plot, so I cannot yet show whether later years had more sampling ... |
| t4 | So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why? | PASS | - | method-catalog | 1.0 | 18 | From the data this site has, I would not stand behind a generic “something changed from 2015 to 2024” claim yet, because the site’s own claim cards need a speci... |
| t5 | Where is the weakest link in that? Where would a reviewer poke holes? | PASS | - | method-catalog | 1.3 | 17 | From the data this site has, the weakest link is that only 2 of 9 source-linked analysis routes are specified far enough to review properly; the rest are still ... |
| t6 | Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like. | **FAIL** | `right_tool`, `has_evidence` | stratified-survey-summary | 1.35 | 18 | From the data this site has, I cannot yet open a one-row view for mammal counts from the restoration bird and mammal survey, because that survey is not structur... |

### c1-what-is-here / t2

User: Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot?

- `traceable`: no survey named and no path to the rows

```
From the data this site has, the trend chart would not answer a general question like “which of those”; it needs one measured quantity, so this is still a selection gap, not evidence that trends are absent. What it can plot over time includes aboveground carbon, basal area, canopy cover, canopy height, canopy openness, adult tree count per 0.04 ha plot, adult tree species richness, and several daily weather measures. If you want, I can check one of those now and see whether it has enough repeated years to read as a trend.
```

### c1-what-is-here / t3

User: Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking.

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, there is no site-wide year-by-year survey-effort measure ready to plot, so I cannot yet show whether later years had more sampling overall. The remaining data gap is that effort is recorded within separate surveys, not as one common time series across all of them. Would you like me to check the restoration bird survey first for year-wise effort?
```

### c1-what-is-here / t6

User: Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like.

- `right_tool`: ran ['stratified-survey-summary'], wanted one of ['coverage-versus-effort', 'entity-record-map', 'group-record-map', 'matrix-profile']
- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, I cannot yet open a one-row view for mammal counts from the restoration bird and mammal survey, because that survey is not structured here with matching event, effort and category fields for a row-level year split. The remaining data gap is that this site does not have a ready single-record table for those mammal counts in this route. If you want, I can instead pull the mapped mammal records for one named mammal so you can see what the recorded observations look like here.
```

## c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots

Session: `ecoanr-round5-final-c2-does-restoration-work`  |  categories: comparison, denominators, trust

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | We have been doing assisted natural regeneration in these fragments for years. Is there anything here that compares restored plots against ones we left to regrow on their own? | PASS | - | stratified-survey-summary | 1.4 | 23 | From the data this site has, yes: one restoration survey maps 132 surveyed sites in 2 treatment categories, with 264 recorded visits, so there is a direct resto... |
| t2 | Good. How do the birds compare across restored, naturally regenerating and benchmark plots? | PASS | - | stratified-survey-summary | 1.5 | 14 | From the data this site has, the bird recovery survey compares 69 surveyed sites across 3 plot categories, with 460 recorded visits, so restored, naturally rege... |
| t3 | How many plots in each of those three, and how many times was each visited? | **FAIL** | `right_tool` | visual-explain, compile-scientific-algebra-9b, local-site-evidence-search | 1.5 | 104 | From the data this site has, the bird recovery survey covers 69 plots across those 3 plot types, with 460 recorded visits in total. This comparison confirms tha... |
| t4 | Is that difference real, or could it just be that people spent more time in the benchmark plots? | **FAIL** | `has_evidence` | visual-explain | 1.5 | 18 | From the data this site has, we cannot say that difference is real. The stored explanation says this comparison keeps survey effort visible, but it is still des... |
| t5 | Which bird species are driving the gap? I care about the rainforest specialists, not the generalists. | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool`, `rows` | - | 1.75 | 14 | Do you want me to use the survey’s own `rainforest bird` class, or do you want named species only? If you mean named species, I will check which forest birds ar... |
| t6 | If I had to put one sentence in a report about whether restoration is working here, what would you let me say? | PASS | - | method-catalog | 1.5 | 24 | From the data this site has, the safest report sentence is: restoration plots can be compared with benchmark and naturally regenerating plots in the bird survey... |
| t7 | And what would you not let me say? | PASS | - | method-catalog | 2.0 | 13 | This site does not have a fitted bird model result for this restoration comparison. So I would not let you say that restoration has been proven to increase rain... |

### c2-does-restoration-work / t3

User: How many plots in each of those three, and how many times was each visited?

- `right_tool`: ran ['compile-scientific-algebra-9b', 'local-site-evidence-search', 'visual-explain'], wanted one of ['coverage-versus-effort', 'matrix-profile', 'plot-indicator-profile', 'stratified-survey-summary']

```
From the data this site has, the bird recovery survey covers 69 plots across those 3 plot types, with 460 recorded visits in total. This comparison confirms that restored, natural regrowth and benchmark plots are all in the same survey, but the summary visible here does not expose the per-category plot counts or per-category visit counts, so I should not invent those three numbers. If you want, I can keep digging for the underlying bird-survey rows so we can get the exact split by plot type.
```

### c2-does-restoration-work / t4

User: Is that difference real, or could it just be that people spent more time in the benchmark plots?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, we cannot say that difference is real. The stored explanation says this comparison keeps survey effort visible, but it is still descriptive only, not a treatment-effect test, and bird detections per visit are an observation summary, not bird population size. Would you like me to look for a plot-level measure in the data this site has, such as canopy cover or tree structure, that may show whether benchmark plots also had different habitat conditions?
```

### c2-does-restoration-work / t5

User: Which bird species are driving the gap? I care about the rainforest specialists, not the generalists.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['nothing'], wanted one of ['entity-record-map', 'group-record-map', 'matrix-profile', 'stratified-survey-summary']
- `rows`: no table, list or row language where the user asked for specifics

```
Do you want me to use the survey’s own `rainforest bird` class, or do you want named species only? If you mean named species, I will check which forest birds are recorded in the bird recovery survey and then compare them across restored, natural regrowth and benchmark plots.
```

## c3-lantana - Lantana keeps coming back: an honest gap and how to test it

Session: `ecoanr-round5-final-c3-lantana`  |  categories: gap-honesty, study-design, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Why does lantana keep coming back after we weed it? | PASS | - | entity-activity-profile | 1.5 | 21 | From the data this site has, lantana was recorded 36 times across 15 squares from 2003 to 2022, mostly in regeneration inventories and woody regeneration measur... |
| t2 | Do you have anything at all on lantana at this site? Even just where it has been recorded? | PASS | - | local-site-evidence-search, entity-record-map | 2.0 | 11 | I read “lantana” as *Lantana camara*, which this site has 36 records of. From the data this site has, this map shows 36 source-linked records of *Lantana camara... |
| t3 | So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots. | **FAIL** | `right_tool` | method-catalog | 1.5 | 43 | From the data this site has, this table shows there is a documented plant-community comparison method here, but it is only a method note, not a fitted result ye... |
| t4 | If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here? | **FAIL** | `honest_gap` | method-catalog, metric-time-series | 1.35 | 25 | From the data this site has, canopy cover is already measured here: this chart shows 5 monthly canopy cover values from 2 source versions, so you do not need to... |
| t5 | How many of the plant community plots could I revisit, and where are they? | **FAIL** | `has_evidence` | stratified-survey-summary | 1.5 | 33 | From the data this site has, I cannot give you a reliable count or map of revisit-ready plant community plots from that survey, because the plant community stru... |
| t6 | Draft the data request for me: exactly what I would ask my field team to bring back. | PASS | - | - | 1.85 | 14 | From the data this site has, canopy cover is already measured here, but this site does not have revisit-ready plot metadata for the plant community survey, and ... |

### c3-lantana / t3

User: So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots.

- `right_tool`: ran ['method-catalog'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'plot-indicator-profile']

```
From the data this site has, this table shows there is a documented plant-community comparison method here, but it is only a method note, not a fitted result yet. Given that lantana here was recorded mainly in regeneration inventory and woody regeneration measurements from the restoration opportunities study, I would use the plant community plots as the main stand-in, and canopy cover only as a supporting stand-in. From general knowledge: canopy cover is indirect because it tracks openness, while plot composition is closer to the weed response itself. If you want, I can pull the rows behind the plant community survey.
```

### c3-lantana / t4

User: If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here?

- `honest_gap`: no plain statement of what is missing

```
From the data this site has, canopy cover is already measured here: this chart shows 5 monthly canopy cover values from 2 source versions, so you do not need to start shade measurement from zero. To test whether shade suppresses lantana, you would still need repeat lantana measurements in the same plots and dates as the shade readings, plus a simple record of weeding history, because the chart shows canopy cover through time but does not by itself test the lantana response. From general knowledge: the clean field design is paired plots or repeat plots with canopy cover, lantana cover or stem counts, and disturbance noted together. If you want, I can pull the rows behind the canopy cover measurements.
```

### c3-lantana / t5

User: How many of the plant community plots could I revisit, and where are they?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, I cannot give you a reliable count or map of revisit-ready plant community plots from that survey, because the plant community structure survey is not stored here with matching plot, visit and effort fields in one usable structure. This table is telling us the missing piece plainly: this site does not have compatible plot-level revisit metadata for that survey, so “how many plots could I revisit, and where” cannot be answered from it as it stands. If you want, I can pull the rows behind the canopy cover measurements instead.
```

## c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule

Session: `ecoanr-round5-final-c4-natives-suppress`  |  categories: relationship, method-disclosure, mechanism

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Different angle. Are there native species here that turn up where lantana does not? | PASS | - | co-occurrence-map | 1.5 | 30 | From the data this site has, yes: native-origin records turn up in 104 squares inside this site’s boundary, while lantana turns up in 15, and only 15 squares ar... |
| t2 | How exactly did you match those two things up? Same plot and same year, or just the same general area? | PASS | - | visual-explain | 1.4 | 17 | From the data this site has, I matched them at the same 1.1 km square inside the site boundary, not at the same plot. For that map I did not require the same ye... |
| t3 | That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with? | **FAIL** | `has_evidence`, `gap_or_answer` | local-site-evidence-search, compile-scientific-algebra-9b, stratified-survey-summary | 1.5 | 89 | The remaining data gap is this: the restoration survey that holds most of the plot-based lantana records does not support a like-for-like plot summary here, so ... |
| t4 | What is the mechanism you would bet on here - shade, leaf litter, root competition? | PASS | - | entity-activity-profile | 1.35 | 16 | From the data this site has, I would not claim a mechanism yet: it has 36 lantana records from three plant surveys, but this table does not give a direct test o... |
| t5 | Is there anything in the canopy or tree structure data that supports the shade story? | **FAIL** | `right_tool`, `has_evidence` | entity-activity-profile | 1.5 | 21 | From the data this site has, not yet: it does include a plant community structure survey and woody regeneration measurements where lantana was recorded, but thi... |
| t6 | Give me three native species to trial as a shade crop, and say how confident you are in each one. | **FAIL** | `rows` | co-occurrence-map | 1.0 | 42 | From the data this site has, my three trial candidates are *Clerodendrum infortunatum* with high confidence, *Maesa indica* with high confidence, and *Oreocnide... |

### c4-natives-suppress / t3

User: That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with?

- `has_evidence`: no figure on a how-much / which / where question
- `gap_or_answer`: neither an answer nor an honest gap

```
The remaining data gap is this: the restoration survey that holds most of the plot-based lantana records does not support a like-for-like plot summary here, so I cannot give you a defensible plot count from this route. From the data this site has, the check failed because the plot records, survey events and survey-effort fields do not line up in one consistent plot table for that summary. If you want, I can pull the lantana plot rows from the plant surveys and check whether one single survey still supports a strict manual plot comparison.
```

### c4-natives-suppress / t5

User: Is there anything in the canopy or tree structure data that supports the shade story?

- `right_tool`: ran ['entity-activity-profile'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'metric-time-series', 'plot-indicator-profile']
- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, not yet: it does include a plant community structure survey and woody regeneration measurements where lantana was recorded, but this table does not show a direct canopy-versus-no-lantana comparison, so it does not by itself support the shade story. The remaining data gap is a like-for-like plot comparison of canopy openness, canopy cover, tree height or basal area between plots with lantana and plots without it. If you want, I can map the squares lantana shares with *Maesa indica*.
```

### c4-natives-suppress / t6

User: Give me three native species to trial as a shade crop, and say how confident you are in each one.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, my three trial candidates are *Clerodendrum infortunatum* with high confidence, *Maesa indica* with high confidence, and *Oreocnide integrifolia* with medium confidence: the first two each share all 15 lantana squares and all 15 have same-year records, while *Oreocnide integrifolia* shares 9 squares and only 4 same-year, across the restoration, threatened-tree, tree and habitat, and plant community surveys. This supports local co-recording in the same 1.1 km squares, not proof that any of them are the best shade crop or that they were in the same plot or acting on lantana by shade. If you want, I can tighten the third one by showing only the same-year squares for *Oreocnide integrifolia*.
```

## c5-what-to-replant - What to replant for a forest that keeps itself going

Session: `ecoanr-round5-final-c5-what-to-replant`  |  categories: design, network, seed-fate

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am putting together a planting list for a two hectare gap. I want a forest that regenerates on its own in thirty years, not a plantation. Where do I start? | PASS | - | site-orientation | 1.9 | 19 | From general knowledge: For a self-regenerating forest, the first step is usually to copy nearby natural forest structure, not to maximise planting numbers. Tha... |
| t2 | Which trees here actually get their seed moved by animals, and by which animals? | **FAIL** | `right_tool` | interaction-pairs | 1.75 | 20 | From general knowledge: In forest restoration, animal-moved seeds matter because they help later waves of tree recruitment reach the gap without repeated planti... |
| t3 | Of those, which lose most of their seed to predators? I do not want to plant something that never recruits. | **FAIL** | `right_tool` | interaction-pairs | 2.0 | 24 | From general knowledge: Seed predation can block recruitment, but to judge planting risk you need seed fate or recruitment rates, not just who was seen at the t... |
| t4 | Are any threatened species in that list worth including? | **FAIL** | `right_tool`, `rows` | entity-activity-profile | 1.5 | 26 | From general knowledge: If a threatened tree is still being recorded with regeneration as well as adult trees, it is often a better restoration candidate than a... |
| t5 | Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge. | PASS | - | local-site-evidence-search, interaction-pairs | 2.0 | 38 | From general knowledge: For a 30-year self-regenerating gap, I would mix a few animal-dispersed canopy trees with some fast early cover and some later-successio... |
| t6 | Which of those would fail if the hornbills do not come back? | PASS | - | interaction-pairs | 2.0 | 21 | From general knowledge: Large-seeded forest trees often benefit from hornbills, but that is a trait-based expectation, not proof for this site. If hornbills sta... |
| t7 | What should I plant first to bring the hornbills in? | **FAIL** | `rows` | interaction-pairs | 2.0 | 18 | From general knowledge: To bring hornbills back, plant the fruit trees they are already known to use first, and make them a small cluster rather than single sca... |

### c5-what-to-replant / t2

User: Which trees here actually get their seed moved by animals, and by which animals?

- `right_tool`: ran ['interaction-pairs'], wanted one of ['co-occurrence-map', 'entity-record-map', 'group-record-map', 'interaction-map', 'matrix-profile']

```
From general knowledge: In forest restoration, animal-moved seeds matter because they help later waves of tree recruitment reach the gap without repeated planting. But a visit to a fruiting tree is not the same as proven seed dispersal. From the data this site has, 150 named tree-animal pairs are recorded across 5,622 rows from the focal-tree frugivore observations, seed-fate work, and seed-predation experiment. The most recorded pairs are Yellow-browed Bulbul with *Persea macrantha* (629 records), White-cheeked Barbet with *Persea macrantha* (458 records), and Southern Hill Myna with *Heynea trijuga* (392 records), but these are records of being seen together, not proof that seed was moved. If you want, I can map where *Persea macrantha* is recorded.
```

### c5-what-to-replant / t3

User: Of those, which lose most of their seed to predators? I do not want to plant something that never recruits.

- `right_tool`: ran ['interaction-pairs'], wanted one of ['entity-record-map', 'group-record-map', 'interaction-map', 'matrix-profile', 'stratified-survey-summary']

```
From general knowledge: Seed predation can block recruitment, but to judge planting risk you need seed fate or recruitment rates, not just who was seen at the tree. From the data this site has, I cannot say which of these trees lose most seed to predators. What it has here is 150 recorded tree-animal pairs across 5,622 rows from frugivore observations and seed-predation work, but these are records of being seen together, not a comparative seed-loss rate or a proof that recruitment fails. If you want, I can map where *Persea macrantha* is recorded.
```

### c5-what-to-replant / t4

User: Are any threatened species in that list worth including?

- `right_tool`: ran ['entity-activity-profile'], wanted one of ['entity-record-map', 'group-record-map', 'matrix-profile', 'plot-indicator-profile']
- `rows`: no table, list or row language where the user asked for specifics

```
From general knowledge: If a threatened tree is still being recorded with regeneration as well as adult trees, it is often a better restoration candidate than a threatened tree known only from a few old adult records. But threat status alone is not enough; you want both persistence and recruitment signs. From the data this site has, *Heynea trijuga* is the clear threatened-tree candidate in that short list: it has 237 records in 45 squares from 2002 to 2022, and it appears in the threatened-tree records as well as regeneration and adult-tree surveys. I would treat that as worth considering; *Persea macrantha* is recorded here too, but this site summary does not tie it to the threatened-tree records in the same way, and these are records, not a count of how many trees survive. If you want, I can map the squares *Heynea trijuga* shares with Nilgiri langur.
```

### c5-what-to-replant / t7

User: What should I plant first to bring the hornbills in?

- `rows`: no table, list or row language where the user asked for specifics

```
From general knowledge: To bring hornbills back, plant the fruit trees they are already known to use first, and make them a small cluster rather than single scattered stems. Hornbills usually respond to food continuity and safe structure, not just one species. From the data this site has, start with *Myristica dactyloides* first. It is the strongest recorded hornbill tree here, with Malabar Grey Hornbill on *Myristica dactyloides* in 132 and 104 records, then *Heynea trijuga* in 97 records, and *Persea macrantha* in 54 and 34 records; there is also a smaller Great Hornbill record on *Myristica dactyloides* with 15 records. These are records of being seen together, not proof of seed movement, so I would use them as your first attraction mix, not as a guarantee of hornbill return. If you want, I can map where *Myristica dactyloides* is recorded.
```

## c6-what-grows-where - What is growing where: plots on a map, then one plot in detail

Session: `ecoanr-round5-final-c6-what-grows-where`  |  categories: place, drill-down, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Show me what is growing where across the fragments. I want to see the plots on a map. | PASS | - | stratified-survey-summary, site-orientation | 1.5 | 40 | From the data this site has, this map shows 42,348 source-linked records for 962 recorded taxa across 302 squares inside the fragments. It is a coverage map fro... |
| t2 | Which plot has the highest share of rainforest species? | PASS | - | plot-indicator-profile | 2.0 | 17 | From the data this site has, this map shows rainforest-bird share for 257 plots from the acoustic restoration survey. The site summary here does not print the w... |
| t3 | Tell me more about that one. What is the stem density there, and what does the canopy look like? | PASS | - | visual-explain, plot-indicator-profile | 1.0 | 43 | From the data this site has, “that one” has to mean the largest point on the rainforest-bird-share map, because no specific plot was clicked; that point is a si... |
| t4 | Where does that number come from? Show me the rows. | PASS | - | - | 1.5 | 11 | From the data this site has, that `1.0` comes from one row only in the acoustic restoration survey. The stored lineage says it is source row `215`, dated 12 Dec... |
| t5 | How does it compare against the benchmark plots? | PASS | - | plot-indicator-profile | 1.5 | 19 | From the data this site has, that point is at the top end of the rainforest-bird-share map with value `1.0`, and this table is the right comparison against the ... |
| t6 | Is that plot an outlier, or is it typical of the restored ones? | **FAIL** | `confidence` | compile-scientific-algebra-9b, visual-explain | 1.5 | 35 | From the data this site has, that point does not look like a lone outlier: the stored comparison shows at least five plotted points with the same top rainforest... |

### c6-what-grows-where / t6

User: Is that plot an outlier, or is it typical of the restored ones?

- `confidence`: no plain statement of how far to trust it

```
From the data this site has, that point does not look like a lone outlier: the stored comparison shows at least five plotted points with the same top rainforest-bird share of `1.0` in the acoustic restoration survey. So it sits at the top end of the observed range, but the remaining data gap is that this return does not print which of those tied top points are restored and which are benchmark in text. If you want, I can trace the tied top points next and see whether they are restored plots or benchmark plots.
```

## c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots

Session: `ecoanr-round5-final-c7-survey-budget`  |  categories: value-of-information, coverage-gap, uncertainty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Say I get twenty drone days next season. Where should I fly to learn the most? | **FAIL** | `right_tool` | survey-priority-squares | 1.3 | 19 | From the data this site has, 102 squares have records but only 22 have documented survey work, so the best first drone days are near Puduthottam, Sirikundra, Th... |
| t2 | What are you basing that on? Places we have never looked, or places where you think something is happening? | **FAIL** | `join_rule_disclosed` | visual-explain | 1.3 | 16 | From the data this site has, it is based on missing information, not on a claim that something ecological is happening there. Because you did not point to one s... |
| t3 | If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover. | **FAIL** | `honest_gap`, `names_alternative` | visual-explain | 0.8 | 23 | From the data this site has, no, this ranking would not change just because the sensor changes: it is still a map of where records are thin against documented s... |
| t4 | And if it is just me and two field assistants for thirty days on foot? | PASS | - | coverage-versus-effort | 1.4 | 17 | From the data this site has, yes, the answer shifts a bit for a foot team: I would work clustered thin-coverage squares, because records occur in 302 cells but ... |
| t5 | Which of the three buys me the most for a restoration decision in the next two years? | PASS | - | compile-scientific-algebra-9b | 0.8 | 22 | From the data this site has, the 30-day foot survey buys you the most for a restoration decision in the next two years, because it can cover clustered thin-cove... |
| t6 | Show me the gap map. Where is coverage thinnest relative to how much is going on there? | **FAIL** | `right_tool` | survey-priority-squares | 1.4 | 15 | From the data this site has, 102 squares hold records but only 22 have documented survey work, and the widest gaps are near Puduthottam, Sirikundra, Thenmalai, ... |
| t7 | Rank the top five places, with a reason for each that I could put in a proposal. | **FAIL** | `multi_turn` | - | 0.75 | 15 | From the data this site has, the top five are: 1) Puduthottam — 903 records but only 4 rows of documented survey work, so it is the biggest clear gap; 2) Siriku... |

### c7-survey-budget / t1

User: Say I get twenty drone days next season. Where should I fly to learn the most?

- `right_tool`: ran ['survey-priority-squares'], wanted one of ['cell-estimate-run', 'cell-estimate-suggest', 'cell-estimate-targets', 'cell-feature-map', 'coverage-versus-effort', 'earth-layer']

```
From the data this site has, 102 squares have records but only 22 have documented survey work, so the best first drone days are near Puduthottam, Sirikundra, Thenmalai and Murugaali-BlackBridge. The map is ranking where new flying would reduce the information gap most, not where biodiversity is richest, and some of that gap may be missing paperwork rather than missing fieldwork. If you want, I can show the whole coverage-versus-effort map behind this ranking.
```

### c7-survey-budget / t2

User: What are you basing that on? Places we have never looked, or places where you think something is happening?

- `join_rule_disclosed`: asked how two things were matched, did not say

```
From the data this site has, it is based on missing information, not on a claim that something ecological is happening there. Because you did not point to one square, this explanation is for the largest square on that map: it counts 903 records for 98 different things recorded there, while the ranking itself is driven by the gap between records and documented survey work. It can therefore surface places never properly documented, or places with thin effort records, and not necessarily the most important habitat. If you want, I can show the whole coverage-versus-effort map behind that ranking.
```

### c7-survey-budget / t3

User: If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover.

- `honest_gap`: no plain statement of what is missing
- `names_alternative`: gap stated without naming what does exist

```
From the data this site has, no, this ranking would not change just because the sensor changes: it is still a map of where records are thin against documented survey work, not a map of invasive cover. So it is good for “where can new effort reduce the biggest gap”, but not for “where is invasive cover most likely”, and some of the gap may still be missing effort notes rather than missing fieldwork. From general knowledge: hyperspectral is useful when you want to separate vegetation types or detect invasive plant cover from spectral differences, so the best flight plan would usually shift toward places where invasive plants are already recorded or suspected, not just where coverage is weak. If you want, I can check where invasive plants are recorded in this site’s data and then compare that with the thin-coverage squares.
```

### c7-survey-budget / t6

User: Show me the gap map. Where is coverage thinnest relative to how much is going on there?

- `right_tool`: ran ['survey-priority-squares'], wanted one of ['cell-estimate-suggest', 'cell-estimate-targets', 'cell-feature-map', 'coverage-versus-effort', 'earth-layer']

```
From the data this site has, 102 squares hold records but only 22 have documented survey work, and the widest gaps are near Puduthottam, Sirikundra, Thenmalai, Murugaali-BlackBridge and Puduthottam Coffee. This map shows where coverage is thinnest relative to recorded activity, but it is not a map of ecological importance, and some of the gap may be missing effort notes rather than missing fieldwork. If you want, I can show the whole coverage-versus-effort map behind this ranking.
```

### c7-survey-budget / t7

User: Rank the top five places, with a reason for each that I could put in a proposal.

- `multi_turn`: dropped the thread: none of ['coverage', 'place', 'square', 'area'] came back

```
From the data this site has, the top five are: 1) Puduthottam — 903 records but only 4 rows of documented survey work, so it is the biggest clear gap; 2) Sirikundra — 186 records and 6 effort rows, so activity is recorded but backing survey work is thin; 3) Thenmalai — 169 records and only 1 effort row, so a small amount of field effort is carrying a lot of inference; 4) Murugaali-BlackBridge — 316 records and 1 effort row, so the gap is sharp despite substantial recorded activity; 5) Puduthottam Coffee — 469 records and 21 effort rows, so it is still under-documented relative to what is being recorded there. This map ranks proposal-worthy information gaps, not ecological importance, and some of the gap may be missing effort notes rather than missing fieldwork. If you want, I can turn these five into a short proposal paragraph with one line on objective, method and expected decision value for each.
```

## c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here

Session: `ecoanr-round5-final-c8-monitoring-plan`  |  categories: design, data-request, gap-honesty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here. | PASS | - | site-orientation | 1.0 | 30 | From general knowledge: To test whether assisted natural regeneration beats active planting, the cleanest design is a matched comparison with the same starting ... |
| t2 | What can I reuse as a baseline instead of starting from scratch? | PASS | - | coverage-versus-effort | 1.35 | 12 | From general knowledge: For ANR versus planting, the strongest reusable baseline is any earlier plot or square data that already measured vegetation structure i... |
| t3 | What is the minimum I have to keep collecting so the old data stays comparable? | **FAIL** | `rows` | method-catalog | 0.85 | 16 | From general knowledge: To keep old and new data comparable, the minimum is to repeat the same field unit, season, effort, and core response measures each round... |
| t4 | What is missing entirely, that I would have to start measuring from zero? | **FAIL** | `names_alternative` | method-catalog | 1.15 | 22 | From general knowledge: For a fair ANR versus planting test, the hardest thing to recover later is repeat, treatment-matched field data collected the same way f... |
| t5 | How many plots, and how many visits a year, to have a real chance of detecting a difference? | **FAIL** | `confidence` | method-catalog | 1.5 | 24 | From general knowledge: The number of plots and visits depends mainly on one chosen primary outcome and how noisy it is across plots. Survival usually needs few... |
| t6 | Write it up as a one page plan I can hand to my team. | PASS | - | method-catalog | 1.85 | 27 | From general knowledge: A fair ANR versus planting test needs the same starting condition, the same field method, and a small set of repeated measures that matt... |
| t7 | And a list of the data I would need to request from the other groups working here. | PASS | - | method-catalog | 1.7 | 19 | From general knowledge: If you want comparisons across groups to hold up, ask for the raw field data, the method sheet, and the effort log, not only summaries. ... |

### c8-monitoring-plan / t3

User: What is the minimum I have to keep collecting so the old data stays comparable?

- `rows`: no table, list or row language where the user asked for specifics

```
From general knowledge: To keep old and new data comparable, the minimum is to repeat the same field unit, season, effort, and core response measures each round; if any one of these shifts, the trend becomes hard to trust. From the data this site has, 9 documented method cards match this question, but they are method notes, not fitted results, and 2 are still not fully specified for implementation review. So the minimum to keep collecting is: the same plot or square, the same treatment label, the same survey timing, the same effort, and the same core vegetation measures already used there such as stem counts, survival, height, dbh, and canopy-related measures; if you drop any of these, the old and new rounds stop being directly comparable. If you want, I can turn that into a one-page field protocol with the exact minimum columns and revisit schedule.
```

### c8-monitoring-plan / t4

User: What is missing entirely, that I would have to start measuring from zero?

- `names_alternative`: gap stated without naming what does exist

```
From general knowledge: For a fair ANR versus planting test, the hardest thing to recover later is repeat, treatment-matched field data collected the same way from the start. From the data this site has, there is no completed, ready-to-run repeat method here that already gives you ANR-versus-planting outcomes through time, so that comparison would have to start from zero. This table shows 9 documented analysis designs, but 2 are still not fully specified, and these are method notes rather than finished results. If you want, I can turn that gap into a minimum new-measurement list for years 0, 1, 2 and 3.
```

### c8-monitoring-plan / t5

User: How many plots, and how many visits a year, to have a real chance of detecting a difference?

- `confidence`: no plain statement of how far to trust it

```
From general knowledge: The number of plots and visits depends mainly on one chosen primary outcome and how noisy it is across plots. Survival usually needs fewer visits than growth, and species composition usually needs more plots. From the data this site has, there is no finished, repeat analysis here that already gives the variance needed to calculate a defensible sample size for ANR versus planting, so I cannot give a hard plot number from this alone. This table shows 9 documented analysis designs, but they are method notes rather than fitted results, so the missing piece is repeat outcome variability from matched restoration plots. If you want, tell me the one outcome that matters most to you — survival, stem density, height, dbh, canopy cover, or cost per surviving recruit — and I can give the minimum practical design for that outcome.
```

