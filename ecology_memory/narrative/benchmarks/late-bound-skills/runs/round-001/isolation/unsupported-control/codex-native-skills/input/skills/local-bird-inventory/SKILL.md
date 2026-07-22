# local-bird-inventory

Complete local 2024 EBTL bird checklist with survey method.

Use for:
- birds recorded locally
- local bird list

Do not use for:
- recent eBird feed
- abundance
- plant interaction

Invoke:

```bash
python3 /bench/arm/input/skill_call.py local-bird-inventory '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
