# Valparai Livelihoods — SYNTHETIC proof-of-concept site pack

**Everything in this pack is fully synthetic.** No file here contains real,
observed, surveyed or published data. It exists solely to test that the generic
`visual-site-pack/0.1` contract and `dss/visual_index/build.py` can carry a
non-ecological (livelihoods / socio-economic) domain without builder changes.

Do not cite it, publish it, or treat any number, place name or boundary in it as
evidence about Valparai or any real community, estate or scheme.

## Why Fable should use this pack

This is the safe UX-development twin of the real `dss/sites/valparai/` pack. Both packs declare
the same versioned capability interfaces and are served by the same
`dss/visual_index/result_service.py` implementation:

- `site-orientation`;
- `entity-record-map`;
- `coverage-versus-effort`;
- `metric-time-series`; and
- `gated-transfer` (currently an explicit blocked/partial capability in both packs).

The entities, metrics, sources and values differ, but the `idli-result/1` visual grammar does not.
For example, `daily_wage` produces the same chart/layer/drill-down structure as the real pack's
`rainfall`, and `Karumalai Estate` records produce the same map structure as real entity records.

Every result from this pack carries `site.synthetic: true`, synthetic source-version flags and a
`synthetic-data` limitation. Fable should render that as a persistent test-data notice. Switching
the configured pack to `dss/sites/valparai/` removes the notice automatically; no component,
route, capability or layout changes are allowed.

## What is synthetic here

- **Geometry** — the AOI polygon (~10.245-10.385N, 76.88-77.015E) and all named
  places were hand-authored in `raw/geometry/valparai_livelihoods_aoi.kml`. The
  estates and villages (Karumalai, Nedumparai, Ambalam, Pannimedu, Sirukundra,
  Thonimalai, Perumpallam, Kadamparai) are **fictional**. Only the plateau's
  approximate location and the town-centre point are realistic.
- **Sources** — five machine-generated CSV sets under `raw/`, licensed CC0-1.0
  and flagged with a `synthetic` capability:
  | source_id | plane | rows |
  |---|---|---|
  | `syn-estate-labour` | locations + events (annual worker headcounts, 2015-2024) + entity hierarchy | 50 events, 5 estates |
  | `syn-wages` | measurements (daily wage, overtime rate, paid days), 2017-2024 monthly | 96 rows → 288 measurements |
  | `syn-mgnrega` | events (public works, persondays), 2019-2024 | 72 |
  | `syn-migration` | events (out-migration by occupation) + occupation crosswalk | 42 |
  | `syn-household-survey` | effort (households visited, enumerator hours, population denominator) + locations | 48 |

## Entities

Estates (5, carrying a `sector → division → ownership_type → estate_unit`
hierarchy), scheme work types (4), and occupations (4, reached through a
verbatim→canonical crosswalk).

## Build

```bash
python3 dss/visual_index/build.py \
  --site-pack dss/sites/valparai_livelihoods \
  --output /tmp/valparai-livelihoods-index
```

Run the typed wage example:

```bash
python3 dss/visual_index/result_service.py \
  --site-pack dss/sites/valparai_livelihoods \
  --index /tmp/valparai-livelihoods-index/site_index.sqlite \
  --state /tmp/valparai-livelihoods-results \
  --query '{"request_id":"wage-demo","capability_id":"metric-time-series","arguments":{"metric":"daily_wage"},"question":"How have daily wages changed?"}'
```

The dual-pack conformance tests build and query both packs:

```bash
python3 -m unittest dss.visual_index.tests.test_result_service.PackSwapContractTest -v
```

## Known contract note

`build.py` reads the AOI from the inline GeoJSON in `site.json`; it has no KML
reader. The KML is kept in `raw/geometry/` as the immutable authored original
and is mirrored into `site.json` by hand (`target_aoi.source_geometry_file`
records the link).
