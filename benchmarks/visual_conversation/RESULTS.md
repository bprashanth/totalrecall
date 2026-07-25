# Visual conversation bench - results

Run: `run1-908663a`  |  endpoint: `http://172.17.0.1:7013`  |  started: 2026-07-25T18:31:40+05:30

**1/30 turns pass (3%)**, 0/7 conversations clean, readable share 93%, median latency 13.9s (max 36.1s).

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| drilldown | 0% |
| estimate | 0% |
| gk_usage | 0% |
| graph_comprehension | 0% |
| honest_limits | 25% |
| orientation | 0% |
| vocabulary | 0% |

## Pass rate by check

| Check | Pass rate |
| --- | --- |
| `gap_or_answer` | 0% |
| `jargon` | 13% |
| `numbers` | 20% |
| `general_knowledge_labelled` | 50% |
| `honest_gap` | 50% |
| `numbers_attributed` | 50% |
| `offers_alternative` | 50% |
| `no_keyword_refusal` | 73% |
| `vocab` | 80% |
| `no_machine_syntax` | 83% |
| `brevity` | 100% |
| `clarifying_questions` | 100% |
| `confidence_in_plain_words` | 100% |
| `estimate_given` | 100% |
| `no_transport_leak` | 100% |
| `non_empty` | 100% |
| `non_match_is_not_absence` | 100% |
| `rows` | 100% |
| `translates` | 100% |
| `visual_marker` | 100% |

## c1-orientation - Orientation and graph comprehension

Categories: orientation, graph_comprehension  |  session: `vcbench-run1-908663a-c1-orientation`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Hello, we are running a livelihoods programme in Valparai. What all data do you have for this place? | **FAIL** | `jargon` | 0.97 | 15 | From the onboarded site records, this visual shows the Valparai programme area and the indexed evidence currently available for it. It is useful for seeing where records are presen... |
| t2 | What is this map actually showing? Kindly explain in simple words na, I have to tell my field team. | **FAIL** | `jargon` | 0.81 | 15 | This map is showing the programme boundary and where indexed records are present inside it. In simple words, darker or denser areas mean more records have been entered there; it do... |
| t3 | This data is covering which years? And is it for the whole plateau or only some estates only? | **FAIL** | `jargon` | 0.61 | 12 | From the onboarded site records, the indexed source files in this map span 2015 to 2024, with different layers covering different subsets within that range. The map is drawn for th... |
| t4 | Out of all this, which one is most useful if I want to understand worker income? | **FAIL** | `jargon` | 0.92 | 14 | From the onboarded site records, the most directly useful source for worker income is the plantation wage dataset, because it tracks monthly wage rates. The estate labour census ca... |

### c1-orientation / t1 - failure detail

User: Hello, we are running a livelihoods programme in Valparai. What all data do you have for this place?

- `jargon`: indexed, onboarded, site records, this visual

```
From the onboarded site records, this visual shows the Valparai programme area and the indexed evidence currently available for it. It is useful for seeing where records are present and how coverage is distributed, but the density shown is only data coverage, not absence, outcome, or trend. This result uses synthetic test data, so it is not evidence about the real Valparai landscape.
```

### c1-orientation / t2 - failure detail

User: What is this map actually showing? Kindly explain in simple words na, I have to tell my field team.

- `jargon`: indexed

```
This map is showing the programme boundary and where indexed records are present inside it. In simple words, darker or denser areas mean more records have been entered there; it does not mean more problems, more people, or confirmed absence elsewhere. This explanation is for the whole map, not one clicked point, and this result is built from synthetic test datasets, so it is not evidence about the real Valparai field situation.
```

### c1-orientation / t3 - failure detail

User: This data is covering which years? And is it for the whole plateau or only some estates only?

- `jargon`: indexed, lineage, onboarded, site records

```
From the onboarded site records, the indexed source files in this map span 2015 to 2024, with different layers covering different subsets within that range. The map is drawn for the declared programme boundary shown in the result, not automatically for the whole Valparai plateau; from this lineage alone, I cannot claim it covers all estates. This result uses synthetic test data, so it is not evidence about the real Valparai area.
```

### c1-orientation / t4 - failure detail

User: Out of all this, which one is most useful if I want to understand worker income?

- `jargon`: onboarded, site records

```
From the onboarded site records, the most directly useful source for worker income is the plantation wage dataset, because it tracks monthly wage rates. The estate labour census can help as supporting context on worker numbers or composition, but by itself it is weaker for income than the wage series. This result still uses synthetic test data, so it is not evidence about real worker income in Valparai.
```

## c2-vocabulary - Vocabulary pickup: MGNREGA / mnrega / job work

Categories: vocabulary, orientation  |  session: `vcbench-run1-908663a-c2-vocabulary`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Kindly show me what public works data you are having for this area. | **FAIL** | `jargon`, `vocab[mgnrega]` | 1.0 | 14 | From public indexed records, this visual shows the area boundary and where source-linked records are available across the site. It reflects data coverage only, not absence or outco... |
| t2 | This mnrega thing, how many works are there in last few years? | **FAIL** | `jargon`, `no_keyword_refusal`, `numbers` | 1.0 | 13 | I could not plot the trend yet because the indexed metric does not recognise `mnrega works` as a registered measure here. Limitation: this pack is using synthetic test data, and th... |
| t3 | In our office we just say job work only. So tell me na, this job work is increasing or decreasing? | **FAIL** | `jargon`, `no_keyword_refusal` | 0.98 | 15 | I cannot say increasing or decreasing yet, because the local trend registry still does not recognise `job work` or `works` as a valid metric here. Limitation: this pack is using sy... |
| t4 | And which village is getting most of this job work? | **FAIL** | `no_keyword_refusal` | 1.0 | 10 | I can check village-wise, but `job work` is still ambiguous in the local registry. Do you want village with highest `number of works`, `expenditure`, `sanctioned amount`, or `perso... |
| t5 | Same thing for women workers, any data on that? | **FAIL** | `jargon`, `no_keyword_refusal`, `no_machine_syntax`, `gap_or_answer` | 1.0 | 11 | I could not confirm a women-workers trend yet, because the local registry does not recognise `women workers` as a valid metric name here. Limitation: this pack is using synthetic t... |

### c2-vocabulary / t1 - failure detail

User: Kindly show me what public works data you are having for this area.

- `jargon`: indexed, this visual
- `vocab[mgnrega]`: none of ['mgnrega', 'public work', 'public-works', 'employment guarantee'] appear in the answer

```
From public indexed records, this visual shows the area boundary and where source-linked records are available across the site. It reflects data coverage only, not absence or outcome. Limitation: this current result is based on synthetic test data, so it is not evidence about a real place.
```

### c2-vocabulary / t2 - failure detail

User: This mnrega thing, how many works are there in last few years?

- `jargon`: indexed, pack
- `no_keyword_refusal`: does not recognise
- `numbers`: no concrete figure

```
I could not plot the trend yet because the indexed metric does not recognise `mnrega works` as a registered measure here. Limitation: this pack is using synthetic test data, and the requested metric name needs to match the local registry. Which one do you want: number of works, sanctioned amount, expenditure, or persondays?
```

### c2-vocabulary / t3 - failure detail

User: In our office we just say job work only. So tell me na, this job work is increasing or decreasing?

- `jargon`: pack
- `no_keyword_refusal`: exact registered measure, registry still does not

```
I cannot say increasing or decreasing yet, because the local trend registry still does not recognise `job work` or `works` as a valid metric here. Limitation: this pack is using synthetic test data, and the trend can be checked only after we use the exact registered measure. Please tell me which one you mean: count of works, expenditure, sanctioned amount, or persondays?
```

### c2-vocabulary / t4 - failure detail

User: And which village is getting most of this job work?

- `no_keyword_refusal`: is still ambiguous in the

```
I can check village-wise, but `job work` is still ambiguous in the local registry. Do you want village with highest `number of works`, `expenditure`, `sanctioned amount`, or `persondays`?
```

### c2-vocabulary / t5 - failure detail

User: Same thing for women workers, any data on that?

- `jargon`: pack
- `no_keyword_refusal`: exact registered measure, registry does not
- `no_machine_syntax`: ` as a valid metric name here. L
- `gap_or_answer`: neither an answer nor an honest gap

```
I could not confirm a women-workers trend yet, because the local registry does not recognise `women workers` as a valid metric name here. Limitation: this pack is using synthetic test data, and we need the exact registered measure before saying whether data exists. Do you mean `female persondays`, `women participation rate`, or `number of women workers`?
```

## c3-drilldown - Drill-down to rows with understandable framing

Categories: drilldown  |  session: `vcbench-run1-908663a-c3-drilldown`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Which villages have the most survey visits? Show rows please. | **FAIL** | `jargon` | 0.96 | 18 | From the onboarded site records, this visual shows where record coverage exists and where explicit survey effort is documented. It does not support row-level village rankings from ... |
| t2 | There is one column called effort. What it means actually? | **FAIL** | `jargon` | 0.82 | 19 | From the stored visual, `effort` means explicit survey-effort denominators recorded by the source, not just record counts. In this explain trace, no specific row was identified, so... |
| t3 | Kindly turn it around and show which village we visited least. We have to plan next round. | **FAIL** | `jargon`, `vocab[village]`, `numbers` | 0.66 | 11 | From the onboarded site records, use this visual to spot cells with documented effort at the low end and prioritise the next survey round there. Cells without explicit effort may s... |
| t4 | Give me one line I can put in our monthly report about this. | **FAIL** | `jargon` | 0.2 | 8 | From the onboarded site records, explicit survey effort is documented in only a small part of the site, so the next round should prioritise villages or cells with the weakest docum... |

### c3-drilldown / t1 - failure detail

User: Which villages have the most survey visits? Show rows please.

- `jargon`: onboarded, pack, site records, this visual

```
From the onboarded site records, this visual shows where record coverage exists and where explicit survey effort is documented. It does not support row-level village rankings from the summary alone, and this pack is using synthetic test data rather than a real place.
```

### c3-drilldown / t2 - failure detail

User: There is one column called effort. What it means actually?

- `jargon`: indexed, pack

```
From the stored visual, `effort` means explicit survey-effort denominators recorded by the source, not just record counts. In this explain trace, no specific row was identified, so the service auto-selected the largest coverage cell and explained `coverage` there as a count of indexed event rows; this pack uses synthetic test data, so it is not evidence about a real place. Which row or village should I explain for the `effort` value?
```

### c3-drilldown / t3 - failure detail

User: Kindly turn it around and show which village we visited least. We have to plan next round.

- `jargon`: onboarded, pack, site records, this visual
- `vocab[village]`: none of ['village'] appear in the answer
- `numbers`: no concrete figure

```
From the onboarded site records, use this visual to spot cells with documented effort at the low end and prioritise the next survey round there. Cells without explicit effort may still have records, but they do not support a reliable “least visited” claim, and this pack is using synthetic test data rather than a real place.
```

### c3-drilldown / t4 - failure detail

User: Give me one line I can put in our monthly report about this.

- `jargon`: onboarded, site records

```
From the onboarded site records, explicit survey effort is documented in only a small part of the site, so the next round should prioritise villages or cells with the weakest documented effort; this view is based on synthetic test data and is not evidence about a real place.
```

## c4-estimate - Estimate with clarification near Kadamparai

Categories: estimate  |  session: `vcbench-run1-908663a-c4-estimate`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Near Kadamparai there is one empty square on the map. Can you estimate how many jobs will be there? | **FAIL** | `no_machine_syntax`, `vocab[kadamparai]` | 1.0 | 11 | Please send the empty square as `at:<lat>:<lon>` or share the map/link with that square selected. Then I will run the estimate workflow for jobs on that exact cell and return the m... |
| t2 | Yes, the square just below Kadamparai village. Take it as 10.255, 76.965. Kindly estimate for that one. | **FAIL** | `jargon`, `no_keyword_refusal`, `no_machine_syntax` | 0.85 | 36 | Estimate menu: supported `AOI baseline mean` (recommended, LOW confidence), `nearest surveyed cells` (LOW), and `spatial-neighbour regression` (LOW). Not supported: `effort-normali... |
| t3 | How much you are trusting this number? Be frank with me. | **FAIL** | `jargon`, `no_keyword_refusal`, `no_machine_syntax` | 0.54 | 17 | Frankly, I would trust it very little. The estimate has LOW confidence, it was generated from only 21 training cells, the held-out fit was weak (`R² -0.10`), and the pack itself sa... |
| t4 | If I put this in a proposal, what caveat I should write? | **FAIL** | `jargon`, `honest_gap` | 0.96 | 7 | Use this caveat: this is a generated, low-confidence estimate of `indexed record density`, not an observed count of jobs. It was derived from synthetic source layers only, the mode... |

### c4-estimate / t1 - failure detail

User: Near Kadamparai there is one empty square on the map. Can you estimate how many jobs will be there?

- `no_machine_syntax`: `at:<lat>:<lon>`
- `vocab[kadamparai]`: none of ['kadamparai'] appear in the answer

```
Please send the empty square as `at:<lat>:<lon>` or share the map/link with that square selected. Then I will run the estimate workflow for jobs on that exact cell and return the map result.
```

### c4-estimate / t2 - failure detail

User: Yes, the square just below Kadamparai village. Take it as 10.255, 76.965. Kindly estimate for that one.

- `jargon`: aoi, indexed, normalised, pack
- `no_keyword_refusal`: did not match `
- `no_machine_syntax`: R², ` (LOW). Not supported: `

```
Estimate menu: supported `AOI baseline mean` (recommended, LOW confidence), `nearest surveyed cells` (LOW), and `spatial-neighbour regression` (LOW). Not supported: `effort-normalised rate transfer` because the target cell has no indexed effort rows. Also, this pack did not match `jobs`; it defaulted to `indexed record density`. The modelled estimate suggests an 80% interval of `0.238095–13.857143` indexed event rows per cell; this is generated, not observed. Confidence is LOW because of `21 training cells; leave-one-out residual spread 13.6 indexed event rows per cell at the 80% level; leave-one-out R² -0.10; signal-to-noise 1.03`; it used the `events` and `cells` planes from `syn-estate-labour`, `syn-mgnrega`, and `syn-migration`. The best improvements are to survey this cell directly and add nearby effort rows; also note this cell already has an observed value in the pack, so that obs
```

### c4-estimate / t3 - failure detail

User: How much you are trusting this number? Be frank with me.

- `jargon`: indexed, pack
- `no_keyword_refusal`: did not match any
- `no_machine_syntax`: R², `), and the pack itself says thi

```
Frankly, I would trust it very little. The estimate has LOW confidence, it was generated from only 21 training cells, the held-out fit was weak (`R² -0.10`), and the pack itself says this interval is broad. Also, this is not a jobs estimate at all: your word `jobs` did not match any pack quantity, so it defaulted to `indexed record density`, and this cell already has an observed value in the pack, which should be preferred over the estimate.
```

### c4-estimate / t4 - failure detail

User: If I put this in a proposal, what caveat I should write?

- `jargon`: indexed, pack
- `honest_gap`: no plain statement that the data is missing

```
Use this caveat: this is a generated, low-confidence estimate of `indexed record density`, not an observed count of jobs. It was derived from synthetic source layers only, the model fit was weak, and the target cell already has an observed pack value that should be preferred where reporting allows. If you want, I can draft this as one proposal-ready sentence in formal NGO language.
```

## c5-honest-limits - Honest limits: school data is absent

Categories: honest_limits  |  session: `vcbench-run1-908663a-c5-honest-limits`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | How many children go to school here? We need it for our education programme. | **FAIL** | `jargon`, `offers_alternative` | 0.98 | 17 | From the onboarded site records, I can only see overall indexed evidence coverage for this area, not a direct count of school-going children. This visual is based on synthetic test... |
| t2 | So you are saying there is no school data at all? Or maybe it is there but not matching? | **FAIL** | `jargon`, `no_keyword_refusal` | 1.0 | 16 | From the onboarded site records, I am not saying school data is absent everywhere. I am saying this result is only a site-orientation view of indexed evidence coverage, and for thi... |
| t3 | Then what all is the closest to household level information you are having? | **FAIL** | `jargon` | 0.81 | 14 | From the onboarded site records, the closest thing to household-level information appears to be a household survey source, along with estate labour, migration, wages, and public-wo... |
| t4 | Fine. Kindly note it down that we need school enrolment data for Valparai. | PASS | - | 1.0 | 5 | Noted. For Valparai, the remaining data gap is school enrolment data for the education programme. Once you have that file or source, I can check coverage and summarise it. |

### c5-honest-limits / t1 - failure detail

User: How many children go to school here? We need it for our education programme.

- `jargon`: indexed, onboarded, site records, this visual
- `offers_alternative`: gap stated without saying what data does exist

```
From the onboarded site records, I can only see overall indexed evidence coverage for this area, not a direct count of school-going children. This visual is based on synthetic test data, so it is not evidence about a real place. If you have a school enrolment file or a named education metric for this site, share that and I’ll check it directly.
```

### c5-honest-limits / t2 - failure detail

User: So you are saying there is no school data at all? Or maybe it is there but not matching?

- `jargon`: indexed, lineage, onboarded, pack, site records
- `no_keyword_refusal`: exact metric name

```
From the onboarded site records, I am not saying school data is absent everywhere. I am saying this result is only a site-orientation view of indexed evidence coverage, and for this whole-result lineage there is no school metric or school-count row behind it. This pack is also synthetic test data, so it cannot support a real estimate for your programme. If you have a school enrolment sheet or the exact metric name you want, send that next.
```

### c5-honest-limits / t3 - failure detail

User: Then what all is the closest to household level information you are having?

- `jargon`: indexed, lineage, onboarded, pack, site records

```
From the onboarded site records, the closest thing to household-level information appears to be a household survey source, along with estate labour, migration, wages, and public-works sources. But this lineage only tells us those source types are indexed here; it does not expose a real household table or a school-going-children field, and this pack is synthetic test data. If you have a household survey file, upload it and I’ll profile it first.
```

## c6-general-knowledge - General knowledge may frame, numbers must come from data

Categories: gk_usage  |  session: `vcbench-run1-908663a-c6-general-knowledge`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Is 10000 rupees a month good income for a tea worker? | **FAIL** | `no_machine_syntax` | 0.74 | 10 | In most parts of India, `Rs 10,000` per month is generally a low income, not a good one, especially by `2026` living costs. For a tea worker, whether it is “good” depends on what i... |
| t2 | What the actual data is saying about tea worker wages here? | **FAIL** | `jargon`, `no_keyword_refusal`, `numbers` | 1.0 | 21 | This visual does not show wage evidence yet. The indexed metric did not match “tea worker wages”, and the returned pack is synthetic test data, so it is not evidence about a real p... |
| t3 | So compared to what you said generally, this is high or low? | **FAIL** | `jargon`, `general_knowledge_labelled`, `numbers_attributed` | 1.0 | 9 | Low. Compared to the general benchmark I mentioned, `Rs 10,000/month` is usually on the low side, not high. But that is only a general comparison, not site evidence from this pack,... |
| t4 | Can you write two lines for our donor about this wage situation? | **FAIL** | `jargon`, `numbers_attributed` | 0.68 | 8 | From the available site pack, we do not yet have a verified wage metric for tea workers, so a firm evidence-based wage conclusion is not possible. On general comparison, `Rs 10,000... |

### c6-general-knowledge / t1 - failure detail

User: Is 10000 rupees a month good income for a tea worker?

- `no_machine_syntax`: ` living costs. For a tea worker

```
In most parts of India, `Rs 10,000` per month is generally a low income, not a good one, especially by `2026` living costs. For a tea worker, whether it is “good” depends on what is included: housing, ration, medical support, bonuses, and whether the work is permanent or seasonal. General ecological context: Tea landscapes often depend on large resident labour forces, and worker wellbeing directly affects plantation stability, local biodiversity management, and long-term land stewardship. If `Rs 10,000` is cash wage only and food or housing is also provided, it may be barely manageable in some estates. If it is the total monthly income for a household, it is usually poor. Do you want a quick comparison with minimum wages and living costs in a specific state like Assam or West Bengal?
```

### c6-general-knowledge / t2 - failure detail

User: What the actual data is saying about tea worker wages here?

- `jargon`: indexed, pack, this visual
- `no_keyword_refusal`: exact metric name
- `numbers`: no concrete figure

```
This visual does not show wage evidence yet. The indexed metric did not match “tea worker wages”, and the returned pack is synthetic test data, so it is not evidence about a real place. If you have the exact metric name or source table used here, I can check that next.
```

### c6-general-knowledge / t3 - failure detail

User: So compared to what you said generally, this is high or low?

- `jargon`: pack
- `general_knowledge_labelled`: general context not marked as general
- `numbers_attributed`: unattributed figures: ['10000']

```
Low. Compared to the general benchmark I mentioned, `Rs 10,000/month` is usually on the low side, not high. But that is only a general comparison, not site evidence from this pack, because we still do not have a resolved wage metric here.
```

### c6-general-knowledge / t4 - failure detail

User: Can you write two lines for our donor about this wage situation?

- `jargon`: site pack
- `numbers_attributed`: unattributed figures: ['10000']

```
From the available site pack, we do not yet have a verified wage metric for tea workers, so a firm evidence-based wage conclusion is not possible. On general comparison, `Rs 10,000` per month appears low, but this should be treated as a provisional benchmark, not a site-confirmed finding.
```

## c7-migration - Out-migration: orientation, drill-down and the user's own words

Categories: orientation, drilldown, vocabulary  |  session: `vcbench-run1-908663a-c7-migration`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | What all is happening with people leaving this area for work? Any data on that? | **FAIL** | `jargon` | 0.78 | 17 | This visual only orients us to what evidence is indexed for the area. It does not show work migration or people leaving for jobs; it shows coverage of mapped records, and this pack... |
| t2 | This migration, which occupation is leaving most? | **FAIL** | `jargon`, `numbers` | 1.0 | 16 | From the available site pack, I cannot say which occupation is leaving most. The visual check shows there is no onboarded method or admitted migration analysis here, and this pack ... |
| t3 | Show me the rows na. | **FAIL** | `jargon` | 0.8 | 18 | There are no source rows behind that migration answer. This lineage is for the whole result, and it shows `0` contributing rows from the site method catalog, because no source-link... |
| t4 | And the tea plucker people, same thing for them? | **FAIL** | `jargon` | 1.0 | 12 | From the available site pack, same issue applies for tea pluckers also. There is no onboarded, source-linked method or admitted migration evidence for that occupation here, and thi... |
| t5 | Summarise in 3 simple points for our team meeting. | **FAIL** | `jargon` | 0.8 | 6 | 1. From the available site pack, we do not have usable evidence on people leaving this area for work. 2. We also cannot say which occupation is leaving most, including tea pluckers... |

### c7-migration / t1 - failure detail

User: What all is happening with people leaving this area for work? Any data on that?

- `jargon`: indexed, pack, this visual

```
This visual only orients us to what evidence is indexed for the area. It does not show work migration or people leaving for jobs; it shows coverage of mapped records, and this pack also says the current result is synthetic test data, not evidence about a real place.
```

### c7-migration / t2 - failure detail

User: This migration, which occupation is leaving most?

- `jargon`: onboarded, pack, site pack, the visual
- `numbers`: no concrete figure

```
From the available site pack, I cannot say which occupation is leaving most. The visual check shows there is no onboarded method or admitted migration analysis here, and this pack is synthetic test data, not real-place evidence.
```

### c7-migration / t3 - failure detail

User: Show me the rows na.

- `jargon`: lineage, onboarded

```
There are no source rows behind that migration answer. This lineage is for the whole result, and it shows `0` contributing rows from the site method catalog, because no source-linked migration method cards are onboarded here.
```

### c7-migration / t4 - failure detail

User: And the tea plucker people, same thing for them?

- `jargon`: onboarded, pack, site pack

```
From the available site pack, same issue applies for tea pluckers also. There is no onboarded, source-linked method or admitted migration evidence for that occupation here, and this pack is synthetic test data, not real-place evidence.
```

### c7-migration / t5 - failure detail

User: Summarise in 3 simple points for our team meeting.

- `jargon`: onboarded, pack, site pack

```
1. From the available site pack, we do not have usable evidence on people leaving this area for work. 2. We also cannot say which occupation is leaving most, including tea pluckers, because no source-linked migration method or rows are onboarded here. 3. The current pack is synthetic test data, so it should not be used as real evidence for this site.
```

