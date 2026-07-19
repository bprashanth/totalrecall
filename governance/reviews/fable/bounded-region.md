# Fable review — ALG-015 BUFFER over REGION

- Reviewer: Fable (supervisor role), 2026-07-18
- Packet: `governance/review-packet-bounded-region.md` (reviewed in isolation)
- Reviewed against: released IR v2.2.1 + v2.3.0 executor contracts; prior decision
  20260716-ALG-contracts (versioning precedent).

**Disposition: accept-partial.**

**Accepted semantic core.** `BUFFER(source: REGION, radius_km) -> REGION` exactly as proposed:
a support transformation, not a data operation. Answers to the packet's questions:

1. **Core support transformation** (packet Q1) — not a REGION parameter and not connector
   metadata. Rationale: it composes by *type identity* (anywhere a REGION node is legal, a
   BUFFER node is legal — SELECT.region, RELATE operand regions), adds zero result types, and
   its semantics are connector-independent. Folding it into REGION as a parameter would overload
   the resolver leaf with a geometric transform; keeping it a node keeps provenance clean
   (source region, radius, method all visible in the tree).
2. **Labelled approximation is acceptable** (Q2). A bbox-only executor may expose a
   latitude-aware bbox expansion **only** under an unerasable provenance label
   (`method: "bbox-approx"`), and any rendered answer must call the area approximate. This is
   consistent with the framework's core move — honesty by labelling, not by prohibition. The
   packet's own counterexample (high-latitude over-coverage, discontinuities) is the reason the
   label must be unerasable and dateline/pole cases fail closed, both accepted as written.
3. **Common support is a canonical-form concern, not a schema constraint** (Q3). Schema
   validation cannot see that two supports are "the same analysis support"; a schema rule would
   be theater. Instead: identical BUFFER nodes canonicalize to one shared node (the existing
   tree-normalization machinery), and any profile that *requires* aligned support states it as a
   compiler obligation. Execution never silently copies one operand's support to another —
   accepted as the invariant it is.
4. **Nested-buffer canonical identity: additive radii** (Q4).
   `BUFFER(BUFFER(R, a), b) ≡ BUFFER(R, a+b)` — true for bbox expansion and for exact geodesic
   buffering alike, so it is method-independent and safe to declare now.
5. **Yes, parser-visible promotion requires a versioned model bundle** (Q5). Same rule as
   ALG-002 in decision 20260716: BUFFER ships in the **v2.4.0 parser-surface bundle**, and
   sectors pin v2.4.0 only when a v2.4.0-trained model exists — the model carries the algebra
   version. Existing trees keep their denotation; no retro-compatibility issue.

**Excluded / deferred surface.** Negative buffers (erosion), asymmetric or anisotropic buffers,
buffering of record geometries (BUFFER over Records is a type error, per invariant 2), and any
polygon-exactness claims in the reference executor. All can arrive later with evidence.

**Conditions precedent for promotion** (beyond the packet's own conformance list, which is
accepted in full): (a) corpus evidence — a minted, execution-verified question set exercising
BUFFER (the search-support question class: "what is around X within Y km" as *selection support*,
distinct from pairwise RELATE proximity), demonstrating small-model compilability; (b) the
v2.4.0 bundle discipline above.

**Strongest counterexample check.** The packet's own counterexample is the right one and its
resolution (unerasable approximation label + fail-closed boundaries) is the one accepted here.
One addition: the confusion risk between `BUFFER` radius and `RELATE.threshold_km` is real for
small models — the conformance suite must include a discrimination test (a question needing
BOTH, e.g. "clinics within 2 km of schools, searching 10 km around Erode town") so the corpus
teaches the distinction rather than leaving it to luck.
