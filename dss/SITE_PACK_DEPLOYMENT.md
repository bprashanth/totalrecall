# Deploying Totalrecall site packs through Idlisseus

Status: proof-of-concept deployment contract.

Site data has one home: `totalrecall/dss/sites/<site-id>/`. Idlisseus owns the chat UI and endpoint
registry, but it does not own or copy the source pack. The Codex-native bridge reads the selected
Totalrecall pack and builds a disposable, derived visual index under that bridge instance's state
directory.

## POC choice: pin one site per bridge process

The first implementation deliberately does not change site merely because a place name appears in
a prompt. Run one bridge process per site, with its own:

- site pack and aliases;
- port;
- process/session/cache state;
- public model id; and
- Idlisseus endpoint name.

One Idlisseus installation can register all of these endpoints. A user selects the appropriate
model in the existing model selector. This gives the POC site isolation without deploying another
copy of the UI.

The registry at [`sites/registry.json`](sites/registry.json) records aliases and suggested
deployment values. It is documentation and configuration inventory in this version; the bridge
does not silently route a running conversation from it.

## Valparai example

From the Totalrecall repository root:

```bash
python3 ecology_memory/integration/codex_native/setup_idlisseus.py start \
  --state ecology_memory/integration/codex_native/runs/service-valparai \
  --port 7012 \
  --site-pack dss/sites/valparai \
  --public-model idli-insight-valparai \
  --endpoint-name "Idli Insight — Valparai"
```

The start command:

1. validates `site.json` and `sources.json`;
2. runs the generic visual-index builder;
3. writes the derived SQLite index and build report below
   `runs/service-valparai/visual-index/`;
4. starts a bridge pinned to the pack, profile, aliases and index; and
5. registers `idli-insight-valparai` in the existing Idlisseus endpoint database.

The source CSV, KML and metadata files remain in Totalrecall. Derived state can be rebuilt from the
pack and must not be treated as a second source of truth.

Inspect or stop that instance with the same state and port:

```bash
python3 ecology_memory/integration/codex_native/setup_idlisseus.py status \
  --state ecology_memory/integration/codex_native/runs/service-valparai \
  --port 7012

python3 ecology_memory/integration/codex_native/setup_idlisseus.py stop \
  --state ecology_memory/integration/codex_native/runs/service-valparai
```

The existing EBTL instance remains compatible with its current command and defaults. It can
continue to use port `7011` and model id `idli-insight`; no `--site-pack` argument is required for
the legacy profile.

## What the site-pack POC supports

For a visual site pack, the bridge can currently:

- answer a broad site-overview request from the declared AOI, source registry and index report;
- resolve exact or partial entity aliases against the pack;
- return source-linked observed events with coordinates, date, uncertainty and immutable source
  row;
- keep a registry miss distinct from evidence of absence; and
- expose the result through the existing chat audit trail.

The generic pack does not yet enable all legacy modelling, remote-layer or rendered-map workflows.
Those paths are reported as a capability gap instead of borrowing the other site's configuration.
The visual bundle and preview prove the data contract, but the chat renderer still needs a generic
visual-result adapter.

## Why not switch on an AOI mention yet?

Prompt text is not a sufficient tenancy boundary. A question may mention several places, compare a
target with a donor region, or change subject mid-conversation. The current bridge also contains
older connectors and renderers whose base layers and defaults are tied to the legacy profile.
Automatic mention routing now would make accidental cross-site evidence more likely.

A production single-endpoint design should:

1. resolve a site from an authenticated organisation/site registry when a session starts;
2. ask when aliases are ambiguous instead of guessing;
3. pin `organisation_id` and `site_id` in session state;
4. pass explicit site/result handles into every connector, skill and renderer;
5. prevent silent site changes during the session; and
6. keep derived indexes and caches partitioned by site-pack digest.

That design can still use language reasoning to understand the user's question. The registry and
session pin decide which data plane the reasoning is allowed to inspect.

## Validation

Rebuild and test the generic index with:

```bash
python3 -m unittest dss.visual_index.tests.test_build -v
```

The setup command can be inspected without mutating a running service:

```bash
python3 ecology_memory/integration/codex_native/setup_idlisseus.py --help
```
