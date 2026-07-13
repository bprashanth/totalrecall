# Round 2 — strategy for defensible livelihoods saturation

## Correction to the Round 1 strategy

Round 1 optimized for the replication contract: a small seed, two generated banks, full regression,
frontier parity, and clean corpus artifacts. That proved the harness could close a bounded sector
suite. It did not prove broad solver generalization. In Round 2, **regression closure is a milestone;
saturation is a discovery-rate claim over untouched distributions**.

## What “saturation” will mean

Round 2 may claim operational saturation only when all of these hold:

1. **Data breadth:** at least four independently verified source families where feasible, spanning
   at least three geographic/temporal grains and explicitly distinguishing observed administrative,
   modeled, and proxy evidence. Every adopted code/table/tag must return real rows for multiple
   test places; sparse or bounded coverage is documented and scored honestly.
2. **Capability breadth:** at least 250 active single-turn questions across a published matrix of
   ordinary, indirect, compositional, adversarial, ambiguity, source-gap, and algebra-breaker
   families. Question count alone is not evidence; matrix cells and semantic diversity are.
3. **Breaker pressure:** at least 50 deliberate probes targeting likely missing semantics such as
   FILTER, GROUP/partition, UNION, set intersection, attribute predicates, unit-safe arithmetic,
   rate denominators, quantiles/distributions, temporal alignment, subgroups, uncertainty,
   conflicting sources, and multi-output requests. Inexpressible cases become proposals, never
   silently weakened golds.
4. **Training/test separation:** development banks may drive fixes. Once the prompt, connectors,
   executor, scorer, and repair stack freeze, run at least three consecutive untouched holdouts of
   at least 40 questions each. Holdout questions and golds are generated after the freeze and may
   not cause a fix without invalidating the sequence and starting a new freeze epoch.
5. **Independent generation:** holdouts vary generator prompt/register and, where quota permits,
   gold author or independent judge. The generator never sees parser outputs, repairs, or failure
   traces. Source-compatible and source-agnostic breaker generation are kept separate.
6. **Discovery plateau:** across the three frozen holdouts, no new uncharacterized failure class;
   fewer than one new issue per 50 questions; stable layer scores; and no manual answer-surface,
   provenance, completeness, or corpus-integrity violation. A known, repeated residue may remain
   only if classified and evidence-backed.
7. **Full guards:** every development fix reruns all active development banks. Every freeze epoch
   records exact code/prompt checksums. Final corpora contain development rows only unless a blind
   holdout is explicitly released after evaluation.

This is still empirical saturation, not a mathematical proof. The report must state the tested
distribution and residual blind spots.

## Round 2 workstreams

### A. Source and evidence expansion

- census official keyless labor/livelihood sources beyond OSM and World Bank;
- prefer complementary grains (subnational, demographic/industry/occupation slice, earnings or
  hours, administrative listings) rather than aliases of the same country series;
- test completeness, pagination/caps, units, revisions, missingness, and upstream modeling status;
- add connectors only through the existing SELECT contract and deterministic routing.

### B. Coverage matrix

Track each question by source, grain, entity family, time form, question type, op skeleton, relation
polarity, thresholds, holes, expected outcome, evidence label, and adversarial capability family.
Empty matrix cells drive generation; raw score does not.

### C. Algebra-breaker program

Maintain two streams:

- **admissible stress tests** that should compile under frozen v2.1;
- **expressiveness probes** intentionally allowed to fail admission and accumulate in breakers.

For every breaker, judge whether it is a connector gap, parser/compiler issue, executor semantics,
scoring defect, dialogue-layer split, or genuine algebra proposal. Never make the gold smaller than
the user's question merely to obtain execution.

### D. Baselines and evidence quality

Use the harness A0/A1/A2 arms on representative strata: no-tools, freeform connectors, and algebra.
Measure factuality, hallucination, honest refusal, latency, and source/evidence labeling—not only
tree shape. Manually audit every sub-perfect row and a stratified sample of green rows.

### E. Freeze epochs and stopping

Development proceeds in named epochs. A freeze checkpoint records checksums for parser, schema,
executor, connectors, scorer, synthesis, and active development banks. Any subsequent fix ends the
epoch. Only three consecutive untouched holdouts with a flat discovery curve permit the Round 2
saturation statement.

## Round 2 deliverables

- expanded source census and connector tests;
- machine-readable coverage matrix and discovery curve;
- development, breaker, and blind-holdout banks with provenance;
- per-epoch chronology and checksums;
- A0/A1/A2 comparison on representative strata;
- evidence-backed spec proposals reconciled against Round 1;
- clean corpus with explicit development/holdout policy;
- appended Round 2 section in `REPORT.md` stating the strongest claim the evidence permits.
