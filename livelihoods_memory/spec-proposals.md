# Spec proposals from this sector (append-only; do NOT edit the spec directly)
Each entry: date · the question that forced it · why the current spec cannot express/handle it ·
the proposed change · evidence (trace path). The cross-sector supervisor reconciles these.

## 2026-07-12 — Connector-leaf evidence labels for upstream modeled statistics

**Question that forced it:** “Is vulnerable employment in Kenya rising or falling?”

**Why v2.1 cannot express it honestly:** `SL.EMP.VULN.ZS` is explicitly published as a modeled
ILO estimate, but the retrieved value enters the tree through `SELECT`, not `ESTIMATE`. The frozen
executor rule therefore stamps the leaf and every downstream result `observed`. Synthesis then
says “observed by the World Bank,” even though no direct observation supports that label. Adding
an `ESTIMATE` node in the parser would also be false: this benchmark did not perform the upstream
ILO model, and gate semantics do not apply to retrieving an already-modeled statistic.

**Proposed change:** make evidence taint originate from either (a) algebraic `ESTIMATE`, or (b) a
connector-declared source evidence class. Extend the connector result contract with an optional
`evidence_label: observed|modelled|proxy` plus a human-readable method/source note. `_route_select`
sets the SELECT typed value's label from this trusted connector metadata; absence defaults to
`observed`. This adds no parser field and no kernel op, and keeps evidence classification out of
the language model. If provenance must distinguish our own estimates from upstream ones, add an
orthogonal provenance reason (`algebraic_estimate|upstream_model`) rather than a new taint class.

**Evidence:** `runs/tick-001/traces.jsonl`, row `lv-trend-01`: World Bank route for
`SL.EMP.VULN.ZS`, execution label `observed`, synthesis “observed by the World Bank.” Census and
official source semantics are recorded in `FINDINGS.md`.

## 2026-07-13 — Typed FILTER for record attributes and source dimensions

**Questions that forced it:** “Which mapped marketplaces in Nairobi are open on Sundays?” and
“What was France's informal-employment rate for women aged 25 to 54 in 2023?”

**Why v2.1 cannot express them honestly:** ANNOTATE can expose a column but cannot restrict rows.
SELECT has no predicate. Curating `female informal employment rate` as an indivisible entity is a
safe connector bridge for a fixed benchmark slice, but it does not compose age, sex, industry,
education, reliability flags, missing attributes, or conjunctions. Dropping adjectives silently
answers a different question.

**Proposed change:** add `FILTER {source, predicate}`. A predicate is typed data, not an opaque SQL
string: boolean `and|or|not`, leaf `{field, cmp, value}`, and a small comparator vocabulary
`eq|ne|lt|lte|gt|gte|in|exists|contains`. Fields must resolve against declared connector dimensions
or ANNOTATE columns; unknown fields produce a DataRequest. FILTER preserves evidence taint and
records input/output counts and the resolved upstream dimension codes in provenance.

**Evidence:** twelve independent `attribute_filter`/`subgroup_filter` probes in
`questions/round2-breakers.json`; source-dimension pressure from ILOSTAT and Eurostat is documented
in `coverage/source-census.json`.

## 2026-07-13 — Partitioned GROUP distinct from spatial/temporal AGGREGATE

**Question that forced it:** “Break down Germany's average weekly hours by sex for every year
since 2019.”

**Why v2.1 cannot express it honestly:** `AGGREGATE.by` is only `space|time` and returns one field
or series. It cannot retain a categorical partition, and emitting three unrelated roots would lose
the fact that the result is one comparable breakdown.

**Proposed change:** add `GROUP {source, keys:[field...], metric}` returning a typed table or keyed
collection. Reuse the typed field resolver from FILTER. `metric` should refer to a unit-checked
aggregate specification, not an unbounded string. RANK/COMPARE may consume a keyed result only via
an explicit reduction; no implicit flattening.

**Evidence:** six `group_partition` probes in `questions/round2-breakers.json`.

## 2026-07-13 — Record-set algebra

**Question that forced it:** “Show all marketplaces or coworking spaces in Nairobi.”

**Why v2.1 cannot express it honestly:** RELATE expresses spatial joins. It cannot union two record
sets, intersect identities, or subtract one typed set from another. Round 1's negated proximity
case is expressible via chained `beyond`, but that De Morgan construction does not provide positive
union and must not be generalized into one.

**Proposed change:** add `SET {items:[Records...], how:union|intersection|difference, identity}`.
The executor requires compatible record schemas and an explicit/deterministic identity policy
(source primary key where shared; otherwise declared spatial/entity dedupe). Provenance retains
per-input counts, duplicates removed, and identity policy.

**Evidence:** six `record_set` probes in `questions/round2-breakers.json`; positive union is also a
characterized Round 1 residue in `REPORT.md`.

## 2026-07-13 — Unit-tagged derived arithmetic

**Question that forced it:** “Normalize Accra's craft-workshop count per 10,000 residents.”

**Why v2.1 cannot express it honestly:** COMPARE offers difference/ratio but values have no unit or
denominator types. It will execute nonsensical arithmetic (hours minus percent, count divided by
rate), cannot scale a ratio, and cannot describe the resulting unit. Some existing same-unit ratios
work numerically but do not establish general derived-measure semantics.

**Proposed change:** first make units/measure definitions part of typed connector values. Then add
`DERIVE` over a restricted arithmetic expression (`add|subtract|multiply|divide|scale`) with unit
checking and explicit zero/missing alignment rules. Keep COMPARE for semantic comparison; do not
turn its `how` enum into an untyped calculator.

**Evidence:** six `derived_rate` probes in `questions/round2-breakers.json`; Round 2 mixed-source
questions exercise only manually audited same-unit difference/ratio cases.

## 2026-07-13 — Distribution-valued aggregation

**Question that forced it:** “What is the median distance from Nairobi coworking spaces to
marketplaces?”

**Why v2.1 cannot express it honestly:** the fixed aggregate vocabulary has no median, quantile,
histogram, spread, top share, or outlier policy. Substituting mean changes the requested statistic.

**Proposed change:** extend aggregation through a typed aggregate specification capable of
returning scalar quantiles or a distribution/histogram value. Parameters include quantile `q`,
binning policy, null handling, and (for spatial grids) cell definition. Exact and approximate
algorithms must be distinguished in evidence/provenance.

**Evidence:** six `distribution` probes in `questions/round2-breakers.json`.

## 2026-07-13 — Explicit temporal alignment and vintage

**Question that forced it:** “Compare Germany's labor series using only years present in both
ILOSTAT and World Bank.”

**Why v2.1 cannot express it honestly:** COMPARE scalarizes series endpoints. It has no inner/outer
calendar join, frequency conversion, lag, interpolation policy, or publication-vintage selector.
Connector-specific nearest-year fallback is useful for a point lookup but is not a general series
alignment algebra and can silently change a comparison.

**Proposed change:** add `ALIGN {items:[Series...], calendar, join, lag?, interpolation?, vintage?}`
returning explicitly aligned series plus a missingness certificate. COMPARE/DERIVE consume aligned
outputs without further implicit endpoint selection.

**Evidence:** six `temporal_alignment` probes in `questions/round2-breakers.json`.

## 2026-07-13 — Concrete epistemic CORROBORATE/VERIFY result

**Question that forced it:** “Do ILOSTAT and World Bank agree on France's self-employment rate in
2023?”

**Why v2.1 cannot express it honestly:** the architecture describes VERIFY at the claim layer, but
the concrete IR has no representation for independent-source agreement, conflict, uncertainty
intervals, observation flags, or sensitivity to source selection. A numerical difference alone
does not say whether sources are independent, definitions match, or disagreement is material.

**Proposed change:** add an epistemic `CORROBORATE`/`VERIFY` claim operation after units, measure
definitions, and temporal alignment exist. It returns `agreement|conflict|incomparable` plus the
evidence inspected, independence/lineage assessment, tolerances, flags, and unresolved asks. This
is not a SELECT source hint and should not force the parser to choose a preferred source.

**Evidence:** six `uncertainty_conflict` probes in `questions/round2-breakers.json` and the upstream
modeled-label proposal above.

## 2026-07-13 — Multi-clause plan is above the single-root kernel

**Question that forced it:** “Compare marketplaces in Nairobi and Accra, and list the Nairobi ones
near coworking spaces.”

**Why v2.1 cannot express it honestly:** one expression root yields one typed output. Forcing both
clauses into a COMPARE or RELATE drops one requested result; answering only the first is the exact
half-gold class rejected in Round 1.

**Proposed change:** add a dialogue/planning `BUNDLE` (or clause-plan) above the kernel with a list
of independently valid expressions, dependency references where needed, and an output contract.
Do not add BUNDLE to the data kernel until tests show cross-clause dependencies require it there.

**Evidence:** six `multi_output` probes in `questions/round2-breakers.json` plus the rejected
Marrakech half-gold in `questions/breakers.json`.

## 2026-07-13 — Causal requests remain typed asks, not ESTIMATE

**Question that forced it:** “Did opening more marketplaces cause household incomes to rise in
Nairobi?”

**Why v2.1 cannot express it honestly:** RELATE is association in space and ESTIMATE transfers a
field; neither establishes treatment, counterfactual, identification assumptions, or causal effect.

**Proposed change:** for now compile causal/counterfactual intent to a typed DataRequest describing
the outcome, treatment, population, period, and required design. If a causal claim layer is later
added, it must carry design/assumptions/diagnostics and a distinct evidence class; never overload
ESTIMATE or observational COMPARE.

**Evidence:** six `causal_counterfactual` probes in `questions/round2-breakers.json` and the Round 1
behavior questions.

## 2026-07-13 — Exact series-point selection

**Question that forced it:** “What's Ghana's self-employment share sitting at right now?”

**Why v2.1 cannot express it honestly:** `SELECT(time:null)` retrieves the available series. The
executor may choose endpoints internally for a comparison, but a standalone request for one latest
value has no explicit scalarizing operation. Treating null time as “latest” would break existing
series and trend semantics, while inventing a calendar year changes the user's request.

**Proposed change:** introduce a typed series-point selector, provisionally
`PICK {source, which:latest|earliest|as_of, as_of?, fallback:exact|previous|nearest}`. It returns one
time-stamped scalar and records the selected observation, source update/vintage, and fallback in
provenance. `as_of` requires an explicit instant; no silent nearest-year policy is permitted. This
may ultimately be a restricted REDUCE operation, but must not overload `SELECT.time` until the
type distinction between interval filtering and point selection is explicit.

**Evidence:** pre-run exclusion `h18-030` in `questions/holdout-h18-generated.json` and admission
record `chronology/20260713_round2_epoch_012_h18_admission.md`.

## 2026-07-13 — Explicit source gaps are not semantic holes

**Question that forced it:** “For Ghana I need the actual headcount of informal-sector workers —
the number of people, not the percentage rate.”

**Why v2.1 needs a protocol clarification:** the requested measure and region are fully specified,
but no connector supports that measure. Replacing the literal entity with a `?measure` hole asks
the user to repeat information already supplied and can falsely improve ambiguity scoring. The
correct result is a `DataRequest(reason:no_connector)` grounded in the literal requested measure.

**Proposed change:** make source availability orthogonal to semantic binding. Preserve explicit
unsupported entities, fields, and regions as literals; emit a source-gap DataRequest with the
missing connector capability and required evidence. Use holes only for unresolved user meaning or
references. Benchmark metadata must therefore allow `expect:data_request` with `must_hole:false`.

**Evidence:** admitted rows `h18-045` and `h18-046` in `questions/holdout-018.json`.

## 2026-07-13 — Connector-declared temporal admissibility

**Questions that forced it:** “Is the number of coworking spaces near a bank increasing in
Berlin?” and “Did the number of craft workshops not near a park in Accra increase between 2015
and 2020?”

**Why v2.1 cannot handle them honestly:** the OSM connector supplies a current snapshot with no
historical observation time, but the symbolic executor accepts `SELECT.time` on those records.
It can therefore return an apparent answer for a trend or two-endpoint change even though both
operands came from the same present-day snapshot. Allowing `answer_or_data_request` would conceal
the evidence defect rather than characterize source variability.

**Proposed change:** every connector declares temporal capability (`snapshot`, `historical`, or
`timeless`), supported valid-time range/frequency where applicable, and the distinction between
record valid time and retrieval time. The executor must fail closed with a typed source-gap
`DataRequest` whenever a trend, historical endpoint, or time filter requires evidence the source
cannot supply. Provenance must record the capability decision. This is a connector/executor
contract, not a new parser operation.

**Evidence:** rejected pre-contact candidates `h19-057` and `h19-062` in
`questions/holdout-h19-generated.json`; admission record
`chronology/20260713_round2_epoch_013_h19_admission.md`.

## 2026-07-13 — Unbounded scalar change needs an interval policy

**Question that forced it:** “How much did employment in agriculture change here?”

**Why v2.1 is ambiguous:** the frozen convention says absent time is `null`, meaning the available
series rather than a time hole. But “how much changed” requests one scalar difference and therefore
needs two endpoints. Two independently invented time holes violate the null-time convention;
duplicating the same null-time series on both sides produces a meaningless zero; silently choosing
the first and last available observations hides a source-dependent interval.

**Proposed change:** Codex/Fable should choose one protocol-level rule: either (a) compile an
unbounded scalar change into a typed interval clarification with start/end slots, or (b) define an
explicit available-range reduction whose returned provenance names the selected endpoints. Until
that choice is released, such questions are ambiguity cases and benchmark authors may not invent
endpoint holes ad hoc. Explicit two-year changes and ordinary unary trend requests remain
unchanged.

**Evidence:** declared bad gold `h19-013` in `questions/holdout-019.json` and independent H19
adjudication in `chronology/20260713_round2_epoch_013_h19_first_contact.md`.

## 2026-07-13 — Family-level discovery accounting and adversarial variants

**Failure that forced it:** H20 produced six failures in the same endpoint-ranking family. Counting
them as six independent algebra gaps would exaggerate novelty; counting the bank as one issue would
hide the breadth of surface forms that broke the compiler.

**Proposed protocol change:** saturation accounting has two axes: discovery families and failing
rows. A family is absorbed only after one generalized repair, multiple positive surface variants,
negative guards against adjacent semantics, a complete-wall regression, and a new untouched-bank
contact. The plateau must be flat on both axes. Reports publish family definitions and row counts;
they may not relabel paraphrases as distinct discoveries or collapse heterogeneous failures into one.

**Evidence:** `h20-019`, `020`, `022`, `023`, `024`, and `026` all require
`RANK(COMPARE(endpoint,endpoint) × candidates)` but use distinct prefix/suffix lists, arrow years,
fall/improvement polarity, top-N, and regional wording.

## 2026-07-13 — Pre-contact semantic gold lints

**Failure that forced it:** the immutable H20 golds for `h20-019` and `h20-027` model a complete
ranking even though each question asks for one winner; `h20-075` does not disambiguate a named
statistical density from density over membership records.

**Proposed protocol change:** before checksum freeze, admission must lint rank cardinality (singular
winner → `k:1`, top-N → `k:N`, explicit full order → no `k`), candidate coverage, distinct named
operands, complete unsupported noun phrases, source-gap versus semantic-hole status, and
record/count/presence/density output form. Lint findings require human adjudication and are recorded
before contact. The linter does not auto-rewrite semantic gold.

**Evidence:** declared H20 defects in `coverage/gold-defects.json` and the immutable first-contact
record in `chronology/20260713_round2_epoch_014_h20_first_contact.md`.

## 2026-07-13 — Output-form-sensitive coarse scoring

**Failure that forced it:** H20 coarse scoring gave compositionally wrong record queries substantial
credit after an invented count wrapper, while strict canonical audit correctly rejected them.
`h20-070` asked for related records but the first parse returned their count.

**Proposed change:** add a separate output-type/form dimension to the coarse diagnostic: Records,
presence, count, density, Series, Scalar, and Ranking (including `k`). Keep strict canonical audit as
the release gate. Do not merely increase the weight of op multisets, which cannot distinguish a
wrapper from the requested root contract.

**Evidence:** H20 ordinary score 0.917 versus strict 18/40 at first contact; `h20-070` is the minimal
record-versus-count counterexample.

## 2026-07-13 — Connector-declared annotation-layer admissibility

**Questions that forced it:** H21 candidates asked to attach daily customer footfall and daily
electricity-outage duration to mapped records.

**Why the current contract is unsafe:** `ANNOTATE` accepts an arbitrary layer string. The executor
can return an Answer whose added field is absent/null rather than a typed source-gap DataRequest.
Schema validity therefore masquerades as evidence availability.

**Proposed change:** connectors declare supported annotation fields, field type/unit, missingness,
and coverage. ANNOTATE must fail closed when the requested field has no declared provider or when
coverage cannot support the requested records. Provenance records provider, matched-row count, and
null count. This is connector/executor admissibility, not a new parser op.

**Evidence:** pre-contact exclusions `h21-034` and `h21-064` from
`questions/holdout-h21-generated.json`; both explicit unsupported layers executed as answers.

## 2026-07-13 — Resolver morphology must not become lexical prefix guessing

**Question that forced it:** “Give me the registered gig-work platforms operating in Nairobi.”

**Why the current resolver is unsafe:** prefix-tolerant token matching can equate `work` with
`workshop`, routing an explicit unsupported gig-platform request to OSM craft records. The result
is a grounded-looking answer from the wrong entity family instead of a source-gap DataRequest.

**Proposed change:** replace uncontrolled token-prefix equality with declared aliases or bounded
morphological normalization. Every fallback match carries a resolver certificate (matched alias,
token transform, alternatives); cross-lexeme prefix matches fail closed. Add adversarial source-gap
tests whose words are prefixes of supported entities.

**Evidence:** pre-contact exclusion `h21-035`; its gold SELECT on the complete unsupported literal
executed as an OSM answer.

## 2026-07-13 — Bounded direction wording needs a stable endpoint/trend convention

**Questions that forced it:** “From 2010 to 2019, did vulnerable employment go up or down?” versus
“Across the explicit 2022–2024 window, did employed persons trend upward or downward?”

**Why v2.1 needs clarification:** both surfaces name a bounded window and a direction, but endpoint
sign and fitted series trend can disagree. Independent adjudication disagreed on whether the first
is CHANGE or TREND.

**Proposed convention:** explicit `from A to B` event wording (`did X go up/down`, `increase or
decrease`) denotes endpoint CHANGE; progressive/trajectory wording (`was X increasing`, `did X
trend upward`, `over/across the window`) denotes unary TREND. If neither cue determines the
quantity, admission must reject or allow explicit alternative golds rather than silently choosing.

**Evidence:** `h20-011`, corrected development row `h4-014`, deterministic adjacent negative
guards, and H21 control `h21-078`.

## 2026-07-13 — National connectors require an explicit scope certificate

**Question that forced it:** H21's mixed comparison subtracts France's national labor-force
participation from Ile de France's regional employment rate. The first wrong parse scoped both
leaves to Ile de France, yet execution returned the same numeric result as the correct gold.

**Why the current connector contract is unsafe:** Nominatim's display name for a subnational place
contains its parent country. The World Bank resolver used that suffix to convert `Ile de France`
into `FRA`, silently coarsening the requested geography and making semantically wrong IR appear
well grounded. The same hazard applies to national-only ILO tables and any future source whose
native grain is coarser than SELECT.region.

**Proposed change:** each connector returns a scope certificate containing requested scope,
resolved scope, native source grain, match rule, and any coarsening. Exact native-scope matches may
execute. Coarsening requires an explicit algebra/policy instruction or returns a typed
`national_scope_required`/`grain_mismatch` DataRequest; a geocoder parent is never implicit user
consent. Cross-grain COMPARE additionally records both certificates. This corroborates BUG-002 but
extends its guard from arithmetic to every SELECT route.

**Evidence:** `h21-037` first-contact actual and gold returned the same 21.337 only under the unsafe
fallback; independent execution adjudication and the fix2 replay are recorded in
`chronology/20260713_round2_epoch_016_h21_absorption.md`.

## 2026-07-13 — Recursive hole safety for every value-or-node slot

**Question that forced it:** H22 asked to transfer an Accra donor pattern to an unnamed target city.
The parser represented the target as `REGION(place="?place")`. The schema checked
`ESTIMATE.target` only as a required leaf, did not recurse into the REGION, and reported the tree
bound. The executor then sent the unresolved placeholder to geocoding and returned `gate_failed`
instead of `unbound_holes`.

**Proposed implementation requirement:** every schema slot that accepts either a scalar value or a
node must recurse when given a node. The validator's collected-hole set is the sole pre-execution
authority, and connector calls are forbidden until it is empty. Add an exhaustive slot test matrix;
this implements the existing frozen recursive-hole rule and does not add an algebra operator.

**Evidence:** immutable `h22-063`, epoch-016 first-contact trace, and the corrected fix2 trace.
Governance record: `BUG-004`.

## 2026-07-13 — Declared numeric value binding for record means

**Question that forced it:** “What is the mean distance from Bengaluru craft workshops to their
nearest markets?” The admitted gold correctly composed `AGGREGATE(mean, RELATE(distance,...))`, but
the executor had no spatial-mean branch and silently returned the number of related rows (371).

**Proposed contract:** a record-valued producer may declare a typed numeric value column and unit.
`RELATE(distance)` declares `dist_km`; a numeric ANNOTATE may declare its connector field. Spatial
mean consumes only that declared column, records its non-null coverage and unit, and returns a
DataRequest if none exists. It must never guess among numeric ids/coordinates or fall through to
count. The local v2.1 implementation now safely supports `dist_km`; the general typed contract
remains proposed.

**Evidence:** immutable `h22-043` and `h22-045`, direct gold execution adjudication, and executor
regressions. Governance record: `EXEC-001`.
