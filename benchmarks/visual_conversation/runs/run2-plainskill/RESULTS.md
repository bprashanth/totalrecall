# Visual conversation bench - results

Run: `run2-plainskill`  |  endpoint: `http://172.17.0.1:7013`  |  started: 2026-07-25T18:44:36+05:30

**18/30 turns pass (60%)**, 0/7 conversations clean, readable share 90%, median latency 18.0s (max 41.5s).

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| drilldown | 67% |
| estimate | 25% |
| gk_usage | 75% |
| graph_comprehension | 25% |
| honest_limits | 75% |
| orientation | 64% |
| vocabulary | 80% |

## Pass rate by check

| Check | Pass rate |
| --- | --- |
| `confidence_in_plain_words` | 50% |
| `general_knowledge_labelled` | 50% |
| `numbers` | 60% |
| `jargon` | 73% |
| `no_keyword_refusal` | 97% |
| `no_machine_syntax` | 97% |
| `brevity` | 100% |
| `clarifying_questions` | 100% |
| `estimate_given` | 100% |
| `gap_or_answer` | 100% |
| `honest_gap` | 100% |
| `no_transport_leak` | 100% |
| `non_empty` | 100% |
| `non_match_is_not_absence` | 100% |
| `numbers_attributed` | 100% |
| `offers_alternative` | 100% |
| `rows` | 100% |
| `translates` | 100% |
| `visual_marker` | 100% |
| `vocab` | 100% |

## c1-orientation - Orientation and graph comprehension

Categories: orientation, graph_comprehension  |  session: `vcbench-run2-plainskill-c1-orientation`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Hello, we are running a livelihoods programme in Valparai. What all data do you have for this place? | **FAIL** | `jargon` | 0.8 | 23 | This map shows the Valparai area boundary and where the data this site holds is concentrated. From the onboarded site records, it currently covers 164 source-linked records for 13 ... |
| t2 | What is this map actually showing? Kindly explain in simple words na, I have to tell my field team. | **FAIL** | `jargon` | 0.65 | 19 | In simple words, this map is showing the Valparai boundary and where the data this site holds is present inside that area. It is not showing livelihood status, risk, need, or absen... |
| t3 | This data is covering which years? And is it for the whole plateau or only some estates only? | PASS | - | 0.49 | 16 | This map combines several time spans, not one single year: estate labour census 2015-2024, wage records 2017-2024, migration records 2018-2024, public works records 2019-2024, and ... |
| t4 | Out of all this, which one is most useful if I want to understand worker income? | **FAIL** | `jargon` | 1.0 | 16 | This site does not yet have a checked summary saying which dataset is best for worker income, so I cannot rank them from onboarded evidence alone. Also, this is synthetic test data... |

### c1-orientation / t1 - failure detail

User: Hello, we are running a livelihoods programme in Valparai. What all data do you have for this place?

- `jargon`: onboarded, site records

```
This map shows the Valparai area boundary and where the data this site holds is concentrated. From the onboarded site records, it currently covers 164 source-linked records for 13 entities across 22 cells. This is only a test view using synthetic data, so treat it as a software demonstration, not real evidence for Valparai.
```

### c1-orientation / t2 - failure detail

User: What is this map actually showing? Kindly explain in simple words na, I have to tell my field team.

- `jargon`: indexed

```
In simple words, this map is showing the Valparai boundary and where the data this site holds is present inside that area. It is not showing livelihood status, risk, need, or absence of people; it is only showing coverage of indexed records from the estate labour census, the household survey, the public works records, migration records, and wage records. This explanation is for the whole map, not one clicked point, and all of it is synthetic test data, so please do not use it as real field evidence.
```

### c1-orientation / t4 - failure detail

User: Out of all this, which one is most useful if I want to understand worker income?

- `jargon`: onboarded

```
This site does not yet have a checked summary saying which dataset is best for worker income, so I cannot rank them from onboarded evidence alone. Also, this is synthetic test data, not real Valparai evidence. Do you mean plantation wages only, or total household income from all sources?
```

## c2-vocabulary - Vocabulary pickup: MGNREGA / mnrega / job work

Categories: vocabulary, orientation  |  session: `vcbench-run2-plainskill-c2-vocabulary`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Kindly show me what public works data you are having for this area. | PASS | - | 1.0 | 21 | This map shows the area boundary and where the data this site holds has records. Right now it is an overview: it maps 164 records across 22 cells, so it shows coverage of records, ... |
| t2 | This mnrega thing, how many works are there in last few years? | **FAIL** | `no_keyword_refusal`, `numbers` | 1.0 | 19 | I could not pull a year-wise trend yet because this site does not recognise “MGNREGA works” as a named time-series. This is only synthetic test data, not evidence about a real plac... |
| t3 | In our office we just say job work only. So tell me na, this job work is increasing or decreasing? | PASS | - | 1.0 | 18 | I still cannot say increasing or decreasing from this site, because the year-wise public works series is not recognised yet, even when I tested persondays, meaning days of paid wor... |
| t4 | And which village is getting most of this job work? | PASS | - | 1.0 | 14 | Do you mean village with the most `works`, or village with the most `persondays`, meaning days of paid work? |
| t5 | Same thing for women workers, any data on that? | PASS | - | 1.0 | 13 | I could not find a named series for women workers in the data this site holds. So at the moment I cannot show a trend or count for women’s job work from here. This is only syntheti... |

### c2-vocabulary / t2 - failure detail

User: This mnrega thing, how many works are there in last few years?

- `no_keyword_refusal`: does not recognise
- `numbers`: no concrete figure

```
I could not pull a year-wise trend yet because this site does not recognise “MGNREGA works” as a named time-series. This is only synthetic test data, not evidence about a real place. Do you mean number of works, or persondays, meaning days of paid work?
```

## c3-drilldown - Drill-down to rows with understandable framing

Categories: drilldown  |  session: `vcbench-run2-plainskill-c3-drilldown`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Which villages have the most survey visits? Show rows please. | PASS | - | 0.73 | 22 | This map shows where records exist and where survey effort is actually documented. From the data this site holds, records appear across 22 grid squares, but explicit survey visits ... |
| t2 | There is one column called effort. What it means actually? | PASS | - | 0.95 | 20 | Here, `effort` means the total documented survey work added up for a map square, not the number of species records. Because no specific place was pointed out, this explanation is f... |
| t3 | Kindly turn it around and show which village we visited least. We have to plan next round. | **FAIL** | `jargon` | 0.8 | 19 | This map can show where documented survey work is lowest, but not name the least-visited village from this view alone. From the onboarded site records, explicit survey effort is re... |
| t4 | Give me one line I can put in our monthly report about this. | **FAIL** | `jargon` | 0.09 | 7 | From the onboarded site records, documented survey work is concentrated in only 3 grid squares, so the next survey round should prioritise places with no recorded effort; this is s... |

### c3-drilldown / t3 - failure detail

User: Kindly turn it around and show which village we visited least. We have to plan next round.

- `jargon`: onboarded, site records

```
This map can show where documented survey work is lowest, but not name the least-visited village from this view alone. From the onboarded site records, explicit survey effort is recorded in only 3 grid squares, so planning the next round should focus first on places with no documented effort. This is synthetic test data, not evidence about a real place.
```

### c3-drilldown / t4 - failure detail

User: Give me one line I can put in our monthly report about this.

- `jargon`: onboarded, site records

```
From the onboarded site records, documented survey work is concentrated in only 3 grid squares, so the next survey round should prioritise places with no recorded effort; this is synthetic test data, not a real site finding.
```

## c4-estimate - Estimate with clarification near Kadamparai

Categories: estimate  |  session: `vcbench-run2-plainskill-c4-estimate`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Near Kadamparai there is one empty square on the map. Can you estimate how many jobs will be there? | **FAIL** | `no_machine_syntax` | 1.0 | 24 | To estimate jobs for that empty square, I need the exact square reference from the map. Please send the map click as `at:<lat>:<lon>` for that Kadamparai square, or share the squar... |
| t2 | Yes, the square just below Kadamparai village. Take it as 10.255, 76.965. Kindly estimate for that one. | **FAIL** | `confidence_in_plain_words` | 0.8 | 12 | I can estimate it, but “jobs” has two different meanings in this site’s data: public-works workdays, or estate payroll jobs. Which one do you want for `10.255, 76.965`? |
| t3 | How much you are trusting this number? Be frank with me. | **FAIL** | `jargon` | 0.78 | 25 | I have not given a number yet, so I cannot honestly rate its trust level. From the onboarded site records, this can only be a worked-out estimate, not a counted value on the ground... |
| t4 | If I put this in a proposal, what caveat I should write? | PASS | - | 1.0 | 6 | Use a caveat like this: “This figure is a modelled estimate for the map square near Kadamparai, not a direct count from that square. It is inferred from nearby surveyed squares and... |

### c4-estimate / t1 - failure detail

User: Near Kadamparai there is one empty square on the map. Can you estimate how many jobs will be there?

- `no_machine_syntax`: `at:<lat>:<lon>`

```
To estimate jobs for that empty square, I need the exact square reference from the map. Please send the map click as `at:<lat>:<lon>` for that Kadamparai square, or share the square ID if the map shows one. Once I have that, I can work out the jobs estimate from the nearby surveyed squares and the employment records this site holds.
```

### c4-estimate / t2 - failure detail

User: Yes, the square just below Kadamparai village. Take it as 10.255, 76.965. Kindly estimate for that one.

- `confidence_in_plain_words`: no everyday statement of how much to trust the number

```
I can estimate it, but “jobs” has two different meanings in this site’s data: public-works workdays, or estate payroll jobs. Which one do you want for `10.255, 76.965`?
```

### c4-estimate / t3 - failure detail

User: How much you are trusting this number? Be frank with me.

- `jargon`: onboarded, site records

```
I have not given a number yet, so I cannot honestly rate its trust level. From the onboarded site records, this can only be a worked-out estimate, not a counted value on the ground. If you pick `public-works workdays` or `estate payroll jobs`, I will run it and then tell you plainly whether it is rough or reasonably solid, based on how many nearby squares had data and how well the method matched held-back squares.
```

## c5-honest-limits - Honest limits: school data is absent

Categories: honest_limits  |  session: `vcbench-run2b-plainskill-c5-honest-limits`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | How many children go to school here? We need it for our education programme. | PASS | - | 1.0 | 41 | This map shows the records available here, but they cover livelihoods, not children attending school, so I cannot give a school-going count from this site data. It also uses synthe... |
| t2 | So you are saying there is no school data at all? Or maybe it is there but not matching? | **FAIL** | `jargon` | 0.9 | 19 | From the data this site holds, it looks like a true gap, not just a naming mismatch. I checked the full site records and the estimate catalogue: they include estate labour, public ... |
| t3 | Then what all is the closest to household level information you are having? | PASS | - | 0.72 | 15 | This map shows the closest thing to household-level information here is the household survey effort itself, and that is documented in only 3 cells. The other data are still useful,... |
| t4 | Fine. Kindly note it down that we need school enrolment data for Valparai. | PASS | - | 1.0 | 7 | Noted in this conversation: for Valparai, the missing priority data is school enrolment. If you want, I can next help frame the exact fields needed, such as school name, age, sex, ... |

### c5-honest-limits / t2 - failure detail

User: So you are saying there is no school data at all? Or maybe it is there but not matching?

- `jargon`: site records, this visual

```
From the data this site holds, it looks like a true gap, not just a naming mismatch. I checked the full site records and the estimate catalogue: they include estate labour, public works, out-migration, wages, and some household survey effort, but nothing on school enrolment or attendance. This visual still uses synthetic test data, so it is only showing the structure of the records, not evidence about a real place.
```

## c6-general-knowledge - General knowledge may frame, numbers must come from data

Categories: gk_usage  |  session: `vcbench-run2b-plainskill-c6-general-knowledge`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Is 10000 rupees a month good income for a tea worker? | PASS | - | 0.75 | 18 | Usually, no. For a tea worker in India, `Rs 10,000` a month is generally a low cash income, and it will be hard to call it “good” unless the estate is also giving housing, rations,... |
| t2 | What the actual data is saying about tea worker wages here? | PASS | - | 0.8 | 18 | The map only shows where this site has records, not tea worker wages themselves. From the data this site holds, there are records spread across the area, but this view cannot say w... |
| t3 | So compared to what you said generally, this is high or low? | **FAIL** | `jargon`, `general_knowledge_labelled` | 1.0 | 9 | Low, from a general India tea-worker point of view. From the onboarded site records, we still cannot compare properly because this site does not show tea wage data, and the test ma... |
| t4 | Can you write two lines for our donor about this wage situation? | PASS | - | 0.43 | 8 | From the data this site holds, we do not yet have direct tea worker wage records for this place, so no site-based wage claim can be made. As a general benchmark only, `Rs 10,000` a... |

### c6-general-knowledge / t3 - failure detail

User: So compared to what you said generally, this is high or low?

- `jargon`: onboarded, site records
- `general_knowledge_labelled`: general context not marked as general

```
Low, from a general India tea-worker point of view. From the onboarded site records, we still cannot compare properly because this site does not show tea wage data, and the test map is not a real place. Do you want me to check current public wage evidence for a specific tea state such as Assam, West Bengal, or Tamil Nadu?
```

## c7-migration - Out-migration: orientation, drill-down and the user's own words

Categories: orientation, drilldown, vocabulary  |  session: `vcbench-run2b-plainskill-c7-migration`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | What all is happening with people leaving this area for work? Any data on that? | PASS | - | 0.9 | 23 | This map shows where the site has livelihood-related records across the area, so it helps locate where data exists on work and movement. From this view alone, it does not show a di... |
| t2 | This migration, which occupation is leaving most? | **FAIL** | `numbers` | 1.0 | 21 | This map only shows where livelihood records exist across the area; it does not split people leaving by occupation. So, from this view, I cannot say which occupation is leaving mos... |
| t3 | Show me the rows na. | PASS | - | 0.95 | 19 | For this full map, there are no row-level lines shown here because it is only an area overview, not a table for one cell or one record. It is built from synthetic household survey,... |
| t4 | And the tea plucker people, same thing for them? | PASS | - | 0.8 | 15 | Yes, for tea plucker people there are separate records in the map, and it shows 5 source-linked records in the target area. This still shows only where records exist, not how many ... |
| t5 | Summarise in 3 simple points for our team meeting. | PASS | - | 0.8 | 16 | 1. The site does have livelihood and out-migration related records spread across the area, so there is some data to work with. 2. What we have seen so far shows where records exist... |

### c7-migration / t2 - failure detail

User: This migration, which occupation is leaving most?

- `numbers`: no concrete figure

```
This map only shows where livelihood records exist across the area; it does not split people leaving by occupation. So, from this view, I cannot say which occupation is leaving most. Do you mean the work people were doing here before leaving, or the work they went out for?
```

