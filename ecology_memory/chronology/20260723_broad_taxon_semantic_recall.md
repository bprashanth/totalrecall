# Broad taxon semantic recall

## Why

Chat `e4295756-a875-4ca0-b111-f3ef5127dd9c` asked, “tell me about monkeys at
EBTL”. The local registry correctly returned no match, but the wider pass searched only
`monkey at EBTL`. OpenAlex returned no works, repository search returned generic monkey
datasets, and the 256-card semantic corpus returned mostly unrelated high-similarity cards.
The final answer therefore reported only a gap.

This was not a connector outage. The discovery audit showed all five admitted connector calls.
It was a query-planning and result-diversity failure: an organisation acronym was left inside a
literature query, the broad vernacular group was not expanded into auditable candidate queries,
and one query could fill the complete result window.

Gibbons must not be silently treated as monkeys: they are apes. A gibbon source may be returned
as related or comparative primate literature when a query seed asks for it, but it is not evidence
of a monkey or gibbon record at EBTL.

## Change

- `discover-ecology-evidence` now accepts up to three `query_variants`.
- A query containing an onboarded site alias is also searched without the alias and with the
  profile's `discovery_context`.
- The exact original query is always retained and audited.
- Variant calls run concurrently, DOI/URL duplicates are removed, title-confirmed leads are
  prioritised within each branch, and results are interleaved across branches.
- Codex is instructed to pass plausible members of a broad lay group to replanning only as
  `untrusted query seeds`. Algebra 9B is instructed to preserve taxonomic distinctions.
- The EBTL profile now declares `dry-deciduous Eastern Ghats near Krishnagiri, Tamil Nadu, India`
  as its portable discovery context.

The controller still does not promote a candidate, paper or dataset into a site occurrence.
Occurrence retrieval, dataset inspection and modelling remain separate audited stages.

## Evidence

A direct admitted-connector probe used these four branches:

1. `primates macaques langurs Tamil Nadu India`
2. `monkeys dry-deciduous Eastern Ghats near Krishnagiri, Tamil Nadu, India`
3. `monkeys`
4. `monkeys at EBTL`

The candidate branch returned, among other leads:

- `10.11609/jott.zpj.971.1552-94`, a taxonomic revision of South Asian langurs and leaf monkeys;
- `10.1371/journal.pone.0087804`, ecological-boundary modelling of the Hanuman langur complex in
  peninsular India; and
- `10.26515/rzsi/v116/i1-4/1993/160905`, an Indian macaque/langur status survey.

These are literature leads, not EBTL records. They demonstrate that the broader search can now
retrieve regionally relevant primate material instead of stopping at the literal acronym query.

After loading the change, a live Codex + Algebra 9B replay first ran the required local search,
received the registry non-match, and then produced a second plan with `query=monkey`,
`region=EBTL`, and the explicit untrusted variants `bonnet macaque`, `gray langur`, and
`hanuman langur`. The controller now adds the onboarded regional context to those bare seeds
before connector execution.

All 254 tests under `ecology_memory/tests` passed after the change, including new coverage for
site-query expansion, exact-query retention, multi-query deduplication, query provenance and
broad-group planner instructions.
