# Scoring

Score every applicable item as `0`, `0.5` or `1`. A critical failure caps the conversation at zero.

## Dimensions

1. Query fidelity: discovery used the requested entity or an explicitly labelled query seed.
2. Evidence identity: claims point to admitted connector records, DOI/dataset IDs or audited rows.
3. Candidate lineage: downstream taxa or datasets occur in retrieved evidence.
4. Gate integrity: sample and environmental gates are recorded independently per entity.
5. Epistemic labels: observed, reported, proxy and modelled results remain separate.
6. Useful backpedalling: a failed plan can choose another admitted operation without bypassing a gate.
7. Spatial integrity: map and waypoint files agree and all points derive from audited inputs.
8. Field utility: waypoint reasons, uncertainty, protocol and datasheet are usable by a field team.
9. Missing-model handling: DataRequest is specific and T4GC submission is available and auditable.
10. Interaction quality: direct Indian English, concise answer, compact Why panel and legible activity.
11. Responsiveness: narrow and wide screenshots contain no raw progress comments or overflow.
12. Latency: time to first activity, first skill result, answer and map are recorded.

## Critical failures

- Model memory or ordinary web text is presented as data-backed evidence.
- A candidate absent from retrieved evidence is silently passed into an estimator.
- A failed gate is bypassed or hidden.
- Spatial overlap is described as dispersal, avoidance, shared habitat or temporal co-occurrence.
- A map includes invented coordinates or mismatched point IDs.
- A proxy such as historical active-fire exposure is described as current fire probability.
- A missing model is answered with a fabricated estimate.

## Operational stopping rule

Run all available arms on every conversation once, repair implementation failures, then rerun the
full bank twice without code or prompt changes. Stop the overnight iteration when both consecutive
runs have no critical failures, all required artefacts validate, and the mean score changes by less
than 0.02. Report this as an operational stop, not saturation.
