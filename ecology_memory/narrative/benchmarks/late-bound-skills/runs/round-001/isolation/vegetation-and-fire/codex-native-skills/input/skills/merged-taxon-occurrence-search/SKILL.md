# merged-taxon-occurrence-search

Resolve a named animal or plant and retrieve bounded georeferenced GBIF and iNaturalist occurrence records in the requested geometry.

Use for:
- species records
- sightings around a place
- where a named species was observed

Do not use for:
- abundance
- complete site inventory
- predicted presence
- literature-only leads

Invoke:

```bash
python3 /bench/arm/input/skill_call.py merged-taxon-occurrence-search '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
