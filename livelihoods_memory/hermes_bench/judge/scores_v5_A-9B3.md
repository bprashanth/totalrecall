# v5 — adapter-003 verdict (Fable, human hat)

## A-9B3-ctx (bare): ~1.7-1.8 overall — THE RESPONDER DIET WORKED.
Turn 1 is near the deepseek bar: dense pack numbers w/ citations (11.96 lakh workers, NIC splits
4,406/3,659/3,539, Kalingarayan 6,000→3,000 ha, Noyyal TDS from papers, powerloom wage ranges
from Brindha, 570.53MT @ 12,685, MGNREGS 80,321 @ 336), honest gap statement + survey
suggestion + natural close. Plan-narration GONE. Indian register emerged ("lakh" forms — the
Indic diet showing). Defect: turn-1 text duplicated twice (echo bug, mechanical); occasional
fabricated GRANULAR sub-splits deeper in session (e.g. cultivator main/marginal 30,696/47,474 —
not in pack) — exactly the class S3 exists for.
Retention: hard-eval 1.000, seed 1.000, indic-eval 0.979 (002: 0.984, Δ within noise n=82).
COMPILE SKILL FULLY HELD; conversation quality gained ~0.4-0.5 bands. Diet hypothesis CONFIRMED.

## A-9B3-ctx-s3: rail worked as DETECTOR, failed as REPAIRER — two bugs, both fixable:
1. REPAIR WITHOUT CONTEXT: repair prompt omitted the pack/digest; deepseek even wrote "since no
   DATA PACK context was provided" and blanket-tagged fabricated numbers as
   "(estimate — basis: Census 2011)" — semantic laundering: claims a SOURCE as an estimate
   basis. Fix: include digest in repair call; verifier must reject basis-text that is just a
   source name for numbers colliding with a source's domain.
2. FALSE POSITIVES ON SCALED FORMS: "11.96 lakh"/"3.70 lakh" = 1,195,773/370,212 scaled; the
   verifier lacks lakh/million/crore normalization → giant violation counts (stripped(32)) on
   honest turns, mangling them. Fix: scale-aware matching (×1e5, ×1e6, ×1e7) in _derived.
S3 verdict: detection precision on TRUE fabrications = good (caught the sub-split inventions);
end-to-end answer quality WORSE than bare on scaled-form turns. Do not deploy s3 until both
fixes land; bare A-9B3-ctx is the current best arm.
