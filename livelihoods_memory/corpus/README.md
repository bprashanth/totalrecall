# Training corpus (auto-compiled by compile_corpus.py)

- `parse.jsonl` — 1088 verified (question → IR) pairs in chat format, across sectors.
  A row is included only if the tree validates AND its execution matched the expected outcome
  class in a benchmark run. When the small parser's own tree scored perfect, that tree is used
  (self-training signal); otherwise the validated gold.
- `clarify.jsonl` — 5 multiturn rows (holed tree → rendered clarifying question →
  user reply → bound tree). Binding is mechanical; these teach turn-1 hole placement.
- System prompt = the live parser prompt (parser.SYSTEM) at compile time; recompile after prompt
  changes: `python3 harness/compile_corpus.py`.
