# Round 2 epoch 017 — H25 first contact

H25 first contacted qwen only after the immutable bank and admission record were committed at
`f5cc55e`. The bank SHA-256 is
`5bdb2c52c9f1c3d5e757c548623ce3a83cbe29cb93d2488e835039aeed41f89a`.

The ordinary harness scored 0.918 overall: shape 0.78, holes 0.97, and execution class 0.93.
Strict canonical audit matched 29/40 and found eleven mismatches: H25-020, 021, 050, 061, 062,
067, 068, 070, 073, 080, and 088. The immutable run is `runs/epoch017-holdout-025/`; the strict
audit is `coverage/semantic-audit-epoch017-holdout-025.json`.

All eleven mismatches are provisionally compiler-bearing. The symptoms include a lost existential
presence aggregate, a worded three-quarter threshold reset to 1 km, loss of the exact Eurostat
`employed persons` measure, winner ranks without `k=1`, an endpoint-change winner collapsed to one
country, ascending/descending inversions on ranked changes and ratios, total failure on a ranked
spatial composition, malformed relational ESTIMATE roles, and an anaphoric relation anchor changed
into a bank-to-bank self-join. H25 therefore rejects epoch 017 and contributes zero consecutive
passes. The saturation counter remains zero.

Manual prose review also found answer-surface failures that structural scoring would miss. H25-088
executed a hallucinated bank self-join with `presence=true`, while synthesis said no banks were
found. H25-073 produced an ascending tree despite “highest to lowest,” then called Germany's 0.85
ratio highest while listing France at 0.99. H25-067 silently answered France alone but synthesized
a three-country claim. These require separate synthesis-faithfulness adjudication during
absorption; green execution is not sufficient evidence.

This checkpoint preserves first-contact evidence before any repair. The immutable bank will not be
edited. Any generalized compiler, synthesis, audit, or harness repair retires epoch 017, requires a
full disclosed wall, a new checksum freeze, and fresh post-freeze banks before the counter can move.
