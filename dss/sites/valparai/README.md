# Valparai visual site pack

[`capabilities.json`](capabilities.json) declares the site-agnostic typed operations currently
supported by the real index. `dss/visual_index/result_service.py` binds those operations to this
pack and emits `idli-result/1`; Idlisseus does not consume `visual_bundle.json` directly.

Status: first feasibility implementation of `visual-site-pack/0.1`.

This site pack consolidates the source files, AOI roles, aliases, source adapters and question
probes used to test the future visual-first data design. It can be exposed through the
deployment-pinned chat POC described in
[`../../SITE_PACK_DEPLOYMENT.md`](../../SITE_PACK_DEPLOYMENT.md).

## Contents

```text
site.json       AOI roles, aliases and named points
sources.json    source registry, rights and schema-driven adapters
questions.json  representative question-to-first-visual probes
raw/            immutable attributed source subsets used by the prototype
derived/        reproducible, source-digested feature and indicator planes
methods/        verified external method code and auditable method cards
```

The target geometry is the published Valparai Plateau study envelope, not a parcel or ownership
boundary. Organisation-supplied KML/GeoJSON should replace or supplement it during onboarding.

## Build and test

From the Totalrecall repository root:

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/valparai \
  --output /tmp/valparai-visual-index

python3 dss/visual_index/derive_grouped_indicators.py \
  --site-pack dss/sites/valparai \
  --recipe dss/sites/valparai/derived/restoration_plot_indicators_v1/recipe.json \
  --output-csv dss/sites/valparai/derived/restoration_plot_indicators_v1/plot_indicators.csv \
  --manifest dss/sites/valparai/derived/restoration_plot_indicators_v1/manifest.json

python3 -m unittest \
  dss.visual_index.tests.test_derive_grouped_indicators \
  dss.visual_index.tests.test_build \
  dss.visual_index.tests.test_result_service -v
```

The current build indexes:

- 21 source records, including a reproducible multi-asset feature cube and a derived
  plot-indicator source;
- 45,328 source-linked events, including 3,199 regeneration rows and 10,752
  restoration-study bird/tree records;
- 42,348 georeferenced events;
- 1,145 resolved or retained broad entities and 1,893 aliases;
- 205 named/source locations, including 44 acoustic-recorder sites;
- 974 explicit effort rows, including 460 fifteen-minute bird point counts and 264
  declared 0.04-hectare adult-tree or regeneration plots;
- 71,595 typed weather, canopy, carbon, tree-structure, seed-fate, bird and habitat measurement rows,
  including 17 method-linked indicators for each of 132 restoration/reference plots;
- 5,622 explicit visitor–focal-tree or animal–seed-experiment association rows; and
- 28,764 finite 2024 Earth-observation feature values across 97 available features, with
  832 cloudy-season gaps retained as missing; and
- 132,096 site-level acoustic-space-use matrix values across 43 recorder sites, 24 hourly
  windows and 128 frequency bins; and
- 302 spatial cells.

The typed result service can map a single resolved entity or a broad canonical hierarchy value.
For example, `{"rank":"class","group":"Amphibia"}` maps each amphibian record with its member
entity retained. It does not collapse mixed protocols into a comparative abundance claim.
The interaction capability likewise requires a source-declared subject and object. It can render
the seed-experiment camera detections as a linked map and network, but it does not call every
detection predation or infer an interaction from two nearby points.
The stratified survey capability maps source-declared sites and compares categories while keeping
site replication and survey effort visible. Its summaries are descriptive observation-process
results; they are not silently promoted to treatment effects or population estimates.
The cell-feature capability maps any indexed feature-year through the same typed operation and
keeps unit, evidence class, source asset, scale and missing support in the result. Environmental
surfaces remain context or model inputs; they never become presence records.
The plot-indicator capability maps a unit-compatible derived or observed measurement and returns
category distributions with the map. Its generic binding is metric, source and category-property;
the operation itself contains no Valparai treatment names or indicator formulas. Formulae,
denominators and gates remain in the source-linked recipe and method cards.
The matrix capability groups any compatible source-linked x/y matrix by a declared category and
keeps contributing sites on a supporting map. For the acoustic source it exposes frequency-time
patterns and recorder coverage; within-site scaling and the distinction between soundscape
activity and bird detections remain explicit limitations.
The method-catalog capability exposes source-linked inputs, implementation state, uncertainty,
gates and claim limits. It is an analysis-design lookup, not a model run, and lets the dialogue
layer explain what can be executed, what needs a wider data search and what still needs a model
request. It now includes pinned State of India's Birds references for effort-visible range maps
and reporting-rate trends, while keeping their national/state thresholds out of site defaults.
The seasonal-surface capability binds an ordered feature series declared by the pack to a
peak-step map and a coverage-aware median and 10th–90th percentile profile. The first admitted
series uses the twelve cloud-masked 2024 Sentinel-2 NDVI composites. It explicitly does not turn
remote-sensing context into a field observation, biological event date or multi-year trend.

Seventeen typed probes are immediately executable, alongside five visual-contract probes awaiting
their next producer operation. Transfer now produces a versioned all-axis AlphaEarth
environmental-analogue screen, spatial support gates, observed donor points and unsupported
target cells. It remains partial because similarity has not passed an effort-aware predictive
discrimination gate. Expected-value collection
mapping is blocked because there is no versioned uncertainty surface or action-cost layer.

## Important data findings

- The three presence datasets use scientific names, underscored common names and spaced common
  names. Explicit crosswalks and aliases are required; simple string grouping splits the same
  entity.
- Several source rows use broad labels at different hierarchy levels. The index retains them
  rather than pretending every row is at the same rank.
- The GBIF frugivory archive contains visitor and focal-tree occurrences but does not retain the
  animal-to-tree join on visitor rows. The richer cited Dryad tables are therefore still required
  before rendering a plant–frugivore network. By contrast, the seed-experiment event identifier
  explicitly names the focal seed species; 745 camera rows can be linked, while three redacted
  event identifiers remain ordinary occurrence rows.
- Presence records and explicit survey effort come from different planes. The builder never
  manufactures effort from the number of presence rows.
- One plot dataset stores entities and coordinates in separate files joined by point id. All 3,684
  plot rows join to their source locations.
- Some records lie outside the target study envelope. They remain visible as context/donor data
  rather than being discarded or described as target observations.
- The available long metric series is suitable for time visuals. Event counts by year are coverage
  visuals, not population trends.
- 12,810 georeferenced event rows are outside the target envelope; 14,959 are inside it.
- Twenty-five opportunistic effort rows have no matching route geometry. They remain explicit
  effort records but cannot appear in a cell-level effort map.
- Fifteen event rows have no usable coordinates. They remain queryable through source and time
  fields instead of being dropped.
- Upstream natural keys are reused in 14 rows. Stable event ids therefore include the immutable
  source-row locator as well as the source's identifier.
- The 2024 source metadata describes a name crosswalk that is absent from the local source subset.
  Those common names resolve only when an earlier admitted crosswalk matches; other labels remain
  unresolved rather than being guessed.

See [`raw/README.md`](raw/README.md) for source attribution and licence details.

## Idlisseus operations

The proof-of-concept deployment is one site-pinned bridge. It reads this pack in Totalrecall,
builds disposable serving state under `runs/insight-valparai/`, and registers the public model
`idli-insight-valparai` as **Idli Insight — Valparai**. It does not copy pack data into
Idlisseus.

Use Idlisseus's virtual-environment Python for the launcher: endpoint registration imports the
Idlisseus database package and its dependencies.

```bash
TOTALRECALL_REPO=/home/beeps/src/github.com/bprashanth/totalrecall
IDLISSEUS_REPO=/home/beeps/src/github.com/bprashanth/idlisseus
IDLISSEUS_PY="$IDLISSEUS_REPO/chatbots/odysseus/venv/bin/python"
VALPARAI_LAUNCHER="$TOTALRECALL_REPO/ecology_memory/integration/codex_native/setup_idlisseus.py"
VALPARAI_PACK="$TOTALRECALL_REPO/dss/sites/valparai"
VALPARAI_STATE="$TOTALRECALL_REPO/runs/insight-valparai"
```

Start or register only the Valparai endpoint:

```bash
"$IDLISSEUS_PY" "$VALPARAI_LAUNCHER" start \
  --idlisseus "$IDLISSEUS_REPO/chatbots/odysseus" \
  --site-pack "$VALPARAI_PACK" \
  --state "$VALPARAI_STATE" \
  --host 172.17.0.1 \
  --port 7012 \
  --public-model idli-insight-valparai \
  --endpoint-name "Idli Insight — Valparai"
```

`172.17.0.1` exposes the bridge to the existing Idlisseus container without opening a new public
listener. Port 7011 is the separate live EBTL endpoint and must not be restarted by these commands.

Status and health:

```bash
"$IDLISSEUS_PY" "$VALPARAI_LAUNCHER" status \
  --state "$VALPARAI_STATE" --port 7012

curl -fsS http://172.17.0.1:7012/health
```

Stop only this endpoint:

```bash
"$IDLISSEUS_PY" "$VALPARAI_LAUNCHER" stop --state "$VALPARAI_STATE"
```

After a pack or producer-code update, stop and start this endpoint with the same state directory.
The start command rebuilds the serving index and updates the existing Idlisseus endpoint record.
Refresh Idlisseus and select **Idli Insight — Valparai** for a new chat.
