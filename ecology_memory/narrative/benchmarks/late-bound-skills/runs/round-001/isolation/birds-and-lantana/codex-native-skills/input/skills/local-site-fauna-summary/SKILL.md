# local-site-fauna-summary

Published EBTL 2024 survey group summaries for butterflies, odonates, birds and herpetofauna, with older-property herpetofauna records kept separate.

Use for:
- what wildlife or animal groups were recorded locally
- local survey coverage

Do not use for:
- complete non-bird species lists
- public occurrence points
- abundance
- proof of absence

Invoke:

```bash
python3 /bench/arm/input/skill_call.py local-site-fauna-summary '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
