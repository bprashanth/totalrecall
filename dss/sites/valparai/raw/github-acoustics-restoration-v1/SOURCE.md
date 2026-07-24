# Acoustic restoration repository snapshot

- Repository: <https://github.com/vjjan91/acoustics-Restoration>
- Commit: `72064c89c9f9d14344c6e217aade02e074e70597`
- Tag: `v1-for-review`
- Related Zenodo DOI: `10.5281/zenodo.7036137`
- Licence: GNU GPL v3, retained as `LICENSE`
- Retrieval: selected paths from the immutable GitHub commit archive, verified in
  `ACQUISITION.json`

The admitted aggregate data include 44 recorder-site descriptions, vegetation measurements,
species habitat traits, 43 site-level frequency-by-hour acoustic-space-use matrices, site-day
acoustic-space-use matrices, 257 site-date bird-detection summaries, richness estimators,
ordinations and vegetation PCA outputs. The analysis notebooks document the recording and
modelling protocol.

`results/datSubset.csv` is deliberately excluded. Although it is present in the repository, the
source README asks prospective users of that clip-level table to contact the lead author. Binary
R workspaces, generated web pages, figures and raw audio are also excluded. No exclusion is
silently replaced with a different source.

Acoustic-space-use values are source-derived activity summaries, not species detections,
abundance, habitat quality or population trends. The site-level matrix was scaled from zero to one
within the source workflow. Bird detections and species traits remain separate planes.
