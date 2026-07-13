# Round 2 epoch 014 — H20 admission boundary

## Independent generation

H20 was authored after the epoch-014 freeze by Cursor Agent using Grok 4.5 High, an xAI-family
generator not used for H18 or H19. The generator was restricted to the frozen v2.1 algebra and
schema, connector vocabulary, source census, coverage matrix, Round 2 protocol, and epoch-014
manifest. It was forbidden from parser/scorer/audit code, all prior questions, runs, traces,
corpus, reports, chronology, repair history, and qwen contact. It produced exactly 80 candidates
(`h20-001` through `h20-080`); all 80 were schema-valid before parser contact.

The main judge audited rows 1–40. An independent blind judge audited rows 41–80 and separately
classified semantic validity, connector expectations, and coverage value. The final selection
prioritized ranks of endpoint-change subtrees, ranks of relational counts/densities, 7- and 8-item
list boundaries, supported and unsupported distance anchors, nested relation polarity,
co-occurrence record/count forms, mixed-source same-unit comparisons, ambiguity, explicit source
gaps, and one transfer control.

## Pre-run adjudication

Forty candidates were excluded before parser contact:

`h20-001`, `h20-008`, `h20-009`, `h20-010`, `h20-012`, `h20-013`, `h20-014`, `h20-015`,
`h20-016`, `h20-017`, `h20-018`, `h20-021`, `h20-025`, `h20-028`, `h20-029`, `h20-032`,
`h20-033`, `h20-034`, `h20-037`, `h20-039`, `h20-040`, `h20-041`, `h20-043`, `h20-044`,
`h20-045`, `h20-046`, `h20-047`, `h20-048`, `h20-049`, `h20-051`, `h20-053`, `h20-054`,
`h20-055`, `h20-056`, `h20-057`, `h20-060`, `h20-064`, `h20-065`, `h20-076`, and
`h20-077`.

`h20-025` was semantically ambiguous because “largest move” does not determine signed versus
absolute change. `h20-054` did not identify whether a co-occurrence count meant left records,
right records, or pairs. Most other exclusions were redundant controls or lower-priority variants.
During the connector-only audit, the Overpass endpoint became network-unreachable. Candidates
whose otherwise-valid golds produced an external harness error (`h20-032`, `h20-033`, `h20-034`,
`h20-045`, `h20-046`, `h20-049`, `h20-053`) were not relabeled as DataRequests; they were replaced
with independently valid, executable candidates so infrastructure failure could not become a
solver score.

Gold-only repairs preserved full requested literals for household-income microdata (`h20-072`)
and cooperative-membership density (`h20-075`) instead of treating the latter as geospatial
record density. Connector-sensitive OSM/ILOSTAT rows use `answer_or_data_request` only where
bounded, sparse, or survey coverage can legitimately vary. Explicit unsupported entities remain
literal source gaps with no semantic hole. No parser, prompt, scorer, semantic audit, executor,
connector, repair, or synthesis code changed.

## Frozen bank

The admitted bank is `questions/holdout-020.json`: 40 rows comprising 11 ranking, 9 state,
6 composite, 6 relation, 4 ambiguity, 2 change, 1 trend, and 1 transfer case. Its expectation mix
is 20 answer, 10 answer-or-data-request, and 10 data-request rows. SHA-256:
`7aa272f2772b0437f6dac5fed25a72e138aa5e6f116bc5dca085ea14f1f2a4d2`.

This checksum is the immutable pre-contact boundary. Any bank/gold edit or any core/harness change
invalidates H20. With no valid post-contact discovery, H20 would be untouched saturation pass 1
of the required 3; otherwise epoch 014 retires and the counter remains zero.
