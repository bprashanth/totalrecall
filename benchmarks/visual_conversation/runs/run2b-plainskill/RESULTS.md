# Visual conversation bench - results

Run: `run2b-plainskill`  |  endpoint: `http://172.17.0.1:7013`  |  started: 2026-07-25T18:50:01+05:30

**9/13 turns pass (69%)**, 0/3 conversations clean, readable share 92%, median latency 17.6s (max 41.5s).

## Pass rate by category

| Category | Turn pass rate |
| --- | --- |
| drilldown | 80% |
| gk_usage | 75% |
| honest_limits | 50% |
| orientation | 80% |
| vocabulary | 80% |

## Pass rate by check

| Check | Pass rate |
| --- | --- |
| `honest_gap` | 0% |
| `non_match_is_not_absence` | 0% |
| `general_knowledge_labelled` | 50% |
| `numbers` | 50% |
| `jargon` | 85% |
| `brevity` | 100% |
| `no_keyword_refusal` | 100% |
| `no_machine_syntax` | 100% |
| `no_transport_leak` | 100% |
| `non_empty` | 100% |
| `numbers_attributed` | 100% |
| `offers_alternative` | 100% |
| `rows` | 100% |
| `visual_marker` | 100% |
| `vocab` | 100% |

## c5-honest-limits - Honest limits: school data is absent

Categories: honest_limits  |  session: `vcbench-run2b-plainskill-c5-honest-limits`

| Turn | User (Indian English) | Result | Failed checks | Read | s | Excerpt |
| --- | --- | --- | --- | --- | --- | --- |
| t1 | How many children go to school here? We need it for our education programme. | **FAIL** | `honest_gap` | 1.0 | 41 | This map shows the records available here, but they cover livelihoods, not children attending school, so I cannot give a school-going count from this site data. It also uses synthe... |
| t2 | So you are saying there is no school data at all? Or maybe it is there but not matching? | **FAIL** | `jargon`, `non_match_is_not_absence` | 0.9 | 19 | From the data this site holds, it looks like a true gap, not just a naming mismatch. I checked the full site records and the estimate catalogue: they include estate labour, public ... |
| t3 | Then what all is the closest to household level information you are having? | PASS | - | 0.72 | 15 | This map shows the closest thing to household-level information here is the household survey effort itself, and that is documented in only 3 cells. The other data are still useful,... |
| t4 | Fine. Kindly note it down that we need school enrolment data for Valparai. | PASS | - | 1.0 | 7 | Noted in this conversation: for Valparai, the missing priority data is school enrolment. If you want, I can next help frame the exact fields needed, such as school name, age, sex, ... |

### c5-honest-limits / t1 - failure detail

User: How many children go to school here? We need it for our education programme.

- `honest_gap`: no plain statement that the data is missing

```
This map shows the records available here, but they cover livelihoods, not children attending school, so I cannot give a school-going count from this site data. It also uses synthetic test data, so it is not evidence about a real place. If you have a household survey or school enrolment list, I can check that next.
```

### c5-honest-limits / t2 - failure detail

User: So you are saying there is no school data at all? Or maybe it is there but not matching?

- `jargon`: site records, this visual
- `non_match_is_not_absence`: did not separate 'not recorded' from 'not happening'

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

