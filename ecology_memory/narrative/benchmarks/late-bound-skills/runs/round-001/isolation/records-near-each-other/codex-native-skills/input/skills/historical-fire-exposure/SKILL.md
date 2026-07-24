# historical-fire-exposure

MODIS active-fire locations in the analysis bbox and pixel-fire-days per square kilometre around the site point over one declared period.

Use for:
- historical fire exposure over a period

Do not use for:
- burned area
- ignition count
- fire probability
- property-polygon burning
- up or down by year

Invoke:

```bash
python3 /bench/arm/input/skill_call.py historical-fire-exposure '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
