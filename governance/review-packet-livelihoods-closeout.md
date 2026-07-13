# Fable review packet — livelihoods Round 2 closeout

## Decision to review

Livelihoods stops at a reproducible, empirically hardened epoch-022 development boundary without
claiming practical or hard saturation. Fable should review the accuracy of that claim and
independently disposition `ALG-013`, `ALG-014`, and `BNCH-004` as `accept`, `accept-partial`,
`defer`, or `reject`.

## Exact terminal state

- Frozen wall: 1,573/1,573 eligible ordinary and strict; 1,576/1,576 synthesis.
- Supporting gates: 175/175 regressions, 14/14 source probes, dialogue 5/5 in both modes.
- Freeze: epoch 022, 62 inputs, no checksum drift.
- Saturation: practical unproven; hard unproven; untouched counter zero.
- H30: 100 raw parser-blind rows, independently audited 57 accept / 28 repairable / 13 exclude /
  2 duplicate, never admitted and never shown to the solver.

## Requested proposal review

- `ALG-013`: explicit global `Field`-to-`Scalar` reduction rather than implicit scalarization.
- `ALG-014`: explicit question-warranted identity for rank candidates sharing place/entity.
- `BNCH-004`: separate immutable scored exams from retained expressiveness breakers during
  precontact admission.

## Required reading

1. `livelihoods_memory/LIVELIHOODS-CLOSEOUT.md`
2. `livelihoods_memory/coverage/epoch-022-certification.json`
3. `livelihoods_memory/coverage/h30-generator-prompt.md`
4. `livelihoods_memory/coverage/h30-author-report.md`
5. `livelihoods_memory/coverage/h30-precontact-independent-audit.md`
6. `livelihoods_memory/spec-proposals.md` — `ALG-013`, `ALG-014`, `BNCH-004`
7. `governance/review-packet-h29.md` — preceding `ALG-012` evidence
8. `governance/review-packet-sat004.md` — claim that was deliberately not made
9. `governance/proposals.json`

## Questions for Fable

1. Should global scalar reduction be one polymorphic reduction operation, explicit aggregate
   scope, or several typed operations?
2. Should rank identity be a label field, a typed candidate record, or derived canonical
   provenance—and how is invention prevented?
3. Should expressiveness breakers be mandatory output of every sector benchmark even when they are
   ineligible for saturation scoring?
4. Is “empirically hardened frozen development boundary” precise enough for cross-sector reporting,
   or should governance define a standard non-saturation maturity label?

No proposal changes bootstrap behavior merely because it is listed here. Promotion requires the
normal independent review, reconciliation, kit conformance, manifest, and validation gates.
