# Fieldnote platform guide

## What Fieldnote is for

Fieldnote is a visual field notebook for practitioners who begin with a place and a question.
The intended loop is:

1. **Orient** — start with a map, coverage and survey effort rather than an empty chat.
2. **Ask** — use ordinary ecological language: a species, season, interaction, restoration
   question or paper method.
3. **See** — return the most useful map or figure before a long explanation.
4. **Read responsibly** — keep provenance, denominators and limitations beside the visual.
5. **Refine** — narrow time, place, species or evidence conditions with a short follow-up.
6. **Act** — inspect source records, reproduce a plot in R, plan data collection, or carry a
   collection of findings into a report.

It is not intended to be a general chat window with charts attached. Conversation chooses and
refines analyses; typed data capabilities create the evidence and visuals.

## Runtime model

```text
practitioner
    |
    v
Fieldnote UI
    |-- aggregate site atlas (fast orientation)
    |-- question and method workbench
    |
    +--> Valparai bridge
    |       |-- Codex CLI in Hermes
    |       |-- admitted site capabilities
    |       `-- idli-result/1 answers, actions and data handles
    |
    `--> R sidecar
            `-- bounded rows -> reproducible ggplot SVG
```

The browser does not receive the bridge token. Fieldnote's server route calls the bridge, follows
immutable result handles, and presents the answer and visual payloads. The R sidecar receives only
the rows needed for a declared figure; it does not independently search the data pack.

## Current operating modes

| Mode | Address | What works |
|---|---|---|
| Local live studio | `http://127.0.0.1:7300` | Codex/Hermes, 29 Valparai skills, audited result payloads, exact live maps, paper reading and R figures |
| Owner-only Sites deployment | `https://valparai-fieldnote.prashanthseven.chatgpt.site` | Aggregate atlas, browser figures, responsive UX and deterministic preview guidance |

The Sites deployment is presently an atlas and design review surface, not the live analytical
service. Sites runs at the edge and cannot reach this host's private Docker address
`172.17.0.1:7012`. It also has no bridge token configured. Calls therefore fail closed into an
explicit preview instead of inventing a data-backed answer.

## A verified question

Question:

> Give me the squares where elephant and leopard records overlap, and show them on a map.

The local live path returned:

- 21 shared 1.1 km squares inside the target;
- 15 shared squares with records from the same year;
- 101 squares with elephant records and 30 with leopard records;
- observed and derived GeoJSON layers, source lineage and an immutable audit;
- the necessary warning that a shared square is neither an interaction nor simultaneous presence.

This confirms that the bridge and `co-occurrence-map` capability answer the question. It also
exposes two separate presentation boundaries:

1. The hosted Sites worker cannot currently reach the bridge, so it returns preview mode.
2. The first generic live-result renderer draws point overlays but does not yet draw returned
   polygon/cell layers. The co-occurrence payload exists even when its cells are not rendered by
   Fieldnote.

These are deployment and rendering gaps, not missing data or a failed analytical capability.

## Intended production topology

The preferred production shape is a narrow HTTPS analysis gateway in front of the existing
bridge:

```text
Fieldnote production worker
        |
        | authenticated HTTPS; short-lived/scoped credential
        v
analysis gateway
        |
        +--> bridge / Codex / Hermes
        +--> result and payload service
        `--> R rendering jobs
```

The gateway should expose only the required health, chat, result-query, result-read and bounded
plot operations. It should enforce user identity, site scope, rate limits, payload limits and
audit logging. Port 7012 and its filesystem token should remain private.

For a proof of concept, the simpler alternative is to serve Fieldnote beside the bridge on this
host and give users access through an authenticated reverse proxy. That is the current fully
functional mode. The hosted Sites version should remain aggregate-only until the gateway exists.

## Result and visual contract

The durable boundary is `idli-result/1`, not bespoke page code. A result supplies:

- the resolved question and bindings;
- evidence classes and claim limitations;
- one or more typed visuals;
- immutable `data_ref` payload handles;
- follow-up actions;
- source versions and audit identity.

Fieldnote should grow into a generic renderer for these visual types:

- point, cell, polygon and raster maps;
- distributions and comparisons;
- time series and seasonal profiles;
- matrices and heat maps;
- network or interaction views;
- metric summaries and source tables.

New site packs should add data and capabilities behind this contract. They should not require a
new chat interface or species-specific UI.

## Progress captured

- Visual-first desktop and mobile studio implemented and screenshot-checked.
- Aggregate Valparai atlas generated from the serving index.
- Local Codex/Hermes bridge integrated without exposing its token to the browser.
- R 4.5.1 sidecar produces ggplot SVGs for seasonal, restoration and acoustic views.
- Paper-to-method flow distinguishes a first-look analogue from a true replication.
- Live occurrence and co-occurrence questions verified against audited result payloads.
- Production dependency audit reports no production vulnerabilities.
- Sites version 1 deployed owner-only; local live containers remain on ports 7300 and 7331.

Source checkpoints:

- `77b4ba1` — Fieldnote visual ecology studio
- `374e7e2` — Sites build adapter
- `f102b05` — tracked runtime libraries
