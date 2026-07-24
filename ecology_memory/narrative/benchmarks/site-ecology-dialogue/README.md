# Site-ecology dialogue benchmark

This benchmark tests an interactive ecology assistant across a realistic programme conversation,
not isolated question answering. It is deliberately site-pack agnostic: a run supplies an
organisation profile, AOI and resource manifest; skills receive those as arguments.

The architecture under test is:

```text
short Codex dialogue and clarification
  -> admitted local/public evidence retrieval
  -> immutable result snapshot + observed data-coverage map
  -> one precise scientific question
  -> Algebra 9B frozen IR
  -> trusted runtime validation, snapshot binding and deterministic execution
  -> observed/modelled/designed visual
  -> next question, field protocol, dashboard or report
```

Codex may use model knowledge to explain or suggest a search seed. It may not turn that seed into a
site claim. Algebra 9B never selects connectors or invents resources. It expresses the scientific
operation after Codex has admitted the entity, region and data. The trusted runtime validates and
executes; it does not choose the search radius, retry, map or next question. Evidence labels in the
UI are derived from audited execution.

## Coverage

The bank covers site orientation, ambiguous vernacular groups, sparse species transfer, nursery
planning, invasive recurrence, fire and vegetation proxies, restoration comparisons, ecological
interactions, repeated-detection survey design, soil/water questions, source outages, maps,
dashboards and reports: 12 conversations and 43 turns. Species names are examples, not routing
keys.

## Invariants

- A broad site question starts from the onboarded resource pack.
- Ambiguous groups produce one short clarification or an evidence-backed local shortlist.
- Retrieval precedes Algebra 9B; Algebra precedes a modelled map.
- Wider returned coordinates are always eligible for an observed data-coverage map, even when the
  transfer gate fails.
- Algebra `SELECT` leaves can bind to named immutable result snapshots without connector reruns.
- No returned points means a labelled spatial collection design, not invented presence.
- Occurrence density is not occupancy; proximity or overlap is not interaction.
- One time slice cannot produce a trend, and a proxy cannot become an ecological outcome.
- Connector failure cannot silently change the estimand or source family.
- Every map point has a stable ID shared by HTML, GeoJSON and field-sheet CSV.
- Dashboard and report claims link back to result IDs and audit turns.
- The first safe progress event should arrive quickly and long work exposes stage changes.

## Running

The runner uses the already-running bridge and never starts or restarts a model server.

```bash
python runner/run.py --run smoke-001 --conversation sparse-species-to-map --max-turns 3
python runner/run.py --run overnight-001 --passes 2
python runner/summarize.py --run overnight-001
```

An operational pass requires two unchanged runs with no critical failure, valid artefacts and less
than 0.02 movement in mean score. This is not a saturation claim.
