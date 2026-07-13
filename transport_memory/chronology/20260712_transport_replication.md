# 2026-07-12 — Transport sector replication of the place-question algebra benchmark

*(Narrative log, written as the experiment ran. Scores and judgments are in FINDINGS.md; this is
the why-and-what-happened story.)*

## Why
The reference run (5 civic sectors, 89 questions, 2B parser, final 1.000) claimed the algebra +
harness generalizes across domains. This directory tests that claim on TRANSPORT/MOBILITY — a
sector with a genuinely different data shape: transit LINES are OSM *relations* (not points),
tram/metro coverage is violently uneven across cities, and the World Bank transport indicators
are sparser and more truncated than the development ones the reference leaned on.

## Census first (the phantom-source lesson)
Before any questions: probed 12 OSM tags x 4 mid-size cities on 4 continents, 8 WB indicator
codes x 4 countries, and the Overpass route-relation query shape. Two WB codes turned out to be
phantoms (IS.VEH.NVEH.P3, IS.ROD.PAVE.ZS — dead outside Kenya, dead after 2010) and were
rejected before they could poison a gold. The census also surfaced the sector's texture: bus
stops/fuel/parking are abundant everywhere; trams exist in exactly one of four probe cities;
nobody in the probe set has a metro; landlocked Czechia has zero container-port rows (a
structural, honest gap the executor already turns into a DataRequest).

## Connector work
- Point tags: 16 new transport entries + aliases in OSM_TAGS (tram stop, railway station,
  subway entrance, ferry terminal, parking, bicycle rental, charging station, taxi, airport,
  petrol/gas aliases for fuel).
- NEW connector `osm_routes_select`: transit lines as route relations, deduped by `ref` so the
  count answers "how many lines" not "how many direction variants" (Brno: 280 relations -> 124
  lines). Route rows deliberately carry no geometry (politeness to Overpass); they count and
  list but cannot RELATE spatially — stated in provenance.
- WB: 6 verified transport indicator codes added to the resolver.
- Routing: osm-routes first (most specific), then WB, then OSM points. The directional-token
  rule earned its keep immediately: "airport" would prefix-match the "air" in "air passengers
  carried" — order + directionality keep both routes clean.

## The loop
- **tick-001** (baseline, stock few-shots): 0.966. Both failures were instructive: a double
  entity truncation ("railway stations"->"railway", "bus station"->"bus" — the second half of
  which would have been a SILENT wrong-source answer had the first half not died honestly), and
  a repair-round derail where the one-round LLM repair returned the repair prompt's own inline
  example as the tree — valid, unrelated, accepted. That second one is a new harness finding:
  validity-only acceptance of repairs is too weak.
- Fixes: transport CHANGE few-shot + entity swap in the within-1km few-shot (14/15 few-shots),
  "railway" alias, and a new mechanical guard — `entities_faithful()` — that rejects repaired
  trees whose SELECT entities share no token with the question.
- **tick-002** (golden-guard re-run): 1.000, no regressions.

## Multiturn and the rotation lesson
Adapting the dialogue cases to transport surfaced under-holing ("Map the stations here." kept
"station" concrete — and bare "station" is four different things in this sector). The first fix
(a "Map the stations here." few-shot) FIXED mt-02 and BROKE mt-05: the 2B had learned the
template ("Map the X here" → hole X), not the lesson ("stations" is subtype-less), and started
holing "parking". Rewording the exemplar to the original template shape resolved both. At 14-15
few-shots you are steering by surface form as much as by content — the reference's saturation
warning, observed directly. Multiturn plateaued at 0.943; the only failing leg anywhere is
MODEL-bind, while MECHANICAL bind is 5/5 — the strongest sector-local confirmation that the
dialogue layer belongs in code.

## The synthesis layer catches what shape scoring cannot
Mining tick-004's synthesis scores (mean 0.954) found the session's best discovery: a CHANGE
question whose parse put COMPARE operands in question order (2010 left, 2019 right) — same
shape as gold, executes fine, and the prose honestly reported "decreased by 38,849,407" for
Vietnamese air traffic that actually TRIPLED. The spec never says which COMPARE operand is the
subtrahend. Filed as a spec proposal (operand-order convention); interim executor rule orients
difference/ratio later-minus-earlier when both sides carry years, stamped in provenance. After
the fix the same question synthesizes "increased by 38,849,407 (oriented later-minus-earlier)"
and the seed's synthesis mean is 1.0.

## Generated banks: two registers, two spec discoveries
gen-001 (neutral, 13 admitted / 15): first contact 0.923, and the mining found (a) an EM-DASH
tokenization bug — "countries—Germany, France, Italy—had" made literal-provenance demote two
correctly-copied countries to holes; (b) the second spec discovery: TWO-PART questions. Both
the frontier gold author and the 2B degrade them — gold silently answers clause one; the 2B
jammed all four quantities into one unreadable RANK. One tree = one answer; proposal filed
(recommend dialogue-layer splitting, no algebra change). After fixes: 0.981 with the multi-part
residue accepted at 0.75, by explicit judge decision, rather than allow-set-ed away.

gen-002 (indirect register, 10 admitted / 12): first contact 0.892. The indirect register's
signature failure was SPURIOUS ESTIMATE — hedged phrasings ("will there be...", "is it enough
...") pull the 2B toward transfer machinery, always with source==target. A deterministic
self-transfer unwrap (ESTIMATE from a place onto itself is degenerate by definition) plus the
existing proximity lint mechanically rebuilt the right trees: 0.958 after fixes.

## Head-to-head with the frontier
deepseekv4 through the same harness: seed 1.000, gen-001 0.981 — IDENTICAL to the 2B, including
failing the same multi-part question the same way. On the indirect bank the frontier scored
BELOW the 2B at first (0.925 vs 0.958): different quirks, not fewer — it over-holed a named
entity (?proxy for "the bus system") and dropped a proximity constraint phrased "within a short
walk of" that the anchor lint didn't yet cover. Extending the lint (model-neutral) lifted it to
0.950; the over-holing stands as a frontier parser failure. The conclusion the reference drew
holds here with unusual crispness: past the mechanical-repair floor, PARSER SIZE IS NOT THE
BINDING CONSTRAINT — the spec and the connectors are.

## Where it ended
qwen2b: seed 1.000 (22 Q), gen-001 0.981 (13 Q), gen-002-indirect 0.958 (10 Q), multiturn
0.943; 43/45 questions at 1.0; both sub-1.0 residues characterized, two spec proposals filed
with trace evidence, corpus compiled (45 parse + 30 clarify rows, meta.sector=transport).
The sector-specific texture that made transport worth testing — route relations as a new
connector shape, violently uneven tram/metro coverage becoming honest DataRequests, landlocked
countries as structural gaps, the EV-infrastructure gradient (Brno 187 chargers, Mombasa 0) —
all of it fit inside the frozen algebra. What did NOT fit was never transport-specific:
operand order and multi-part questions are cross-sector spec debts.
