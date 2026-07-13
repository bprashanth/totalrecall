# IR spec v0 — the JSON expression tree a question compiles to

This is the concrete, machine-checkable form of the algebra in `README.md`. It is **v0**: the whole point
of the harness is to discover where it breaks and revise it. Every revision bumps the version and is
recorded in `../runs/` and `FINDINGS.md`.

## Shape

An IR is a single JSON object = an **expression tree**. Every node has an `op`. Kernel ops take other nodes
as inputs; leaves carry literals or **holes**.

```json
{ "op": "AGGREGATE", "by": "time", "metric": "count",
  "source": { "op": "SELECT", "entity": "clinic", "region": {"op":"REGION","place":"Kisumu, Kenya"},
              "time": {"start":"2015","end":"2023"} } }
```

A **hole** is any string beginning with `?`, e.g. `"?entity_subtype"`, `"?time_window"`. A tree with any
hole is **unbound** and must not execute — the hole is the clarifying question (Layer 3 of the algebra).

## Kernel ops (Layer 1)

| op | required fields | input types | output |
|---|---|---|---|
| `SELECT` | `entity`, `region`, `time` | — (leaf-ish; region may be a REGION node) | Records |
| `ANNOTATE` | `source`, `layer` | source: Records | Records (+column) |
| `RELATE` | `left`, `right`, `relation` | left,right: Records | Records (+column) |
| `AGGREGATE` | `source`, `by`, `metric` | source: Records | Field (`by:"space"`) or Series (`by:"time"`) |
| `COMPARE` | `left`, `how` (+`right` unless `how:trend_direction`) | left,right: Field/Series/Scalar | Scalar/Field/Series |
| `ESTIMATE` | `source`, `target`, `method` | source: Records | Field (**modelled**) |
| `RANK` | `items` (list of ≥2 nodes), `order` (`desc|asc`), optional `k` | items: anything scalarizable | Ranking (ordered `{label,value}` list) |

**Negation & thresholds (added tick-021, spec v1→v2).** The negation probe broke the algebra a second
time: "pharmacies with NO hospital within 1km" was inexpressible — the 2B produced the affirmative
RELATE (the exact-opposite answer set) and the frontier model either dropped the constraint or used a
count-arithmetic workaround (`total − within`) that cannot produce the record set. Fix: **`beyond`** as
a relation (the complement of `within`) plus optional **`threshold_km`** on RELATE (distances in
questions were previously ignored silently). Conjunctions chain: "near a park but not near a bank" =
`RELATE(beyond, RELATE(within, X, parks), banks)`. A **polarity lint** (negated question + `within`
tree → flip) guards the silent-opposite failure mechanically.

**RANK (added tick-008, spec v0→v1).** The first op the loop *discovered missing*: "which of A, B, C has
the most X" cannot be expressed with binary COMPARE — both a 2B and a frontier model degraded it by
silently dropping a place or nesting COMPAREs (comparing a *difference* to a *count*: type-meaningless but
it executes — see open question on unit tags). Rule: **two things = COMPARE; three or more = RANK.** Each
item is one subtree per thing ranked; the executor scalarizes items (implicit coercion), labels them by
their innermost REGION (or entity), sorts, and answers argmax/argmin/full order.

Leaf/support nodes:
- `REGION` — `{ "op":"REGION", "place":"<name>" }` resolve a place name to a boundary/bbox.
- Values are plain JSON (strings, numbers, `{start,end}` for time).

Field vocabularies:
- `relation` ∈ `distance | within | cooccur`
- `by` ∈ `space | time`
- `metric` ∈ `count | density | mean | presence`
- `how` ∈ `difference | ratio | trend_direction`
- `method` ∈ `interpolate | feature | envelope`

## Question-level → kernel compositions (Layer 1 mapping)

| question type | canonical tree |
|---|---|
| STATE ("what X is here") | `SELECT` (optionally `AGGREGATE by:space`) |
| RELATION ("X near Y") | `RELATE(SELECT x, SELECT y)` |
| CHANGE ("what changed t1→t2") | `COMPARE(AGGREGATE(SELECT@t1), AGGREGATE(SELECT@t2), how:difference)` |
| TREND ("rising or falling") | `COMPARE(AGGREGATE(SELECT, by:time), how:trend_direction)` |
| VALUE ("measurement at points") | `ANNOTATE(points, layer)` or `ESTIMATE` if the place is data-poor |
| TRANSFER (any of the above, records elsewhere) | wrap the source in `ESTIMATE` |

## Epistemic layer (Layer 2) — not ops, but rules on the tree

- **Evidence label** is *computed*, never written by the parser. Executor rule: a subtree containing an
  `ESTIMATE` is `modelled`; a `COMPARE`/`RELATE` mixing `observed` and `modelled` is `modelled`; everything
  else is `observed`. (`proxy` is set when a SELECT's entity resolves to a declared proxy — see resolver.)
- **Gate = admissibility on ESTIMATE.** `ESTIMATE` executes only if a gate certificate passes
  (similarity/coverage between `source` records and `target`). No pass → the evaluation returns a
  **DataRequest** instead of a Field.
- **Return type** of an evaluation is `Answer` **or** `PartialAnswer + DataRequest`. Unbound holes,
  failed gate, or an empty SELECT all yield a DataRequest naming exactly what's missing.
- **Empty-result semantics differ by op** (tick-003): `SELECT → ∅` is a **data gap** → DataRequest;
  `RELATE/COMPARE → ∅` over non-empty inputs is a **true negative** → a legitimate Answer ("none within
  1km"). Emptiness is only a gap at the *leaf*; higher up the tree it is information.
- **Enum fields filled from natural language get a synonym-normalization layer in code** (tick-003):
  e.g. `near|nearby|close to|adjacent → within`. The parser prompt advertises canonical terms only, but
  the schema canonicalizes rather than rejects; enumerating aliases in the vocab is whack-a-mole.
- **Trees normalize to a canonical form** (tick-005): the algebra has redundant denotations —
  `AGGREGATE(by:time, metric:mean)` over a series-producing SELECT is an identity, so
  `COMPARE(SELECT,SELECT)` ≡ `COMPARE(AGG(SELECT),AGG(SELECT))`. Consumers (scoring, tree-equality,
  caching) compare canonical forms, never raw trees. Executor treats identity-AGGREGATE as passthrough.
- **Hole detection is recursive over all leaves** (tick-004-ds): a hole nested inside a value dict
  (`time:{start:"?y"}`) makes the tree unbound exactly as a top-level hole does. A partially-bound tree
  must never execute.
- **Time is never a hole**: absent time = `null` = all available data. Asking "which years?" on a trend
  question is clarify-noise; the default is total coverage and the answer states its window.
- **Provenance = the tree itself** plus per-node row counts / sources stamped during execution.

## What the parser must produce

Strictly this JSON tree, nothing else. No prose. Holes for anything the question leaves genuinely
underspecified (which subtype, which time window) — but **do not** invent holes for things the question
fixes. Over-holing is a scored failure just like under-holing.

## Known-open questions (to resolve via the loop)
- Is `RELATE` one op or does `cooccur` deserve its own? (co-occurrence may need AGGREGATE semantics.)
- Does `ESTIMATE.method` belong in the tree or should the executor choose it from the gate result?
- Do we need a `FILTER`/`RANK` op, or are those AGGREGATE/COMPARE parameters?
- Behaviour/intent questions: represented as `SELECT` on a proxy entity + a forced DataRequest?
