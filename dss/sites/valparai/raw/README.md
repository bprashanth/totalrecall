# Raw source subsets

These are unchanged source files copied from the repository's earlier benchmark cache into the
maintained Valparai site pack. They are kept with their source README/codebook and are treated as
immutable bronze inputs.

| Directory | DOI | Licence | Included subset |
|---|---|---|---|
| `zenodo-7008315` | `10.5281/zenodo.7008315` | CC BY 4.0 | curated 2015–18 occurrence table and README |
| `zenodo-11903722` | `10.5281/zenodo.11903722` | CC BY 4.0 | 2020–23 occurrence table, place/name crosswalks and README |
| `zenodo-13910696` | `10.5281/zenodo.13910696` | CC BY 4.0 | 2024 occurrence table and README |
| `zenodo-10077040` | `10.5281/zenodo.10077040` | CC BY 4.0 | sites, plot entities, point locations, habitat and README |
| `zenodo-7060430` | `10.5281/zenodo.7060430` | CC BY 4.0 | sampling effort, events, route habitat, KML and README |
| `zenodo-7457732` | `10.5281/zenodo.7457732` | CC BY 4.0 | sites, adult/regeneration/canopy tables, entity hierarchy and README |
| `zenodo-18646715` | `10.5281/zenodo.18646715` | CC BY 4.0 | daily/monthly summaries and README; high-frequency raw logger file omitted |
| `dryad-5x69p8d0r-frugivory` | `10.5061/dryad.5x69p8d0r` | CC0 1.0 | focal-tree watches, scans, visitor crosswalk and traits |
| `dryad-qv9s4mwd5-seed-fate` | `10.5061/dryad.qv9s4mwd5` | CC0 1.0 | camera visits, seed fates and movement distances |
| `dryad-rjdfn2zc3-restoration-birds` | `10.5061/dryad.rjdfn2zc3` | CC0 1.0 | point counts, effort, plot coordinates, habitat and tree quadrats |
| `dryad-b2rbnzsff-shade-birds` | `10.5061/dryad.b2rbnzsff` | CC0 1.0 | bird detections, guilds and scientific-name crosswalk |
| `dryad-8kprr4xvb-restoration-opportunities` | `10.5061/dryad.8kprr4xvb` | CC0 1.0 | plot locations, adult trees, regeneration, carbon, conservation and dispersal traits |
| `gbif-v6ku49-butterflies` | `10.15468/v6ku49` | CC BY 4.0 | butterfly point counts, Darwin Core metadata and immutable archive |
| `gbif-ysrzbw-frogs` | `10.15468/ysrzbw` | CC BY 4.0 | frog belt-transect occurrences and effort, Darwin Core metadata and archive |
| `gbif-d96cu4-herpetofauna` | `10.15468/d96cu4` | CC BY 4.0 | systematic and incidental herpetofauna records, methods and archive |
| `gbif-4e53vk-threatened-trees` | `10.15468/4e53vk` | CC BY 4.0 | threatened trees, PCQ samples and 65-trail inventory |
| `gbif-2bqrzp-frugivory` | `10.15468/2bqrzp` | CC BY 4.0 | fruiting trees and animal-visitor study occurrences |
| `gbif-utzvkm-seed-predation` | `10.15468/utzvkm` | CC BY 4.0 | focal trees and camera detections from a seed-predation experiment |

Zenodo licences were verified against its record API on 2026-07-24. Five Dryad datasets were
retrieved through the authorised API on 2026-07-25 and checked against their file manifests.
Documented upstream digest anomalies remain explicit in each source's `SOURCE.md` or
`ACQUISITION.json`; all advertised byte sizes match. The six GBIF Darwin Core
archives were retrieved and verified against their GBIF dataset metadata on 2026-07-25; each
source README records the archive SHA-256 and exact modified timestamp. Use the citation given in
each source README. The source registry records the stable record URL and computes a content hash
across every admitted local file at build time.

Photos, PDFs, audio and raw high-frequency logger data were not duplicated. Retrieve them from
the source record if a later question needs them, then add them as a new declared site-pack source
version. The GBIF source directories retain both the original archive and its unpacked files;
`occurrence.txt`, `eml.xml` and `meta.xml` are byte-for-byte archive members.
