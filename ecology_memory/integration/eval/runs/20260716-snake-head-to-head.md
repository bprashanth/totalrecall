# Matched Hermes snake dialogue — 2026-07-16

## Question

Why did the original Hermes shell appear better than the typed 2B and typed DeepSeek runs, and does
the typed system improve evidence quality when the same four turns are run head to head?

The matched turns were:

1. `tell me about ebtl`
2. `what about snakes`
3. `what snake data do you have, and which records are direct observations versus estimates?`
4. `how did you decide on those species?`

Full machine-readable transcripts:

- `20260716-210136-site_snake_inventory.json` — typed Qwen 2B and typed DeepSeek-v4
- `20260716-211107-site_snake_inventory.json` — exact origin untyped DeepSeek-v4

## Root cause of the earlier comparison

The earlier typed profile was deployed below `/opt/data/profiles/dss-eval/plugins`, but Hermes was
started with the default `HERMES_HOME`. In this build `-p dss-eval` did not change the plugin
discovery root. Therefore the typed bridge was not loaded. The reported “typed” conversations were
really a neutral Hermes profile with no model-visible connectors and no typed result injection.

That explains both failure shapes:

- Qwen 2B received a `no_connector`/unbound result and filled the gap with invented taxa, records,
  and internal implementation language.
- DeepSeek retained better conversational discipline but could only ask questions or promise a
  search that its profile could not perform.

The launcher now sets `HERMES_HOME=/opt/data/profiles/dss-eval`. Typed results are inserted at the
Hermes `llm_execution` boundary because this Hermes CLI streams provider output before an
output-transform hook can replace it. Hermes still owns the UI, session, and follow-up history.

## What the original actually used

The origin stack is richer: its conservation skill and PLAYBOOK expose occurrence, land-cover,
terrain, literature, and prediction connectors. `discovery.py` performs semantic retrieval over
content cards with `BAAI/bge-small-en-v1.5`, and the scarcity recipe asks the agent to discover
papers, gather donor occurrences, run a transfer gate, then label any result as modelled.

The user-supplied origin answer was conversationally strong, but it did not execute that full
recipe. It searched the semantic corpus, queried two species, and supplied the rest from model
memory. In the matched run the embedding query for snakes returned unrelated amphibian, fire,
gecko, and lizard cards. The relevant local faunal survey was not mounted in that corpus.

The strongest available source was instead the repository primary document
`benchmarks/algebra/ebtl/newsletters/Faunal survey 2024.pdf` (SHA-256
`3b9c21031bfb27fde27854bc4ed350f9f7a3142bec96c0a58257bdabfa3e5d5a`). Pages 23–24 document 14
site snake species: three encountered during the 5–7 September 2024 VES and eleven earlier property
records not encountered during that survey. The typed import stores those rows, status distinctions,
page numbers, method, author, dates, and source hash in
`harness/data/ebtl_faunal_survey_2024.json`.

## Results

| Check | Typed Qwen 2B | Typed DeepSeek-v4 | Origin DeepSeek-v4 |
|---|---|---|---|
| Broad opening clarifies | Pass | Pass | Pass, after five tool calls |
| Complete local snake inventory | Pass: 14 | Pass: 14 | Fail: survey missed |
| Survey encounters vs earlier records | Pass: 3 vs 11 | Pass: 3 vs 11 | Fail |
| Species-selection lineage | Pass: pages 23–24, no inference | Pass | Admitted shortlist came from memory |
| Unsupported local claim | None | None | Initially reported 1,658 “snake” records; later identified the taxon-key result as peanut worms |
| Regional evidence discipline | Not invoked by this inventory trace | Not invoked | Regional counts eventually returned, but no environmental transfer gate was run |
| Four-turn wall time | 21.243 s | 25.084 s | 555.973 s |
| Final Hermes session size | 8 messages, 0 tool calls | 8 messages, 0 tool calls | 64 messages, 56 tool-call messages |

The origin session database recorded 23 model API calls, 376,970 input tokens, 14,046 output tokens,
and approximately USD 0.0462 for this trace. Typed parser work occurs inside the bridge, so Hermes'
own token counter reports zero for the short-circuited final responses; this is not a claim that the
typed parser itself is free.

## Interpretation

Typed is now better on this *supported imported capability*: it returns the complete local primary
evidence, preserves survey semantics, and behaves identically across the base 2B and DeepSeek. The
original remains better at open-ended agentic exploration and natural elaboration. Its apparent
advantage in the supplied trace came from richer tools and prompts plus fluent model priors, not
from a completed or correctly gated evidence chain.

This dialogue is now a development regression, not untouched evidence that a 2B beats DeepSeek:
the connector and routing were repaired after seeing its failures, and the inventory renderer is
deterministic. A model-quality claim still requires parser-blind post-freeze dialogues across
unseen taxa, places, ambiguity shapes, missing sources, and transfer outcomes.

The desired combined route is:

1. query local primary inventories first;
2. if local coverage is absent or incomplete, use semantic discovery to produce candidate sources;
3. enumerate donor records by taxon, retaining source and grain;
4. apply an explicit environmental transfer gate separately per candidate species;
5. present local documented, donor observed, and site-modelled claims as different evidence classes.

The released typed IR can estimate one named species, but it cannot yet cleanly express “discover a
category, group donor occurrences by species, rank candidates, and execute a gated transfer for each
candidate.” This is the practical evidence for the ALG-003 keyed/grouped-result gap. Until that
contract is reconciled, the typed runtime must return a DataRequest for exhaustive unrecorded-species
predictions rather than disguise a model-selected shortlist as a typed result.

## Remaining comparison work

- Score the `site_snake_transfer` case after keyed candidate enumeration has a governed contract.
- Surface bridge provenance in Hermes `/why`; the JSON diagnostic already carries the typed IR,
  execution route, evidence labels, and transfer-gate result.
- Add the imported faunal survey to the origin semantic corpus only during the later, authorized
  `dss_typed/` export; keep the current origin baseline untouched for reproducibility.
- Run the same multi-turn wall against the deployed LoRA when `qwen3.5-2b-lora` exists.
