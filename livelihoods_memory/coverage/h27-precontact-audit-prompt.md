# Independent H27 precontact semantic audit

Work in `/home/beeps/src/github.com/bprashanth/totalrecall/livelihoods_memory`.

Read ONLY:

- `algebra/ir-spec.md`
- `algebra/README.md`
- `coverage/source-census.json`
- `freezes/epoch-019.json`
- `questions/holdout-027.json`

Do not read or search any parser, connector, executor, scorer, audit, test, prompt, prior question
bank, run, corpus, report, finding, chronology, proposal, or git history. Do not contact qwen, another
model, the network, or public APIs. Do not edit the question bank or any existing file.

Independently audit all 100 H27 rows for natural-language/gold semantic agreement under frozen IR
v2.1. Check operand roles and orientation, places, entities, years, output heads, RANK candidate
closure/order/k, relation polarity/threshold/nesting, legal ESTIMATE source/target/method, exact hole
roles, source-gap-versus-hole status, `must_hole`, `must_estimate`, and whether any wording requests
semantics the gold silently drops. Treat `answer_or_data_request` as an outcome-class allowance, not
permission to weaken the question. Representation and direct execution have already been checked;
focus on semantic faithfulness.

Create exactly `coverage/h27-precontact-independent-audit.md`. State the number reviewed, list every
suspect row with a precise reason and safe precontact repair or exclusion, then give a final count of
accepted rows. If all rows are sound, say so explicitly. Create no other file.
