# Ecology ANR bench - results

Run: `round5-split-not-cut`  |  endpoint: `http://172.17.0.1:7012`  |  model: `idli-insight-valparai`  |  started: 2026-07-26T03:10:59+05:30

**39/66 turns pass (59%)**, 0/10 conversations clean, mean language score 1.49/2, median latency 20.9s (max 70.4s), 0 turns retried.

## How this number was baselined

- ROUTING EXPECTATIONS RE-BASELINED after the bridge shipped `interaction-pairs` and `survey-priority-squares` (commit 1a57eb9). The rule applied: widen an existing `capabilities_any` list only where the newly-chosen tool genuinely answers the question better; never narrow one, and never add a routing requirement to a turn that did not already have one. Where the model simply picked a worse tool, the turn was left failing.
- WIDENED (5 turns, routing is genuinely right): c5/t2 and c5/t3 now accept `interaction-pairs` -- it names the recorded tree-animal pairs, which is exactly what 'who disperses what' asks for, where `interaction-map` only maps declared association types. c5/t4 now accepts `entity-activity-profile` and `interaction-pairs` -- it answered with Heynea trijuga, 237 records in 45 squares, 2002-2022, tied to the threatened-tree records. c7/t1 and c7/t6 now accept `survey-priority-squares` -- it ranks by the records-versus-effort gap and names squares by real places, which is the question.
- LEFT FAILING (5 turns, the tool picked was worse): c1/t6 ran `stratified-survey-summary` for 'show me the rows behind the mammal counts', could not produce a row, and offered the mapped-records route in its own next sentence -- a tool that could answer was available and not used. c2/t3 and c2/t5 never called `stratified-survey-summary` with the declared `Site_type` category that holds the split being asked for. c3/t3 ran `method-catalog` for a question about canopy cover and plant-community plots. c4/t5 ran `entity-activity-profile` and then asserted there was no canopy comparison, without querying the ten canopy and structure metrics this index holds (`canopy_cover`, `canopy_openness`, `basal_area`, `tree_height` among them).
- Re-grading the bridge's own round5 transcript under these corrected expectations moves it from 27/52 to 31/52 and `right_tool` from 58% to 79%. That is the size of the harness drift, isolated from any product change.
- GRADER CALIBRATED TWICE, both times against transcripts rather than intuition. Round 1: `honest_gap` and `confidence` were widened after reading the failures showed 'there is still no recorded lantana name here' and 'I cannot call that a real plot-type effect yet' were being missed. Round 2: `join_rule_disclosed` was widened (a join is also disclosed by saying what the table actually records and how unequal the watching behind it was), and the gap checks were made conditional -- where the product now finds the data and answers with a figure, answering is better than confessing, so `honest_gap` passes on evidence and `names_alternative` binds only when absence was actually claimed. Uncorrected, round 2 scores 37/66; corrected, 46/66. Both numbers are stated here on purpose.

## Pass rate by dimension

| Check | Pass rate | n |
| --- | --- | --- |
| `join_rule_disclosed` | 33% | 6 |
| `rows` | 61% | 23 |
| `right_tool` | 79% | 29 |
| `has_evidence` | 79% | 34 |
| `gap_or_answer` | 80% | 5 |
| `traceable` | 88% | 33 |
| `confidence` | 89% | 18 |
| `not_catch_all` | 96% | 25 |
| `multi_turn` | 98% | 57 |
| `dead_end` | 98% | 66 |
| `next_step_in_prose` | 98% | 66 |
| `brevity` | 100% | 1 |
| `general_knowledge_labelled` | 100% | 2 |
| `honest_gap` | 100% | 7 |
| `jargon` | 100% | 66 |
| `names_alternative` | 100% | 4 |
| `no_invention` | 100% | 1 |
| `no_reask` | 100% | 57 |
| `no_transport_leak` | 100% | 66 |
| `place_names` | 100% | 3 |
| `questions` | 100% | 35 |
| `responded` | 100% | 66 |
| `visual_present` | 100% | 10 |

## Pass rate by conversation

| Conversation | Turn pass rate |
| --- | --- |
| c1-what-is-here - What is even here, and what can I trust for a trend | 50% |
| c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots | 71% |
| c3-lantana - Lantana keeps coming back: an honest gap and how to test it | 67% |
| c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule | 50% |
| c5-what-to-replant - What to replant for a forest that keeps itself going | 43% |
| c6-what-grows-where - What is growing where: plots on a map, then one plot in detail | 67% |
| c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots | 57% |
| c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here | 86% |
| c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs | 57% |
| c10-budget-monitoring-plan - Three years of monitoring against a real budget | 43% |

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| comparison | 71% |
| coverage-gap | 50% |
| data-request | 86% |
| denominators | 71% |
| design | 57% |
| drill-down | 67% |
| gap-honesty | 77% |
| mechanism | 50% |
| method-disclosure | 54% |
| network | 50% |
| orientation | 50% |
| place | 67% |
| relationship | 50% |
| seed-fate | 43% |
| study-design | 67% |
| traceability | 61% |
| trust | 62% |
| uncertainty | 57% |
| value-of-information | 50% |

## c1-what-is-here - What is even here, and what can I trust for a trend

Session: `ecoanr-round5-split-not-cut-c1-what-is-here`  |  categories: orientation, trust, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have just taken over restoration monitoring for the Anamalai rainforest fragments. Before I plan anything I need to know what long-term monitoring actually exists here, and how far back it goes. | PASS | - | site-orientation, coverage-versus-effort | 1.5 | 27 | From the data this site has, monitoring records are spread across 302 map squares, but explicit survey effort is documented in only 42 squares. This map shows t... |
| t2 | Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot? | **FAIL** | `traceable`, `multi_turn` | metric-time-series | 1.5 | 19 | This chart could not infer which repeated measure you meant from “those”, so it cannot yet show one trend line. From the data this site has, trend-ready measure... |
| t3 | Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking. | PASS | - | metric-time-series, coverage-versus-effort | 1.05 | 25 | From the data this site has, explicit survey effort is documented in 42 map squares, while records of any kind occur in 302 squares. This map answers where effo... |
| t4 | So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why? | **FAIL** | `traceable`, `confidence` | method-catalog | 1.0 | 23 | From the data this site has, I would stand behind change claims most readily for adult-tree stocks per hectare and plot diversity by habitat, origin, conservati... |
| t5 | Where is the weakest link in that? Where would a reviewer poke holes? | PASS | - | visual-explain | 0.9 | 22 | This answer is for the whole table, because no single row was selected. From the data this site has, the weakest link is the set of change claims that need the ... |
| t6 | Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like. | **FAIL** | `right_tool`, `has_evidence` | - | 1.9 | 11 | Which year do you want me to open for the mammal records? If you want, I can pull one year and show the source rows behind that count. |

### c1-what-is-here / t2

User: Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot?

- `traceable`: no survey named and no path to the rows
- `multi_turn`: dropped the thread: none of ['monitoring', 'survey', 'records', 'years'] came back

```
This chart could not infer which repeated measure you meant from “those”, so it cannot yet show one trend line. From the data this site has, trend-ready measures do exist, including aboveground carbon, basal area, canopy cover, canopy height, canopy openness, adult tree richness, adult tree count per 0.04 ha plot, and daily weather measures like rainfall and temperature. If you want, I can open one of these now and check how far back that series goes.
```

### c1-what-is-here / t4

User: So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why?

- `traceable`: no survey named and no path to the rows
- `confidence`: no plain statement of how far to trust it

```
From the data this site has, I would stand behind change claims most readily for adult-tree stocks per hectare and plot diversity by habitat, origin, conservation status and dispersal traits, because the site’s method catalogue lists these with 0 extra checks, while the other change routes need 3 to 8 checks before they are safe to use. For a 2015 to 2024 claim, I would be much more cautious with occupancy, reporting-rate trends, canopy-response comparisons and reference-similarity methods, because this table says they depend on more conditions being met and it is not itself a fitted result. If you want, I can test the adult-tree stock route first and see whether the records here actually cover 2015 to 2024 well enough.
```

### c1-what-is-here / t6

User: Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like.

- `right_tool`: ran ['nothing'], wanted one of ['coverage-versus-effort', 'entity-record-map', 'group-record-map', 'matrix-profile']
- `has_evidence`: no figure on a how-much / which / where question

```
Which year do you want me to open for the mammal records? If you want, I can pull one year and show the source rows behind that count.
```

## c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots

Session: `ecoanr-round5-split-not-cut-c2-does-restoration-work`  |  categories: comparison, denominators, trust

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | We have been doing assisted natural regeneration in these fragments for years. Is there anything here that compares restored plots against ones we left to regrow on their own? | PASS | - | stratified-survey-summary | 1.5 | 22 | From the data this site has, yes: the restoration opportunities survey does compare two plot classes, with 19 benchmark sites over 38 visits and 113 fragment si... |
| t2 | Good. How do the birds compare across restored, naturally regenerating and benchmark plots? | PASS | - | stratified-survey-summary | 1.5 | 14 | From the data this site has, the bird recovery survey splits 69 sites evenly across benchmark, restored and unrestored plots: 23 sites each. Benchmark plots are... |
| t3 | How many plots in each of those three, and how many times was each visited? | **FAIL** | `rows` | stratified-survey-summary | 2.0 | 13 | From the data this site has, the bird recovery survey has 23 benchmark plots with 152 visits, 23 restored plots with 154 visits, and 23 unrestored plots with 15... |
| t4 | Is that difference real, or could it just be that people spent more time in the benchmark plots? | PASS | - | compile-scientific-algebra-9b, visual-explain | 1.0 | 34 | From the data this site has, it does not look like a simple time-spent artefact: the bird recovery survey already standardises by visits, and benchmark plots st... |
| t5 | Which bird species are driving the gap? I care about the rainforest specialists, not the generalists. | **FAIL** | `right_tool`, `rows` | local-site-evidence-search, plot-indicator-profile | 1.5 | 44 | From the data this site has, this particular view cannot tell us which species are driving the gap for rainforest specialists. The bird recovery survey does hol... |
| t6 | If I had to put one sentence in a report about whether restoration is working here, what would you let me say? | PASS | - | stratified-survey-summary | 1.5 | 21 | From the data this site has, restoration appears to be helping birds: in the bird recovery survey, restored plots had more bird records per visit and more detec... |
| t7 | And what would you not let me say? | PASS | - | stratified-survey-summary | 1.5 | 13 | From the data this site has, there is no causal estimate of restoration effect here. I would not let you say restoration caused bird recovery, or that restored ... |

### c2-does-restoration-work / t3

User: How many plots in each of those three, and how many times was each visited?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, the bird recovery survey has 23 benchmark plots with 152 visits, 23 restored plots with 154 visits, and 23 unrestored plots with 154 visits. So the plot counts are balanced across the three classes, and visit effort is nearly balanced too. If you want, I can check whether the visits were spread across the same years and seasons in all three.
```

### c2-does-restoration-work / t5

User: Which bird species are driving the gap? I care about the rainforest specialists, not the generalists.

- `right_tool`: ran ['local-site-evidence-search', 'plot-indicator-profile'], wanted one of ['entity-record-map', 'group-record-map', 'matrix-profile', 'stratified-survey-summary']
- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, this particular view cannot tell us which species are driving the gap for rainforest specialists. The bird recovery survey does hold species-level bird records overall, with 10,752 records covering 268 recorded bird names across 69 plots and 460 visits, but this route does not split those names into specialist species by restored, unrestored and benchmark classes. If you want, I can test a shortlist of likely rainforest specialists one by one and see which of them are actually recorded across those plot classes.
```

## c3-lantana - Lantana keeps coming back: an honest gap and how to test it

Session: `ecoanr-round5-split-not-cut-c3-lantana`  |  categories: gap-honesty, study-design, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Why does lantana keep coming back after we weed it? | PASS | - | entity-record-map | 1.0 | 26 | I read “lantana” as *Lantana camara*, which this site has 36 records of, with 17 in the squares inside this site’s boundary; this map shows where it was recorde... |
| t2 | Do you have anything at all on lantana at this site? Even just where it has been recorded? | PASS | - | local-site-evidence-search, entity-record-map | 1.75 | 12 | I read “lantana” as *Lantana camara*, which this site has 36 records of; 17 fall in the squares inside this site’s boundary. This map shows where it has been re... |
| t3 | So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots. | **FAIL** | `right_tool`, `not_catch_all` | site-orientation | 1.5 | 25 | From the data this site has, the map confirms both plot-based restoration measurements and broader mapped habitat coverage are available here, but this view sho... |
| t4 | If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here? | **FAIL** | `rows` | method-catalog | 1.7 | 28 | From the data this site has, there is one source-linked shade-response analysis design, but it is not yet a fitted result; it shows 6 required inputs and 5 chec... |
| t5 | How many of the plant community plots could I revisit, and where are they? | PASS | - | stratified-survey-summary, plot-indicator-profile | 1.5 | 31 | From the data this site has, the Plant community structure survey recorded 110 named sites or plots in 2003, and those records fall within 5 squares inside this... |
| t6 | Draft the data request for me: exactly what I would ask my field team to bring back. | PASS | - | method-catalog | 1.85 | 19 | From the data this site has, there is one shade-response analysis design to work from, with 6 required inputs and 5 checks; this table is a method note, not a f... |

### c3-lantana / t3

User: So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots.

- `right_tool`: ran ['site-orientation'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'plot-indicator-profile']
- `not_catch_all`: answered a specific question with only ['site-orientation']

```
From the data this site has, the map confirms both plot-based restoration measurements and broader mapped habitat coverage are available here, but this view shows coverage only, not which one best predicts lantana return. For a stand-in, canopy cover is the simpler repeat measure for reinvasion risk, while plant community plots are the stronger stand-in if you need to explain why lantana returns. If you want, tell me whether this is for quick monitoring or for causal analysis, and I’ll narrow it to one.
```

### c3-lantana / t4

User: If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, there is one source-linked shade-response analysis design, but it is not yet a fitted result; it shows 6 required inputs and 5 checks before you can test the claim. From general knowledge: to test whether shade suppresses lantana, the core field measures are 1. lantana abundance in the same plots on repeat visits, 2. canopy cover in those same plots and dates, and 3. plot context from the existing plant community plots so shade is compared against the same local vegetation setting. If you want, I can turn that into a short field sheet with what, where, how often, and by which method.
```

## c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule

Session: `ecoanr-round5-split-not-cut-c4-natives-suppress`  |  categories: relationship, method-disclosure, mechanism

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Different angle. Are there native species here that turn up where lantana does not? | **FAIL** | `right_tool` | entity-activity-profile | 1.5 | 31 | From the data this site has, I read `lantana` as Lantana camara, with 36 records in 15 1.1 km squares from the restoration, plant-community and threatened-tree ... |
| t2 | How exactly did you match those two things up? Same plot and same year, or just the same general area? | PASS | - | visual-explain | 1.4 | 18 | From the data this site has, that match was only at the same 1.1 km square level, not the same plot and not the same year. The audit trail for this table says “... |
| t3 | That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with? | PASS | - | stratified-survey-summary, entity-record-map | 1.5 | 40 | From the data this site has, I took `plot level` to mean the restoration survey’s surveyed sites, because that is the main plot-based survey behind the lantana ... |
| t4 | What is the mechanism you would bet on here - shade, leaf litter, root competition? | PASS | - | - | 2.0 | 8 | From the data this site has, I would not bet strongly on any one mechanism yet. The plot-level support is still not there, so this site does not have the eviden... |
| t5 | Is there anything in the canopy or tree structure data that supports the shade story? | **FAIL** | `right_tool`, `has_evidence` | entity-activity-profile | 1.5 | 18 | From the data this site has, there is canopy and tree-structure data in the same lantana-linked survey mix: canopy openness, aboveground carbon, basal area, dbh... |
| t6 | Give me three native species to trial as a shade crop, and say how confident you are in each one. | **FAIL** | `rows` | entity-record-map | 1.5 | 36 | From the data this site has, my three trial species would be Vateria indica with high confidence, Palaquium ellipticum with medium-high confidence, and Cullenia... |

### c4-natives-suppress / t1

User: Different angle. Are there native species here that turn up where lantana does not?

- `right_tool`: ran ['entity-activity-profile'], wanted one of ['co-occurrence-map', 'entity-record-map', 'group-record-map', 'interaction-map', 'matrix-profile']

```
From the data this site has, I read `lantana` as Lantana camara, with 36 records in 15 1.1 km squares from the restoration, plant-community and threatened-tree surveys. This table does not yet name the native species from squares without lantana; it only supports square-level sharing, and those records can come from different surveys and years. If you want, tell me whether you mean native plants only or all native species, and I’ll pull that comparison.
```

### c4-natives-suppress / t5

User: Is there anything in the canopy or tree structure data that supports the shade story?

- `right_tool`: ran ['entity-activity-profile'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'metric-time-series', 'plot-indicator-profile']
- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, there is canopy and tree-structure data in the same lantana-linked survey mix: canopy openness, aboveground carbon, basal area, dbh and tree height appear in the plant-community and restoration records. But this table does not show whether plots with Lantana camara had lower canopy openness or different tree structure than plots without it, so it does not yet support the shade story by itself. If you want, I can draft the exact plot-level comparison to test shade against lantana with these measurements.
```

### c4-natives-suppress / t6

User: Give me three native species to trial as a shade crop, and say how confident you are in each one.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, my three trial species would be Vateria indica with high confidence, Palaquium ellipticum with medium-high confidence, and Cullenia exarillata with medium-high confidence; all three are well recorded here across multiple surveys, with 436, 258 and 233 records respectively inside this site’s boundary. From general knowledge: these are native wet-forest trees, so they are plausible shade-crop candidates, but this site’s maps show recorded presence, not proven shade performance or management fit. My confidence is only about “good native candidates already well represented in the records here”, not about nursery ease, growth rate or crop yield effects. If you want, I can turn this into a one-page trial shortlist with what to measure for each species.
```

## c5-what-to-replant - What to replant for a forest that keeps itself going

Session: `ecoanr-round5-split-not-cut-c5-what-to-replant`  |  categories: design, network, seed-fate

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am putting together a planting list for a two hectare gap. I want a forest that regenerates on its own in thirty years, not a plantation. Where do I start? | PASS | - | site-orientation | 2.0 | 24 | From general knowledge: For a self-regenerating forest, start with native species already surviving and recruiting in the same landscape. Favour a mix of canopy... |
| t2 | Which trees here actually get their seed moved by animals, and by which animals? | PASS | - | interaction-pairs | 1.25 | 17 | From the data this site has, the frugivory and seed-fate studies recorded 150 animal-tree pairs across 5,622 rows; the most recorded were Yellow-browed Bulbul w... |
| t3 | Of those, which lose most of their seed to predators? I do not want to plant something that never recruits. | **FAIL** | `has_evidence`, `traceable` | interaction-pairs, discover-biotic-interactions, local-site-evidence-search | 1.5 | 70 | From the data this site has, that predator-pair table did not return any stored tree-animal pairs for your exact predation question, so this site does not yet l... |
| t4 | Are any threatened species in that list worth including? | **FAIL** | `rows` | entity-activity-profile | 1.5 | 30 | From general knowledge: If you want long-term regeneration, a threatened tree is worth adding only if it is native here and already shows local adult and regene... |
| t5 | Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge. | PASS | - | local-site-evidence-search | 2.0 | 18 | From the data this site has, only these two are in the shortlist with direct support from this conversation: 1. *Heynea trijuga* — site-backed. It has animal-li... |
| t6 | Which of those would fail if the hornbills do not come back? | **FAIL** | `rows` | interaction-pairs | 1.5 | 24 | From the data this site has, none of the two site-backed shortlist species looks hornbill-only. Malabar Grey Hornbill was recorded with *Heynea trijuga* (97 and... |
| t7 | What should I plant first to bring the hornbills in? | **FAIL** | `rows` | - | 1.5 | 17 | From general knowledge: Large-fruited native trees are often the quickest way to draw hornbills back, but only if those trees can also establish locally and fru... |

### c5-what-to-replant / t3

User: Of those, which lose most of their seed to predators? I do not want to plant something that never recruits.

- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
From the data this site has, that predator-pair table did not return any stored tree-animal pairs for your exact predation question, so this site does not yet let me rank seed loss by tree from that table. That is a gap in what was written down, not proof that predation is absent; but the local records do show both *Persea macrantha* and *Heynea trijuga* as regenerating here, so neither currently looks like a tree with zero recruitment. If you want, I can map *Heynea trijuga* next, since it has strong animal-linked records and local regeneration records.
```

### c5-what-to-replant / t4

User: Are any threatened species in that list worth including?

- `rows`: no table, list or row language where the user asked for specifics

```
From general knowledge: If you want long-term regeneration, a threatened tree is worth adding only if it is native here and already shows local adult and regeneration records. That lowers the risk of planting a species that needs repeated rescue. From the data this site has, *Heynea trijuga* is the clearer one to include first: it has 237 records across 45 squares from 2002 to 2022, including 41 regeneration records in the restoration study and 33 records in the threatened-tree and trail survey. *Persea macrantha* also looks worth considering for regeneration, but this site’s profile for it comes only from the plant community and tree-structure surveys, not the threatened-tree work. These are records, not abundance counts, so they support shortlist priority, not planting density. If you want, I can pull the strongest 5 to 10 animal-linked native trees from this evidence into a first planting shortlist.
```

### c5-what-to-replant / t6

User: Which of those would fail if the hornbills do not come back?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, none of the two site-backed shortlist species looks hornbill-only. Malabar Grey Hornbill was recorded with *Heynea trijuga* (97 and 14 records) and *Persea macrantha* (54 and 34 records) in the frugivory and seed-fate studies, but both of those trees were also recorded with other birds and mammals earlier in this conversation, so I would not drop them just because hornbills are missing. If you want, I can now tighten the shortlist into `safer without hornbills` and `better if hornbills return`.
```

### c5-what-to-replant / t7

User: What should I plant first to bring the hornbills in?

- `rows`: no table, list or row language where the user asked for specifics

```
From general knowledge: Large-fruited native trees are often the quickest way to draw hornbills back, but only if those trees can also establish locally and fruit reliably. So I would favour trees with both hornbill use and independent local records. From the data this site has, the hornbill-linked trees recorded most often in the frugivory and seed-fate studies were *Myristica dactyloides* (132 and 104 records), *Heynea trijuga* (97 and 14), and *Persea macrantha* (54 and 34). For first planting, I would start with *Heynea trijuga* and *Persea macrantha* because this conversation also found them in local regeneration or adult-tree records; treat *Myristica dactyloides* as a high-value next candidate, but confirm local establishment at your site before using it heavily. These are records of hornbills seen with those trees, not proof of seed movement, so use them to set planting order, not to assume recruitment success. If you want, I can turn this into a phased planting list: `plant first`, `plant after shade builds`, and `hold until more evidence`.
```

## c6-what-grows-where - What is growing where: plots on a map, then one plot in detail

Session: `ecoanr-round5-split-not-cut-c6-what-grows-where`  |  categories: place, drill-down, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Show me what is growing where across the fragments. I want to see the plots on a map. | PASS | - | site-orientation | 1.4 | 18 | From the data this site has, this map shows where records linked to fragments are concentrated across Valparai, with 42,348 records covering 302 map squares and... |
| t2 | Which plot has the highest share of rainforest species? | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool`, `has_evidence` | - | 2.0 | 7 | Do you mean rainforest species in the bird surveys, or in the vegetation plots? I need that one choice because this site has plot-based data from more than one ... |
| t3 | Tell me more about that one. What is the stem density there, and what does the canopy look like? | PASS | - | plot-indicator-profile | 1.5 | 30 | From the data this site has, I treated your earlier question as the bird recovery survey reading, but this map cannot tie rainforest-bird share to one georefere... |
| t4 | Where does that number come from? Show me the rows. | PASS | - | visual-explain | 1.5 | 18 | From the data this site has, that number does not come from any source rows, because the earlier request did not resolve to a mapped plot value at all. The stor... |
| t5 | How does it compare against the benchmark plots? | PASS | - | plot-indicator-profile | 1.5 | 17 | From the data this site has, in the bird recovery survey, benchmark plots have much higher canopy cover than restored plots: benchmark mean 77.2 across 23 plots... |
| t6 | Is that plot an outlier, or is it typical of the restored ones? | **FAIL** | `confidence` | visual-explain | 1.5 | 21 | From the data this site has, no single plot had been identified, so I checked the largest recorded canopy-cover point on that map. It is 100 from one row in the... |

### c6-what-grows-where / t2

User: Which plot has the highest share of rainforest species?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['nothing'], wanted one of ['group-record-map', 'matrix-profile', 'plot-indicator-profile', 'stratified-survey-summary']
- `has_evidence`: no figure on a how-much / which / where question

```
Do you mean rainforest species in the bird surveys, or in the vegetation plots? I need that one choice because this site has plot-based data from more than one survey, and the “highest share” will differ by survey.
```

### c6-what-grows-where / t6

User: Is that plot an outlier, or is it typical of the restored ones?

- `confidence`: no plain statement of how far to trust it

```
From the data this site has, no single plot had been identified, so I checked the largest recorded canopy-cover point on that map. It is 100 from one row in the bird recovery survey, and that is not typical of restored plots: restored plots had mean canopy cover 58.0 and a maximum of 80, so this point sits above the restored range. If you want, I can pull the restored-plot rows only and show where that upper end sits.
```

## c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots

Session: `ecoanr-round5-split-not-cut-c7-survey-budget`  |  categories: value-of-information, coverage-gap, uncertainty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Say I get twenty drone days next season. Where should I fly to learn the most? | **FAIL** | `has_evidence` | survey-priority-squares | 1.3 | 18 | From the data this site has, the best learning return is around Puduthottam first, then Sirikundra, Thenmalai and Murugaali-BlackBridge, because these places ha... |
| t2 | What are you basing that on? Places we have never looked, or places where you think something is happening? | **FAIL** | `join_rule_disclosed` | visual-explain | 1.4 | 20 | It is based on where the data is thin, not where I think something ecological is happening. Because you did not point to one square, I checked the largest ranke... |
| t3 | If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover. | PASS | - | group-record-map | 1.9 | 21 | Yes, the answer would change. From the data this site has, I would shift from “where is documentation thinnest” to “where introduced plants are already recorded... |
| t4 | And if it is just me and two field assistants for thirty days on foot? | PASS | - | coverage-versus-effort | 1.9 | 13 | From the data this site has, I would still send the team to the under-documented parts, because records occur in 302 squares but explicit survey effort is docum... |
| t5 | Which of the three buys me the most for a restoration decision in the next two years? | PASS | - | compile-scientific-algebra-9b | 1.4 | 54 | From the data this site has, the hyperspectral option buys you the most for a restoration decision in the next two years, because it targets introduced-plant se... |
| t6 | Show me the gap map. Where is coverage thinnest relative to how much is going on there? | **FAIL** | `has_evidence` | survey-priority-squares | 1.9 | 15 | From the data this site has, coverage is thinnest near Puduthottam, then Sirikundra, Thenmalai and Murugaali-BlackBridge: these places have many records but ver... |
| t7 | Rank the top five places, with a reason for each that I could put in a proposal. | PASS | - | survey-priority-squares | 1.65 | 15 | From the data this site has, the top five are: 1. Puduthottam — highest priority because 903 records are present but only 4 rows of documented survey work suppo... |

### c7-survey-budget / t1

User: Say I get twenty drone days next season. Where should I fly to learn the most?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, the best learning return is around Puduthottam first, then Sirikundra, Thenmalai and Murugaali-BlackBridge, because these places have many records but very little documented survey work behind them. This map ranks where the missing information is greatest, not where biodiversity is richest, and some gaps may be missing paperwork as much as missing fieldwork. If you want, I can show the full map of coverage versus documented effort behind this ranking.
```

### c7-survey-budget / t2

User: What are you basing that on? Places we have never looked, or places where you think something is happening?

- `join_rule_disclosed`: asked how two things were matched, did not say

```
It is based on where the data is thin, not where I think something ecological is happening. Because you did not point to one square, I checked the largest ranked square on that map: it holds 903 records across 98 different recorded subjects, from the tree and habitat structure survey, and the ranking lifts places where records are present but documented survey work is little or absent. Missing survey work can also mean missing paperwork, so this is a priority map for learning, not a hotspot map. If you want, I can show the full coverage-versus-effort map behind that ranking.
```

### c7-survey-budget / t6

User: Show me the gap map. Where is coverage thinnest relative to how much is going on there?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, coverage is thinnest near Puduthottam, then Sirikundra, Thenmalai and Murugaali-BlackBridge: these places have many records but very little documented survey work behind them. The map shows where a survey would teach us most, not where biodiversity is richest, and some of the gap may be missing paperwork rather than missing fieldwork. If you want, I can show the whole coverage-versus-effort map behind this ranking.
```

## c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here

Session: `ecoanr-round5-split-not-cut-c8-monitoring-plan`  |  categories: design, data-request, gap-honesty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here. | PASS | - | site-orientation | 1.0 | 25 | From the data this site has, there is enough existing restoration, regeneration, bird and plot material to set up a three-year matched comparison: the same plot... |
| t2 | What can I reuse as a baseline instead of starting from scratch? | PASS | - | coverage-versus-effort | 1.5 | 17 | From the data this site has, you can reuse baseline only in the 42 cells where survey effort is documented, especially from the restoration, bird, frugivory, th... |
| t3 | What is the minimum I have to keep collecting so the old data stays comparable? | **FAIL** | `join_rule_disclosed` | method-catalog | 1.25 | 25 | From the data this site has, the closest restoration method already recorded here depends on 6 required inputs and 5 checks, so that is the minimum backbone you... |
| t4 | What is missing entirely, that I would have to start measuring from zero? | PASS | - | stratified-survey-summary | 1.75 | 20 | The remaining data gap is a direct ANR-versus-active-planting time series. In the restoration survey this site has, the split is Benchmark and Fragment, with 13... |
| t5 | How many plots, and how many visits a year, to have a real chance of detecting a difference? | PASS | - | compile-scientific-algebra-9b | 2.0 | 30 | From the data this site has, I cannot defend a plot count yet. The restoration survey shows 132 surveyed sites and 264 visits, with 19 Benchmark sites and 113 F... |
| t6 | Write it up as a one page plan I can hand to my team. | PASS | - | - | 1.85 | 23 | **One-Page Plan** **Purpose** Answer one question in 3 years: does assisted natural regeneration do better than active planting here? From the data this site ha... |
| t7 | And a list of the data I would need to request from the other groups working here. | PASS | - | - | 2.0 | 17 | Use this as the data request to other groups working here. 1. Plot register: plot name, treatment type, year started, exact boundaries, area, slope, aspect, ele... |

### c8-monitoring-plan / t3

User: What is the minimum I have to keep collecting so the old data stays comparable?

- `join_rule_disclosed`: asked how two things were matched, did not say

```
From the data this site has, the closest restoration method already recorded here depends on 6 required inputs and 5 checks, so that is the minimum backbone you must keep unchanged if you want old and new canopy-response results to stay comparable. This table is a method note, not a fitted result, and it does not name the six fields in the summary view, so I should not guess them. If you want, I can pull the matching plot-measure route and turn those six inputs into a short field list for year 0 to year 3.
```

## c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs

Session: `ecoanr-round5-split-not-cut-c9-seed-dispersal-design`  |  categories: network, design, method-disclosure

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am designing the dispersal side of our planting. Who actually disperses what here? Give me the recorded tree and animal pairs, not the general story. | PASS | - | interaction-pairs | 1.75 | 20 | From the data this site has, the focal-tree frugivore visitation study, the seed-fate study, and the seed-predation experiment together record 150 tree-animal p... |
| t2 | Which of the trees you just named have no recorded disperser at all? Those are the ones that worry me. | **FAIL** | `gap_or_answer` | interaction-pairs | 1.0 | 21 | From the data this site has, none of the trees just named are without a recorded animal pair: *Persea macrantha* is recorded with Yellow-browed Bulbul, White-ch... |
| t3 | How much of that is real absence, and how much is nobody having watched that tree? Tell me how the watching effort differs between trees. | PASS | - | entity-activity-profile | 1.5 | 29 | From the data this site has, I cannot call any missing pair a real absence here, because the two trees were not watched equally. *Persea macrantha* has 91 recor... |
| t4 | Of the dispersers on that list, which ones are actually recorded in the degraded fragments I would be restoring? | **FAIL** | `rows` | stratified-survey-summary, entity-activity-profile | 1.0 | 51 | From the data this site has, Southern Hill Myna, Malabar Grey Hornbill, Mountain Imperial Pigeon, and Malabar giant squirrel are all recorded in the bird-recove... |
| t5 | So if I plant for the dispersers I already have, what does the planting list look like? | PASS | - | compile-scientific-algebra-9b | 1.5 | 51 | From the data this site has, the defensible planting list is short: *Persea macrantha* and *Heynea trijuga*. Those are the trees this site explicitly pairs with... |
| t6 | Be straight with me. A bird recorded on a fruiting tree is not the same as that bird moving the seed. How much of this list rests on that assumption? | **FAIL** | `join_rule_disclosed` | visual-explain | 1.5 | 18 | From the data this site has, all of that planting list rests on the weaker reading, not on demonstrated seed movement. The pair table is built from the focal-tr... |
| t7 | What would my team have to record next season to turn these pairs into real dispersal evidence? | PASS | - | method-catalog | 1.85 | 22 | From the data this site has, this route did not return a ready method card for turning contact pairs into dispersal proof. So I am grounding the field list belo... |

### c9-seed-dispersal-design / t2

User: Which of the trees you just named have no recorded disperser at all? Those are the ones that worry me.

- `gap_or_answer`: neither an answer nor an honest gap

```
From the data this site has, none of the trees just named are without a recorded animal pair: *Persea macrantha* is recorded with Yellow-browed Bulbul, White-cheeked Barbet, Red-whiskered Bulbul and Southern Hill Myna, and *Heynea trijuga* is recorded with Southern Hill Myna in the focal-tree frugivore and seed-fate studies. This still does not prove seed movement; it only shows that those tree-animal pairs were recorded together. If you want, I can map where *Persea macrantha* or *Heynea trijuga* is recorded.
```

### c9-seed-dispersal-design / t4

User: Of the dispersers on that list, which ones are actually recorded in the degraded fragments I would be restoring?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, Southern Hill Myna, Malabar Grey Hornbill, Mountain Imperial Pigeon, and Malabar giant squirrel are all recorded in the bird-recovery study from restored, naturally regenerating, and benchmark plots, so they do occur in the degraded-fragment restoration landscape. Southern Hill Myna has 134 records there, Malabar Grey Hornbill 47, Mountain Imperial Pigeon 49, and Malabar giant squirrel 67; these are records, not abundance, and they do not by themselves prove dispersal inside those plots. For Yellow-browed Bulbul, White-cheeked Barbet, and Red-whiskered Bulbul, this route did not give a usable match, so that is a naming gap in this view, not evidence they are absent from the fragments. If you want, I can map where Southern Hill Myna and Malabar Grey Hornbill are recorded together in the restoration landscape.
```

### c9-seed-dispersal-design / t6

User: Be straight with me. A bird recorded on a fruiting tree is not the same as that bird moving the seed. How much of this list rests on that assumption?

- `join_rule_disclosed`: asked how two things were matched, did not say

```
From the data this site has, all of that planting list rests on the weaker reading, not on demonstrated seed movement. The pair table is built from the focal-tree frugivore study, the seed-fate study, and the seed-predation experiment, and its own limitation says each pair is only an animal recorded at or on a plant, not proof that the seed was moved, eaten, or dispersed. So the list is useful as a shortlist of observed contacts, but every item still needs stronger backing if you want to claim actual dispersal. If you want, I can separate this into “recorded contact only” and “best-supported for planting anyway.”
```

## c10-budget-monitoring-plan - Three years of monitoring against a real budget

Session: `ecoanr-round5-split-not-cut-c10-budget-monitoring-plan`  |  categories: value-of-information, design, coverage-gap

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have thirty field days and twenty drone days a year, for three years. Where do I start? Give me named places, not coordinates. | PASS | - | survey-priority-squares | 1.3 | 19 | From the data this site has, start with Puduthottam, Sirikundra, Thenmalai, Murugaali-BlackBridge, and Puduthottam_Coffee; the map ranks these as the places whe... |
| t2 | Why those places? Show me the gap between what has been recorded there and what has actually been surveyed. | **FAIL** | `join_rule_disclosed` | coverage-versus-effort | 1.3 | 25 | From the data this site has, those places rise to the top because records are spread across 302 map squares, but documented survey work exists in only 42 square... |
| t3 | Split the thirty field days across those places for year one. | **FAIL** | `rows` | compile-scientific-algebra-9b | 0.65 | 36 | From the data this site has, a practical year-one split is: Murugaali-BlackBridge 10 days, Puduthottam 7 days, Thenmalai 5 days across its two ranked squares, V... |
| t4 | What do the drone days add that the field days do not, given what this site already measures? | **FAIL** | `traceable` | local-site-evidence-search, method-catalog | 1.25 | 22 | From the data this site has, the current measured work is dominated by ground-based methods: adult-tree counts, basal area, carbon, habitat and trait comparison... |
| t5 | What can I already get from the existing surveys, so that I am not paying to collect it twice? | **FAIL** | `has_evidence` | local-site-evidence-search, method-catalog | 1.35 | 26 | From the data this site has, the existing surveys already support adult-tree counts, basal area, carbon per hectare, habitat and dispersal-trait diversity, cano... |
| t6 | If year one comes back and those gap squares are genuinely empty, what changes in year two? | PASS | - | local-site-evidence-search, method-catalog | 0.9 | 19 | From the data this site has, if year one shows those squares are genuinely empty after proper survey effort, year two should shift from broad gap-filling to rep... |
| t7 | Write me the three year plan, year by year, and tell me what would make me abandon it. | PASS | - | local-site-evidence-search, method-catalog | 0.85 | 21 | From the data this site has, Year 1 should finish the gap-checking work in the priority places and use the existing surveys to collect only adult-tree counts, b... |

### c10-budget-monitoring-plan / t2

User: Why those places? Show me the gap between what has been recorded there and what has actually been surveyed.

- `join_rule_disclosed`: asked how two things were matched, did not say

```
From the data this site has, those places rise to the top because records are spread across 302 map squares, but documented survey work exists in only 42 squares. This map shows that gap directly: a place can have many records and still have very little written survey effort behind it, so it is weak for absence claims or effort-adjusted comparisons. If you want, I can pull the exact recorded-versus-survey gap again for Puduthottam, Sirikundra, and Thenmalai one by one.
```

### c10-budget-monitoring-plan / t3

User: Split the thirty field days across those places for year one.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, a practical year-one split is: Murugaali-BlackBridge 10 days, Puduthottam 7 days, Thenmalai 5 days across its two ranked squares, Varatuparai 2 days, Manamboli 2 days, Sirikundra 1 day, Puduthottam_Coffee 1 day, Selaliparai 2 1 day, and Pannimade 1 day. This is a planning split from the observed gap between records and documented survey work, so it pushes effort hardest into places with many records but very little written survey effort behind them. The remaining data gap is that the scientific calculator would not run on the map summaries alone; it asked for more specific records first, so treat this as an evidence-based starting allocation, not a modelled optimum. If you want, I can turn this into a month-by-month year-one field schedule by place.
```

### c10-budget-monitoring-plan / t4

User: What do the drone days add that the field days do not, given what this site already measures?

- `traceable`: no survey named and no path to the rows

```
From the data this site has, the current measured work is dominated by ground-based methods: adult-tree counts, basal area, carbon, habitat and trait comparisons, canopy-response analyses, checklist occupancy, and reporting-rate trends. The local search did not match a recorded drone-specific topic, so this is a naming gap, not proof of absence; and this table documents method designs, not fitted results. If you want, I can draft a short list of what drone days should collect here so they add something the current field methods do not.
```

### c10-budget-monitoring-plan / t5

User: What can I already get from the existing surveys, so that I am not paying to collect it twice?

- `has_evidence`: no figure on a how-much / which / where question

```
From the data this site has, the existing surveys already support adult-tree counts, basal area, carbon per hectare, habitat and dispersal-trait diversity, canopy-response analyses, checklist-based occupancy, range surfaces, and reporting-rate trends. The local topic lookup did not match a named alias, so that is a naming gap, not proof of absence; and this table lists documented methods, not finished model outputs. If you want, I can turn this into a numbered “do not re-collect” list for your field and drone teams.
```

