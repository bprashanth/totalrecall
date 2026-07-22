# published-vegetation-survey-sites

Twenty-six published Anamalai vegetation survey sites from Zenodo 10077040.

Use for:
- published vegetation survey locations around Valparai or Anamalai

Do not use for:
- restoration projects
- invasive-removal interventions
- restoration outcomes

Invoke:

```bash
python3 /bench/arm/input/skill_call.py published-vegetation-survey-sites '{"region":"EBTL"}'
```
For a named-taxon skill add `entity`; add `radius_km` only when the user explicitly asks to widen a search. Only include arguments the question supplies or the conversation has established. The command returns audited JSON.
