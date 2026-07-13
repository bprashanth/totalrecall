# Independent blind H30 gold-audit protocol

The auditor is a fresh context-free agent distinct from the H30 author. It may read the H30 raw
bank and author report plus exactly the specification and boundary files allowed to the author:
`algebra/README.md`, `algebra/ir-spec.md`, `ROUND2.md`, `coverage/source-census.json`, aggregate
metadata in `coverage/matrix.json`, `freezes/epoch-022.json`, and
`coverage/h30-generator-prompt.md`.

The auditor must not inspect or invoke the parser, compiler, repair, scorer, executor, connector,
or audit implementation; prior question banks; runs or traces; corpus rows; earlier holdouts or
failure maps; reports, chronology, proposals, or git history/diffs. It does not edit the raw bank.

Every row receives one disposition:

- `accept`: wording uniquely warrants the entire frozen-v2.1 tree and declared outcome;
- `repairable-precontact`: a narrow wording or gold correction can remove ambiguity without
  introducing a parser-targeted mechanism;
- `exclude`: frozen v2.1 cannot express the request, the intended gold is materially debatable,
  evidence is unwarranted, or repair would change the challenge; or
- `duplicate`: the semantic and linguistic pressure is not sufficiently distinct.

The auditor checks literal provenance, entity/place/time/subgroup locality, direction and threshold
polarity, spatial predicate order, rank candidate cardinality and ordering, binary operand
completeness, estimate source/method/target typing, typed-hole dominance, output head, expected
execution class, exact preorder shape excluding REGION, and agreement of recursive hole/estimate
flags. It also checks the bank-level adversarial, three-operation, sibling-local, family, and
skeleton-diversity requirements.

The deliverable is `coverage/h30-precontact-independent-audit.md`, listing every non-accepted ID,
the exact reason and safe repair if any, totals by disposition, and whether the surviving bank can
meet `SAT-004` without relying on a disputed row. Admission remains the root judge's decision and
occurs before any parser contact.
