# Ecology ANR bench - results

Run: `round1`  |  endpoint: `http://172.17.0.1:7012`  |  model: `idli-insight-valparai`  |  started: 2026-07-26T00:47:57+05:30

**3/52 turns pass (6%)**, 0/8 conversations clean, mean language score 1.58/2, median latency 18.5s (max 72.7s), 3 turns retried.

## How this number was baselined

- ROUTING EXPECTATIONS RE-BASELINED after the bridge shipped `interaction-pairs` and `survey-priority-squares` (commit 1a57eb9). The rule applied: widen an existing `capabilities_any` list only where the newly-chosen tool genuinely answers the question better; never narrow one, and never add a routing requirement to a turn that did not already have one. Where the model simply picked a worse tool, the turn was left failing.
- WIDENED (5 turns, routing is genuinely right): c5/t2 and c5/t3 now accept `interaction-pairs` -- it names the recorded tree-animal pairs, which is exactly what 'who disperses what' asks for, where `interaction-map` only maps declared association types. c5/t4 now accepts `entity-activity-profile` and `interaction-pairs` -- it answered with Heynea trijuga, 237 records in 45 squares, 2002-2022, tied to the threatened-tree records. c7/t1 and c7/t6 now accept `survey-priority-squares` -- it ranks by the records-versus-effort gap and names squares by real places, which is the question.
- LEFT FAILING (5 turns, the tool picked was worse): c1/t6 ran `stratified-survey-summary` for 'show me the rows behind the mammal counts', could not produce a row, and offered the mapped-records route in its own next sentence -- a tool that could answer was available and not used. c2/t3 and c2/t5 never called `stratified-survey-summary` with the declared `Site_type` category that holds the split being asked for. c3/t3 ran `method-catalog` for a question about canopy cover and plant-community plots. c4/t5 ran `entity-activity-profile` and then asserted there was no canopy comparison, without querying the ten canopy and structure metrics this index holds (`canopy_cover`, `canopy_openness`, `basal_area`, `tree_height` among them).
- Re-grading the bridge's own round5 transcript under these corrected expectations moves it from 27/52 to 31/52 and `right_tool` from 58% to 79%. That is the size of the harness drift, isolated from any product change.
- GRADER CALIBRATED TWICE, both times against transcripts rather than intuition. Round 1: `honest_gap` and `confidence` were widened after reading the failures showed 'there is still no recorded lantana name here' and 'I cannot call that a real plot-type effect yet' were being missed. Round 2: `join_rule_disclosed` was widened (a join is also disclosed by saying what the table actually records and how unequal the watching behind it was), and the gap checks were made conditional -- where the product now finds the data and answers with a figure, answering is better than confessing, so `honest_gap` passes on evidence and `names_alternative` binds only when absence was actually claimed. Uncorrected, round 2 scores 37/66; corrected, 46/66. Both numbers are stated here on purpose.

## Pass rate by dimension

| Check | Pass rate | n |
| --- | --- | --- |
| `next_step_in_prose` | 17% | 52 |
| `dead_end` | 19% | 52 |
| `gap_or_answer` | 33% | 3 |
| `general_knowledge_labelled` | 50% | 2 |
| `honest_gap` | 50% | 6 |
| `has_evidence` | 56% | 27 |
| `rows` | 56% | 16 |
| `join_rule_disclosed` | 67% | 3 |
| `traceable` | 67% | 27 |
| `right_tool` | 71% | 24 |
| `confidence` | 92% | 12 |
| `not_catch_all` | 95% | 20 |
| `jargon` | 96% | 52 |
| `brevity` | 100% | 1 |
| `multi_turn` | 100% | 45 |
| `names_alternative` | 100% | 4 |
| `no_invention` | 100% | 1 |
| `no_reask` | 100% | 45 |
| `no_transport_leak` | 100% | 52 |
| `questions` | 100% | 26 |
| `responded` | 100% | 52 |
| `visual_present` | 100% | 8 |

## Pass rate by conversation

| Conversation | Turn pass rate |
| --- | --- |
| c1-what-is-here - What is even here, and what can I trust for a trend | 0% |
| c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots | 0% |
| c3-lantana - Lantana keeps coming back: an honest gap and how to test it | 17% |
| c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule | 0% |
| c5-what-to-replant - What to replant for a forest that keeps itself going | 14% |
| c6-what-grows-where - What is growing where: plots on a map, then one plot in detail | 0% |
| c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots | 0% |
| c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here | 14% |

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| comparison | 0% |
| coverage-gap | 0% |
| data-request | 14% |
| denominators | 0% |
| design | 14% |
| drill-down | 0% |
| gap-honesty | 15% |
| mechanism | 0% |
| method-disclosure | 0% |
| network | 14% |
| orientation | 0% |
| place | 0% |
| relationship | 0% |
| seed-fate | 14% |
| study-design | 17% |
| traceability | 6% |
| trust | 0% |
| uncertainty | 0% |
| value-of-information | 0% |

## c1-what-is-here - What is even here, and what can I trust for a trend

Session: `ecoanr-round1-c1-what-is-here`  |  categories: orientation, trust, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have just taken over restoration monitoring for the Anamalai rainforest fragments. Before I plan anything I need to know what long-term monitoring actually exists here, and how far back it goes. | **FAIL** | `next_step_in_prose`, `dead_end`, `has_evidence` | site-orientation, coverage-versus-effort | 1.25 | 27 | General ecological context: In fragmented rainforest landscapes, long-term monitoring usually mixes repeated biodiversity surveys with vegetation plots and rest... |
| t2 | Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot? | **FAIL** | `has_evidence` | metric-time-series | 1.5 | 21 | General ecological context: A trend needs the same thing to have been measured repeatedly, not just many records. In restoration sites, this is often easier for... |
| t3 | Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking. | **FAIL** | `next_step_in_prose`, `dead_end`, `has_evidence` | metric-time-series | 1.9 | 15 | General ecological context: To test whether later years only look richer because more people surveyed, we need effort recorded by year, not just more observatio... |
| t4 | So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why? | **FAIL** | `next_step_in_prose`, `dead_end` | method-catalog | 1.5 | 22 | General ecological context: For a 2015 to 2024 change claim, I would trust repeated plot and canopy measures more than raw sighting counts. Counts can go up sim... |
| t5 | Where is the weakest link in that? Where would a reviewer poke holes? | **FAIL** | `next_step_in_prose`, `dead_end` | visual-explain | 1.3 | 27 | General ecological context: Reviewers usually attack the step where a general method is turned into a site-specific claim. The weak point is often not the stati... |
| t6 | Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like. | **FAIL** | `next_step_in_prose`, `right_tool`, `has_evidence` | stratified-survey-summary, local-site-evidence-search | 1.35 | 35 | General ecological context: A reviewer often wants to inspect one raw record before trusting a count. That helps separate a true repeated observation from a sum... |

### c1-what-is-here / t1

User: I have just taken over restoration monitoring for the Anamalai rainforest fragments. Before I plan anything I need to know what long-term monitoring actually exists here, and how far back it goes.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `has_evidence`: no figure on a how-much / which / where question

```
General ecological context: In fragmented rainforest landscapes, long-term monitoring usually mixes repeated biodiversity surveys with vegetation plots and restoration measurements. For planning, the first check is not just how many records exist, but where survey effort was explicitly recorded and whether the time span is visible in the data. From the data this site has, monitoring is substantial and spread widely across the Anamalai fragments, with records in many places but explicit survey effort recorded in a much smaller subset. This map is useful for seeing where monitoring was actually documented, but it does not show the year range, so the remaining data gap is how far back those monitored series go.
```

### c1-what-is-here / t2

User: Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot?

- `has_evidence`: no figure on a how-much / which / where question

```
General ecological context: A trend needs the same thing to have been measured repeatedly, not just many records. In restoration sites, this is often easier for vegetation structure, carbon, bird richness, canopy and weather than for one-off species lists. From the data this site has, a trend can be checked for repeated measures such as aboveground carbon, bird richness from acoustic surveys, adult tree richness and count, basal area, mean tree height, canopy cover or openness, coffee stems, cut tree stems, and daily weather. This chart could not open because your question did not name one measure; tell me which one you want first, and I’ll pull the year-wise trend for that.
```

### c1-what-is-here / t3

User: Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `has_evidence`: no figure on a how-much / which / where question

```
General ecological context: To test whether later years only look richer because more people surveyed, we need effort recorded by year, not just more observations. If effort is not recorded as its own measure, the trend is still at risk of sampling bias. From the data this site has, I cannot show a year-wise survey-effort chart because survey effort is not recorded here as a plottable measure. The remaining data gap is that later-year increases cannot yet be separated from more people looking, using this route alone.
```

### c1-what-is-here / t4

User: So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: For a 2015 to 2024 change claim, I would trust repeated plot and canopy measures more than raw sighting counts. Counts can go up simply because effort went up; a stronger claim needs either fixed plots, a reference benchmark, or an effort-adjusted method. From the data this site has, I would stand behind claims built from repeated adult-tree stocks per plot area, plot diversity with trait filters, canopy response against a reference, benchmarked canopy profile, single-season occupancy, and effort-adjusted reporting-rate trends. I would not stand behind a simple “more records means more biodiversity” claim, because this methods view says the defensible route here is to use designs that control for plot area, detectability, reference condition, or changing survey effort.
```

### c1-what-is-here / t5

User: Where is the weakest link in that? Where would a reviewer poke holes?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: Reviewers usually attack the step where a general method is turned into a site-specific claim. The weak point is often not the statistic itself, but whether the site’s own records actually show that method fits the years, places and effort pattern being claimed. From the data this site has, the weakest link is the methods screen I used last time: it did not actually match your 2015 to 2024 trend question, and it returned no supporting rows. A reviewer would rightly say that the broad list of defensible methods was not yet tied to this site, this time window, or these records, so that part needs a proper site-specific check before I would stand behind it.
```

### c1-what-is-here / t6

User: Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like.

- `next_step_in_prose`: answer names no move the user could make next
- `right_tool`: ran ['local-site-evidence-search', 'stratified-survey-summary'], wanted one of ['coverage-versus-effort', 'entity-record-map', 'group-record-map', 'matrix-profile']
- `has_evidence`: no figure on a how-much / which / where question

```
General ecological context: A reviewer often wants to inspect one raw record before trusting a count. That helps separate a true repeated observation from a summary that mixes categories, sites or effort. From the data this site has, I could not open a clean row-level view for mammal counts from that restoration survey, because the site, effort and category fields do not line up well enough in that source. The remaining data gap is that a plain search for “mammal” in the local records also did not resolve to one recorded mammal name, so I cannot yet show you a single raw row from that route.
```

## c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots

Session: `ecoanr-round1-c2-does-restoration-work`  |  categories: comparison, denominators, trust

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | We have been doing assisted natural regeneration in these fragments for years. Is there anything here that compares restored plots against ones we left to regrow on their own? | **FAIL** | `next_step_in_prose`, `dead_end`, `has_evidence`, `traceable` | method-catalog | 1.25 | 28 | General ecological context: In restoration work, the cleanest comparison is usually a matched plot design where assisted regeneration and passive regrowth are t... |
| t2 | Good. How do the birds compare across restored, naturally regenerating and benchmark plots? | **FAIL** | `next_step_in_prose`, `dead_end` | stratified-survey-summary | 1.5 | 19 | General ecological context: Bird records often respond quickly to habitat structure, but simple differences between plot types can still reflect survey effort a... |
| t3 | How many plots in each of those three, and how many times was each visited? | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool` | - | 1.5 | 6 | From the data this site has, the bird comparison table confirms 69 surveyed plots across the three plot types and 460 visits in total. The exact split by plot t... |
| t4 | Is that difference real, or could it just be that people spent more time in the benchmark plots? | **FAIL** | `next_step_in_prose`, `dead_end`, `has_evidence` | method-catalog | 1.5 | 21 | From the data this site has, I cannot call that a real plot-type effect yet. The bird comparison we saw is descriptive and keeps effort visible, so yes, extra t... |
| t5 | Which bird species are driving the gap? I care about the rainforest specialists, not the generalists. | **FAIL** | `next_step_in_prose`, `dead_end`, `rows` | group-record-map | 1.4 | 22 | From the data this site has, I have taken “rainforest specialists” to mean the mature-forest bird set recorded here. This map shows that set is well represented... |
| t6 | If I had to put one sentence in a report about whether restoration is working here, what would you let me say? | **FAIL** | `next_step_in_prose`, `dead_end` | site-orientation | 1.4 | 15 | From the data this site has, I would allow this sentence: restoration appears to be moving plots toward benchmark forest bird communities, but the current evide... |
| t7 | And what would you not let me say? | **FAIL** | `next_step_in_prose`, `dead_end`, `honest_gap` | site-orientation | 1.5 | 11 | From the data this site has, I would not let you say that restoration has already proven a causal recovery of rainforest specialist birds, or that restored plot... |

### c2-does-restoration-work / t1

User: We have been doing assisted natural regeneration in these fragments for years. Is there anything here that compares restored plots against ones we left to regrow on their own?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
General ecological context: In restoration work, the cleanest comparison is usually a matched plot design where assisted regeneration and passive regrowth are tracked with the same field measures over time. From the data this site has, there are source-linked analysis notes that look relevant to restored-versus-regrowth comparisons, but this table is only telling us which analysis designs exist, not giving a fitted result. So yes, there is something to inspect here, but this map view alone does not yet show whether the comparison was actually run or what it found.
```

### c2-does-restoration-work / t2

User: Good. How do the birds compare across restored, naturally regenerating and benchmark plots?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: Bird records often respond quickly to habitat structure, but simple differences between plot types can still reflect survey effort and detectability, not only restoration effect. From the data this site has, there is a direct bird comparison across three plot types, with 69 surveyed sites and 460 visits kept visible in the summary. This chart is useful for seeing how detections differ between restored, naturally regenerating and benchmark plots, but it is descriptive only: detections are not the same as bird population size, and it does not by itself prove treatment effect.
```

### c2-does-restoration-work / t3

User: How many plots in each of those three, and how many times was each visited?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['nothing'], wanted one of ['coverage-versus-effort', 'matrix-profile', 'plot-indicator-profile', 'stratified-survey-summary']

```
From the data this site has, the bird comparison table confirms 69 surveyed plots across the three plot types and 460 visits in total. The exact split by plot type is not exposed in the short summary here, and the follow-up count trace I tried for the per-type breakdown did not return, so I cannot state those three counts safely from this run alone.
```

### c2-does-restoration-work / t4

User: Is that difference real, or could it just be that people spent more time in the benchmark plots?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, I cannot call that a real plot-type effect yet. The bird comparison we saw is descriptive and keeps effort visible, so yes, extra time in benchmark plots could explain part of the difference, and this follow-up check did not return a matching ready analysis here to separate effort from plot type.
```

### c2-does-restoration-work / t5

User: Which bird species are driving the gap? I care about the rainforest specialists, not the generalists.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, I have taken “rainforest specialists” to mean the mature-forest bird set recorded here. This map shows that set is well represented in the records, but it does not yet tell us which particular species are driving the restored-versus-benchmark gap, because these are raw records from mixed survey effort, not an effort-adjusted species ranking.
```

### c2-does-restoration-work / t6

User: If I had to put one sentence in a report about whether restoration is working here, what would you let me say?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
From the data this site has, I would allow this sentence: restoration appears to be moving plots toward benchmark forest bird communities, but the current evidence here is still descriptive and part of that gap could reflect uneven survey effort. The map is a site overview only, so treat that as a cautious summary, not proof of treatment effect.
```

### c2-does-restoration-work / t7

User: And what would you not let me say?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `honest_gap`: neither a plain statement of what is missing nor a real figure

```
From the data this site has, I would not let you say that restoration has already proven a causal recovery of rainforest specialist birds, or that restored plots have fully matched benchmark plots. This map is only a site overview, and the bird comparison we checked is still descriptive, with survey effort and detectability still able to affect the gap.
```

## c3-lantana - Lantana keeps coming back: an honest gap and how to test it

Session: `ecoanr-round1-c3-lantana`  |  categories: gap-honesty, study-design, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Why does lantana keep coming back after we weed it? | **FAIL** | `next_step_in_prose`, `dead_end`, `gap_or_answer` | entity-record-map | 2.0 | 23 | From the data this site has, I could not confirm a recorded `lantana` record here, so this answer is general rather than site-specific. General ecological conte... |
| t2 | Do you have anything at all on lantana at this site? Even just where it has been recorded? | **FAIL** | `has_evidence`, `traceable` | local-site-evidence-search, entity-record-map | 2.0 | 14 | From the data this site has, I do not have a recorded `lantana` name or a map of its records here. The site search and the map both came back as a name non-matc... |
| t3 | So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots. | **FAIL** | `right_tool` | - | 1.85 | 9 | From the data this site has, we do not yet have a recorded `lantana` name to calibrate any stand-in against actual lantana records here. General ecological cont... |
| t4 | If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here? | **FAIL** | `next_step_in_prose`, `dead_end`, `rows`, `honest_gap` | - | 0.85 | 10 | From the data this site has, there is still no recorded `lantana` name here, so you would need to add a direct lantana field to the plant community plots. Measu... |
| t5 | How many of the plant community plots could I revisit, and where are they? | PASS | - | stratified-survey-summary | 1.4 | 14 | From the data this site has, 132 plant community plot sites are mapped, with 264 explicit visits, so these are the plots you could likely target for revisit. Th... |
| t6 | Draft the data request for me: exactly what I would ask my field team to bring back. | **FAIL** | `next_step_in_prose`, `dead_end` | - | 1.85 | 15 | From the data this site has, you can anchor this to the 132 plant community plot sites with 264 recorded visits, but `lantana` itself is not yet being recorded ... |

### c3-lantana / t1

User: Why does lantana keep coming back after we weed it?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `gap_or_answer`: neither an answer nor an honest gap

```
From the data this site has, I could not confirm a recorded `lantana` record here, so this answer is general rather than site-specific. General ecological context: lantana often comes back because weeding removes the top growth but not the root crown, buried seeds keep germinating for years, and fresh light after clearing helps new shoots establish. In practice, it usually needs repeat follow-up on resprouts and seedlings, not one-time removal alone.
```

### c3-lantana / t2

User: Do you have anything at all on lantana at this site? Even just where it has been recorded?

- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
From the data this site has, I do not have a recorded `lantana` name or a map of its records here. The site search and the map both came back as a name non-match, and that is not evidence that lantana is absent. If you want, I can next check nearby public records for `Lantana camara` around this site.
```

### c3-lantana / t3

User: So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots.

- `right_tool`: ran ['nothing'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'plot-indicator-profile']

```
From the data this site has, we do not yet have a recorded `lantana` name to calibrate any stand-in against actual lantana records here. General ecological context: for a woody invasive like lantana, `canopy cover` alone is usually a weak stand-in. It can help explain where lantana may do well, but it does not tell you whether lantana is actually there. Plant community plots are usually the better stand-in, especially if they record shrub cover, disturbance, gaps, edge conditions, and other invasive plants. If you need one practical stand-in now, I would start with the plant community plots and use canopy cover only as a supporting map. Do you want a quick field proxy for prioritising weeding, or a stronger analysis proxy for estimating likely lantana presence?
```

### c3-lantana / t4

User: If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `rows`: no table, list or row language where the user asked for specifics
- `honest_gap`: neither a plain statement of what is missing nor a real figure

```
From the data this site has, there is still no recorded `lantana` name here, so you would need to add a direct lantana field to the plant community plots. Measure lantana presence, percent cover, stem counts, height class, and whether it is seedling, resprout, or mature, and at the same points measure canopy cover, light reaching the understorey, and disturbance like recent weeding, edge, grazing, or fire. General ecological context: if you only measure shade, you cannot tell whether low lantana is due to shade or due to repeated clearing; you need both shade and disturbance in the same plots.
```

### c3-lantana / t6

User: Draft the data request for me: exactly what I would ask my field team to bring back.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
From the data this site has, you can anchor this to the 132 plant community plot sites with 264 recorded visits, but `lantana` itself is not yet being recorded by name. So the field request should add a small lantana-and-shade module at each revisit plot. **Field Data Request** Please revisit the existing plant community plot locations and bring back, for each plot: 1. Plot identity and revisit details - Plot name or code already used in the earlier survey - Date - Team names - GPS point at plot centre - Photo set: north, south, east, west, and one canopy photo upward 2. Lantana recording - Lantana present: yes/no - If present, percent cover of lantana in the plot - Number of lantana stems, or stem density by subplot if very dense - Height class: seedling, sapling/small shrub, mature shrub - Regrowth type: new seedling, coppice/resprout from cut base, or old uncut plant - Fruiting or flowering: yes/no 3. Shade and light - Canopy cover above the plot - Understorey light reaching lantana height, if possible at a fixed time window - Gap or no gap above plot - Distance to nearest open edge, road, trail, or stream 4. Disturbance and management - Was the plot weeded before: yes/no/don’t 
```

## c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule

Session: `ecoanr-round1-c4-natives-suppress`  |  categories: relationship, method-disclosure, mechanism

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Different angle. Are there native species here that turn up where lantana does not? | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool`, `traceable`, `gap_or_answer` | - | 2.0 | 14 | To check that properly, I need one narrow choice: which native species or group should I compare with lantana here? For example, one named species, native trees... |
| t2 | How exactly did you match those two things up? Same plot and same year, or just the same general area? | **FAIL** | `next_step_in_prose`, `dead_end` | - | 1.9 | 11 | I have not matched them yet. I stopped at the clarification because “native species” was too broad. If we do this with the map here, the default match is shared... |
| t3 | That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with? | **FAIL** | `next_step_in_prose`, `dead_end`, `has_evidence` | local-site-evidence-search, stratified-survey-summary | 1.5 | 67 | From the data this site has, I cannot defend a plot-level count yet. The check came back blocked because the plant survey source does not keep a compatible shar... |
| t4 | What is the mechanism you would bet on here - shade, leaf litter, root competition? | **FAIL** | `next_step_in_prose`, `dead_end`, `confidence`, `general_knowledge_labelled` | - | 1.85 | 10 | From the data this site has, we do not have a direct mechanism test yet. The records so far only support co-recording or non-overlap, not why that pattern happe... |
| t5 | Is there anything in the canopy or tree structure data that supports the shade story? | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool`, `not_catch_all`, `has_evidence`, `traceable` | site-orientation | 2.0 | 20 | From the data this site has, not yet. This map shows where records are concentrated, but record density is coverage only, not canopy, shade, or absence, so it d... |
| t6 | Give me three native species to trial as a shade crop, and say how confident you are in each one. | **FAIL** | `traceable` | local-site-evidence-search | 1.35 | 44 | From the data this site has, I would start with **Acronychia pedunculata**, **Syzygium cumini**, and **Vateria indica**. My confidence is: - **Acronychia pedunc... |

### c4-natives-suppress / t1

User: Different angle. Are there native species here that turn up where lantana does not?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['nothing'], wanted one of ['co-occurrence-map', 'entity-record-map', 'group-record-map', 'interaction-map', 'matrix-profile']
- `traceable`: no survey named and no path to the rows
- `gap_or_answer`: neither an answer nor an honest gap

```
To check that properly, I need one narrow choice: which native species or group should I compare with lantana here? For example, one named species, native trees, birds, frogs, or another group.
```

### c4-natives-suppress / t2

User: How exactly did you match those two things up? Same plot and same year, or just the same general area?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
I have not matched them yet. I stopped at the clarification because “native species” was too broad. If we do this with the map here, the default match is shared squares inside this site’s boundary: where lantana was recorded and where the chosen native species was also recorded in the same square. That does not mean same plot, same visit, or direct interaction; and it is not same year unless we deliberately add a same-year condition.
```

### c4-natives-suppress / t3

User: That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, I cannot defend a plot-level count yet. The check came back blocked because the plant survey source does not keep a compatible shared plot/event structure for matching lantana against native-versus-alien plant records at plot level, so I do not have a valid number of plots to report.
```

### c4-natives-suppress / t4

User: What is the mechanism you would bet on here - shade, leaf litter, root competition?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `confidence`: no plain statement of how far to trust it
- `general_knowledge_labelled`: site records and general knowledge not separated

```
From the data this site has, we do not have a direct mechanism test yet. The records so far only support co-recording or non-overlap, not why that pattern happens. General ecological context: If I had to bet, I would put shade and litter first, then root competition. In lantana thickets, heavy shade cuts light for seedlings, and dense litter can block germination and early survival. Root competition matters too, but it is usually harder to separate in field records unless someone measured soils, light, or seedling performance directly.
```

### c4-natives-suppress / t5

User: Is there anything in the canopy or tree structure data that supports the shade story?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['site-orientation'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'metric-time-series', 'plot-indicator-profile']
- `not_catch_all`: answered a specific question with only ['site-orientation']
- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
From the data this site has, not yet. This map shows where records are concentrated, but record density is coverage only, not canopy, shade, or absence, so it does not support the shade story by itself.
```

### c4-natives-suppress / t6

User: Give me three native species to trial as a shade crop, and say how confident you are in each one.

- `traceable`: no survey named and no path to the rows

```
From the data this site has, I would start with **Acronychia pedunculata**, **Syzygium cumini**, and **Vateria indica**. My confidence is: - **Acronychia pedunculata: high.** It shows up in regeneration, tree-neighbour measurements, and older restoration-tree records here, so it looks like a strong local candidate for a shade-focused trial. - **Syzygium cumini: medium-high.** It is recorded here in regeneration, adult trees, and tree-structure measurements, which supports local fit, but the site evidence is less dense than for the first two. - **Vateria indica: medium.** It is clearly recorded here and often in wooded settings, but the records I checked are more from detections and transects than from the fuller tree-structure mix, so I would trial it more cautiously. General ecological context: For a first trial, I would favour species with repeated local records across more than one record type, because that is the safest sign they are established in the same landscape. My confidence here is about local evidence support for trialling, not proof that any one species will beat lantana under shade without field testing.
```

## c5-what-to-replant - What to replant for a forest that keeps itself going

Session: `ecoanr-round1-c5-what-to-replant`  |  categories: design, network, seed-fate

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am putting together a planting list for a two hectare gap. I want a forest that regenerates on its own in thirty years, not a plantation. Where do I start? | PASS | - | site-orientation | 2.0 | 19 | **General ecological context:** For a self-regenerating forest, start with function, not just species count. You usually need a mix of fast shade-makers, longer... |
| t2 | Which trees here actually get their seed moved by animals, and by which animals? | **FAIL** | `next_step_in_prose`, `dead_end`, `has_evidence` | interaction-map | 2.0 | 19 | General ecological context: In tropical forest recovery, animal-dispersed trees are often the backbone of self-assembly because birds and mammals keep bringing ... |
| t3 | Of those, which lose most of their seed to predators? I do not want to plant something that never recruits. | **FAIL** | `next_step_in_prose`, `dead_end` | interaction-map | 2.0 | 16 | General ecological context: Heavy seed loss can block recruitment, but a visit to a seed station is not the same as measured seed predation. To drop a tree from... |
| t4 | Are any threatened species in that list worth including? | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool`, `rows`, `traceable` | - | 1.9 | 11 | I need to resolve what “that list” means before I test threat status. Are you asking about the tree species you are considering for planting, or the animal-move... |
| t5 | Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge. | **FAIL** | `next_step_in_prose`, `dead_end`, `rows` | local-site-evidence-search, group-record-map | 1.5 | 42 | General ecological context: For a 30-year self-assembling stand, the first shortlist should favour native canopy and subcanopy trees with animal-dispersed fruit... |
| t6 | Which of those would fail if the hornbills do not come back? | **FAIL** | `next_step_in_prose`, `dead_end`, `rows` | group-record-map, discover-biotic-interactions | 1.5 | 73 | General ecological context: If a planting mix depends too much on one large frugivore, recovery becomes brittle. For a 30-year target, safer species are the one... |
| t7 | What should I plant first to bring the hornbills in? | **FAIL** | `next_step_in_prose`, `dead_end`, `rows` | local-site-evidence-search, group-record-map | 2.0 | 28 | General ecological context: To bring hornbills back, the first planting should offer food early and often, not only future timber. In practice that means starti... |

### c5-what-to-replant / t2

User: Which trees here actually get their seed moved by animals, and by which animals?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `has_evidence`: no figure on a how-much / which / where question

```
General ecological context: In tropical forest recovery, animal-dispersed trees are often the backbone of self-assembly because birds and mammals keep bringing seed in after planting. But a trait like “animal-dispersed” is not the same as a recorded local association between a tree and a disperser. From the data this site has, there are no recorded source-linked rows for seed movement itself, so I cannot name tree-animal pairs here from this map. What the records do have for follow-up are four observed relation types around focal trees and seed experiments: camera detections at focal seed trees, detections at seed experiments, focal scans on fruiting trees, and observed visits to focal trees.
```

### c5-what-to-replant / t3

User: Of those, which lose most of their seed to predators? I do not want to plant something that never recruits.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: Heavy seed loss can block recruitment, but a visit to a seed station is not the same as measured seed predation. To drop a tree from a planting list, we need evidence of repeated seed loss or poor establishment, not only animal presence. From the data this site has, there are 745 recorded detections at seed experiments linking 37 recorded things in 72 pairs, so there is useful pressure around seeds. But this map does not show which tree loses the most seed, or whether the animal caused seed death rather than just being present, so I cannot rule trees out for recruitment failure from this alone.
```

### c5-what-to-replant / t4

User: Are any threatened species in that list worth including?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['nothing'], wanted one of ['entity-activity-profile', 'entity-record-map', 'group-record-map', 'interaction-pairs', 'matrix-profile', 'plot-indicator-profile']
- `rows`: no table, list or row language where the user asked for specifics
- `traceable`: no survey named and no path to the rows

```
I need to resolve what “that list” means before I test threat status. Are you asking about the tree species you are considering for planting, or the animal-moved tree set we were trying to narrow down?
```

### c5-what-to-replant / t5

User: Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `rows`: no table, list or row language where the user asked for specifics

```
General ecological context: For a 30-year self-assembling stand, the first shortlist should favour native canopy and subcanopy trees with animal-dispersed fruit, and avoid known invasive fillers even if they are common in the records. A first shortlist is only a draft until it is checked against nearby mother trees, nursery availability, and what is regenerating on site already. From the data this site has, tree records are strong enough to anchor a draft list, but this map is an inventory, not a full planting checklist, and record counts are not directly comparable across surveys. My shortlist is: from this site’s own records, `Vateria indica` and `Clerodendrum infortunatum`; from general knowledge for wet forest recovery around Valparai, `Artocarpus hirsutus`, `Cullenia exarillata`, `Elaeocarpus tuberculatus`, `Syzygium cumini`, `Syzygium densiflorum`, `Litsea floribunda`, and `Persea macrantha`; and I would explicitly leave out `Maesopsis eminii` even though it is in the records, because it is not a good choice for native forest recovery.
```

### c5-what-to-replant / t6

User: Which of those would fail if the hornbills do not come back?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `rows`: no table, list or row language where the user asked for specifics

```
General ecological context: If a planting mix depends too much on one large frugivore, recovery becomes brittle. For a 30-year target, safer species are the ones likely to be moved by several birds and mammals, not just hornbills. From the data this site has, hornbills are recorded here, but this map is only a record inventory and does not link them to your shortlisted trees, so none of those trees can be ruled in or out as hornbill-dependent from local records alone. Outside this data, the species I would treat as most at risk if hornbills do not return are `Persea macrantha`, `Litsea floribunda`, `Elaeocarpus tuberculatus`, and possibly `Artocarpus hirsutus`; I would treat `Syzygium cumini`, `Syzygium densiflorum`, `Clerodendrum infortunatum`, and probably `Cullenia exarillata` as safer because other frugivores can likely carry them too.
```

### c5-what-to-replant / t7

User: What should I plant first to bring the hornbills in?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `rows`: no table, list or row language where the user asked for specifics

```
General ecological context: To bring hornbills back, the first planting should offer food early and often, not only future timber. In practice that means starting with native fleshy-fruited trees that fruit across different months, then adding slower canopy species behind them. From the data this site has, hornbills are recorded in this landscape, but this map does not show which tree species brought them in. Outside this data, I would plant first for attraction: `Syzygium cumini`, `Syzygium densiflorum`, `Elaeocarpus tuberculatus`, and `Litsea floribunda`; then add `Persea macrantha`, `Artocarpus hirsutus`, `Cullenia exarillata`, and `Vateria indica` as the slower second wave.
```

## c6-what-grows-where - What is growing where: plots on a map, then one plot in detail

Session: `ecoanr-round1-c6-what-grows-where`  |  categories: place, drill-down, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Show me what is growing where across the fragments. I want to see the plots on a map. | **FAIL** | `next_step_in_prose`, `dead_end` | stratified-survey-summary, site-orientation | 2.0 | 31 | **Map** General ecological context: In fragmented rainforest landscapes, what is recorded in each patch often reflects both real habitat differences and where p... |
| t2 | Which plot has the highest share of rainforest species? | **FAIL** | `next_step_in_prose`, `dead_end`, `has_evidence`, `traceable` | plot-indicator-profile, matrix-profile, stratified-survey-summary | 1.5 | 34 | From the data this site has, I cannot identify a highest-plot value for rainforest-species share from the available plot summaries. I checked the restoration pl... |
| t3 | Tell me more about that one. What is the stem density there, and what does the canopy look like? | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool`, `has_evidence`, `traceable` | - | 2.0 | 6 | I do not yet have a specific plot to inspect. In the last step, the data here did not identify any one plot as having the highest rainforest-species share. Whic... |
| t4 | Where does that number come from? Show me the rows. | **FAIL** | `next_step_in_prose`, `dead_end` | visual-explain | 1.4 | 20 | This is for the busiest square on that map, because no specific point or square was identified in your question. In that 1.1 km square spanning 10.360–10.370 N ... |
| t5 | How does it compare against the benchmark plots? | **FAIL** | `next_step_in_prose`, `dead_end` | stratified-survey-summary | 1.0 | 18 | From the data this site has, I read your question as a comparison with the benchmark category in the bird recovery study, and this map-table view shows 69 surve... |
| t6 | Is that plot an outlier, or is it typical of the restored ones? | **FAIL** | `next_step_in_prose`, `dead_end` | stratified-survey-summary | 1.0 | 18 | From the data this site has, I read “that plot” as a restored-site comparison in the bird recovery study, but this map and table do not support calling one plot... |

### c6-what-grows-where / t1

User: Show me what is growing where across the fragments. I want to see the plots on a map.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
**Map** General ecological context: In fragmented rainforest landscapes, what is recorded in each patch often reflects both real habitat differences and where people have surveyed more. So this map is best read first as where the records are concentrated, then followed by a check on survey effort. From the data this site has, this map shows recorded observations across the fragments: 42,348 records covering 962 kinds of plants and animals across 302 squares inside the site boundary. It shows where records are dense, not where something is absent, and not a direct measure of what is growing most.
```

### c6-what-grows-where / t2

User: Which plot has the highest share of rainforest species?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
From the data this site has, I cannot identify a highest-plot value for rainforest-species share from the available plot summaries. I checked the restoration plots data for a plot-wise comparison, but this site does not currently hold that rainforest-share table in a usable form, so there is no defensible plot ranking to report from these records.
```

### c6-what-grows-where / t3

User: Tell me more about that one. What is the stem density there, and what does the canopy look like?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['nothing'], wanted one of ['cell-feature-map', 'group-record-map', 'matrix-profile', 'metric-time-series', 'plot-indicator-profile']
- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
I do not yet have a specific plot to inspect. In the last step, the data here did not identify any one plot as having the highest rainforest-species share. Which plot do you want me to open: name the plot, or point to it on the map?
```

### c6-what-grows-where / t4

User: Where does that number come from? Show me the rows.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
This is for the busiest square on that map, because no specific point or square was identified in your question. In that 1.1 km square spanning 10.360–10.370 N and 76.990–77.000 E, the number is a straight count of 3,300 recorded observations from the bird recovery study, and 12 example rows shown behind it include rows 1554 to 1565 with names such as *Clerodendrum infortunatum*, *Apollonias arnottii*, *Ardisia pauciflora* and *Litsea bourdillonii*. The data here can show example rows behind that square, but not dump all 3,300 rows in this reply.
```

### c6-what-grows-where / t5

User: How does it compare against the benchmark plots?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
From the data this site has, I read your question as a comparison with the benchmark category in the bird recovery study, and this map-table view shows 69 surveyed sites across 3 site types with 460 recorded visits. It is useful for seeing how detections and survey effort differ between the benchmark plots and the other plot types, but it is only a descriptive comparison: these are records per visit, not population size, and not proof that the benchmark condition caused the difference.
```

### c6-what-grows-where / t6

User: Is that plot an outlier, or is it typical of the restored ones?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
From the data this site has, I read “that plot” as a restored-site comparison in the bird recovery study, but this map and table do not support calling one plot an outlier or typical. They show restored, benchmark and other site types across 69 surveyed sites with 460 visits, and are useful for descriptive comparison only; they do not give a defensible plot-level outlier test or population-level verdict.
```

## c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots

Session: `ecoanr-round1-c7-survey-budget`  |  categories: value-of-information, coverage-gap, uncertainty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Say I get twenty drone days next season. Where should I fly to learn the most? | **FAIL** | `next_step_in_prose`, `dead_end` | coverage-versus-effort | 1.8 | 20 | General ecological context: With fixed drone time, you usually learn most by flying the mismatch zones, where biodiversity records are present but survey effort... |
| t2 | What are you basing that on? Places we have never looked, or places where you think something is happening? | **FAIL** | `next_step_in_prose`, `dead_end`, `join_rule_disclosed` | visual-explain | 0.65 | 17 | It is based on mismatch, not on me inferring a biological hotspot. This explanation is for the biggest square on that map because no specific square was identif... |
| t3 | If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover. | **FAIL** | `next_step_in_prose`, `dead_end`, `honest_gap` | entity-record-map | 1.3 | 21 | General ecological context: Yes, the answer can change with hyperspectral data. For invasive cover, the best flights are usually where the target plant is alrea... |
| t4 | And if it is just me and two field assistants for thirty days on foot? | **FAIL** | `next_step_in_prose`, `dead_end` | coverage-versus-effort | 1.4 | 16 | General ecological context: On foot, you usually learn most by revisiting the mismatch areas rather than trying to cover everything. A small team can check habi... |
| t5 | Which of the three buys me the most for a restoration decision in the next two years? | **FAIL** | `next_step_in_prose`, `dead_end` | method-catalog | 1.3 | 18 | General ecological context: For a restoration decision on a two-year horizon, the best option is usually the one that reduces the biggest uncertainty you alread... |
| t6 | Show me the gap map. Where is coverage thinnest relative to how much is going on there? | **FAIL** | `next_step_in_prose`, `dead_end` | coverage-versus-effort | 1.05 | 13 | From the data this site has, this is the gap map: records occur in 302 squares inside the site's boundary, but explicit effort is documented in only 42. The thi... |
| t7 | Rank the top five places, with a reason for each that I could put in a proposal. | **FAIL** | `jargon`, `rows` | compile-scientific-algebra-9b, visual-explain | 1.9 | 28 | From the data this site has, the top five proposal priorities on this gap map are: 1. the 1.1 km square spanning 10.360–10.370 N and 76.990–77.000 E, because it... |

### c7-survey-budget / t1

User: Say I get twenty drone days next season. Where should I fly to learn the most?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: With fixed drone time, you usually learn most by flying the mismatch zones, where biodiversity records are present but survey effort is thin or uneven. That helps separate true gaps on the ground from gaps caused only by where people have already looked. From the data this site has, records are spread across 302 squares inside the site's boundary, but explicit survey effort is documented in only 42 squares. Use this map to prioritise squares that show records with little or no documented effort, because those are the best places to reduce uncertainty with your twenty drone days. Where effort is not documented, the map can show coverage, but it cannot tell you absence or survey-adjusted rates.
```

### c7-survey-budget / t2

User: What are you basing that on? Places we have never looked, or places where you think something is happening?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `join_rule_disclosed`: asked how two things were matched, did not say

```
It is based on mismatch, not on me inferring a biological hotspot. This explanation is for the biggest square on that map because no specific square was identified: there the map is simply counting recorded observations from the restoration bird study, and comparing that kind of coverage against where explicit survey effort was written down elsewhere. So my suggestion meant “fly where records exist but effort is poorly documented or thin”, not “fly where the data proves something special is happening”, and also not just “places never looked at” because some squares have records without matching effort records.
```

### c7-survey-budget / t3

User: If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `honest_gap`: neither a plain statement of what is missing nor a real figure

```
General ecological context: Yes, the answer can change with hyperspectral data. For invasive cover, the best flights are usually where the target plant is already recorded across enough places to learn its spectral pattern, and where nearby unsampled areas could then be checked for spread. From the data this site has, I would shift from general gap-filling to places where `Maesopsis eminii` is already recorded, because that is the closest direct evidence here for invasive cover. This map shows many such records, including many inside the site, but these are occurrence points only: they do not by themselves show cover, absence, or spread rate. One useful follow-up: do you want to treat `Maesopsis eminii` as the invasive target, or do you mean invasive plants in general?
```

### c7-survey-budget / t4

User: And if it is just me and two field assistants for thirty days on foot?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: On foot, you usually learn most by revisiting the mismatch areas rather than trying to cover everything. A small team can check habitat condition, invasive patches, and false gaps much better than a sensor can, but only across a smaller area. From the data this site has, I would still prioritise squares inside the site's boundary that show records but little or no documented effort, because your team can test whether those are real gaps or just weak survey history. With 302 squares showing records and only 42 with explicit effort, this map supports a targeted foot plan, but where effort is missing it still cannot tell absence or survey-adjusted rates.
```

### c7-survey-budget / t5

User: Which of the three buys me the most for a restoration decision in the next two years?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: For a restoration decision on a two-year horizon, the best option is usually the one that reduces the biggest uncertainty you already have, not the fanciest sensor. Here, the main uncertainty is still uneven survey coverage. From the data this site has, the strongest buy is the 30-day foot survey, because the evidence we do have points to a large coverage-versus-effort gap, and that is the most direct thing to reduce before choosing restoration action. This comparison view could not find a ready method card for your exact question, so this is still a cautious decision: hyperspectral becomes more valuable only if invasive cover is the near-term decision bottleneck, while the general drone option stays weaker for a two-year restoration choice than targeted ground checking.
```

### c7-survey-budget / t6

User: Show me the gap map. Where is coverage thinnest relative to how much is going on there?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
From the data this site has, this is the gap map: records occur in 302 squares inside the site's boundary, but explicit effort is documented in only 42. The thinnest coverage relative to apparent activity is where the map shows records without matching effort records, but where effort is missing this map cannot tell absence or survey-adjusted rates.
```

### c7-survey-budget / t7

User: Rank the top five places, with a reason for each that I could put in a proposal.

- `jargon`: capability, site pack
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, the top five proposal priorities on this gap map are: 1. the 1.1 km square spanning 10.360–10.370 N and 76.990–77.000 E, because it has the strongest recorded activity on this view; 2. 10.340–10.350 N and 76.890–76.900 E, because it is the next strongest concentration of records; 3. 10.340–10.350 N and 76.930–76.940 E, because many records are already clustered there. Then 4. 10.350–10.360 N and 76.990–77.000 E, because it is another high-activity square that can quickly reduce uncertainty; and 5. 10.350–10.360 N and 76.930–76.940 E, because it is still a strong recorded cluster worth checking before restoration decisions. This ranking comes from the biggest record concentrations on the map, not from proof of ecological importance, and where effort is missing the map cannot tell absence or survey-adjusted rates. ### Scientific analysis **Scientific question sent to 9B** > Which five squares inside the site's boundary show the highest recorded coverage relative to documented survey effort in the stored coverage-versus-effort result? **How 9B expressed the question scientifically** No valid Algebra tree was returned.. **What Idli Insight executed** Execut
```

## c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here

Session: `ecoanr-round1-c8-monitoring-plan`  |  categories: design, data-request, gap-honesty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here. | **FAIL** | `next_step_in_prose`, `dead_end`, `traceable` | site-orientation | 1.5 | 25 | This map shows where this site already has records; use those better-covered cells to place matched ANR and active-planting plots, so the comparison is fair and... |
| t2 | What can I reuse as a baseline instead of starting from scratch? | **FAIL** | `next_step_in_prose`, `dead_end` | coverage-versus-effort | 1.9 | 13 | General ecological context: For restoration monitoring, the strongest baseline is usually existing measured plots or surveys with clear effort, not just scatter... |
| t3 | What is the minimum I have to keep collecting so the old data stays comparable? | **FAIL** | `next_step_in_prose`, `dead_end` | method-catalog | 1.25 | 13 | General ecological context: To keep old and new restoration data comparable, the minimum is to hold the measurement method, plot design, timing, and effort stea... |
| t4 | What is missing entirely, that I would have to start measuring from zero? | **FAIL** | `next_step_in_prose`, `dead_end` | method-catalog | 1.4 | 14 | General ecological context: Old biodiversity and vegetation records can give you context, but they rarely contain the intervention details needed for a clean AN... |
| t5 | How many plots, and how many visits a year, to have a real chance of detecting a difference? | **FAIL** | `jargon` | coverage-versus-effort, compile-scientific-algebra-9b | 2.0 | 24 | General ecological context: In restoration monitoring, the number of plots matters more than very frequent visits once you have seasonal coverage. A practical d... |
| t6 | Write it up as a one page plan I can hand to my team. | PASS | - | - | 1.85 | 18 | **Three-Year Monitoring Plan: ANR vs Active Planting** **Purpose** From the data this site has, we want a fair test of whether assisted natural regeneration (AN... |
| t7 | And a list of the data I would need to request from the other groups working here. | **FAIL** | `next_step_in_prose`, `dead_end` | method-catalog | 1.85 | 17 | From the data this site has, there are method notes you can align to, but this table is only a guide to analysis designs, not a finished comparison result. Ask ... |

### c8-monitoring-plan / t1

User: Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `traceable`: no survey named and no path to the rows

```
This map shows where this site already has records; use those better-covered cells to place matched ANR and active-planting plots, so the comparison is fair and cheaper to run. For 3 years, take a baseline now, then monitor every 6 months for native seedling recruitment, survival, height, canopy closure, weeds, fire/grazing damage, and cost per surviving native stem; add one annual bird or frog check as a broader recovery signal. What should “beats” mean here: stronger native regeneration, lower cost per success, or faster canopy/carbon recovery?
```

### c8-monitoring-plan / t2

User: What can I reuse as a baseline instead of starting from scratch?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: For restoration monitoring, the strongest baseline is usually existing measured plots or surveys with clear effort, not just scattered sightings. If effort is documented, you can compare change over time; if not, you can mostly use it only for context and targeting. From the data this site has, you can reuse the 42 cells with documented survey effort as your real baseline. The wider 302 cells with records are still useful for context and plot placement, but not for claiming absence or fair rate comparisons where effort was not recorded.
```

### c8-monitoring-plan / t3

User: What is the minimum I have to keep collecting so the old data stays comparable?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: To keep old and new restoration data comparable, the minimum is to hold the measurement method, plot design, timing, and effort steady. If any one of these shifts, apparent change can come from method drift, not ecological change. From the data this site has, there are method notes you can reuse, but this table is a guide to analysis designs, not a finished result by itself. The minimum to keep collecting is the same plot layout, the same field measures, the same season, and the same survey effort as the earlier work; if you change any of these, keep a small overlap period where both old and new methods are run together.
```

### c8-monitoring-plan / t4

User: What is missing entirely, that I would have to start measuring from zero?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
General ecological context: Old biodiversity and vegetation records can give you context, but they rarely contain the intervention details needed for a clean ANR-versus-planting test. For that comparison, treatment history and repeated survival data are usually the first big gaps. From the data this site has, the method notes show analysis designs, but not a ready-made ANR-versus-planting baseline by themselves. What you will likely need to start from zero is treatment tracking for each plot, repeated seedling or sapling survival by treatment, management inputs like weeding and protection, and cost records in the same format across both approaches.
```

### c8-monitoring-plan / t5

User: How many plots, and how many visits a year, to have a real chance of detecting a difference?

- `jargon`: capability, site pack

```
General ecological context: In restoration monitoring, the number of plots matters more than very frequent visits once you have seasonal coverage. A practical design usually needs enough matched plots in each treatment, then repeat visits at the same time each year. From the data this site has, only 42 cells have documented survey effort, so those are the safest pool for placing comparable monitoring plots. The remaining data gap is that this site does not yet show the treatment-wise variation needed to calculate a defensible minimum sample size, so any number now would be a planning rule, not an evidence-based estimate; as a practical minimum, start with 15-20 matched plots in ANR and 15-20 in planting, with 2 visits a year at fixed seasons. ### Scientific analysis **Scientific question sent to 9B** > Using the site's documented survey effort and method notes, what minimum three-year monitoring design in plots per treatment and visits per year would give a defensible chance to detect a difference between assisted natural regeneration and active planting? **How 9B expressed the question scientifically** No valid Algebra tree was returned.. **What Idli Insight executed** Execution s
```

### c8-monitoring-plan / t7

User: And a list of the data I would need to request from the other groups working here.

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface

```
From the data this site has, there are method notes you can align to, but this table is only a guide to analysis designs, not a finished comparison result. Ask other groups for the same core fields and timing, so their records can sit beside yours without breaking comparability. **Data to request from other groups** - Plot list with unique plot ID, treatment type, start date, and exact location - Plot design: plot size, subplot layout, tagging method, and revisit schedule - Baseline vegetation before treatment: existing seedlings, saplings, canopy cover, weed cover, disturbance - Treatment details: ANR actions done, planting density, species planted, source of planting stock - Survival records by visit: live, dead, missing, damaged - Growth records by visit: height, stem diameter if taken, canopy closure - Management effort: weeding, mulching, guarding, soil work, fire line work - Damage records: grazing, fire, drought, trampling, invasive plants, pest or disease notes - Cost records in one format: labour days, materials, transport, contractor or staff time - Survey method sheet: who collected, when, in which season, and with what field definitions - Any bird or frog monitoring lin
```

