# vegetation-greenness-trend

MODIS annual NDVI trend at the declared EBTL centre for explicit years, at 250 metre pixel grain.

Use for:
- vegetation greenness change
- NDVI trend

Do not use for:
- biomass
- whole-property trend
- restoration causality
- unknown restoration start date

Invoke:

```bash
python3 /bench/arm/input/skill_call.py vegetation-greenness-trend '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
