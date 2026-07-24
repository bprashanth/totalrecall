# Guided Codex investigation trial — 2026-07-23

## Why

The Codex-native ecology chat was producing compact but terminal answers: it reported local
evidence and what was missing, then stopped. Field users need a shorter, staged dialogue that can
offer wider retrieval, a raw visual, modelling and confirmation sites without silently doing all
of those expensive or assumption-changing operations at once.

The scientific Algebra already has typed holes for missing values. This trial deliberately leaves
that frozen schema unchanged and adds a session-level continuation envelope for optional user
decisions.

## What changed

- Codex is instructed to perform one evidence-bearing stage per turn unless the user explicitly
  requests a complete workflow.
- The bridge records completed skill calls and derives up to three next actions from a generic
  capability graph.
- Pending actions and a bounded investigation history persist with the resumable Codex session.
- Selecting an exact action label binds controller-owned entity/region arguments and limits that
  turn to the authorized skill set.
- Named taxa returned by local evidence proceed to a bounded occurrence search. Broad topics
  proceed to source discovery. Common-name punctuation is normalized at the connector boundary.
- Failed or empty occurrence retrievals cannot offer mapping or transfer.
- Discovery results are offered for inspection only when a focal query term occurs in the returned
  title.
- `build-ecology-field-map(map_mode="observed")` maps and exports raw returned occurrences without
  invoking an estimator or generating field-request points. Modelled mapping remains a separate
  action.
- Odysseus forwards the validated actions into its existing durable `ask_user` card and restores
  the card from saved message metadata.

## Live Codex-default smoke

Disposable bridge: port 7012, existing `hermes-live` container, model `gpt-5.4`, reasoning `low`.
No model server or container was started or restarted.

Session `guided-russell-live-4`:

1. `Where is Russell’s viper at EBTL?`
   - ran only `local-site-evidence-search`;
   - returned the older property record and September 2024 non-detection in three sentences;
   - offered `Search wider records`.
2. `Search wider records`
   - controller bound `Russell's Viper` and `dry-Deccan donor belt`;
   - ran only `merged-taxon-occurrence-search`;
   - returned 274 coordinate-deduplicated GBIF/iNaturalist observations;
   - offered `Show the raw points` and `Test transfer to the site`.
3. `Show the raw points`
   - controller forced `map_mode: observed`;
   - returned an HTML side-panel map with 274 `OBS-...` records;
   - the audit contained no estimate stage;
   - offered `Test environmental transfer`.

Observed latency was about 21 seconds, 60 seconds and 21 seconds for the three turns. The second
turn is still too slow for an ideal field interaction. The Codex resume context also grew quickly,
so speed/context reduction should be a separate follow-up after behaviour is stable.

## Failures found during the smoke

The first wider-search attempt exposed two controller errors:

- curly apostrophes in `Russell’s` did not match the ASCII common name at the taxonomy boundary;
- a failed occurrence search still exposed map/transfer actions.

Typography is now normalized generically and continuation derivation checks the actual execution
status and returned rows. A later run showed that a combined “wider data” action allowed Codex to
choose unrelated repository discovery. The capability was split into occurrence-only and
source-discovery actions, and irrelevant discovery titles no longer become inspection buttons.

The UI screenshot exposed fixed-height choice buttons whose wrapped descriptions overlapped the
next control. Guided choice buttons now use automatic height. The raw-map screenshot also showed
that 274 records made the document extremely long; the complete table remains downloadable and is
collapsed by default.

## Evidence

- `ecology_memory/narrative/benchmarks/guided-investigation/smoke/guided-actions-card.png`
- `ecology_memory/narrative/benchmarks/guided-investigation/smoke/russells-viper-observed-map.png`
- disposable audit:
  `/tmp/idli-guided.CUqDzI/sessions/guided-russell-live-4/audit.jsonl`

The `/tmp` audit is development evidence and is not a durable benchmark artefact. The screenshots
are retained in the repository.

## Tests

- `python3 -m unittest ecology_memory.tests.test_codex_native -q` — 38 passed.
- Odysseus focused suite:
  `tests/test_idli_insight_ui.py`, `tests/test_ask_user_tool.py`,
  `tests/test_ask_user_persistence.py` — 18 passed.

This is a guided Codex-default trial, not a cross-model benchmark and not a saturation claim.
