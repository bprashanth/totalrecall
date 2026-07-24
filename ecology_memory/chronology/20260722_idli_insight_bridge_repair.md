# Idli Insight bridge repair

## Why

The first Codex-native Idlisseus POC proved that a general agent could discover and invoke the
frozen conservation skills, but a browser trace exposed four transport and presentation defects:

- each browser turn became a different Codex session;
- an uploaded workbook was reduced to placeholder prose and never reached the sandbox;
- the audit trace and answer were concatenated into one noisy Markdown response;
- a Markdown file created inside the execution sandbox was not an Idlisseus visual report.

The long implementation thread then became unusable after the Codex backend returned `Request
blocked` for that legacy context. Its rollout was 48.7 MB and had processed about 948.6 million
cumulative tokens. The repositories were still clean, so the implementation was recovered into a
fresh thread rather than attempting to resume the poisoned context.

## What changed

The internal endpoint now has the provider-neutral public identity `idli-insight`. Idlisseus sends
the stable browser session id only to this internal bridge, so one browser conversation resumes one
Codex thread. The existing endpoint database row was updated in place without restarting any
container or model server.

For attached files, Idlisseus resolves each upload through its owner-aware upload handler and sends
a small manifest. The bridge independently requires each source to resolve beneath the configured
upload root, bounds count and size, copies it into the session input tree, records a digest, and
shows Codex only the sandbox path. This is a trusted internal-service boundary, not end-user
authorization at the bridge token itself.

The OpenAI-compatible stream no longer turns progress into answer Markdown. The public stream is
now deliberately smaller than the private audit: only actual skill invocations cross the bridge,
as `insight_skill` events containing the skill name, status, and stable audit id. Idlisseus
persists that summary in assistant-message metadata and renders it in a compact, responsive
**Why** panel above the answer. Raw commands, file paths, outputs, discovery, skill reads, progress
commentary, and backend model routing remain only in server logs and JSONL audit files. The final
answer is emitted once as clean text.

The history renderer recognizes the original `Codex CLI · native skill trace` Markdown, extracts
only its `Invoke skill` names and audit id, removes the trace and duplicate answer, and labels the
reply `idli-insight`. This cleans the already-saved
`3de2c583-6667-4972-acd8-369c69dcb5da` thread without rewriting its database rows. The same model
mask applies to live role labels and the message-stats popup.

An explicit `publish-report` presentation skill now accepts bounded Markdown and source metadata,
writes the existing owner-stamped deep-research JSON schema, and returns the normal authenticated
`/api/research/report/<id>` URL. Idlisseus continues to own HTML rendering, download, and Discuss;
Codex does not write arbitrary HTML.

## Verification

- `python3 -m unittest ecology_memory.tests.test_codex_native`: 10 passed.
- Idlisseus focused bridge, UI-source, transport and provider tests inside an isolated temporary
  tree in the existing application container: 35 passed.
- A headless Chromium render replayed the exact linked thread from the local session database at
  desktop and 390-pixel mobile widths. It produced two clean answers, **Why** summaries of two and
  one invoked skills, no raw Codex/path text, no duplicated answer, and no page errors.
- A live compatibility smoke turn returned one `Why · 1 skill used` prelude naming only
  `local-snake-inventory`, followed by the answer. The deployed renderer converted that exact
  payload to clean content and a structured audit panel.
- Both modified Python surfaces compile and both repository diffs pass `git diff --check`.
- The existing `hermes-live` and Idlisseus containers and every model server remained running.
  Only the lightweight Python bridge on port 7011 was restarted once to load its formatting code.

This was an integration repair, not a new parser benchmark epoch and not evidence for a saturation
claim. The frozen algebra, connector behavior, benchmark schemas, and skill catalog were unchanged.
