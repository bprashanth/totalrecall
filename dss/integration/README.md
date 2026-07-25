# Producer–consumer integration exchange

This directory is the Totalrecall-owned outbox for changes that may affect an Idlisseus
consumer. It keeps site-pack, data and result production in Totalrecall while allowing the
Idlisseus owner to accept, refine or reject presentation changes without either agent editing
the other repository.

## Ownership

- Totalrecall owns and writes `totalrecall/dss/integration/proposals/`.
- Idlisseus reads those proposals but does not edit them.
- Idlisseus owns and writes `idlisseus/dss/integration/responses/`.
- Totalrecall reads those responses but does not edit them.
- The normative wire contract remains
  `idlisseus/dss/VISUAL_RESULT_CONTRACT.md`. A proposal is not a contract change until the
  Idlisseus owner accepts it and updates the contract or renderer fixtures.

## Exchange layout

```text
totalrecall/dss/integration/
├── README.md
├── proposal.schema.json
├── check_exchange.py
└── proposals/
    ├── index.json
    └── <proposal-id>/
        ├── proposal.json
        ├── README.md
        └── fixtures/ or screenshots/       optional

idlisseus/dss/integration/
└── responses/
    └── <proposal-id>/
        ├── response.json
        ├── README.md
        └── fixtures/ or screenshots/       optional
```

The Idlisseus response JSON should contain:

```json
{
  "schema_version": "producer-consumer-response/1",
  "proposal_id": "TR-VIS-0001",
  "consumer": "idlisseus",
  "disposition": "accepted|accepted_with_changes|implemented|deferred|rejected",
  "consumer_commit": null,
  "contract_version": "idli-result/1",
  "summary": "What changed or why it did not change",
  "producer_action_required": [],
  "validated_fixtures": [],
  "updated_at": "YYYY-MM-DD"
}
```

## Lifecycle

1. Totalrecall finds a producer/consumer mismatch.
2. It adds one immutable proposal directory and appends it to `proposals/index.json`.
3. The proposal carries a minimal generic payload example, requested behaviour, compatibility
   assessment and acceptance checks. It must not require the consumer to understand a sector.
4. Fable reads the index, implements or declines the proposal in Idlisseus, and writes an
   Idlisseus-owned response under the same proposal id.
5. Totalrecall runs `check_exchange.py`, reads the response, and performs any named producer
   follow-up. An implementation is considered integrated only after the real producer result and
   the consumer fixture both pass.

Neither side marks the other side's work complete. Commits and fixture evidence in the response
are the hand-off.

## Checking for responses

From the Totalrecall repository:

```bash
python3 dss/integration/check_exchange.py
```

The default response directory is the sibling checkout
`../idlisseus/dss/integration/responses`. A different checkout can be supplied with
`--responses`.
