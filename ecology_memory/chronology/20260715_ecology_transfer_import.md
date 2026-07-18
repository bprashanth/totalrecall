# Ecology transfer import — 2026-07-15

## Why

TRANSFER was the largest semantic mismatch between the origin scaffold and the bootstrapped
executor. The origin distinguishes local satellite-feature analogy from cross-region climate
envelopes. The bootstrap only checked geographic proximity and then relabelled donor rows, which
could make a valid-looking tree execute to a non-estimate.

## What changed

The imported gate now implements three frozen ESTIMATE methods without adding algebra vocabulary.
`feature` samples annual 64-band AlphaEarth embeddings and asks whether target pixels have a close
donor analogue. `envelope` samples 19 WorldClim bioclimatic variables and measures how much of the
target is inside every donor range. `interpolate` accepts only numeric point measurements and only
inside their support. Occurrence transfers require at least 20 donor points; substantial target
overlap routes back to observations.

After a feature or climate gate passes, an Earth Engine random forest estimates a target-bbox
suitability fraction from presences and deterministic pseudo-absences. The result is always
`modelled`, reports held-out accuracy, requests designed absence surveys, and surfaces major
ecological limitations. A failed gate remains a DataRequest.

## What we found

Valparai Lantana records could not transfer to Delhi: none of the deterministic Delhi samples was
inside the donor WorldClim envelope. A small held-out AOI inside the donor environment exercised
both success paths: AlphaEarth analog coverage was 0.8 and climate-envelope coverage 1.0, and both
models returned properly labelled fields. These are connector branch tests, not claims about
Lantana presence.

The full 270-question wall then passed again at 1.000 with no synthesis-audit failures. Eight unit
tests guard the non-live semantic boundaries.
