# Ecology source census

Checked live on 2026-07-15. Counts are reproducibility probes, not stable ecological claims;
upstream observations and the current 30-day eBird window will change.

| family | capability and grain | auth | evidence | license/admission | live probes |
|---|---|---|---|---|---|
| GBIF Occurrence API | taxon occurrences; record/point/event | keyless | observed presence; never abundance | adapter retains each record license and admits CC0, CC-BY-4.0, CC-BY-SA-4.0 only | licensed 2024–2026 Lantana rows: Valparai 1, Mysuru 1, Bengaluru 7 after cross-source dedupe |
| iNaturalist v1 API | research-grade taxon observations; record/point/event | keyless for reads | observed presence; observer-effort biased | request restricted to CC0/CC-BY/CC-BY-SA; coordinates, quality, URI and license retained | independently contributed to all three Lantana probes; mirrored records deduped against GBIF |
| eBird API 2.0 | recent checklist observations; point/species/time, 1–30 days | configured free API key | observed records; partial-coverage proxy when bbox exceeds 50 km | eBird API Terms; not copied into the LoRA corpus as raw response content | bbox-post-filtered rows: Valparai 25, Mysuru 81, Bengaluru 84 |
| Earth Engine public catalog | MODIS annual bbox NDVI series; NASADEM/JRC/ESA/RESOLVE point annotations | configured Earth Engine account | remote-sensing measurement, classification/model, or geocoder-bbox proxy as declared per layer | MODIS/NASA unrestricted; ESA/RESOLVE/AlphaEarth CC-BY-4.0; WorldClim CC-BY-SA-4.0; JRC free with attribution | 2024 bbox NDVI: Valparai 0.806804, Mysuru 0.462235, Bengaluru 0.413182; three-site elevation sampling also returned rows |
| Zenodo 10077040 | 26 Anamalai vegetation survey sites; published site/habitat points | keyless snapshot | observed published survey locations | CC-BY-4.0; local four-column file is an exact projection of authoritative `01_sites.csv` | Valparai geocoder bbox contains 10; Mysuru and Bengaluru correctly contain 0 |
| Nominatim | named REGION to display name, centroid and bbox | keyless | support resolver, not ecological evidence | OSM/Nominatim attribution required | areal resolutions verified for Valparai, Mysuru and Bengaluru |

## Source semantics and limits

- GBIF search pages are capped and live results revise. The adapter reports upstream total counts
  separately from its bounded, license-filtered rows. It excludes geospatial-issue records and
  preserves GBIF quality flags.
- iNaturalist is queried at research grade with explicit reusable-license filters. Its weekly GBIF
  publication means cross-provider duplicates are expected; only likely cross-provider mirrors
  are collapsed, never same-provider records sharing a coordinate/date.
- eBird's nearby endpoint is radial. The adapter post-filters every result to the requested
  rectangular bbox. A bbox whose half diagonal exceeds the API's 50 km limit is labelled `proxy`.
  Historic requests beyond 30 days become `DataRequest(unsupported_time)`.
- MODIS `MOD13A3` NDVI is QA-masked, scaled by 0.0001 and averaged annually. The geometry is the
  geocoder bbox rather than an administrative polygon, so place-wide NDVI is labelled `proxy`.
- JRC surface-water occurrence masks never-water pixels; for a percentage those pixels are valid
  zeroes, so the annotation adapter explicitly unmasks them to zero.
- Zenodo record 10077040 describes rainforest fragments, mature forest and coffee plantations.
  Calling these rows “restoration sites” would be false; the imported filename is retained only
  for snapshot continuity and the resolver exposes them as vegetation survey sites.

## Authoritative references

- GBIF Occurrence API: https://techdocs.gbif.org/en/openapi/v1/occurrence
- GBIF occurrence fields/licenses: https://techdocs.gbif.org/en/data-use/download-formats
- iNaturalist API practices: https://www.inaturalist.org/pages/api+recommended+practices
- eBird API 2.0: https://documenter.getpostman.com/view/664302/S1ENwy59
- MODIS MOD13A3: https://developers.google.com/earth-engine/datasets/catalog/MODIS_061_MOD13A3
- ESA WorldCover v200: https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200
- NASADEM: https://developers.google.com/earth-engine/datasets/catalog/NASA_NASADEM_HGT_001
- JRC surface water: https://developers.google.com/earth-engine/datasets/catalog/JRC_GSW1_4_GlobalSurfaceWater
- RESOLVE Ecoregions: https://developers.google.com/earth-engine/datasets/catalog/RESOLVE_ECOREGIONS_2017
- AlphaEarth embeddings: https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_SATELLITE_EMBEDDING_V1_ANNUAL
- WorldClim V1 BIO: https://developers.google.com/earth-engine/datasets/catalog/WORLDCLIM_V1_BIO
- Published survey sites: https://zenodo.org/records/10077040
