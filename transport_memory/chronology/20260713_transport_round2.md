# 2026-07-13 — Round 2: from regression closure to a discovery-rate claim

## Why

Round 1 proved the harness could close a bounded suite (45 questions, 0.985). It proved
nothing about questions nobody had tuned against. The livelihoods sector wrote a stronger
Round-2 protocol — saturation as a discovery-rate claim over untouched distributions, with a
frozen epoch and a no-fixes holdout sequence — and we adopted it for transport (ROUND2.md).

## What we did

**Sources.** Censused and adopted two new keyless families: GTFS static feeds (Mobility
Database's public catalog + GCS mirror; four verified city feeds) and city open-data ridership
(Socrata; Chicago observed, New York upstream-ESTIMATED — adopted with label 'modelled' so the
taint propagates, the same trap the livelihoods run caught with modeled ILO series). Re-audited
the Round-1 WB series and stamped their ICAO staff-estimate caveats into provenance. Negative
controls verified: unregistered cities die as DataRequests, never silent fallbacks.

**Coverage.** Built the matrix (harness/coverage.py, own adaptation): 45 Round-1 questions =
11 skeletons, osm-routes nearly empty, both new families empty. Generated gen-003 against
exactly those cells (18 Qs; first contact 0.968 → 1.000 after two layer-correct fixes: the
truncation few-shot swap and a distance-anchor lint pattern). Admission got a grounded-value
check after the gold author produced an "answer" of value None from a wrong-source route.

**Breakers.** 32 pre-judged probes across 8 families of semantics OUTSIDE the op set. The 2B's
signature move under pressure: silent semantic weakening (27/32) — count all stops when asked
for sheltered ones, count trams when asked for bus+tram. Zero invented ops. Seven proposals
filed; three executor completions landed pre-freeze (windowed mean, same-entity orientation
guard, grain-mismatch disclosure). The probes falsified one of the judge's own pre-run
verdicts — "per 1000 residents in Winnipeg" divides by CANADA's population, fluently and
green-scoringly — which is now disclosed in provenance and recorded as a proposal.

**The epoch.** Froze everything (checksums in ROUND2.md), then three untouched holdouts:
neutral 42 Qs 0.982, indirect 44 Qs 0.960, terse/mixed 45 Qs 0.968 — 131 first-contact
questions, zero fixes, checksums re-verified intact afterwards.

## What we found

Two genuinely new failure classes in 131 questions (0.76/50, under the rate threshold): the
2B cannot compose delta-PER-ITEM comparisons ("which grew faster" → it compares window means;
three instances, and the frozen executor handled the correct gold trees perfectly — a pure
curriculum gap), and once in the terse register it TYPO'D a city ("Evrora") that slipped
through faithfulness on its country token and died as error instead of DataRequest. Everything
else was instances of Round-1-characterized classes (truncation, over/under-holing, lint
phrasing gaps, arity confusion, multi-part).

## The call

ROUND2.md demands both a low discovery rate AND no new classes. Rate: passed. Classes: two.
So the saturation statement was NOT issued — deliberately. The protocol only means something
if it can say no. One targeted curriculum exemplar and one terminal-state fix, then a fresh
epoch, is the path to the claim. Every failure across all 131 unseen questions terminated
honestly; nothing fabricated, nothing silently mis-sourced that provenance does not now
disclose. That — not a scoreboard — is the property the benchmark exists to defend.
