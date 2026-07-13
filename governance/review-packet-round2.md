# Round 2 framework review packet

## Requested review

Fable should independently review every ID in `proposals.json` and return one of `accept`,
`accept-partial`, `defer`, or `reject`, with a semantic rationale, dependencies, and the smallest
safe adoption. In particular, review whether SAT-001 should become the canonical bootstrap
protocol and whether ALG-002/003/005/006/007 form one typed-data roadmap rather than unrelated ops.

The H20 livelihoods round adds three explicit review items: SAT-002 separates discovery-family
novelty from failing-row volume and defines absorption evidence; BNCH-001 adds a pre-contact
semantic lint gate for gold; SCR-001 makes coarse diagnostics sensitive to requested output form.
They are proposals only and do not change the released bootstrap until Codex/Fable reconciliation,
decision, implementation, and validation are recorded.

The later cost-aware stopping proposal `SAT-004` has its own self-contained review entry point at
`governance/review-packet-sat004.md`. Review it independently of H28's eventual score.

H21 pre-contact admission adds SRC-002 (annotation-layer capability), BUG-003 (fail-closed resolver
morphology), and ASK-004 (bounded endpoint-direction versus trend wording). These were discovered
without parser contact and are likewise unreleased pending independent review and conformance tests.

## Evidence

- Livelihoods proposals: `livelihoods_memory/spec-proposals.md`
- Livelihoods failed untouched curve: `livelihoods_memory/coverage/discovery-curve.json`
- Livelihoods protocol: `livelihoods_memory/ROUND2.md`
- Transport proposals: `transport_memory/spec-proposals.md`
- Transport protocol: `transport_memory/ROUND2.md`
- Canonical released spec: `kit/algebra/ir-spec.md`
- Codex review: `governance/reviews/codex-round2.md`

## Non-negotiable review constraints

- Never weaken a user's question to fit the current IR.
- Keep sector snapshots immutable.
- Do not promote prose-only agreement; record a decision and executable conformance tests.
- Distinguish parser syntax, data-kernel semantics, claim-layer semantics, and dialogue planning.
- Preserve evidence labels, units, grain, alignment, completeness, and provenance mechanically.
