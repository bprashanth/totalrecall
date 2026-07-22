# local-bird-lantana-overlap

Join the EBTL bird checklist to an admitted regional Lantana feeding dataset and return overlap with an interpretation gate.

Use for:
- which regional Lantana-associated birds are also in the local bird list

Do not use for:
- Lantana confirmed at EBTL
- local feeding
- local seed dispersal
- causality

Invoke:

```bash
python3 /bench/arm/input/skill_call.py local-bird-lantana-overlap '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
