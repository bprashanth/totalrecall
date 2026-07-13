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
