# Valparai site-pack integration with Idlisseus

Date: 2026-07-25.

## Why

The Valparai pack already produced typed visual results, but it was not running as a selectable
Idlisseus endpoint. The goal of this pass was to integrate the real pack through the same generic
bridge and `idli-result/1` boundary used by the synthetic reference, without copying data into
Idlisseus or disturbing the live EBTL endpoint on port 7011.

## What ran

The existing producer-owned launcher built the Valparai visual index from
`dss/sites/valparai/`, pinned the bridge to that pack and started it on the Docker bridge address
`172.17.0.1:7012`.

The first registration attempt used the system Python. The index and bridge started, but importing
the Idlisseus database package failed because `httpx` was not installed in that interpreter.
Repeating registration with `chatbots/odysseus/venv/bin/python` succeeded. The Valparai README now
uses that interpreter explicitly.

No model server or Docker container was started, stopped or restarted. The existing Idlisseus
container was only checked for reachability. Port 7011 remained healthy and unchanged.

## Verification

Fifty-six tests passed across:

- real and synthetic pack builds;
- source adapters and denominators;
- typed result capabilities;
- immutable result payloads;
- pack-swap renderer contracts;
- site-pinned bridge routing; and
- uploaded CSV/Excel routing.

The live endpoint reported:

- model id `idli-insight-valparai`;
- 29 agent-visible skills;
- 19 typed, upload, estimation and earth-layer capabilities; and
- a healthy Hermes/Codex runner.

An `entity-record-map` smoke query for lion-tailed macaque returned a complete
`idli-result/1` result with 428 source-linked points, including 345 in target cells. Its immutable
GeoJSON handle returned all 428 features.

The endpoint record was registered in Idlisseus as **Idli Insight — Valparai** and the running
Idlisseus container reached its capability API through `host.docker.internal:7012`.

Finally, a real chat turn asked, “Tell me about this site.” The agent returned a short explanation
of record coverage and emitted one stored `idli-result` marker for the Valparai site-orientation
map. The response correctly described the map as data coverage rather than abundance, absence or
condition, and described the declared outline as a study boundary rather than a legal property
boundary.

## Result

Valparai is now a live, site-isolated Idlisseus option using the real Totalrecall pack. Pack data,
derived index state, results and audits remain in Totalrecall. Idlisseus owns only the endpoint
record, authenticated proxy and generic presentation.
