# Round 2 epoch 016 certification

H21 retired epoch 015 at strict 17/40. Independent adjudication found 23 valid compiler-bearing
rows across six families, with no gold or audit defects. The disclosed fix2 replay is strict 40/40,
and all 40 rows were released to development. Ninety-two deterministic tests cover the new rules
and their adjacent negative semantics.

The first wall attempt exposed a latent H19 outcome defect that old unsafe geocoding had concealed:
the correctly resolved Warsaw capital region exceeds the OSM connector's exact-count cap. The
immutable H19 row is registered as defective, while its disclosed copy correctly expects a
`source_truncated` DataRequest. The second attempt exposed a late-pass interaction that replaced
valid arithmetic COMPARE trees with literal source gaps. A negative guard was added. Both attempts
were discarded and every bank rerun after each metadata or parser change.

The final v3 active wall contains 1,040 questions across 24 banks and 34 gold-tree skeletons. The
ordinary harness passes 1,040/1,040. Strict canonical audit passes 1,038/1,040 overall and
1,038/1,038 eligible; the only mismatches are the two long-declared `gen-001` defects. H21's
disclosed bank passes 40/40 under both gates.

Dialogue binding passes 5/5 for both model and mechanical paths. The ten adopted ILOSTAT/Eurostat
source-census probes remain green. Coverage now spans four source families, three principal grains,
and 34 skeletons. Corpus compilation produces 1,052 unique parse rows plus five clarification rows;
nine immutable defect questions are absent, while five corrected development copies are retained
under composite bank/id defect identity.

National-only World Bank and ILO routes now require the original requested scope to resolve as a
country, curated statistical-region aliases are country-qualified before geocoding, and region
failures return typed DataRequests. These local guards are captured for framework review in
SRC-003; they do not change frozen v2.1 algebra.

Epoch 016 is certified for new blind holdouts. This is not a saturation claim: H21 is disclosed
development, the counter is zero, and H22 must be authored only after the epoch-016 checksum
boundary.
