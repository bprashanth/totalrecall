# Round 2 epoch 017 — H25 admission boundary

H25 was authored after commit `dbcce44` by Cursor Agent using GPT-5.6 Sol High. The generator was
restricted to the frozen IR documents, Round 2 protocol, source census, aggregate coverage matrix,
and epoch-017 manifest. It was explicitly forbidden from reading the parser, scorer, audits, tests,
prior questions, runs, corpus, reports, findings, chronology, proposals, caches, or git history; it
could not call qwen, execute trees, or use the network. The invocation prompt is preserved at
`coverage/h25-generator-prompt.md`. Cursor wrote only the 96-row raw pool
`questions/holdout-h25-generated.json`.

The main judge validated all 96 tree schemas and preorder shapes, then executed every gold directly
before parser contact. Ten raw expectations did not execute: three requested computed annotation
layers unavailable from the selected rows, five reached known OSM truncation limits, and two used a
Warsaw spelling the current region resolver could not resolve. Those candidates were not admitted.
No solver change was made. A transient first execution of H25-034 returned a connector RuntimeError;
the cached replay and subsequent direct execution returned the complete 47-row-derived count, so it
was treated as upstream transport noise rather than a reproducible executor class.

Raw exact-year golds used scalar strings. Although structurally valid, the connectors interpret a
bounded request only from `{start,end}`. Before selection, every exact year was therefore normalized
to a one-year window and all golds were executed again. This is an admission repair to generated
gold, not a parser or harness repair. Transfer notes were also changed from unconditional source
claims to conditional statements about Records-typed sources and honest gate failure.

An independent parser-blind judge audited rows 49–96 without model or network contact. Its strict
census-only pass correctly rejected claims not explicitly demonstrated by the small source-census
sample. The main judge did not treat that sparse sample as an exhaustive connector allowlist: for
the selected statistical rows, precontact direct execution returned exactly one requested annual
point per operand with route, source/table, unit, and observation flags. That stronger row-level
evidence admitted H25-051, 061, 062, 064, 065, 067, 068, and 073. The independent semantic audit
found no tree/orientation/cardinality defect in those rows; its objection was evidence scope only.

The selected 40 rows are balanced across eight state/source controls, eight spatial relations and
compositions, eight temporal/arithmetic questions, eight ranks, four transfers, and four
ambiguity/behaviour/source-gap questions. They exercise OSM records including the new metro route,
World Bank country series and Gini, ILOSTAT, Eurostat NUTS-2 data, within/beyond/cooccurrence and
two-anchor composition, worded fractions, counts/presence/density, level/change/trend/ratio,
winner/intermediate/full ranks, ranked endpoint changes and ratios, all three ESTIMATE methods,
typed holes, behavior proxies, and a fully bound non-curated source gap.

The immutable bank is `questions/holdout-025.json`. Its SHA-256 is recorded by the preparation
command and the commit that follows this chronology. It becomes untouched pass 1 only if ordinary
execution, strict canonical audit, synthesized-answer and provenance review, and mismatch
adjudication identify no valid parser, connector, executor, scorer, audit, corpus, or framework
repair. No expectation or gold may change after qwen contact.
