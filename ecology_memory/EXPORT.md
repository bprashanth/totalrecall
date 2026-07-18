# EXPORT.md — merging results back into an origin system (tips, applied situationally)

Goal: an origin system (e.g. an agent using a frontier API model + md-file algebra scaffold)
adopts what a sector run produced: a fine-tuned small model, new connectors, new datasets.

## Guidelines (not a rigid pipeline — adapt per system)
1. **Export the scaffold, not just the model.** Freeform tool-use hallucinates at every scale
   (measured: frontier ~30-35% freeform). The valuable export is compile→execute: expose ONE tool
   to the origin agent — evaluate(question) → {answer, provenance, evidence label, or a
   clarifying question / data request} — backed by: the tuned model (merged weights + serving
   shim; note vLLM may silently no-op LoRA on hybrid archs — sanity-diff adapter vs base before
   trusting), parser prompt (or minimal prompt if tuned), ir_schema+executor+repair passes, and
   the sector connectors. The origin keeps its personality/UX; data questions route through this.
2. **Connectors/datasets join by contract.** If import followed IMPORT.md, sector connectors and
   origin connectors share one contract — joining back is copying sector_memory/harness/
   connectors.py (+ data/) into the origin's connector dir. If the origin live-mounts connectors,
   no restart needed.
3. **A/B before switching.** Run the sector's FROZEN holdout bank through origin-as-is vs
   origin+exported-stack using the arms machinery (dual judges, executed ground truth,
   hallucination intervals). Pre-register the switch criteria (e.g. factuality up, hallucination
   interval strictly better, latency acceptable). Switch only on a win; keep the old path behind a
   flag for rollback.
4. **The model carries the algebra.** A tuned model + pinned executor IS the algebra version;
   record framework-lock alongside the deployed weights so the origin knows what dialect of trees
   its executor speaks. Origin md-scaffolds (soul/playbook) shrink to persona + routing; the
   compile rules live in weights+code now.
5. Bench sets for ongoing regression: the sector's frozen banks travel with the export.
