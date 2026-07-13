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

### Round 2 checkpoint 4 — cross-family H19 rejects saturation again

After H17 and H18 drove epochs 012 and 013, H19 was independently authored with Google's
Gemini 3.1 Pro under a parser-blind allowlist. Sixty-four candidates were generated; 40 survived
pre-contact semantic and execution audit. That audit itself rejected historical trend questions
over current-snapshot OSM data instead of weakening their expectation, producing governed
proposal `SRC-001`. It also exposed the unresolved policy for a scalar change with no interval,
recorded as `ASK-003`.

H19 first contact scored 0.927 coarsely and only 21/40 under the strict canonical audit. Final
adjudication found 16 valid compiler/schema discoveries, two bad or ambiguous golds, and two
strict-audit equivalence defects. General fixes now preserve explicit subnational record scope,
compile complete rank value subtrees (including densities and endpoint changes), retain all list
members, complete nested spatial constraints, and omit absent optional fields rather than emitting
schema-invalid nulls. The two bad golds are quarantined and excluded from training.

Epoch 014 recertifies 963 valid questions across 22 banks and 27 skeletons: ordinary 963/963,
strict 961/963 overall and 961/961 eligible, dialogue 5/5, and 51/51 deterministic regressions.
The corpus contains 975 parse and 5 clarification rows with all six declared bad-gold questions
excluded. This is still not saturation. H19 is disclosed development, so the consecutive untouched
counter is zero and three new post-epoch-014 cross-family banks remain required.

### Round 2 checkpoint 5 — H20 adds family-level stopping evidence

H20 was authored after the epoch-014 freeze by Cursor Agent using xAI Grok 4.5 High. Eighty blind
candidates were independently audited down to a 40-row bank spanning endpoint-change ranks,
relational ranks, nested polarity, mixed-source comparisons, deictic ambiguity, long lists, and
explicit source gaps. Its checksum and exclusions were committed before qwen contact.

First contact scored 0.917 under the ordinary diagnostic but only 18/40 under strict canonical
audit. Independent adjudication found 19 clean compiler discoveries, two compiler discoveries with
orthogonal rank-cardinality gold defects, one ambiguous density gold, and no audit-equivalence
defects. The valid discoveries reduce to six semantic families rather than 21 unrelated defects:
endpoint quantity construction, candidate/item/cardinality separation, distinct relation roles,
clause-local mixed-source binding, deictic-place semantics, and full unsupported phrase/output-form
preservation.

Sixty-eight deterministic regressions now exercise positive variants and adjacent negative guards.
The final disclosed H20 replay is strict 37/37 over eligible rows; the two immutable mismatches are
the registered missing-`k:1` golds, and the matching but ambiguous density row remains excluded.
Thirty-seven rows join development. The first replay's misleading 40/40—before the compiler began
enforcing singular-winner cardinality—is direct evidence that matching defective gold is not
closure.

H20 also refines the stopping philosophy. SAT-002 proposes publishing both discovery-family and
failing-row curves and requires generalized repair plus variants, negative guards, full-wall
regression, and a later untouched contact before a family closes. BNCH-001 proposes pre-contact
semantic lints for cardinality, candidate coverage, operands, source gaps, and output form.
SCR-001 proposes output-form-sensitive coarse diagnostics while retaining strict audit as the
release gate. These are durable proposals for Fable review, not silent bootstrap changes.

Epoch 014 is retired and the saturation counter is still zero. Epoch 015 now certifies exactly
1,000 questions across 23 banks and 31 skeletons: ordinary 1,000/1,000, strict 998/1,000 overall
and 998/998 eligible, dialogue 5/5, and 69/69 deterministic regressions. Corpus compilation yields
1,012 unique parse rows plus five clarification rows with composite defect identity preserved.
H21 and later cross-family banks must independently test whether the H20 families actually remain
closed; none of the disclosed H20 evidence counts toward the required three passes.

### Round 2 checkpoint 6 — H21 proves the family gate was necessary

H21 first contact against epoch 015 scored 0.902 under the ordinary diagnostic and only 17/40
under strict canonical audit. Independent adjudication classified all 23 mismatches as genuine
compiler-bearing rows and found no gold or audit defects. The failures again reduce to six broad
families, but they are new variants: ranked endpoint ratios and candidate closure, heterogeneous
source/facet operands, literal median/share source gaps, user-relative and anaphoric holes,
distance/corresponding relational counts, and written subtract/divide orientation.

This rejects saturation and resets the counter to zero. It also empirically validates SAT-002's
stronger rule: a family is not closed merely because disclosed examples and guards pass; a later
untouched contact must fail to find a valid new variant. H21 found new variants in every family.

The disclosed fix2 replay is 40/40 under both ordinary and strict scoring, with 91/91 deterministic
regressions. All 40 independently adjudicated rows join development. Connector hardening prevents
national World Bank/ILO data from silently satisfying a subnational SELECT, qualifies curated
statistical regions before geocoding, and converts region-resolution failures to DataRequests.
SRC-003 proposes general native-grain scope certificates for Fable review.

Epoch 015 remains permanently failed. A complete epoch-016 wall/corpus/dialogue certification and
new checksum freeze are required before H22; no H21 replay contributes to the three-bank stopping
sequence.

Epoch 016 subsequently certifies 1,040 questions across 24 banks and 34 skeletons: ordinary
1,040/1,040, strict 1,038/1,038 eligible, dialogue 5/5, source census 10/10, and deterministic
regressions 92/92. Two earlier wall attempts were rejected rather than averaged away: one exposed a
Warsaw source-truncation expectation that unsafe geocoding had hidden, and one exposed a late-pass
arithmetic regression. The corpus now contains 1,052 unique parse rows and five clarification rows.
The untouched saturation counter remains zero until a post-freeze H22 contact.

### Round 2 checkpoint 7 — H22 closes eligible rows but opens the executor contract

H22 again rejects saturation: epoch-016 first contact was strict 17/40. All 23 mismatches contained
real compiler failures, spanning five generalized families, while four questions also had
ambiguous or inexpressible wording and were quarantined rather than tuned. The repaired disclosed
bank is strict 36/36 over eligible rows; the four immutable defects remain visible.

More importantly, direct gold execution found that valid algebra could still lie: spatial mean
returned a row count, all-null annotation counted as grounded, a nested transfer-target hole
executed, and a one-point trend returned a null Answer. The executor/schema now fail closed and the
coarse diagnostic checks rank cardinality, arithmetic mode, reduction head, and annotation layer.
Governance proposals BUG-004 and EXEC-001 capture the cross-sector contracts; strict canonical
audit remains mandatory.

The saturation counter is zero. H23/H24 raw banks were generated before the H22 repairs and may
only be used as pre-freeze development pressure. Countable evidence must be generated anew after a
complete epoch-017 freeze.

### Round 2 checkpoint 8 — H23/H24 prevent an under-tested epoch-017 freeze

The corrected post-H22 wall is exact on all 1,074 eligible rows across 25 banks, but two
pre-freeze pressure banks show that regression closure is not yet enough. H23 is strict 8/40 and
H24 is strict 25/40 on first contact. They were generated against the retired epoch-016 boundary,
so they are disclosed development pressure and contribute no saturation passes.

The preserved contact establishes 47 exact divergences to adjudicate before epoch 017 can freeze.
The counter remains zero. After generalized absorption and another complete wall, all countable
saturation banks must be newly authored from the resulting checksum boundary.

### Round 2 checkpoint 9 — pressure absorbed, boundary still not frozen

Independent adjudication found 46 compiler-bearing divergences across the two pressure banks plus
one strict-audit equivalence defect. Generalized repairs move H23 from 8/40 to 40/40 strict and H24
from 25/40 to 40/40; 114 deterministic tests pass. The separate disclosed development releases
score 1.000 ordinarily and 40/40 strictly. None of those replays count toward saturation.

This round materially strengthened evidence honesty. A zero-overlap entity-restoration bug and
uncontrolled resolver prefix/subset matching could turn unsupported restrictive phrases into
plausible answers from broader OSM entities. The resolver now fails closed except for declared
aliases, and legacy unsafe gold assumptions are quarantined. Frozen IR signatures are enforced
before execution. Verified World Bank Gini and OSM metro routes expand the live source census to
14/14 probes across four tested families.

The governance ledger now carries additional reviewable proposals: complete input-type validation
(`BUG-005`), constrained typed holes (`ASK-005`), and spatial candidate generation/optimization
(`ALG-010`), with expanded evidence for fail-closed resolver morphology (`BUG-003`). These are
proposals for orchestrator/Fable reconciliation, not silent changes to algebra v2.1.

Because parser, connector, schema, executor, and audit code changed, the prior 1,076-row wall is
retired. The next required step is another complete all-bank wall, corpus/dialogue/source
certification, and an epoch-017 checksum freeze. Only banks newly generated after that freeze may
start the three-contact saturation sequence.

### Round 2 checkpoint 10 — epoch 017 certified, counter still zero

After two rejected full walls, two later candidate walls invalidated by corpus/freeze-core changes,
and the final v8 rerun, epoch 017 is certified. The wall contains 1,156 questions across 27 runnable
banks and 37 unique skeletons. All 1,153 eligible rows pass both the ordinary harness and strict
canonical audit. The three excluded active rows are exact immutable defects, not tolerated compiler
residue. Deterministic regressions pass 120/120, the expanded source census passes 14/14, and model
plus mechanical dialogue binding each pass 5/5.

The training corpus is now bank-scoped. A freeze audit caught an old H10 proxy trace re-entering
through global text membership even though its development row had been superseded. Exact active
bank+ID+text admission removes it and yields 1,148 unique parse rows plus five clarification rows
with zero immutable-defect leakage. `BUG-006` makes that rule reviewable for automatic bootstrap
adoption.

The 51-file checksum manifest is `freezes/epoch-017.json`; machine-readable gate evidence is
`coverage/epoch-017-certification.json`. This is a start line, not a saturation claim. H23/H24 and
all repaired walls are development evidence, so the untouched counter remains zero. Three entirely
new post-freeze cross-family banks of at least 40 rows each are still required, with any valid new
family, repair, connector, or core change retiring the sequence and forcing a new boundary.

### Round 2 checkpoint 11 — H25 invalidates compiler-only saturation and establishes epoch 018

H25 was the first countable post-epoch-017 bank and immediately rejected that boundary: ordinary
0.918 and strict 29/40. All eleven exact mismatches were compiler-bearing. General repairs close
existential output heads, worded fractions, exact indicator aliases, winner cardinality, complete
rank candidates, direction, relational rank recovery, transfer roles, and unresolved anaphora.
The disclosed replay is ordinary 1.000 and strict 40/40, but contributes zero saturation passes.

More importantly, H25 forced an audit of the delivered answer rather than only the internal IR.
The supposedly certified epoch-017 wall contained systemic truth failures: 43 of 44 true Boolean
results were narrated as no/zero, 45 observed results were called modelled, modelled estimates lost
local-corroboration warnings, and prose invented aggregates and source attributions. Epoch 017 is
therefore invalid independently of its H25 compiler failures.

The solver now renders common typed values and failures deterministically and freezes a separate
all-row synthesis/evidence audit. Six candidate walls were rejected for progressively subtler
issues: stale scoring, temporal language on cross-sectional differences, incomplete comparison
answers, null arithmetic, omitted annotations, scope taxonomy, partial-list evidence, nonspecific
DataRequests, coordinate precision, and compact traces that omitted cited series endpoints. V7
passed independent review; v8 repeated the full wall after the certification artifact entered the
freeze evidence.

Epoch 018 covers 1,196 questions across 28 runnable banks and 38 skeletons. Ordinary and strict
audits pass all 1,193 eligible rows; synthesis faithfulness passes 1,196/1,196. Regressions pass
143/143, source census 14/14, dialogue 5/5 on both binders, and corpus compilation produces 1,188
unique parse rows plus five clarification rows. The 54-file manifest is `freezes/epoch-018.json`.

This is a stronger start line, not saturation. `BUG-007`, `SAT-003`, and `BNCH-002` are explicit
Fable-review proposals for deterministic answer truth, prose/evidence saturation gates, and
executable pre-contact gold/source warrants. The untouched counter is zero; only fresh H26–H28
banks generated after the epoch-018 checksum may advance it, and any valid repair at any layer
resets the sequence.

### Round 2 checkpoint 12 — H26 absorbed, epoch 019 wall pending

H26 invalidated the epoch-018 line before parser contact when its executable-gold audit exposed an
untyped connector outage (`BUG-008`), then supplied a much broader 86-row disclosed pressure bank.
Immutable first contact was ordinary 0.902 and strict 53/86. Independent GPT-5.6 Sol High
adjudication found 32 compiler/binder gaps, one canonical country-label equivalence, and no gold
defects among the 33 non-exact rows.

General v2.1 repairs now close clause-scoped statistical and spatial arithmetic, nested relations,
rank candidate/quantity semantics, typed anaphora, behaviour boundaries, transfer composition, and
late-pass stability. The disclosed final replay is ordinary 86/86, strict 86/86, and synthesis
86/86; 151 deterministic tests pass. `questions/round2-h26-dev.json` permanently adds these rows to
the regression wall.

No new algebra operation was needed. `BNCH-002` and `SAT-003` gained additional supporting evidence,
while `BUG-008` remains the only new framework proposal from this cycle. The saturation counter is
zero. Epoch 019 cannot freeze until the complete historical wall, source census, dialogue suite,
corpus audit, coverage matrix, and answer-faithfulness audit pass with H26 included.

### Round 2 checkpoint 13 — epoch 019 certified at 1,282 active questions

The expanded wall now contains 1,282 questions across 29 runnable banks and 39 skeletons. All
1,279 eligible rows pass ordinary and strict canonical scoring, and synthesis/evidence audit passes
1,282/1,282. Regressions pass 152/152, source census 14/14, and both dialogue binders 5/5. The corpus
contains 1,273 unique parse rows plus five clarification rows, including all 86 disclosed H26 rows.

The first wall correctly caught one historical regression: a behavioural heuristic erased an
explicit statistical rank because its decision preamble contained “choosing.” A general precedence
guard closed it and the complete v2 and post-certification-artifact v3 walls are clean. Coverage
also now shares the freeze bank registry after a directory glob admitted 80 retired pressure rows;
`BUG-009` exposes that framework invariant for Fable review.

Epoch 019 is a fresh start line, not a saturation result. H26 and every repair/replay contribute
zero untouched passes. The checksum manifest is `freezes/epoch-019.json`; three entirely new,
independently generated post-freeze banks must pass every compiler, execution, evidence, source,
corpus, and audit gate without causing a change.

### Round 2 checkpoint 14 — H27 rejects epoch 019 and widens compositional closure

H27 was generated by a parser-blind Cursor Agent invocation, independently audited with GPT-5.5
High before contact, directly executed, checksummed, and committed before qwen saw any row. Its 100
questions span 67 declared capability families, 20 shapes, 60 adversarial surfaces, seven hole
cases, and fourteen estimates. Immutable first contact scored ordinary 0.920 and strict 62/100, so
epoch 019 retired with zero saturation passes.

The 38 exact misses reduce to reusable record/output heads, spatial clause composition,
qualifier-scoped statistics, complete derived ranks, donor-source transfer plans, unsupported
literal fidelity, and geography/entity warrant. General v2.1 closure repairs now recover all
faithfully stated rows. Four immutable rows are registered defects because their gold invents
Córdoba Argentina, Cebu City, or a train-station subtype absent from the question; their disclosed
development wording is generated reproducibly in `questions/round2-h27-dev.json` (`BNCH-003`).

The second immutable replay is strict 96/100 with exactly those four declared defects remaining.
It also exposed and fixed a late mixed-geography regression and a false coarse-score disagreement
between hyphenated and spaced annotation layers (`BUG-010`). The disclosed final replay is ordinary
1.000, strict 100/100, and synthesis 100/100 after exact unsupported train-station literals were
preserved. Every repair and scorer change keeps the counter at zero and moves the next possible
start line to epoch 020; the expanded historical wall is now mandatory.
