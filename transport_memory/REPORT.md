# REPORT — transport sector replication (2026-07-12)

Parser under test: **qwen3.5-2b** (local vLLM, 172.17.0.1:8001), spec **v2 (frozen)**, harness
unchanged in trace/summary/corpus schemas. Question banks: `seed` (22, hand-written gold),
`gen-001` (13, neutral generation), `gen-002-indirect` (10, indirect register) = **45 questions**.
Judge decisions and per-tick reasoning: `FINDINGS.md`. Narrative: `chronology/`. Proposals:
`spec-proposals.md`. Browsable traces: `runs/index.html`.

## Scoreboard trajectory (qwen2b)

| tick | bank | event | overall |
|---|---|---|---|
| 001 | seed (22) | baseline, stock curriculum | 0.966 |
| 002 | seed | + CHANGE few-shot, railway alias, repair-faithfulness guard | **1.000** |
| 003/004 | seed guard + mt | station-hole few-shot (incl. one rotation, fixed) | 1.000 / mt 0.943 |
| 005 | seed guard | + COMPARE orientation (executor), synth-scorer extensions | 1.000 (synth 1.0) |
| 006 | gen-001 (13) | **first contact, unseen** | 0.923 |
| 007 | gen-001 | + charging alias, this-X few-shot, em-dash fix, time peepholes | 0.981 |
| 008 | seed + mt guards | all green | 1.000 / 0.943 |
| 010 | gen-002 (10) | **first contact, unseen, indirect register** | 0.892 |
| 011 | gen-002 | + self-transfer unwrap, prefix-tolerant provenance | 0.958 |
| 012/013 | ALL banks + mt guards | final battery, all green | 1.000 / 0.981 / 0.958 / 0.943 |

Final: **43/45 questions at 1.0**; weighted overall across the three banks **0.985**.

## Head-to-head vs the reference run

| | reference (5 civic sectors) | transport (this run) |
|---|---|---|
| parser | 2B (qwen3.5-2b) | same model, same endpoint |
| questions | 89 across 6 banks | 45 across 3 banks |
| final overall | 1.000 | seed 1.000 · gen-001 0.981 · gen-002 0.958 (0.985 weighted) |
| first-contact on unseen banks | 0.93–0.97 | 0.923 (neutral) · 0.892 (indirect) |
| ops discovered missing | RANK, `beyond` | none (v2 sufficed) — but 2 semantic spec debts filed |
| multiturn | mech-bind >> model-bind | same: mech 5/5, model-bind only failing leg (0.943) |

Frontier control (deepseekv4, same prompt/harness): seed **1.000**, gen-001 **0.981** (identical
to the 2B, failing the same multi-part question the same way), gen-002 **0.950** — *below* the
2B's 0.958. Frontier failure modes were different, not fewer (over-holed a named entity;
dropped a "short walk of" proximity constraint until the lint learned the phrasing). Past the
mechanical-repair floor, parser size is not the binding constraint.

## Failure-layer counts (across all mining, before fixes)

| layer | count | instances |
|---|---|---|
| CONNECTOR | 3 | railway/charging truncation aliases; (census) 2 phantom WB codes rejected pre-bank |
| PARSER | 5 | missing CHANGE exemplar; entity truncation; under-holing "stations"; "this X" deictic; spurious ESTIMATE (indirect register) |
| HARNESS | 5 | repair-derail (validity-only acceptance); em-dash tokenization; time misfiled/missing; adjectival-place false demotion; anchor-lint phrasing gap |
| SCORING | 3 | synth scorer: string findings, operand-stated differences, "cannot" gap phrasing |
| SPEC | 2 | COMPARE operand order (silent sign flip); multi-part questions (one tree = one answer) |

New mechanical repairs added (all logged in FINDINGS): `entities_faithful` repair-acceptance
guard, SELECT-time fill/hoist peepholes, ESTIMATE self-transfer unwrap, non-alnum provenance
tokenization with prefix tolerance, difference/ratio later-minus-earlier orientation
(provenance-stamped), anchored-proximity lint phrase extension.

## Residue (characterized, not tolerated)

1. **gen-tran-10 (gen-001, 0.75)** — two-part composite. Inexpressible in one tree; the 2B jams
   both clauses into a 4-item RANK, the frontier and the gold silently drop clause two. Spec
   proposal filed (recommend dialogue-layer splitting); scoring left honest rather than
   allow-set-ed.
2. **gen-tran-05 (gen-002, 0.58)** — entity split across the sentence ("Indian railways ... has
   passenger traffic grown"); "passenger traffic" alone is mode-ambiguous (air/rail), so the
   correct terminal state is the no_connector DataRequest the parse now reaches; aliasing it to
   a rail indicator would recreate the reference's wrong-source trap.
3. **multiturn model-bind (0.943)** — the 2B cannot reliably substitute values into holes;
   mechanical binding is 5/5. Ship binding as code (the architecture already assumes this).

## Spec proposals filed (evidence-backed, spec untouched)

1. **COMPARE operand-order semantics** — question-order operands execute to a sign-flipped
   scalar that survives every structural check and becomes a fluent wrong answer ("decreased"
   for a series that tripled). Discovered via the SYNTHESIS layer, invisible to shape scoring.
2. **Multi-part questions** — one tree returns one answer; both 2B and frontier degrade
   two-part questions; recommend dialogue-layer clause splitting over a QUERYSET op.

## Transport-specific findings worth carrying cross-sector

- **Transit lines are relations, not points**: new connector (`osm_routes_select`) with a
  different Overpass query shape; a "line" is 2+ direction-variant relations, deduped by `ref`
  (Brno: 280 relations -> 124 lines). Route rows carry no geometry by design — countable, not
  spatially relatable — stated in provenance.
- **Sector thinness is structured, not random**: trams exist in 1 of 4 probe cities, no metro
  in any, landlocked countries have zero port rows, and the EV gradient is stark (Brno 187
  charging stations, Mombasa 0). All of these become honest DataRequests, and the scorer
  correctly treats expected ones as CORRECT.
- **The data census kills phantoms before they poison golds**: IS.VEH.NVEH.P3 and
  IS.ROD.PAVE.ZS look like ideal transport indicators and are dead outside Kenya/pre-2010;
  rejected at census time, so no bank ever referenced them.

## Deliverables

- `corpus/parse.jsonl` — 45 verified question->IR rows (`meta.sector: "transport"`);
  `corpus/clarify.jsonl` — 30 multiturn rows. Concatenable with other sectors as-is.
- `runs/*/traces.jsonl` + `summary.json` in the reference schema; `runs/index.html` reports.
- `FINDINGS.md` (census + all judge decisions), `spec-proposals.md` (2 entries),
  `chronology/20260712_transport_replication.md`, `questions/{seed,gen-001,gen-002-indirect}.json`
  + `questions/breakers.json` (4 rejected candidates with reasons).
