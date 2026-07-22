# Round 001 results

Round 001 ran from 23:58 on 2026-07-21 to 01:57 on 2026-07-22.  It contains six
conversations, 16 user turns per arm, 80 final-answer slots, and the complete prompt, model,
binding, execution, provenance, latency and token traces.  No benchmark answer was used to repair
an arm during the round.

## Result

| Arm | Trace score | Calls | Failed calls | Non-empty answers | Total stage time |
|---|---:|---:|---:|---:|---:|
| Codex native skills | **190/192 (99.0%)** | 16 | 0 | 16/16 | 7.5 min |
| Codex capability-first | 166/192 (86.5%) | 39 | 0 | 16/16 | 18.6 min |
| Codex late-bound | 163/192 (84.9%) | 39 | 0 | 16/16 | **6.2 min** |
| Codex naked/web | 155/192 (80.7%) | 16 | 0 | 16/16 | 20.7 min |
| LoRA-9B late-bound | 62/192 (32.3%) | 41 | 9 | 9/16 | 65.3 min |

The score is a one-pass trace review under the pre-registered six-dimension rubric, not a claim of
statistical significance or saturation.  `scores.json` retains every turn-level dimension and
`metrics.json` retains the deterministic run accounting.

## The simplest design won

Codex with native executable skills was the strongest arm.  It found the local survey, snake,
satellite, occurrence, estimation and literature procedures when they were useful, called more
than one when necessary, and stopped at their declared evidence boundaries.  It answered the
local snake sequence exactly; retained 75 km retrieval versus 10 km relation semantics; rejected
same-time and causal promotion; exposed missing fire years and restoration start date; joined the
regional Lantana study to the local bird list; and rejected the unsupported composite control.

This is not evidence that algebra is unnecessary.  Every native skill call crossed an allowlisted
gateway that built validated IR and used the same deterministic executor.  The successful shape
was:

```text
question -> agent selects executable skill(s) -> skill builds bounded IR -> executor -> audited data -> agent answer
```

In other words, deterministic algebra lived inside the skill contracts.  The model did not have
to invent the entire bindable tree before it learned what measurements existed.

The native arm's one strict failure was geometry.  `BUFFER 75` produced a latitude-adjusted bbox,
not an exact 75 km circle.  The answer disclosed that, and the closest qualifying pair was inside
the true radius, but the 218/110 source counts and 176 matches describe the bbox pool.  Exact
radius queries need a post-retrieval geodesic filter before those counts can be called 75-km
counts.

## What the algebra arms established

The algebra itself was most valuable on the spatial dialogue.  Capability-first and late-bound
Codex both preserved two 75 km buffers feeding a 10 km `RELATE`, executed the merged occurrence
source, and correctly refused to turn record proximity into co-presence.  This is the clearest
case where explicit structure makes a data-science claim easier to audit than ordinary tool use.

Capability-first was perfect on the known local inventory and spatial conversations.  It weakened
when the selector omitted useful partial capabilities: the king-cobra common name missed the
working taxon alias, vegetation/fire returned a broad data request instead of executing available
satellite partials, and the Lantana follow-up was treated as history instead of running the
available overlap.  One Lantana compile also applied spatial co-occurrence to literature and
transfer rows, which was the wrong relation.

Free late binding was faster and produced the safest unsupported-control trace.  Its frozen IR
retained Krishnagiri, 5 km, restoration sites, elephant records, removal treatment and outcome,
accepted only the supported elephant leaf, rejected the tempting Anamalai site card, and named the
missing datasets.  But its general compiler often emitted abstract leaves such as `vegetation`,
`fire`, or `?proxy`.  Structural retrieval then searched `SELECT` skills, so the relevant
`ANNOTATE` or literature/overlap skills never appeared.  It also classified the snake follow-ups
as history and never executed the exact snake skill.

That failure is more specific than "embeddings are bad."  BGE successfully surfaced and linked
both occurrence leaves for the spatial tree and both king-cobra estimate ingredients.  It failed
when the pre-retrieval algebra had already chosen the wrong operation or an information-poor
placeholder.  Semantic matching cannot reliably repair a frozen structural mistake.

## The local 9B result is a scaffold failure as well as a model failure

LoRA-9B sometimes compiled excellent algebra.  Its first spatial tree was an `AGGREGATE` over a
10 km `RELATE` with two 75 km occurrence buffers, and deterministic execution found the expected
matches.  The responder then timed out, so the user received nothing.

Across the round, seven responder turns and two compiler calls failed at the endpoint deadline.
Seven of 16 final answers were empty.  Several successful outputs leaked internal role/prompt text,
invented conversation turns, expanded EBTL incorrectly, lost the immediately preceding audit, or
claimed registered skills/data did not exist.  The median stage took 52 seconds and p95 reached
300 seconds.

The harness contributed directly: it resent compiler, linker, full execution packs and responder
messages as one growing model dialogue.  A timed-out generation continued occupying the
single-worker server and caused later connection failures.  More training alone will not repair
that.  The next local-model arm should isolate stage histories, keep a compact code-owned audited
conversation ledger, cap execution payloads, require schema-valid compiler/linker output, and use
a stateless responder call.  A split arm—9B compiler plus a stronger responder—is now justified,
but only after the 9B linker is also improved.

## Where an ordinary frontier agent is enough

Naked Codex did useful public-web work.  It found regional king-cobra and Lantana literature,
explained satellite products and grain well, preserved the proximity/time distinction, and
rejected simple restoration causality.  It scored 80.7% without any private assets.

Its boundary appeared where the problem required a common data model.  It could not recover the
local 2024 snake table, called Indian rock python a minimum dangerous-snake count after losing the
requested set, and never executed the control's exact 5 km site/elephant/intervention/outcome
join.  Instead it promoted adjacent landscape evidence and an invasive-removal activity/aim into
a likely improvement.  This is the narrative reason to keep the data/skill layer: frontier search
is sufficient for finding public facts, but not reliably for proving a multi-source estimate or
honest absence of one.

## Decision from round 001

Use native executable skills backed by deterministic algebra as the new baseline.  Keep algebra
explicit for multi-source relations, comparisons and estimates, but compose it from selected
skill signatures rather than asking a general compiler to invent unknown leaves and hoping a
semantic linker can repair them.  Skill contracts should self-advertise operation, return shape,
georeferencing, evidence class, exclusions and a bounded IR builder.

The next matched run should test only the decisions this round exposed:

1. exact geodesic filtering after bbox retrieval;
2. native skills versus a hybrid that selects skill signatures and then composes algebra;
3. 9B compilation with compact code-owned history and a stateless stronger responder;
4. a trained 9B linker/compiler on the observed operation-shape discriminations; and
5. the same untouched question bank, so improvements cannot come from question-specific routes.

Round 001 reaches its exploratory stop condition: it separates the architectures and identifies
concrete failure layers.  It does not satisfy the repository's post-freeze saturation contract.

