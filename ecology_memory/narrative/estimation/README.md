# Ecology estimation benchmark

This is the larger follow-up to the frozen five-question ecology narrative pilot. It asks what
happens when conservation staff need an estimate because field access is expensive, seasonal,
dangerous, permission-limited, or simply too slow for the decision in front of them.

Start with [DESIGN.md](DESIGN.md) and [bank.json](bank.json). Raw outputs are retained under
`runs/<model>/<question>.json`. This is a separate benchmark version: it does not alter or rescore
the five-question pilot in the parent directory.

The completed result is presented in the [estimation narrative](index.html), with a written
[results report](RESULTS.md) and clickable [evidence wall](evidence.html). Final scores are in
[scoring.json](scoring.json); every audit correction to the first-pass rubric coding is declared
in [audit_overrides.json](audit_overrides.json).

The agents see only ordinary questions such as “is the plot improving?”, “is X near Y?”, “is this
changing through time?” and “what is likely here when observations are sparse?” They receive no
connector catalog, source pack, dataset, estimator or fit gate. The hidden evaluation asks whether
they independently discover when the problem calls for an SDM, random forest, satellite proxy,
temporal comparison, spatial transfer, occupancy/detectability model, causal design, or a field-data
request—and whether they keep the resulting evidence state intact.

Reproduce the final aggregate with:

```bash
python3 finalize_scoring.py
python3 score.py
```
