# Round 2 epoch 012 — H18 admission boundary

## Independent generation

H18 was authored after the epoch-012 freeze by Cursor Claude Opus 4.8 thinking-high-fast, an
Anthropic-family generator. The author was allowed to inspect the frozen v2.1 schema, connector
vocabulary, coverage matrix, and epoch manifest, but not the parser, traces, run output, or prior
holdout questions. It completed 52 candidates and was interrupted while attempting its own
self-check; the complete candidate file was then audited independently rather than trusting the
author's unfinished validation.

The main judge audited all 52 golds. A blind auxiliary audit covered rows 27–52 without inspecting
the parser or any run. Because the holdout protocol requires 40 rows, exclusions were based first
on invalid or inexpressible denotations, then on redundancy. The final mix deliberately retains
some simple controls alongside adversarial forms: 18 composite, 8 relation, 1 state/density,
1 change, 1 ranking, 3 transfer, and 8 ambiguity or explicit-source-gap rows.

## Pre-run adjudication

Twelve rows were excluded before first contact:

- `h18-030`: “right now” requests one latest scalar, but `SELECT(time:null)` returns a series.
- `h18-032`: “last couple of decades” does not license the invented 2003 boundary.
- `h18-037`, `h18-038`, `h18-041`, `h18-043`: the questions did not license the authored
  non-default transfer methods.
- `h18-047`: ownership grouping is explicit, not ambiguous, and v2.1 cannot group by a categorical
  connector field.
- `h18-027`, `h18-028`, `h18-031`, `h18-036`, `h18-042`: valid but redundant simple or envelope
  controls, removed to preserve more structural pressure.

Gold-only repairs before freezing were limited to completing the explicit “since 2005” interval,
orienting temporal differences as later-minus-earlier, using supported NUTS-2 aliases, and
classifying explicitly named unsupported measures as literal source gaps rather than invented
semantic holes. Mechanical metadata was regenerated from the schema. No parser, prompt, scorer,
executor, connector, or synthesis code changed.

The admitted bank is `questions/holdout-018.json`: 40 rows, SHA-256
`a5a3f5a986eef0b9f8cbacbfc974261137f618c46ee397c6e2040a31d959b85b`. This checksum is the
immutable pre-contact boundary. Any later gold or bank change invalidates H18.

## Framework discoveries before scoring

The audit itself produced two durable proposals without counting them as parser discoveries:

- `ALG-009`: exact series-point selection for requests such as “right now” or “latest value”.
- `ASK-002`: explicit unsupported entities remain literal source gaps and must not be converted
  into clarification holes.

H18 also independently corroborates `ALG-003` with an ownership-partition request. These remain
proposals for Codex/Fable review and are not silently merged into the frozen algebra.
