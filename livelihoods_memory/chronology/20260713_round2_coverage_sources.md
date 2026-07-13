# Round 2 checkpoint 1 — capability baseline and source expansion

## Coverage baseline

The Round 1 bank contains 52 active single-turn questions but only 12 unique operator skeletons.
The generated `coverage/matrix.json` makes the repetition visible. Major empty cells include
ANNOTATE, co-occurrence, presence, ascending/top-k ranks, multi-year SELECT windows, richer
ESTIMATE methods, mixed-source trees, subgroup algebra, and subnational official statistics.

This changes the generation objective. Round 2 targets matrix cells and failure classes; it does
not reward paraphrase count.

## Connector checkpoint

ILOSTAT and Eurostat were independently live-probed from their official endpoints and added behind
the existing SELECT contract. ILOSTAT contributes country-year labor-survey measures and explicit
sex/economic-activity slices. Eurostat contributes NUTS-2 annual series. Together with OSM and
World Bank, there are now four adopted source families across city-bbox records, country annual
series, and NUTS-2 annual series.

The source integrity snapshot has ten passing bounded probes. ILO model-extrapolated rows are
excluded, overlapping survey vintages are not mixed, Eurostat queries fix all non-time dimensions,
and all choices/flags are written into provenance. No frozen algebra or evidence rule changed.

## Next gate

Author a large development bank from the empty admissible cells and a separate expressiveness
breaker stream. Run first-contact qwen parsing before any repair, classify failures by layer, and
only then iterate with the complete Round 1 guard.
