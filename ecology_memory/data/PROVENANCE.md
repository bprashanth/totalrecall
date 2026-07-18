# Imported ecology data provenance

The origin repository remains read-only. Files here are immutable snapshots copied for a
self-contained benchmark; adapters must cite this manifest and live-source checks before using a
snapshot to mint gold.

| file | origin | SHA-256 | rows | stated origin | license status | admission |
|---|---|---|---:|---|---|---|
| `imported/restoration_sites.csv` | `idlisseus/dss/queries/data/restoration_sites.csv` | `78bab6b96e592ac639b0d8a5469ad9d9927c6cf3c8497723b4afd06bb5e91862` | 26 | Zenodo 10077040 `01_sites.csv` exact four-column projection | CC-BY-4.0 | admitted as vegetation survey sites; never label as restoration interventions |
| `imported/lantana_occurrence.csv` | `idlisseus/dss/queries/data/lantana_occurrence.csv` | `9ef7e38a26172d351567b101398795d92e2d2567c3f2b1deffd2060c532a7878` | 250 | file rows say iNaturalist research-grade; origin prose says GBIF | pending per-record/source check | quarantined |

The Lantana snapshot remains quarantined: live GBIF phantom checks found a mix of CC0 and
CC-BY-NC-4.0 rows. Live adapters fetch and retain only explicitly admitted reusable licenses;
the mixed snapshot is never used to mint gold or training rows.
