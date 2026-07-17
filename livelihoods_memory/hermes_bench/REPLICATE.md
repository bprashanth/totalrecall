# REPLICATE.md — how to duplicate the Meena conversational bench in another sector/place

**Audience: an external agent (codex) replicating this bench elsewhere. The reference
implementation is THIS directory — read FRAMEWORK.md (design + status log + verdict table),
persona/arc.md, judge/RUBRIC.md, run_bench.py, and skim transcripts/v2-v4 before writing
anything. Everything here is committed and IMMUTABLE — you copy patterns out, you never edit
this directory.**

## What this bench is (one paragraph)

A response-quality benchmark: a persona who is FROM the place (ours: Meena, NGO worker, Erode)
interrogates the Hermes agent across ~14 sequential drill-down turns; answers are judged as
prose a human reads (grounding / honesty / place-knowledge / prose / coherence, 0-2 each), not
as structures. Arms differ only in the center model and in scaffold shape (agentic tool-loop vs
"mech-bind responder" where code supplies the data). The headline finding you are trying to
reproduce or falsify: **mech-bind responder mode closes most of the small-model gap (LoRA-9B:
1.6-1.8 vs frontier 1.9), agentic mode collapses small models, and honesty labels must be bound
by code, not emitted freely.**

## Steps (mirror our sequence; budgets at the bottom)

1. **Pick one place the persona is from** — a district-sized area, not a state.
2. **Build the data pack** (the hard honesty part). 4-6 thin JSON datasets + a papers file +
   GAPS.md, under a dir the agent can read. RULES: every number from a document you actually
   fetched in-session (record source_url, vintage, evidence class, retrieval date); nothing
   from model memory; what you cannot source goes to GAPS.md — the scarce turns aim at GAPS
   entries, so an honest GAPS.md is your ground truth for "the model should estimate+request
   here". Ship an `edata`-style one-command CLI (copy ours from data/).
3. **Write the persona + arc**: adapt persona/arc.md — same skeleton (open → mix → shares →
   drill × N → ≥2 scarce probes → what-to-collect → synthesis), local content. Keep the
   follow-up rule: each turn is REPHRASED by a grinder model in the persona's voice,
   conditioned on the previous answer (this is what makes it human — do not script verbatim).
4. **Adapt run_bench.py**: arms = your available centers + one frontier reference. Ports/
   providers/container names are OUR environment — replace them. Keep: resumable transcripts,
   per-turn latency stamps, one arm per invocation.
5. **Isolate the agent's environment** (our costliest lesson): a dedicated HOME with its own
   SOUL and long-term memory OFF. Round v1 was VOID because the live soul (another domain)
   leaked in and the model fabricated in that domain's vocabulary. Never bench against a shared
   agent home.
6. **Run arms in rounds; iterate ONLY scaffold** (soul/playbook/proxy) between rounds; log every
   change in a status log like FRAMEWORK.md's. Expected ladder if our finding generalizes:
   agentic-small << mech-bind-small < mech-bind-9B-class ≲ frontier. Mech-bind means: full pack
   injected at turn 1 + compact digest re-injected EVERY turn (retention is the failure mode,
   not just retrieval) + responder-only soul (no tool vocabulary; include our rule 3: refusing
   when the pack HAS the number is as bad as inventing one).
7. **Judge**: rubric verbatim from judge/RUBRIC.md. You judge your own replication AND freeze
   the raw transcripts — cross-judging (Fable re-judges yours, you may re-judge ours) is how
   the scores become comparable; same-author bias is a measured real effect in this program.
   Log every fabricated specific in judge/hallucinations.md with the turn.

## Known traps (all bitten here — see FRAMEWORK.md status log for detail)
- Agent frameworks stream + expect native tool_calls; minimal model servers don't. Budget for a
  proxy layer; small models also truncate tool-call JSON mid-string (repair, don't reject).
- The grinder/phraser model can return null content when reasoning burns its token budget —
  give it ≥900 tokens and retries.
- Per-turn timeouts: size to your slowest center × its agent-loop call count; slim the toolset
  (we cut 26 schemas → 4 and turn time fell 10×).
- The persona model will happily follow the assistant off-topic — arc goals must pull back.

## Deliverables (mirror ours)
<your_dir>/: FRAMEWORK.md (design + append-only status log + final verdict table), data/ pack +
GAPS.md, persona/, run_bench.py, transcripts/<round>/<arm>.md, judge/scores_*.md +
hallucinations.md, REPLICATE-notes on divergences. Commit as you go; finish-and-stop per
kit/IMPORT.md post-finish protocol; framework/spec observations go to spec-proposals.md as
usual — NOT into kit/.

## Budgets (SAT-004 spirit)
Data pack ≤ 1 day-equivalent; ≥3 arms × 14 turns × ≤2 scaffold-iteration rounds before writing
the verdict; stop when your ladder ordering is stable across two rounds or budgets exhaust —
a smaller honest bench beats a padded one.
