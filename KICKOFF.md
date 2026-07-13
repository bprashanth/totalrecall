# How to kick off an agent on a new sector (for the human)

## One-time
```bash
cd ~/src/github.com/bprashanth/totalrecall
chmod +x bootstrap.sh
```

## Per sector (e.g. livelihoods with codex 5.6)
```bash
./bootstrap.sh livelihoods          # creates livelihoods_memory/ with scaffold + instructions
cd livelihoods_memory
# start your agent IN THIS DIRECTORY. It will auto-read AGENTS.md; its full mission is PROMPT.md.
# A sufficient opening instruction to codex:
#   "Read PROMPT.md and execute the mission top to bottom. You are the engineer and judge;
#    the parser under test is the local 2B described there. Work autonomously, document as
#    you go, and don't stop until you have a REPORT.md with the head-to-head table."
```

## What the agent will need to do itself (by design)
- Find + verify its own sector data sources, and write connectors for them (PROMPT.md §4–5 gives
  the contract and exactly where the code hooks in: `harness/connectors.py` + one routing branch in
  `harness/executor.py::_route_select`).
- Author the seed question bank with gold trees, then widen it with the generator.
- Run the tick loop, judge equivalences, log spec proposals — WITHOUT editing the frozen spec.

## Running multiple sector agents in parallel — safe, with two rules
Each `<sector>_memory/` is a SNAPSHOT (bootstrap copies the kit at bootstrap time) with its own
caches, runs, and corpus — sectors share NOTHING on disk, so parallel runs cannot corrupt each
other. They do share two things: (1) the 2B parser at :8001 — vLLM batches concurrent requests, so
parallelism only costs throughput, never correctness; the hard rule (in AGENTS.md) is that no agent
may ever stop/restart it; (2) public API rate limits (Overpass/Nominatim) — each sector has its own
HTTP cache, expect the first census to be the slow part. Bootstrap AFTER the kit's latest sync if
you want the newest harness and saturation protocol. The snapshot is the isolation guarantee:
later kit changes don't touch an already-bootstrapped sector. Each new snapshot includes
`framework-lock.json`, recording the released proposal and protocol versions it inherited.

## Prerequisites on this box (check before starting an agent)
- 2B parser serving: `curl -s http://172.17.0.1:8001/v1/models` → `qwen3.5-2b`.
  (If the 122B is running instead: `docker stop vllm-qwen35 && cd ~/src/github.com/bprashanth/idlisseus && bash models/qwen3.5-2b/run.sh`)
- OpenRouter key present: `~/.config/idlisseus/openrouter.json` (for the deepseek gold author).

## Reintegration (the supervisor's job, not the sector agent's)
Each sector dir accumulates: `runs/` (traces, browsable via `runs/index.html`), `corpus/*.jsonl`
(concatenable across sectors; `meta.sector` distinguishes), `FINDINGS.md`, `spec-proposals.md`,
`chronology/`. The cross-sector supervisor (Fable, in heartwood/docs/architecture/memory) reads
spec-proposals from all sectors, reconciles the algebra, and merges corpus files for cross-sector
LoRA training — or trains per-sector LoRAs from single files where a sector's language is
idiosyncratic.

Sectors so far: `transport` (Fable replication subagent), `livelihoods` (reserved for codex 5.6).
