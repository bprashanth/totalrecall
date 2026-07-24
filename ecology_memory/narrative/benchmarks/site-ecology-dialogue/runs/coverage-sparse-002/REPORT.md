# Sparse dangerous-taxa coverage run

Run: `coverage-sparse-002`  
Conversation: `dangerous-taxa-data-coverage-transfer`  
Date: 2026-07-24

## Result

| Turn | Outcome | Score | Latency |
|---|---|---:|---:|
| Local reported venomous taxa | four older property records, zero detections in the short 2024 survey | 1.0 | 13.407 s |
| Search 200 km and show data | 924 points across four independent taxon snapshots; responsive coverage map | 1.0 | 60.764 s |
| Transfer exact snapshots | four independent Algebra calls; all gates/errors retained | 1.0 | 97.604 s |

Turn 2 returned 275 `Naja naja`, 272 `Daboia russelii`, 160 `Echis carinatus` and 217
`Craspedocephalus gramineus` points. The map used the four immutable result handles and identified
iNaturalist and GBIF/paper-data as the retained source labels. It did not rerun a connector.

The first turn-3 pass exposed a compiler type error: Algebra 9B selected `interpolate` for
occurrence-grain inputs. The runtime correctly failed those gates instead of coercing the data.
The compiler boundary was then clarified: interpolation requires numeric point measurements;
occurrence-presence transfer uses the `feature` gate.

A post-run live retry produced four `feature` trees. Three exact snapshots passed their
AlphaEarth-analogue gates. One 9B tree narrowed the donor extent to the target AOI; this led to the
deterministic evidence-extent binder, which binds an `ESTIMATE` donor `SELECT` to the exact snapshot
explicitly selected by outer Codex and records the binding. It does not choose a radius or model.

A final targeted live replay confirmed the fix for `Naja naja`: the exact 200 km snapshot supplied
all 275 donor rows to the feature gate. The AlphaEarth analogue gate then failed honestly at the
scientific boundary (`target_analog_fraction=0.49`, threshold `0.5`) and requested local target
observations; no snapshot mismatch remained.

The turn was rescored with the corrected multi-taxon invariant: several compiler calls are valid
when each is independently bound to a distinct evidence snapshot. A bulk ungated call still fails.

This is a regression/development run, not a saturation result.

## Visual check

- `screenshots/data-coverage-wide.png` — 1440×1000
- `screenshots/data-coverage-narrow.png` — 390×844

The first capture was rejected because duplicate red waypoint marks covered the taxon layers. The
checked-in captures show four colour-coded occurrence layers, a target-AOI marker, responsive
controls and stable observed IDs retained in the table/CSV/GeoJSON.
