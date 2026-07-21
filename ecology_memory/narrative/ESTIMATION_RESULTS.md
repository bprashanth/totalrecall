# Ecology estimation lens — the data comes in patches

Status: scored secondary analysis of the frozen five-question pilot; no new model contact.

## The claim

In ecology, “estimate” is rarely one clever number. It is a controlled transition between partial
sources: a satellite pixel becomes a pressure proxy, a remote interaction becomes a local
hypothesis, or a regional occurrence becomes a target expectation only after environmental gates.
The important property is not whether the prose sounds cautious. It is whether the operation ran
and the evidence class survived the transition.

This is a post-hoc lens over Q3–Q5, not a second independent benchmark. It reuses the frozen prompts,
raw runs, and original per-dimension scores without rescoring any answer.

## Result

| condition | workflow score | executed analysis | evidence boundary | complete workflows |
|---|---:|---:|---:|---:|
| Gemini 3.5 Flash agent | 4/30 | 1/6 | 0/6 | 0/3 |
| DeepSeek V4 Flash + web | 13/30 | 0/6 | 4/6 | 0/3 |
| accepted ecology stack | 21/30 | 3/6 | 6/6 | 1/3 |
| LoRA-9B end to end | 21/30 | 3/6 | 5/6 | 1/3 |
| plan-bound LoRA-9B diagnostic | 28/30 | 6/6 | 6/6 | 2/3 |

The DeepSeek row is the clearest new pattern. It scored reasonably on the whole answers because it
named sensible methods and preserved two important caveats, but its executed-analysis score is
zero: it did not compute the site fire values, join the two bird tables, or run either arachnid
gate. In these workflows, a correct recipe can read like a result.

Gemini shows a different failure mode. It attempted substantial tool use, but two runs ended
without a final answer and the surviving transfer answer replaced measured gates with qualitative
habitat reasoning. That is not random nonsense; it is ecological common sense crossing an
evidence boundary unnoticed.

The accepted stack kept every estimation boundary intact, but completed only the fire workflow.
For these three frozen operations, the plan-bound diagnostic shows that the source/connector
substrate can execute all three; its remaining incomplete workflow was response loss, not missing
data. This is why the next repair is routing and rendering rather than adding a larger general
model.

## The estimation ladder

1. **Local observation:** three snakes encountered in a short survey must not erase eleven older
   property records or become a claim of absence.
2. **Spatial annotation:** WorldCover class 10 at a published coordinate is modelled tree cover,
   not floristic composition or evidence of a restoration treatment.
3. **Historical proxy:** MODIS pixel-fire-days describe detected historical pressure, not today's
   calibrated fire risk.
4. **Mechanism transfer:** a locally listed bird appearing in a remote Lantana feeding table creates
   a hypothesis worth checking, not proof of a local interaction.
5. **Gated transfer:** a regional arachnid is not “expected here” until independent feature and
   climate gates both pass.

The ladder is ordered by claim transition, not statistical sophistication. It should not be read as
a five-point interval scale or used for a correlation claim.

## What a data patch must carry

Every patch needs at least: source, geography, time, grain, evidence class, operation, and the claim
it is not allowed to support. Patches become useful when code can join them while preserving those
fields. Without that contract, adding more sources can make an answer more persuasive and less true.

Reproduce the table with `python3 score_estimation.py`. The definitions live in
`estimation_lens.json`; original rationales remain in `scoring.json`.
