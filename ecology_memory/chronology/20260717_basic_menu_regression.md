# 2026-07-17 — basic menu regression

## Trigger

A live meeting-path session opened with “tell me about ebtl”, selected “wildlife, what is seen
there”, and received `typed_evaluate data_request / no connector`. This contradicted the opening
menu's promise and showed that the repaired showcase had tested direct taxa questions without
testing its own generic category choice.

## Root cause

Dialogue routing correctly recognized wildlife, but emitted “What wildlife species have been
recorded at EBTL?”. The ecology parser had no literal wildlife-to-local-inventory repair and the
resolver had no category-level evidence entity. It therefore passed an untyped `wildlife species`
leaf to the generic connector router, which correctly—but unhelpfully—failed closed.

The local-source import was also incomplete. The previously structured evidence retained 67 birds
and 14 snakes, but the same 26-page faunal report contains survey summaries for 54 butterflies,
42 odonates, and the complete observed-versus-earlier herpetofauna table.

## Repair

The primary-evidence ledger now records the four faunal groups, dates, methods, page spans,
examples, and detection-status boundaries. A `wildlife_inventory` connector returns those local
survey summaries. It reports 20 herpetofauna encountered during the 2024 VES separately from 13
earlier property records not encountered then, and keeps two indirect elephant-passage reports
outside the survey-detection count.

Natural replies for all four menu categories now bind deterministically. Wildlife follow-ups state
the 2024 group breakdown and answer population questions directly. The broader audit found and
fixed a second context loss: after a correct fire answer, “what years did you measure and is that a
forecast?” had been reparsed as an unrelated taxon query. Year/forecast wording now binds to the
persisted fire result.

## Real Hermes evidence

The corrected four-turn typed wildlife run is
`integration/eval/runs/20260717-092145-basic_wildlife_choice.json`. It returns the local survey on
turn two, the observed-versus-older breakdown on turn three, and an explicit inventory-versus-
population distinction on turn four. The passing natural-language vegetation, restoration, and
corrected fire runs are `20260717-092253-basic_vegetation_choice.json`,
`20260717-092251-basic_restoration_choice.json`, and
`20260717-092344-basic_fire_choice.json`.

The complete prior 12-case showcase was then rerun on current code. All turns exited zero, no
`no_connector`, `data_request`, HTTP, or traceback markers appeared, and every normalized answer
was identical to its previously scored artifact. These runs protect against regression but do not
count as untouched saturation holdouts.

## New head-to-head

Untouched origin DeepSeek ran the same four turns in
`integration/eval/runs/20260717-093126-basic_wildlife_choice.json`. Typed completed in 24.859 s;
origin required 241.713 s. Origin first reported 1,658 unresolved GBIF keys as wildlife records in
the “site,” then turned a capped occurrence sample into an unsupported 271-record 2024 breakdown
and named-species counts. It also conflated the analysis AOI with the property. Its last answer
correctly said occurrence uploads are not population counts, but that does not validate the
preceding local claims. Typed used the page-addressed survey and made no critical error.
