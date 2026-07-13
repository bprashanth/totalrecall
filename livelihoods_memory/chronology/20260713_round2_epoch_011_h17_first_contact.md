# Round 2 epoch 011 — H17 first contact

## Generation and admission

H17 was generated only after the epoch-011 freeze by Cursor GPT-5.5-high-fast, an external
OpenAI-family author that was prohibited from inspecting the parser, run traces, or prior holdout
questions. It produced 52 candidates from the frozen v2.1 algebra, connector vocabulary, coverage
matrix, and freeze manifest.

The main judge audited all gold before qwen exposure. Static OSM time values were normalized to
v2.1 `null`; one missing count wrapper was restored; a two-item RANK was rewritten as COMPARE but
then excluded; and an invented proximity threshold was removed. Twelve candidates were excluded
before the run for ambiguous or unsupported denotations, unjustified annotation/ranking, or low
novelty. The admitted 40-row bank was frozen at SHA-256
`3705cd9f84bf6113d117898e785f68e91379da2a7fd3dbe6d26037508e643823`.

## Untouched result

The ordinary harness scored 0.915 overall: shape 0.78, holes 0.90, and execution class 0.93.
Strict canonical audit matched 23/40 and found 17 denotation mismatches:
`h17-001`, `002`, `003`, `006`, `008`, `010`, `012`, `013`, `019`, `027`, `029`, `030`,
`033`, `044`, `046`, `047`, and `049`.

This is a failed epoch and contributes zero saturation passes. The bank and traces are immutable
first-contact evidence. No parser repair is permitted until this evidence checkpoint is committed
and every mismatch is classified against the frozen algebra. If valid discoveries are absorbed,
the development wall must be recertified, a new epoch frozen, and the required three-bank
cross-family sequence restarted from zero.

## Classification and epoch-012 absorption

All 17 mismatches were valid compiler discoveries; none was excluded as bad gold. They exposed
clause-scoped two-anchor composition (`and not`, `while also being beyond`, `but are within`, and
`and a Y within`), output wrappers over completed relation trees, relation arithmetic, word-form
top-k, cross-country ratio operand aliasing, city-to-supported-region ranks, same-time
measure-minus-measure, named donors with deictic targets, typed facility/indicator holes, and
generic relation anchors.

Repairs remained inside frozen v2.1. The principal change is one clause-scoped three-entity
relation compiler followed by output-form binding, rather than additional algebra. Independent
binders cover rank `k`, textual operand regions, rejected fallback indicators, and transfer roles.
Sixteen deterministic regressions include negative controls: meta-language “both clauses” must not
trigger shared-distance semantics, and “yes/no” must not make a relation negative.

The first disclosed rerun reached 36/40 strict and exposed four incomplete hole/role rules. The
second reached 40/40. Two complete-wall candidates were then rejected: v1 regressed `gen-live-11`
and `h3-040`; v2 treated the word `no` inside “yes/no” as relation negation. After narrowing those
rules, the final 887-question v3 wall reached ordinary 887/887 and strict 885/885 over eligible
rows (885/887 including the two declared legacy gold defects). Both dialogue binders remain 5/5.

`coverage/epoch-012-certification.json` records the certified wall. H17 remains a failed untouched
bank and contributes zero saturation passes. Epoch 012 restarts the cross-family sequence.
