# Codex review — Round 2 proposal set

Date: 2026-07-13

This review separates evidence acceptance from immediate IR growth. Repeated pressure is strong
evidence that a semantic gap is real; it is not automatically evidence that the first proposed
syntax is the smallest coherent solution.

| ID | Verdict | Reason |
|---|---|---|
| EVD-001 | accept | Already reconciled into v2.2; it fixes honesty at the connector boundary without burdening the parser. |
| ALG-001 | accept-partial | v2.2's list-valued `SELECT.entity` handles common positive unions. General set identity remains unresolved. |
| ALG-002 | accept | FILTER is independently forced by both sectors. Adopt only with typed connector fields and predicates. |
| ALG-003 | accept | GROUP is distinct from collapse-style AGGREGATE and has cross-sector evidence; keyed output semantics must be explicit. |
| ALG-004 | defer | Intersection/difference need an identity contract. Positive union is already covered. |
| ALG-005 | accept-partial | Accept units, grain co-scoping, and restricted derived arithmetic as a design direction; syntax waits for a typed-value RFC. |
| ALG-006 | accept-partial | Median/quantile pressure is established. Prefer a typed aggregate specification over ad-hoc metric strings. |
| ALG-007 | accept | Alignment is prerequisite infrastructure for honest cross-series operations; implicit nearest-year behavior is insufficient. |
| ALG-008 | defer | Valid need, but VERIFY depends on units, definitions, alignment, and lineage. Adding it first would encode unjustified agreement. |
| PLN-001 | accept-partial | Accept a no-half-gold completeness contract and upstream clause splitting now; defer BUNDLE until cross-clause dependencies demand it. |
| ASK-001 | accept | This is an honesty/protocol rule, not a data-kernel op. Causal claims require a design-bearing future layer. |
| SAT-001 | accept | Round 1 closure demonstrated why regression score is not saturation. Freeze epochs and discovery-rate stopping should become canonical. |

## Framework-diff disposition

The livelihoods snapshot differs from `kit/` in nine harness modules, the IR spec, and PROMPT.
Those files must not be copied wholesale back into the kit. Connector mappings are sector-local;
parser curricula and repairs require cross-sector regression; general coverage/freeze/audit tools
are reusable harness candidates; algebra changes require the proposal gate above. The snapshot's
v2.1 spec is historical evidence, while the kit's v2.2 spec is the current released baseline.
