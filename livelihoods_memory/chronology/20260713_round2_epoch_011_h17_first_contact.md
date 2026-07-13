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
