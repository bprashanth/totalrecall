# semantic-literature-discovery

BGE-small semantic search over admitted paper and dataset content cards, returning ranked DOI, title and column leads.

Use for:
- find studies or datasets by meaning
- Lantana and bird literature

Do not use for:
- local observation
- causal finding
- automatically admitted extracted points

Invoke:

```bash
python3 /bench/arm/input/skill_call.py semantic-literature-discovery '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
