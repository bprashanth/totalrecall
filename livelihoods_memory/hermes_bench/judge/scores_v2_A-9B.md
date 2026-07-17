# v2 A-9B — near-frontier substance, broken delivery. Means: grounding 1.7, honesty 1.6,
place 1.6, prose 0.9, coherence 1.2.
Turn 1 substance ≈ deepseek: real pack numbers w/ citations (2.25M pop, 53.1% WPR, 19,521 units,
77,500 SSI workers, 80,321/185,051 MGNREGS, ₹336/day, 570.53MT @ ₹12,685, GI 2019), honest
"what I don't have" list, natural close. THE PARAM CURVE HOLDS for content quality.
Three delivery defects: (1) PLAN LEAKAGE — internal monologue ("The user wants me to... Let me
organize...") printed before answers (adapter minimal-prompt habit + shim passes raw text);
(2) intent-only turns — t2 ended after "I'll pull the datasets..." without doing it (18s);
(3) latency — t1 1571s; 2 of 14 turns hit even the 1800s kill (26 tool schemas × HF-shim 9B).
All three look scaffold-fixable -> v3.
