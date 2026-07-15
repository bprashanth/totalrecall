# Inexpressible question proposals

These natural Indian public-service questions were excluded from `bank.json` because the frozen
algebra cannot represent their requested operation faithfully:

- “Ward-wise pothole repair time after complaint, median days tell.” The aggregate vocabulary has
  `mean` but no median/percentile statistic.
- “How many garbage complaints are still open after thirty days?” This needs attribute predicates
  and duration filtering; there is no `FILTER` operation.
- “Which ward improved the most after the new contractor took charge?” This needs an intervention
  boundary plus a ranking over per-ward changes.
- “Morning bus availability is okay, but after 8 pm which areas are left out?” Time-of-day filtering
  and service-frequency semantics are absent.
- “Are complaints high because collection is poor or because reporting is easier?” Competing causal
  explanations cannot be represented as a proxy `SELECT` without pretending they are observations.
- “Show one-kilometre walking distance, not straight-line distance.” `RELATE` currently executes
  haversine distance and has no network-distance mode.

