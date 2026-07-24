# Evidence-chain benchmark report: `overnight-001`

## Decision

Keep Codex native as the user-facing planner, but put source lineage, gates, relation operations,
artefact construction and model-request records behind deterministic skills. Do not enable the
algebra/backpedal prefix or either synchronous verifier by default.

The arm named `codex-algebra-backpedal` was not Codex plus an Algebra runtime. It was the same Codex
path with one backpedalling instruction prepended to each question. The DeepSeek-V4 and local-9B
arms also used Codex for every skill selection and execution; each second model saw only the
question, Codex answer and compact audit, then accepted or revised the prose.

The frozen run contains 128 scored turns: five conversations, 16 turns per arm, four arms and two
unchanged passes. It recorded no rubric-level critical failure. It did **not** meet the operational
stopping rule because every arm's pass-mean score changed by more than 0.02. This is development
evidence, not a saturation claim.

## Results

| Arm | Mean turn score | Weighted requirements | Exact replay | Pass mean change | Median end-to-end | p95 end-to-end |
|---|---:|---:|---:|---:|---:|---:|
| Codex native | 0.796 | 0.777 | 75.0% | 0.141 | 34.6 s | 122.4 s |
| Codex + algebra/backpedal | 0.692 | 0.670 | 81.3% | 0.099 | 28.5 s | 79.7 s |
| Codex + DeepSeek-V4 | 0.719 | 0.734 | 93.8% | 0.038 | 64.1 s | 200.4 s |
| Codex + local lora9b004d | 0.803 | 0.777 | 50.0% | 0.042 | 61.6 s | 208.2 s |

“Exact replay” means that the identical arm/conversation/turn received the same rubric fraction in
both passes. End-to-end verifier-arm latency is native generation plus verification. Each arm ran
its own native session, so cache and upstream connector timing also contribute to arm differences.

The local 9B verifier's 0.007 raw-score lead over native is not operationally useful. It reproduced
only half the scores, changed a perfect Lantana estimate turn to 0.25 on replay, and had much worse
tail latency. DeepSeek was more repeatable but scored below native, added a 127.4 s verifier p95,
and could not repair an operation that the native planner had not called. DeepSeek returned 18
accepts, 13 revisions and one parse failure; local 9B returned 23 accepts, seven revisions and two
parse failures. Backpedalling was consistently worse on the Eucalyptus chain.

## Conversation findings

| Native conversation | Mean score | Exact replay | Finding |
|---|---:|---:|---|
| Eucalyptus and birds | 0.673 | 60% | Honest evidence gap; inconsistent follow-through after no bird was named |
| Lantana rebound map | 1.000 | 100% | Donor search, independent gates and balanced fallback map worked |
| Sparse taxa and relation | 0.625 | 75% | Exposed a missing generic `RELATE` operation and region alias |
| Satellite and fire | 1.000 | 100% | Discovery/proxy boundary and structured missing-model route worked |
| ANR spatial design | 0.938 | 50% | Protocol, datasheet and neutral matched-plot map worked |

The Eucalyptus abstention was scientifically correct: admitted results described bird-pollinated
`Eucalyptus caesia` but did not name a bird taxon or show Eucalyptus seed dispersal by birds. The
benchmark's conditional second turn still awarded occurrence credit only if a taxon search ran, so
it penalised the correct “no evidence-derived bird candidate” result. This must not be “fixed” by
inventing a bird. The next controller revision should turn that branch into a precise, explicit
data request while keeping the source gap visible.

A post-run map replay added that useful branch: when only one admitted named taxon is available,
`build-ecology-field-map` returns a one-taxon balanced collection design and explicitly refuses to
call it overlap. Both replay passes emitted the map, GeoJSON and CSV with stable points. The frozen
scorer gave each map turn 0.8 because its CSV check was case-sensitive (`CSV` versus `csv`); that
check is fixed for future runs without rewriting the frozen score.

Audit review also caught a more important issue that the numeric score rewarded: one replay pass
promoted hornbills from a general seed-dispersal dataset even though the source did not connect
hornbills to Eucalyptus. The runtime prompt now requires one returned source to directly contain
the candidate, focal entity and requested relation. General literature can create a labelled query
seed only; it must be searched again with the focal entity and relation before downstream use. A
`postfix-lineage-001` smoke then abstained correctly: no bird occurrence or estimate was run because
no direct Eucalyptus relation source was returned. This is safer despite receiving less credit from
the frozen operation-count rubric. A future benchmark revision should score direct relation lineage
explicitly rather than rewarding any occurrence call.

## Deterministic repair and replay

The frozen run showed that `donor belt` did not resolve to the already declared
`dry-Deccan donor belt`, and the visible catalog had no generic two-taxon relation skill. After the
run, the runtime added `relate-taxon-occurrences`, normalised the region alias, and retained the two
input denominators and declared distance threshold in the audited `RELATE` result.

`postfix-relation-001` replayed the complete four-turn sparse-taxa conversation twice using native
Codex. It scored 8/8 turns at 1.000, with 100% exact replay and zero score delta. Median end-to-end
latency was 42.5 s and p95 was 93.5 s. This narrow replay is evidence for the relation repair only;
it does not retroactively make the frozen full-bank run pass its stopping rule.

The scorer was also corrected to remove Markdown emphasis before semantic checks. The frozen raw
score had treated “does **not** prove” as different from “does not prove”, and had missed the ANR
answer's explicit “should not claim ... works better” boundary because it searched only for the
literal word `effect`. Its CSV-artifact check is now case-insensitive. Frozen scores above are
preserved; they were not rewritten post hoc.

## Product and artefact verification

Browser checks covered live current-skill activity, the compact Why panel, desktop and narrow map
views, and desktop and narrow protocol views. Opening a map or protocol now keeps Chat active and
the session hash intact. Map HTML, CSV and GeoJSON share stable `FIELD-XX` identifiers; source-backed
protocols keep repository columns separate from programme-added columns. The field-map fallback is
labelled as a balanced sampling design when no admitted fine surface passes.

Representative captures are under
`runs/development-001/screenshots/`, including
`chat-live-current-skill-desktop.png`, `chat-map-sidepanel-desktop.png`,
`chat-map-sidepanel-mobile.png`, `chat-protocol-sidepanel-desktop.png` and
`chat-protocol-sidepanel-mobile.png`.

## Recommended architecture

1. Use model knowledge only to label search seeds.
2. Admit candidates only from connector results with source identifiers.
3. Carry result handles into inspection, estimation, relation, protocol and map skills.
4. Enforce sample and environment gates independently per entity.
5. Render skill-produced maps, datasheets and structured T4GC requests directly; do not let a
   verifier rewrite away their fields.
6. If desired, use DeepSeek asynchronously to flag self-contained document omissions. It cannot
   replace the controller or execute a missing connector operation.

Machine-readable metrics are in `summary.json`; complete answers, timings and verifier decisions
are in `turns.jsonl`; skill audits are in `audit.jsonl`. The run manifest records the frozen bank,
runtime hashes, endpoint observations and Idlisseus commit.
