# Valparai research acquisition and visual-model roadmap

This file is the human-readable companion to
[`acquisition_catalog.json`](acquisition_catalog.json) and
[`indicators.json`](indicators.json). It records why a source is being pursued before it enters
the serving pack. `sources.json` remains the registry of admitted, immutable source versions.

## Current evidence shape

The first two admitted tranches now cover:

- repeated and opportunistic mammal observations;
- road-event observations with explicit transect effort;
- trees, regeneration, canopy and point-level habitat structure;
- daily and monthly weather;
- butterfly point counts and frog belt transects with source-reported effort;
- systematic and incidental herpetofauna records, kept distinguishable by method;
- threatened-tree, PCQ and trail-inventory observations;
- focal-tree watches, visitor behaviour scans, seed fate and movement;
- restored, naturally regenerating and benchmark bird point counts with explicit effort;
- restoration habitat and tree-quadrat measurements;
- shade-plantation bird guild and scientific-name crosswalks; and
- source-linked camera detections at focal seed experiments.

This supports immediate maps of records, coverage, effort and measured habitat. It does not yet
support a claim of local absence, causal restoration effect, population trend, dispersal from
unjoined visitor occurrences, phenophase, corridor use or transferable suitability.

## Acquisition order

1. Build the treatment/effort-aware comparison operations over the newly admitted restoration
   point counts, habitat plots and tree quadrats. Keep site category, survey effort and uncertainty
   visible; do not compare raw record totals as recovery.
2. Extend the admitted 2024 Earth-observation feature cube to a multi-year series where the
   question needs it. The first cube contains harmonised Sentinel-2 indices and monthly NDVI,
   Dynamic World probabilities, terrain, ERA5-Land, CHIRPS and all 64 annual AlphaEarth axes.
   Its manifest records asset IDs, dates, scale, cloud/composite rules, rights and digest, and
   retains cloudy-season missingness.
3. Add the Western Ghats bird occupancy and State of India’s Birds methods as reproducible
   model cards. Their wider-scale outputs are context and donor evidence, not local presence.
4. Resolve acoustic-source rights, then index recording stations, schedules, outages,
   soundscape summaries and manually verified labels before considering automated detections.
5. Add SoilGrids only with its 5th, 50th and 95th quantiles. At 250 m it is a context and
   survey-design layer, not a substitute for plot samples.
6. Use IUCN and eBird only through authorised connectors and their own redistribution and
   sensitive-location rules.

## Modelling gate

A distribution or transfer map is produced only when the run records:

- a resolved entity and an inspectable occurrence/effort source set;
- the target and donor scopes;
- predictor identity, resolution, time support and missingness;
- environmental support or extrapolation for every target cell;
- spatially separated validation, not a random split over clustered points;
- metrics appropriate to the observation process and prevalence;
- calibration and uncertainty;
- a comparison with a simple baseline;
- source and model versions; and
- a clear distinction between observed points, modelled values and cells where the gate failed.

With too few target records, the default next visual is the wider source-coverage map. If donor
data exist, the agent may offer a gated model; if the gate fails, it still shows donor points and
unsupported target cells. A field-data request comes after this check and should name safe,
high-information cells and a source-backed protocol rather than ask vaguely for “more data”.

The first implemented transfer stage is deliberately narrower than a distribution model. It uses
all 64 normalised AlphaEarth axes to show environmental analogues of admitted donor-occurrence
cells, derives the support threshold from other spatial blocks, and hatches unsupported target
cells. It always leaves predictive discrimination unevaluated until compatible effort-linked
nondetection or declared target-group background data can support that test.

## Visual acceptance questions

The conversational benchmark should include short, ordinary Indian-English turns such as:

- “Tell me about this place.”
- “Where have people actually looked?”
- “What snakes do we have records for?”
- “Nothing here—is there useful data nearby?”
- “Can that wider data tell us anything about this side of the plateau?”
- “Show me the records and the model separately.”
- “Which rainforest trees have birds or mammals been recorded around?”
- “Does that mean they dispersed the seeds?”
- “How are the restored and naturally growing patches different?”
- “Is that a real trend or only more surveys?”
- “Where should we check next without sending people into a risky place?”
- “Make a dashboard of what we have established so far.”

Every first answer should prefer an appropriate map, chart, network, hierarchy or protocol visual.
The side text states the evidence class, denominator and most important limitation in a few lines.
