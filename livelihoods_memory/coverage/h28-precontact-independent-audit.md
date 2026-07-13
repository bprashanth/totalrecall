# H28 precontact independent audit

Reviewed: all 100 raw rows, without parser, model, network, execution, run, corpus, or prior-bank
access. The audit used only the frozen IR v2.1 specification, Round-2 protocol, epoch-020 freeze
manifest, source census, and raw H28 bank.

## Result

Eighty-nine rows were accepted as written. Five had semantic defects that are safely repairable
without adding an algebra or parser mechanism:

- `h28-011` requested the *nearest* bank, while frozen `RELATE(distance)` attaches distance but has
  no minimum/nearest operator. Admission removes “nearest” from the question.
- `h28-035`, `h28-036`, and `h28-046` explicitly requested earlier-over-later temporal ratios.
  Frozen v2.1 canonically executes different-year ratios as later/earlier. Admission reverses the
  written roles and raw gold operands so the requested answer and executable denotation agree.
- `h28-076` used “there” while declaring an unknown target. “There” resolves to Dakar, so admission
  instead says “another, unspecified place,” preserving the intended precise target hole.

The audit also noted that seven valid `beyond` rows exposed a documentation inconsistency: v2's
normative negation section defines `beyond`, and the frozen schema/executor implement it, but the
formal vocabulary summary accidentally omitted it. The summary was corrected to
`distance | within | beyond | cooccur`; this is a non-behavioural erratum, not a new algebra op.

Six fixed source-gap rows (`h28-080`, `092`, `093`, `098`, `099`, `100`) could not prove their hard
DataRequest expectations from the bounded census alone because the census is not an exhaustive
negative-capability declaration. The separate frozen-connector execution supplied that missing
warrant: all six returned typed DataRequests. Their exact expectations are therefore retained.

All gold shapes, recursive hole flags, RANK candidate closure/order/k, ESTIMATE source/target/method
roles, fixed unsupported literals, and the remaining operand scopes passed. Warsaw's three regional
trees require only the already reviewed connector-label alias from `Warsaw capital region, Poland`
to `Warsaw capital region`; question scope remains Poland.

Final admission result: 100/100 semantically acceptable after the five recorded repairs; no
exclusions and no parser contact.
