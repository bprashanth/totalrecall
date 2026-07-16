# Fable review — typed data composition contracts (ALG-002/003/005/007/008)

- Reviewer: Fable (supervisor role), 2026-07-16
- Packet: `governance/review-packet-algebra-contracts.md` (reviewed in isolation; no experiment
  directories or discovery provenance inspected)
- Reviewed against: released IR spec **v2.2.1** (7 kernel ops + REGION, typed holes, computed
  evidence labels, DataRequest as first-class return, canonical-form rules, per-op empty semantics)
- Standing criteria applied: (a) the kernel stays small — a new parser-visible op must buy
  expressiveness no composition can, because every op is surface a 2B-class compiler must learn and
  every sector must re-pin; (b) honesty machinery lives in code (executor/validator), not in model
  behavior; (c) any contract must state what happens on failure, and the failure must be a typed
  DataRequest or typed error, never a silent coercion.

---

## ALG-002 — typed FILTER

**Disposition: accept-partial.**

**Accepted semantic core.** A unary Records→Records node:

```json
{ "op": "FILTER", "source": <Records-producing node>,
  "where": [ { "field": "<connector-declared column>", "cmp": "eq|ne|lt|le|gt|ge|contains",
               "value": <JSON literal or hole> } ] }
```

- `where` is a conjunctive list (AND only). `value` is a **literal or a typed hole — never a
  subtree**. This is the load-bearing restriction: it keeps FILTER a predicate, not an expression
  language.
- Answer to packet Q1: FILTER is a core algebra operation, not a connector capability. SELECT is
  already a filter over a connector's universe (entity/region/time are its only predicates); what is
  missing is refinement over the *returned columns*, and that is connector-independent by
  construction if `field` is typed against the connector's declared column schema. Pushdown into a
  connector query is an executor optimization with an identical observable contract — permitted,
  never required.
- Answer to Q3: no scoping rule is needed; typing does it. FILTER's input and output are Records;
  AGGREGATE consumes Records and produces Field/Series. Therefore `AGGREGATE(FILTER(...))` is
  well-typed and `FILTER(AGGREGATE(...))` is a type error caught by schema validation. "Filtering
  before aggregation" is a theorem of the type system, not a convention.
- Unknown-field behavior: **fail closed at execution into a DataRequest naming the field and the
  columns the connector does declare.** This extends the existing leaf-gap semantics naturally: an
  unknown column is a data gap, not an empty answer, and never predicate-true.
- Null/missing behavior: a predicate over a missing value **excludes the row and increments a
  `null_excluded` count stamped in provenance** alongside `rows_in`/`rows_out`. Exclusion is
  allowed; unaccounted exclusion is not.

**Excluded / deferred surface.** Disjunction (`OR`) and predicate nesting; negation as a predicate
combinator (`ne` on a single field is enough for v1 — the algebra's precedent is De Morgan by
op-chaining, and chained FILTERs give AND for free); regex/fuzzy matching; cross-field predicates
("field A > field B"); aggregate-threshold predicates ("wards with more than 100 complaints") —
that is HAVING, requires ALG-003's keyed output, and must arrive as a composition
(`FILTER` is not the vehicle), so it is deferred jointly.

**Required invariants and conformance tests.**
1. Empty-result semantics mirror RELATE, and this must be written into the spec table:
   `FILTER → ∅` over non-empty input is a **true negative** (a legitimate Answer); a gap is only a
   gap at the leaf. Test: filter that matches nothing yields Answer, not DataRequest.
2. Canonical form: `FILTER(FILTER(x, P), Q) ≡ FILTER(x, P ∧ Q)` and conjunct order is
   insignificant. Scorer/equality/caching compare the merged, sorted form. Test: both spellings
   score identical skeletons.
3. Unknown field → DataRequest carrying the declared-column list. Test per connector class.
4. `null_excluded`, `rows_in`, `rows_out` present in provenance whenever a FILTER executes.
5. Type error on FILTER over Field/Series/Scalar/Ranking, caught at validation.
6. Holes in `field` or `value` make the tree unbound (recursive hole rule already covers this;
   test it anyway).
7. Evidence-label passthrough: FILTER never changes the label of its source rows.

**Dependencies and versioning.** No dependency on the other four. New parser-visible surface →
**minor IR bump (v2.4.0 track, see cross-proposal §4) with skeleton-scorer awareness**; sectors
adopt by re-pinning; the compile corpus must gain FILTER rows before any small-model sector depends
on it (the model carries the algebra version).

**Strongest counterexample.** "Wards where garbage complaints exceeded sewage complaints" — a
row-wise cross-measure comparison. The proposed contract cannot express it, and the temptation will
be to grow `value` into a subtree or add computed fields, at which point FILTER becomes a query
language a 2B cannot reliably emit. The contract survives the counterexample only by declaring it
out of scope: such questions compile through GROUP/COMPARE composition or return DataRequest. If
reviewers cannot hold that line, FILTER should not ship.

---

## ALG-003 — partitioned GROUP

**Disposition: accept-partial — as a typed extension of AGGREGATE's `by`, not a new op.**

**Accepted semantic core.** Generalize `AGGREGATE.by` from the enum `space | time` to also admit
`{ "field": "<connector-declared column>" }`, producing the **existing keyed Field type** (ordered
label→value pairs), where labels are the key column's values:

```json
{ "op": "AGGREGATE", "by": { "field": "ward" }, "metric": "count", "source": <Records> }
```

- Answer to packet Q1: neither a new keyed-result type nor Records-with-key-columns. `AGGREGATE
  by:space` **already is** a single-key GROUP whose key is the place column and whose output is a
  keyed Field; the honest generalization is to let the key be any declared column. This keeps the
  skeleton unchanged (still AGGREGATE — cross-sector comparability and scorer untouched), adds zero
  new ops to the parser surface, and composes for free everywhere Field already composes (COMPARE,
  RANK, rendering).
- Answer to Q2: a record with a missing key value goes into an explicit **`(unknown)` bucket**,
  never silently dropped, with its count in provenance. Empty partitions are **absent** unless the
  connector declares the key's domain (e.g. an official ward list), in which case zero-fill is
  permitted and the zero-filled keys are stamped as `domain_filled` in provenance. Zero-fill
  without a declared domain is fabrication and is prohibited.
- Answer to Q3: v1 guarantees are — deterministic ordering (descending by value, ties by label;
  renderers may re-sort but the canonical form is fixed for equality/caching), single key only,
  cardinality reported in provenance, and the renderer rule as proposed: a keyed result must never
  flatten to an unlabeled list or scalar (already true for `by:space`; now stated generally).

**Excluded / deferred surface.** Multi-key and nested grouping (see counterexample); `by:{field}`
combined with time bucketing in one node; per-partition metrics beyond the existing metric
vocabulary (`count | density | mean | presence`); ordering/limit parameters (RANK already owns
"top-k of a keyed thing" — `RANK` over a keyed Field's entries, or `k` on RANK, covers it without
new surface).

**Required invariants and conformance tests.**
1. Identity with the released op: on a Records set whose place column is the key,
   `AGGREGATE(by:{field:"<place column>"})` ≡ `AGGREGATE(by:"space")` canonically. This is the
   compatibility anchor; test it per connector.
2. Unknown key column → DataRequest naming declared columns (same rule as FILTER).
3. `(unknown)` bucket accounting present whenever ≥1 record lacked the key.
4. Zero-fill only with declared domain, stamped; test both branches.
5. Keyed Field feeds RANK and COMPARE unchanged; test `RANK(items from grouped Field)` and
   `COMPARE` of two grouped Fields on the same key domain.
6. Evidence label: computed exactly as for existing AGGREGATE (no change to the taint algebra).

**Dependencies and versioning.** Independent of ALG-002 (they compose but neither requires the
other). Parser-visible surface change (a new `by` form) → same minor-bump track as ALG-002; ship
them together as one corpus/retrain event to avoid two successive parser-surface bumps.

**Strongest counterexample.** "Monthly complaint trend per ward" — two keys (time × ward). The
single-key contract cannot express it; nesting `by:{field}` inside/around `by:time` either invents
a table type (new result algebra, new renderer, new scorer) or produces Fields-of-Series that
nothing downstream consumes. This is the real design cliff and exactly why multi-key is deferred
pending evidence that (a) the question class occurs and (b) a small model can compile whatever
shape is chosen.

---

## ALG-005 — unit-tagged derived arithmetic

**Disposition: accept-partial — as a result-metadata + executor-conformance contract; no new
parser surface, no new ops.**

**Accepted semantic core.** Every Field/Series/Scalar carries typed metadata
`{ measure, unit, grain, lineage }` populated from connector declarations at the leaves and
propagated by the executor; the arithmetic ops the algebra already has (`COMPARE how:difference`,
`how:ratio`, RANK's scalarization) enforce compatibility:

- **`difference` requires identical `(measure, unit, grain)`** on both operands; mismatch fails
  closed into a typed error surfaced as clarification/DataRequest — never a bare scalar.
- **`ratio` permits heterogeneous units and *forms* the derived unit** (`unit_left / unit_right`),
  recording numerator and denominator lineage in the result. Ratio is how per-capita and density
  questions are legitimately expressed; blocking cross-unit ratio would kill the intent the
  operation exists for. What ratio must NOT permit silently is **grain mismatch**: a ward-level
  numerator over a national denominator fails closed unless the denominator is explicitly declared
  a proxy by the connector/resolver, in which case it executes and the result's evidence label
  taints to `proxy` with the substitution named in provenance.
- **RANK scalarization requires all items to agree on `(measure, unit)`** — this closes the
  already-documented hole where a difference was ranked against a count ("type-meaningless but it
  executes").
- Answer to packet Q2: enforcement is **mandatory at execution time**, where units are first
  knowable (they come from connector metadata the parser never sees). Validation-time checking is
  vacuous today and should not be specified; if statically-visible unit annotations ever enter the
  IR, revisit.
- Answer to Q3 (required result metadata): `unit` (string, connector vocabulary), `measure`
  (stable identifier), `grain` (spatial level + population/denominator base), `lineage` for any
  ratio (numerator and denominator's measure+unit+grain), and vintage passthrough where the
  connector declares it (interface shared with ALG-007). Scale/percent normalization: `percent` vs
  `fraction` is a unit distinction, not a rendering nicety — normalize in code the way relation
  synonyms are normalized.

**Excluded / deferred surface.** Any new arithmetic forms (sums of series, general expressions,
unit conversion tables); packet Q1's answer is that the *first governed surface is exactly the
arithmetic v2.2.1 already performs* — difference, ratio, trend_direction (which, being unary,
gets no compatibility check beyond its own series' internal consistency), and RANK scalarization.
Automatic unit conversion (km² vs hectares) is deferred: v1 says incompatible-and-unconverted
fails closed; a conversion table is a later, evidence-driven addition.

**Required invariants and conformance tests.**
1. Difference over mismatched units → typed failure, no numeric output; test with a
   modeled-indicator vs count pair.
2. Ratio forms derived unit and full lineage; test per-capita style composition.
3. Grain mismatch: blocked by default; executes-with-proxy-taint only when declared; both
   branches tested (this is the regression test for the known city-rate/national-denominator
   failure class).
4. RANK over heterogeneous measures → typed failure.
5. Metadata survives the canonical-form identities (identity-AGGREGATE passthrough must not strip
   tags).
6. Backward compatibility: connectors that declare no units yield `unit:"unknown"`, which is
   **compatible only with itself** and never blocks single-source trees — so existing sectors keep
   executing unchanged while gaining tags incrementally.

**Dependencies and versioning.** No parser change → this is the cheapest honest win on the table:
**executor + result schema only, v2.3.0 track**, old trees remain valid, sectors gain protection
without retraining anything. Depends on connectors declaring units/grain (WB-class indicators
already can; count-based connectors declare `count`). Pairs naturally with ALG-003's keyed
outputs and ALG-007's vintage field but requires neither.

**Strongest counterexample.** A composite index (unitless, "score") differenced against another
unitless score from a different methodology: identical `(measure:"index", unit:"1", grain)` tags
pass every check, yet the subtraction is meaningless. Unit typing catches unit clashes, not
semantic incommensurability — the contract must claim only what it enforces, and `measure`
identifiers must be granular enough (source-scoped, not just "index") to make the check
non-vacuous. If measure identity is left loose, the tags become theater.

---

## ALG-007 — explicit temporal alignment and vintage

**Disposition: accept-partial — as a mandatory contract on multi-input temporal operations, not a
new ALIGN op; defaults narrower than proposed.**

**Accepted semantic core.** Answer to packet Q1: a contract, not an op. An explicit ALIGN node is
parser surface a small model would have to learn to emit in exactly the cases it least understands;
the algebra's precedent (operand orientation, v2.1) is that deterministic temporal hygiene is an
executor canonical-form rule stamped in provenance. Accepted rules, applying to COMPARE over two
Series and any future multi-series op:

1. **Join policy: exact-period inner join** on period identity. **No interpolation, no
   nearest-period substitution, ever** — accepted as stated, this is the contract's core and it is
   right.
2. **Dropped periods produce a certificate**: provenance lists the overlap window used, the
   periods discarded from each side, and counts (answers Q3). Renderers must surface the window
   ("2015–2021 common coverage"), consistent with the existing rule that the answer states its
   window.
3. **Zero overlap fails closed into a DataRequest** naming each side's available window — an
   honest gap, not an error string.
4. **Mixed frequency**: v1 permits alignment only when the finer series is **coarsenable by a
   declared semantics** — measures must be connector-declared as flow (sum-coarsenable) or stock
   (mean/last-coarsenable); undeclared → fail closed. This narrows the packet's "coarser common
   frequency" default, because unrestricted coarsening is resampling under another name and would
   contradict rule 1 in spirit.
5. **Vintage**: passthrough only in v1 — if a connector declares a source vintage it is stamped
   into the result and named when two inputs' vintages differ; no blocking semantics yet
   (deferred until a sector shows a vintage-mix producing a wrong answer, at which point a
   compatibility rule can be evidenced rather than guessed).
6. Answer to Q2 (safe defaults): only these — inner join, declared-coarsening, total-coverage
   window when time is unspecified (existing rule), later-minus-earlier orientation (existing
   v2.1 rule, unchanged and now subsumed under this contract's umbrella).

**Excluded / deferred surface.** Lag/lead operators; calendar-system conversion; seasonal
adjustment; any interpolation whatsoever; vintage *selection* ("as known at the time");
alignment of more than two series (arrives automatically if a future op needs it, under the same
contract).

**Required invariants and conformance tests.**
1. Overlap certificate present whenever any period was dropped; absent when none was.
2. Zero-overlap → DataRequest with both windows named.
3. No output period exists that was absent from both inputs (no synthetic periods) — property
   test, not example test.
4. Flow vs stock coarsening honored; undeclared measure at mixed frequency → fail closed.
5. Orientation rule regression: same-entity time-anchored COMPARE still orients
   later-minus-earlier with the reorientation stamped.
6. Interaction with ALG-005: aligned results retain unit/grain tags; a dropped-period certificate
   never alters tags.

**Dependencies and versioning.** No parser surface → **v2.3.0 track together with ALG-005** (they
share the result-metadata plumbing and are one executor-conformance release). Requires connectors
to declare frequency and flow/stock class for mixed-frequency support; without declarations the
contract still holds (same-frequency joins + fail-closed), so partial connector adoption is safe.

**Strongest counterexample.** Pre/post questions — "did complaints rise after the 2021 policy?"
compiled as two windowed AGGREGATEs of *different lengths* fed to COMPARE. Period-identity inner
join is the wrong frame there (nothing aligns; the windows are intentionally different), and a
naive reading of this contract would fail-closed a perfectly honest tree. The contract must scope
itself to **period-indexed Series operands** and explicitly exempt window-scalar comparisons
(Scalar operands carry their window in metadata; no alignment applies). Without that scoping
sentence, the contract breaks the CHANGE question class the algebra was born from.

---

## ALG-008 — epistemic CORROBORATE / VERIFY

**Disposition: defer.**

**Accepted semantic core.** None for release. Two ideas are worth preserving in the record: (a)
corroboration belongs to a **typed claim/evidence layer above the record algebra** (packet Q1 —
its operands are labeled claims with lineage, not Records; forcing it into the Records algebra
would misuse RELATE/union machinery whose label rule — weakest wins — is deliberately the
*opposite* of corroboration); (b) conflict and incomparability should eventually be **typed
result statuses** alongside Answer and DataRequest (packet Q3), not sentinel values inside rows.

**Why defer rather than accept-partial.** The operation's honesty depends entirely on an
**independence model that does not exist in the framework**: connectors do not declare lineage
ancestry, so the executor cannot distinguish two genuinely independent observations from two
downstream copies of the same upstream source (the ILO-modeled-statistics case documented in
v2.2's leaf-label adoption is precisely a shared-lineage trap — WB-served series that *look* like
a second source). Every other contract in this packet fails closed when its metadata is missing;
CORROBORATE with missing independence metadata would fail *open* — it would certify agreement it
cannot verify. An honesty operation that can silently certify false independence is a net
negative to exactly the property this algebra exists to protect. Minimum independence checks
(packet Q2) therefore *precede* the op: a connector-level lineage/ancestry declaration
(`derived_from`, methodology id) and a measure-compatibility check reusing ALG-005's
measure/unit/grain tags. Both are prerequisites, and the second is another reason ALG-005 ships
first.

**Evidence bar for revival.** A sector demonstrating (1) a question class where two
lineage-independent connectors cover the same measure and genuinely disagree; (2) that freeform
(non-algebra) models fabricate consensus on those questions; (3) a lineage declaration schema
adopted by at least two connectors; (4) any evidence a small model can compile the resulting
surface — or a decision that this layer is executor/synthesis-side only and never parser-visible,
which this reviewer suspects is the right destination.

**Dependencies and versioning.** Depends on ALG-005 metadata and on a connector-contract lineage
extension (itself a governance proposal). No version implication now.

**Strongest counterexample.** Two connectors serving unemployment for the same region: one raw
WB-served ILO modeled estimate, one national statistics office series — the ILO estimate is
itself calibrated on the NSO series. CORROBORATE reports independent agreement; the truth is one
source wearing two hats. The framework currently *refuses* this comparison honestly (union label:
weakest wins; no independence claim anywhere). Shipping the op without lineage metadata would
convert today's honest silence into tomorrow's confident false certification.

---

## Cross-proposal answers

1. **Dependencies.** ALG-002 and ALG-003 are mutually independent and neither is a prerequisite
   for 005 or 007 (which are executor/result-contracts). ALG-008 depends on ALG-005's
   measure/unit/grain tags plus a not-yet-proposed connector lineage declaration. HAVING-class
   questions need 002+003 jointly — deferred as a composition, not a contract.
2. **Independent release without silent coercion.** 005 and 007 (fail-closed by construction, no
   parser surface); 002 and 003 (typed, fail-closed, but parser-visible). 008 cannot ship without
   coercion risk today — its missing metadata fails open.
3. **Invariant placement.** Schema validation: op shapes, `where` literal-only, `by:{field}` form,
   enum/synonym normalization, recursive holes. Executor conformance: type checks, fail-closed
   unit/grain/frequency rules, empty-semantics per op, provenance counts and certificates,
   canonical-form identities. Rendering: keyed results keep labels, answers name operands and
   windows, dropped-period and proxy substitutions surfaced in prose.
4. **Versioning.** Two releases, deliberately ordered:
   - **v2.3.0 — ALG-005 + ALG-007** (result metadata, executor conformance; zero parser surface;
     existing trees and existing tuned models remain fully valid; pure honesty hardening).
   - **v2.4.0 — ALG-002 + ALG-003** (parser surface: one new op + one new `by` form; skeleton
     scorer extended; compile corpus and tuned adapters must be refreshed **before** sectors
     depend on the surface — the model carries the algebra version, so sectors pin v2.4.0 only
     when a v2.4.0-trained model bundle exists).
   - ALG-008: no version; parked with a named evidence bar.
5. **Sound-but-underevidenced.** ALG-002's disjunction and ALG-003's multi-key are coherent but
   excluded pending question-class evidence; ALG-008 in its entirety; ALG-007's vintage
   *semantics* beyond passthrough. Per governance, this review is one of two independent reviews;
   nothing here authorizes implementation, promotion, or release.
