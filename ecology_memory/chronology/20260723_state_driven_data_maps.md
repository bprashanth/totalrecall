# State-driven data-request maps — 2026-07-23

## Trigger

Chat `96f71512-b900-4686-bc43-e9a7b6456b15` asked about sand boa at EBTL and
then, in ordinary language, where it could be found to collect data. The result named Common Sand
Boa but offered repository discovery and no map.

## Audit diagnosis

- The local query `sand boa` selected the broad four-row wildlife group summary rather than the
  structured 14-row snake inventory.
- Common Sand Boa appeared only as an example in that returned summary. No scientific name or
  coordinates were returned.
- The controller required an exact full-name match, so `sand boa` did not become Common Sand Boa.
- Algebra selected `discover-ecology-evidence`; that returned 16 article/repository metadata leads
  and zero georeferenced occurrence points.
- No taxonomy resolver, occurrence connector, transfer gate or map skill ran. There were therefore
  no points that Codex could have hidden or rendered.

## General correction

- A structured local name match now outranks a group-summary text match. Shorter names and names
  with extra context match only when they identify a unique structured row.
- `sand boa` now returns one local row: Common Sand Boa, `Eryx conicus`, directly observed during
  the September 2024 VES.
- The source-reported scientific name is passed to the public resolver. A live check resolved
  `Eryx conicus` as an exact GBIF species match with usage key `5225641` and returned 118
  coordinate-deduplicated GBIF/iNaturalist points in the dry-Deccan donor region.
- Natural spatial-data wording is recognised without skill terminology.
- Named local taxa offer both wider occurrence retrieval and a field-check map.
- Wider points offer raw-point, transfer-test and modelled-map actions.
- Recoverable geospatial taxon data requests offer a map button; unresolved/ambiguous taxa and
  missing connectors remain blocked.
- A modelled map rechecks the seeded local row, records the local-to-scientific translation, runs
  the public occurrence and transfer path using that scientific name, and offers a follow-up raw
  map of supporting donor points.

## Sand boa execution check

A direct `sand boa` map execution promoted the query to `Eryx conicus`, retained the local observed
survey row, passed the AlphaEarth analogue gate at `0.93`, returned an AOI-wide suitability
fraction of `0.025`, and produced nine spatially balanced confirmation points because the admitted
model has no within-AOI ranking surface. The point reason states that they reduce spatial
uncertainty; it does not call them predicted snake locations.

After the host bridge reload, a fresh end-to-end chat used only ordinary wording: “Where can I
expect to find sand boa at EBTL to collect useful data?” Algebra selected the self-contained map
operation. The final answer retained the local Common Sand Boa / `Eryx conicus` survey row, the
model result, all nine point IDs and coordinates, and side-panel map
`idli-map-39c2320027bd75562ee7`. The controller also emitted a “Show supporting occurrence points”
button bound to `Eryx conicus` in the dry-Deccan donor region. Audit:
`natural-data-map-live-146af824-66fc-4e7c-87d8-0bf3b0e01aa8/1`.
