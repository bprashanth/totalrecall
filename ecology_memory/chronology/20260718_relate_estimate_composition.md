# 2026-07-18 — RELATE/ESTIMATE composition repair

## Failure that forced the change

The typed runtime could answer declared one-card questions but repeatedly returned `no_connector`
or a single `SELECT` for questions that required composition. The immediate examples were:

- compare two named taxa across a regional support;
- distinguish a 100 km search extent from a 10 km pairwise distance;
- use the regional result as context, then independently estimate each taxon at the target; and
- refuse the tempting but unsupported shortcut of transferring a relation result itself.

This was not a missing-data problem. The capability selector exposed one leaf at a time, operator
capabilities were absent, and the binder was allowed to replace a valid composed root with the
selected leaf. As a result, an LLM could express `RELATE` or `ESTIMATE`, but the routing layer
silently erased it before deterministic execution.

## Implemented architecture

```text
question + audited dialogue history
  -> semantic retrieval of a minimal capability set
       (operator + data connector class + declared/bounded region support)
  -> small-model compilation of the complete IR
  -> optional post-IR semantic critic
  -> contract binder (fills declared slots; never changes a composed root)
  -> schema validation
  -> deterministic Python execution over locked origin connectors
  -> evidence-pack audit
  -> bounded natural-language response
```

The selector now retrieves up to four compatible ingredients rather than choosing one dataset.
`RELATE` and `ESTIMATE` are explicit operator capabilities with dependencies. Generic regional
occurrence queries bind the concrete taxon named by the user instead of treating the connector
class as a literal entity. Site-only cards are pruned when a broader regional support and generic
occurrence connector are selected.

The binder projects only schema-declared fields and preserves `RELATE`, `ESTIMATE`, `COMPARE`,
`RANK`, and `AGGREGATE` roots. This fixed a Qwen-2B draft that correctly selected `ESTIMATE` but
included non-executable explanatory metadata. The repair is contract-driven, not a question phrase
router.

## Algebra and execution boundary

- `RELATE` over coordinate records now returns both denominators, both matched counts/fractions,
  both search supports, the pairwise threshold, and `temporal_alignment=not established`. Its
  evidence label is `proxy`; proximity never establishes interaction, habitat preference,
  simultaneous observation, or target-site occurrence.
- `ESTIMATE` accepts one taxon's donor occurrence rows and a distinct target. It retains donor
  entity, donor region, donor count, target region, gate, model year, and limitations for later
  turns.
- `ESTIMATE(RELATE(...))` fails explicitly as `unsupported_relational_transfer`. Joint-relation
  transfer has no admitted estimator or validation contract.
- The estimator is the hash-locked origin `predict.py`, called through a thin typed adapter. The
  first local reimplementation returned 0.4337 where production returned 0.039; it was rejected.
  With the locked 2023 AlphaEarth path, the typed elephant result is exactly the production 0.039,
  including 0.95 test accuracy and the 0.94 analog-gate fraction.
- `BUFFER(REGION, radius_km)` is implemented only in the sector's experimental dialect to keep
  search extent separate from pairwise distance. It is registered as ALG-015 and has a neutral
  review packet. It is not in the released kit or framework manifest.

The exact origin `points.get` resolver/merger remains the point backend, constrained to its bounded
GBIF and iNaturalist point sources. Its hidden paper-data path can invoke an interactive column
matcher for several minutes and is not an admissible side effect of a point leaf. Semantic paper
discovery and paper-dataset extraction remain explicit connector operations with separate
provenance.

## Live multi-turn acceptance

Artifact: `integration/eval/runs/20260718-relate-estimate-typed-v3.json`; real resumed Hermes
session `20260718_185102_333e6c`.

1. Regional relation: 735 elephant and 547 Little Cormorant occurrence records; 231/735 (31.4%)
   and 215/547 (39.3%) had a counterpart within 5 km. The response calls this a spatial
   occurrence-record proxy and states that temporal alignment was not established.
2. Interpretation challenge: the next turn refuses to infer shared habitat, same-time presence,
   or occurrence inside the target and requests a target field design.
3. Independent elephant estimate: its own 735 donor rows and environmental gate produce the locked
   origin result, suitability fraction 0.039, without claiming animal count or current presence.
4. Independent Little Cormorant estimate: its own 547 donor rows and gate produce 0.047. A newly
   added audit rejected “low fraction means limited potential presence”; the safe fallback reports
   the classified-cell fraction and limitations without converting it into occurrence probability.

All four turns exited successfully in 79.571 seconds total after connector/model caches, versus
326.205 seconds for the matched origin DeepSeek-v4 conversation. Origin correctly invoked the
production estimator and obtained 0.039 for elephant, but its relation interpretation asserted
shared water/habitat behavior not established by the returned coordinates and attached an
unsupported acreage conversion to the model output. The typed arm is therefore better on this
conversation's declared evidence contract, while sharing the production estimator rather than
claiming a new model-quality gain.

A separate live probe compiled two taxon leaves over the same 100 km buffered target support while
retaining a 10 km relation threshold. This demonstrates the expressiveness need behind ALG-015;
it does not satisfy the proposal's full geographic conformance wall.

## Stop-condition decision

The narrow RELATE/ESTIMATE repair stop is met when all of the following hold:

- a natural Qwen-2B turn compiles and executes a two-leaf regional relation;
- both denominators and bidirectional match rates survive response synthesis;
- multi-turn interpretation does not launder proximity into interaction or local occurrence;
- each target estimate re-executes one taxon's donor connector and gate independently;
- the typed estimate matches the locked production estimator on the shared input/year;
- relation-valued transfer fails closed;
- search extent and relation threshold can be represented independently; and
- targeted tests, CLI checks, governance validation, JSON validation, and diff checks pass.

All eight conditions pass: 190 ecology tests, 18 framework tests, the Hermes CLI contract,
governance validation, syntax/JSON validation, diff integrity, and the origin read-only check are
green. This is not practical or hard saturation. Generic open-category discovery, systematic literature
graph expansion, geographic edge semantics for ALG-015, untouched post-freeze holdouts, and LoRA
training remain separate work.

## Tracked state per run

For each turn the artifact retains the user prompt, resumed session, chosen capabilities, complete
IR, schema result, execution status, connector events, source row counts, evidence label, spatial
and temporal grain, gate fields, response audit, fallback status, and compile/render/wall latency.
Progress is measured by semantic contract checks, not merely whether an answer was fluent.
