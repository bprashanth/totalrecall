# Evidence-chain and field-map benchmark

This benchmark tests whether Idli Insight can turn a model-suggested ecological lead into an
audited, data-backed action without treating model memory as evidence.

The required chain is:

```text
hypothesis/query seed
  -> query-bound discovery from admitted connectors or corpora
  -> retrieved papers, datasets or occurrence records
  -> explicit sample and environmental gates
  -> deterministic estimate or an explicit DataRequest
  -> plain-English result with provenance
  -> overlap map and precise field waypoints when spatial action is justified
```

The model may use its own knowledge to propose search terms or candidate taxa. A candidate becomes
actionable only after an admitted source returns it. Web text is not evidence unless it is ingested
as a cited source through an admitted connector. Spatial proximity is never evidence of dispersal,
avoidance, habitat use or temporal co-occurrence.

## Scope and isolation

- `questions.json` is frozen before the implementation run.
- Existing frozen ecology banks, IR schemas and connector result schemas are not modified.
- Each scored conversation starts with a fresh Idlisseus/Codex session. Turns within one
  conversation retain history and audited result handles.
- Live discovery calls are cached with query, connector, timestamp and source identifiers.
- Answers are scored from the user-visible response, audit JSONL and emitted artefacts.
- HTML maps must be self-contained or served from the authenticated Idlisseus artefact route. CSV
  and GeoJSON waypoints must contain the same point identifiers as the map.
- A missing estimator must end in a specific DataRequest and expose `Request this model from T4GC`;
  it must not be replaced with an unaudited narrative estimate.
- This is an operational benchmark and architecture comparison, not a saturation claim.

## Pass conditions

For a turn requiring a complete evidence chain:

1. The discovery query contains the user entity or a candidate explicitly labelled as a hypothesis.
2. Every asserted paper, dataset and occurrence has a connector/source identifier.
3. Candidate taxa used downstream occur in retrieved evidence, not only in model prose.
4. Each entity is estimated independently and records its sample-size and environmental gate.
5. The answer distinguishes observed, literature-reported, proxy and modelled evidence.
6. A map is emitted only from returned or modelled coordinates. It includes method, uncertainty,
   waypoint reason and stable audit/result identifiers.
7. Failed gates produce a precise collection request or T4GC model request.

## Benchmark arms

The initial arms are declared in `arms.json`. A run records exact model IDs, endpoint health,
prompt hashes, skill hashes, connector cache hashes and wall time. Backpedalling means the planner
may revise a failed admitted plan (for example, use observed points after an observed-overlap gate
rejects transfer); it never means bypassing a gate.

## Output layout

Each run directory contains:

```text
manifest.json
turns.jsonl
audit.jsonl
scores.json
screenshots/
artifacts/<conversation>/<turn>/{map.html,waypoints.geojson,waypoints.csv}
```

Screenshots cover chat activity, the compact Why panel, a successful map, a failed gate with model
request action, and responsive narrow/wide layouts.

## Run

The runner uses the already-running Idli Insight bridge and only observes declared model endpoints;
it never starts or restarts a model server.

```bash
# one-turn smoke across all available arms
python runner/run.py --run smoke-001 \
  --conversation eucalyptus-bird-evidence-chain --max-turns 1

# operational overnight stop protocol: two unchanged passes
python runner/run.py --run overnight-001 --passes 2

# reproducible score, latency and replay summary
python runner/summarize.py --run overnight-001
```

`codex-deepseek-v4` and `codex-lora9b004d` use the second model as an evidence verifier over the
Codex answer and compact audited skill material. A verifier may remove or qualify unsupported prose;
it cannot add evidence or bypass a connector gate. If an endpoint is unavailable, the arm records a
runtime failure and continues.

`codex-algebra-backpedal` is a prompt-only Codex arm: the runner prepends an instruction to choose
another admitted operation after a failed gate. It does not invoke the Algebra parser, controller or
a separate Algebra model. In both verifier arms, Codex performs all skill selection and execution
before the runner calls DeepSeek-V4 or local `lora9b004d`; those verifiers have no skill access.

The completed development run is reported in `runs/overnight-001/REPORT.md`. Its frozen raw scores
are preserved. A post-run deterministic relation repair is isolated in `runs/postfix-relation-001/`.
