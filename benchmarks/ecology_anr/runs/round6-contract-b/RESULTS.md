# Ecology ANR bench - results

Run: `round6-contract-b`  |  endpoint: `http://172.17.0.1:7012`  |  model: `idli-insight-valparai`  |  started: 2026-07-26T03:45:59+05:30

**45/66 turns pass (68%)**, 2/10 conversations clean, mean language score 1.84/2, median latency 22.4s (max 339.9s), 1 turns retried.

## How this number was baselined

- ROUTING EXPECTATIONS RE-BASELINED after the bridge shipped `interaction-pairs` and `survey-priority-squares` (commit 1a57eb9). The rule applied: widen an existing `capabilities_any` list only where the newly-chosen tool genuinely answers the question better; never narrow one, and never add a routing requirement to a turn that did not already have one. Where the model simply picked a worse tool, the turn was left failing.
- WIDENED (5 turns, routing is genuinely right): c5/t2 and c5/t3 now accept `interaction-pairs` -- it names the recorded tree-animal pairs, which is exactly what 'who disperses what' asks for, where `interaction-map` only maps declared association types. c5/t4 now accepts `entity-activity-profile` and `interaction-pairs` -- it answered with Heynea trijuga, 237 records in 45 squares, 2002-2022, tied to the threatened-tree records. c7/t1 and c7/t6 now accept `survey-priority-squares` -- it ranks by the records-versus-effort gap and names squares by real places, which is the question.
- LEFT FAILING (5 turns, the tool picked was worse): c1/t6 ran `stratified-survey-summary` for 'show me the rows behind the mammal counts', could not produce a row, and offered the mapped-records route in its own next sentence -- a tool that could answer was available and not used. c2/t3 and c2/t5 never called `stratified-survey-summary` with the declared `Site_type` category that holds the split being asked for. c3/t3 ran `method-catalog` for a question about canopy cover and plant-community plots. c4/t5 ran `entity-activity-profile` and then asserted there was no canopy comparison, without querying the ten canopy and structure metrics this index holds (`canopy_cover`, `canopy_openness`, `basal_area`, `tree_height` among them).
- Re-grading the bridge's own round5 transcript under these corrected expectations moves it from 27/52 to 31/52 and `right_tool` from 58% to 79%. That is the size of the harness drift, isolated from any product change.
- GRADER CALIBRATED TWICE, both times against transcripts rather than intuition. Round 1: `honest_gap` and `confidence` were widened after reading the failures showed 'there is still no recorded lantana name here' and 'I cannot call that a real plot-type effect yet' were being missed. Round 2: `join_rule_disclosed` was widened (a join is also disclosed by saying what the table actually records and how unequal the watching behind it was), and the gap checks were made conditional -- where the product now finds the data and answers with a figure, answering is better than confessing, so `honest_gap` passes on evidence and `names_alternative` binds only when absence was actually claimed. Uncorrected, round 2 scores 37/66; corrected, 46/66. Both numbers are stated here on purpose.

## Pass rate by dimension

| Check | Pass rate | n |
| --- | --- | --- |
| `join_rule_disclosed` | 50% | 6 |
| `rows` | 70% | 23 |
| `right_tool` | 83% | 29 |
| `has_evidence` | 85% | 34 |
| `traceable` | 88% | 33 |
| `confidence` | 94% | 18 |
| `multi_turn` | 98% | 57 |
| `brevity` | 100% | 1 |
| `dead_end` | 100% | 66 |
| `gap_or_answer` | 100% | 5 |
| `general_knowledge_labelled` | 100% | 2 |
| `honest_gap` | 100% | 7 |
| `jargon` | 100% | 66 |
| `names_alternative` | 100% | 4 |
| `next_step_in_prose` | 100% | 66 |
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
| c1-what-is-here - What is even here, and what can I trust for a trend | 50% |
| c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots | 71% |
| c3-lantana - Lantana keeps coming back: an honest gap and how to test it | 83% |
| c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule | 83% |
| c5-what-to-replant - What to replant for a forest that keeps itself going | 43% |
| c6-what-grows-where - What is growing where: plots on a map, then one plot in detail | 100% |
| c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots | 43% |
| c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here | 100% |
| c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs | 71% |
| c10-budget-monitoring-plan - Three years of monitoring against a real budget | 43% |

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| comparison | 71% |
| coverage-gap | 43% |
| data-request | 100% |
| denominators | 71% |
| design | 64% |
| drill-down | 100% |
| gap-honesty | 92% |
| mechanism | 83% |
| method-disclosure | 77% |
| network | 57% |
| orientation | 50% |
| place | 100% |
| relationship | 83% |
| seed-fate | 43% |
| study-design | 83% |
| traceability | 78% |
| trust | 62% |
| uncertainty | 43% |
| value-of-information | 43% |

## c1-what-is-here - What is even here, and what can I trust for a trend

Session: `ecoanr-round6-contract-b-c1-what-is-here`  |  categories: orientation, trust, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have just taken over restoration monitoring for the Anamalai rainforest fragments. Before I plan anything I need to know what long-term monitoring actually exists here, and how far back it goes. | PASS | - | site-orientation, coverage-versus-effort, method-catalog | 2.0 | 43 | From the data this site has, there are 9 documented monitoring or analysis routes, including repeat tree-plot measures, restoration plot comparisons, bird-check... |
| t2 | Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot? | **FAIL** | `has_evidence`, `traceable` | metric-time-series | 2.0 | 23 | From the data this site has, the trend route does not recognise “monitoring streams” as a plottable measure. But it does show that repeatable trend-ready measur... |
| t3 | Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking. | PASS | - | metric-time-series, stratified-survey-summary | 2.0 | 340 | From the data this site has, the bird recovery monitoring is the clearest repeated survey stream: it runs from 2002 to 2020, with 460 documented visits and 6,90... |
| t4 | So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why? | **FAIL** | `traceable` | method-catalog | 2.0 | 19 | From the data this site has, I would stand behind change claims most readily for sampled adult-tree count, basal area, and aboveground carbon per hectare. Next ... |
| t5 | Where is the weakest link in that? Where would a reviewer poke holes? | PASS | - | method-catalog | 1.75 | 14 | The remaining data gap is 2024 coverage: this table does not show that the same monitoring stream was actually sampled through 2024. So that is the first hole a... |
| t6 | Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like. | **FAIL** | `right_tool` | entity-activity-profile, visual-explain | 1.35 | 44 | From the data this site has, I opened the 2024 mammal point: it counts 637 dated records from the survey `Mammal occurrence records, 2024`. A single row here is... |

### c1-what-is-here / t2

User: Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot?

- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
From the data this site has, the trend route does not recognise “monitoring streams” as a plottable measure. But it does show that repeatable trend-ready measures exist. These include aboveground carbon, basal area, canopy cover, canopy height, canopy openness, adult tree count per plot, adult tree species richness. Daily weather measures such as temperature and rainfall. If you want, I can open one of those as a time trend and show how far back it goes.
```

### c1-what-is-here / t4

User: So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why?

- `traceable`: no survey named and no path to the rows

```
From the data this site has, I would stand behind change claims most readily for sampled adult-tree count, basal area, and aboveground carbon per hectare. Next for plot diversity by habitat, origin, conservation status. Dispersal traits, because those are the only two documented routes here with zero extra checks before analysis. I would be more cautious with occupancy, reporting-rate trends, similarity to reference plots. Canopy-response claims, because those need several more conditions and this table is only a methods catalogue, not a finished result. The remaining data gap is 2024 coverage: this table does not show which streams actually run through 2024. So I would not defend a 2015 to 2024 change claim until we confirm the end year for the chosen stream. If you want, I can now check which of those two strongest routes actually have data extending to 2024.
```

### c1-what-is-here / t6

User: Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like.

- `right_tool`: ran ['entity-activity-profile', 'visual-explain'], wanted one of ['coverage-versus-effort', 'entity-record-map', 'group-record-map', 'matrix-profile']

```
From the data this site has, I opened the 2024 mammal point: it counts 637 dated records from the survey `Mammal occurrence records, 2024`. A single row here is a dated sighting with a species name and a count, for example row 637 on 2024-01-06 for Jungle-striped squirrel with count 1, or rows 628 and 629 on 2024-01-23 for Gaur with counts 27 and 34. These are records, not abundance estimates, so more rows can also mean more survey effort. If you want, I can pull the same kind of row-level view for 2015 or 2020–23 so you can compare how consistent the records are.
```

## c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots

Session: `ecoanr-round6-contract-b-c2-does-restoration-work`  |  categories: comparison, denominators, trust

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | We have been doing assisted natural regeneration in these fragments for years. Is there anything here that compares restored plots against ones we left to regrow on their own? | PASS | - | stratified-survey-summary | 1.85 | 26 | From the data this site has, there is a comparison view in the restoration opportunities study. But it splits sites as `Benchmark` and `Fragment`, not a clean a... |
| t2 | Good. How do the birds compare across restored, naturally regenerating and benchmark plots? | PASS | - | stratified-survey-summary | 2.0 | 12 | From the data this site has, the bird recovery survey does compare all three: benchmark, restored, and unrestored plots. Benchmark plots have 23 sites and 152 v... |
| t3 | How many plots in each of those three, and how many times was each visited? | **FAIL** | `rows` | stratified-survey-summary | 2.0 | 13 | From the data this site has, the bird recovery survey has 23 benchmark plots with 152 visits, 23 restored plots with 154 visits. 23 unrestored plots with 154 vi... |
| t4 | Is that difference real, or could it just be that people spent more time in the benchmark plots? | PASS | - | compile-scientific-algebra-9b, visual-explain | 1.8 | 33 | From the data this site has, it does not look like the benchmark difference is only because people spent more time there. Benchmark had 2,280 survey minutes, sl... |
| t5 | Which bird species are driving the gap? I care about the rainforest specialists, not the generalists. | **FAIL** | `right_tool`, `rows` | local-site-evidence-search | 2.0 | 340 | From the data this site has, I can compare the three plot types in the bird point-count survey. But I have not yet established a species-level `rainforest speci... |
| t6 | If I had to put one sentence in a report about whether restoration is working here, what would you let me say? | PASS | - | visual-explain | 2.0 | 17 | From the data this site has, the safest report sentence is: restored plots show higher bird detections per visit than unrestored plots. But still remain below b... |
| t7 | And what would you not let me say? | PASS | - | visual-explain | 2.0 | 11 | From the data this site has, I would not let you say restoration caused bird recovery here. This site does not have a causal test in this result, and it does no... |

### c2-does-restoration-work / t3

User: How many plots in each of those three, and how many times was each visited?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, the bird recovery survey has 23 benchmark plots with 152 visits, 23 restored plots with 154 visits. 23 unrestored plots with 154 visits. This is a survey-effort summary, not a treatment-effect result. If you want, I can check whether those visits were spread evenly across years or seasons.
```

### c2-does-restoration-work / t5

User: Which bird species are driving the gap? I care about the rainforest specialists, not the generalists.

- `right_tool`: ran ['local-site-evidence-search'], wanted one of ['entity-record-map', 'group-record-map', 'matrix-profile', 'stratified-survey-summary']
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, I can compare the three plot types in the bird point-count survey. But I have not yet established a species-level `rainforest specialist` label inside that same split. The site does hold rainforest-bird metrics elsewhere, but that is not yet the same as a species list driving this gap. Do you want me to treat `rainforest specialists` as the site’s rainforest-bird classification, or do you want only named forest-interior species from the point-count survey?
```

## c3-lantana - Lantana keeps coming back: an honest gap and how to test it

Session: `ecoanr-round6-contract-b-c3-lantana`  |  categories: gap-honesty, study-design, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Why does lantana keep coming back after we weed it? | PASS | - | entity-activity-profile | 1.75 | 24 | From general knowledge: Lantana usually comes back after weeding because cut stems re-sprout, the soil seed bank stays alive. New seed keeps arriving from birds... |
| t2 | Do you have anything at all on lantana at this site? Even just where it has been recorded? | PASS | - | local-site-evidence-search, entity-record-map | 2.0 | 13 | I read “lantana” as *Lantana camara*, which this site has 36 records of. From the data this site has, 36 source-linked records are available for *Lantana camara... |
| t3 | So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots. | **FAIL** | `right_tool` | metric-time-series, stratified-survey-summary | 2.0 | 31 | From general knowledge: Canopy cover can be a rough proxy for light and disturbance, but it is not a direct proxy for lantana recovery. Repeat plant plots are u... |
| t4 | If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here? | PASS | - | method-catalog | 1.85 | 334 | From the data this site has, there is one source-linked shade-response method, with 6 required inputs and 5 checks. But it is a study design, not a fitted resul... |
| t5 | How many of the plant community plots could I revisit, and where are they? | PASS | - | stratified-survey-summary, coverage-versus-effort | 2.0 | 22 | From the data this site has, the plant community structure survey holds 110 named plots from 2003, spread across 5 map squares. So those are the plots you could... |
| t6 | Draft the data request for me: exactly what I would ask my field team to bring back. | PASS | - | method-catalog | 1.85 | 22 | From the data this site has, there is one shade-response study design here, with 6 required inputs and 5 checks. It is a study design, not a finished result, so... |

### c3-lantana / t3

User: So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots.

- `right_tool`: ran ['metric-time-series', 'stratified-survey-summary'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'plot-indicator-profile']

```
From general knowledge: Canopy cover can be a rough proxy for light and disturbance, but it is not a direct proxy for lantana recovery. Repeat plant plots are usually better if you want to track comeback after weeding. From the data this site has, canopy cover is available as 5 monthly values from the restoration opportunities work and another plot study. So it can serve only as a coarse stand-in. The plant community structure survey is a better plot-based stand-in here: it holds 3,744 records across 110 named plots in 2003, with 880 measurement readings. But this view does not summarise those plots cleanly. If you want, I can compare the lantana records with documented survey effort.
```

## c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule

Session: `ecoanr-round6-contract-b-c4-natives-suppress`  |  categories: relationship, method-disclosure, mechanism

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Different angle. Are there native species here that turn up where lantana does not? | PASS | - | entity-activity-profile, group-record-map, compile-scientific-algebra-9b, co-occurrence-map | 2.0 | 74 | From the data this site has, yes: native records span 104 squares inside this site’s boundary, while lantana was recorded in 15. All 15 of those are shared, so ... |
| t2 | How exactly did you match those two things up? Same plot and same year, or just the same general area? | PASS | - | visual-explain | 2.0 | 18 | It was matched at the same 1.1 km square, not the same plot. For the map I showed, the rule was: lantana and native records count as together if both were writt... |
| t3 | That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with? | PASS | - | local-site-evidence-search, stratified-survey-summary, compile-scientific-algebra-9b | 1.35 | 55 | From the data this site has, the nearest plot-like unit exposed here is 132 surveyed sites with 264 visits in the restoration opportunities study, not a clean p... |
| t4 | What is the mechanism you would bet on here - shade, leaf litter, root competition? | PASS | - | method-catalog | 2.0 | 18 | From the data this site has, I would not defend any one mechanism yet: this particular methods view did not return a site-backed causal test for lantana. So the... |
| t5 | Is there anything in the canopy or tree structure data that supports the shade story? | PASS | - | method-catalog, plot-indicator-profile | 1.5 | 22 | From the data this site has, there is canopy data that is relevant to a shade story: canopy openness is recorded for 1,289 plots in the tree and habitat structu... |
| t6 | Give me three native species to trial as a shade crop, and say how confident you are in each one. | **FAIL** | `rows` | group-record-map, entity-activity-profile | 2.0 | 45 | From general knowledge: I am reading “shade crop” here as native shade-tree candidates, not proof of agronomic performance. From the data this site has, my thre... |

### c4-natives-suppress / t6

User: Give me three native species to trial as a shade crop, and say how confident you are in each one.

- `rows`: no table, list or row language where the user asked for specifics

```
From general knowledge: I am reading “shade crop” here as native shade-tree candidates, not proof of agronomic performance. From the data this site has, my three would be Vateria indica with high confidence because it has 802 records across 46 squares and turns up in the threatened-tree inventory, plant community structure, restoration opportunities, bird recovery, and tree and habitat structure surveys. Cullenia exarillata with medium-high confidence because it has 398 records across 52 squares in the restoration, structure, threatened-tree and seed-predation surveys. And Palaquium ellipticum with medium-high confidence because it has 397 records across 46 squares in the plant community structure, threatened-tree, tree and habitat structure, bird recovery, and restoration surveys. These are still records, not trial results or effort-normalised performance. So my confidence is about how well each species is supported in this site’s data, not about proven shade yield. If you want, I can rank these three by which one has the strongest regeneration evidence.
```

## c5-what-to-replant - What to replant for a forest that keeps itself going

Session: `ecoanr-round6-contract-b-c5-what-to-replant`  |  categories: design, network, seed-fate

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am putting together a planting list for a two hectare gap. I want a forest that regenerates on its own in thirty years, not a plantation. Where do I start? | PASS | - | site-orientation | 1.3 | 21 | From the data this site has, start by treating your 2-hectare gap as part of a larger forest mosaic, not as an empty patch: this map shows 42,348 source-linked ... |
| t2 | Which trees here actually get their seed moved by animals, and by which animals? | **FAIL** | `has_evidence`, `rows` | interaction-pairs, interaction-map | 1.5 | 23 | From the data this site has, this view does not yet give named seed-dispersal pairs for trees and animals. It says no source-reported frugivory links are indexe... |
| t3 | Of those, which lose most of their seed to predators? I do not want to plant something that never recruits. | PASS | - | interaction-pairs | 2.0 | 18 | From the data this site has, the seed-predation records are strongest for Ormosia travancorica with an unidentified rat (78 records), Cullenia exarillata with I... |
| t4 | Are any threatened species in that list worth including? | **FAIL** | `right_tool` | local-site-evidence-search | 2.0 | 43 | From the data this site has, yes: `Ormosia travancorica`, `Cullenia exarillata`, and `Syzygium rubicundum` are all recorded in the threatened-tree trail invento... |
| t5 | Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge. | **FAIL** | `traceable` | local-site-evidence-search | 2.0 | 18 | From the data this site has, I would start the shortlist with these 3 because they are already in this site’s own records and also came up in our seed and regen... |
| t6 | Which of those would fail if the hornbills do not come back? | **FAIL** | `rows` | discover-biotic-interactions, group-record-map | 1.5 | 60 | From the data this site has, hornbills are recorded here, but this map is only an inventory of hornbill records from different surveys, not a test of which tree... |
| t7 | What should I plant first to bring the hornbills in? | PASS | - | local-site-evidence-search, group-record-map | 2.0 | 28 | From the data this site has, hornbills are recorded here. Among the species already on our table I would plant `Cullenia exarillata` and `Syzygium rubicundum` f... |

### c5-what-to-replant / t2

User: Which trees here actually get their seed moved by animals, and by which animals?

- `has_evidence`: no figure on a how-much / which / where question
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, this view does not yet give named seed-dispersal pairs for trees and animals. It says no source-reported frugivory links are indexed here, and it did not substitute simple co-occurrence in the same square. If you want, I can check the indexed relation types it does hold next: camera detections at focal seed trees, detections at seed experiments, focal scans on fruiting trees, or observed visits to focal trees.
```

### c5-what-to-replant / t4

User: Are any threatened species in that list worth including?

- `right_tool`: ran ['local-site-evidence-search'], wanted one of ['entity-activity-profile', 'entity-record-map', 'group-record-map', 'interaction-pairs', 'matrix-profile', 'plot-indicator-profile']

```
From the data this site has, yes: `Ormosia travancorica`, `Cullenia exarillata`, and `Syzygium rubicundum` are all recorded in the threatened-tree trail inventory for Valparai and ATR. Of these, `Ormosia travancorica` has the clearest local case for inclusion, because this site also records it in woody regeneration and in restoration quadrats. `Cullenia exarillata` and `Syzygium rubicundum` also have regeneration records here, so they are not showing up only as adult trees. The remaining data gap is that these rows confirm local recording and recruitment evidence. But the search I ran does not itself print the threat category label for each species. If you want, I can pull the source-linked rows behind these three and separate adult-tree records from regeneration records for a planting shortlist.
```

### c5-what-to-replant / t5

User: Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge.

- `traceable`: no survey named and no path to the rows

```
From the data this site has, I would start the shortlist with these 3 because they are already in this site’s own records and also came up in our seed and regeneration checks: 1. `Ormosia travancorica` — from this site’s own records. 2. `Cullenia exarillata` — from this site’s own records. 3. `Syzygium rubicundum` — from this site’s own records. From general knowledge: For a self-assembling forest, I would mix a few large-canopy framework trees, a few animal-dispersed fruiting trees, and a few slower late-successional trees. The aim is not maximum species count on day one; it is to rebuild shade, fruit flow, and recruitment over time. I would add these as provisional candidates from general ecological knowledge, not yet confirmed from this site’s own records in this chat: 4. `Vateria indica` — from general knowledge. 5. `Myristica beddomei` — from general knowledge. 6. `Palaquium ellipticum` — from general knowledge. 7. `Syzygium densiflorum` — from general knowledge. 8. `Litsea floribunda` — from general knowledge. 9. `Drypetes wightii` — from general knowledge. 10. `Dimocarpus longan` — from general knowledge. The remaining data gap is that only the first 3 are tied to this site’
```

### c5-what-to-replant / t6

User: Which of those would fail if the hornbills do not come back?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, hornbills are recorded here, but this map is only an inventory of hornbill records from different surveys, not a test of which tree fails without them. None of our three site-backed trees can yet be shown from this site’s own records to depend specifically on hornbills. From the data this site has, `Ormosia travancorica`, `Cullenia exarillata` and `Syzygium rubicundum` look safer than the rest because the local animal links we saw were rats, chevrotain and civet, not hornbills. From general knowledge: the species I would treat as most likely to weaken if hornbills do not return are `Myristica beddomei`, `Palaquium ellipticum`. Probably `Vateria indica`, because large-fruited forest trees often lose long-distance dispersal first; if you want, I can now cut this to a hornbill-independent planting shortlist.
```

## c6-what-grows-where - What is growing where: plots on a map, then one plot in detail

Session: `ecoanr-round6-contract-b-c6-what-grows-where`  |  categories: place, drill-down, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Show me what is growing where across the fragments. I want to see the plots on a map. | PASS | - | site-orientation | 2.0 | 22 | From the data this site has, this map shows 42,348 source-linked records for 962 entities across 302 cells inside the site boundary. This is a coverage map, not... |
| t2 | Which plot has the highest share of rainforest species? | PASS | - | plot-indicator-profile, visual-explain | 2.0 | 32 | From the data this site has, the highest recorded rainforest-bird share on this map is `1.0`, which means all classified detections in that measurement were rai... |
| t3 | Tell me more about that one. What is the stem density there, and what does the canopy look like? | PASS | - | plot-indicator-profile, visual-explain | 2.0 | 54 | From the data this site has, that top rainforest-bird point is one acoustic measurement row from 12 December 2020. This site does not have a stem-density value ... |
| t4 | Where does that number come from? Show me the rows. | PASS | - | visual-explain | 1.9 | 12 | From the data this site has, that `1.0` comes from one recorded measurement row in the passive acoustic restoration monitoring data. Because no exact point was ... |
| t5 | How does it compare against the benchmark plots? | PASS | - | plot-indicator-profile | 1.7 | 23 | From the data this site has, this rainforest-bird measure is not separated out for benchmark plots in the stored summary. The map holds 257 plots, but the compa... |
| t6 | Is that plot an outlier, or is it typical of the restored ones? | PASS | - | plot-indicator-profile | 1.85 | 13 | From the data this site has, I cannot tell whether that top plot is an outlier among restored plots, because this survey output does not separate the 257 plots ... |

## c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots

Session: `ecoanr-round6-contract-b-c7-survey-budget`  |  categories: value-of-information, coverage-gap, uncertainty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Say I get twenty drone days next season. Where should I fly to learn the most? | PASS | - | survey-priority-squares | 1.8 | 16 | From the data this site has, 102 squares have records but only 22 have documented survey work. The top places to learn the most are near Puduthottam, Sirikundra... |
| t2 | What are you basing that on? Places we have never looked, or places where you think something is happening? | **FAIL** | `join_rule_disclosed` | visual-explain | 1.9 | 18 | This explanation is for the biggest square on that map, because you did not point to one specific place. It is based on the gap between records and documented s... |
| t3 | If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover. | PASS | - | group-record-map | 1.8 | 18 | Yes, it would change. From the data this site has, I would start from squares where introduced plants are already recorded: 1,154 records fall inside this site’... |
| t4 | And if it is just me and two field assistants for thirty days on foot? | **FAIL** | `has_evidence` | survey-priority-squares | 1.8 | 14 | For learning the most on foot, I would still start near Puduthottam, then Sirikundra, Thenmalai, Murugaali-BlackBridge, and Puduthottam_Coffee. The data here sa... |
| t5 | Which of the three buys me the most for a restoration decision in the next two years? | PASS | - | coverage-versus-effort, compile-scientific-algebra-9b | 1.8 | 25 | From the data this site has, the hyperspectral option buys you the most for a restoration decision within two years, because it lines up directly with introduce... |
| t6 | Show me the gap map. Where is coverage thinnest relative to how much is going on there? | **FAIL** | `has_evidence` | survey-priority-squares | 1.8 | 11 | From the data this site has, coverage is thinnest near Puduthottam, then Sirikundra, Thenmalai, Murugaali-BlackBridge, and Puduthottam_Coffee. This map ranks wh... |
| t7 | Rank the top five places, with a reason for each that I could put in a proposal. | **FAIL** | `multi_turn` | - | 1.8 | 10 | From the data this site has, the top five are: 1. Puduthottam, because it has 903 records but only 4 documented survey-work rows; 2. Sirikundra, because it has ... |

### c7-survey-budget / t2

User: What are you basing that on? Places we have never looked, or places where you think something is happening?

- `join_rule_disclosed`: asked how two things were matched, did not say

```
This explanation is for the biggest square on that map, because you did not point to one specific place. It is based on the gap between records and documented survey work: that 1.1 km square has 903 records across 98 subjects, backed here by the tree and habitat structure survey. So it is ranking thin documentation, not guessing that something ecological is happening there. Missing survey-work records can also mean missing paperwork, not only places never visited. If you want, I can show the full coverage-versus-effort map behind that ranking.
```

### c7-survey-budget / t4

User: And if it is just me and two field assistants for thirty days on foot?

- `has_evidence`: no figure on a how-much / which / where question

```
For learning the most on foot, I would still start near Puduthottam, then Sirikundra, Thenmalai, Murugaali-BlackBridge, and Puduthottam_Coffee. The data here says these are the biggest gaps between records and documented survey work, not the places with the richest ecology. Some of that gap may be missing paperwork rather than truly unvisited ground. If you want, I can show the full map of coverage versus survey effort behind this ranking.
```

### c7-survey-budget / t6

User: Show me the gap map. Where is coverage thinnest relative to how much is going on there?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, coverage is thinnest near Puduthottam, then Sirikundra, Thenmalai, Murugaali-BlackBridge, and Puduthottam_Coffee. This map ranks where the data gap is biggest, not where the ecology is richest. Thin effort can also mean thin paperwork rather than no fieldwork. If you want, I can show the full coverage-versus-effort map behind this ranking.
```

### c7-survey-budget / t7

User: Rank the top five places, with a reason for each that I could put in a proposal.

- `multi_turn`: dropped the thread: none of ['coverage', 'place', 'square', 'area'] came back

```
From the data this site has, the top five are: 1. Puduthottam, because it has 903 records but only 4 documented survey-work rows; 2. Sirikundra, because it has 186 records but only 6 effort rows; 3. Thenmalai, because it has 169 records but only 1 effort row; 4. Murugaali-BlackBridge, because it has 316 records but only 1 effort row; 5. Puduthottam_Coffee, because it has 469 records but only 21 effort rows. In proposal language, each is a high-value gap where recorded activity is already substantial but the survey work behind it is thin. So extra effort is likely to reduce uncertainty quickly. This ranks where the data is thinnest, not where the ecology is richest. Some of the gap may be missing paperwork rather than truly missing fieldwork. If you want, I can turn these five into a short proposal paragraph.
```

## c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here

Session: `ecoanr-round6-contract-b-c8-monitoring-plan`  |  categories: design, data-request, gap-honesty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here. | PASS | - | site-orientation | 2.0 | 39 | **3-year design** From the data this site has, you can run a fair comparison because it already holds restoration plots, woody regeneration, tree measurements a... |
| t2 | What can I reuse as a baseline instead of starting from scratch? | PASS | - | coverage-versus-effort | 1.75 | 15 | From the data this site has, the safest baseline to reuse is any plot or square with both observations and documented survey effort. Here, records exist in 302 ... |
| t3 | What is the minimum I have to keep collecting so the old data stays comparable? | PASS | - | method-catalog | 1.7 | 27 | From the data this site has, the minimum is to keep the same core field set that links old and new plot records. The method note closest to this question points... |
| t4 | What is missing entirely, that I would have to start measuring from zero? | PASS | - | method-catalog | 1.75 | 28 | The remaining data gap is this: the site does not yet have a ready ANR-versus-planting comparison record you can run as-is. The closest intervention note still ... |
| t5 | How many plots, and how many visits a year, to have a real chance of detecting a difference? | PASS | - | stratified-survey-summary | 2.0 | 32 | From the data this site has, the closest repeated comparison is the restoration bird survey. It used 23 sites in each category, with 152 visits in the benchmark... |
| t6 | Write it up as a one page plan I can hand to my team. | PASS | - | - | 2.0 | 19 | **3-year monitoring plan: ANR versus active planting** **Purpose** Answer one question: after 3 years, does assisted natural regeneration do better than active ... |
| t7 | And a list of the data I would need to request from the other groups working here. | PASS | - | - | 1.85 | 13 | From the data this site has, ask other groups for the smallest set that will let you compare their plots with yours without breaking comparability. 1. Plot regi... |

## c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs

Session: `ecoanr-round6-contract-b-c9-seed-dispersal-design`  |  categories: network, design, method-disclosure

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am designing the dispersal side of our planting. Who actually disperses what here? Give me the recorded tree and animal pairs, not the general story. | PASS | - | interaction-pairs | 2.0 | 21 | From the data this site has, there are 150 recorded tree-animal pairs across 5,622 rows. The most recorded pair is Yellow-browed Bulbul with *Persea macrantha* ... |
| t2 | Which of the trees you just named have no recorded disperser at all? Those are the ones that worry me. | PASS | - | interaction-pairs | 2.0 | 22 | From the data this site has, none of the trees I just named has zero recorded dispersers: *Persea macrantha* has 31 named pairs across 3,144 rows. *Heynea triju... |
| t3 | How much of that is real absence, and how much is nobody having watched that tree? Tell me how the watching effort differs between trees. | PASS | - | interaction-pairs, visual-explain | 2.0 | 43 | From the data this site has, I cannot split real absence from under-watching cleanly. But the watching effort is clearly uneven between these two trees: *Persea... |
| t4 | Of the dispersers on that list, which ones are actually recorded in the degraded fragments I would be restoring? | PASS | - | stratified-survey-summary, entity-activity-profile, compile-scientific-algebra-9b, local-site-evidence-search | 2.0 | 104 | From the data this site has, the restoration bird survey does include unrestored fragments: 23 unrestored sites with 154 visits. In the local records I checked,... |
| t5 | So if I plant for the dispersers I already have, what does the planting list look like? | **FAIL** | `rows` | interaction-pairs | 1.75 | 34 | From the data this site has, the first-pass planting list for dispersers already recorded here is *Persea macrantha*, *Heynea trijuga*, and *Myristica dactyloid... |
| t6 | Be straight with me. A bird recorded on a fruiting tree is not the same as that bird moving the seed. How much of this list rests on that assumption? | **FAIL** | `join_rule_disclosed` | visual-explain | 2.0 | 19 | From the data this site has, almost all of that shortlist rests on that assumption. The list is built from recorded pairs only: an animal seen at or on a plant,... |
| t7 | What would my team have to record next season to turn these pairs into real dispersal evidence? | PASS | - | method-catalog | 2.0 | 25 | From the data this site has, the current surveys give recorded pairs, not demonstrated seed movement. The site’s own method notes show stronger inference needs ... |

### c9-seed-dispersal-design / t5

User: So if I plant for the dispersers I already have, what does the planting list look like?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, the first-pass planting list for dispersers already recorded here is *Persea macrantha*, *Heynea trijuga*, and *Myristica dactyloides*. *Persea macrantha* is the strongest repeat on these records, *Heynea trijuga* is recorded with Southern Hill Myna and Malabar Grey Hornbill, and *Myristica dactyloides* is recorded with Malabar Grey Hornbill. These figures come from focal-tree frugivore visitation and scan observations, focal-tree seed-predator visits and seed fates, and rainforest tree-animal detections. These are records of animals and trees being seen together, not proof that seed was moved. So this is a practical shortlist, not a demonstrated dispersal plan. If you want, I can map where *Myristica dactyloides* is recorded.
```

### c9-seed-dispersal-design / t6

User: Be straight with me. A bird recorded on a fruiting tree is not the same as that bird moving the seed. How much of this list rests on that assumption?

- `join_rule_disclosed`: asked how two things were matched, did not say

```
From the data this site has, almost all of that shortlist rests on that assumption. The list is built from recorded pairs only: an animal seen at or on a plant, or detected in the same experiment, from focal-tree frugivore visitation and scan observations, focal-tree seed-predator visits and seed fates. Rainforest tree-animal detections; those records do not prove seed movement, and the ranking also reflects where watching was heaviest. So the shortlist is a “trees already used by animals recorded here” list, not a demonstrated seed-dispersal list. If you want, I can now separate it into a safer core list and a weaker assumption-heavy list.
```

## c10-budget-monitoring-plan - Three years of monitoring against a real budget

Session: `ecoanr-round6-contract-b-c10-budget-monitoring-plan`  |  categories: value-of-information, design, coverage-gap

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have thirty field days and twenty drone days a year, for three years. Where do I start? Give me named places, not coordinates. | PASS | - | survey-priority-squares | 1.8 | 21 | From the data this site has, start with Puduthottam, Sirikundra, Thenmalai, Murugaali-BlackBridge and Puduthottam_Coffee. Across the wider map, 102 squares have... |
| t2 | Why those places? Show me the gap between what has been recorded there and what has actually been surveyed. | **FAIL** | `right_tool`, `join_rule_disclosed` | visual-explain | 1.9 | 30 | Because you did not point to one place, this explanation is for the largest square on that view: near Puduthottam, it has 903 records but only 4 rows of documen... |
| t3 | Split the thirty field days across those places for year one. | PASS | - | compile-scientific-algebra-9b | 1.65 | 35 | From the data this site has, I would split year-one field time as: Puduthottam 8 days, Sirikundra 6 days, Thenmalai 5 days, Murugaali-BlackBridge 5 days, and Pu... |
| t4 | What do the drone days add that the field days do not, given what this site already measures? | **FAIL** | `traceable` | local-site-evidence-search, method-catalog | 1.7 | 24 | From the data this site has, I cannot yet show a site-backed drone-versus-field contrast: this route found no matching method card for that comparison. The earl... |
| t5 | What can I already get from the existing surveys, so that I am not paying to collect it twice? | **FAIL** | `has_evidence` | method-catalog, local-site-evidence-search | 1.85 | 21 | From the data this site has, the existing surveys already support adult-tree stock, basal area and above-ground carbon per hectare. Also plot diversity by habit... |
| t6 | If year one comes back and those gap squares are genuinely empty, what changes in year two? | PASS | - | coverage-versus-effort | 1.15 | 15 | From the data this site has, year two should shift from checking those same empty squares again to strengthening effort-backed coverage around them, because rec... |
| t7 | Write me the three year plan, year by year, and tell me what would make me abandon it. | **FAIL** | `rows`, `confidence` | coverage-versus-effort | 1.15 | 19 | From the data this site has, Year 1 is for checking the top gap places and writing effort down properly, because records already sit in 302 cells but explicit s... |

### c10-budget-monitoring-plan / t2

User: Why those places? Show me the gap between what has been recorded there and what has actually been surveyed.

- `right_tool`: ran ['visual-explain'], wanted one of ['cell-estimate-suggest', 'cell-estimate-targets', 'cell-feature-map', 'coverage-versus-effort', 'earth-layer', 'site-orientation', 'survey-priority-squares']
- `join_rule_disclosed`: asked how two things were matched, did not say

```
Because you did not point to one place, this explanation is for the largest square on that view: near Puduthottam, it has 903 records but only 4 rows of documented survey work behind them, drawn here from the tree and habitat structure survey. The same records-versus-survey gap is why Sirikundra (186 vs 6), Thenmalai (169 vs 1), Murugaali-BlackBridge (316 vs 1). Puduthottam_Coffee (469 vs 21) rise up the list. This shows where the data gap is widest, not where the ecology is richest, and some of the gap may be missing survey paperwork rather than no fieldwork. If you want, I can show the full map of coverage versus documented survey effort.
```

### c10-budget-monitoring-plan / t4

User: What do the drone days add that the field days do not, given what this site already measures?

- `traceable`: no survey named and no path to the rows

```
From the data this site has, I cannot yet show a site-backed drone-versus-field contrast: this route found no matching method card for that comparison. The earlier local search was a naming gap, not evidence that the site lacks relevant measurements. From general knowledge: drone days usually add repeatable overhead coverage of canopy, structure and access-constrained ground, while field days add species identity, signs. Measurements taken on the ground; but that is general ecology, not this site’s own evidence. If you want, I can check the site’s admitted methods one by one for canopy profile, tree stocks, plot diversity, occupancy, or effort-adjusted trend. Tell you which of those a drone day could strengthen here.
```

### c10-budget-monitoring-plan / t5

User: What can I already get from the existing surveys, so that I am not paying to collect it twice?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, the existing surveys already support adult-tree stock, basal area and above-ground carbon per hectare. Also plot diversity by habitat, origin, conservation status and dispersal traits; these are the clearest things not to pay to collect twice. The same table also shows methods for community similarity, canopy-response, occupancy, range support and reporting-rate trend. But those need more inputs or checks before they can be used. The local search on your plain-language question hit a naming gap rather than a true absence. This is a methods table, not a measured result from the landscape. If you want, I can turn it into a short “collect / do not recollect” list for your year-one field and drone plan.
```

### c10-budget-monitoring-plan / t7

User: Write me the three year plan, year by year, and tell me what would make me abandon it.

- `rows`: no table, list or row language where the user asked for specifics
- `confidence`: no plain statement of how far to trust it

```
From the data this site has, Year 1 is for checking the top gap places and writing effort down properly, because records already sit in 302 cells but explicit survey effort is documented in only 42. Year 2 is for shifting days away from any gap square that stays empty after proper effort and into nearby under-documented cells. Year 3 is for repeating only the places that now have both records and documented effort, so you can defend trend or rate claims. I would abandon this plan if Year 1 still does not produce clean effort records, because then the main gap remains paperwork rather than ecology, or if the priority squares stay empty after proper survey and the wider coverage-versus-effort map shows better under-documented cells elsewhere. Cells without documented effort cannot support absence claims or effort-adjusted comparisons, so the plan only holds if you fix that in the first year. If you want, I can turn this into a short operational schedule with field days and drone days side by side.
```

