# IR spec v2.4.0-draft — conditional BUFFER + FILTER parser-surface bundle

This is an unreleased delta over [ir-spec.md](ir-spec.md), which remains the canonical released
v2.3.0 specification. The draft is enabled only when a caller explicitly selects algebra profile
`v2.4.0-draft`. It must not appear in `framework-manifest.json.released_proposals` until every
promotion condition in `governance/decisions/20260718-ALG-015-BUFFER.md` passes.

This draft implements the two accepted-conditional parser-visible contracts coordinated for the
v2.4 bundle: ALG-015 BUFFER and ALG-002 FILTER. Reference connectors declare typed row fields;
release still requires a model trained on this complete surface and a green parser conformance
wall. ALG-003 GROUP remains outside this document pending its keyed-result RFC.

## BUFFER support transformation

```text
BUFFER(source: REGION, radius_km: positive finite number) -> REGION
```

JSON shape:

```json
{
  "op": "BUFFER",
  "source": {"op": "REGION", "place": "Erode town"},
  "radius_km": 10.0
}
```

`BUFFER` constructs search/analysis support. It does not select records and it does not specify a
downstream relation's pairwise distance. `SELECT.region` and `ESTIMATE.target` may consume REGION
or BUFFER support. A BUFFER source must itself produce REGION support.

An unknown radius is represented as `"?radius_km"`; the tree validates as unbound and cannot
execute. Zero, negative, boolean, NaN, and infinite radii are invalid.

## Canonical form

Concrete nested radii add:

```text
BUFFER(BUFFER(R, a), b) ≡ BUFFER(R, a+b)
```

Identical written REGION/BUFFER values canonicalize to the same support value. Canonicalization
never copies one operand's support onto another. A compiler must explicitly write a common support
under every operand that the question places in that support; intentionally different supports
remain different.

## Reference geometry and provenance

The reference executor uses a latitude-adjusted bbox expansion, not exact polygon buffering. Every
such result and execution event carries:

```json
{
  "method": "bbox-approx",
  "approximate": true,
  "support_type": "analysis-search-bbox"
}
```

It also preserves the source region, radius, and resulting bbox. Answer synthesis must call the
support approximate. It must not call it an exact radius polygon, surveyed boundary, property, or
complete survey area. Buffers that cross a dateline/polar boundary fail closed until exact geometry
semantics are governed.

## Version boundary

- Default kit APIs remain v2.3.0 and reject BUFFER.
- `validate`, `canonicalize`, parser `build_messages`/`parse`, and executor `execute` accept the
  explicit `algebra_version="v2.4.0-draft"` profile.
- Existing v2.3 trees retain their denotation under both profiles.
- Promotion requires the neutral conformance corpus, parser evidence, full regression wall, and a
  trained model bundle carrying the released v2.4.0 algebra profile.

## FILTER record refinement

```text
FILTER(source: Records, where: Predicate[1..]) -> Records
Predicate = {field: declared column, cmp: eq|ne|lt|le|gt|ge|contains,
             value: JSON literal or typed hole}
```

JSON shape:

```json
{
  "op": "FILTER",
  "source": {
    "op": "SELECT",
    "entity": "clinic",
    "region": {"op": "REGION", "place": "Erode town"},
    "time": null
  },
  "where": [
    {"field": "name", "cmp": "contains", "value": "health"},
    {"field": "lat", "cmp": "ge", "value": 11.3}
  ]
}
```

`where` is conjunctive (AND) only. FILTER is refinement over returned record columns; it does not
replace SELECT's entity, region, or time slots. Predicate values are literals or typed holes,
never subtrees. Disjunction, regex/fuzzy matching, cross-field expressions, aggregate/HAVING
predicates, and nested predicate languages are not part of v2.4.

### Connector field declarations

Every Records value consumed by FILTER must carry `fields`, a mapping from filterable row-column
name to its declared type. The reference vocabulary includes `number`, `identifier`, `string`,
`category`, `boolean`, and period types, optionally suffixed with `|null`. Unknown fields fail
closed as `DataRequest(reason="unknown_filter_field")` naming the declared alternatives. A
missing declaration fails closed as `filter_schema_missing`; the executor never infers a schema
from incidental keys in returned rows.

`eq` and `ne` apply to compatible declared literals. `lt|le|gt|ge` require number or declared
period fields. `contains` is case-insensitive and requires string/category/period text. An
incompatible predicate literal fails closed as `filter_predicate_type`. Connector rows violating
their own declaration fail closed as `filter_source_type_error`.

### Empty, null, label, and provenance semantics

- FILTER over a non-Records value is a validation/type error.
- A predicate over a null or missing row value excludes that row. Each execution stamps
  `rows_in`, `rows_out`, and unique-row `null_excluded` counts in provenance.
- Empty FILTER output over non-empty source Records is a legitimate negative Answer, not a data
  gap. Empty leaf SELECT behavior remains unchanged.
- FILTER passes through its source evidence label and semantic metadata unchanged.

### Canonical form

```text
FILTER(FILTER(x, P), Q) ≡ FILTER(x, P ∧ Q)
```

Nested predicates merge into one `where` list and sort by canonical JSON representation, making
conjunct order insignificant for equality, scoring, and caching. A hole in either `field` or
`value` makes the complete tree unbound under the existing recursive-hole rule.

## Bundle boundary

- Default kit APIs remain v2.3.0 and reject both BUFFER and FILTER.
- The explicit `v2.4.0-draft` profile admits both contracts together; there is no BUFFER-only or
  FILTER-only released dialect.
- GROUP is not implied by FILTER and remains `rfc-required` until its keyed-result representation
  and downstream matrix are accepted.
