# Round 2 epoch 011 development absorption — H14 through H16

## Why

Epoch 010 ended with untouched strict scores of H14 23/40, H15 37/40, and H16 22/40. The epoch
was invalid and the banks were retained unchanged so their failures could become development
evidence. This loop classified every mismatch before changing the compiler.

## Classification and judge decisions

All 38 mismatches were admissible parser/compiler discoveries; no gold was excluded. H14 exposed
lost/swapped spatial operands, nested relation and relation-arithmetic collapse, clause-specific
threshold loss, vague facility holes, and city-country rank splitting. H15 exposed rank-direction
text leaking into country names. H16 exposed unknown `elsewhere` transfer targets, purpose clauses
overriding the requested measure, existential presence loss, and abstract work/livelihood rates
being treated as concrete indicators.

GPT-5.5-high-fast performed a read-only independent clustering pass. The main judge checked every
row against the question, gold IR, execution class, and frozen v2.1 semantics. Its advisory gold
concerns did not invalidate any of the 38 failed rows: cautious holes remain correct for unspecified
workplaces/proxies, and `presence(SELECT ?type)` preserves the explicitly requested yes/no form.

Repairs were mechanical and general: plural-aware entity restoration; spatially scoped `market`
recognition without reviving the `job market` routing bug; rank-list cleanup; typed unknown transfer
targets; purpose-preamble handling; total-vs-related-subset arithmetic; chained within/beyond
construction with per-clause distances; answer-form preservation; and abstract-rate holes.

## Result

Disclosed development reruns reached strict canonical H14 40/40, H15 40/40, and H16 40/40, with
the expected execution classes. The original holdout files and epoch-010 traces remain immutable.
Development copies have mechanically regenerated `gold_shape` metadata because the generated
holdouts used a stale shape representation; canonical semantic audit, not that stale coarse field,
is the admission authority.

The three 40-row banks now join the development wall. They do not count as untouched saturation
evidence. After the complete wall passes, epoch 011 will freeze and the three-bank sequence restarts
with newly generated questions.

## Full-wall certification and rejected attempts

The active wall is now 847 questions across 19 banks. Certification was intentionally layered and
four candidate wall runs were recorded rather than overwriting inconvenient evidence:

1. `epoch011-guard-*` / v1 scored almost perfectly in the coarse harness, but strict audit exposed
   three real old-bank denotation errors: an explicit coworking entity erased by a vague purpose
   preamble, a repeated market anchor mis-bound across comparison clauses, and a named transfer
   donor lost when the target was deictic. The wall was rejected.
2. v2 closed those exact rows, but independent GPT-5.5 review showed the facility repair was global
   rather than per leaf and donor recovery depended on narrow purpose words. The wall was rejected
   before freeze even though its observed rows passed.
3. v3 added generalized adversarial regressions, then the full wall found six H16 `elsewhere`
   transfers retaining the donor as target. The wall was rejected.
4. v4 passed all six deterministic regressions, ordinary harness 847/847, and canonical audit on
   every eligible row. It is the certified epoch-011 wall.

Strict canonical totals are 845/847 over all historical rows and 845/845 over eligible rows. The
only two mismatches are the already declared `gen-live-04` and `gen-live-14` legacy gold defects:
the former omits the current existential-presence answer form and uses legacy relation orientation;
the latter applies record aggregation to a connector Series. The compiler was not regressed toward
either bad gold. Dialogue guards also passed 5/5 for both model and mechanical binding.

`coverage/epoch-011-certification.json` is the machine-readable certificate. This closure is not a
saturation pass: H14-H16 were disclosed and absorbed, so epoch 011 contributes zero untouched
banks. The required three consecutive cross-family untouched banks begin only after the epoch-011
freeze, and any subsequent compiler/prompt/scorer/connector change invalidates that sequence.
