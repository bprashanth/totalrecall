# Spec proposals from this sector (append-only; do NOT edit the spec directly)
Each entry: date · the question that forced it · why the current spec cannot express/handle it ·
the proposed change · evidence (trace path). The cross-sector supervisor reconciles these.

## 2026-07-12 · COMPARE how:difference has NO operand-order semantics (transport, tick-004)

**Question**: tr-chg-01 — "How much did the number of air passengers carried change between 2010
and 2019 in Vietnam?"

**What happened**: the 2B compiled left=SELECT@2010, right=SELECT@2019 (operands in the order the
question names them — a fully defensible reading). The gold used left=@2019, right=@2010 (change
= later minus earlier). Shape scoring treats the trees as identical (same op multiset), both
execute cleanly — but the scalars have OPPOSITE SIGNS (-38,849,407 vs +38,849,407), and the
synthesis stage faithfully rendered the negative as "decreased by 38,849,407" for a series that
in reality tripled. A silent wrong answer that every structural/behavioral check greenlights.

**Why the spec can't express/handle it**: ir-spec v2 defines `how ∈ difference|ratio|...` but
never defines which operand is subtrahend/divisor. The algebra has a redundant denotation pair
(COMPARE(a,b) vs COMPARE(b,a)) whose members are NOT equivalent, yet canonicalization (tick-005
rule) has no way to pick one — for CHANGE questions the user's intent fixes the orientation
(change over time = later minus earlier), but that intent lives outside the tree.

**Proposal**: define in the spec: for `how: difference|ratio`, when both operands carry
resolvable time anchors, the canonical orientation is LATER-minus-EARLIER (resp. later/earlier),
and executors MUST orient accordingly (stamping the reorientation in provenance); when operands
are place-anchored (A vs B, same time), orientation stays as-written (first-named = left) and
the answer surface must name the operands. Alternative considered: force the parser to always
emit later-first — rejected, it penalizes a defensible parse for an unstated convention.

**Evidence**: runs/tick-004/traces.jsonl (tr-chg-01: ir + execution.value.note
"14377619 difference 53227026 = -38849407"); gold_ir in questions/seed.json.

**Interim harness measure (documented in FINDINGS)**: executor `_compare` now orients
difference/ratio by series end-year when both sides expose one (later minus earlier), noting
"oriented later-minus-earlier" in provenance. Place-vs-place comparisons (equal/absent years)
are untouched.

## 2026-07-12 · Multi-part questions: one tree can only answer the FIRST clause (transport, gen-001)

**Questions**: gen-tran-09 "Does Munich have more bus stops than Stuttgart? And of those bus
stops, how many are within 1 km of a railway station in each city?"; gen-tran-10 "Compare the
number of railway stations in Oslo and Helsinki, and also tell me which has more tram stops?"

**What happened**: the strong gold author (deepseek-v4) produced valid, executing golds that
SILENTLY DROP the second clause (both golds are just the first-clause COMPARE). Structural
admission passed them — every check is per-tree, and the tree is a correct compilation of
clause one. The parser under test degrades the same way, so scoring shows green on a half-answer.

**Why the spec can't express it**: an IR evaluation returns ONE Answer (or DataRequest). There
is no tuple/sequence construct, and RANK/COMPARE cannot merge heterogeneous sub-questions
("difference of counts" + "which has more trams" are different metrics over different entities).

**Proposal**: either (a) a QUERYSET wrapper (ordered list of independent trees, answers
returned as a labelled tuple — no cross-tree dataflow, purely multiplexing), or (b) a
documented DIALOGUE-layer rule: multi-part questions are split upstream of the parser and
compiled/answered one tree at a time (the clarify machinery already supports sequential turns).
(b) requires no algebra change and matches the one-question-one-tree design stance; recommend (b).

**Evidence**: questions/gen-001.json (gen-tran-09/10 gold_ir vs question text);
runs/tick-006-gen-001/traces.jsonl once run.

**Judge decision meanwhile**: the two questions STAY in the bank with first-clause golds — both
parser and gold degrade identically, so they measure compilation of the dominant clause; the
half-answer limitation is recorded here rather than papered over.

# ---------------- Round 2 (2026-07-13) ----------------
Evidence base: `questions/breakers-round2.json` (32 probes, 8 capability families) +
`runs/round2-breakers-pre/traces.jsonl` (2B behavior, pre-fix) and `runs/round2-breakers-post/`
(after the three executor completions). Headline parser behavior on inexpressible asks:
**27/32 silently WEAKENED the question to something expressible** (counted all bus stops when
asked for sheltered ones; counted only trams when asked for bus+tram combined; answered the
total when asked for a per-mode breakdown), 4 honest DataRequests, 1 invalid tree, 0 invented
ops. A 2B under out-of-algebra pressure does not hallucinate syntax — it quietly narrows
semantics. That is precisely why inexpressible questions must become proposals rather than
weakened golds: the weakened tree scores green and reads authoritative.

## 2026-07-13 · FILTER / attribute predicates (brk2-01..06; gen3-tran-03)

**Questions**: "How many bus stops in Winnipeg have shelters?" and 5 siblings (wheelchair
access, platform counts, opening hours, electrification, night service).
**Why v2.1 cannot express them**: SELECT picks an entity class; ANNOTATE adds a column;
nothing predicates on attributes. The upstream DATA exists (OSM shelter=yes, GTFS
wheelchair_boarding/calendar).
**Observed degradations**: the 2B counts the UNFILTERED class (brk2-01: all 200 bus stops —
a fluent wrong answer); the gold author silently widens named-instance refinements
(gen3-tran-03: "central railway station" → all stations).
**Proposal**: a FILTER op `{op, source, attr, predicate, value}` over Records (the spec's own
open question §"Do we need a FILTER..." — transport now has 7 concrete instances). ANNOTATE
alone cannot substitute: it adds the column but nothing consumes it.

## 2026-07-13 · GROUP / partition key (brk2-07..10)

**Questions**: "bus stops per district", "ridership by mode", "which neighbourhood has the
most stops", "each of Brno's districts".
**Why**: AGGREGATE collapses to ONE value; RANK requires the caller to enumerate items. No
group key, no sub-region enumeration, and the one-answer contract forbids the plural output.
**Observed**: brk2-08 answered the system-wide TOTAL when asked for a by-mode breakdown —
green-scoring, wrong. **Proposal**: `AGGREGATE.group_by: <layer|key>` producing a keyed Field
(one answer object, many labelled values) — subsumes the multi-output half of the Round-1
multi-part proposal for the homogeneous case.

## 2026-07-13 · Positive UNION over record sets (brk2-12..15) — transport evidence for the OPEN cross-sector proposal

**Questions**: "bus and tram stops combined", "ferry terminals and railway stations",
"bus, tram or train access points", union nested in COMPARE.
**Why**: no OR over record sets; no honest umbrella entity covers the asked unions.
**Observed**: the 2B counts ONE branch of the union (brk2-12: trams only — a half-answer
indistinguishable from a real answer) or dies no_connector on the union phrase (brk2-14).
**Position**: +1 to the open UNION proposal with these traces. NOTE: negated union needs NO
new machinery — De Morgan via chained `beyond` is already expressible (livelihoods proof);
this entry is strictly about the positive case. Union also composes upward (brk2-15): fixing
it at the record-set level fixes it inside COMPARE/RANK for free.

## 2026-07-13 · Distribution metrics: median / percentile (brk2-27..29)

**Why**: metric vocab is count|density|mean|presence; no order statistics over a series or
over ranked items (RANK truncates from the top only — no middle selection).
**Observed**: brk2-29 ("90th percentile") pushed the 2B into a structurally INVALID ESTIMATE
(missing source) that the repair round could not save — the only invalid tree in the program.
**Proposal**: extend metric vocab with `median` (and optionally `p<NN>`), defined over Series
and over RANK item values.

## 2026-07-13 · Temporal argmax / alignment (brk2-23, 24, 26)

**Questions**: "did A and B peak in the same year", "in which YEAR did X fall the most",
"have A and B moved together since 2010".
**Why**: no argmax-year, no windowed differences, no series-vs-series co-movement; COMPARE
reduces series to endpoint scalars, and trend_direction outputs a STRING that composes with
nothing.
**Observed**: brk2-24 — the 2B FABRICATED a time window (2000–2000) out of nothing to force
the question into COMPARE shape; a fabricated-parameter failure mode worth naming.
**Proposal**: `ARGMAX/ARGMIN {source: Series, over: value|delta} -> Scalar(year)`; defer
co-movement (correlation) — it may be synthesis-layer, not algebra.

## 2026-07-13 · Row-level ordering: nearest-k over records (brk2-30, 31)

**Questions**: "WHICH bus stop is closest to the station", "the five northernmost tram stops".
**Why**: RELATE distance already computes per-row `dist_km`, then the value is unreachable —
RANK ranks subtree items (places), never rows; no row-level order/limit.
**Observed**: the 2B answers the citywide COUNT instead of the nearest instance.
**Proposal**: either `RANK.over_rows: true` (rank rows of a single Records input by an
attribute) or a `LIMIT/ORDER` pair on Records. The executor already has every number needed.

## 2026-07-13 · Units, scalar arithmetic and grain co-scoping (brk2-19, 20, 32) + AMENDMENT to the Round-1 COMPARE-orientation proposal

**Evidence**: "bus stops per 1000 residents in Winnipeg" compiles to COMPARE(ratio, count,
population) and EXECUTES — with CANADA's population (41.65M) as a silent denominator, because
the region resolver honestly falls back city→country for country-grain indicators. Chicago
ridership "per resident" divides by the population of the UNITED STATES. Both are fluent,
green-scoring, and wrong at the grain level; and the x1000 / percent-change renderings are
affine transforms the algebra cannot state (brk2-32: how:ratio is the correct tree, the
"%" is rendering debt).
**Interim executor measures (implemented, provenance-stamped, this round)**: (1) typed values
now carry a `grain` tag and COMPARE stamps `[GRAIN MISMATCH: left=city-bbox, right=country]`
into the note when operands are not co-scoped — the answer surface must disclose it;
(2) **orientation amendment**: the Round-1 later-minus-earlier rule now fires ONLY when both
operands resolved to the SAME entity — the evidence run showed it silently inverting a
cross-entity per-capita ratio (air passengers / population → "people per passenger") because
population's series simply ends later. The spec rule should read: "canonical orientation
later-minus-earlier applies to same-quantity, time-anchored operands only."
**Proposal**: unit/grain metadata on typed values as SPEC (not just executor courtesy), plus
a scalar affine node or synthesis-layer unit rendering rules. City-grain denominators also
need a demographics source family — a connector census item, tracked separately.
