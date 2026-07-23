# Codex background + Algebra 9B data planning — 2026-07-23

## Why

The broad question “tell me about the site” was compiled as the literal entity `EBTL site`. The
local entity search returned no match, then wider semantic discovery tokenised “Elephants by the
Lake” as an elephant topic and returned unrelated elephant datasets. A broad onboarded-site
inventory needs a different operation from entity search.

The previous multi-model benchmark also used Codex for every skill decision and sent its completed
answer to 9B only as a verifier. That did not test 9B as the data planner.

## What changed

- `site-overview` compiles the onboarded profile, analysis geometry, six local evidence partitions,
  configured capabilities, uploaded geometry assets and explicit gaps into one labelled snapshot.
- `plan-data-with-algebra-9b` calls the already-running local 9B-004d Chat Completions endpoint.
  The server supplies the immutable question, permitted catalogue and audited prior plan outcomes.
- The 9B result is a bounded plan envelope outside the frozen scientific Algebra. Code validates
  skill ids and arguments, stores a plan id and allows only the exact next planned skill.
- Codex cannot invoke a data skill before planning, change the planned arguments or silently switch
  to another skill. It may replan up to three times after a partial or failed result.
- Answers separate labelled model background from labelled Idli Insight results. Guided site
  follow-ups offer local wildlife, invasive management and fire history.

## Verification evidence

A live direct 9B probe for `tell me about the site` returned one valid `site-overview` step in about
ten seconds. The planner response made no connector call or scientific claim.

The first full bridge probe failed closed because the prompt described the planner as an invokable
tool even though Codex-native skills are command-backed wrappers. The prompt now supplies the
session-bounded `SKILL.md` path and exact wrapper command and explicitly says not to wait for a
named tool. A second fresh bridge probe completed the intended sequence:

1. Codex produced three `[Model background]` sentences without opening local data.
2. Algebra 9B-004d selected one `site-overview` step.
3. The gateway bound and completed that exact step.
4. Codex returned separately labelled local profile, geometry, wildlife, nursery, resource-census,
   capability and missing-property-boundary findings.
5. The controller offered wildlife, invasive-management and fire-history follow-up actions.

That turn took 68 seconds, including two shell-quoting retries discovered by the probe. The supplied
planner command was then changed to avoid an apostrophe in its JSON argument, removing that retry
path for subsequent turns.

Forty-five unit tests cover site-versus-taxon routing, profile inventory, plan validation,
immutable-question handling, exact ordered binding, site follow-up actions and existing ecology
regressions. The server also passes bytecode compilation, the new skill passes `quick_validate.py`,
and `git diff --check` is clean.

This is a hybrid development trial, not a pure-9B agent result and not a saturation claim.
