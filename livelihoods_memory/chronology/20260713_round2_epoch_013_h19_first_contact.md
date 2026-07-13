# Round 2 epoch 013 — H19 first contact

H19 first contacted the frozen epoch-013 parser only after pre-contact bank commit `d102d1c`.
The immutable bank contained 40 questions at SHA-256
`fc4df34c1335d350ac3eb25b529b7377443da16bf90a4abf72883bfd89076d38`.

The qwen2b run is preserved at `runs/epoch013-holdout-019/`. Coarse harness scores were:

- parse valid: 40/40;
- schema valid: 39/40;
- shape match: 32/40;
- holes correct: 38/40;
- execution class: 37/40;
- overall: 0.9271.

The strict canonical audit matched 21/40 and reported 19 mismatches. Initial independent
adjudication found candidate compiler failures in region-scope preservation (`h19-006`,
`h19-008`, `h19-049`), presence composition (`h19-010`), temporal direction/endpoints
(`h19-011`, `h19-013`), list preservation (`h19-018`, `h19-044`), deictic region retention
(`h19-029`), density ranking (`h19-031`), rank-of-changes (`h19-032`, `h19-056`), computed
distance (`h19-034`, `h19-061`), nested relation completeness (`h19-035`), comparison of
relational counts (`h19-036`), count operands (`h19-038`), and generic-statistics ambiguity
(`h19-046`). `h19-040` appears instead to expose a strict-audit canonicalization error: the
expected canonical form truncates “Île de France” to “ile de” while the parser preserves the
complete place.

These classifications are provisional until row-by-row adjudication is complete, but the stopping
decision is not: H19 is a failed untouched bank, epoch 013 cannot contribute a saturation pass,
and any repair retires the freeze and resets the consecutive-pass count to zero.
