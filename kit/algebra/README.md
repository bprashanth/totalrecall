# The algebra, layered — language → primitives → tool calls

The released machine contract is [ir-spec.md](ir-spec.md) at v2.3.0. The reviewed but unreleased
ALG-015 implementation candidate is isolated in
[ir-spec-v2.4.0-draft.md](ir-spec-v2.4.0-draft.md); it requires an explicit draft profile and is
not part of the bootstrap manifest.

*(Design write-up produced in the memory-architecture brainstorm, 2026-07-10. Kept as-is; the harness in
`../harness/` exists to test it. Findings that confirm or overturn parts of this live in `FINDINGS.md` and
the per-run docs under `../runs/`.)*

Yes — this is a valid approach, and it has strong precedent. What you're describing is semantic parsing to
a closed query algebra: LLMs are unreliable as *sources of facts* but quite reliable as *compilers* from
English into a small, constrained formal target. That's the whole text-to-SQL literature. The design stance
becomes: **the model does translation and synthesis; the algebra does truth.** Everything below follows
from taking that stance seriously.

The key clarification first: the design mixes three different layers of primitive, and separating them
answers most of the open questions (including where the gate and verify live).

## Layer 1: Data primitives (the kernel — deterministic, closed)

These operate on a few typed values: `Records` (rows with geometry + time + attributes), `Region` (a
boundary), `Field` (a continuous surface over a region), `Series` (value over time), `Scalar`. The minimum
kernel is small:

| Op | Signature | Covers |
|---|---|---|
| **SELECT** | entity, region, time-window → Records | "the food vendors here, last year" |
| **ANNOTATE** | Records + layer → Records with new column | the existing connector shape |
| **RELATE** | Records × Records → Records with distance/containment/co-occurrence | "x in relation to y" |
| **AGGREGATE** | Records → Field or Series (count/density by cell or time-bin) | turns points into something comparable |
| **COMPARE** | two Fields / Series / Scalars → difference | "is x and y different" — works along space, time, or place |
| **ESTIMATE** | Records (from elsewhere) + place → Field | transfer/interpolation — the only op that *models* |

Notice that the existing taxonomy (STATE / RELATION / CHANGE / TREND / VALUE) is the **question-level**
vocabulary, and each compiles down to kernel compositions: CHANGE = `COMPARE(AGGREGATE(t₁), AGGREGATE(t₂))`
— two snapshots. TREND = `AGGREGATE` into a Series, then a direction fit — so trend vs. change is not two
primitives, it's two compositions of the same ones. RELATION = two SELECTs joined by RELATE. That two-level
structure is a feature: the router speaks question-level, the executor speaks kernel-level, and the golden
traces can assert on *either*.

Also: don't invent the data layer from scratch. SELECT/RELATE/AGGREGATE/COMPARE already exist with
battle-tested semantics in SQL/PostGIS. Steal those semantics wholesale. The part that doesn't exist
anywhere — the part that's actually yours — is layer 2.

## Layer 2: Epistemic primitives (they operate on *claims*, not data)

This is where GATE and VERIFY live, and why they felt like they didn't fit the list — they're not data
transformations.

- **GATE is not an op the planner composes — it's an admissibility rule on ESTIMATE.** An ESTIMATE node is
  only legal if it carries a gate certificate (which similarity held, how strong). Think of it as a
  precondition in the type system, not a verb in the sentence. This is much stronger than "the model should
  remember to gate": an ungated ESTIMATE is simply an invalid expression that the executor refuses to run.

- **Evidence labels propagate like taint.** Every value carries `observed | modelled | proxy`, and the
  algebra defines propagation: anything downstream of an ESTIMATE is modelled; a COMPARE of observed vs.
  modelled is modelled-with-caveat. The "observed vs modelled always labelled" invariant then stops being
  model discipline and becomes a mechanical property — code checks whether the expression tree contains an
  ESTIMATE node and injects the label. This is the actual invention in the system. The spatial ops are
  commodity; the **algebra of evidence labels** is not.

- **VERIFY is a primitive, but at the claim layer — and it's a family.** verify-by-eyeball (show raw
  records beside the model), verify-by-agreement (two independent methods concur), verify-by-holdout
  (backtest when new data arrives), and yes, verify-by-user (ask) as the base case. They all share a
  signature: claim → evidence-the-user-can-inspect.

- **DataRequest is a first-class *return type*.** Every query evaluates to either `Answer` or
  `PartialAnswer + DataRequest`. "The ask" isn't a failure path or a suggestion the model may or may not
  remember — it's one of the two things an evaluation can produce. This matches the philosophy doc exactly
  and makes "never return empty" structural.

- **Provenance is free.** The expression tree *is* the provenance. No separate lineage bookkeeping.

## Layer 3: Dialogue primitives — and a trick that makes clarification mechanical

The piece to take away most. Parse the question into the IR *with typed holes*: "map the vendors" parses to
`SELECT(?entity_subtype, place.boundary, ?time_window)`. The rule: **an expression executes only when it
has no free variables; a free variable *is* the clarifying question.** "Ask, don't assume" stops being a
constitution rule the model might drift away from and becomes: the binder failed, so ask about exactly the
unbound slot. It also fixes the Goodhart problem on `asked_when_ambiguous` — the assistant can't over-ask,
because a fully-bound expression gives it nothing to ask about.

## The minimum system

Five stages, model only at the edges (which matches what the architecture doc already found empirically):

1. **Parse** — LLM: question → IR (JSON expression tree), schema-validated, retry on invalid. Few-shot
   from the golden set.
2. **Bind** — code: entity names through the resolver, place through FACTS, times normalized. Unbound
   variable → clarify and stop.
3. **Check** — code: admissibility (ESTIMATE needs a gate pass → else emit DataRequest), node-count budget
   cap.
4. **Execute** — code: walk the tree, one connector per kernel op. Zero model involvement.
5. **Synthesize** — LLM: result + evidence labels + provenance → short prose.

On skills/hooks specifically: expose **one `evaluate(expression)` tool** rather than one tool per op. If
the agent composes ops call-by-call, you're back to freestyle drift — the exact discipline failures the
docs catalogue. One-shot evaluation means the budget hook is trivial (cap tree size, not call count), the
trace is the expression itself, and golden-trace assertions become "question X must parse to a tree
containing ESTIMATE + gate" — far crisper than asserting on answer text. Recipes/skills then live at the
question level as IR templates the router selects; hooks enforce IR properties (valid schema, no free vars,
gated estimates, modelled-label present) entirely in code.

## Is there a better way to model it?

The honest alternatives: (a) pure agentic tool use with no IR — more flexible, but the project's own
regression history is the argument against it; the failures were discipline and state, and an IR is
discipline made structural. (b) Compile straight to SQL/PostGIS — genuinely viable for layer 1, and worth
considering, but it has no ESTIMATE/GATE/DataRequest, so you'd still build layer 2 on top. Which points to
the framing to actually adopt:

**The algebra = a commodity data kernel (borrow SQL/PostGIS semantics) + a small epistemic layer that is
genuinely novel: evidence-label propagation, gate-as-admissibility, verify-as-claim-op,
DataRequest-as-return-type, holes-as-clarification.** Roughly six kernel ops and five epistemic constructs.
That's the whole minimum algebra — and every constitution invariant becomes either a type rule or a code
check on the tree, rather than prose the model must remember.

The concrete first test: take the five golden questions, hand-write the target IR for each, and measure
only parse accuracy (question → correct tree). That isolates the one step where the model can silently
fail, and it's cheap to run before building any executor.
