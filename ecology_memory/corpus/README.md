# Training corpus (auto-compiled by compile_corpus.py)

- `parse.jsonl` — 270 verified (question → IR) pairs in chat format.
  A row is included only if the tree validates AND its execution matched the expected outcome
  class, shape, hole, estimate, and grounding requirements in an allowlisted benchmark run. The
  row always uses the small parser's own verified tree; a gold fallback is never silently trained.
- `clarify.jsonl` — 5 multiturn rows (holed tree → rendered clarifying question →
  user reply → bound tree). Binding is mechanical; these teach turn-1 hole placement.
- System prompt = the live parser prompt (parser.SYSTEM) at compile time; recompile after prompt
  changes: `python3 harness/compile_corpus.py`.
- Admission allowlist = `verified-runs.json`; verified runs: active-040, active-005-mt.
