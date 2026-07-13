# Working rules (auto-read by coding agents)

Mission and full instructions: **PROMPT.md in this directory — read it first, top to bottom.**
Stopping and saturation contract: **SATURATION.md — read it before declaring completion.**

Hard rules:
1. The parser under test is the LOCAL 2B (`qwen2b` via `harness/llm.py`), never yourself. You are
   the engineer + judge; judging decisions go to FINDINGS.md with reasoning.
2. The IR spec (`algebra/ir-spec.md`, v2) is FROZEN. Inexpressible questions → evidence-backed
   entry in `spec-proposals.md` (that's a discovery, not a failure). Do not add ops, fields, or
   vocab; do not change hole/evidence/empty-result semantics.
3. Never fabricate data. Unmappable entity → DataRequest. Empty leaf SELECT → DataRequest. Empty
   RELATE/COMPARE over non-empty inputs → a legitimate "none" answer.
4. Do not change trace/summary/corpus schemas (comparability contract).
5. Golden regression discipline: after any fix, re-run ALL previous banks before proceeding.
6. Every experiment ends with a `chronology/YYYYMMDD_name.md` narrative (why + what we found).
7. Parser few-shots ≤ 15 total; entity swaps allowed, tree-shape curriculum preserved.
8. Be polite to public APIs (the disk cache in `harness/cache/` is your friend; don't hammer
   Overpass/Nominatim).
9. **NEVER start, stop, or restart any model server or docker container.** The 2B at
   `172.17.0.1:8001` is SHARED INFRASTRUCTURE — other sector runs and experiments use it
   concurrently (vLLM batches concurrent requests; parallelism is safe, restarts are not). If the
   endpoint is down or serves the wrong model name, STOP and report in FINDINGS.md; do not fix it
   yourself. Ports 8002+ are reserved for other experiments (specialist models, LoRA serving) —
   don't bind anything there either.
10. A perfect repaired bank is regression closure, not saturation. Follow SATURATION.md: freeze
    exact code and banks, then require three consecutive untouched post-freeze holdouts. Any
    holdout-driven fix invalidates the epoch.
