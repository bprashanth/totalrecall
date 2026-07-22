# gated-species-presence-transfer

Estimate target species suitability from donor occurrence records only after environmental feature or climate-envelope gates.

Use for:
- could a species occur at a data-poor site
- careful regional-to-site estimate

Do not use for:
- direct observation
- abundance
- ungated extrapolation
- transfer of a relationship

Invoke:

```bash
python3 /bench/arm/input/skill_call.py gated-species-presence-transfer '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
