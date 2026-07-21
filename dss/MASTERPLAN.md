# DSS master plan — one conversational entrypoint over sector and place packs

Status: **design only**. This document authorizes no runtime migration, connector rewrite, model
deployment or serving change.

## Goal

Provide one stable command for the current conversational data system while keeping four axes
independent:

```bash
dss/chat.sh --sector cc --place ebtl --runtime typed --model latest
```

The same entrypoint should later support `livelihoods` and `transport`, additional named places,
and controlled typed/untyped/no-algebra/origin comparisons. `cc` is the canonical user-facing
alias for the current ecology sector; `ecology` remains an accepted compatibility alias so corpus
and provenance paths do not need disruptive renaming.

Initial defaults may remain `sector=cc`, `place=ebtl`, `runtime=typed`, `model=latest`, but defaults
must be visible in the startup banner and trace.

## Architectural boundary

Do not move the present sector shell and add conditionals. Promote its reusable conversation and
audit machinery into DSS, then load declarative sector and place packs:

```text
user turn
  → chosen place + sector packs
  → semantic capability selection
  → algebra compiler
  → versioned validator
  → deterministic connector registry/executor
  → evidence/provenance audit
  → concise responder
  → Hermes session and /why ledger
```

The LLM is the synthesis/compiler layer, not the connector registry. Training teaches linguistic
and algebraic behavior. Live connector availability, schemas and source policy remain runtime
declarations.

## Proposed layout

```text
dss/
  chat.sh
  runtime/                 shared selector/compiler/executor/responder/bridge
  profiles/                tested role combinations and experimental overrides
  models/latest.json       promoted bundle pointer and algebra compatibility
  places/ebtl.json
  places/erode.json
  sectors/cc/
  sectors/livelihoods/
  sectors/transport/
```

Each sector pack owns capability declarations, connector adapters, resolver aliases, output field
schemas, evidence/grain rules, source/license/auth metadata, response constraints and tests. Each
place pack owns names and aliases, geometry and its accuracy class, administrative hierarchy, the
meaning of “here”, local dataset bindings and sector-specific scope restrictions.

Place data must never blur spatial grains. A declared property polygon, geocoded administrative
bbox, approximate BUFFER bbox, raster pixel and regional donor belt remain distinct supports.

## Connector selection

Every capability receives a stable internal ID, for example `cc:taxon-occurrences`,
`transport:bus-stops`, or `shared:osm-amenities`. The selector returns the smallest sufficient set
of IDs. The compiler still emits source-independent algebra such as `SELECT(entity="bus stop")`.

At execution time, the registry asks declared resolvers whether they can satisfy each SELECT under
the chosen pack and place:

- one admitted match executes;
- no match returns a precise DataRequest;
- incompatible multiple matches ask for clarification;
- a multi-source union occurs only when a capability explicitly declares merge and deduplication
  semantics.

Connector/API names do not enter the algebra. The execution trace records the selected capability,
actual connector, parameters, counts, evidence label and spatial/temporal support.

Adding ordinary data or a connector should update a pack and its tests, not require retraining.
Retraining is reserved for a parser-visible algebra change or a demonstrated recurring compiler
failure that catalog/lexicon changes cannot solve.

## Runtime meanings

- `typed`: capability selection → algebra → deterministic connector execution → audited answer.
- `untyped`: Hermes chooses tools exposed by the same sector pack without typed algebra, enabling
  an apples-to-apples data comparison.
- `no-algebra`: model plus explicitly selected place description, with no project connectors or
  project data.
- `origin`: exact legacy stack where one exists; initially only the current CC/EBTL baseline.

Do not silently call an origin stack “untyped” for one sector while using a different architecture
for another. Preserve `origin` as its own explicit comparison arm.

## Place selection

`--place <registered-id>` binds deictic references such as “here” for the complete session. A
literal geocodable place may be supported later, but its derived bbox must be labeled and cannot
inherit site-only datasets. Registered IDs such as `ebtl` and `erode` are the first implementation
targets.

The current `--context` flag may remain temporarily as a deprecated alias for `--place`. Session
resume must reject a conflicting sector/place/model/algebra tuple rather than silently rebinding
old evidence.

## Model and algebra bundles

`--model latest` resolves through a manifest, never a shell constant. A promoted entry records:

- served role/endpoint and model/adapter identity;
- algebra version carried by the model;
- supported runtime roles and context limit;
- trained corpus strata;
- promotion evidence and rollback identity.

An incompatible model/algebra pair fails during preflight. Experimental `--selector`, `--compiler`,
`--responder` and `--algebra` overrides remain available, and every trace records their resolved
values.

## Update protocol

For a connector or dataset:

1. add an adapter and capability declaration;
2. declare output kind, fields, grain, evidence, scope, license, authentication and freshness;
3. run live phantom checks and fixture tests;
4. add place-specific and general paraphrase/multi-turn cases;
5. run typed execution, untyped availability and cross-sector collision tests; and
6. publish the pack without changing the model unless compiler evidence independently requires it.

For a model/algebra bundle:

1. freeze the parser-visible algebra;
2. mint and execution-verify development corpus;
3. freeze an unseen evaluation wall before training;
4. train a versioned candidate;
5. pass new-surface conformance and released-surface regression;
6. run matched multi-turn typed/untyped/no-algebra/origin comparisons where applicable; and
7. update `latest.json` only after promotion, preserving rollback.

## First implementation slice

Keep the first slice intentionally small:

1. create shared `dss/chat.sh` and shared runtime ownership;
2. extract the current CC implementation into a pack without changing its behavior;
3. extract EBTL into a place pack;
4. preserve the old shell as a forwarding compatibility shim;
5. support explicit `cc`, `livelihoods`, and `transport` choices, plus EBTL and Erode place packs;
6. keep `--sector all` disabled until at least two packs pass capability-ID collision and evidence-
   boundary tests; and
7. prove the existing EBTL typed and exact-origin regression conversations before adding features.

## Acceptance conditions

The migration is complete only when the old explicit EBTL commands produce equivalent traces and
answers through the new entrypoint, connector routing is pack-owned rather than hardwired in the
shell, place binding survives multi-turn resume, `/why` exposes actual audited calls, and adding a
new pack requires no edit to shared routing code.

