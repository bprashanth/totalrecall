# Framework governance

This directory is the review and promotion boundary between sector experiments and the canonical
bootstrap kit. Sector snapshots remain immutable evidence. A discovery in a sector does not become
framework behavior merely because a sector harness implemented a workaround.

## Lifecycle

1. A sector records evidence in its append-only `spec-proposals.md` and experiment chronology.
2. The supervisor assigns a stable proposal ID in `proposals.json` and records dependencies,
   compatibility, required tests, and a recommendation.
3. Codex and Fable review independently. Reviews are evidence, not implementation authority.
4. A reconciled decision is recorded under `decisions/`. Acceptance requires agreement on the
   semantic contract; a proposal may be accepted in part or accepted as protocol rather than IR.
5. Accepted changes are implemented and tested in `kit/`. Only then may the manifest call them
   `implemented` or `validated`.
6. `framework-manifest.json` names the stable algebra and saturation protocol copied by bootstrap.

Allowed proposal states are `proposed`, `deferred`, `rejected`, `accepted`,
`accepted-conditional`, `rfc-required`, `implemented`, and `validated`. Conditional acceptance and
RFC-required status are decision records, not release states. Only `validated` changes belong in a
released bootstrap manifest. Reviews use `accept`, `accept-partial`, `defer`, or `reject`.

## Snapshot rule

Existing `<sector>_memory/` directories are historical snapshots. `bootstrap.sh` creates new
snapshots from the current released kit and writes `framework-lock.json`. Existing sectors are
upgraded only by an explicit migration or by bootstrapping a fresh directory; they are never
silently mutated when governance advances.

## Agreement gate

`python3 scripts/validate_governance.py` verifies the registries and release manifest. Promotion
requires separate Codex and Fable review artifacts plus a decision record. A textual agreement in
a chat is not sufficient because it is not durable or reproducible.
