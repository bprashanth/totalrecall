# local-snake-inventory

Complete documented EBTL snake inventory, separating snakes encountered in the September 2024 visual survey from older property records and retaining the declared dangerous subset.

Use for:
- snakes recorded at EBTL
- 2024 snakes versus older records
- snakes dangerous to people

Do not use for:
- regional occurrence search
- population
- proof of absence

Invoke:

```bash
python3 /bench/arm/input/skill_call.py local-snake-inventory '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
