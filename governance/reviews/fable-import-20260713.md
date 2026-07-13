# Fable review import — 2026-07-13

This is an evidence-preserving import from the Fable-owned orchestration repository at
`../heartwood/docs/architecture/memory/`. It is not represented as a fresh model response: a direct
Cursor/Fable call was attempted on 2026-07-13 and refused until the account acknowledges Fable 5's
data-retention policy.

Authoritative source artifacts inspected:

- `CLAUDE.md`: binds semantic changes to the dual-review governance gate.
- `chronology/20260713_lora_spec22_round2.md`: explicitly adopts the livelihoods discovery-rate
  saturation protocol and records the v2.2 union/evidence-label adoptions.
- `benchmarks/spec-proposals.md`: records Fable's reconciled and queued decisions.

| ID | Imported Fable disposition | Evidence |
|---|---|---|
| EVD-001 | accept; implemented in v2.2 | Connector-leaf labels adopted and live-verified. |
| ALG-001 | accept-partial; implemented in v2.2 | Positive entity union adopted as list-valued SELECT.entity; no general set algebra. |
| ALG-002 | defer for v2.3 design | FILTER is in the explicit reconciliation queue with two-sector evidence. |
| ALG-003 | defer for v2.3 design | GROUP/partition is in the explicit reconciliation queue. |
| ALG-004 | not reviewed beyond positive union | No Fable acceptance of general identity/intersection/difference semantics. |
| ALG-005 | defer for v2.3 design | Units and grain co-scoping are queued; the transport grain defect is marked urgent. |
| ALG-006 | defer for v2.3 design | Quantiles are in the explicit reconciliation queue. |
| ALG-007 | defer for v2.3 design | Temporal argmax is queued; the broader ALIGN proposal has not been accepted. |
| ALG-008 | not yet reviewed | No acceptance of a concrete VERIFY claim op. |
| PLN-001 | accept-partial; no algebra op | Mandatory dialogue-layer clause splitting was decided; BUNDLE/QUERYSET was rejected for now. |
| ASK-001 | not yet reviewed | No durable Fable decision found for the causal typed-ask contract. |
| SAT-001 | accept | Fable chronology says the livelihoods protocol was adopted and transport Round 2 launched under it. |

Two additional Fable-owned urgent items are promoted into the registry as BUG-001 and BUG-002.
