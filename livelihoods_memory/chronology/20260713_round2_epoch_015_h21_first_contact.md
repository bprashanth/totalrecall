# Round 2 epoch 015 — H21 first contact

H21 first contacted the frozen epoch-015 solver only after the admitted bank and checksum were
committed at `ca54089`. The immutable bank contains 40 questions at SHA-256
`770457ea283aab67b68f97d59d902e4f2a124cd53d1ec2ceb6d8734b0ba0b579`.

The qwen 2B ordinary harness scored 0.902 overall: shape 0.820, holes 0.880, and execution class
0.850. Strict canonical audit matched 17/40 and reported 23 mismatches: `h21-001`, `002`, `004`,
`005`, `007`, `008`, `010`, `032`, `033`, `037`, `039`, `040`, `041`, `043`, `044`, `048`,
`049`, `050`, `051`, `053`, `054`, `068`, and `079`.

The frozen evidence is under `runs/epoch015-holdout-021/`. H21 is not a saturation pass; epoch 015
cannot contribute to the required sequence and the counter remains zero. No parser, audit,
connector, scorer, or repair change is permitted until this evidence checkpoint is committed and
the mismatch set is independently adjudicated.

Provisional clusters include new endpoint-rank surfaces, heterogeneous mixed-source ranks, exact
unsupported statistical literals, partial-hole role scope, deictic candidate ranks, anaphoric
binary comparisons, distance holes, and relational-count ratios. These classifications are not
final in this immutable checkpoint.
