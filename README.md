# totalrecall

Totalrecall is the producer and evaluation repository for place-based evidence systems. It holds
the reusable authoring kit, immutable site packs, ingestion and analysis services, benchmark
memory, and the Fieldnote visual-first application. Idlisseus is a separate chat-first consumer;
both applications can use the same site-pack service and `idli-result/1` contract.

## Repository map

```text
totalrecall/
├── dss/
│   ├── sites/             admitted site packs: identity, sources, adapters and capabilities
│   ├── ingestion/         site onboarding, dataset admission, adapters and schema evolution
│   ├── connectors/        reusable acquisition connectors
│   ├── visual_index/      canonical index builder, typed capabilities and result services
│   └── integration/       Totalrecall-owned proposals to consumer repositories
├── ux/                    Fieldnote application, server routes and R visualisation sidecar
├── kit/                   reusable onboarding, conformance and benchmark-authoring machinery
├── benchmarks/            cross-model and multi-turn acceptance scenarios
├── ecology_memory/        domain memory, experiments and evaluation history
├── livelihoods_memory/    domain memory, experiments and evaluation history
├── transport_memory/      domain memory, experiments and evaluation history
├── runs/                  generated serving indexes and local runtime state
├── tests/                 repository-level tests
├── governance/            decisions, evidence and reviews
├── handoff/               bounded hand-off material for follow-on work
└── scripts/               repository operations and validation helpers
```

The durable product boundary is:

```text
immutable source + reviewed adapter
        -> site-pack index and registered capability
        -> idli-result/1
        -> Fieldnote, Idlisseus or another compatible consumer
```

- Site data, source meaning, analytical validity and result lineage belong in `dss/`.
- Fieldnote is the application under `ux/`; it is not the whole Totalrecall repository.
- Benchmark and memory directories help build and test packs but are not browser-serving APIs.
- Large original files remain in their admitted site pack or referenced immutable storage.
  Disposable SQLite indexes and result payloads are rebuilt under `runs/`.
- Consumer UI changes are coordinated through `dss/integration/`; pack development must not
  hard-code site or sector vocabulary into a consumer.

## DSS site packs

Place-specific source data and visual indexes live under [`dss/`](dss/). See
[`dss/ingestion/ON_BOARDING.md`](dss/ingestion/ON_BOARDING.md) for the entry point to site
onboarding, dataset admission, adapters and schema evolution,
[`dss/SITE_PACK_DEPLOYMENT.md`](dss/SITE_PACK_DEPLOYMENT.md) for the deployment-pinned Idlisseus
POC, [`dss/SITE_PACK_AUTHORING.md`](dss/SITE_PACK_AUTHORING.md) for the authoring contract, and
[`dss/sites/registry.json`](dss/sites/registry.json) for the current site inventory.

## Fieldnote

Fieldnote is the visual-first site-pack consumer in [`ux/`](ux/). Its runtime and operating
instructions are in [`ux/README.md`](ux/README.md), and its source-to-visual path is described in
[`ux/DATA_PIPELINE.md`](ux/DATA_PIPELINE.md).
