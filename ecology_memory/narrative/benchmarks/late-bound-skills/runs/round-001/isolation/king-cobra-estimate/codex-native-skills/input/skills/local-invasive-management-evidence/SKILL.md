# local-invasive-management-evidence

Local documented non-native plant management, bounded public occurrence counts and regional literature leads, with missing local outcome measurements explicit.

Use for:
- what invasive management is documented locally
- known evidence and gaps

Do not use for:
- before-after outcome
- Lantana confirmed locally
- satellite invasive extent
- causal effect

Invoke:

```bash
python3 /bench/arm/input/skill_call.py local-invasive-management-evidence '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
