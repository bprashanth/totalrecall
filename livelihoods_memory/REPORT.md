# REPORT — livelihoods sector replication (2026-07-12)

> **Round 1 status correction (2026-07-13):** this report establishes replication closure, not
> domain saturation. A green 52-question active bank is a regression result after repairs, and is
> insufficient evidence for general livelihoods queries. Round 2 is now in progress under the
> stronger frozen-holdout and discovery-curve protocol in `ROUND2.md`. The Round 1 numbers below
> remain unchanged as the baseline rather than being retrospectively relabeled.

Parser under test: **qwen3.5-2b** at the shared local endpoint. Frozen algebra: **v2.1**. Final
question banks: hand-written `seed` (24), neutral `gen-001` (17), and indirect-register
`gen-002-indirect` (11): **52 unique single-turn questions**, plus five multiturn cases. Every
final qwen run includes synthesis; trace, summary, and corpus schemas remain unchanged.

## Outcome

The final qwen3.5-2b battery is **52/52 at 1.000**, with synthesis **1.000** on all three banks and
multiturn **1.000**. DeepSeek-v4, using the same prompt, executor, and strict scorer, is also
**52/52 at 1.000**. The final corpus contains 52 unique qwen parse rows and five unique verified
mechanical-binding rows. No rejected or superseded question enters the corpus.

No new kernel op was required. The main algebra contribution is an evidence-layer proposal:
connector leaves need trusted upstream evidence labels because modeled ILO estimates currently
enter through SELECT and are falsely tainted `observed`. A second logical finding required no op:
under negation, “no A or B nearby” is expressible by De Morgan as chained `beyond(A)` and
`beyond(B)`; positive A-or-B still requires the known record-set union proposal.

## Score trajectory

| tick | bank | event | overall |
|---|---|---|---:|
| 001 | seed (24) | stock curriculum, first livelihoods contact | 0.911 |
| 002 | seed | aliases, CHANGE/behavior curriculum, provenance + real density | **1.000** |
| 002-mt | multiturn (5) | first dialogue contact | 0.886 |
| 003 | seed + multiturn guards | abstract job-market indicator hole | **1.000 / 1.000** |
| 004 | gen-001 (17 unseen) | neutral first contact | **1.000** |
| 006 | gen-002 final subset (11 unseen) | indirect first contact | 0.875 |
| 007 | gen-002 | De Morgan, explicit CHANGE, named-indicator binding | **1.000** |
| 008–010 | all qwen guards + frontier | frontier combined-union normalization | **all 1.000** |
| 011–012 | strict hole scorer + corpus audit | field-level holes, active/qwen-only corpus | **all 1.000** |
| 013 | final qwen synthesis guards | parser/execution/synthesis | **1.000 / 1.000 / 1.000** |

The original indirect batch scored 0.872 over 12 rows; after manual rejection of one contradictory
half-gold, first-contact on the final 11-question set is 0.875. That is the honest unseen baseline.

## Head-to-head

| | civic reference | transport replication | livelihoods replication |
|---|---:|---:|---:|
| parser | qwen3.5-2b | qwen3.5-2b | qwen3.5-2b |
| single-turn questions | 89 | 45 | **52** |
| final qwen score | 1.000 | 0.985 weighted | **1.000 weighted** |
| unseen neutral first contact | 0.93–0.97 | 0.923 | **1.000** |
| unseen indirect first contact | — | 0.892 | **0.875** |
| multiturn | mechanical > model | 0.943 | **1.000** |
| frontier final | — | 1.000 / 0.981 / 0.950 | **1.000 / 1.000 / 1.000** |
| new kernel ops | RANK, `beyond` | none | none |
| evidence/spec proposals | foundational v2 | 2 semantic debts | **1 upstream-evidence proposal** |

Livelihoods starts lower than the civic first-contact range on its hand-written seed because the
stock prompt had no two-snapshot CHANGE or causal-livelihood exemplar. It exceeds both references
on neutral unseen first contact. Its indirect first contact is slightly below transport, but the
residue was fully removed with model-neutral guards and no additional few-shots.

## Data census and connectors

Two keyless sources were adopted only after live tests across Bengaluru/India, Nairobi/Kenya, and
Accra/Ghana:

- **OSM Overpass:** marketplaces, banks, ATMs, coworking spaces, and broad `craft=*` workshops.
  Employment-agency and training tags were rejected as normal axes because they were nearly empty.
- **World Bank Indicators API:** nine verified country-year labor series (unemployment, labor
  force, self/vulnerable employment, participation, youth unemployment, wage/salaried work, and
  service/agriculture employment), with 35–36 rows per test country through 2025.

OSM completeness was repaired during generated-gold admission. The original 200-row ceiling made
Lyon craft workshops and Osaka ATMs look exactly 200 and produced a false three-city bank ranking.
The connector now requests `cap+1` at a 500-row safety cap and returns `source_truncated` rather
than presenting incomplete counts or spatial inputs. Re-admitted values were Lyon 425, Osaka 265,
and Accra 493 > Nairobi 433 > Lagos 156.

## Failure-layer accounting

Counts below are distinct issue clusters discovered before final fixes, not repeated regression
appearances of the same question.

| layer | clusters | representative findings |
|---|---:|---|
| CONNECTOR | 4 | craft/ratio truncation aliases; `co-working` orthography; silent OSM cap; sparse-source gaps |
| PARSER | 8 | possessive distance; two-snapshot CHANGE; causal behavior; abstract job market; dropped negated disjunct; named-indicator over-hole; generic-place under-hole; named behavior-place over-hole |
| HARNESS | 9 | possessive provenance; count-as-density; unary-trend right crash; De Morgan normalization; source-gap surface; ranking reorder guard; record-count guard; active-bank corpus filtering; verified dialogue dedupe |
| SCORING | 6 | string trends; signed differences; gap morphology; ranking order; record headline; hole-field equality |
| GOLD/JUDGE | 3 | negated-union half-gold corrected; multi-part half-gold rejected; contradictory contextual half-gold rejected |
| SPEC | 1 | connector-leaf label for upstream modeled statistics |

The most important failures were structurally green:

1. a 2000→2020 question compared 2020 against the all-data 2025 endpoint;
2. density returned a raw count and prose invented “per unit area”;
3. capped OSM rows executed as exact totals;
4. ranking prose copied correct values but declared the wrong order;
5. a bank-only execution claimed it had also checked ATMs;
6. “Five out of 59” passed because the scorer found `59` anywhere;
7. boolean hole scoring admitted missing and extra slots;
8. corpus compilation resurrected rejected historical golds.

These are why every final score is paired with manual prose, source-completeness, and corpus audits.

## Mechanical repairs added

- punctuation/prefix-aware literal provenance for possessives and localized names;
- real bbox-area density with units and approximation provenance;
- unary trend normalization and strict validation;
- explicit two-year CHANGE synthesis from named endpoints;
- unique named-indicator binding for `?indicator` only;
- named behavior-place binding and generic deictic-facility hole insertion;
- negated-disjunction expansion, including combined frontier leaves;
- OSM truncation detection and honest source-gap surfaces;
- ranking-order and record-headline synthesis fallbacks;
- active-bank, qwen-only parse corpus selection and verified dialogue deduplication.

Few-shots finish at the hard cap **15/15**. Their tree-shape curriculum is preserved; entity and
surface swaps cover livelihoods distance, CHANGE, causal behavior, and abstract job-market holes.

## Residue and proposals

There is no scored final residue. Characterized external/algebra debt remains:

1. **Upstream modeled evidence (open proposal):** World Bank employment shares explicitly sourced
   from modeled ILO estimates are labeled `observed` because they use SELECT, not ESTIMATE.
   `spec-proposals.md` proposes connector-declared trusted evidence taint without a new parser op.
2. **Positive record-set union (known open proposal):** “near a bank or ATM” cannot produce the
   union record set. Negated union is now normalized by De Morgan and needs no op.
3. **Multi-part questions (known dialogue decision):** one tree answers one clause; two unsafe
   generated golds demonstrate why clause splitting must precede parsing.
4. **Coverage limits:** OSM results over the safety cap and genuinely empty/sparse places produce
   DataRequests. This is honest incompleteness, not a benchmark failure.

## Deliverables

- `runs/*/{traces.jsonl,summary.json}` and browsable `runs/index.html` (39 checkpoint runs);
- `questions/seed.json`, `questions/gen-001.json`, `questions/gen-002-indirect.json`, and the
  append-only rejected `questions/breakers.json`;
- `corpus/parse.jsonl`: **52** unique qwen question→IR rows, all `meta.sector=livelihoods`;
- `corpus/clarify.jsonl`: **5** unique, verified, hole-free mechanical-binding rows;
- `FINDINGS.md`, `spec-proposals.md`, and ten experiment narratives under `chronology/`.

The final state is saturated under the tested sources, registers, and frozen v2.1 algebra: both
the 2B and frontier parse every active question perfectly, all deterministic executions have the
expected class, synthesis integrity checks are perfect, and the training artifacts contain only
active verified examples.

## Why Round 1 is not a true saturation claim

The preceding sentence used “saturated” too broadly. Precisely, Round 1 closed its own regression
suite. It did **not** establish saturation over the livelihoods question distribution because:

- only two data-source families and two principal grains were exercised;
- the neutral generator was shown the supported source vocabulary, biasing it toward answerable
  questions rather than actively seeking missing algebra;
- the indirect bank was used to derive repairs, so its final score is not an independent estimate;
- frontier parsing shared the same mechanical repair stack;
- 52 questions leave major capability families unprobed (filtering, grouping, units, distributions,
  temporal alignment, subgroups, record attributes, uncertainty, cross-source conflicts, and
  multi-output requests).

Round 2 therefore treats the 52 questions as the first development bank. Its stopping condition is
consecutive untouched holdouts with a flat **new failure-class discovery curve**, not a perfect
score on repaired questions. Results will be appended here only after the Round 2 freeze protocol.

### Round 2 checkpoint 1 — breadth infrastructure

The first capability snapshot confirms only 12 unique gold-tree skeletons in Round 1 and exposes
entirely empty cells including ANNOTATE, co-occurrence, presence, ascending/top-k ranks, explicit
multi-year windows, mixed-source compositions, subgroup filtering, and subnational series. The
snapshot is now generated as `coverage/matrix.json`, so later claims can be checked against semantic
cells rather than total questions.

Two official keyless connectors have been adopted after bounded live probes. ILOSTAT adds curated
country-year survey series for informal employment, weekly hours, and labor underutilization while
excluding rows explicitly marked model-extrapolated and refusing to splice overlapping survey
sources. Eurostat adds employment/unemployment series for six verified NUTS-2 regions, fixes every
non-time response dimension, and preserves upstream flags/update timestamps. The ten-probe source
integrity snapshot passes in full. This brings the working census to four source families and three
principal grains; it is a breadth prerequisite, not yet a saturation result.

### Round 2 checkpoint 2 — two failed freeze epochs

The first two blind sequences did not pass. Each produced 30/40 strict semantic matches despite
high coarse scores, so both freezes were invalidated and neither contributes to the saturation
claim. Their disclosed admissible rows expanded the development wall by 76 cases and drove repairs
for transfer typing, proxy/hole behavior, entity morphology, answer form, nested spatial logic,
and threshold binding. Four defective/ambiguous golds were quarantined rather than weakened.

Before epoch 003, the active ordinary regression wall is 382/382 across four source families; the
330 Round-2 rows plus seed and indirect banks pass the canonical audit. This is still a development
checkpoint. The required evidence remains three new consecutive untouched holdouts after the new
freeze, followed by the discovery curve, baseline arms, and corpus audit.

### Round 2 checkpoint 3 — wide search rejects saturation

The loop continued through freeze epoch 010 and expanded the certified development wall from 382
to 727 questions. Exact checksums, exclusions, and per-epoch results are recorded in
`chronology/20260713_round2_epochs_003_010.md`. The expanded compiler now handles terse and
goal-first answer forms, anaphoric holes, annotations over relations, left/right nested spatial
constraints, subset arithmetic, relation comparisons/ranks, NUTS/country routing, and explicit or
unknown transfer targets.

This work does **not** end in a saturation claim. Strict untouched results remain non-flat:
H3 30/40, H4 34/40, H5 15/40, H8 22/40, H9 40/40, H10 28/40, H11 31/40,
H12 37/40, H13 30/40, H14 23/40, H15 37/40, and H16 22/40. H9 demonstrates a local
plateau for an exact statistical register, not general solver saturation. H14–H16 remain failed
untouched evidence at this checkpoint and must drive the next development epoch.
