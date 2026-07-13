# H26 first-contact independent mismatch audit

Work in `/home/beeps/src/github.com/bprashanth/totalrecall/livelihoods_memory`.

Read:

- `algebra/ir-spec.md`
- `questions/holdout-026.json`
- `runs/epoch018-retired-holdout-026/traces.jsonl`
- `coverage/semantic-audit-epoch018-retired-holdout-026.json`
- `coverage/synthesis-audit-epoch018-retired-holdout-026.json`

This is read-only adjudication. Do not call qwen, network services, or another model. Do not inspect
or edit parser, executor, scorer, connector, synthesis, tests, prior banks, or prior runs. Create
only `coverage/h26-first-contact-independent-audit.md`.

Audit every non-perfect ordinary row and every strict canonical mismatch. For each, classify it as:

1. valid general compiler/binder gap;
2. harmless canonical-equivalence/audit normalization gap;
3. benchmark/gold defect;
4. executor/synthesis/evidence defect;
5. source volatility only.

Explain the smallest general semantic rule required, without proposing question-ID patches. Pay
special attention to answer heads, cross-place operand closure, nested relations, temporal aliases,
ranking candidates/cardinality/direction, unresolved-role holes, transfer source composition,
source/provider and place aliases, and whether the delivered prose contradicts typed execution.

End with counts by class, a deduplicated discovery-family list, and an explicit statement of whether
H26 could count toward saturation (it cannot, because epoch 018 was already retired precontact).
