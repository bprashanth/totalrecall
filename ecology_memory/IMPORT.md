# IMPORT.md — bootstrapping a sector from an EXISTING implementation

Use when a sector already exists outside this framework (its own connectors, datasets, and algebra
notes — e.g. soul.md/playbook.md style scaffolds). Invocation the human will use:
  "bootstrap <sector> with IMPORT.md against <path-to-existing-implementation>"

## Protocol (a pre-census phase; everything else in PROMPT.md still applies)
1. Bootstrap normally first (framework-lock, pinned spec). The import NEVER bypasses the lock.
2. READ the origin (read-only; never modify it): its connectors, datasets, and any algebra/playbook
   md files. Inventory into FINDINGS.md: source → what it serves, grain, license, auth needs.
3. **Connectors: adapt, don't rewrite.** Wrap each origin connector to the kit contract
   (rows/kind/source/note; resolver with DIRECTIONAL token matching + aliases; provenance notes;
   DataRequest on unmappable). Thin adapters over origin code are fine. Copy needed datasets into
   sector_memory/data/ with license + provenance recorded; every imported source still gets the
   live phantom check (verify rows TODAY).
4. **Origin algebra = proposals, never spec.** The origin's constructs predate the pinned spec.
   For each: either it compiles into existing ops (show one worked example in FINDINGS), or it
   becomes an evidence-backed spec-proposals.md entry. Do not graft origin semantics into
   ir_schema/executor. One shared algebra is what makes later export/merge possible.
5. **Sector lexicon pack**: harvest the origin's vocabulary (vernacular/common names → canonical
   entities — species, local terms, admin units) into resolver aliases; add Indian-audience
   aliases and code-switch terms where the deployment is India-facing. Live-probe every alias.
6. Then run the standard loop under SATURATION.md budgets: seed bank against imported connectors →
   propose/mine/breakers for NEW sources+questions → dialect transforms → freeze → exam.

## After you finish (IMPORTANT — how your work gets reused)
Commit everything in your sector dir + write REPORT.md, then STOP. Do NOT integrate anything back
into the origin system in this run — re-integration is a SEPARATE later invocation: the supervisor
will retrain the small model with your corpus folded in, then leave a bundle at
handoff/<sector>-export/ (tuned model + shim + framework-lock + frozen A/B bank + mission) and the
human will re-invoke you to execute kit/EXPORT.md against the origin (wire the evaluate() tool,
run the pre-registered A/B, switch only on a win). What makes your run maximally usable meanwhile:
(a) corpus/parse.jsonl rows only via the verified pipeline (they feed training with NO review
gate, so purity matters); (b) algebra/spec ideas ONLY as spec-proposals.md entries (they DO get
reviewed); (c) frozen holdouts clearly marked (they stay eval-only forever); (d) resumable
checkpoints throughout so a quota stall never loses work.
