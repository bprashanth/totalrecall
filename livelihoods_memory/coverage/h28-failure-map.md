# H28 immutable first-contact failure map

H28 produced 56 canonical mismatches. Read-only trace adjudication reduced them to five reusable
mechanisms rather than row-specific exceptions:

1. **RANK construction and closure (16):** missing `k`, ranged SELECTs substituted for endpoint
   COMPARE items, and related count/density candidates dropped or merged.
2. **Spatial relation scope and composition (15):** subject/anchor inversion, written-distance or
   polarity loss, answer heads replacing RELATE, and nested conjunction/co-occurrence deletion.
3. **Temporal operand binding (8):** explicit trend language lost to endpoint arithmetic, ratio
   changed to difference, subtraction order reversed, or qualifiers/times leaked between operands.
4. **ESTIMATE source composition and holes (9):** RELATE/ANNOTATE donor expressions collapsed to
   SELECT and unresolved entity/layer/anchor roles filled without warrant.
5. **Output/literal honesty (8):** record heads changed to aggregates, unsupported modifier spans
   truncated, anaphors invented, and a causal claim converted to plausible arithmetic.

The repair is compositional: candidate-local RANK closure; clause-local spatial and statistical
frames; typed ESTIMATE source preservation; and a final output/literal/hole contract. Applying
these deterministic passes to the immutable first-contact trees yields canonical equivalence on
100/100 rows offline. This is development evidence only and must still pass a complete parser run.

The 30 synthesis-audit failures were separately shown to share one scorer-contract defect. The
renderer faithfully says “temporarily unavailable” and “availability gap,” while its mechanical
`gap_stated` regex recognized neither phrase. Thirteen gold-equivalent parse controls proved the
problem independent of parsing. The scorer now recognizes its own renderer language, with a
regression assertion; immutable first-contact scores remain unchanged.
