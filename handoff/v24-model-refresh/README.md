# v2.4 model-refresh handoff

Status: **ready for a clean diet rebuild; no training or promotion has been performed by this
handoff**.

This is the operator-facing packet for the parser-visible v2.4 bundle. Its scope is deliberately
limited to the generic BUFFER and FILTER contracts. It does not require sector discovery, source
review, connector research, or changes to GROUP.

## Frozen contract

- `BUFFER(source: REGION, radius_km) -> REGION` controls retrieval/search support.
- `RELATE.threshold_km` controls distance between returned records. It is never a substitute for
  BUFFER radius.
- `FILTER(source: Records, where:[predicate,...]) -> Records` applies an AND-only conjunction over
  connector-declared fields.
- FILTER values are compatible JSON literals or typed holes. `null` is not a FILTER literal in
  this version; questions requiring `is null` or `is not null` are outside the frozen surface.
- GROUP is absent and remains governed separately.

The released v2.3 profile must continue to reject BUFFER and FILTER. Only a model bundle explicitly
carrying the v2.4 algebra version may receive the new prompt surface.

## Admitted inputs

The content-addressed manifest is [manifest.json](manifest.json). The diet builder must consume:

1. the complete currently promoted training diet as retention;
2. one pre-admitted v2.3 origin-retention shard;
3. one pre-admitted clarification shard;
4. the 20-row execution-verified v2.4 surface corpus; and
5. additional correct-by-construction BUFFER/FILTER discrimination variants.

The provenance owner materializes the two private shards under neutral staging names and verifies
their hashes before the operator begins. Their semantic contents do not need another review. The
operator must not search for, reinterpret, relabel, or selectively edit those examples.

## Required sequence

1. Rebuild the candidate diet from the admitted inputs. Do not resume or reuse a previously
   generated candidate diet.
2. Validate every compiler target with the explicit `v2.4.0-draft` schema before admitting it.
3. Fixture-execute every generated BUFFER/FILTER gold that has an executable fixture.
4. Reject duplicates, evaluation leakage, undeclared fields, `ne null`, invented defaults, and
   questions whose requested predicate is outside the frozen algebra.
5. Record counts and SHA-256 hashes for every stratum and the final shuffled diet.
6. Train a new candidate name; never overwrite a promoted adapter or merged model.
7. Evaluate the candidate before any serving alias changes.

## Promotion gates

- Gold execution remains 20/20 on the coordinated BUFFER/FILTER bank.
- Parser-required conformance is 15/15 exact canonical matches.
- A separately frozen, unseen paraphrase wall reaches at least 95% overall, with zero failures on
  radius-versus-threshold separation, missing-radius holes, predicate preservation, and unsupported
  predicate refusal.
- Released-v2.3 retention has no material aggregate regression and no critical-class regression.
- The candidate at least matches the currently promoted model on the pre-registered multi-turn
  Hermes comparison for correctness and grounding.

Passing the 15 training-visible cases is necessary but is not evidence of generalization by
itself. The unseen wall and retention wall are mandatory.

## Existing-candidate warning

A prior draft diet contains FILTER examples whose value is `null`, outside the frozen contract.
Its associated training trace does not establish a completed adapter. Treat that draft as rejected
input. Rebuild from the hashes in this packet.

## Service boundary

Training may produce an adapter and merged candidate without altering a shared inference service.
Starting, stopping, restarting, or repointing a shared model server is a separate authorized
operation. If no isolated candidate endpoint already exists, stop after producing the ready-to-
serve artifact and instructions for the service owner.

