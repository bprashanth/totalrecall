# State of India's Birds 2023 method snapshot

This directory is a selected, immutable snapshot of the State of India's Birds 2023 analysis
repository at commit `5d85c3567990062d7f58a6eb40819cf4f82d885b` (tag `v2023`). The repository
code is MIT licensed and archived as Zenodo DOI `10.5281/zenodo.12698375`.

The snapshot retains the pipeline documentation and the functions that define source filtering,
range support, occupancy, reporting-rate trends, uncertainty summaries and their visual grammar.
`ACQUISITION.json` records the archive digest and a SHA-256 digest for every selected file.

It deliberately excludes the eBird Basic Dataset, observer and checklist rows, sensitive-species
locations, spatial inputs, fitted objects and generated results. Those inputs have separate terms
and must arrive through an authorised connector. Nothing in this directory is evidence that a
species occurs in Valparai, and a national or state result must not be silently presented as a
site-scale estimate.

The corresponding entries in `../method_cards.json` are research references. Their source
thresholds document one published implementation; they are not universal defaults. A local run
must expose the observation process, effort and coverage, test scale and environmental support,
and keep observed records separate from modelled surfaces.
