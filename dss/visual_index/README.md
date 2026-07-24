# Visual-ready AOI index prototype

This directory is the dependency-light feasibility implementation for the companion Idlisseus
design,
[`VISUAL_FIRST_AOI_DATA_DESIGN.md`](../../../idlisseus/docs/VISUAL_FIRST_AOI_DATA_DESIGN.md).
It proves the logical tables and visual-view contracts against a maintained site pack. The
deployment-pinned bridge integration is documented in
[`../SITE_PACK_DEPLOYMENT.md`](../SITE_PACK_DEPLOYMENT.md).

Build:

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/valparai \
  --output /tmp/valparai-visual-index
```

Outputs:

- `site_index.sqlite` — canonical facts and materialised aggregates;
- `visual_bundle.json` — data for the tested visual contracts;
- `preview.png` — one static feasibility preview; and
- `build_report.json` — counts, elapsed build time and integrity result.

Run the regression tests:

```bash
python3 -m unittest dss.visual_index.tests.test_build -v
```

The code intentionally uses the Python standard library and Pillow already present on this host.
It is a proof of the logical contract, not a recommendation to use SQLite as the production
warehouse.

## Typed result service

`result_service.py` translates the pinned index into browser-neutral `idli-result/1` objects. It
does not interpret free text: a conversation layer selects a declared capability and binds typed
arguments. The current producer supports site orientation, entity and canonical hierarchy-group
record maps, explicit subject-object association maps and networks, coverage versus effort and
metric time series. It can also compare source-declared survey categories while mapping every
site and retaining explicit effort denominators, and map any cell-aligned feature-year while
retaining its unit, evidence class, source asset, scale and missing support. The group operation
takes a hierarchy rank and value rather than a site-specific list, so the same result grammar can
map a taxonomic class, an occupation sector or another pack-defined hierarchy. Interaction
adapters are equally generic but stricter: a source must expose the relation or an explicit join;
proximity never creates an edge. Stratified summaries are descriptive unless a separate
inferential design is declared. Environmental features remain context or predictor inputs rather
than occurrence evidence. A declared but incomplete transfer capability returns a structured
blocked result.

One-shot query:

```bash
python3 dss/visual_index/result_service.py \
  --site-pack dss/sites/valparai \
  --index /tmp/valparai-visual-index/site_index.sqlite \
  --state /tmp/valparai-result-state \
  --query '{"request_id":"demo-1","capability_id":"entity-record-map","arguments":{"entity":"lion-tailed macaque"},"question":"Where have lion-tailed macaques been recorded?"}'
```

Internal HTTP service:

```bash
python3 dss/visual_index/result_service.py \
  --site-pack dss/sites/valparai \
  --index /tmp/valparai-visual-index/site_index.sqlite \
  --state /tmp/valparai-result-state \
  --api-token-file /path/to/site-result-service.token \
  --host 127.0.0.1 \
  --port 7120
```

It exposes `POST /v1/results/query`, `GET /v1/results/{result_id}` and
`GET /v1/results/{result_id}/data/{handle}`. These are bridge/server endpoints, not public browser
URLs. Idlisseus should proxy authorised handles through its own same-origin API.

`PackSwapContractTest` builds the real Valparai pack and the synthetic Valparai livelihoods pack,
runs their declared typed question probes through this same service, validates both against the
shared schema and asserts that matching capabilities return identical renderer grammar.
