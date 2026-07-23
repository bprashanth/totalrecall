# Gated map artifact completion — 2026-07-23

## Trigger

Chat `aed5c571-d8da-45f7-9625-0a176241d713` asked where Common Sand Boa could be
expected at EBTL, agreed to a site-screening exercise twice, and finally asked for the screening
map. No map appeared.

## Audit diagnosis

- Algebra 9B repeatedly selected only `local-site-evidence-search`.
- No occurrence retrieval, transfer gate or map renderer ran on the explicit map turn.
- Codex accurately reported that the plan contained no map; it did not hide a returned artifact.
- The one-stage default instruction discouraged Codex from replanning even though the requested
  artifact had not been returned.
- The local match appeared in a survey-summary `examples` list. The action graph checked only
  row-level common/scientific-name fields, so it offered literature discovery instead of wider
  georeferenced occurrences.

## General fix

- Explicit map, field-point, screening-map and within-site “where” requests now require exactly one
  self-contained `build-ecology-field-map` plan step in the appropriate observed or modelled mode.
- The typed validator rejects a local-summary-only plan for an explicit map request.
- The map skill runs occurrence retrieval and environmental transfer internally. When no
  fine-scale ranking surface runs, it returns labelled spatially balanced confirmation points.
- A subsequent planner pass after a `data_request` is instructed to prefer a gated modelled field
  map when a named taxon and target geometry are established.
- Exact taxon matches inside survey-summary example lists now authorize the generic wider
  occurrence path. Returned occurrence points continue to offer raw-map and transfer buttons.
- Algebra plan parsing tolerates only a completely empty trailing padding step and normalises the
  declared one-entity map field from a scalar to a list. Unknown populated steps still fail closed.

## Verification

Forty-nine focused bridge tests pass. A live Algebra 9B probe for “ok give me the screening map”,
with Common Sand Boa supplied as a conversational query seed, returned one modelled
`build-ecology-field-map` step.

A direct execution probe then ran the real occurrence and AlphaEarth path:

- the AlphaEarth analogue gate passed (`target_analog_fraction = 0.93`);
- the AOI-wide modelled suitability fraction was `0.025`;
- the admitted model returned no within-AOI ranking surface;
- the renderer therefore returned nine stable `FIELD-01` to `FIELD-09` confirmation points,
  labelled as a spatially balanced data-collection design rather than predicted snake locations.

After the host bridge reload, a fresh end-to-end Codex chat asked “Build a modelled field map for
Common Sand Boa at EBTL.” Algebra returned exactly one map step; the gateway completed it and
published side-panel document `idli-map-44883b4b5a44585f25ae` with GeoJSON and CSV downloads.
The final answer retained the `0` exact EBTL occurrences, `118` deduplicated wider-region support
points, AOI-wide `0.025` suitability fraction and designed-versus-predicted distinction. The turn
completed in 51.954 seconds.

No model service or container was restarted for these probes.
