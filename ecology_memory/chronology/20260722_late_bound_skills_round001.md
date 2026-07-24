# Late-bound skills round 001

## Why

We needed to decide whether a place question should be compiled after an LLM first selects
capabilities, compiled into general algebra and bound semantically afterward, or handled by an
ordinary agent over executable skills.  We also needed matched controls for the promoted local 9B
and for a frontier agent with only web access.

## What was frozen

Five arms saw the same five three-turn NGO conversations and one unsupported composite control.
Codex was pinned to GPT-5.4 medium.  The local endpoint served `merged-9b-003`.  The late-bound
compiler could not see skill cards before its raw IR was saved and hashed.  BGE-small returned at
most three structurally eligible cards; code validated every selected ID before executing the
existing frozen harness.  Codex arms ran in isolated Docker views, and credentials/session state
stayed outside the repository.

No algebra, connector, card or prompt was repaired after a benchmark answer appeared.  Smoke-test
fixes before the frozen round were limited to container stdin/web flag plumbing, keeping auth out
of the run tree, enforcing catalog-declared site scope, and preventing execution of an unbound
late-bound leaf.

## What ran

Round 001 ran 80 answer slots from 2026-07-21 23:58 to 2026-07-22 01:57.  The frozen matrix is at
`narrative/benchmarks/late-bound-skills/runs/round-001/matrix.json`; stage logs, semantic ranks,
bindings, gateway calls and hashes are in the adjacent run tree.  Turn-level scores and runtime
metrics are in `scores.json` and `metrics.json`.

## What we found

Native Codex over executable skills backed by bounded IR scored 190/192.  Capability-first Codex
scored 166, free late-bound Codex 163, naked Codex 155, and LoRA-9B late-bound 62.

The result does not remove algebra.  It places algebra inside executable skill contracts and uses
explicit composition when a relation or estimate needs it.  The model can discover and call the
measurements that exist; code still owns IR construction, evidence labels, gates, provenance and
failure.

Free late binding worked when the general compiler chose the right structural operation.  It was
excellent for the two-radius spatial query and for retaining every unsupported-control clause.
It failed when the compiler produced `SELECT vegetation`, `SELECT fire`, or `SELECT ?proxy` while
the useful contract was an `ANNOTATE`, literature, or overlap skill.  Semantic retrieval cannot
repair a frozen operation mismatch.

The local 9B compiler sometimes produced the best raw spatial algebra, but its end-to-end arm had
nine failed stages and seven empty answers.  Growing internal-stage history caused extreme
latency, endpoint backpressure and corrupted responses.  The next local experiment must separate
stage histories and use a compact audited ledger before interpreting this as a training-only
problem.

Naked Codex was sufficient for public literature and broad satellite explanations.  It was not
reliable for local survey facts or the composite geometry/intervention/outcome join, where it
substituted plausible regional prose for an executed common data model.

## Stop and next action

The exploratory stop condition is met: the arms are separated, the strongest baseline is clear,
and failures are localized to selection/shape, binding, geometry, execution, response history or
public-data absence.  This is not saturation.  The next frozen round should compare native skills
against signature-first algebra composition, add exact geodesic filtering, and test a 9B compiler
with compact state plus a stateless stronger responder on the identical untouched bank.

