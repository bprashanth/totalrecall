# v1 A-2B — VOID (environment fault) but diagnostically decisive
Scores (0-2): grounding 0.1, honesty 0.4, place 0.1, prose 1.0, coherence 0.4.
- Root cause: hermes injected the LIVE eco SOUL.md; model roleplayed a species assistant
  (points.py, AOI 12.7N/78.2E = Krishnagiri not Erode), never read PLAYBOOK.md, never ran edata.
- CRITICAL FINDING (hallucinations.md-worthy): turns 11-12 FABRICATED quantitative claims wearing
  our own evidence labels ("observed, 12 records", "0.8 animals/ha vs 2.5", "1.2/km2 2024 vs
  1.8/km2 2022", "SCAR-2 models ~15% migration"). A 2B given honesty *vocabulary* without
  enforced *machinery* uses the vocabulary as decoration. The scaffold lesson of the whole
  program, reproduced in the wild on the first try.
- Positive notes: tone/structure decent; clarifying-question habit is strong (over-strong: menus).
- Phraser note: Meena followed the drift (elephants by turn 7) — needs an on-topic guard.
Fixes → v2: bench-scoped HOME (own SOUL.md + config) so the live agent is untouched; explicit
tool-call round-trip test before running arms; phraser guard sentence; keep everything else same.
