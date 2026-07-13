# Round 2 epoch 015 certification

H20 retired epoch 014 with 22 strict mismatches. Independent adjudication found 19 clean compiler
discoveries, two compiler discoveries with orthogonal rank-cardinality gold defects, one ambiguous
gold, and no strict-audit defect. The compiler-bearing rows reduce to six discovery families, now
guarded by 69 deterministic positive and negative regressions. Thirty-seven eligible H20 rows were
released into development; the immutable bank and all three defects remain unchanged.

The first complete-wall candidate exposed five latent development gold errors: four singular-winner
ranks without `k:1` and one explicit from-to “go up or down” request mislabeled as a whole-window
trend. The disclosed development copies were corrected; the four originating immutable holdouts
were registered as defects. Because gold changed, every bank was rerun rather than reusing the
otherwise valid candidate.

The final active wall contains exactly 1,000 questions across 23 banks and 31 gold-tree skeletons.
The ordinary harness passes 1,000/1,000. Strict canonical audit passes 998/1,000 overall and
998/998 eligible; the only mismatches are the two legacy defects in `questions/gen-001.json`.
The H20 disclosed bank passes 37/37 under both gates. Dialogue binding remains 5/5 for model and
mechanical paths.

Corpus compilation now preserves defect identity as `(bank,id)` instead of collapsing the registry
to question text. This excludes the nine immutable defect rows that have no corrected development
copy, retains four corrected copies from H2–H4, excludes the two legacy gen-001 defects, and produces
1,012 unique parse rows plus five clarification rows. This repair is itself regression-tested.

Coverage reports 1,000 active questions and 31 skeletons. Governance validates 21 proposals with
only four released; SAT-002, BNCH-001, and SCR-001 remain proposals for Fable review. Epoch 015 is
certified for new blind holdouts. This is not a saturation claim: H20 is disclosed development and
the consecutive untouched counter is zero of three.
