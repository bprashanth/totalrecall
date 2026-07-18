# 2026-07-16 — snake inventory import and matched Hermes dialogue

## Trigger

User traces showed a local 2B hallucinating snake taxa and a typed DeepSeek asking repeated
clarifications, while the origin DeepSeek shell appeared to search and reason more effectively.
The task was to determine whether this came from model quality, prompts, semantic retrieval,
connectors, or the typed algebra, then exercise identical multi-turn conversations.

## Diagnosis and repair

The typed plugin was installed in the isolated profile but not discovered because Hermes still used
the default home. `integration/chat.sh` now exports the isolated `HERMES_HOME`; the typed middleware
is verified as loaded. A normal completion is returned at the execution boundary so the audited
typed answer is both displayed and persisted instead of being followed by a second model
paraphrase.

The category request also exposed a real source gap. A primary site faunal survey already existed
outside the mounted semantic corpus. Its snake tables were imported as 14 structured records with
page and survey-status provenance. Broad snake requests now resolve to this inventory. Inference
phrasing such as “likely”, “unrecorded”, or “transfer” bypasses that inventory rewrite and reaches
the ESTIMATE contract, which currently fails closed without occurrence-grain donor records.

## Evidence

Both typed Qwen 2B and typed DeepSeek completed the same four-turn inventory dialogue with the exact
14-species result and source lineage. The exact origin DeepSeek run was more agentic but first
misclassified a GBIF taxon key, later retracted 1,658 supposed local snake observations as peanut
worms, and never found the site survey. The origin semantic retrieval implementation does use
bge-small embeddings, but the matched snake query returned irrelevant cards because the decisive
document was absent from the indexed corpus.

Full evidence and remaining limitations are recorded in
`integration/eval/runs/20260716-snake-head-to-head.md`. The origin repository stayed clean and no
container or model server was restarted.

## State after the run

- 120 ecology contracts and the Hermes shell contract pass.
- Inventory dialogue: supported and grounded in typed Qwen 2B and typed DeepSeek.
- Dynamic unrecorded-species discovery and per-species transfer: still unsupported; requires a
  governed keyed/grouped result and donor-evidence route.
- `/why` integration for typed bridge provenance: open.
- LoRA comparison: blocked on deployment of `qwen3.5-2b-lora`.
