# Ecology ANR bench - results

Run: `round6-contract-a`  |  endpoint: `http://172.17.0.1:7012`  |  model: `idli-insight-valparai`  |  started: 2026-07-26T03:34:30+05:30

**42/66 turns pass (64%)**, 0/10 conversations clean, mean language score 1.86/2, median latency 20.7s (max 72.2s), 0 turns retried.

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
| `place_names` | 67% | 3 |
| `confidence` | 72% | 18 |
| `names_alternative` | 75% | 4 |
| `join_rule_disclosed` | 83% | 6 |
| `traceable` | 85% | 33 |
| `right_tool` | 86% | 29 |
| `has_evidence` | 88% | 34 |
| `visual_present` | 90% | 10 |
| `dead_end` | 98% | 66 |
| `jargon` | 98% | 66 |
| `next_step_in_prose` | 98% | 66 |
| `brevity` | 100% | 1 |
| `gap_or_answer` | 100% | 5 |
| `general_knowledge_labelled` | 100% | 2 |
| `honest_gap` | 100% | 7 |
| `multi_turn` | 100% | 57 |
| `no_invention` | 100% | 1 |
| `no_reask` | 100% | 57 |
| `no_transport_leak` | 100% | 66 |
| `not_catch_all` | 100% | 25 |
| `questions` | 100% | 35 |
| `responded` | 100% | 66 |

## Pass rate by conversation

| Conversation | Turn pass rate |
| --- | --- |
| c1-what-is-here - What is even here, and what can I trust for a trend | 50% |
| c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots | 71% |
| c3-lantana - Lantana keeps coming back: an honest gap and how to test it | 83% |
| c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule | 83% |
| c5-what-to-replant - What to replant for a forest that keeps itself going | 29% |
| c6-what-grows-where - What is growing where: plots on a map, then one plot in detail | 67% |
| c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots | 71% |
| c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here | 57% |
| c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs | 71% |
| c10-budget-monitoring-plan - Three years of monitoring against a real budget | 57% |

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| comparison | 71% |
| coverage-gap | 64% |
| data-request | 57% |
| denominators | 71% |
| design | 54% |
| drill-down | 67% |
| gap-honesty | 69% |
| mechanism | 83% |
| method-disclosure | 77% |
| network | 50% |
| orientation | 50% |
| place | 67% |
| relationship | 83% |
| seed-fate | 29% |
| study-design | 83% |
| traceability | 67% |
| trust | 62% |
| uncertainty | 71% |
| value-of-information | 64% |

## c1-what-is-here - What is even here, and what can I trust for a trend

Session: `ecoanr-round6-contract-a-c1-what-is-here`  |  categories: orientation, trust, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have just taken over restoration monitoring for the Anamalai rainforest fragments. Before I plan anything I need to know what long-term monitoring actually exists here, and how far back it goes. | PASS | - | site-orientation, coverage-versus-effort, site-overview | 1.75 | 47 | From the data this site has, long-term monitoring does exist: there are 21 registered datasets here, including weather from 2014 to 2026, mammal records split a... |
| t2 | Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot? | **FAIL** | `has_evidence`, `traceable` | metric-time-series | 2.0 | 20 | From the data this site has, the repeatable trend view is set up for weather and restoration-plot measurements, not for every monitoring stream. The trendable m... |
| t3 | Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking. | **FAIL** | `visual_present`, `right_tool`, `has_evidence` | local-site-evidence-search | 2.0 | 31 | To answer that properly, I need one choice from you: which monitoring stream should I test for year-wise effort? The site holds separate effort-bearing streams ... |
| t4 | So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why? | **FAIL** | `traceable`, `confidence` | method-catalog | 2.0 | 17 | From the data this site has, I would stand behind change claims that use repeated plot measurements or effort-adjusted detections, not raw later-year record tot... |
| t5 | Where is the weakest link in that? Where would a reviewer poke holes? | PASS | - | method-catalog | 1.75 | 17 | This site does not have a ready, already-fitted trend result for that claim. The weakest link is implementation and input completeness: the one admitted effort-... |
| t6 | Show me the actual records behind the mammal counts for one year, so I can see what a single row looks like. | PASS | - | local-site-evidence-search, discover-ecology-evidence, group-record-map, visual-explain | 2.0 | 58 | From the data this site has, I used the largest single mammal record on this map because no specific record was identified. In the 2024 mammal dataset, that one... |

### c1-what-is-here / t2

User: Which of those has been repeated often enough that I could look at a trend, rather than just a snapshot?

- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
From the data this site has, the repeatable trend view is set up for weather and restoration-plot measurements, not for every monitoring stream. The trendable measures it returned include daily rainfall, temperature, humidity, daylight, wind, radiance. Plot indicators such as canopy openness, canopy cover, canopy height, basal area, tree height, aboveground carbon, coffee stems and cut tree stems. Would you like me to check one of these properly as a time series, such as rainfall, canopy openness or aboveground carbon?
```

### c1-what-is-here / t3

User: Show me how the survey effort is spread across the years. I want to know whether the later years just had more people looking.

- `visual_present`: no result marker on a turn that warrants a picture
- `right_tool`: ran ['local-site-evidence-search'], wanted one of ['coverage-versus-effort', 'metric-time-series', 'seasonal-surface-profile']
- `has_evidence`: no figure on a how-much / which / where question

```
To answer that properly, I need one choice from you: which monitoring stream should I test for year-wise effort? The site holds separate effort-bearing streams for restoration birds, butterflies, frogs, road events and some tree surveys. They are not directly comparable as one pooled series. Would you like restoration birds first?
```

### c1-what-is-here / t4

User: So if I wanted to claim that something changed between 2015 and 2024, which of these would you actually stand behind, and why?

- `traceable`: no survey named and no path to the rows
- `confidence`: no plain statement of how far to trust it

```
From the data this site has, I would stand behind change claims that use repeated plot measurements or effort-adjusted detections, not raw later-year record totals. The site’s admitted methods for this include adult tree stocks per plot area, trait-qualified plot diversity, canopy response against reference, benchmark-normalised canopy profile, single-season occupancy. Effort-adjusted reporting-rate trend, which is exactly the kind of control you need if later years had more people looking. If you want, I can take one of these and check whether the 2015 to 2024 comparison is actually supportable here.
```

## c2-does-restoration-work - Does restoration work: birds in restored, regenerating and benchmark plots

Session: `ecoanr-round6-contract-a-c2-does-restoration-work`  |  categories: comparison, denominators, trust

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | We have been doing assisted natural regeneration in these fragments for years. Is there anything here that compares restored plots against ones we left to regrow on their own? | PASS | - | stratified-survey-summary | 1.9 | 26 | From the data this site has, there is a restoration survey that splits 132 surveyed sites into 2 treatment categories and keeps effort visible. In that survey, ... |
| t2 | Good. How do the birds compare across restored, naturally regenerating and benchmark plots? | PASS | - | stratified-survey-summary | 2.0 | 13 | From the data this site has, the bird survey compares 23 benchmark, 23 restored, and 23 unrestored plots, with 152, 154, and 154 visits respectively. Benchmark ... |
| t3 | How many plots in each of those three, and how many times was each visited? | PASS | - | stratified-survey-summary | 2.0 | 12 | From the data this site has, the bird survey includes 23 benchmark plots, 23 restored plots, and 23 unrestored plots. Benchmark was visited 152 times, restored ... |
| t4 | Is that difference real, or could it just be that people spent more time in the benchmark plots? | PASS | - | method-catalog, compile-scientific-algebra-9b, visual-explain | 2.0 | 41 | From the data this site has, the benchmark plots were not sampled more heavily overall: they had 152 visits and 2280 minutes, while restored and unrestored each... |
| t5 | Which bird species are driving the gap? I care about the rainforest specialists, not the generalists. | **FAIL** | `rows` | stratified-survey-summary, local-site-evidence-search | 2.0 | 45 | The remaining data gap is that this site does not have a ready species-by-plot summary for that bird comparison. From the data this site has, the same bird surv... |
| t6 | If I had to put one sentence in a report about whether restoration is working here, what would you let me say? | **FAIL** | `confidence` | visual-explain | 2.0 | 18 | From the data this site has, restored plots show better bird detection rates than unrestored plots and are closer to benchmark plots, with similar survey effort... |
| t7 | And what would you not let me say? | PASS | - | visual-explain | 2.0 | 11 | This site does not have a causal test showing that restoration caused bird recovery here. So I would not let you say restoration has been proven to increase bir... |

### c2-does-restoration-work / t5

User: Which bird species are driving the gap? I care about the rainforest specialists, not the generalists.

- `rows`: no table, list or row language where the user asked for specifics

```
The remaining data gap is that this site does not have a ready species-by-plot summary for that bird comparison. From the data this site has, the same bird survey does hold 268 distinct bird subjects across 69 named plots and 460 visits. But this particular view cannot tell which rainforest specialist species are driving the restored versus benchmark gap. From general knowledge: in restoration studies, that question usually needs species-level detections linked to plot type, not just total bird detections. If you want, I can check named rainforest specialists one by one in this site’s bird records and see which of them are actually recorded in restored, unrestored, and benchmark plots.
```

### c2-does-restoration-work / t6

User: If I had to put one sentence in a report about whether restoration is working here, what would you let me say?

- `confidence`: no plain statement of how far to trust it

```
From the data this site has, restored plots show better bird detection rates than unrestored plots and are closer to benchmark plots, with similar survey effort. So the bird evidence is consistent with restoration helping but does not by itself prove a causal effect. This trace fell back to the largest single plot because no specific plot was named. The underlying comparison is still a descriptive survey summary rather than a treatment test. If you want, I can turn that into a stricter one-line report sentence or a more cautious donor-facing version.
```

## c3-lantana - Lantana keeps coming back: an honest gap and how to test it

Session: `ecoanr-round6-contract-a-c3-lantana`  |  categories: gap-honesty, study-design, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Why does lantana keep coming back after we weed it? | PASS | - | entity-record-map | 2.0 | 23 | I read “lantana” as *Lantana camara*, which this site has 36 records of; 17 fall in squares inside this site’s boundary. So the map shows where it has been reco... |
| t2 | Do you have anything at all on lantana at this site? Even just where it has been recorded? | PASS | - | local-site-evidence-search, entity-record-map | 1.9 | 10 | I read “lantana” as *Lantana camara*, which this site has 36 records of. The map shows where those records are available, and 17 fall in squares inside this sit... |
| t3 | So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots. | **FAIL** | `right_tool` | method-catalog, local-site-evidence-search | 2.0 | 39 | From the data this site has, the plant community plots look like the better stand-in here: there is 1 specified plot-diversity analysis route, with 9 required i... |
| t4 | If I wanted to test whether shade suppresses lantana, what would I actually have to go and measure, given what is already here? | PASS | - | method-catalog | 1.85 | 20 | From the data this site has, there is one shade-response analysis design for canopy cover. It needs 6 inputs with 5 further checks before it can be run. This vi... |
| t5 | How many of the plant community plots could I revisit, and where are they? | PASS | - | stratified-survey-summary | 2.0 | 28 | From the data this site has, the plant community structure survey has 110 named sites or plots from 2003, with records in 5 squares inside this site’s mapped ar... |
| t6 | Draft the data request for me: exactly what I would ask my field team to bring back. | PASS | - | method-catalog | 1.85 | 18 | From the data this site has, the shade-response method note points to 6 required inputs and 5 further checks. This is a methods note, not a finished lantana res... |

### c3-lantana / t3

User: So what could I use as a stand-in? I was thinking canopy cover, or the plant community plots.

- `right_tool`: ran ['local-site-evidence-search', 'method-catalog'], wanted one of ['cell-feature-map', 'earth-layer', 'group-record-map', 'matrix-profile', 'plot-indicator-profile']

```
From the data this site has, the plant community plots look like the better stand-in here: there is 1 specified plot-diversity analysis route, with 9 required inputs and no extra checks listed at this stage. Canopy cover also has 1 source-linked analysis route, but 0 are specified without an extra implementation review state. That route carries 5 checks with 6 required inputs. These are analysis designs from the site’s methods list, not fitted results on lantana itself. If you want, I can pull the canopy route next and say exactly what those checks are.
```

## c4-natives-suppress - Which natives sit where the invasives do not: co-occurrence and the join rule

Session: `ecoanr-round6-contract-a-c4-natives-suppress`  |  categories: relationship, method-disclosure, mechanism

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Different angle. Are there native species here that turn up where lantana does not? | PASS | - | co-occurrence-map | 2.0 | 26 | Yes. From the data this site has, `Native` records appear in 104 squares inside this site’s boundary, while lantana appears in 15. So native species do turn up ... |
| t2 | How exactly did you match those two things up? Same plot and same year, or just the same general area? | PASS | - | visual-explain | 1.75 | 21 | It was matched by the same 1.1 km square inside this site’s boundary, not by the same plot. For this map, lantana and `Native` were counted as overlapping if bo... |
| t3 | That is a coarse join. Can you do it at the plot level instead, and tell me how many plots that leaves me with? | PASS | - | entity-activity-profile, stratified-survey-summary, compile-scientific-algebra-9b | 2.0 | 72 | From the data this site has, the nearest plot or site-level footing I can defend is the restoration survey, which has 132 surveyed site units and 264 visits. Th... |
| t4 | What is the mechanism you would bet on here - shade, leaf litter, root competition? | PASS | - | - | 2.0 | 9 | From the data this site has, I would not make a site-specific mechanism claim yet. This site does not have a direct plot-level test here linking lantana presenc... |
| t5 | Is there anything in the canopy or tree structure data that supports the shade story? | PASS | - | plot-indicator-profile | 2.0 | 23 | From the data this site has, there is canopy openness data for 1,289 plots. But this view does not split plots into lantana versus no-lantana, so it does not ye... |
| t6 | Give me three native species to trial as a shade crop, and say how confident you are in each one. | **FAIL** | `rows` | group-record-map, entity-record-map | 1.5 | 34 | From the data this site has, I would shortlist `Vateria indica` (higher confidence), `Palaquium ellipticum` (medium confidence), and `Cullenia exarillata` (medi... |

### c4-natives-suppress / t6

User: Give me three native species to trial as a shade crop, and say how confident you are in each one.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, I would shortlist `Vateria indica` (higher confidence), `Palaquium ellipticum` (medium confidence), and `Cullenia exarillata` (medium confidence): all three are native and well represented here, with 436, 258. 233 records inside this site’s boundary respectively, but these are record counts from mixed surveys, not a trial result or an effort-normalised ranking. From general knowledge: `Vateria indica` is my strongest bet for a shade-tree trial, while `Palaquium ellipticum` and `Cullenia exarillata` are also plausible evergreen canopy candidates. My confidence drops because this site does not yet show their survival, growth, or direct shade effect in a coffee-style trial. If you want, I can compare all records with documented effort before we narrow this to one or two trial species.
```

## c5-what-to-replant - What to replant for a forest that keeps itself going

Session: `ecoanr-round6-contract-a-c5-what-to-replant`  |  categories: design, network, seed-fate

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am putting together a planting list for a two hectare gap. I want a forest that regenerates on its own in thirty years, not a plantation. Where do I start? | PASS | - | site-orientation | 1.9 | 24 | From the data this site has, there are 42,348 source-linked records covering 962 entities across 302 cells. So the right starting point is a local reference mod... |
| t2 | Which trees here actually get their seed moved by animals, and by which animals? | PASS | - | interaction-pairs | 1.75 | 15 | From the data this site has, 150 named tree-animal pairs were recorded across 5,622 rows, and the most recorded pair is Yellow-browed Bulbul with *Persea macran... |
| t3 | Of those, which lose most of their seed to predators? I do not want to plant something that never recruits. | **FAIL** | `has_evidence` | interaction-pairs, compile-scientific-algebra-9b | 2.0 | 29 | The remaining data gap is that this site does not yet give a defensible ranking of which tree loses the most seed to predators from this view. The focal-tree fr... |
| t4 | Are any threatened species in that list worth including? | **FAIL** | `right_tool` | stratified-survey-summary | 1.5 | 57 | From the data this site has, this restoration summary route cannot split the local tree list by threat class, even though that survey covers 3,827 records of 17... |
| t5 | Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge. | **FAIL** | `rows` | local-site-evidence-search, interaction-pairs | 2.0 | 35 | From the data this site has, a cautious shortlist is *Persea macrantha*, *Heynea trijuga*, *Vateria indica*, *Myristica beddomei*, *Cullenia exarillata*, *Palaq... |
| t6 | Which of those would fail if the hornbills do not come back? | **FAIL** | `rows` | interaction-pairs | 2.0 | 25 | From the data this site has, reading “hornbills” as Malabar Grey Hornbill, the shortlist species most exposed are *Heynea trijuga* with 97 and 14 local pair rec... |
| t7 | What should I plant first to bring the hornbills in? | **FAIL** | `rows` | interaction-pairs | 2.0 | 16 | From the data this site has, plant *Myristica dactyloides* first, then *Heynea trijuga*, then *Persea macrantha*. Those are the trees recorded here with Malabar... |

### c5-what-to-replant / t3

User: Of those, which lose most of their seed to predators? I do not want to plant something that never recruits.

- `has_evidence`: no figure on a how-much / which / where question

```
The remaining data gap is that this site does not yet give a defensible ranking of which tree loses the most seed to predators from this view. The focal-tree frugivore visits and scans, the focal-tree seed-predator and seed-fate work. The rainforest tree-animal detections here show which trees and animals were recorded together. But that does not prove how much seed was actually lost or which tree recruits worst. If you want, I can check *Persea macrantha* or *Heynea trijuga* first and see whether the site holds a better tree-by-tree route for recruitment risk.
```

### c5-what-to-replant / t4

User: Are any threatened species in that list worth including?

- `right_tool`: ran ['stratified-survey-summary'], wanted one of ['entity-activity-profile', 'entity-record-map', 'group-record-map', 'interaction-pairs', 'matrix-profile', 'plot-indicator-profile']

```
From the data this site has, this restoration summary route cannot split the local tree list by threat class, even though that survey covers 3,827 records of 179 subjects across 132 named sites or plots from 2016 to 2023. Outside this data, the public sources I could verify today do not support a strong threatened-species shortlist from the trees already named in the pair table: *Heynea trijuga* is shown as Least Concern in the source trail I checked at https://en.wikipedia.org/wiki/Heynea_trijuga and https://powo.science.kew.org/taxon/urn:lsid:ipni.org:names:578838-1. I did not get a current authoritative threat page to verify *Persea macrantha* in this turn. If you want, I can check *Persea macrantha* next and tell you whether it is both locally recorded with dispersers and publicly documented as threatened.
```

### c5-what-to-replant / t5

User: Now give me a shortlist of eight to ten species, and be explicit about which ones come from this site's own records and which come from general knowledge.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, a cautious shortlist is *Persea macrantha*, *Heynea trijuga*, *Vateria indica*, *Myristica beddomei*, *Cullenia exarillata*, *Palaquium ellipticum*, *Syzygium densiflorum* and *Litsea floribunda*. Of these, only *Persea macrantha* and *Heynea trijuga* are backed here by focal-tree frugivore visits and scans, focal-tree seed-predator and seed-fate work. Rainforest tree-animal detections, and those records show animals and trees recorded together, not proof that seed was moved. From general knowledge: if you want a 10-species working list for a self-replacing wet forest, I would tentatively add *Ficus* spp. and *Diospyros* spp. because they often help year-round food supply and structural spread. But those two are general restoration picks here, not species I can yet tie to this site’s own interaction records. If you want, I can map where *Persea macrantha* is recorded.
```

### c5-what-to-replant / t6

User: Which of those would fail if the hornbills do not come back?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, reading “hornbills” as Malabar Grey Hornbill, the shortlist species most exposed are *Heynea trijuga* with 97 and 14 local pair records. *Persea macrantha* with 54 and 34; those are the shortlist trees this site actually recorded with that hornbill. *Myristica dactyloides* shows the strongest hornbill pairing overall at 132 and 104 records, but that species was not in the shortlist I gave you. These figures come from focal-tree frugivore visitation and scan observations, focal-tree seed-predator visits and seed fates. Rainforest tree and animal detections, and they are records of trees and hornbills being seen together, not proof that hornbills are essential for recruitment. If you want, I can map where *Heynea trijuga* is recorded.
```

### c5-what-to-replant / t7

User: What should I plant first to bring the hornbills in?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, plant *Myristica dactyloides* first, then *Heynea trijuga*, then *Persea macrantha*. Those are the trees recorded here with Malabar Grey Hornbill, with 132 and 104 records for *Myristica dactyloides*, 97 and 14 for *Heynea trijuga*. 54 and 34 for *Persea macrantha*. These figures come from focal-tree frugivore visitation and scan observations, focal-tree seed-predator visits and seed fates. Rainforest tree and animal detections, and they are records of hornbills and trees being seen together, not proof that planting them will bring hornbills back. From general knowledge: to pull large frugivores back, early planting usually works best when these food trees are clustered, protected from browsing. Mixed with faster shade-forming natives rather than planted as scattered singles. If you want, I can map where *Myristica dactyloides* is recorded.
```

## c6-what-grows-where - What is growing where: plots on a map, then one plot in detail

Session: `ecoanr-round6-contract-a-c6-what-grows-where`  |  categories: place, drill-down, traceability

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Show me what is growing where across the fragments. I want to see the plots on a map. | PASS | - | site-orientation | 1.5 | 19 | From the data this site has, this map shows 42,348 source-linked records for 962 entities across 302 squares inside the site boundary. It is a coverage map, not... |
| t2 | Which plot has the highest share of rainforest species? | **FAIL** | `next_step_in_prose`, `dead_end`, `right_tool`, `has_evidence`, `traceable` | - | 2.0 | 13 | Do you mean rainforest bird detections, or rainforest tree/plant records by plot? |
| t3 | Tell me more about that one. What is the stem density there, and what does the canopy look like? | PASS | - | plot-indicator-profile, visual-explain | 2.0 | 66 | From the data this site has, this is the largest rainforest-bird point on that view because no specific plot was identified. It is one acoustic measurement row ... |
| t4 | Where does that number come from? Show me the rows. | PASS | - | visual-explain | 1.85 | 11 | From the data this site has, that 1.0 value comes from one recorded row only, from the passive acoustic restoration monitoring data dated 12 December 2020. The ... |
| t5 | How does it compare against the benchmark plots? | PASS | - | plot-indicator-profile | 2.0 | 15 | From the data this site has, that point is at the maximum value in this acoustic plot set: 1.0, against an overall median of 0.892 and mean of 0.844 across 257 ... |
| t6 | Is that plot an outlier, or is it typical of the restored ones? | **FAIL** | `confidence` | visual-explain | 2.0 | 16 | From the data this site has, that point is not typical of the full acoustic plot set: it sits at the maximum value, 1.0, while the median across 257 plots is 0.... |

### c6-what-grows-where / t2

User: Which plot has the highest share of rainforest species?

- `next_step_in_prose`: answer names no move the user could make next
- `dead_end`: no next move in the prose and no buttons for the interface
- `right_tool`: ran ['nothing'], wanted one of ['group-record-map', 'matrix-profile', 'plot-indicator-profile', 'stratified-survey-summary']
- `has_evidence`: no figure on a how-much / which / where question
- `traceable`: no survey named and no path to the rows

```
Do you mean rainforest bird detections, or rainforest tree/plant records by plot?
```

### c6-what-grows-where / t6

User: Is that plot an outlier, or is it typical of the restored ones?

- `confidence`: no plain statement of how far to trust it

```
From the data this site has, that point is not typical of the full acoustic plot set: it sits at the maximum value, 1.0, while the median across 257 plots is 0.892 and the upper quartile is 0.989. I cannot say whether it is typical of restored plots specifically, because this result did not split restored plots from benchmark plots. It came back as one unspecified class only. If you want, I can check another plot measure that may separate restored and benchmark plots cleanly.
```

## c7-survey-budget - Where to spend a survey budget: drone days, hyperspectral, boots

Session: `ecoanr-round6-contract-a-c7-survey-budget`  |  categories: value-of-information, coverage-gap, uncertainty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Say I get twenty drone days next season. Where should I fly to learn the most? | **FAIL** | `jargon` | survey-priority-squares | 1.65 | 20 | From the data this site has, 102 squares have records but only 22 have documented survey work. So the best learning return is where that gap is widest: near Pud... |
| t2 | What are you basing that on? Places we have never looked, or places where you think something is happening? | **FAIL** | `join_rule_disclosed` | visual-explain | 1.9 | 21 | This explanation is for the top-ranked square on that map, because you did not point to one specific square. From the data this site has, the ranking is based o... |
| t3 | If it were a hyperspectral sensor instead, would the answer change? I would be looking for invasive cover. | PASS | - | coverage-versus-effort | 1.9 | 20 | From the data this site has, probably not much: this map shows records in 302 squares but explicit survey effort in only 42. So the main problem is still where ... |
| t4 | And if it is just me and two field assistants for thirty days on foot? | PASS | - | survey-priority-squares | 1.9 | 13 | From the data this site has, the answer stays broadly the same for a foot survey: start near Puduthottam, then Sirikundra, Thenmalai, Murugaali-BlackBridge. Pud... |
| t5 | Which of the three buys me the most for a restoration decision in the next two years? | PASS | - | coverage-versus-effort | 1.5 | 19 | From the data this site has, the 30 days on foot buys you the most for a restoration decision in the next two years, because records exist in 302 squares but ex... |
| t6 | Show me the gap map. Where is coverage thinnest relative to how much is going on there? | PASS | - | survey-priority-squares | 1.8 | 13 | From the data this site has, coverage is thinnest near Puduthottam, then Sirikundra, Thenmalai, Murugaali-BlackBridge, and Puduthottam_Coffee. The biggest gaps ... |
| t7 | Rank the top five places, with a reason for each that I could put in a proposal. | PASS | - | survey-priority-squares | 1.8 | 21 | From the data this site has, the top five are: 1. Puduthottam — 903 records but only 4 documented survey rows, so it is the strongest case for urgent gap-fillin... |

### c7-survey-budget / t1

User: Say I get twenty drone days next season. Where should I fly to learn the most?

- `jargon`: the visual

```
From the data this site has, 102 squares have records but only 22 have documented survey work. So the best learning return is where that gap is widest: near Puduthottam, then Sirikundra, Thenmalai, Murugaali-BlackBridge, and Puduthottam_Coffee. The visual shows Puduthottam with 903 records but only 4 documented survey rows; Sirikundra 186 and 6. Thenmalai 169 and 1; Murugaali-BlackBridge 316 and 1; Puduthottam_Coffee 469 and 21. This ranks where the data is thinnest, not where the ecology is richest. Weak effort records can also mean weak paperwork, not only weak field coverage. If you want, I can show the full map of coverage versus survey effort behind this ranking.
```

### c7-survey-budget / t2

User: What are you basing that on? Places we have never looked, or places where you think something is happening?

- `join_rule_disclosed`: asked how two things were matched, did not say

```
This explanation is for the top-ranked square on that map, because you did not point to one specific square. From the data this site has, the ranking is based on the gap between existing records and documented survey work, not on a claim that something ecological is happening there: in the top square, 903 records for 98 subjects fall inside that 1.1 km square. The visible rows behind it come from the tree and habitat structure survey. So this is a “least documented relative to records” ranking, not a “most interesting ecology” ranking. Weak effort records can also mean weak paperwork, not only that nobody went there. If you want, I can show the full coverage-versus-effort map behind that ranking.
```

## c8-monitoring-plan - A three year monitoring plan: does ANR beat active planting here

Session: `ecoanr-round6-contract-a-c8-monitoring-plan`  |  categories: design, data-request, gap-honesty

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here. | **FAIL** | `traceable` | site-orientation | 2.0 | 39 | **3-year design** From the data this site has, you can build this around permanent restoration plots and repeat bird and regeneration measurements, rather than ... |
| t2 | What can I reuse as a baseline instead of starting from scratch? | PASS | - | coverage-versus-effort | 1.85 | 16 | From the data this site has, the safest baseline to reuse is the part with documented survey effort, not all mapped records. The map shows records in 302 cells,... |
| t3 | What is the minimum I have to keep collecting so the old data stays comparable? | **FAIL** | `rows` | method-catalog | 2.0 | 18 | From the data this site has, this exact “minimum comparable set” is not listed in the methods view I checked. To keep old and new rounds comparable, the minimum... |
| t4 | What is missing entirely, that I would have to start measuring from zero? | **FAIL** | `names_alternative` | method-catalog | 1.9 | 16 | This site does not have a direct, ready before-after treatment series for ANR versus planting. So you would have to start measuring treatment identity, repeat p... |
| t5 | How many plots, and how many visits a year, to have a real chance of detecting a difference? | PASS | - | method-catalog | 1.85 | 22 | From the data this site has, there is no fitted site-specific power result for ANR versus planting. So I cannot defend one exact plot number from these records ... |
| t6 | Write it up as a one page plan I can hand to my team. | PASS | - | - | 2.0 | 20 | **One-page monitoring plan** From the data this site has, the strongest reusable baseline is in the cells with documented survey effort. The site also holds res... |
| t7 | And a list of the data I would need to request from the other groups working here. | PASS | - | - | 1.85 | 21 | From the data this site has, ask other groups for the exact fields that let you align their old and new work with your plots. Keep the request tight. Ask for ra... |

### c8-monitoring-plan / t1

User: Help me design three years of monitoring to answer whether assisted natural regeneration beats active planting here.

- `traceable`: no survey named and no path to the rows

```
**3-year design** From the data this site has, you can build this around permanent restoration plots and repeat bird and regeneration measurements, rather than starting from zero. 1. Set up matched plots in the same starting condition. Use paired blocks across the same slope, canopy, soil and disturbance level. In each block, keep one ANR plot and one active planting plot. Keep an untreated comparison only if operations allow it. 2. Measure the outcome that answers “beats”. Make one primary outcome only: native woody recruit density and survival by year 3. Keep secondary outcomes separate: species richness, height growth, canopy cover, shrub cover, seedling-to-sapling transition, invasive cover, and bird detections. 3. Fix the sampling unit now. Use permanent plots for vegetation. Use the same plot corners every round. Add fixed photo points and one short bird point-count station per plot cluster. 4. Sample on a repeat timetable. Do baseline before treatment. Then remeasure at 6, 12, 24 and 36 months. If mortality is a big concern, add a 3-month survival check in year 1. 5. Record treatment effort as well as outcomes. For ANR, record climber cutting, weeding, fire protection and gu
```

### c8-monitoring-plan / t3

User: What is the minimum I have to keep collecting so the old data stays comparable?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, this exact “minimum comparable set” is not listed in the methods view I checked. To keep old and new rounds comparable, the minimum is usually: the same permanent plot locations, the same plot size, the same census timing, the same species-level stem records, the same size class or DBH rule. The same effort record for each visit. From general knowledge: if any one of those shifts, you can still monitor change, but you weaken direct comparison with the older baseline. This methods view did not return a matching card for this question, so it does not prove the site lacks the information. It only shows that this route could not express the comparability rule directly. If you want, I can check one of the admitted method cards next: plot-area-normalised adult tree stocks, trait-qualified plot diversity, reference-community Chao similarity, canopy response with reference, benchmark-normalised canopy profile, closed-canopy enrichment counterfactual, detection-aware single-season occupancy, effort-visible-range support map, or effort-adjusted reporting-rate trend.
```

### c8-monitoring-plan / t4

User: What is missing entirely, that I would have to start measuring from zero?

- `names_alternative`: gap stated without naming what does exist

```
This site does not have a direct, ready before-after treatment series for ANR versus planting. So you would have to start measuring treatment identity, repeat plot outcomes, and repeat visit effort from zero for that comparison. This table shows 9 documented analysis designs, but only 2 are specified without needing extra implementation review. It is a methods view, not a fitted result. So it tells you what the site can structure, not that the ANR-versus-planting comparison has already been measured here. If you want, I can turn this into a short “start from zero” list with the minimum new fields to add in every plot visit.
```

## c9-seed-dispersal-design - Designing the dispersal side of a planting, from the recorded pairs

Session: `ecoanr-round6-contract-a-c9-seed-dispersal-design`  |  categories: network, design, method-disclosure

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I am designing the dispersal side of our planting. Who actually disperses what here? Give me the recorded tree and animal pairs, not the general story. | PASS | - | interaction-pairs | 1.5 | 19 | From the data this site has, there are 150 recorded tree-animal pairs across 5,622 rows. The most recorded are Yellow-browed Bulbul with *Persea macrantha* (629... |
| t2 | Which of the trees you just named have no recorded disperser at all? Those are the ones that worry me. | PASS | - | interaction-pairs | 2.0 | 20 | From the data this site has, none of the trees named last time are blank on this count. *Persea macrantha* has 31 recorded animal pairs across 3,144 rows, and *... |
| t3 | How much of that is real absence, and how much is nobody having watched that tree? Tell me how the watching effort differs between trees. | **FAIL** | `confidence` | coverage-versus-effort | 1.75 | 24 | This site does not have tree-by-tree watching effort for this question, so I cannot split “real absence” from “nobody watched that tree” honestly. From the data... |
| t4 | Of the dispersers on that list, which ones are actually recorded in the degraded fragments I would be restoring? | **FAIL** | `rows` | stratified-survey-summary, entity-activity-profile | 1.85 | 45 | From the data this site has, unrestored fragments were surveyed hard enough to matter: 23 unrestored sites and 154 visits in the bird recovery study, alongside ... |
| t5 | So if I plant for the dispersers I already have, what does the planting list look like? | PASS | - | interaction-pairs | 1.75 | 16 | From the data this site has, the defensible starter list for dispersers already recorded in unrestored fragments is short: *Heynea trijuga* and *Persea macranth... |
| t6 | Be straight with me. A bird recorded on a fruiting tree is not the same as that bird moving the seed. How much of this list rests on that assumption? | PASS | - | visual-explain | 1.5 | 14 | From the data this site has, all of that planting list rests on the weaker reading: the result is a ranked list of Southern Hill Myna recorded with those trees,... |
| t7 | What would my team have to record next season to turn these pairs into real dispersal evidence? | PASS | - | method-catalog | 2.0 | 25 | From the data this site has, there is no admitted frugivory method note in the site’s method catalogue. So this view cannot give you a site-issued dispersal pro... |

### c9-seed-dispersal-design / t3

User: How much of that is real absence, and how much is nobody having watched that tree? Tell me how the watching effort differs between trees.

- `confidence`: no plain statement of how far to trust it

```
This site does not have tree-by-tree watching effort for this question, so I cannot split “real absence” from “nobody watched that tree” honestly. From the data this site has, records occur in 302 squares inside the site boundary, but explicit survey effort is documented in only 42 squares. Outside those 42, a missing pair cannot support an absence claim, only a recording gap. This map is built from the frugivory, seed-predation, restoration-bird, threatened-tree and other survey records held here, and it shows coverage versus documented effort, not dispersal itself. If you want, I can map where *Persea macrantha* is recorded.
```

### c9-seed-dispersal-design / t4

User: Of the dispersers on that list, which ones are actually recorded in the degraded fragments I would be restoring?

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, unrestored fragments were surveyed hard enough to matter: 23 unrestored sites and 154 visits in the bird recovery study, alongside 23 restored and 23 benchmark sites. I can confirm Southern Hill Myna is recorded in that restoration-bird study. But this site is not cleanly splitting the other named dispersers by fragment type in the view I can defend here. So for them I cannot honestly say “recorded in degraded fragments” yet. These are still records written down by surveys, not proof of dispersal. The Southern Hill Myna profile mixes records from the restoration-bird study, tea bird counts, and fruiting-tree visitor observations. If you want, I can now check the other named dispersers one by one and tell you which of them the site can explicitly place in unrestored fragments.
```

## c10-budget-monitoring-plan - Three years of monitoring against a real budget

Session: `ecoanr-round6-contract-a-c10-budget-monitoring-plan`  |  categories: value-of-information, design, coverage-gap

| Turn | User | Result | Failed | Tools run | Lang | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- | --- |
| t1 | I have thirty field days and twenty drone days a year, for three years. Where do I start? Give me named places, not coordinates. | PASS | - | survey-priority-squares | 1.9 | 22 | From the data this site has, start with Puduthottam, Sirikundra, Thenmalai, Murugaali-BlackBridge. Puduthottam Coffee; the next named places are Manamboli, Vara... |
| t2 | Why those places? Show me the gap between what has been recorded there and what has actually been surveyed. | **FAIL** | `place_names` | visual-explain, coverage-versus-effort | 1.4 | 32 | From the data this site has, the gap is large: records occur in 302 squares, but explicit survey work is documented in only 42 squares. So places rise in the pr... |
| t3 | Split the thirty field days across those places for year one. | **FAIL** | `rows` | compile-scientific-algebra-9b | 1.1 | 26 | From the data this site has, for year one I would split the 30 field days like this: 5 days at Puduthottam; 4 each at Sirikundra, Thenmalai, and Murugaali-Black... |
| t4 | What do the drone days add that the field days do not, given what this site already measures? | **FAIL** | `traceable`, `confidence` | local-site-evidence-search, method-catalog | 1.7 | 28 | From the data this site has, the extra value from drone days is map-wide canopy context: the admitted methods here include canopy-cover response, open-versus-cl... |
| t5 | What can I already get from the existing surveys, so that I am not paying to collect it twice? | PASS | - | local-site-evidence-search, method-catalog | 2.0 | 26 | From the data this site has, do not pay again for sampled adult-tree count, basal area, aboveground carbon, and plot diversity by habitat, origin, conservation ... |
| t6 | If year one comes back and those gap squares are genuinely empty, what changes in year two? | PASS | - | local-site-evidence-search, method-catalog | 2.0 | 18 | From the data this site has, if year one shows those priority squares are genuinely empty, year two should shift from first-pass discovery to repeatable absence... |
| t7 | Write me the three year plan, year by year, and tell me what would make me abandon it. | PASS | - | local-site-evidence-search, method-catalog | 1.35 | 24 | From the data this site has, year 1 is gap-filling: put field days into the named thin-documentation places, use drone days for canopy context. Reuse the existi... |

### c10-budget-monitoring-plan / t2

User: Why those places? Show me the gap between what has been recorded there and what has actually been surveyed.

- `place_names`: places given as coordinates or squares, never by their name

```
From the data this site has, the gap is large: records occur in 302 squares, but explicit survey work is documented in only 42 squares. So places rise in the priority list where records exist but the survey behind them is thinly documented. For the earlier ranking, the stored explanation fell back to the largest ranked square because no one place was named. That square had 903 records covering 98 subjects, but only thin documented survey support behind it. This is a map of where the data is thinnest, not where the ecology is richest. Some of the gap may be missing survey paperwork rather than missing fieldwork. If you want, I can pull the named top places into a three-year field-and-drone schedule.
```

### c10-budget-monitoring-plan / t3

User: Split the thirty field days across those places for year one.

- `rows`: no table, list or row language where the user asked for specifics

```
From the data this site has, for year one I would split the 30 field days like this: 5 days at Puduthottam; 4 each at Sirikundra, Thenmalai, and Murugaali-BlackBridge. 3 each at Puduthottam Coffee and Manamboli; 2 each at Varatuparai, the second Thenmalai square, and Selaliparai 2; and 1 day at Pannimade. This is a planning split from the observed gap between records and documented survey work, so it points you to the thinnest data first, not necessarily the richest ecology. I also tried the scientific calculation route, but it stopped because it needed more specific record-level inputs than the ranking view provides. If you want, I can turn this into a month-by-month year-one field schedule with repeat visits built in.
```

### c10-budget-monitoring-plan / t4

User: What do the drone days add that the field days do not, given what this site already measures?

- `traceable`: no survey named and no path to the rows
- `confidence`: no plain statement of how far to trust it

```
From the data this site has, the extra value from drone days is map-wide canopy context: the admitted methods here include canopy-cover response, open-versus-closed canopy comparison. Range-support surfaces, while many other methods still depend on field plots or repeated checklists. The same site also shows 9 source-linked analysis methods, but only 2 are specified without extra implementation review. This table is about analysis designs, not finished results. The remaining data gap is that this site does not show a drone-specific method card. So I cannot claim more than canopy-scale spatial coverage from the evidence here. If you want, I can turn that into a practical split of what to do on drone days versus field days in year one.
```

