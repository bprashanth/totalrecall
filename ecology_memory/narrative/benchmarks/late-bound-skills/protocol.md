# Frozen protocol

## Shared conditions

- Questions and turn order are identical.
- One fresh session/history per arm and conversation; no state crosses conversations or arms.
- Codex is pinned to GPT-5.4 with medium reasoning.  The local arm is pinned to the promoted
  `merged-9b-003` served as `lora9b` on port 8004; no service may be restarted or substituted.
- The algebra is the existing ecology JSON IR.  The late-bound compiler sees no skill name or
  description until its raw algebra has been persisted and hashed.
- BGE-small retrieves at most three structurally eligible skill cards.  Retrieval never directly
  authorizes execution.  The model may select one exact candidate or `NONE`; code validates the
  selected manifest before binding.
- Model prose never establishes an evidence label or transfer gate.  The deterministic executor
  owns execution, emptiness, provenance, evidence labels, and DataRequests.
- Existing source and connector gaps remain gaps.  In particular, the round does not add a fire
  time-series wrapper, restoration start date, property polygon, restoration-intervention
  inventory, or invasive-removal outcome dataset.

## Isolation

Each Codex conversation runs with a private `CODEX_HOME` and Docker mount view containing only the
assets admitted to that arm.  The host repository, narrative, scoring files, other arm workspaces,
and earlier outputs are absent.  The Codex binary is mounted read-only.  Authentication is copied
into the private home, never into the recorded prompt/output bundle.

The native-skill arm receives generated `SKILL.md` files and a single allowlisted skill-call
client.  That client talks to the host runner, which validates the skill ID and arguments before
calling the frozen executor.  API keys never enter the agent container.

The naked arm receives an empty workspace and ordinary web search.  It receives no local site
card beyond what the questions themselves say.

## Observable audit

Every stage records request text, SHA-256, raw JSONL/API response, visible final message, session
or history ID, latency, parsed object, validation outcome, and model identity.  Hidden reasoning is
not available and is not claimed as evidence.  The run stores pre-link algebra separately from
bound algebra; a post-retrieval replan cannot silently replace the frozen first tree.

## Pre-registered gaps

- The fire connector aggregates an interval and cannot answer whether fire rose or fell by year.
- `SITE_EBTL.json` has no restoration start date or surveyed property polygon.
- No admitted dataset identifies restoration interventions near Krishnagiri or before/after
  invasive-removal outcomes.
- Local published evidence is richer than public point sources and must be exposed explicitly to
  the native-skill arm.
- `merged-9b-003` was not trained on BUFFER/FILTER rows.  Its arm is runtime-prompted with the same
  grammar as Codex for architecture comparability and must not be described as v2.4-conformant.

