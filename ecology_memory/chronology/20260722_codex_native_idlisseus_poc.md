# Codex-native skills through Idlisseus

## Why

The first late-binding benchmark indicated that one resumable Codex CLI agent with native skill
files was the strongest tested arm. Before designing the next benchmark, we needed the winning
shape in a form a person could try through the existing Idlisseus browser, through an API, and
through a more detailed terminal trace.

## What was built

- An authenticated OpenAI-compatible bridge on port 7011.
- A shared Idlisseus endpoint named `Codex CLI · Native Skills` with model id
  `gpt-5.4-codex-native-skills`.
- One resumable Codex GPT-5.4 medium thread per Idlisseus session.
- The exact frozen 12-card skill catalog from the late-bound-skills benchmark, rendered as an
  index plus progressive-disclosure `SKILL.md` files.
- An allowlisted skill gateway backed by the deterministic executor.
- A structured SSE audit client and persistent raw Codex/skill logs.
- A frozen five-conversation manual question bank for the next POC.

Idlisseus remains the UI and session transport. Its Agent mode is not used: Codex CLI is already
the sole agent loop, so the browser should remain in Chat mode.

## Failure found during integration

The first host-run smoke test never invoked a skill. Codex's `workspace-write` sandbox failed
before every shell command because `bwrap` could not configure its namespace in this host
environment. The model noticed the failure and declined to invent an answer, but that was not the
benchmark architecture.

The corrected runner uses `docker exec` in the already-running `hermes-live` container. It does not
start, stop, or restart a container. Codex runs as uid/gid 65534 with a private directory under
`/tmp`; that user cannot traverse the Hermes data mount. Codex is unrestricted inside this
container boundary, matching the successful benchmark's native-skill behavior.

A second integration defect appeared on the first follow-up: Codex CLI 0.144.1 requires resume
options before the thread id and does not accept `-C` on `exec resume`. The bridge now relies on the
process working directory and uses the current resume argument order.

## Verification

The question `What animals and birds have people seen at EBTL?` caused Codex to:

1. inspect the frozen index;
2. select and execute the local fauna summary;
3. notice that the result did not contain complete species lists;
4. backtrack and add the bird and snake inventory skills;
5. separate 2024 observations, older property records, indirect elephant evidence, and missing
   non-bird lists in the answer.

The follow-up `What about snakes?` resumed the same Codex thread and reused the prior audited result
without an unnecessary connector call. A further OpenAI-compatible streaming check returned five
valid chunks, a visible trace, an audit id, and a final answer. Idlisseus's container can reach and
authenticate to the registered `/v1/models` endpoint.

Static verification:

```text
python3 -m unittest ecology_memory.tests.test_codex_native
Ran 5 tests — OK
```

## Boundary

This is safe enough for trusted-team experimentation, not public multi-tenant use. The bearer
token and allowlisted data gateway prevent direct arbitrary calls, and the agent runs as an
unprivileged container user, but the existing Hermes container has outbound network access and a
general shell. A public deployment needs a dedicated long-lived runner with no unrelated mounts
and explicit egress restrictions.
