# Valparai method references

This directory holds immutable external analysis code and the method cards derived from it.
It is not an executable skill bundle.

`method_cards.json` describes the operations, inputs, denominators, gates, visual grammar and
claim limits that a generic analysis capability can bind to compatible planes in a site pack.
The source scripts remain beside their verified acquisition manifest so a result can point back
to the exact implementation that motivated a card.

The current Zenodo record is MIT-licensed companion code for the observations admitted as
`dryad-8kprr4xvb-restoration-opportunities`. Its methods are references, not automatically
approved production models. Cards marked `requires_model_review` or
`research_reference_not_operational` must pass their stated gates before a result can be labelled
modelled.

`github-ebird-occupancy-v3.3` is a separate GPL-3.0 method snapshot for detection-aware
single-season occupancy modelling. It includes only code and published aggregate/model summaries.
Underlying checklist rows, coordinates, rasters and fitted objects are not admitted; their
separate data terms still apply.

`github-soib-2023-v2023` is a selected MIT-licensed snapshot of the State of India's Birds 2023
range, reporting-rate trend, uncertainty and plotting pipeline. It contains no eBird checklist
rows, observer data, sensitive locations, spatial inputs or fitted outputs. Its thresholds and
grid scales document a national/state implementation and require explicit redesign and validation
before any site-scale use.
