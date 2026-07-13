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

## 2026-07-13 — H14–H16 classified and absorbed [PARSER/HARNESS]

All 38 strict mismatches from epoch 010 were valid compiler discoveries; no gold was quarantined.
The failures clustered in spatial operand restoration/composition, rank-place span extraction,
unknown transfer targets, purpose-preamble binding, existential presence, and cautious holes for
abstract livelihood/work measures. A read-only GPT-5.5-high-fast clustering pass was advisory; the
main judge verified each question/gold/execution pair under frozen v2.1 semantics.

General mechanical repairs closed the disclosed banks at canonical H14 40/40, H15 40/40, and H16
40/40. The original holdouts remain immutable; normalized development copies join the regression
wall. This invalidates epoch 010 permanently and supplies no saturation passes. See
`chronology/20260713_round2_epoch_011_absorption.md` for the repair taxonomy and admission decision.

## 2026-07-13 — Epoch 011 certified development wall [PARSER/HARNESS/SCORING]

The 847-question, 19-bank active wall is certified after three explicitly rejected candidate runs.
The final v4 wall is 847/847 under the ordinary harness and 845/845 on strict canonical semantics
for all eligible rows. Across all historical rows it is 845/847; the only exceptions are the two
pre-declared `gen-001` legacy gold defects, which remain visible and ineligible rather than being
used to distort the parser. Both model and mechanical dialogue binders pass 5/5, and six new
deterministic parser regressions pass.

The rejected wall attempts matter: the coarse score first hid three denotation defects; a second
attempt passed observed rows but failed adversarial review of rule generality; a third generalized
the rules but reopened six deictic-transfer cases. Only v4 is freezeable. This is development-wall
closure, not saturation evidence. The untouched three-bank discovery-rate sequence restarts after
the epoch-011 freeze. Machine-readable evidence is in `coverage/epoch-011-certification.json`.

## 2026-07-13 — H17 defeats epoch 011; epoch 012 absorbs 17 discoveries [PARSER/HARNESS]

The first post-freeze OpenAI-family bank scored strict 23/40 despite the certified 847-question
wall. All 17 mismatches were admissible. The resulting v2.1 compiler coverage includes scoped
multi-anchor predicates and outputs, relation arithmetic, word top-k, distinct ratio regions,
supported-region rank phrasing, deictic transfer targets, and rejected-fallback holes. No new
algebra operator was required.

The absorption loop itself rejected two seemingly clean wall attempts after strict regression
checks. The final epoch-012 wall contains 887 questions and passes ordinary 887/887, strict eligible
885/885, 16/16 deterministic regressions, and dialogue 5/5 for each binder. H17 is immutable failed
evidence, not a saturation success; the untouched counter is zero at the epoch-012 freeze.

## 2026-07-13 — H21 rejects epoch 015 and exposes false-grounding risks [PARSER/CONNECTOR/HARNESS]

H21 scored 17/40 on first-contact strict audit despite a certified 1,000-question development
wall. Independent adjudication found 23 compiler-bearing rows, no gold defects, and no audit
defects. Direct execution of all admitted golds confirmed every declared outcome class. The
failures form six families: rank blueprint/candidate/cardinality closure, operand-local source and
facet binding, complete unsupported indicators, unresolved deictic roles, relational predicate
composition, and noncommutative orientation.

Judge decision: H21 invalidates epoch 015 and contributes zero saturation passes. Its recurrence of
the H20 family labels is not evidence that the failures were “known residue”; the new surfaces were
not handled and therefore the families were not absorbed under SAT-002. Family closure requires a
later untouched contact, not only disclosed positive and negative guards.

General repairs plus 91 deterministic tests close the immutable bank at strict 40/40. All 40 valid
rows become disclosed development in `questions/round2-h21-dev.json`. No IR operation or field was
added.

Execution adjudication also found a false-grounding path: the World Bank connector inferred France
from the Nominatim parent of Ile de France, allowing wrong subnational IR to return the intended
national number. National-only connectors now require the original requested scope to be a country;
curated statistical regions are geocoded with country qualification; region-resolution exceptions
return typed DataRequests. Judge decision: implicit geographic coarsening is an evidence defect,
not a convenient fallback. SRC-003 proposes a general connector scope certificate and corroborates
BUG-002.

## 2026-07-13 — Epoch 016 certified after two rejected walls [PARSER/CONNECTOR/HARNESS]

The final v3 wall passes ordinary 1,040/1,040 and strict 1,038/1,038 eligible across 24 banks and
34 skeletons. The two noneligible strict mismatches are the declared `gen-001` defects. Dialogue
passes 5/5 on both binding paths, source census passes 10/10, 92/92 regressions pass, and corpus
output contains 1,052 unique parse plus five clarification rows.

Judge decision: the v1 and v2 wall attempts do not count. V1 revealed H19's latent Warsaw
source-truncation expectation defect after geocoder correction. V2 revealed a late source-gap pass
overwriting correct arithmetic. Each change reset the wall and forced all banks to rerun. Epoch 016
starts with saturation counter zero; only post-freeze H22+ contacts may increment it.

## 2026-07-13 — H22 rejects epoch 016 and exposes execution-grounding defects [PARSER/HARNESS/SCORING]

H22 first contact was ordinary 0.924 but strict 17/40. Independent adjudication found genuine
compiler divergence in all 23 mismatches, grouped into five families: computed-rank planning and
cardinality, operand-local spatial arithmetic, answer-head preservation, exact lexical/time source
semantics, and transfer donor composition. Four rows also have unsafe wording/spec ambiguity and
are registered as immutable defects rather than tuning targets (`h22-010`, `023`, `024`, `047`).

Direct gold execution found four harness defects: spatial mean returned row count, all-null
ANNOTATE appeared grounded, a REGION-wrapped ESTIMATE target hole reached geocoding, and a
one-point trend returned a null Answer. These now fail closed or compute the declared distance
mean. BUG-004 and EXEC-001 record the framework-level recursive-slot and typed-value contracts;
SRC-002 and SCR-001 receive further empirical support.

Fix2 is strict 36/36 on eligible H22 rows, with only the four registered defects mismatching the
immutable bank; 104 deterministic guards pass. This disclosed replay cannot count as saturation.
H23/H24 were authored against the now-retired epoch and are therefore development pressure only.
Full rationale: `chronology/20260713_round2_epoch_017_h22_absorption.md`.

## 2026-07-13 — Epoch-017 wall and H23/H24 pressure reject a premature freeze [PARSER/HARNESS]

The corrected 1,076-row wall passes ordinary and strict audit on all 1,074 eligible rows. Five
disclosed expectations were updated to typed DataRequests after H22's fail-closed annotation and
trend fixes; their immutable originals remain registered defects. Dialogue passes 5/5 through both
binding paths, the source census passes 10/10, and 104 deterministic tests pass.

H23 and H24 were generated against the retired epoch-016 boundary, so they are development
pressure only. Their selected golds were validated and directly executed before qwen contact.
First contact is strict 8/40 for H23 and 25/40 for H24 (ordinary 0.823 and 0.919). Judge decision:
epoch 017 is not freezeable; the 47 exact divergences require full adjudication and generalized
absorption. Neither pressure bank can increment the untouched saturation counter, regardless of
its repaired replay score.

## 2026-07-13 — H23/H24 absorption closes 46 compiler-bearing rows [PARSER/HARNESS/CONNECTOR]

H23's 32 strict mismatches were all genuine compiler divergences. H24's 15 mismatches contained
14 compiler/harness divergences and one strict-audit country-suffix equivalence. General repairs
cover computed ranks, operand-local statistical arithmetic, nested spatial outputs/arithmetic,
unresolved discourse roles, direct transfer/statistic forms, and complete source-gap literals.
Fix1 reached strict 32/40 and 35/40; fix2 reaches 40/40 on both immutable banks, with 114/114
deterministic guards. Separate disclosed development releases are also strict 40/40 and ordinary
1.000. Judge decision: these are absorption results and add zero untouched passes.

The most serious finding was false grounding. Named-entity restoration rewrote a zero-overlap
`cold storage depot` leaf to `marketplace`; resolver subset/prefix behavior also broadened `main
marketplace`, `night market`, and `coworking access`, and had previously equated `work` with
`workshop`. Restoration now requires positive lexical overlap and resolvers use bounded plural
normalization plus declared aliases. Unknown modifiers fail closed. The immutable `gen-002`
main-marketplace and H10 coworking-access gold assumptions are registered as defects; H10's
disclosed row now asks explicitly for coworking-space count. This further corroborates `BUG-003`.

The schema now enforces frozen Records inputs and structured ESTIMATE target types before
execution (`BUG-005`). H23's unresolved Indian focus city demonstrates that opaque hole names
cannot retain machine-checkable parent constraints (`ASK-005`). Raw H23 probe 079 demonstrates a
genuine absent capability for spatial candidate generation and constrained optimization
(`ALG-010`); it was not forced into a phantom SELECT.

Live/cache-backed verification added World Bank Gini (`SI.POV.GINI`) for Brazil, India, and Kenya
and OSM metro stations in Bengaluru. Source census is 14/14 across ILOSTAT, Eurostat, World Bank
Gini, and OSM metro families. H24's immutable DataRequest expectations remain preserved; its
disclosed development metadata expects the two newly grounded Answers.

## 2026-07-13 — Two rejected epoch-017 walls expose late-pass interference [PARSER/HARNESS]

Wall v3 exposed 36 strict mismatches after resolver hardening and also revealed that H22's 36-row
development release was missing from the freeze bank list. Thirteen failures came from late
source-gap repair erasing already-complete mixed comparisons or nested relations; six came from
mistaking narrative em-dash preambles for place headings. The rest required unique named-statistic
reconciliation, deictic locative cleanup, idiomatic behavior handling, operand-clause cleanup, or
two exact reviewed aliases. Targeted v4 replays close all affected banks, including H22.

Complete wall v5 then exposed `h3-044`'s “but not within” conjunction variant and a late pass
overwriting Madrid's reviewed regional unemployment interpretation. Both were guarded and targeted
replays are exact. Judge decision: v3 and v5 are rejected evidence, never certification. The
breakers file remains checksummed proposal/coverage evidence but is not a runnable bank schema.
Full narrative: `chronology/20260713_round2_epoch_017_wall_rejections.md`.

## 2026-07-13 — Epoch 017 certified and frozen at 1,153 eligible rows [BENCHMARK/CORPUS]

Final wall v8 covers 1,156 questions across 27 runnable banks and 37 skeletons. Ordinary and strict
audits pass all 1,153 eligible rows. The three active exclusions are exact registered defects: two
legacy `gen-001` structural golds and `gen-002`'s unsafe expected Answer for “main marketplace.”
Strict raw matching is 1,154/1,156 because the latter tree is correctly literal and question-faithful
despite its stale outcome expectation. Regression tests are 120/120, source census 14/14, and both
dialogue binders 5/5.

Pre-freeze corpus audit found a superseded H10 “coworking access” trace admitted through global
question-text membership. Judge decision: activity is the tuple `(active bank, bank-local id,
current text)`, not the existence of the same text anywhere under `questions/`. Bank-scoped
admission plus the composite defect registry produces 1,148 unique parse rows and five clarification
rows, with zero immutable-defect leaks and the superseded proxy absent. Governance record:
`BUG-006`.

`coverage/epoch-017-certification.json` records the full gate. `freezes/epoch-017.json` hashes 51
files. Saturation counter remains zero: all H23/H24 and wall evidence is disclosed development;
only newly generated post-freeze banks can count.

## 2026-07-13 — H25 rejects epoch 017 and exposes the answer-truth boundary [PARSER/SYNTHESIS/AUDIT]

H25 first contact scored strict 29/40; all eleven mismatches were genuine compiler discoveries.
The independent prose audit then found that epoch 017's exact eligible IR wall did not imply safe
answers: Boolean polarity, observed/modelled labels, source attribution, numeric derivation, rank
language, failure taxonomy, and modelled-field cardinality were systematically unprotected.

Judge decision: epoch 017 is invalid and the saturation counter remains zero. Typed results and
failure reasons now render deterministically; arbitrary record attributes cannot enter the answer
boundary; explicit question/IR contracts fail closed; and synthesis/evidence audit is mandatory.
Governance records `BUG-007`, `SAT-003`, and `BNCH-002` expose the framework changes for Fable
review.

## 2026-07-13 — Epoch 018 certified only after six rejected truth walls [BENCHMARK/EVIDENCE]

Candidate walls v1–v6 were rejected for real answer or replay defects despite green compiler rows.
The sequence discovered cross-sectional differences narrated as temporal changes, choice questions
without winners, undefined ratios rendered as `None`, omitted annotations, wrong source-versus-scope
taxonomy, unsupported claims from compact samples, nonspecific asks, coordinate precision loss, and
series endpoints omitted from persisted traces.

V7 passes independent all-row replay. Final v8 confirms the exact certification boundary:
1,193/1,193 eligible ordinary and strict rows, 1,196/1,196 synthesis rows, 143/143 regressions,
14/14 source probes, dialogue 5/5 through both binders, and 1,188 unique parse plus five clarification
corpus rows. `freezes/epoch-018.json` hashes 54 inputs with zero replay mismatch. Counter remains
zero pending three new post-freeze untouched banks.

## 2026-07-13 — H26 broad pressure absorbed without widening frozen algebra [PARSER/CONNECTOR/AUDIT]

The 86-row H26 bank widened pressure across 55 declared capability families. Retired-epoch first
contact was ordinary 0.902 and strict 53/86; independent read-only adjudication assigned 32 of 33
non-exact rows to general compiler/binder gaps and the remaining row to a harmless country alias.
No admitted gold was defective.

General repairs close answer heads, nested and cross-place spatial composition, terse statistical
operands, derived ranks, typed unresolved roles, transfer source composition, and late-pass
interference. Final disclosed replay is ordinary, strict, and synthesis exact at 86/86, with
151/151 regressions. No new v2.1 operation or field was required. The precontact connector-outage
discovery remains separately proposed as `BUG-008`; H26 further validates `BNCH-002` and `SAT-003`.
Judge decision: H26 is now active development regression evidence but supplies zero untouched
saturation passes. Epoch 019 requires a completely replayed and certified wall before new banks.

## 2026-07-13 — Active coverage is a registry, not a directory glob [BENCHMARK/CORPUS]

The post-H26 matrix initially counted 1,362 rows while the registered wall contained 1,282. The
extra 80 were retired H23/H24 pressure rows admitted solely because their filenames remained in the
questions directory. The matrix now shares the freeze bank registry and exactly matches the wall:
1,282 rows, 29 banks, and 39 skeletons. Regression `BUG-009` makes cross-artifact bank-set equality
reviewable by Fable/orchestrator. Judge decision: pressure and immutable artifacts remain valuable
evidence but are never active merely because they remain on disk.

## 2026-07-13 — Epoch 019 certified after H26 and active-bank closure [BENCHMARK/EVIDENCE]

The v2 and post-certification-artifact v3 walls are exact on all 1,279 eligible rows; synthesis is
exact on all 1,282. The wall spans 29 banks and 39 skeletons. Regressions are 152/152, source census
14/14, dialogue 5/5 on both binders, and corpus 1,273 parse plus five clarification rows. Judge
decision: epoch 019 is a valid freeze boundary, but its saturation counter is zero. Only new banks
authored after the exact freeze commit may advance the required three-bank sequence.
