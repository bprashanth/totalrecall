# Round 2 epoch 013 certification

H18's 14 valid discoveries were absorbed into general parser rules and 33 deterministic guards.
Its two independently identified bad golds were not promoted into `round2-h18-dev.json`; the
development copy contains 38 valid rows. A composite `(bank, id)` gold-defect registry now prevents
schema-valid but semantically wrong gold from entering the training corpus. Composite identity is
required because `gen-live-04` is reused by an unrelated valid question in another bank.

The active wall is 925 questions across 21 banks and 26 distinct skeletons. The first complete wall
candidate passed ordinary 925/925 and strict 923/925 overall, or 923/923 over eligible rows. The
only strict mismatches are the two previously declared defects in `gen-001.json`. Dialogue binding
remains 5/5 for both model and mechanical paths. The compiled corpus contains 937 parse rows and 5
clarification rows; all four declared bad-gold questions are absent while the unrelated valid
duplicate ID remains present.

This certifies a new freeze, not saturation. H18 contributes no untouched pass, epoch 012 is
retired, and the required three-bank cross-family sequence restarts from zero after epoch 013.
