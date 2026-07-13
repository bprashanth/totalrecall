# Round 2 epoch 012 — H18 first contact

## Immutable result

H18 ran only after the admitted bank and checksum were committed at `3156e7a`. The qwen 2B
ordinary harness scored 0.900 overall on 40 rows: parse valid 0.975, schema valid 0.975, shape
0.825, holes 0.875, execution class 0.850, and grounded execution 0.950.

Strict canonical audit matched 24/40. The 16 mismatches are `h18-002`, `h18-003`, `h18-004`,
`h18-008`, `h18-011`, `h18-014`, `h18-016`, `h18-020`, `h18-021`, `h18-022`, `h18-023`,
`h18-039`, `h18-044`, `h18-045`, `h18-048`, and `h18-050`.

The frozen evidence is under `runs/epoch012-holdout-018/`. H18 is not a saturation pass. No
parser repair is permitted until this result is checkpointed and the mismatches are independently
adjudicated. If any valid compiler discovery is absorbed, epoch 012 is invalidated, the counter
remains zero, and a new full-wall certification and freeze are required.
