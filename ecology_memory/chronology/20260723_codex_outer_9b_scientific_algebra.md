# Codex outer dialogue + 9B scientific Algebra — 2026-07-23

## Why

The first hybrid trial gave Algebra 9B a catalogue of skills and used it as a workflow planner.
That tested whether 9B could choose operations, but not the intended boundary: Codex should manage
the conversation and evidence discovery, while the Algebra-trained model should express only the
scientific computation.

The chat presentation also exposed implementation labels such as `[Model background]` and
`[Local asset]`. Those labels were auditable but read like internal markup rather than a useful
answer, and the user could not easily see the exact scientific question sent to 9B.

## What changed

- The visible planner skill was replaced by `compile-scientific-algebra-9b`.
- Codex now owns dialogue, clarification, site orientation, connector discovery and ordinary
  evidence skills. It passes only one `scientific_question` to the compiler.
- The controller supplies the frozen IR grammar, connector capability catalogue and a manifest of
  resource symbols admitted by the user, onboarded profile or audited prior skill results. 9B
  receives no skill catalogue and returns one Algebra tree, not plan JSON.
- Code validates the frozen schema and rejects any entity, region or raster layer that was neither
  user-named nor admitted. The deterministic binder may remove only harmless record-kind suffixes
  from an exact admitted taxon and maps resolved site names back to stable declared region symbols.
- The validated tree executes through the existing deterministic executor, including its empty
  result and estimate-gate semantics. Codex cannot author or repair the tree.
- The final response now adds a stable **Scientific analysis** panel containing the exact question
  sent to 9B, a plain-English reading of the returned Algebra, the bound execution result and a
  collapsed exact IR audit. Bracketed provenance tags are rewritten as natural phrases.
- The skill metadata and `SKILL.md` were rebuilt according to the repository's installed
  skill-creator guidance and pass its validator.

The frozen Algebra schema and frozen 12-skill benchmark catalogue were not changed.

## Verification evidence

Focused bridge tests cover the outer/inner prompt boundary, compiler input sanitisation, successful
9B-tree execution, rejection of a model-invented taxon, exact admitted-symbol binding, response
formatting and bracket-tag removal.

A live request to the already-running `lora9b` endpoint returned valid `SELECT` Algebra. The first
probe surfaced two boundary forms—`Daboia russelii occurrence records` and the expanded EBTL display
name. After deterministic admitted-symbol binding, the same path produced:

```json
{
  "op": "SELECT",
  "entity": "Daboia russelii",
  "region": {"op": "REGION", "place": "EBTL"},
  "time": null
}
```

The executor then returned the expected `empty_select` data request for that narrow site query,
rather than fabricating a presence claim. This was a compiler/binder verification, not a model
quality or saturation claim.

A fresh end-to-end bridge chat then used `local-site-evidence-search` followed by
`compile-scientific-algebra-9b`. Its visible answer contained the local previous-property record,
the empty bounded occurrence result, and a separate scientific panel with the exact question,
plain-English 9B interpretation, bound execution and collapsed IR. It exposed no bracketed
provenance tags. The probe also caught two wasted retries caused by an apostrophe inside
single-quoted shell JSON; the generated wrapper and relevant skill instructions now provide a
shell-safe `--pairs key="value"` form. After that last change, 256 repository tests pass, the skill
validator passes, `git diff --check` is clean, and the lightweight bridge is healthy with 21 skills.
