# IR spec v2.4.0-draft — conditional parser-surface bundle

This is an unreleased delta over [ir-spec.md](ir-spec.md), which remains the canonical released
v2.3.0 specification. The draft is enabled only when a caller explicitly selects algebra profile
`v2.4.0-draft`. It must not appear in `framework-manifest.json.released_proposals` until every
promotion condition in `governance/decisions/20260718-ALG-015-BUFFER.md` passes.

The complete v2.4 parser/model bundle is also expected to include ALG-002 FILTER after its own
connector-field-schema condition is satisfied. This document specifies only the independently
implemented ALG-015 candidate.

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
