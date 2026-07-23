# Site-ecology dialogue benchmark report

Run date: 24 July 2026

## What was tested

The benchmark contains 11 conversations and 39 turns. It covers onboarding, ambiguous vernacular
groups, sparse species, nursery and tree planning, invasive recurrence, fire, restoration
comparison, biotic interactions, repeat-detection design, water/soil/greenness, connector failure,
maps, protocols, dashboards and reports.

The tested arm is the architecture actually intended for Idli Insight:

```text
Codex default model: dialogue, clarification and connector arguments
  -> admitted local/public evidence
  -> one evidence-bound scientific question
  -> local Algebra 9B-004d: frozen scientific IR only
  -> controller validation, binding and deterministic execution
  -> observed/modelled/designed visual and next action
```

The 9B model is not a post-hoc verifier and does not receive the skill catalogue. No DeepSeek or
LoRA “verification pass” arm is reported because that would still leave GPT doing the substantive
work and would not answer the model-wrapper question.

## Results

The complete `overnight-001` pass produced:

- `39` completed turns;
- mean contract score `0.833`;
- `24/39` perfect turns;
- `0` critical evidence failures;
- median first progress `0.002 s`;
- median first completed skill `0.008 s`;
- median final answer `14.473 s`.

Ambiguous-group clarification, repeated-detection survey design and source-outage invariance scored
`1.0` on every turn. Restoration comparison averaged `0.938`. The weakest conversation was
interaction/colocation (`0.646`): its first two evidence stages passed, but the fixed script then
continued without selecting the assistant's returned bird and Eucalyptus clarification. A future
runner should select validated `insight_actions` dynamically rather than treating every
conversation as a fixed transcript. Nursery/protocol/dashboard and water/soil overview handoffs
also remain partial. These are completeness failures, not hidden evidence failures.

Focused regression dialogues after fixes produced:

- broad site orientation → local evidence → dashboard: final two turns `1.0`, with a responsive
  six-result dashboard and one declared geometry gap;
- historical fire exposure: first turn `1.0`; the admitted result arrived in `0.022 s` and remained
  a historical proxy rather than next-week fire probability;
- deliberate occurrence outage: retrieval repeat `1.0`; the same estimand and source family were
  retained and no source lottery was used;
- bird–Eucalyptus interaction: first turn `1.0`; model knowledge became a connector query seed,
  and no feeding/colocation row became a dispersal claim;
- sparse species: evidence → Algebra 9B → nine-point designed field map completed; a valid
  AOI-wide estimate without a ranking surface was not presented as hotspot prediction.

The accumulated dashboard first took about `79.7 s` before deterministic presentation prefetch.
After the fix, the dashboard result is emitted in `0.30 s` and the explanatory answer completes in
about `8.6–13.0 s`. Fire/site/local prerequisites also emit their first audited result in roughly
`0.01–0.03 s`. Network-dependent discovery and resumed Codex turns remain slower.

## Bugs found and general fixes

1. **Unrelated local-asset substitution.** A fire question could retrieve nursery data. Capability
   routing now binds fire exposure and greenness-trend measurement families before dialogue.
2. **Model-memory source claims.** Wider occurrence and biotic-relation questions could cite
   remembered URLs without a connector call. The prompt contract now requires admitted connector
   lineage; benchmark fault injection verifies exact-source failure behaviour.
3. **Per-turn scoring lost prior evidence.** The scorer now evaluates the conversation audit
   ledger while retaining a per-turn audit record.
4. **Map omission after a valid estimate.** Explicit natural-language map intent is checked for
   completion. If Codex finishes the science but omits rendering, the controller uses the latest
   admitted taxon and completes the already-requested map.
5. **No-points visual dead end.** Failed gates and unavailable occurrence sources now produce
   stable `FIELD-...` collection points. They are labelled `Designed`, never observed or predicted.
6. **Source outage bypass inside map rendering.** The renderer now honours the same occurrence
   outage. Without source-identified cache it creates new collection points instead of querying a
   different connector.
7. **Flaky GloBI relation filter.** A live `interactionType` server error retries the same
   source/target query and filters the requested relation locally. The fallback is audited; no
   alternative evidence source is substituted.
8. **Recursive dashboards.** Dashboard envelopes are views, not ecological results, and are
   excluded from subsequent dashboard refreshes.
9. **Mobile field sheet clipping.** The narrow map view now changes its point table into labelled
   stacked cards.

All routing is by capability, evidence kind and declared arguments. No elephant, tortoise, viper,
Eucalyptus or other species-specific skill was added.

## Visual evidence

- [Chat evidence, wide](runs/smoke-site-002/screenshots/chat-evidence-wide.png)
- [Chat evidence, narrow](runs/smoke-site-002/screenshots/chat-evidence-narrow.png)
- [Evidence dashboard, wide](runs/smoke-site-002/screenshots/idli-dashboard-wide.png)
- [Evidence dashboard, narrow](runs/smoke-site-002/screenshots/idli-dashboard-narrow.png)
- [Source-outage collection map, wide](runs/final-outage-002/screenshots/idli-map-wide.png)
- [Source-outage collection map, narrow](runs/final-outage-002/screenshots/idli-map-narrow.png)

The dashboard and map captures are the actual persisted HTML documents. The chat evidence capture
uses the production renderer/CSS fixture because the public chat URL is behind Cloudflare Access in
this environment; no credentials were bypassed.

## Verification

- Totalrecall ecology suite: `269` tests passed.
- Idlisseus focused bridge/UI suite: `15` tests passed.
- Bridge health after restart: `gpt-5.4`, Hermes execution boundary, `23` skills.
- The runner only observes the existing bridge. It never starts or restarts the local model server
  or Docker container.

The benchmark is a development and regression instrument, not ecological validation. A high score
means the answer, audit, gates and artefacts satisfy the declared evidence contract; it does not
mean a field estimate is biologically correct without independent validation.
