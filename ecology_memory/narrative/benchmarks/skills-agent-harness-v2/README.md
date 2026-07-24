# Skills × agent-harness POC

This POC asks whether executable skills repair the estimation failures documented in the ecology
narrative, and then separates skill quality from agent-harness quality.

The frozen manual bank is `questions.json`.  It has five short conversations covering repeated
fits, phantom trends, failed transfer, regional-to-local mechanism claims, and spatial proximity.
Questions never mention algebra, connectors, gates, skills, or benchmark internals.

The first interactive arm is the previous winner:

```text
Idlisseus frontend -> Codex CLI GPT-5.4 medium -> native SKILL.md procedures
                    -> allowlisted skill gateway -> deterministic executor -> audited answer
```

Idlisseus is a transport and UI in this arm.  Its own LLM agent loop should stay off; Codex CLI is
the agent.  The OpenAI-compatible bridge includes a compact live trace in the answer so the stock
Idlisseus frontend can display skill discovery, reads, invocations, repairs and calculations
without a frontend fork.

Run and setup instructions live in `../../../integration/codex_native/README.md`.

## Isolation contract

- The question bank, skill cards and runtime hashes are recorded before scored runs.
- One fresh Codex session and workspace is used per conversation.
- Only turns within a conversation share history.
- The agent sees the skill index and selected `SKILL.md` files, not narrative, scores or other runs.
- Registered skills are immutable during a scored run.
- Proposed or improvised skills are quarantined and cannot affect a later arm.
- Skill-enabled arms do not receive public-web search.
- Every Codex JSONL event and every skill request/result is retained server-side.

This manual POC is evidence for architecture choice, not a saturation claim.
