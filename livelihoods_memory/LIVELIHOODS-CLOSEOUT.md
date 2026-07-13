# Livelihoods Round 2 closeout

## Claim at stop

Livelihoods Round 2 stops by explicit cost decision at an **empirically hardened, frozen
development boundary**. It does **not** claim practical saturation under `SAT-004`, and it does not
claim hard three-bank saturation. The last countable untouched-pass counter is zero.

The exact boundary is epoch 022, freeze commit `65924a8`, confirmed through commit `73d4c48`.
H30 was authored and independently audited without parser contact, but was deliberately not
admitted, executed, or scored before stopping. It is diagnostic evidence, not a pass or failure.

## What was achieved

- The active wall contains 1,576 questions across 32 banks and 42 exact skeletons.
- All 1,573 eligible rows pass ordinary and strict canonical scoring.
- Synthesis/evidence scoring passes 1,576/1,576.
- Parser regressions pass 175/175; source probes pass 14/14; model and mechanical dialogue binders
  each pass 5/5.
- `freezes/epoch-022.json` hashes 62 active inputs; pre-freeze, post-artifact, and post-freeze walls
  plus two manifest verifications found no drift.
- H28 exposed 56 strict compiler failures and 30 synthesis-contract failures; its generalized
  absorption and wall narrowing are retained as disclosed development evidence.
- H29 independently exposed 43 strict failures across six mechanisms and two synthesis-contract
  failures. Generalized absorption reached 94/94 and motivated `ALG-012`.
- H30 added 100 parser-blind questions: 93 adversarial, 82 with at least three operations, 36 exact
  shapes, and 94 capability labels. Independent audit classified 57 accept, 28 narrowly
  repairable, 13 exclude, and two duplicate. The possible repaired survivor is 85 rows, but it was
  never constructed or shown to the solver.

## What was not achieved

- No qualifying post-epoch-022 bank completed immutable first contact, so practical saturation is
  unproven.
- Hard `3/3` saturation remains unattempted at this boundary.
- H30's 28 proposed repairs were not applied or re-audited, and its gold trees were not directly
  executed by the harness.
- Connector breadth remains the governed 14-probe census, not a claim of general real-world source
  coverage.
- Passing the historical wall proves retained behavior on registered questions, not unrestricted
  natural-language generalization.

## Improvements supported by the evidence

1. `ALG-013`: add an explicit, typed global `Field`-to-`Scalar` reduction. Seven H30 rows expose
   the missing global-count/global-mean contract.
2. `ALG-014`: give `RANK` candidates explicit question-warranted identities. Five clean H30 breaker
   patterns cannot be faithfully labeled by place/entity alone.
3. `BNCH-004`: make two-lane admission standard—expressible rows become immutable scored exams;
   non-expressible rows become durable algebra breakers.
4. Promote `ALG-012` only after Fable review and kit-level conformance tests; its sector
   implementation is strong evidence, not released framework behavior.
5. For subsequent sectors, use practical rather than hard saturation in the first pass, but stop
   when marginal discovery cost becomes disproportionate. Always publish the exact claim level,
   untouched counter, last freeze, and incomplete gates as done here.

## Durable evidence and handoff

- `REPORT.md`, checkpoints 17–22: chronological saturation decision and final status.
- `chronology/20260713_round2_epoch_022_h29_absorption.md`: last completed absorption and freeze.
- `coverage/epoch-022-certification.json`: exact active-wall certification.
- `coverage/h30-generator-prompt.md`, `coverage/h30-author-report.md`, and
  `coverage/h30-precontact-independent-audit.md`: untouched H30 generation and audit record.
- `../governance/review-packet-livelihoods-closeout.md`: Fable/orchestrator entry point.
- `../governance/proposals.json`: unreleased proposal registry.

Future work must not describe H30 as a saturation exam result unless it first creates a
reproducible admitted artifact and observes the unchanged epoch-022 solver under the original
protocol. Alternatively, H30 may remain permanently uncontacted and a newly bootstrapped sector or
later livelihoods round can start from whatever framework version governance has validated.
