# Visual conversation bench - results

Run: `run3-cellsquare`  |  endpoint: `http://172.17.0.1:7013`  |  started: 2026-07-26T00:26:55+05:30

**24/30 turns pass (80%)**, 2/7 conversations clean, readable share 63%, median latency 16.0s (max 59.8s).

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| drilldown | 78% |
| estimate | 75% |
| gk_usage | 100% |
| graph_comprehension | 100% |
| honest_limits | 75% |
| orientation | 79% |
| vocabulary | 70% |

## Pass rate by check

| Check | Pass rate |
| --- | --- |
| `gap_or_answer` | 0% |
| `non_match_is_not_absence` | 0% |
| `honest_gap` | 50% |
| `numbers` | 60% |
| `jargon` | 97% |
| `brevity` | 100% |
| `clarifying_questions` | 100% |
| `confidence_in_plain_words` | 100% |
| `estimate_given` | 100% |
| `general_knowledge_labelled` | 100% |
| `no_keyword_refusal` | 100% |
| `no_machine_syntax` | 100% |
| `no_transport_leak` | 100% |
| `non_empty` | 100% |
| `numbers_attributed` | 100% |
| `offers_alternative` | 100% |
| `rows` | 100% |
| `translates` | 100% |
| `visual_marker` | 100% |
| `vocab` | 100% |

## c1-orientation - Orientation and graph comprehension

Categories: orientation, graph_comprehension  |  session: `vcbench-run3-cellsquare-c1-orientation`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Hello, we are running a livelihoods programme in Valparai. What all data do you have for this place? | PASS | - | 0.69 | 16 | From the data this site has, Valparai is covered by a map of recorded livelihoods information, with records spread across the area rather than tied to just one point. It is useful ... |
| t2 | What is this map actually showing? Kindly explain in simple words na, I have to tell my field team. | PASS | - | 0.65 | 16 | This map is showing where the data this site has is concentrated, not where livelihoods are best or worst. Because you did not point to one square, the explanation is for the busie... |
| t3 | This data is covering which years? And is it for the whole plateau or only some estates only? | PASS | - | 0.47 | 17 | From the data this site has, the records shown here run from 2018 to 2024, based on the public-works records and out-migration records behind the map. The map shows records spread ... |
| t4 | Out of all this, which one is most useful if I want to understand worker income? | PASS | - | 0.58 | 13 | From the data this site has, the most useful starting point for worker income is the daily wage chart, because it shows recorded wage values through time rather than just where rec... |

## c2-vocabulary - Vocabulary pickup: MGNREGA / mnrega / job work

Categories: vocabulary, orientation  |  session: `vcbench-run3-cellsquare-c2-vocabulary`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Kindly show me what public works data you are having for this area. | PASS | - | 0.8 | 24 | From the data this site has, the map shows records in 22 map squares, but documented survey effort in only 3 squares. So this shows where public-works-related records are present, ... |
| t2 | This mnrega thing, how many works are there in last few years? | **FAIL** | `numbers` | 0.89 | 21 | From the data this site has, I cannot show a year-wise count of MGNREGA works from this chart because that count is not recorded as a time measure here. What the records can plot o... |
| t3 | In our office we just say job work only. So tell me na, this job work is increasing or decreasing? | PASS | - | 0.93 | 16 | From the data this site has, I read “job work” as paid days per month, meaning days of paid work, and this chart shows 96 monthly values through time. It lets you inspect the patte... |
| t4 | And which village is getting most of this job work? | PASS | - | 0.83 | 12 | From the data this site has, I cannot tell which village is getting the most public-works job work from this summary, because the village-wise public-works records here do not line... |
| t5 | Same thing for women workers, any data on that? | **FAIL** | `gap_or_answer` | 0.75 | 14 | From the data this site has, there is a women workers field in the estate labour records, but this summary cannot show it cleanly because the worker records and the matching survey... |

### c2-vocabulary / t2 - failure detail

User: This mnrega thing, how many works are there in last few years?

- `numbers`: no concrete figure

```
From the data this site has, I cannot show a year-wise count of MGNREGA works from this chart because that count is not recorded as a time measure here. What the records can plot over time is the daily wage, the overtime rate, or paid days per month. This is synthetic test data, so treat it as a demo of what can be charted here, not evidence about a real place.
```

### c2-vocabulary / t5 - failure detail

User: Same thing for women workers, any data on that?

- `gap_or_answer`: neither an answer nor an honest gap

```
From the data this site has, there is a women workers field in the estate labour records, but this summary cannot show it cleanly because the worker records and the matching survey effort do not line up. So yes, there is some women workers data recorded here, but not in a form that this map can summarise reliably. This is synthetic test data, so treat it as a demo of the gap, not evidence about a real place.
```

## c3-drilldown - Drill-down to rows with understandable framing

Categories: drilldown  |  session: `vcbench-run3-cellsquare-c3-drilldown`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Which villages have the most survey visits? Show rows please. | PASS | - | 0.11 | 22 | From the data this site has, I cannot rank villages by survey visits from this reply: the village-wise household survey split did not return usable rows, and the fallback only show... |
| t2 | There is one column called effort. What it means actually? | **FAIL** | `jargon` | 0.63 | 19 | Here, `effort` means documented survey work done in a map square, used as the denominator for judging coverage; it is not the same as the number of records found. Because no exact ... |
| t3 | Kindly turn it around and show which village we visited least. We have to plan next round. | PASS | - | 0.19 | 16 | From the data this site has, I still cannot name the least-visited village: the village-wise survey split did not return usable rows. The fallback map only shows that records are s... |
| t4 | Give me one line I can put in our monthly report about this. | PASS | - | 0.0 | 7 | From the data this site has, village-wise survey visits could not be ranked from the current records, but the map shows records in 22 map squares and explicit survey effort in only... |

### c3-drilldown / t2 - failure detail

User: There is one column called effort. What it means actually?

- `jargon`: denominator

```
Here, `effort` means documented survey work done in a map square, used as the denominator for judging coverage; it is not the same as the number of records found. Because no exact square was pointed out, the explanation the system gave is for the biggest count square on this map, where 25 records from the public-works and migration tables fall inside one 1.1 km square. This map also says explicit survey effort is recorded only in 3 squares, and it uses synthetic test data, not evidence about a real place.
```

## c4-estimate - Estimate with clarification near Kadamparai

Categories: estimate  |  session: `vcbench-run3-cellsquare-c4-estimate`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Near Kadamparai there is one empty square on the map. Can you estimate how many jobs will be there? | PASS | - | 0.24 | 60 | I read “jobs” here as public-works persondays, meaning days of paid work, and I used the empty square just north of Kadamparai: the 1.1 km square spanning 10.270–10.280 N and 76.96... |
| t2 | Yes, the square just below Kadamparai village. Take it as 10.255, 76.965. Kindly estimate for that one. | PASS | - | 0.53 | 18 | I read “jobs” here as public-works persondays, meaning days of paid work. For the 1.1 km square covering your point 10.255 N, 76.965 E, spanning 10.250–10.260 N and 76.960–76.970 E... |
| t3 | How much you are trusting this number? Be frank with me. | PASS | - | 0.76 | 26 | Frankly, I would trust the worked-out number only lightly. This square already has a real recorded figure, and that is the one to trust more: about 6,176 persondays, meaning days o... |
| t4 | If I put this in a proposal, what caveat I should write? | **FAIL** | `honest_gap` | 0.76 | 11 | Use a caveat like this: “This figure is indicative only. It is based on recorded public-works persondays — days of paid work — in nearby surveyed map squares, and for this square t... |

### c4-estimate / t4 - failure detail

User: If I put this in a proposal, what caveat I should write?

- `honest_gap`: no plain statement that the data is missing

```
Use a caveat like this: “This figure is indicative only. It is based on recorded public-works persondays — days of paid work — in nearby surveyed map squares, and for this square the model check was weak; the worked-out range was broad. For this location, the site also has a real recorded figure, which should be treated as stronger than the estimate, and the result should not be read as a direct ground count.” If you want it shorter for proposal text: “This is a rough planning figure, not a direct field measurement, and should be used with caution.”
```

## c5-honest-limits - Honest limits: school data is absent

Categories: honest_limits  |  session: `vcbench-run3-cellsquare-c5-honest-limits`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | How many children go to school here? We need it for our education programme. | PASS | - | 0.57 | 26 | From the data this site has, I cannot give a number of children going to school from this map. It shows only where records are present and where survey effort was recorded: records... |
| t2 | So you are saying there is no school data at all? Or maybe it is there but not matching? | **FAIL** | `non_match_is_not_absence` | 0.38 | 19 | It is closer to “there may be records, but they do not match in a way that lets this table count school-going children.” The stored explanation says the household survey summary fa... |
| t3 | Then what all is the closest to household level information you are having? | PASS | - | 0.72 | 16 | From the data this site has, the closest things to household-level information are the household survey, the public-works records with households engaged, and the migration records... |
| t4 | Fine. Kindly note it down that we need school enrolment data for Valparai. | PASS | - | 1.0 | 8 | Noted in this conversation: you need school enrolment data for Valparai for the education programme. At present, the data this site has does not give a usable school enrolment coun... |

### c5-honest-limits / t2 - failure detail

User: So you are saying there is no school data at all? Or maybe it is there but not matching?

- `non_match_is_not_absence`: did not separate 'not recorded' from 'not happening'

```
It is closer to “there may be records, but they do not match in a way that lets this table count school-going children.” The stored explanation says the household survey summary failed because the survey entries and the effort entries do not line up on the same site and category, and there were zero contributing rows for that count. This is also synthetic test data, so it does not show a real place-level school total.
```

## c6-general-knowledge - General knowledge may frame, numbers must come from data

Categories: gk_usage  |  session: `vcbench-run3-cellsquare-c6-general-knowledge`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | Is 10000 rupees a month good income for a tea worker? | PASS | - | 0.32 | 27 | From the data here, the chart only shows daily wage, not full monthly earnings, and it uses synthetic test data, so it cannot tell us whether ₹10,000 a month is good at a real tea ... |
| t2 | What the actual data is saying about tea worker wages here? | PASS | - | 0.76 | 12 | From the data here, the chart says there are 96 monthly entries for daily wage, which means the records do track tea worker pay over time. This chart still uses synthetic test data... |
| t3 | So compared to what you said generally, this is high or low? | PASS | - | 0.46 | 15 | From the data here, we cannot say high or low, because the chart only confirms that daily wage records exist and it uses synthetic test data, not real wages for this place. In gene... |
| t4 | Can you write two lines for our donor about this wage situation? | PASS | - | 0.72 | 12 | From the data here, the records do track tea worker daily wages over time, with 96 monthly wage entries available. This chart uses synthetic test data, so for a donor note you shou... |

## c7-migration - Out-migration: orientation, drill-down and the user's own words

Categories: orientation, drilldown, vocabulary  |  session: `vcbench-run3-cellsquare-c7-migration`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | What all is happening with people leaving this area for work? Any data on that? | PASS | - | 0.81 | 31 | From the data this site has, out-migration is one of the recorded themes, but this map only shows where records exist overall, not how many people left or where they went. A direct... |
| t2 | This migration, which occupation is leaving most? | **FAIL** | `numbers` | 1.0 | 12 | From the data this site has, I cannot say which occupation is leaving most. The migration records here did not return a usable occupation-wise count, so this is a real data gap in ... |
| t3 | Show me the rows na. | PASS | - | 0.97 | 18 | From the data this site has, I cannot show the migration rows for occupation here. The closest migration breakdown came back empty because the records do not line up in a usable ro... |
| t4 | And the tea plucker people, same thing for them? | PASS | - | 0.6 | 15 | From the data this site has, the closest match to tea pluckers is plantation labour, and this map shows 50 recorded entries across 5 members of that group in the target area. It sh... |
| t5 | Summarise in 3 simple points for our team meeting. | PASS | - | 0.8 | 9 | 1. From the data this site has, people leaving for work is recorded as a topic, so there is some migration data in the records. 2. From the data this site has, we could not get a u... |

### c7-migration / t2 - failure detail

User: This migration, which occupation is leaving most?

- `numbers`: no concrete figure

```
From the data this site has, I cannot say which occupation is leaving most. The migration records here did not return a usable occupation-wise count, so this is a real data gap in this setup. This is also synthetic test data, so treat it as a demo of record structure, not a finding about a real place.
```

