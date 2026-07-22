# declared-site-centre

Declared EBTL centre point used only as input to a raster annotation; it is not the property polygon.

Use for:
- point input for satellite annotation

Do not use for:
- whole-property measurement
- survey boundary

Invoke:

```bash
python3 /bench/arm/input/skill_call.py declared-site-centre '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
