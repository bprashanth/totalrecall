# MISSION: replicate the place-question algebra benchmark on YOUR sector

You are an autonomous engineering agent. This directory was bootstrapped for one **sector** (see
`sector.json`). Your job: run the self-improving benchmark loop that tests whether user questions
about places, in *your sector*, compile into the frozen query algebra and execute against *real
data* — and produce results directly comparable to the reference run. Work top-to-bottom through
this document. Do not wait for permission between steps; document as you go.

## 1. What this is (2-minute context)
A small local model translates an English question into a JSON expression tree (the "IR"), a
deterministic executor runs the tree against live data connectors, and code (not model discipline)
enforces honesty: observed-vs-modelled labels, ask-when-ambiguous via typed holes, data gaps as
first-class DataRequest answers. The reference run (5 civic sectors, 89 questions) reached 1.000
with a 2B parser and, along the way, *discovered* two algebra ops via failure probes (RANK, and the
`beyond` complement relation). Read `algebra/README.md` (the design) and `algebra/ir-spec.md` (the
machine-checkable spec, **v2.1 — FROZEN for you**) before writing any code. v2.1's COMPARE
operand-orientation rule (later-minus-earlier for time-anchored difference/ratio) is already
implemented in the executor — do not re-fix it, and do not penalize the parser for operand order.

## 2. Roles — read carefully, this is where comparability lives
- **Parser under test = the local Qwen3.5-2B**, OpenAI-compatible at `http://172.17.0.1:8001/v1`
  (served name `qwen3.5-2b`). You do NOT parse questions yourself — comparability with the
  reference requires the same 2B doing the compilation. Verify it's up:
  `curl -s http://172.17.0.1:8001/v1/models`. `harness/llm.py` already routes role `qwen2b` there.
- **Question generator + gold author = deepseek-v4** via OpenRouter (key at
  `~/.config/idlisseus/openrouter.json`; `llm.py` role `deepseekv4`). Gold trees are only admitted
  if they validate AND execute to the expected outcome class AND satisfy structural requirements
  (`propose.py` does all of this).
- **You = the engineer and the sector JUDGE.** In the reference run the judge decided: which tree
  shapes are equivalent paraphrases (allow-sets), which failure belongs to which layer
  (connector/parser/harness/scoring/spec), and what fix goes where. Every such decision you make
  MUST be written to `FINDINGS.md` with reasoning. What you may NOT do: change the IR spec —
  ops, fields, vocabularies, hole semantics, evidence rules are frozen. If your sector's questions
  cannot be expressed, that is a **discovery**: write it to `spec-proposals.md` with the failing
  question + trace as evidence, mark the question blocked, and move on. (This is how RANK and
  `beyond` were found; a proposal with evidence is a success, not a failure.)

## 3. Environment facts
- Local model endpoint as above. If `:8001` serves a different model name, STOP and report — do not
  substitute another parser. The 2B is SHARED, always-on infrastructure: other sector runs hit it
  concurrently (vLLM batches requests — parallel benches are safe and expected). NEVER stop,
  restart, or reconfigure it or any docker container, and never bind servers on ports 8002+ (they
  are reserved for other experiments).
- OpenRouter for deepseek: already wired in `llm.py`. All LLM + HTTP responses are disk-cached in
  `harness/cache/` (safe to delete; re-fetches).
- Keyless data sources already wired: Nominatim (region resolver — keep it, it's sector-neutral),
  OSM Overpass (point amenities), World Bank (country indicator series). Be polite to Overpass
  (the cache does most of this).

## 4. Step 0 — sector data census (do this BEFORE questions)
Find 2–4 data sources for your sector. Requirements: reachable without accounts/keys where
possible; VERIFY each actually returns rows for 2–3 test places before building on it (phantom
sources were a real failure mode). For each source record in FINDINGS.md: what entity types it
serves, its geographic/temporal grain, and a working sample request. The reference lesson: most
places are data-thin — the abundant axis becomes your bridge; genuine thinness becomes DataRequest
answers, which the scorer treats as CORRECT when expected.

## 5. Adding connectors (the only code you're expected to write)
Contract (see `harness/connectors.py` for two worked examples):
- A connector function returns `{"rows": [...], "kind": "records"|"series", "source": str,
  "note": str}`. Records rows carry `lat`/`lon` (+`name`,`time`); series rows carry `{t, value}`.
- **Resolver**: map lay entity phrases to your source's vocabulary with DIRECTIONAL token matching
  (all key-tokens must appear in the entity phrase, prefix-tolerant; never entity⊆key — that
  mis-routed "school"→"school enrollment" in the reference and scored green on wrong data). Add
  explicit aliases for common truncations. Flag ambiguity, never guess silently.
- **Routing**: add a branch in `executor.py::_route_select` (order: most-specific resolver first).
  Unmappable entity ⇒ raise `DataRequest("no_connector", ...)` — never fabricate.
- Sparse time series: nearest-year fallback within ±3, and SAY SO in the note (provenance).
- Cache all HTTP through `connectors._get`.

## 6. Question bank
Author `questions/seed.json` (~20 questions, hand-written gold IR) covering ALL types: STATE,
RELATION (incl. `beyond` negations + threshold distances), CHANGE, TREND, VALUE if your sector has
point measurements, TRANSFER (must contain ESTIMATE), AMBIGUOUS (must produce holes — deictic
place words are always holes), BEHAVIOUR (intent questions → proxy + data_request), COMPOSITE,
RANKING (3+ items, must contain RANK). Then widen with `propose.py` (edit its GEN_PROMPT sector
notes; keep generation NEUTRAL — the generator never sees parser outputs). Fields per question:
`{id, sector, type, q, gold_ir, gold_shape, expect, must_hole?, must_estimate?, gold_shapes?}` —
copy the reference format exactly.

Two KNOWN cross-sector limitations (found independently in both prior sectors — don't rediscover
them the hard way):
- **Multi-part questions** ("does A have more X than B, AND how many of those are near Y?"): one
  tree answers ONE question, and the gold author will SILENTLY produce a half-gold for the first
  clause — execution-validation cannot catch it. Do not admit such questions; split them into two
  single-clause questions, or exclude and note them. (Cross-sector decision: dialogue-layer clause
  splitting, not a new op — see the central spec-proposals.)
- **Entity unions** ("hospitals and clinics"): no OR over record sets exists. If your sector needs
  it (e.g. "bus and tram stops"), that's evidence for the open union proposal — log it with the
  trace, use the broader umbrella entity if your resolver has one, and move on.

## 7. The loop (a "tick")
```
python3 harness/run_bench.py --model qwen2b --questions questions/seed.json --out runs/tick-001 --synth
# keep --synth ON: reading the synthesized prose is how a structurally-green wrong answer gets
# caught (the COMPARE sign bug was found ONLY because a sector agent read "decreased by 38M" for
# a series that tripled). Structural scores alone can lie; prose is your canary.
python3 harness/mine.py runs/tick-001          # classifies failures by layer
# fix at the RIGHT layer:
#   CONNECTOR -> connector/resolver/alias;  PARSER -> few-shots in parser.py (keep total <=15;
#   above that fixes start rotating — that's in-context saturation, STOP adding);
#   SCORING -> allow-sets (gold_shapes) for genuine paraphrase equivalences (document in FINDINGS);
#   SPEC -> spec-proposals.md, never the spec itself.
# then guards: re-run ALL previous banks — a fix that breaks an old bank doesn't ship.
python3 harness/compile_corpus.py              # refresh corpus/ (the training-data deliverable)
python3 harness/inspect.py                     # HTML reports: runs/index.html
python3 harness/multiturn.py runs/tick-XXX-mt qwen2b   # dialogue layer check (adapt CASES to sector)
```
Repeat until scores plateau AND the residue is characterized (not merely tolerated). Also run
`--model deepseekv4` once on your final banks as the frontier reference point.

## 8. Parser prompt rules (edit carefully)
You may swap the ENTITIES in `parser.py` few-shots to your sector's domain, but keep the same tree
shapes (they are a curriculum: holes, deictic place, RANK, beyond+threshold, conjunction chain,
count-over-RELATE). Keep the system prompt otherwise verbatim. The repair stack (brace-completion,
peephole unmerge, literal-provenance check, semantic lints with mechanical synthesis) is part of
the frozen harness — extend lint patterns for your sector's phrasings if needed, and log any new
mechanical repair you add to FINDINGS.md.

## 9. Deliverables (the comparability contract — do not deviate)
- `runs/*/traces.jsonl` + `summary.json` in the reference schema (run_bench emits it — don't edit).
- `corpus/parse.jsonl` + `corpus/clarify.jsonl` via compile_corpus (identical format; your rows
  carry your sector in `meta.sector` → cross-sector LoRA merges are simple concatenation, and a
  sector-specific LoRA trains on your file alone).
- `FINDINGS.md` (findings + judge decisions), `spec-proposals.md` (evidence-backed),
  `chronology/YYYYMMDD_<name>.md` — one plain-word narrative per experiment: why, and what you
  ended up with.
- A final `REPORT.md`: scoreboard trajectory, per-layer failure counts, your sector's residue,
  and the head-to-head table vs BOTH references: the civic reference (2B, six banks, 89 Qs,
  final 1.000; first-contact on unseen banks 0.93–0.97) and the transport replication
  (45 Qs, final 0.985 weighted; first-contact 0.89–0.97 — see
  `../transport_memory/REPORT.md` if present).

## 10. Known traps (each cost a prior sector run a tick)
Geocoding picks tiny same-named POIs (rank areal features, pad bboxes); localized place names break
downstream URLs (resolve from the user's original string, compare alphanumerics only); duplicate
place segments ("X, X") geocode to the wrong country; models truncate entity phrases (aliases +
"copy phrases whole" rule); an executing gold is not a correct gold (structure requirements exist
for a reason); **plausible-looking indicator codes can be phantoms** — the transport run killed two
World Bank codes at census time that looked real but returned no rows, so verify EVERY code with a
live request before it enters the resolver; empty SELECT = data gap but empty RELATE over non-empty
inputs = a true "none" answer; and NEVER present a modelled estimate as observed — the label
propagation does this for you if you don't bypass it.
