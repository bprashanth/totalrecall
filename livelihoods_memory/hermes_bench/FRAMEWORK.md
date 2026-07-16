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
