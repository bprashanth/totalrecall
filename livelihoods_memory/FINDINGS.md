# FINDINGS — livelihoods sector
Running log, newest at bottom. Tag each finding [HARNESS]/[CONNECTOR]/[PARSER]/[SPEC-PROPOSAL]/[SCORING].
Every equivalence decision you make as judge gets recorded here with its reasoning.

## 2026-07-12 — Step 0: livelihoods data census [CONNECTOR]

Probed Bengaluru (India), Nairobi (Kenya), and Accra (Ghana) before authoring any questions.
All HTTP responses are in `harness/cache/data/`. The cities deliberately span South Asia and
two African labor markets; the country series use IND/KEN/GHA. No candidate below is admitted
merely because its code or tag looks plausible.

**Source 1 — OSM Overpass, present-day livelihood infrastructure (ADOPTED).** Grain is an OSM
node/way within the resolved city bbox, with no historical time axis. Working request shape:
`POST https://overpass-api.de/api/interpreter` with
`nwr["amenity"="marketplace"](bbox); out center;` (the connector uses the equivalent cached
node+way query). Verified row counts:

| entity/tag | Bengaluru | Nairobi | Accra | decision |
|---|---:|---:|---:|---|
| marketplaces (`amenity=marketplace`) | 63 | 142 | 37 | adopt; abundant informal-commerce proxy |
| banks (`amenity=bank`) | 1439 | 433 | 493 | adopt; capped at 200 during normal queries |
| ATMs (`amenity=atm`) | 1148 | 160 | 236 | adopt; capped at 200 during normal queries |
| coworking (`office=coworking`) | 115 | 6 | 1 | adopt, with thinness stated |
| craft businesses (`craft=*`) | 371 | 40 | 191 | adopt as broad artisan/craft-business records |
| employment agencies (`office=employment_agency`) | 3 | 1 | 0 | reject as a normal axis; genuine gap |
| training (`amenity=training`) | 2 | 1 | 2 | reject as a normal axis; genuine gap |

Judge decision: a marketplace, bank, ATM, coworking office, or mapped craft business is an
observed *facility record*, not a job, worker, income, or proof of livelihood use. Questions
about employment behavior or economic outcomes must not silently use these as causal facts;
they require a named proxy/hole or a DataRequest.

**Source 2 — World Bank Indicators API, country-year labor series (ADOPTED).** Working request:
`GET https://api.worldbank.org/v2/country/KEN/indicator/SL.EMP.SELF.ZS?format=json&per_page=300`.
Every adopted code returned 35 yearly rows (1991–2025) for IND, KEN, and GHA, except total labor
force and labor-force participation, which returned 36 (1990–2025):

| lay entity | code |
|---|---|
| unemployment | `SL.UEM.TOTL.ZS` |
| labor force | `SL.TLF.TOTL.IN` |
| self-employment share | `SL.EMP.SELF.ZS` |
| vulnerable-employment share | `SL.EMP.VULN.ZS` |
| labor-force participation | `SL.TLF.CACT.ZS` |
| youth unemployment | `SL.UEM.1524.ZS` |
| wage and salaried workers | `SL.EMP.WORK.ZS` |
| employment in services | `SL.SRV.EMPL.ZS` |
| employment in agriculture | `SL.AGR.EMPL.ZS` |

Geographic grain is country, temporal grain is annual. A city phrase cannot be treated as a
country series: if World Bank country resolution fails, the result must remain a DataRequest.
The share indicators are percentages, while total labor force is a count; resolver aliases must
therefore retain the measure noun and never map bare `employment` to an arbitrary percentage.

**[SPEC-PROPOSAL pressure found during census] Upstream evidence status.** The World Bank labels
the adopted employment-share series as modeled ILO estimates. The frozen evidence algebra marks
all connector results without an algebraic `ESTIMATE` node as `observed`, so it currently cannot
distinguish an observed API retrieval from a model-derived statistic upstream of that API. I will
not change the rule locally. A benchmark trace using one of these indicators will be attached to
an evidence-backed proposal after the first tick.

**Routing decision.** World Bank remains before OSM for specific indicator phrases; OSM handles
physical records. Directional token matching prevents bare `market`, `bank`, or `craft` from
matching longer labor-indicator phrases and prevents bare `employment` from guessing a series.

## 2026-07-12 — tick-001 baseline (qwen2b, seed, 24 questions): 0.911 [PARSER]

First-contact aggregate: overall **0.911**, shape 0.917, holes 0.917, exec class 0.708. Sixteen
questions were perfect. The residue was useful rather than random:

**Craft-workshop cluster (4 rows) [CONNECTOR + PARSER].** The 2B shortened `craft workshop` to
`craft` once and `workshop` three times. All four trees otherwise had the exact composition,
including thresholds and the within→beyond conjunction. Because this source intentionally uses
the broad `craft=*` tag, both fragments are safe sector aliases; added as explicit truncation
insurance. The count-over-RELATE exemplar was entity-swapped to `craft workshop`/`marketplace`
without changing its tree shape, reinforcing whole-phrase copying.

**lv-ratio-01 [CONNECTOR].** The 2B copied natural morphology (`self-employed`) and shortened
`wage and salaried workers` to `wage and salaried`. The original token matcher cannot equate
`employed` with `employment`; both phrases nevertheless name the exact verified indicators, so
explicit aliases were added. Bare `employment` remains unmapped to avoid guessing a measure.

**lv-rel-03 [HARNESS + PARSER].** The literal-provenance pass tokenized on whitespace and could
not trace `Bengaluru` to `Bengaluru's`, demoting a named place to `?place`. It now tokenizes on
all non-alphanumerics with guarded prefix tolerance. Independently, the parser compiled a unary
mean instead of `RELATE(distance)`; the within exemplar was entity-swapped, same two-SELECT
curriculum shape, to a possessive distance question.

**lv-change-01/02 [PARSER + SCORING].** The stock 13 examples had no two-snapshot CHANGE tree.
lv-change-02 chose a unary trend. More dangerously, lv-change-01 scored **1.000** structurally
while comparing a 2000–2020 series endpoint with the all-data 2025 endpoint; synthesis claimed
the result was 2000→2020. This is a structurally green wrong-answer class. Added a two-snapshot
CHANGE exemplar (14th) and clarified lv-change-02 to ask for percentage points. The scorer schema
is frozen, so the trace remains evidence that manual synthesis inspection is mandatory.

**lv-beh-02 [PARSER].** “Do nearby marketplaces actually improve household incomes?” is causal,
not a direct measurement. The model hallucinated `nearby marketplaces` as a REGION and tried a
household-income trend, causing geocoding error. Added one causal-behavior → `SELECT(?proxy,
?place)` exemplar (15th). The cap is now reached; no more few-shots will be added.

**lv-state-04 [HARNESS].** The stock density implementation returned the raw record count with
note `density proxy`; synthesis fluently promoted it to “37 per unit area,” and every mechanical
synthesis score was green. Fixed at the executor layer: density now divides by the resolved bbox
area in km² and provenance states `bbox-area approximation`. This is an executor implementation
bug, not a new algebra op.

**Synthesis scorer [SCORING].** String scalar directions were always marked as not stating the
finding; signed differences stated without a minus sign were missed; “no available … data” was
missed as a gap. Extended those mechanical checks, following only phrases observed in this tick.

**Evidence judgment [SPEC-PROPOSAL].** `lv-trend-01` retrieved a modeled ILO estimate but stamped
and verbalized it as observed. Proposal filed in `spec-proposals.md`; frozen evidence rules remain
unchanged locally.

## 2026-07-12 — tick-002 full seed guard: 1.000 [PARSER/HARNESS]

All 24 questions reached 1.000 on every structural/behavioral dimension. No fix rotated another
shape at the 15-example cap. Manual synthesis checks confirmed the material repairs:

- self-employment change now compares exactly 2000 and 2020 and reports −7.49 percentage points;
- youth unemployment compares exactly 2010 and 2020 and reports −4.74 percentage points;
- density is 0.0869 mapped marketplaces/km² over the 425.662 km² resolved Accra bbox, not 37
  mislabeled as a density;
- the ratio executes against the two intended percentage series;
- behavior questions stop at typed holes rather than geocoding a causal phrase.

Synthesis mean was 0.993. The sole subscore miss was a valid gate gap phrased “local data is
required”; the gap regex recognized `need` but not `required`. Added that observed morphological
variant. This changes only mechanical surface scoring, not any trace or corpus schema.

## 2026-07-12 — tick-002-mt first livelihoods dialogue pass: 0.886 [PARSER/HARNESS]

Three of five cases were perfect for both model and mechanical binding.

- **mt-02 [HARNESS fixture]:** turn 1 correctly produced `?facility_type` + `?place`, and model
  binding executed. Mechanical binding failed only because the scripted slot map offered
  `workshop_type`, not the actual `facility_type`; added the exact slot key.
- **mt-04 [PARSER]:** “How is the job market doing around here?” produced a trend over concrete
  `job` with only `?place`. Both binders correctly preserved that skeleton, so the reply's “use
  youth unemployment” had no indicator hole to fill and execution honestly returned
  `no_connector`. Judge decision: `job market` is an abstract topic, not a measurable entity;
  correct turn 1 is a trend tree over `SELECT(?indicator, ?place)`. Entity-swapped the existing
  trend exemplar to that exact hole-bearing shape. Few-shot count stays 15 and the unary trend
  curriculum is preserved.

The next gate is dialogue rerun plus all 24 seed questions; the swap does not ship if it rotates
a previously green parse.

## 2026-07-12 — tick-003 multiturn + complete seed guard: 1.000 / 1.000

All five dialogue cases are perfect on turn-1 hole placement and on model/mechanical binding:
both binders kept the skeleton, filled every hole, and executed 5/5. The full 24-question seed
guard concurrently stayed 1.000. The trend-exemplar swap caused no rotation. Unlike transport's
model-bind residue, these short livelihoods replies were handled perfectly; deterministic binding
remains preferable because it is guaranteed not to rewrite the tree, but there is no measured
dialogue residue on this bank.

## 2026-07-12 — neutral generation admission: 17/18 [HARNESS/CONNECTOR]

The livelihoods-only neutral generator produced 18 candidates; the frontier gold author admitted
17 by schema/structure/execution. One Marseille relation was retained in `questions/breakers.json`
after a transient source error rather than being forced into the bank.

Manual admission review found an important **false-gold class**: OSM SELECT was hard-capped at
200 but returned no truncation signal. Lyon craft workshops and Osaka ATMs both executed at exactly
200, and the three-city bank ranking initially compared `200,200,156`. Execution validation called
all of these valid. Increased the safety cap to 500 and query `cap+1`; if the extra row exists,
the connector now raises `source_truncated` rather than presenting partial data as a total or
complete spatial input. Re-admission yielded Lyon 425, Osaka 265, and the real bank order Accra
493 > Nairobi 433 > Lagos 156. All 17 golds then passed again. This is a connector completeness
invariant that should be reintegrated cross-sector.

## 2026-07-12 — tick-004 first contact gen-001 (17 unseen): parser 1.000 [PARSER]

All 17 unseen questions scored 1.000 on every parse/execution dimension, and synthesis's existing
mechanical dimensions also averaged 1.000. This is above both reference first-contact bands.

Manual prose inspection nevertheless found **gen-live-14 [HARNESS/SYNTHESIS]**: execution ranked
Canada (20.125) > United States (14.891) > Australia (14.142), but prose called the United States
highest and listed Canada last while copying all three values. The old `states_finding` accepted
any one row label, so the exact-opposite ordering stayed green. Added an order-preservation check
to the existing dimension and a deterministic fallback renderer when model prose reorders trusted
ranking rows. No trace/summary field changed.

## 2026-07-12 — indirect generation admission: 11/15 after manual judge [SCORING]

Automated generation admitted 13 and rejected two transient OSM executions. Manual judging then
removed two unsafe golds:

- a Marrakech two-part question whose gold answered only clause one (known dialogue-layer split);
- a contradictory potter/supply-store preamble whose gold answered only the later
  craft-workshop/marketplace clause.

One candidate asked for marketplaces with “no bank or ATM within 500m.” Frontier gold collapsed
`bank or ATM` to one ambiguous SELECT, which happened to route to bank and execute green. Judge
correction: under negation, De Morgan makes this expressible in v2.1 without UNION:
`beyond(ATM, beyond(bank, marketplaces))`. Positive “near a bank or ATM” still needs record-set
union. The corrected chained gold returned 59, versus 61 when ATM was silently dropped.

## 2026-07-12 — tick-006 indirect first contact: 0.872 [PARSER/HARNESS]

Seven of eleven final questions were perfect. Failures and fixes:

- **gen-live-08:** parser dropped the ATM complement and synthesis falsely claimed the bank-only
  61 rows satisfied “bank or ATM.” Added a model-neutral negated-disjunction lint that chains the
  second `beyond` with the same threshold.
- **gen-live-10:** explicit 2010→2020 CHANGE became unary trend with illegal `right:null`, which
  the validator accepted and executor crashed on. Validator now enforces unary trend; structural
  normalization drops stray trend rights; explicit `changed` + two named years mechanically
  creates the two SELECT snapshots. This also guards tick-001's structurally-green endpoint bug.
- **gen-live-11:** the abstract-job-market exemplar rotated onto a question that explicitly named
  self-employment, producing `?indicator`. A binder now fills only `?indicator` from a unique
  verified resolver match in the question; bare employment remains a hole/gap.
- **gen-live-05 (hidden wrong reason despite score 1.000):** `co-working` missed the `coworking`
  resolver and returned no_connector. Added the exact orthographic alias; Bulawayo then truthfully
  returned empty_select (no mapped rows), still the expected transfer DataRequest.

Connector/empty-leaf DataRequests now have deterministic honesty surfaces after the 2B said a
no_connector outcome meant “no pottery studios exist.” A source gap is never a real-world zero.

## 2026-07-12 — tick-007 indirect after repairs: parser 1.000 [HARNESS/SYNTHESIS]

All 11 indirect questions reached 1.000 structurally and behaviorally. Manual prose review caught
another green fabrication: the corrected gen-live-08 execution returned 59 records, while prose
began “Five out of 59.” The scorer found `59` anywhere and passed it. Records synthesis now requires
the first stated quantity to equal `n_rows`; otherwise it falls back to the trusted count, sample
names, and source. The existing `states_finding` field enforces the same rule (schema unchanged).

## 2026-07-12 — ticks 008–010 final guards + frontier control [HARNESS]

Tick 008: qwen2b seed 1.000 (24), neutral 1.000 (17), indirect 1.000 (11), multiturn
1.000 (5). DeepSeek frontier then scored seed 1.000, neutral 1.000, and indirect 0.977: its only
miss was gen-live-08, where it retained the literal combined entity `bank or ATM` in one beyond
RELATE. The initial De Morgan repair handled qwen's dropped-ATM tree but saw both words in the
frontier leaf and did not split it. Generalized the normalizer: a combined negated-union leaf is
rewritten to the first anchor and then chained with the second. Tick 010 results:

- qwen2b: **1.000 / 1.000 / 1.000**, multiturn **1.000**;
- deepseekv4: **1.000 / 1.000 / 1.000**.

All qwen banks were rerun after the frontier-derived repair; no regression or prompt rotation.
At 52 unique single-turn questions plus five dialogue cases, two register shifts, 15/15 few-shots,
and full frontier parity, the measured loop is saturated. Remaining debt is characterized rather
than hidden: upstream modeled-source evidence labels (spec proposal), OSM completeness above the
safe cap (honest DataRequest), sparse maps, and known positive record-set union/multi-part limits.

## 2026-07-12 — tick-011/012 corpus audit and final strict guards [SCORING/HARNESS]

The first corpus compile produced 54 parse rows and 20 clarification rows. Audit found four
compiler/scorer issues that benchmark summaries had hidden:

1. historical traces reintroduced the two manually rejected half-golds;
2. clarification compilation admitted failed bindings and repeated the same five cases per tick;
3. `holes_correct` only tested whether *some* hole existed, allowing a `?place`-only parse where
   gold required both entity and region;
4. latest-mtime selection allowed frontier rows to replace parser-under-test rows.

Fixes preserve file formats: compile only questions present in active final banks; require valid,
hole-free, skeleton-preserving, executing mechanical bindings and dedupe them; compare hole FIELD
multisets (names may vary); and source parse training rows only from qwen2b. The stricter scorer
exposed named behavior places left as `?place` and frontier concretization of generic “livelihood
facilities.” Mechanical binders now retain Bogotá/Porto named in the question and hole generic
facility nouns in deictic contexts.

Tick 012 strict final battery: qwen2b 1.000 on 24/17/11 plus multiturn 1.000; DeepSeek 1.000 on
24/17/11. Final corpus audit: 52 active, unique livelihoods parse rows; five unique, verified,
hole-free clarification rows; zero rejected-question leakage.

Tick 013 aligned the gap scorer with the deterministic phrase `source-coverage gap` and reran all
qwen banks plus dialogue: parser, execution, synthesis, and multiturn are each 1.000.

## 2026-07-13 — Round 2 coverage census [HARNESS]

The 52-question Round 1 suite has only 12 unique operator skeletons. All five ranks are descending
over exactly three items; no question exercises `ANNOTATE`, `RELATE(cooccur)`, aggregate
`presence`, rank `k`, ascending rank, interpolation/feature estimation, mixed-source composition,
subnational series, or explicit multi-year SELECT windows. Its 85 SELECT occurrences reduce to
30 OSM questions, 14 World Bank questions, seven hole questions, and one honest no-connector gap.

`harness/coverage.py` now emits one machine-readable row per question with skeleton, source, grain,
entity, time form, relation/threshold, arithmetic mode, holes, and adversarial family.
`coverage/matrix.json` is the Round 1 baseline. Judge decision: paraphrases do not count as new
semantic coverage; empty/singleton cells drive Round 2 generation.

## 2026-07-13 — Round 2 official-source census [CONNECTOR]

Two complementary keyless official sources were live-probed and adopted, bringing the tested
source families to four and the principal grains to three.

**Source 3 — ILOSTAT bulk indicator API (ADOPTED, curated observed-source stratum).** The connector
uses official indicator CSV tables, exact entity-to-table/subgroup mappings, and ISO-3 countries.
It excludes observation status `M` (model-based extrapolation). Where national survey sources
overlap, it selects one coherent source by longest distinct-year coverage, latest year, then source
code; it never splices vintages and records every alternative in provenance. Verified slices:

| entity | place | table | chosen source | verified window |
|---|---|---|---|---|
| informal-employment rate | France | `SDG_0831_SEX_ECO_RT_A` | `BB:3067` | 2019–2023 |
| female average weekly hours | Germany | `HOW_TEMP_SEX_NB_A` | `BA:2242` | 2019–2023 |
| labour underutilization | Spain | `LUU_XLU4_SEX_RT_A` | `BA:2244` | 2019–2023 |
| average weekly hours | Kenya | `HOW_TEMP_SEX_NB_A` | `BX:3465` | 2019, 2021 |

Frozen v2.1 has no FILTER node, so sex/sector slices remain explicit curated entity phrases. This
is deliberate algebra pressure: arbitrary subgroup requests become breaker proposals rather than
connector-side adjective guessing. Modeled ILOEST tables are not admitted into this observed
stratum because frozen evidence semantics cannot label upstream models correctly.

**Source 4 — Eurostat JSON Statistics API (ADOPTED, NUTS-2 survey-series stratum).** Curated NUTS-2
names/codes prevent a city geocode from being silently treated as a statistical region. Employment
rate, sex-specific employment rate, employed persons, and unemployment rate queries fix every
non-time dimension and reject an unexpectedly multidimensional response. Verified 2022–2024 rows
exist for Ile de France (`FR10`), Berlin (`DE30`), Comunidad de Madrid (`ES30`), Cataluña (`ES51`),
Lombardia (`ITC4`), and Warszawski stołeczny (`PL91`). Upstream flags and update timestamps remain
in provenance.

`coverage/source-census.json` records ten passing nonempty/unique/ordered/numeric/bounded checks,
units, table/source codes, samples, flags, and selection notes. FAOSTAT employment was not counted
as an independent family because its employment domain is derived from ILOSTAT; aliasing an
upstream source would inflate evidence diversity.

## 2026-07-13 — Round 2 first broad development loop [PARSER/HARNESS/SCORING]

The 214-question Round 2 development bank passed schema and real execution at gold admission. On
first qwen contact it scored 0.875 overall but only 0.45 execution-class accuracy. Full-phrase
measure loss, NUTS-2 shortening, wrong statistical aggregation types, ratio/rank collapse, dormant
ops, and hole errors formed distinct repair clusters. ANNOTATE also exposed a validator hole:
`layer` accepted a dict and the executor crashed with an unhashable value.

After repairs the normal harness reached 214/214. This was not accepted as closure. A new strict
canonical IR audit compared source-resolved entity identities, regions, exact time, operands,
rank order/k, thresholds, layers, and hole positions. It found 17 mechanically green semantic
mismatches, including four reversed `Subtract X from Y` results, missing top-k, two mixed-source
trees whose leaves had collapsed to the same indicator, invented time on a source gap, and a
dropped `survey` noun. Tick 004 is 214/214 under both scoring regimes.

Judge decision: the published coarse `shape_match` remains useful for algebra skeletons but is not
sufficient saturation evidence. Every freeze/holdout now requires `semantic_audit.py` to pass.
Final regression after prompt rotation is seed 24/24, gen-001 17/17, gen-002 11/11, and multiturn
5/5 for both model and mechanical binders.

## 2026-07-13 — Round 2 failed freeze epochs and expanded guard [PARSER/HARNESS]

Freeze epochs 001 and 002 both failed at 30/40 strict semantic matches and were invalidated. They
are development discovery, not holdout evidence. Once disclosed, 39 admissible H1 cases and 37
admissible H2 cases joined the regression wall; four bad/ambiguous golds were excluded with reasons.
The failures added general repairs for answer form, behavior proxies, morphological entity
restoration, transfer contracts, deictic regions, conjunctive spatial predicates, clause-scoped
thresholds, and negative relations.

The pre-epoch-003 active wall contains 382 questions. All 382 score 1.000 in the ordinary harness;
the 330 Round-2 development cases, seed 24, and indirect 11 also pass strict canonical audit. Two
retained gen-001 cases are documented legacy gold defects rather than silently normalized: one
contradicts the current existential answer-form contract and one applies record aggregation to a
connector Series. Neither is eligible as blind saturation evidence.

## 2026-07-13 — Round 2 wide holdout campaign [NEGATIVE SATURATION RESULT]

Freeze epochs 003–010 grew the certified active wall to 727 questions and repeatedly found new
failure classes after perfect regression closure. The strict holdout sequence is
30, 34, 15, 22, 40, 28, 31, 37, 30, 23, 37, 22 matches out of 40 (H3/H4/H5/H8–H16).
The curve is not flat; the isolated H9 40/40 is register-local and its epoch was already invalid.

New compiler coverage includes terse existential/list forms, address/name annotations, relation
arithmetic, right-nested relative clauses, anaphoric facility holes, comma city-country ranks,
rank direction, goal behavior proxies, and explicit/unknown transfer targets. H14–H16 nevertheless
reopen wider-facility and compositional failures. Judge decision: report the negative result and
continue from those banks; do not call the 727/727 development wall saturation.
