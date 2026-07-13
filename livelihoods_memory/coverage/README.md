# Round 2 coverage artifacts

`matrix.json` is regenerated from admitted question banks by:

```bash
python harness/coverage.py
```

Each row records the gold tree skeleton, operator multiplicity, inferred source and grain, entity
and region diversity, temporal form, relation polarity and threshold, aggregate/compare/estimate
mode, rank order and arity, holes, and an optional adversarial capability family. Explicit
`source_family`, `grain`, and `capability_family` question metadata override inference for new
connectors and breaker strata.

The matrix is a guard against fake breadth: paraphrases increase question count but do not create
new skeletons, sources, grains, or capability cells. Empty or singleton cells drive Round 2
generation. Frozen-epoch checksums include this artifact and its input banks.

`source-census.json` is a cache-backed/live integrity snapshot for new connector tables and
geographies. Regenerate it with `python3 harness/source_census.py`; every probe checks nonempty,
ordered, unique, numeric, bounded annual rows and retains unit, upstream table/source code,
observation flags, update timestamp, and connector selection policy in its note.

`semantic-audit-*.json` applies a stricter canonical IR comparison than the legacy op-multiset
score. It checks source-resolved entity identity, region, time, operand orientation, rank order/k,
threshold, annotation layer, and hole position while allowing only documented equivalences such as
mean-by-time over a source Series. Round 2 freeze and holdout claims require this audit to pass.
