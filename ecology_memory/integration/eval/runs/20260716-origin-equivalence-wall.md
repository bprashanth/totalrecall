# Origin versus typed Hermes: connector-equivalence wall

Date: 2026-07-16  
Baseline: the literal `/home/beeps/src/github.com/bprashanth/idlisseus/agents/hermes/chat.sh`
selected by `--runtime untyped --context ebtl --model deepseekv4`  
Candidate: `integration/chat.sh --runtime typed --context ebtl --model qwen2b`

## What “equivalent” means here

There are four separate claims; a green result in one column does not imply the others.

1. **Shell parity:** both arms use Hermes sessions, clarification, resume, and the EBTL context.
2. **Implementation parity:** the typed route calls the same hash-locked origin connector source,
   not a rewritten Earth Engine/API algorithm.
3. **Query parity:** AOI, time, metric, and spatial grain have the same meaning.
4. **Answer efficacy:** the answer reports the executed result, separates evidence classes, and
   does not add unsupported ecological claims.

The typed runtime intentionally does not reproduce free-form terminal exploration. It dispatches
one registered `typed_evaluate` tool, whose executor calls locked connector functions with governed
arguments. Therefore Hermes's session footer reports **zero model-authored tool calls**, while the
same turn visibly prints the real connector events, for example:

```text
┊ 🧮 typed_evaluate  answer
┊ 🔌 origin.fire.points  0 rows
┊ 🔌 origin.fire.exposure  1 rows
```

The footer and connector trace count different things. No synthetic tool-call messages were added
to Hermes's database merely to change the footer.

The one-shot `--trace-json` diagnostic also executes inside this deployed container. A verification
trace for elephant records reports both connector events and five discovery cards, matching the
normal conversational route rather than depending on a different host embedding environment.

## Matched wall

| Topic | Typed production execution | Origin execution | Result |
|---|---|---|---|
| Fire exposure | Exact `fire.points` over the EBTL bbox plus exact `fire.exposure` at 5 km | Exact `fire.points` over EBTL, then an agent-selected corridor | Implementation parity. Typed keeps exact-AOI locations separate from buffered pixel-fire-days and does not call either a forecast. |
| Elephant evidence | Exact `points.get` over EBTL; on empty, exact `discovery.search` over embedded corpus cards | Exact `points.get`, `discovery.search`, then agent-selected donor-belt queries | Local lookup/discovery parity. Typed stops at a coverage gap and treats the five semantic hits as unverified leads. Origin usefully explored donors but later mixed incompatible spatial and evidence claims. |
| Land cover | Exact `landcover.classify` at the declared centre plus exact `area_by_class` over the analysis bbox | Exact `landcover.area_by_class` over the same bbox | Source/value parity. Typed names both grains and says neither is the 70-acre property polygon. |
| Restoration change | Exact `greenness.trend` for the 250 m centre pixel, 2019–2024 | Exact `greenness.trend` over model-generated site/corridor samples, 2019–2025 | Function parity, deliberately different declared grain. Typed reports a point proxy and refuses whole-property or causal attribution. |
| Snakes | Imported, page-addressed EBTL Faunal Survey 2024 inventory | Origin occurrence/discovery exploration | Deliberate source improvement, not parity. Typed returns all 14 documented species and distinguishes 3 survey encounters from 11 earlier property records. Origin missed the local PDF and suffered a GBIF taxon-key/category failure. |

The copied connector directory is an exact mechanical mirror of origin `dss/connectors` (excluding
Python caches), and admitted files are checked against `integration/manifests/origin-lock.json`
before import. Thin adapters currently cover `fire`, `landcover`, `greenness`, `points`, and
`discovery`; copying the directory does not by itself make every connector an admitted typed
operation.

## Trace evidence and latency

Latency is wall-clock for all turns in each case. It is diagnostic, not a controlled model-speed
benchmark: the origin arm lets DeepSeek freely inspect help, write intermediate files, retry
commands, and choose extra analyses, while typed Qwen executes a bounded plan.

| Case | Typed | Origin | Typed connector signal | Origin final session tool count |
|---|---:|---:|---|---:|
| Fire | 41.874 s | 99.937 s | `origin.fire.points`, `origin.fire.exposure` | 14 |
| Elephant | 30.488 s | 228.045 s | `origin.points.get`, `origin.discovery.search` | 41 |
| Land cover | 26.828 s | 78.085 s | `origin.landcover.classify`, `origin.landcover.area_by_class` | 8 |
| Restoration | 23.301 s | 219.241 s | `origin.greenness.trend` | 43 |
| Snakes | 25.026 s | 555.973 s | `published-taxon-inventory` | 56 |

Artifacts:

- Fire: [`20260716-221403-site_fire_risk.json`](20260716-221403-site_fire_risk.json)
  (updated typed) and [`20260716-220057-site_fire_risk.json`](20260716-220057-site_fire_risk.json)
  (literal origin arm).
- Elephant: [`20260716-222721-site_elephant_evidence.json`](20260716-222721-site_elephant_evidence.json)
  (updated typed) and [`20260716-220825-site_elephant_evidence.json`](20260716-220825-site_elephant_evidence.json)
  (literal origin arm).
- Land cover: [`20260716-221430-site_landcover_limits.json`](20260716-221430-site_landcover_limits.json)
  (updated typed) and [`20260716-221245-site_landcover_limits.json`](20260716-221245-site_landcover_limits.json)
  (literal origin arm).
- Restoration: [`20260716-222028-site_restoration_proxy.json`](20260716-222028-site_restoration_proxy.json)
  (both arms).
- Snakes: [`20260716-222554-site_snake_inventory.json`](20260716-222554-site_snake_inventory.json)
  (updated typed) and [`20260716-211107-site_snake_inventory.json`](20260716-211107-site_snake_inventory.json)
  (literal origin arm).

## Efficacy findings

The production origin remains better at open-ended exploration: it reads connector cards, discovers
available commands, widens searches, and proposes next actions. That behavior is also the source of
most failures in this wall:

- time-window drift between tool invocation and final prose;
- treating active-fire exposure as risk rather than a historical proxy;
- changing the nearest elephant record from roughly 50–70 km to 6.4 km on a later turn;
- conflating an ~8.7 km² analysis bbox with the 70-acre property;
- calling WorldCover classes observed ground conditions and attaching unsupported restoration
  interpretations;
- treating a 2021-era WorldCover product as a 2024 comparison layer;
- implying site-wide or causal restoration progress from model-selected satellite samples.

The typed route is materially stronger on reproducibility, provenance, evidence labels, dialogue
correction, and stopping at the evidence boundary. It is weaker at autonomous follow-on analysis:
it will not widen an AOI, extract a semantic hit, or launch transfer unless that step is represented
and passes the algebraic gate.

## Import incompatibilities still open

1. Origin `points.py` is now the actual occurrence merger, but its cached common CSV drops source
   record URLs, licenses, quality flags, and full dates. The exact adapter cannot honestly claim
   that its returned rows are license-filtered. This is the most important back-integration issue:
   enrich the origin common point schema or hydrate candidates through an evidence-preserving
   adapter before admitting them to redistribution/training.
2. `points.get` has no time argument. Typed time-bounded occurrence requests fail closed rather
   than silently ignoring the constraint.
3. Semantic `discovery.search` supplies ranked dataset cards, not observations. Dynamic category
   discovery is only complete when a selected card can be extracted, spatially checked, typed, and
   either admitted as local evidence or routed through an explicit transfer gate.
4. Only five copied connector modules have typed adapters in this wall. Terrain, water, eBird,
   literature extraction, prediction, and the remaining production connectors still need contract
   adapters and matched cases before global connector equivalence can be claimed.
5. The local Qwen endpoint still cannot perform Hermes-native automatic tool calling. The governed
   dispatch works around that limitation without granting the 2B arbitrary terminal access; a real
   LoRA head-to-head cannot run until its advertised model ID exists.

## Stop condition for this integration slice

This wall is complete when every selected topic has a resumed Hermes multi-turn trace, the candidate
either calls the exact locked production function or records a justified source improvement, the
answer survives evidence/scale review, all contracts pass, the connector mirror remains unchanged,
and the origin worktree stays clean. Those conditions now hold for the five-topic slice.

The broader project stop condition is **not** met. Global parity requires adapters and matched cases
for the remaining admitted connectors; model superiority requires a deployed 2B LoRA and untouched,
parser-blind banks scored against DeepSeek on correctness, grounding, dialogue, latency, brevity,
and cost.
