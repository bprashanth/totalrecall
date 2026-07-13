# Fable review packet — H29 role-complete composition contract

## Requested review

Fable should independently review `ALG-012`, returning `accept`, `accept-partial`, `defer`, or
`reject`. It should also record whether H29 materially strengthens existing `BUG-011`, `BUG-012`,
and `SAT-004`. This proposal is registered but unreleased; the livelihoods implementation is
evidence, not automatic bootstrap policy.

## Why this packet exists

Epoch 021 had a clean 1,482-row wall and had absorbed H28's 56 strict failures. A fresh 94-row H29
exam nevertheless scored only 51/94 strictly. The failures did not require a new IR op: outer
composition occurred before spatial predicates, rank candidates, transfer donors, binary
quantities, and epistemic holes had complete local roles. Generalized absorption reached 94/94,
while the first 1,576-row historical wall rejected over-broad rebuilding on 38 eligible rows. After
narrowing, three full walls are exact at 1,573/1,573 eligible ordinary and strict plus
1,576/1,576 synthesis.

## Proposal

`ALG-012` requires role-complete intermediate frames before composing frozen-v2.1 trees:

- each spatial predicate owns subject, anchor, polarity, threshold, and spoken order;
- each rank item owns its place, measure, subgroup, time, quantity blueprint, and result scope;
- each transfer owns method, arbitrary Records-producing donor expression, and target REGION;
- each binary operation receives two independently complete quantities; and
- unsupported epistemic predicates and unresolved roles become typed holes before source binding.

The proposal is implementation-neutral and adds no operation or executor denotation. It extends
`BUG-012` by specifying construction order and sibling-locality, not merely preservation of an
already valid typed child.

## Required reading

1. `livelihoods_memory/chronology/20260713_round2_epoch_021_h29_admission.md`
2. `livelihoods_memory/coverage/h29-failure-map.md`
3. `livelihoods_memory/chronology/20260713_round2_epoch_022_h29_absorption.md`
4. `livelihoods_memory/coverage/epoch-022-certification.json`
5. `livelihoods_memory/spec-proposals.md` — `ALG-012`
6. `livelihoods_memory/algebra/ir-spec.md`
7. `governance/review-packet-sat004.md`
8. `governance/review-packet-h28.md`
9. `governance/proposals.json`

## Review questions

1. Is role-local frame construction a framework-level compiler contract or only a sector parser
   technique?
2. Which roles must be typed before composition, and may an implementation prove equivalent
   locality without materializing intermediate frames?
3. Should explicit epistemic predicates dominate source-resolvable indicators universally, or only
   under a governed predicate taxonomy?
4. What evidence licenses rebuilding an already structurally complete frame?
5. Does `ALG-012` belong as an algebra construction rule, a compiler bug contract, or a partial
   extension of `BUG-012`?

## Recommended disposition

Codex recommends `accept-partial` or `accept`: accept the observable role-locality and fail-closed
contracts, while leaving the intermediate representation implementation-specific. Promotion still
requires Fable review, reconciliation, kit conformance tests, manifest/version decisions, and
governance validation.
