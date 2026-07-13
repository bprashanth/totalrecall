# FINDINGS — transport sector
Running log, newest at bottom. Tag each finding [HARNESS]/[CONNECTOR]/[PARSER]/[SPEC-PROPOSAL]/[SCORING].
Every equivalence decision you make as judge gets recorded here with its reasoning.

## 2026-07-12 — Step 0: data census [CONNECTOR]

Probed 4 mid-size cities on 4 continents (Brno CZ, Rosario AR, Mombasa KE, Da Nang VN) for 12 OSM
transport tags, the Overpass route-relation shape, and 8 World Bank transport indicators for
KEN/VNM/ARG/CZE. Full matrix in the census output (cache: harness/cache/data/). Verdicts:

**Source 1 — OSM Overpass, point tags (ADOPTED).** Counts per city (200 = query cap):
- `highway=bus_stop`: rich everywhere (Brno 200, Rosario 200, Da Nang 200, Mombasa 35).
- `railway=station`: present everywhere (6–27). `amenity=bus_station`: 1–25, present everywhere.
- `amenity=fuel`: rich everywhere (101–200). `amenity=parking`: rich everywhere (85–200).
- `amenity=ferry_terminal`: present in all four (5–15) — even inland Brno (reservoir ferries).
- `railway=tram_stop`: Brno 200, Rosario 2, Mombasa/Da Nang 0 — classic sector thinness; tram
  questions outside tram cities must be honest DataRequests, and that is a CORRECT outcome.
- `railway=subway_entrance`: 0 in all four probe cities (none has a metro) — usable only for
  metro cities (e.g. Prague, Sofia) or as deliberate data-gap probes.
- `amenity=bicycle_rental` (0–93), `amenity=charging_station` (0–187; Brno 187 vs Mombasa 0 —
  striking EV infrastructure gradient), `amenity=taxi` (1–38), `aeroway=aerodrome` (0–3): all
  real but thin; usable with expectations set per-city.
- Working sample: POST https://overpass-api.de/api/interpreter,
  `(node["highway"="bus_stop"](bbox);way[...](bbox););out center 200;`. Grain: point/city-bbox,
  no time axis (current snapshot).

**Source 2 — OSM Overpass, route RELATIONS (ADOPTED — new connector `osm_routes_select`).**
A transit LINE is `relation[type=route][route=bus|tram|ferry|...]` — a different query shape from
nodes/ways. Verified: Brno 280 bus-route relations, Rosario 133, Da Nang 49. Two connector
decisions, recorded as judge calls:
1. **Direction-variant dedupe**: a line is typically 2+ relations (one per direction). Brno's 280
   relations collapse to 124 unique `ref`s. Rows are deduped by `ref` so "how many bus lines"
   counts LINES; the note records both numbers.
2. **No geometry**: fetching member geometry for hundreds of relations would hammer Overpass, so
   route rows carry no lat/lon. Lines are countable/listable but NOT spatially relatable; the
   connector note says so (RELATE over them yields 0 matches — a documented limitation, see
   spec-proposals if a question forces it).

**Source 3 — World Bank transport indicators (ADOPTED, verified codes only).**
- IS.AIR.PSGR (air passengers carried) + IS.AIR.DPRT (carrier departures): 50–54 yearly points
  for ALL four test countries, 1970–2023. The abundant axis for CHANGE/TREND/RANKING questions.
- IS.RRS.TOTL.KM (rail lines km), IS.RRS.PASG.KM (passenger-km), IS.RRS.GOOD.MT.K6 (freight):
  present for all four but SPARSE and truncated windows (Kenya rail lines only 1995–2004;
  Argentina 2005–2019) — the ±3 nearest-year fallback will matter; single-year windows outside
  coverage are honest gaps.
- IS.SHP.GOOD.TU (container port traffic): 15 pts 2010–2024 for KEN/VNM/ARG; CZE = 0 rows
  (landlocked — an honest, structural data gap; executor returns empty_select DataRequest,
  verified end-to-end).
- **REJECTED as phantom**: IS.VEH.NVEH.P3 (motor vehicles/1000 — only KEN 2003–2010, dead
  elsewhere) and IS.ROD.PAVE.ZS (paved roads % — only KEN, ends 2010). Not added to the resolver;
  vehicle-ownership and road-quality questions in this sector are DataRequests by design.

**Routing order** (executor `_route_select`): osm-routes (most specific: "bus line/route") →
World Bank (indicator phrases) → OSM points. Verified directional matching keeps "bus stop" out
of WB and "air passengers carried" out of OSM ("airport" key would prefix-match "air" — the
WB-first order for indicator phrases guards it; tested).

**[CONNECTOR] Resolver cleanup**: alias-hits that map to the SAME indicator code (e.g. "air
passengers"/"air passenger") are no longer flagged ambiguous — ambiguity = distinct codes only.
Added irregular-plural alias "ferries" (token-stemmer can't reach ferry from ferries).

## 2026-07-12 — tick-001 baseline (qwen2b, seed bank, 22 Qs): overall 0.966

First-contact on the hand-written seed bank, stock few-shot curriculum: **0.966** (20/22 at 1.0)
— inside the reference's 0.93–0.97 first-contact band. Dimension means: shape 0.95, holes 0.95,
exec_class 0.91, everything else 1.0. Two failures, judged:

**tr-rel-03 [CONNECTOR + PARSER] — entity truncation, one honest death and one silent near-miss.**
The 2B truncated BOTH entity phrases: "railway stations"→"railway" and "bus station"→"bus". Tree
shape was perfect (RELATE/SELECT/SELECT with threshold_km 2.0). "railway" had no tag mapping →
honest no_connector DataRequest (cost exec_class only). The graver half: "bus" resolves to
highway=bus_stop — had "railway" resolved, the answer would have used bus STOPS where the
question said bus STATION, a wrong-source answer that scores green. This is the reference's
truncation trap reproduced in transport. Fixes: (1) alias "railway"→railway=station [CONNECTOR];
(2) swapped the within-1km few-shot's entities to "railway station"/"bus station" (Kigali) to
demonstrate whole-phrase copying on exactly the phrases this sector truncates [PARSER; few-shot
count now 14/15]. Note "bus"→bus_stop stays: bare "bus" in a stop-context question is correct;
only the truncation path was wrong, and it is fixed at the source (copying).

**tr-chg-02 [PARSER + HARNESS] — no CHANGE exemplar, then a REPAIR DERAIL (new failure mode).**
First parse: COMPARE with "right": null (schema-invalid) — the curriculum had NO two-snapshot
CHANGE exemplar, and "change between 2000 and 2020" over one series reads as unary to a 2B.
Then the one-round LLM repair returned a tree that VALIDATED and was accepted — but it was the
repair message's own inline example (AGGREGATE over RELATE) filled with few-shot entities
("hotel", "park") — unrelated to the question. The faithfulness pass demoted its invented places
to ?place, but nothing checked ENTITIES. Judged HARNESS: validity-only acceptance of repairs is
too weak; an unrelated-but-valid tree is worse than a failed repair (it scores shape/holes wrong
instead of surfacing the parse failure). Fixes: (1) added a CHANGE few-shot (air passengers
carried, Brazil, 2005 vs 2015 — entities/years disjoint from the bank) [PARSER]; (2) NEW
MECHANICAL GUARD `entities_faithful()` on repair acceptance only: every non-hole SELECT entity
in a repaired tree must share a word-token with the question, else the repair is rejected and
the original (invalid) parse stands, surfacing the true failure [HARNESS — logged per PROMPT §8].

## 2026-07-12 — tick-002 (golden-guard re-run of seed after fixes): overall 1.000

All 22/22 at 1.0. tr-rel-03 now copies "railway station"/"bus station" whole (the Kigali few-shot
did its job; the alias was not even needed for the parse but stays as truncation insurance).
tr-chg-02 now parses directly to the two-snapshot COMPARE (no repair round triggered). No
regressions anywhere — the entity-faithfulness repair guard fired on nothing (it only gates
repair candidates, and no repairs ran this tick).

## 2026-07-12 — multiturn tick-002-mt (transport dialogue cases): 0.943

4/5 perfect. mt-02 ("Map the stations here.") failed on UNDER-HOLING: turn-1 tree kept entity
"station" concrete (only ?place holed). Bare "station" in transport is genuinely ambiguous
(railway/bus/fuel/charging station), and the resolver rightly refuses to guess → no_connector
even after the place bound. Also observed: model-bind stuffed the entire reply string into
`region` ("Railway stations, around Brno, Czechia") while mech-bind bound cleanly — more
evidence for the reference's thesis that hole-binding is code, not model, work. [PARSER] fix:
swapped the ambiguous-collective-noun few-shot ("health facilities" → ?facility_type) to the
sector's own word ("Map the stations here." → ?station_type), same tree shape, per PROMPT §8
entity-swap allowance. Guard re-runs of seed + mt queued as tick-003/tick-003-mt.

## 2026-07-12 — [HARNESS] propose.py must run from the sector root
propose.py's log_breaker writes the relative path questions/breakers.json; invoked from
harness/ it crashes (FileNotFoundError) after generation. Not a code edit — operational note:
run `python3 harness/propose.py` from transport_memory/.

## 2026-07-12 — tick-003 (seed guard after station few-shot): 1.000; tick-003-mt: 0.857 with ROTATION

Seed stays perfect. Multiturn: mt-02 turn-1 now holes ?station_type correctly and mech-bind
executes to answer — but the fix ROTATED: mt-05 ("Map the parking around here.") began
over-holing "?parking_type" although the question names parking. The 2B generalized my "Map the
stations here." exemplar by its TEMPLATE ("Map the X here" → hole X) rather than by the noun's
ambiguity. Textbook in-context rotation at 14 few-shots. [PARSER] fix: reword the exemplar to
the original template ("Tell me about the stations here.") so the shared surface form no longer
collides with mt-05's phrasing; the lesson ("stations" is subtype-less) is unchanged. Also
re-confirmed both ticks: model-bind mangles replies (whole reply string into entity/region)
while mech-bind is clean — the dialogue layer is code.

## 2026-07-12 — tick-004 (guard) 1.000 seed; tick-004-mt 0.943, residue characterized

Exemplar reword resolved the rotation: mt-05 back to 1.0 (parking stays concrete), mt-02 holes
?station_type and mech-binds to an executing answer. The ONLY failing leg anywhere in multiturn
is now MODEL-bind on mt-02 (the 2B rewrites the reply into the entity field instead of
substituting the hole). mech-bind: 5/5 bound, 5/5 skeleton kept, 5/5 exec. Judge call: this is
the multiturn plateau; residue = model-bind fragility, which the architecture already treats as
optional (the reference's own conclusion: hole-binding is CODE). No further parser changes for
this — the corpus's clarify.jsonl teaches turn-1 hole placement, and binding ships mechanical.

## 2026-07-12 — tick-004 synthesis mining: the OPERAND-ORDER discovery [SPEC-PROPOSAL] + scorer gaps [SCORING]

Synthesis mean 0.954; mining the sub-1.0 rows found the session's most important bug — visible
ONLY at the synthesis layer:

**[SPEC-PROPOSAL] COMPARE.difference has no operand-order semantics.** tr-chg-01: parser put
operands in question order (left=2010, right=2019); gold used later-first. Same shape, both
execute, opposite SIGNS. The prose then honestly said "decreased by 38,849,407" for air traffic
that TRIPLED 2010→2019. Every structural check scores this green — a silent wrong answer class.
Full proposal + evidence in spec-proposals.md. Interim mechanical measure in the executor
(judge decision, deterministic, provenance-stamped): when BOTH difference/ratio operands expose
series end-years and they differ, orient later-minus-earlier and append "(oriented
later-minus-earlier)" to the note. Place-vs-place comparisons (same/absent years) untouched —
there first-named-first is the user's own framing.

**[SCORING] score_synthesis mechanical gaps** (all extensions logged per the lint-extension
allowance): (1) trend answers ("rising") scored states_finding=False because a scalar STRING
finding had no check path — now the direction word itself is the finding; (2) a difference
stated via its operands ("Brno has 101, Rosario 105") now counts when two prose numbers differ
by |headline| — echoing "-4" verbatim is worse prose, not better; (3) gap_stated regex missed
"cannot"/"can't"/"not locate" phrasings of an honest gap.

## 2026-07-12 — tick-006 first contact on gen-001 (13 Qs, unseen): 0.923; mined + judged

Slightly under the reference's 0.93–0.97 unseen-bank band. Failure-by-failure:

- **gen-tran-02 [CONNECTOR]**: truncation "charging station"→"charging" → no_connector, on an
  otherwise PERFECT beyond+threshold tree. Alias "charging"→charging_station added (bare
  "charging" is unambiguous in this sector).
- **gen-tran-07 [PARSER]**: "near this hotel" — deictic "this X" construction: model wrote
  REGION place="hotel" (a non-geocodable literal that IS traceable to the question, so the
  provenance pass rightly left it). The curriculum's deictic list covers here/this area/nearby
  but had no "this <entity>" exemplar. Added few-shot: "How many cafes are within 500 meters of
  this railway station?" → count-over-RELATE with BOTH regions ?place (15/15 few-shots — cap
  reached, no more additions this session).
- **gen-tran-10 [SPEC evidence, residue accepted]**: the two-part Oslo/Helsinki question — the
  2B jammed BOTH clauses into ONE 4-item RANK (railway counts + tram counts, labels duplicated
  per city). More faithful to the question than the first-clause-only gold, but a misleading
  answer surface (a single ordering over mixed quantities). Recorded as evidence on the
  multi-part spec proposal. JUDGE DECISION: gold stays first-clause COMPARE; the 4-item RANK is
  NOT admitted to an allow-set (rewarding it would celebrate an unreadable answer); the 0.75
  stands as characterized residue until the spec question is settled cross-sector.
- **gen-tran-12 [HARNESS x2]**: (1) EM-DASH BUG — "countries—Germany, France, Italy—had" glues
  tokens under whitespace-split, so literal-provenance demoted the correctly-copied "Germany"
  and "Italy" to ?place (the em-dash-free "France," survived). faithfulness_pass and
  entities_faithful now tokenize on all non-alphanumerics. (2) The model omitted SELECT "time"
  fields / misfiled time INSIDE a REGION node; per spec "absent time = null = all data", so
  mech_repair now fills missing time:null and hoists REGION.time to the SELECT — both
  deterministic, meaning-preserving peepholes (logged per PROMPT §8).

## 2026-07-12 — tick-007 (gen-001 after fixes): 0.981 · tick-008 guards: seed 1.000, mt 0.943

gen-tran-02/07/12 all at 1.0 (alias, this-X exemplar, em-dash + time peepholes each did their
job); only the multi-part gen-tran-10 residue remains (0.75, by judge decision). Golden-guard
discipline: full seed re-run 1.000, multiturn unchanged at 0.943 with the same characterized
model-bind residue. No rotation from the 15th few-shot.

## 2026-07-12 — gen-002-indirect first contact (tick-010): 0.892 · frontier head-to-head (tick-009)

**Frontier reference (deepseekv4, same prompt/harness): seed 1.000, gen-001 0.981 — IDENTICAL
scores to the 2B, failing the exact same question (gen-tran-10, the multi-part composite) the
exact same way.** The residue is spec-level, not model-capability-level; a bigger parser buys
nothing here. This mirrors the reference run's conclusion and is the cleanest evidence yet.

**Indirect register (tick-010, 0.892) mined:**
- gen-tran-02/03 [HARNESS→mech_repair]: hedged phrasings ("will there be a fuel station close
  to the airport?", "is the tram network extensive enough?") pulled the 2B into SPURIOUS
  ESTIMATE — both times with source region == target region, a degenerate SELF-TRANSFER
  (ESTIMATE means records from ELSEWHERE). New deterministic peephole unwraps self-transfers to
  their source SELECT; for gen-tran-03 the existing proximity-anchor lint then mechanically
  wraps the RELATE(within, fuel station, airport) the question asks for. Note the epistemic
  stake: a spurious ESTIMATE would have labelled OBSERVED Lyon tram data as MODELLED — the
  label-propagation working as designed, on a wrong tree.
- gen-tran-05 [HARNESS bug]: literal-provenance demoted "India" to ?place because the question
  says "Indian railways" — exact-token membership can't see adjectival forms. traceable() now
  prefix-tolerant (len>=4 guard). Remaining failure on this question is characterized residue:
  the entity is SPLIT across the sentence ("Indian railways ... passenger traffic"), and
  "passenger traffic" alone is genuinely mode-ambiguous (air? rail?) — mapping it to a rail
  indicator by alias would be a wrong-source risk; the honest outcome is the no_connector
  DataRequest the fixed parse now produces.
- Breaker-file bonus (admission catching gold defects): the frontier gold author ITSELF
  truncated "bus stops"→"bus" on the Gyeongju transfer, and honestly holed ?indicator for
  "which city has a better bus network" (a value-laden comparative the generator mistyped as
  expect-answer). Both rejected by execution/structure admission — the pipeline defends gold
  quality as designed.

## 2026-07-12 — tick-011/012: gen-002 0.958 after fixes; ALL guards hold; 2B BEATS frontier on indirect

- tick-011 gen-002 (qwen2b): 0.892 → **0.958**. Self-transfer unwrap fixed gen-tran-02 (bare
  SELECT, observed label restored) and gen-tran-03 (unwrap + proximity lint mechanically built
  the RELATE(within, fuel station, airport) tree). Sole residue gen-tran-05 (0.58): entity
  split across the sentence ("Indian railways ... passenger traffic") — the parse now honestly
  dies no_connector on the mode-ambiguous "passenger traffic"; wrong-source aliasing rejected.
- tick-012 guards: seed 1.000, gen-001 0.981, multiturn 0.943 — nothing rotated.
- tick-012-ds: **deepseekv4 scores 0.925 on gen-002 — BELOW the 2B's 0.958.** Frontier failure
  modes are DIFFERENT, not fewer: (1) over-holing — compiled the Curitiba bus question to
  SELECT ?proxy (behaviour-style caution) although the question names "the bus system"; the 2B
  compiled it correctly; (2) dropped the proximity constraint on the Lisbon parking question —
  phrased "within a short walk of", which the anchor lint didn't cover, so no mechanical
  rescue; (3) same honest no_connector on "passenger traffic" as the 2B. JUDGE decisions:
  (1) is a frontier parser failure, gold stands; (2) is a LINT PATTERN GAP — "a short
  walk/stroll/drive of" added to the anchored-proximity alternation (sector-phrasing extension,
  model-neutral, benefits both parsers); re-running frontier + all 2B guards after it.

## 2026-07-12 — FINAL tick-013: frontier 0.950 on gen-002 after lint extension; all guards green

The "short walk of" lint pattern mechanically rescued deepseek's dropped-constraint parse
(gen-tran-04 → 1.0). Final board — qwen2b: seed 1.000 (22), gen-001 0.981 (13), gen-002 0.958
(10), multiturn 0.943; deepseekv4: seed 1.000, gen-001 0.981, gen-002 0.950. The 2B matches the
frontier on direct/neutral registers and EDGES it on the indirect register, because the
mechanical repair stack was tuned against real failure traces (mostly the 2B's) and generalizes
model-neutrally, while the frontier brings its own unrepaired quirks (over-holing ?proxy on a
named entity). 43/45 questions at 1.0; both residues characterized (multi-part composite =
spec-level; split-entity mode-ambiguous indicator = honest DataRequest).

# ================= ROUND 2 =================

## 2026-07-13 — R2 Step A: source-expansion census [CONNECTOR]

Two NEW keyless source families adopted (verified rows before adoption, per Round-1
discipline); full integrity snapshot in `coverage/source-census.json` (15/15 probes green,
incl. 2 negative controls).

**Source 4 — GTFS static feeds via the Mobility Database keyless mirror (ADOPTED,
`gtfs_select`).** The catalog CSV (bit.ly/catalogs-csv → GCS, 3355 feeds) indexes
agency-published GTFS zips on the keyless `mdb-latest` bucket. Curated registry of 4 verified
feeds: Winnipeg (mdb-717, 3873 stops/71 routes), Christchurch (mdb-1313, 2060/29), Oulu
(mdb-869, 1659/52), Tampere (mdb-866, 3410 stops/113 routes). Entities: "transit stops"
(stops.txt, WITH lat/lon — spatially relatable, unlike OSM route relations) and "scheduled
routes" (routes.txt, no geometry, note says so). Grain: city-feed/stop-point, operator
snapshot. Evidence: observed (agency-published). Judge decisions:
1. **No silent fallback**: "transit stops" in an unregistered city returns an EMPTY result →
   `empty_select` DataRequest naming the registered cities. Falling through to OSM bus_stop
   points would be a wrong-source answer that scores green (the Round-1 school/enrollment
   lesson applied forward). Verified: Rosario → DataRequest.
2. **Parent stations excluded**: stops.txt rows with `location_type` ∉ {'',0} (stations,
   entrances) are dropped so "how many stops" counts boarding stops, not station shells.
3. Transitland API v2 and the Mobility Database v1 API were REJECTED as keyless families
   (both require keys); the catalog CSV + GCS mirror is the keyless path.

**Source 5 — city open-data ridership series via Socrata (ADOPTED, `ridership_series`).**
Grain: city-system/annual — a grain neither OSM (snapshot points) nor the WB (country/annual)
covers. Registry: Chicago CTA annual boarding totals (w8km-9pzd, 38 yearly points 1988–2025,
bus/rail/total; observed administrative) and NY MTA daily ridership (vxuj-8kew, SoQL
server-side yearly aggregation; 2021–2024 usable). Judge decisions:
1. **[EVIDENCE-STATUS FINDING — the transport twin of livelihoods' modeled-ILO catch]** The
   MTA upstream fields literally read `subways_total_estimated_ridership` — this is
   upstream-MODELED data. The connector labels the whole city `modelled`, and the taint
   propagates: a trend answer over NYC ridership now carries label `modelled` end-to-end
   (verified). Chicago (farebox/administrative counts) stays `observed`. Without this per-city
   registry field, estimated ridership would have entered as 'observed' exactly like ILO
   modeled stats did in the livelihoods run.
2. **Partial-year guard**: years with <360 days of daily data are dropped with a provenance
   note — 2020 has only 306 days (dataset starts 2020-03-01) and the trailing year is always
   in progress; a partial annual sum silently poisons CHANGE/TREND answers. (An analogous
   trailing-partial risk exists for Chicago 2025; the dataset publishes full-year totals, so
   it is kept — but flagged for the synthesis canary.)
3. `_maximal_hits` added to the new resolvers: "bus ridership" also hits the subset key
   "ridership"; subset hits are specificity, not ambiguity (Round-1 same-code WB lesson,
   generalized to token-subset keys).

**Round-1 family re-audit [EVIDENCE-STATUS]**: WB IS.AIR.PSGR / IS.AIR.DPRT are ICAO
compilations that INCLUDE ICAO staff estimates for gap years; IS.SHP.GOOD.TU includes
UNCTAD derivations. Kept label `observed` (administrative compilations, primarily reported)
but the caveat now rides in every provenance note via `WB_EVIDENCE_NOTES` — the answer
surface can no longer present these as purely reported counts.

**Routing order is now**: gtfs → ridership → osm-routes → world-bank → osm-points (most
specific multi-token keys first). Regression-verified: "bus stop"→OSM points, "bus lines"→OSM
routes, "air passengers"→WB all unchanged.

## 2026-07-13 — R2 Step B: coverage matrix baseline [HARNESS]

`harness/coverage.py` (own adaptation of the livelihoods reference; source inference mirrors
the executor routing order exactly, so the matrix can never claim a source the executor would
not pick). Round-1 baseline over 45 questions: **11 unique skeletons**; empty/singleton cells
that drive Round-2 generation: osm-routes×STATE is a singleton and osm-routes appears nowhere
else; gtfs-mobility-database and city-open-data-ridership are empty everywhere; world-bank has
no STATE or COMPOSITE cell; relations `distance`/`cooccur` unused; ESTIMATE `interpolate`
unused; time_form `window` only 3. gen-003 targets exactly these cells.

## 2026-07-13 — R2 tick-014/015: gen-003 first contact 0.968 → 1.000; guards all green

gen-003 (18 Qs, generated against the coverage-matrix gaps: GTFS cities, ridership series,
osm-routes, time windows, distance, interpolate) — first contact **0.968** (15/18), inside the
Round-1 band. Mined + judged:
- **gen3-tran-01/16 [PARSER]**: the Round-1 truncation trap on the NEW 3-token phrase:
  "scheduled transit stops/routes" → bare "transit" → honest no_connector (bare "transit" is
  deliberately unmapped — mode-less, aliasing it would guess). Fix per Round-1 playbook:
  entity-swapped few-shot #1 (clinic count → "scheduled transit stops", Bergen — place
  disjoint from banks), few-shot total stays 15. NO alias for "transit" (judge call: the
  resolver must not guess a mode).
- **gen3-tran-03 [HARNESS lint gap]**: "how far is the nearest X from Y" — distance-anchor
  phrasing outside the proximity lint's patterns; the 2B emitted a bare SELECT. Extension of
  the anchored-proximity lint (model-neutral, same class as Round-1's "short walk of"):
  distance pattern → mechanical RELATE(relation:"distance") wrap.
- **Gold-quality catches (gold author = deepseekv4, admission = execution+structure):**
  (1) gen3-tran-06's gold used entity "rail transit" → routed to OSM stations → empty
  time-bins → trend over nothing → "answer" with value None. STATUS-ONLY ADMISSION IS TOO
  WEAK — added the grounded-value admission check to propose.py (answer must carry rows or a
  non-null value). Gold hand-corrected to "rail ridership" (question intent: popularity =
  ridership, source exists, label modelled). (2) gen3-tran-18 was rejected at admission by a
  TRANSIENT Overpass failure; verified healthy and re-admitted (breaker log annotated, not
  deleted). (3) gen3-tran-03's gold widens "central railway station" → all stations —
  accepted as the best expressible tree, logged as FILTER-proposal evidence.
- tick-015 after fixes: gen-003 **1.000**, seed 1.000, gen-001 0.981, gen-002 0.958,
  mt 0.943 — no rotation from the few-shot swap or lint extension.

## 2026-07-13 — R2 breaker program: 32 probes, 8 families; 3 executor completions [SPEC-PROPOSAL x7, HARNESS x3]

Full pre-judged bank: `questions/breakers-round2.json`; evidence runs
`runs/round2-breakers-{pre,post}`. Outcome bins: 25 inexpressible (→ 7 proposal entries in
spec-proposals.md), 4 expressible stress tests, 3 executor-gaps. **Headline: on inexpressible
asks the 2B silently WEAKENS (27/32) rather than hallucinating ops (1/32 invalid, 0 invented
ops)** — sheltered stops → all stops; bus+tram union → trams only; by-mode breakdown → the
total. The weakened trees score green and read authoritative; this is the strongest argument
yet for proposals-not-weakened-golds.

Three judge decisions became PRE-FREEZE executor completions (all deterministic,
provenance-stamped, all guards re-run green — tick-016):
1. **Windowed mean (brk2-25)**: AGGREGATE{by:space, metric:mean} over a Series now collapses
   to the window mean. Before: passthrough made "average 1990s vs 2010s" compare ENDPOINT
   years 1999 vs 2019 — answer -61.8M with the true decade-mean answer +55.8M — opposite
   signs, silent. by:time stays the documented bin/identity; metric:count stays
   value-semantics passthrough (Round-1 RANK golds scalarize the latest VALUE — redefining
   count would rewrite their denotations; checked before deciding).
2. **Same-entity orientation guard (brk2-21)**: my per-capita gold was silently INVERTED by
   the Round-1 later-minus-earlier measure (population's series merely ends later than air
   passengers') — "people per passenger" instead of per-capita. Orientation now requires both
   operands to have resolved to the same entity. Round-1 change-question behavior verified
   unchanged.
3. **Grain tags + mismatch disclosure (brk2-19/20)**: the evidence run FALSIFIED my pre-run
   judgement ("city population dies honestly as a DataRequest" — WRONG): wb_resolve_iso
   falls back city→country, so "per 1000 residents in Winnipeg" divided by CANADA (41.65M)
   and Chicago-per-resident divided by the USA (341.8M). Typed values now carry `grain`;
   COMPARE stamps `[GRAIN MISMATCH: left=city-bbox, right=country]` into the note. The bank
   entries were corrected and the mis-judgement is recorded here — the runner out-judged the
   judge, which is the point of running probes.

Scoring blind spot noted (not fixed, characterized): shape is an op multiset, so a COMPARE
with the wrong `how` (trend_direction where difference was asked, brk2-25 parse) can shape-
match. Known limitation carried from Round 1; the synthesis canary is the compensating
control.

## 2026-07-13 — R2 tick-016 (post-completion guard battery): ALL GREEN — development closes

gen-003 1.000 · seed 1.000 · gen-001 0.981 · gen-002 0.958 · mt 0.943 (the two sub-1.0 rows
are the Round-1 characterized residues: multi-part composite gen-tran-10, split-entity
gen-tran-05). Breaker re-run after completions: brk2-25 gold now decade-means; brk2-19/20
0.75 with disclosure (parser residue: reaches for metric "density" on rate questions —
characterized, PARSER class, evidence in the rate-denominator proposal); brk2-21 0.75 (2B
flattens 2-level per-capita nesting to a plain difference — characterized). Development is
closed; FREEZE follows.

# ================= ROUND 2 — FROZEN EPOCH r2-freeze-1 (no fixes past this line until holdout C) =================

## 2026-07-13 — HOLDOUT A (neutral register, 42 Qs, first contact): 0.982

38/42 at 1.0. Four sub-1.0 rows, judged (characterize ONLY — the epoch forbids fixes):
- **ho2a-tran-36 (0.75) — NEW CLASS #1: nested-COMPARE delta-of-deltas weakening [PARSER].**
  "Is bus or rail ridership changing faster since 2021?" The GOLD is legitimate and grounded:
  difference-of-deltas COMPARE(COMPARE(bus@23,bus@21), COMPARE(rail@23,rail@21)) → -346.5M
  (rail changed faster) — note the frozen executor handled it correctly (per-branch same-entity
  orientation, no cross-branch flip). The 2B weakened to a single trend over bus only. No
  Round-1/Round-2 development bank exercised 3-COMPARE nesting; the curriculum has no such
  exemplar. Genuinely uncharacterized before this run → counts against the discovery budget.
- **ho2a-tran-30 (0.83) — under-holing, characterized class (Round-1 mt-02) [PARSER].**
  "Do people in Zurich prefer buses over trams?" — SELECT entity "people" concrete instead of
  the ?proxy hole. Mechanism identical to mt-02's under-holing (concrete entity where a hole
  belongs); terminal state is still an honest DataRequest (no_connector "people" — nothing
  fabricated). Judged an INSTANCE of the characterized under-holing class; the borderline
  nature of this call is recorded deliberately.
- **ho2a-tran-41 (0.83) — connector-lexicon synonym gap, characterized class [CONNECTOR].**
  "Is flying getting more common in Indonesia?" → entity "flights": correct tree, honest
  no_connector ("flights"/"flying" not in the WB alias table; "aircraft departures" is).
  Round 1's most common connector fix class (charging/railway aliases). Instance recorded;
  alias NOT added (frozen).
- **ho2a-tran-42 (0.83) — restated-entity selection, characterized class (gen-tran-05) [PARSER].**
  "…compare public transit in Tampere and Oulu — which city has more scheduled routes?" The 2B
  compiled the umbrella noun "public transit" instead of the question's own restatement
  "scheduled routes" → honest no_connector. Same mechanism as the Round-1 split/restated-entity
  residue.

Bank-A discovery count: **1 new class / 42 questions**; no answer-surface, provenance, or
corpus-integrity violation; all failures terminate in honest DataRequests or a disclosed
weakening caught by shape scoring.

## 2026-07-13 — HOLDOUT B (indirect register, 44 Qs, first contact): 0.960

39/44 at 1.0. Five sub-1.0 rows, all judged INSTANCES of classes already on the books
(0 new classes this bank):
- **ho2b-tran-37 (0.75), ho2b-tran-40 (0.42): the delta-comparison nesting class (#1, discovered
  in Holdout A)** — "which country had a larger increase 2000→2010" (gold: COMPARE of two
  per-country delta-COMPAREs) and "biggest increase since 2010 among three" (gold: RANK over
  three delta-COMPAREs). The 2B substitutes window MEANS for deltas each time. Three instances
  across A+B make this the epoch's dominant parser residue: the curriculum teaches
  change-of-one-series and compare-two-values but never delta-PER-ITEM composition. Fix
  candidates (post-epoch): one delta-per-item few-shot (would need a slot under the 15 cap) —
  NOT applied inside the frozen epoch.
- **ho2b-tran-17 (0.67), ho2b-tran-35 (0.67): over-holing a NAMED place [PARSER, characterized]**
  — goal-first sentences with the city mid-clause ("...in Accra — which fuel stations...")
  pushed the 2B to region "?place" despite the name being present. Round 1 characterized
  over-holing when judging the frontier's ?proxy on the Curitiba question (tick-012); these are
  the 2B's instances of the same class, triggered by the indirect register. Terminal state:
  unbound-holes DataRequest (a needless clarifying question — annoying, never wrong).
- **ho2b-tran-30 (0.75): COMPARE/RANK arity confusion [PARSER, characterized tick-008 family]**
  — a two-city comparative compiled to a 2-item RANK (plus a degenerate double-AGGREGATE). The
  reverse of Round 1's nested-COMPARE-for-3 failures; same arity-selection mechanism.

Bank-B discovery count: **0 new classes / 44 questions**. Layer scores stable (parse/schema
1.00, exec_grounded 1.00); every failure lands in an honest DataRequest or a shape-scored
weakening; no answer-surface or provenance violation.

## 2026-07-13 — HOLDOUT C (mixed/terse register, 45 Qs, first contact): 0.968

40/45 at 1.0. Five sub-1.0 rows, judged:
- **ho2c-tran-29 (0.71) — NEW CLASS #2: place transcription typo + error-not-DataRequest
  terminal [PARSER + HARNESS].** "i need bus stop counts for evora portugal..." — the 2B wrote
  "Evrora, Portugal". The faithfulness pass accepted the typo because ANY token of a place may
  trace (the country token "portugal" vouched for the misspelled city), and the Nominatim miss
  then surfaced as execution status **error** (RuntimeError) rather than an unresolved-region
  DataRequest. Two coupled mechanisms never seen in Round 1 (which produced truncations and
  inventions, never misspellings). Post-epoch fix candidates: per-token city-segment
  traceability; region-not-found → DataRequest. NOT applied inside the epoch.
- **ho2c-tran-38 (0.75) — dropped proximity constraint, characterized lint-phrasing-gap class**
  ("near railway stations" carries no article, so the anchored-proximity pattern missed it;
  same class as Round 1's "short walk of" and tick-014's "how far").
- **ho2c-tran-39 (0.75) — multi-output ask ("count both"), characterized multi-part class**
  (Round-1 spec proposal; the 2B answered one of the two counts).
- **ho2c-tran-44 (0.83) — entity truncation ("container port traffic" → "container port"),
  characterized truncation class; honest no_connector.**
- **ho2c-tran-45 (0.50) — RANK composition failure in the terse register ("...— order
  descending" became an illegal `order` field on AGGREGATE), characterized tick-008 RANK
  family; the strict-fields schema guard surfaced it loudly (unknown-field error), nothing
  silent.**

Bank-C discovery count: **1 new class / 45 questions**.

## 2026-07-13 — EPOCH r2-freeze-1 VERDICT (checksums re-verified: all frozen files intact)

| bank | register | n | overall | new classes | characterized-class instances |
|---|---|---|---|---|---|
| holdout A | neutral | 42 | 0.982 | 1 (delta-nesting) | 3 |
| holdout B | indirect | 44 | 0.960 | 0 | 5 |
| holdout C | mixed/terse | 45 | 0.968 | 1 (place-typo terminal) | 4 |
| **total** | | **131** | **0.970 wtd** | **2** | **12** |

Discovery RATE: 2 new classes / 131 questions = **0.76 per 50 questions — below the <1/50
threshold**, and bank B ran clean of new classes entirely. But ROUND2.md's plateau criterion
also demands **no new failure class across the sequence**, and there were two. JUDGE VERDICT:
**the saturation statement is NOT issued.** The honest claim: the transport stack is
approaching plateau on this distribution (layer scores stable: parse 1.00 / schema ≥0.98 /
grounded ≥0.98 everywhere; every failure terminates honestly; no provenance or corpus
violations), with one dominant residual parser class (delta-per-item composition, 3 instances)
and one low-frequency transcription class (1 instance). Both now have identified, cheap fix
candidates; a fresh freeze epoch after those fixes is the path to the saturation statement.
Claiming saturation over a criterion this protocol explicitly wrote down would be exactly the
kind of grade inflation the frozen-epoch design exists to prevent.
