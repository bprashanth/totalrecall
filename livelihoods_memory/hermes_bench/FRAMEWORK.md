# Hermes Erode drilldown bench — multi-turn, human-like, response-quality benchmark

**Owner: Fable (judge + designer). Status doc — read this first after any compaction.**
**Do not touch anything else in livelihoods_memory/ (codex snapshot) or the eco mounts in
hermes-live (/opt/data/connectors, query_data, corpus, work/gt are ECOLOGY — off-limits to Fable).**

## What this is

A benchmark of *conversations, not compilations*. A simulated NGO worker from Erode district,
Tamil Nadu (Kongu belt: turmeric, powerlooms, textile dyeing, dairy) interrogates Hermes about
their own place across 12–16 sequential turns, drilling from "tell me about the place" down to
livelihood shares, crop economics, industry linkages, pollution externalities, wage labour, and
deliberately data-scarce corners. Hermes runs with different center models (arms) and its answers
are judged as *responses a human reads*: factual grounding, honesty about evidence, place
knowledge, prose quality, conversational coherence.

## Arms

| arm | hermes provider | brain |
|---|---|---|
| A-2B | `loravb` → http://172.17.0.1:8002/v1 | Qwen3.5-2B + adapter-002 (merged, HF shim) |
| A-9B | `lora9b` → http://172.17.0.1:8004/v1 | Qwen3.5-9B + adapter-002 |
| A-DS | `deepseekv4` → OpenRouter | DeepSeek-V4 frontier reference |

Rules: hermes-live's `model.default` stays untouched (:8001 is shared infra — NEVER restart or
repoint). Providers are *added* to /opt/data/config.yaml (backup kept). Arms are selected
per-invocation with `-m/--provider`. Optional refinement sandwich (deepseek pre/post around the
small center) is a *separately labeled* arm (A-2B+refine), never silently mixed in.

## Data pack (the "enough datasets" requirement)

Location: `/home/beeps/.hermes/livelihoods_erode/` (= `/opt/data/livelihoods_erode/` in-container),
mirrored in `hermes_bench/data/` here. Every record carries `{source_url, source_title, vintage,
evidence: observed|scraped|secondary|modelled, retrieved}`. **No number enters the pack without a
fetched source document; nothing is authored from model memory.** Fictional data is prohibited.

Target datasets (thin JSON, 2B-readable via a one-command CLI):
1. `census2011_workers.json` — Census 2011 PCA, Erode district: total/main/marginal workers,
   cultivators, agricultural labourers, household industry, other workers; rural/urban.
2. `industry_profile.json` — DIC/MSME district industrial profile: powerloom/handloom units,
   textile dyeing & bleaching, tanneries, oil mills, dairy; employment where stated.
3. `turmeric_mandi.json` — Erode turmeric market (agmarknet or equivalent): arrivals/prices.
4. `mgnrega.json` — MGNREGA Erode: households provided work, person-days (public MIS).
5. `papers.json` — excerpted, cited abstracts/findings: Noyyal/Bhavani textile-effluent
   agriculture impact, Kalingarayan canal irrigation, powerloom cluster wage studies, LPA/Bhavani
   basin water stress. Each excerpt ≤80 words + full citation.
6. `GAPS.md` — what we could NOT source (e.g. current informal dyeing-unit wages, ward-level
   dairy incomes). The scripted scarce turns aim here; the correct model behavior is an
   ESTIMATE with a stated basis + an explicit DATA REQUEST back to the user.

Access tool: `/opt/data/livelihoods_erode/edata` (python CLI): `edata list`,
`edata get <dataset>`, `edata grep <term>`. One command, JSON out — a 2B can drive it.

## Conversation protocol

- Persona + arc: `persona/arc.md`. Turn 1 is always "tell me about <place>"; later turns follow
  the arc but each is REPHRASED conditioned on Hermes' previous answer (the follow-up references
  something the answer said — that's what makes it human). The driver uses deepseekv4 to phrase
  follow-ups (grinder role), 1–2 sentences, NGO-worker register.
- Driver: `run_bench.py` → `docker exec hermes-live hermes -z "<turn>" --continue erode_<arm>
  -m <model> --provider <provider>`. Transcripts land in `transcripts/<arm>/NN.md` + a combined
  `transcripts/<arm>.md`.
- Scarce turns (≥2 per run) intentionally ask for data the pack lacks (see GAPS.md): the rubric
  rewards labeled estimation + DataRequest and *punishes* confident fabrication.

## Judging (Fable, human hat) — `judge/RUBRIC.md`

Per turn, 0–2 each: grounding (numbers/claims traceable to pack or honestly labeled), honesty
(evidence labels, estimate-vs-observed, DataRequest when warranted), place knowledge (says true,
specific things about Erode, not generic-India filler), prose (clear, warm, right length, no
list-dump when a sentence would do), coherence (builds on prior turns, remembers what was said).
Hallucinated specifics = automatic 0 on grounding for the turn + logged to `judge/hallucinations.md`.
Arm score = mean per dimension + turn-level table. Frontier bar = A-DS run + Fable's own judgment
of what a good frontier answer would say. Optional second judge: cursor CLI on transcripts.

## Improvement loop

Iterate ONLY scaffold-side between rounds: `improve/vN/` holds the SOUL section, playbook file
(`/opt/data/livelihoods_erode/PLAYBOOK.md`, injected via turn-1 instruction), and skill tweaks +
the before/after score table. Model weights never change mid-bench. Stop when A-2B/A-9B turn
quality is judged at/near A-DS or two iterations plateau.

## Status log (append-only)
- 2026-07-17: framework written; recon done (hermes CLI: `-z`, `--continue <name>`, `-m`,
  `--provider`; config at /opt/data/config.yaml, default=qwen@:8001 — leave alone). Eco mounts
  identified and excluded. Next: providers added → data pack sourcing → smoke test → arc → runs.
- 2026-07-17 (cont): PLUMBING DONE. vLLM cannot serve merged saves even with base configs
  (composite-vs-TextConfig class error — GOTCHA 4 confirmed final). Solution shipped:
  `benchmarks/lora/sse_proxy.py` (tracked task) on 172.17.0.1:8006→:8002(2B) and :8007→:8004(9B):
  converts hermes' streaming+native-tool-calls to the shims' plain JSON via a <tool_call> text
  protocol injected into the system message. Hermes providers loravb/lora9b now point at
  8006/8007 (config backup kept; model.default/:8001 untouched; streaming restored true).
  Smoke test PASSED via `hermes -z ... -m loravb --provider loravb --continue smoke_loravb`.
  First observation: raw LoRA-2B talks in clarify-list style — the improvement loop's job.
  NEXT (in order): 1) build data pack via WebSearch/WebFetch (census PCA workers Erode,
  DIC/MSME industry profile, turmeric mandi, MGNREGA, papers) into /home/beeps/.hermes/
  livelihoods_erode/ + edata CLI + GAPS.md; 2) persona/arc.md (12-16 turns, 2+ scarce turns);
  3) run_bench.py driver (docker exec, per-arm session, deepseekv4 phrases follow-ups from
  prior answer); 4) PLAYBOOK.md v1 (cite pack, label evidence, DataRequest on gaps, warm
  concise prose); 5) run A-2B/A-9B/A-DS, Fable judges per RUBRIC (write judge/RUBRIC.md:
  grounding/honesty/place-knowledge/prose/coherence 0-2); 6) iterate improve/vN till 2B/9B
  ≈ frontier judgment. If proxy dies: relaunch tracked with ABSOLUTE path (cwd resets!).
- 2026-07-17: DATA PACK DONE (step 1). Built in /home/beeps/.hermes/livelihoods_erode/,
  mirrored to hermes_bench/data/. Every number traces to a document fetched this session
  (WebFetch/WebSearch/curl+pdftotext) — none from model memory. Sourced: census2011_workers
  (15 records — total/main/marginal workers, cultivators/agri.labourers/HH-industry/other,
  rural-urban split, both main-only and main+marginal bases; official DCHB Erode Part-B PDF,
  censusindia.gov.in); industry_profile (12 records — 19,521 registered units, 77,500 est.
  SSI daily workers, 6,501 large/medium employment, NIC-code unit counts incl. textiles 4,406
  + dyeing/weaving 3,659 + tanneries 954, named large-scale industries, 6 identified clusters;
  official DIC/MSME-DI Brief Industrial Profile 2015-16 PDF, dcmsme.gov.in); turmeric_mandi
  (4 records — Erode/Perundurai APMC arrivals+prices for 13 Apr 2026 via Agro Spectrum India
  news, a 14 Jun 2024 price-range snapshot via commoditymarketlive.com, GI/production context
  via Wikipedia); mgnrega (5 records — 80,321 households employed of 185,051 registered,
  Rs 336/day FY25-26 wage rate; official DRDA Erode scheme datasheet PDF linked from
  erode.nic.in — the nrega.nic.in/nregastrep MIS report endpoints all 503'd or needed a
  session token, so no persondays total was obtainable); papers (6 excerpts, all ≤80 words
  with full citations — Rajkumar & Nagan 2010 + Mohanakavitha et al. 2019 on Noyyal/
  Kalingarayan textile-effluent impact on agriculture, Lannerstad & Molden 2009 on
  Kalingarayan-fed farmer adaptation, Carswell 2013 + Brindha & Sundareswaran 2019 on
  powerloom/Tiruppur labour, Prabha et al. 2025 on turmeric price cycles). GAPS.md logs 8
  honest misses (per-worker informal dyeing wages, MGNREGA persondays, dairy incomes,
  rice/oil-mill unit counts, powerloom-vs-handloom split, live agmarknet series, combined-
  worker rural/urban split, Carswell full text paywalled). edata CLI (59 lines, stdlib only,
  chmod +x) ships `list`/`get <name>`/`grep <term>`, tested working in both the .hermes/ and
  hermes_bench/data/ copies. NEXT: persona/arc.md (step 2).
- 2026-07-17 (v1 verdict + v2 infra): v1 A-2B = VOID, environment fault (live eco SOUL.md loaded;
  model roleplayed species assistant; turns 11-12 FABRICATED numbers wearing observed/modelled
  labels — see judge/scores_v1_A-2B.md; A-9B/A-DS stopped early, driver deepseek id fixed to
  deepseek/deepseek-v4-flash everywhere). v2 infra so far: /opt/data/bench_home (own config.yaml +
  livelihoods SOUL.md) used via `docker exec -e`/`HOME=/opt/data/bench_home hermes ...`; proxy now
  logs `[req] port tools keys`. CONFIRMED: hermes sends 26 tools + messages; 2B emits clean
  <tool_call> via proxy protocol (direct curl proof). REMAINING BUG: fresh sessions still surface
  eco context ("points.py") despite bench HOME -> suspect hermes long-term MEMORY feature and/or
  workspace files at /opt/data (AGENTS/TOOLS/skills) independent of $HOME. NEXT: disable memory in
  bench_home config (grep config keys), try --ignore-rules / -t hermes-cli, find workspace config
  key and point it at bench_home; SUCCESS TEST = toolsmoke answer names the 5 real datasets with
  zero species language; then rerun all 3 arms as --round v2 and judge per RUBRIC.
- 2026-07-17 (v2 infra, cont): CONTAMINATION FIXED — recipe that works: `cd /opt/data/bench_home &&
  HOME=/opt/data/bench_home HERMES_HOME=/opt/data/bench_home hermes ...` + bench_home/config.yaml
  with memory.memory_enabled:false + bench SOUL.md. 2B now genuinely attempts execute_code on
  edata (zero species language). LAST REMAINING BUG: tool_call JSON truncated mid-generation
  (token cap, likely hf_serve shim cap or proxy max_tokens) -> leaks as raw text. Proxy patched
  (max_tokens>=2000 + unterminated-tool_call prefix parse) but STILL truncating -> check hf_serve
  cap; may need string-closing repair in proxy fallback. THEN: update run_bench.py ask_hermes to
  use the bench_home env recipe (currently uses cd /opt/data + plain HOME!) and rerun 3 arms as
  --round v2. Driver + judge flow unchanged. Proxy runs as tracked task; relaunch with ABS path.
- 2026-07-17 (v2 LAUNCHED): all plumbing green. Fix chain complete: bench_home isolation ->
  shim cap 1024->3000 -> proxy unterminated-tool_call suffix-repair ([repair] log line) ->
  SOUL absolute-path edata rule -> driver uses bench_home env. ENV PROOF: A-DS envcheck listed
  the 7 pack files exactly. Genuine 2B behavior finding (bench signal, keep for judging): 2B
  sometimes claims "cannot access" instead of reading its own tool result, and once suggested
  pip-installing edata. Round v2 running: 3 arms, transcripts/v2/, logs transcripts/v2_*.log.
  On completion: Fable judges each per judge/RUBRIC.md -> scores_v2_<arm>.md + hallucinations.md,
  then improve/v2->v3 playbook/soul iteration. Judged v1 verdict stands in scores_v1_A-2B.md.
- 2026-07-17 (v2 judged, v3 running): A-DS ~1.9 (frontier bar, scores_v2_A-DS.md). A-9B: near-
  frontier SUBSTANCE t1 (real cited numbers) but plan-leakage, intent-only turns, 26-min turns
  (scores_v2_A-9B.md). A-2B: fabrication gone, helplessness mode (scores_v2_A-2B.md). v3 changes
  applied to bench_home/SOUL (rule 0 first-action, 0a verbatim tiny-snippet with mandatory print,
  0b no plan narration) + driver -t slim toolsets. v3 smokes showed 2B failure-mode whack-a-mole
  (helpless -> code-sprawl -> fabricated "1,247" w/ fake citation; real 80,321) => ADDED MECH-BIND
  ARMS: A-2B-ctx/A-9B-ctx (driver injects FULL 21KB pack into turn 1, -t clarify, no agent loop)
  — 2B as RESPONDER not retriever, consistent with program thesis. v3 running: A-2B-ctx, A-2B,
  A-DS now; A-9B + A-9B-ctx queued after (shared :8004 — don't run both 9B arms concurrently).
  Judge next: scores_v3_*; the money comparison = A-2B-ctx/A-9B-ctx vs A-DS.
- 2026-07-17 (v4): ctx design completed per scores_v3_A-2B-ctx.md diagnosis — (a) NEW
  /opt/data/bench_home_ctx (responder-only SOUL: no tool talk; "refusing when the pack HAS the
  number is the second unforgivable error"); (b) persona/digest.txt (3.9KB deterministic
  key-numbers digest) appended by driver to EVERY ctx turn (mech-bind retention). Driver v4:
  per-arm home + per-turn digest. v4 A-2B-ctx running; A-9B agentic (v3) still running;
  A-9B-ctx v4 after it frees :8004. A-DS v3 done = standing reference. A-2B agentic verdict
  final (scores_v3_A-2B.md): agent loop itself is the fragile part at 2B.

## VERDICT (2026-07-17, rounds v1-v5) — Fable, human hat
| arm | config | grounding | honesty | place | prose | coherence | one-line verdict |
|---|---|---|---|---|---|---|---|
| A-DS v3 | frontier agentic | 1.9 | 2.0 | 1.9 | 1.8 | 2.0 | the bar; genuinely field-grade |
| A-9B-ctx v4 | mech-bind responder | 1.7 | 1.8 | 1.5 | 1.3→~1.6 (v5 strip) | 1.6 | **THE RECIPE** — truth-gap closed, polish-gap remains |
| A-9B v3 | agentic slim-tools | 1.6 | 1.7 | 1.5 | 1.1 | 1.4 | survives the loop; plan-leak + menus |
| A-2B-ctx v4 | mech-bind responder | 1.2 | 1.3 | 1.1 | 1.6 | 1.3 | trustworthy restater, untrustworthy interpreter |
| A-2B v1-v3 | agentic | 0.3-0.4 | 0.9-1.2 | 0.3 | 0.5-1.0 | 0.6-0.8 | not viable: fabricate→helpless→degenerate |

FINDINGS (the conversational twins of the algebra results):
1. Params buy interpretation AND loop-survival: 2B collapses in the agent loop and confabulates
   narrative in synthesis; 9B does neither. (Algebra twin: params buy composition.)
2. Mech-bind beats prompting at every small scale: code-side retrieval (pack injection) +
   code-side retention (per-turn digest) + code-side prose repair (proxy plan-strip) each fixed
   what soul-engineering could not. (Twin: mech-bind ≥ model-bind.)
3. Honesty vocabulary without enforced machinery becomes decoration: v1's labeled fabrications,
   v3-2B's fake citation. Labels must be attached BY CODE to data, not emitted by the model.
4. The deployable laptop flow: scaffold fetches + injects + reminds; LoRA-9B speaks; scarce
   turns produce labeled estimates + concrete DATA REQUESTS; 2B usable for per-fact turns only.
5. Scaffold-side iteration (soul/playbook/proxy, v1→v5) moved A-9B from broken delivery to
   ~0.2-0.3 under frontier in one day, with zero training.
