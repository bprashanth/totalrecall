# REPORT — transport Round 2: discovery-rate saturation protocol (2026-07-13)

Parser under test unchanged: **qwen3.5-2b** (local vLLM, 172.17.0.1:8001). Spec **v2.1 frozen**
(proposals only). Protocol: `ROUND2.md` (adopted from the livelihoods Round-2 protocol);
saturation = a discovery-rate claim over untouched distributions, not regression closure.
Judge log: `FINDINGS.md`; proposals: `spec-proposals.md`; narrative: `chronology/`.

## What Round 2 added over Round 1

| dimension | Round 1 close | Round 2 close |
|---|---|---|
| source families | 2 (OSM points+routes, WB series) | **5** (+ GTFS feeds, + city open-data ridership; census `coverage/source-census.json`, 15/15 probes green incl. negative controls) |
| grains | city-bbox point, country/annual | + city-feed/stop-point, + city-system/annual |
| questions (dev) | 45 / 3 banks | **63 / 4 banks** (+ gen-003 targeting empty matrix cells) |
| breadth accounting | question count | **coverage matrix** (`harness/coverage.py`; 11 skeletons; empty/singleton cells drove generation) |
| breaker pressure | 4 admission rejects | **32 pre-judged probes / 8 capability families** + 7 evidence-backed spec proposals |
| test separation | guard re-runs | **frozen epoch r2-freeze-1**: checksums + 3 untouched holdouts (131 Qs), zero fixes mid-sequence (checksums re-verified after) |

## New sources (both keyless, verified rows before adoption)

- **GTFS static feeds** via the Mobility Database catalog + `mdb-latest` GCS mirror (the
  keyed APIs were rejected). 4 verified feeds: Winnipeg 3873 stops/71 routes, Christchurch
  2060/29, Oulu 1659/52, Tampere 3410/113. Observed (agency-published). Unregistered city →
  honest DataRequest, never an OSM fallback.
- **City open-data ridership** (Socrata): Chicago CTA annual totals 1988–2025 (**observed**,
  administrative) and NY MTA daily-aggregated 2021–2024 (**modelled** — the upstream columns
  literally say `..._estimated_ridership`; the label taints every answer built on it).
  Partial years (<360 days) dropped in-connector with a provenance note.
- **Evidence-status audit of Round-1 families**: WB air/port series carry ICAO/UNCTAD staff-
  estimate caveats in every provenance note now (`WB_EVIDENCE_NOTES`) — the transport twin of
  the livelihoods modeled-ILO finding.

## Breaker program (32 probes, `questions/breakers-round2.json`, runs/round2-breakers-{pre,post})

25 inexpressible → **7 proposal entries** (FILTER/attribute predicates; GROUP/partition;
positive UNION — transport evidence added to the open cross-sector proposal, negated union NOT
re-proposed (De Morgan, livelihoods proof); median/percentile; temporal argmax; row-level
ordering; units/grain co-scoping + an AMENDMENT to the Round-1 COMPARE-orientation proposal).
4 expressible stress tests (all pass post-completions). 3 executor-gaps → three deterministic,
provenance-stamped executor completions, all guards re-run green:

1. **Windowed mean**: AGGREGATE(by:space, metric:mean) over a series = window mean (before:
   "average 1990s vs 2010s" silently compared 1999 vs 2019 — opposite sign from the true answer).
2. **Same-entity orientation guard**: later-minus-earlier now requires same resolved entity —
   the Round-1 interim rule was silently inverting per-capita ratios to "people per passenger".
3. **Grain tags + mismatch disclosure**: "bus stops per 1000 residents in Winnipeg" executes
   against CANADA's population (city→country resolver fallback); COMPARE now stamps
   `[GRAIN MISMATCH: left=city-bbox, right=country]` into provenance. (The evidence run
   FALSIFIED the judge's pre-run claim that this case died honestly — recorded as such.)

Headline parser behavior under out-of-algebra pressure: **27/32 silent semantic weakenings,
0 invented ops** — a 2B narrows meaning rather than breaking syntax, which is why
inexpressible questions must become proposals, never weakened golds.

## Frozen-epoch discovery-rate table (epoch r2-freeze-1)

131 holdout questions generated AFTER the freeze, three registers, first contact, no fixes;
all frozen-file checksums re-verified intact after holdout C.

| bank | register | n | overall | parse/schema | new classes | characterized instances |
|---|---|---|---|---|---|---|
| A | neutral | 42 | **0.982** | 1.00 / 1.00 | 1 | 3 |
| B | indirect | 44 | **0.960** | 1.00 / 1.00 | 0 | 5 |
| C | mixed/terse | 45 | **0.968** | 1.00 / 0.98 | 1 | 4 |
| **total** | | **131** | **0.970** | | **2** | **12** |

Discovery rate: **0.76 new classes per 50 questions** (threshold <1). New classes, both
characterized with evidence and cheap fix candidates:

1. **Delta-per-item composition** (3 instances, A+B): "which changed faster/more" over 2–3
   items needs COMPARE/RANK over per-item delta-COMPAREs; the 2B substitutes window means.
   The frozen executor handled the gold trees correctly — this is purely a curriculum gap.
2. **Place transcription typo** (1 instance, C): "Evora"→"Evrora" rode through faithfulness on
   its sibling "portugal" token; Nominatim miss surfaced as `error` instead of a DataRequest.

## Verdict

**The saturation statement is NOT issued.** The discovery RATE clears the threshold and bank B
ran clean, but ROUND2.md also requires zero new failure classes across the sequence, and there
were two. The honest claim this evidence permits: *the transport stack is approaching plateau
on the tested distribution (single-turn English transport place-questions over five keyless
source families, three registers), all 131 first-contact failures terminate honestly
(DataRequest or shape-scored weakening — no fabrication, no provenance violation), and the
residual surface is two named classes with identified fixes.* The path to the statement is one
more freeze epoch after the delta-composition few-shot and the region-typo terminal fix.

Residual blind spots (stated per protocol): registers beyond the three tested (non-English,
multi-turn drift), sources beyond the five families, cities/countries outside the generator's
coverage habits, and the scoring blind spot that op-multiset shape cannot see a wrong
COMPARE `how` (synthesis prose remains the compensating canary).

## Deliverables

- `ROUND2.md` (protocol + freeze checksums) · `coverage/{matrix.json,source-census.json,README.md}`
- `questions/{gen-003,breakers-round2,holdout-r2-a,holdout-r2-b,holdout-r2-c}.json` (+
  `holdout-rejects.json` admission log)
- `runs/tick-014..016*`, `runs/round2-breakers-{pre,post}`, `runs/holdout-r2-{a,b,c}` + index.html
- `corpus/parse.jsonl` 63 rows / `clarify.jsonl` 40 rows — **development rows only** (holdouts
  stay blind per protocol; schema unchanged)
- `FINDINGS.md` (census, every judge decision, epoch verdict) · `spec-proposals.md` (+7 entries,
  1 amendment) · `chronology/20260713_transport_round2.md`
