# Late-bound skills benchmark

Status: round 001 preregistered on 2026-07-21 and completed on 2026-07-22.  See
[`RESULTS.md`](RESULTS.md), `runs/round-001/scores.json`, and
`runs/round-001/metrics.json`.

This benchmark asks whether the released, cross-sector place algebra should be bound to data
sources before compilation, after compilation, or left to an ordinary skill-using agent.  It also
tests whether the promoted local 9B model can use the late-bound design and whether a frontier
agent without the local skill/data layer is already sufficient.

The five primary arms are frozen in `arms.json`:

1. `codex-capability-first` — GPT-5.4 selects current capability cards, compiles the admitted cards
   into the released algebra, receives deterministic execution, and writes the answer.
2. `codex-late-bound` — GPT-5.4 compiles before seeing skills.  BGE-small retrieves skill cards for
   the frozen algebra leaves, GPT-5.4 chooses among those candidates, code validates/binds them,
   and the deterministic executor runs the tree.
3. `codex-native-skills` — GPT-5.4 receives the same skills as executable Markdown procedures and
   may call them directly without emitting algebra.
4. `lora9b-late-bound` — promoted `merged-9b-003` follows the same late-bound protocol as arm 2.
   It is runtime-prompted with BUFFER even though its 3,895-row diet contains no BUFFER/FILTER
   rows; this is not a claim of v2.4-trained conformance.
5. `codex-naked` — GPT-5.4 receives only the ordinary questions and normal web access: no local
   algebra, capabilities, skills, datasets, connector descriptions, or EBTL evidence pack.

`questions.json` contains five simple-English NGO conversations plus one unsupported control.
Every arm sees one turn at a time and retains state only within that conversation.  The raw run
tree records prompts, model events/responses, pre-link algebra, semantic candidates and scores,
bindings, execution packs, tool calls, answers, timings, session IDs, and content hashes.

The Codex arms run in separate Docker filesystem views with a private `CODEX_HOME`; the repository,
other arms, scoring notes, and prior run outputs are not mounted.  Source aggregation occurs only
after every arm has finished.  The 9B endpoint is stateless, so the harness resends bounded
conversation history.

Run:

```bash
python3 ecology_memory/narrative/benchmarks/late-bound-skills/runner/run_round.py \
  --round round-001
```

This is a first-contact architecture probe, not a saturation claim.  No benchmark-driven change to
the frozen ecology algebra, connector set, or promoted model is permitted during the round.
