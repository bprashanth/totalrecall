# v3 A-9B agentic — the 9B SURVIVES the agent loop. Means: grounding 1.6, honesty 1.7,
place 1.5, prose 1.1, coherence 1.4. 14/14 turns, ZERO timeouts (slim toolsets cut turn
latency from 26min to ~2.5min — the 26-schema prompt was most of the 9B's v2 latency).
Real dataset pulls, correct numbers with sources, honest scarce-turn behavior (names exactly
what survey would close the gap). Two prose defects: plan-narration leaks before answers
(soul rule 0b did NOT stop it — ingrained habit; fix mechanically in proxy = v5 candidate,
strip leading plan-speak paragraphs), and option-menus instead of one follow-through.
KEY CONTRAST: same scaffold collapses the 2B (degeneration/fabrication) but the 9B runs it
fine — parameters buy agent-loop survival, not just composition.
