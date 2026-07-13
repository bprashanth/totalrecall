# Round 2 epoch 018 — H26 admission and precontact retirement

## Independent generation

H26 was generated after the exact epoch-018 freeze commit `3661348` by Cursor Agent using
GPT-5.6 Sol High. The allowlist in `coverage/h26-generator-prompt.md` exposed only the frozen algebra,
Round-2 protocol, source census, coverage matrix, and freeze manifest. It forbade parser, scorer,
executor, connector, prior-bank, prior-run, corpus, report, chronology, network, and qwen access.
The resulting 96-row raw pool is `questions/holdout-h26-generated.json`, SHA-256
`942247b2b7f1327b0a38e3b4526ae2740a3fbd153406dfb8590a0f4e60fc2a01`.

## Qwen-free admission

An independent semantic audit accepted 92 surfaces and rejected or required repair for four:

- `h26-020` said “at least” while frozen `beyond` is strict; the admitted wording says “more than”;
- `h26-060` explicitly constrained the provider to World Bank, which frozen SELECT cannot encode,
  so it is excluded;
- `h26-075` left signed versus absolute change ambiguous; the admitted wording explicitly orders
  signed 2022-minus-1992 changes;
- `h26-087` treated “there” as unresolved despite its immediate Guadalajara antecedent, so it is
  excluded rather than assigned a false hole.

The main audit also clarified `h26-049` as the frozen later-over-earlier temporal ratio and
`h26-070` as Madrid region rather than Madrid city. The generator had wrapped one-year statistical
levels in invalid mean-by-space aggregates; `harness/prepare_h26.py` removes only those wrappers,
normalizes the verified Warsaw regional alias, recomputes exact shapes, and executes every gold.
Eight hard-Answer candidates were then excluded on direct evidence: empty selected station sets
(`h26-006`, `h26-018`, `h26-019`), completeness-cap failures (`h26-012`, `h26-021`, `h26-022`,
`h26-023`), and a wholly absent annotation (`h26-016`). These are benchmark-admission defects,
not solver discoveries.

The admitted immutable bank is `questions/holdout-026.json`, SHA-256
`0ec26875ede08c865358f6f2584a496b6d8c96565c9c6874d54f588dd572f794`. It contains 86 rows,
10 question types, 55 capability families, 22 exact gold skeletons, 61 adversarial rows, six typed
hole rows, and ten transfer rows. Declared outcomes are 48 Answer, 30 Answer-or-DataRequest, and
eight DataRequest; direct execution produced 66 grounded answers and 20 honest DataRequests.
No parser-under-test call occurred before this checksum.

## Discovery before parser contact

The live direct-gold audit exhausted bounded retries for a verified spatial source. The connector's
transport RuntimeError escaped as generic executor `error`, although the plan was valid and the only
missing input was temporarily unavailable evidence. This violates the framework's evidence
taxonomy: an outage is neither no connector, no records, truncation, nor a failed query plan.

The executor now returns typed `source_unavailable`; deterministic synthesis says the source is
temporarily unavailable, explicitly says this is not evidence of absence, and asks for retry or a
verified alternate connector. The synthesis wall audits this distinction. Regression count is now
144. Governance proposal `BUG-008` records the shared-framework contract for Fable review.

## Saturation decision

This was a valid executor/answer-boundary change before any H26 parser contact. Under `SAT-003`, it
retires epoch 018 and resets the counter, even though there is no contaminated score to preserve.
H26 will be contacted only as disclosed development pressure so its broad 86-row surface can expose
compiler gaps before the next expensive wall. It cannot count as an untouched pass because its raw
questions predate the next exact checksum freeze. After H26 absorption and full wall certification,
the three-bank sequence restarts with entirely new post-freeze banks.
