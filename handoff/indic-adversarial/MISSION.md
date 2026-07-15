# MISSION: adversarial second-author Indic question bank

You are GPT 5.6 acting as an INDEPENDENT question author. A prior (same-author) eval concluded that
Indian-dialect phrasing costs current models almost nothing on this framework. Your bank exists to
TEST that conclusion: author questions in genuine Indian urban/semi-urban English that MAXIMALLY
DIFFERENTIATE the models. If they hold ~0.9 on your bank, the conclusion stands; if they crater,
you found what our factory missed. Do not look at reference-bank-DO-NOT-COPY-STYLE.json except to
avoid duplicating its phrasings.

GOAL: an execution-verified bank of 80–100 questions at handoff/indic-adversarial/bank.json, EXACT
schema of harness/questions/seed.json rows ({id, sector, type, q, gold_ir, gold_shape, expect,
must_hole?, gold_shapes?}). Every gold must validate (harness/ir_schema.py) AND execute
(harness/executor.py) to its expected class. Spec = harness/../algebra semantics as implemented;
spec is FROZEN — inexpressible question ideas go to handoff/indic-adversarial/proposals.md.

RESOURCES (all local, no keys needed): the self-contained harness/ copy here (connectors: OSM
Overpass, World Bank, IChangeMyCity Bengaluru complaints incl. Indian entity aliases); an MT
round-trip service for genuine translationese at http://172.17.0.1:8005 (en<->hi/kn/ta/te/mr);
OpenRouter key at ~/.config/idlisseus/openrouter.json if you want cheap generator models.

AUTHENTICITY HINT (from the human): Indian Reddit threads, civic forums, WhatsApp-style public
discussions, parliamentary questions and NGO reports show how people NATURALLY FRAME questions —
use them for phrasing patterns, not for facts. Recommended flow: real public question language →
extract phrasing patterns → map selected examples MANUALLY to algebra → use as authentic anchors →
generate controlled variations around them. Respect site licensing; patterns not verbatim dumps.

ECONOMY: you are on a metered quota. Use CHEAPER models/sub-agents for grind (generation drafts,
paraphrase volume, containment checks); reserve your own reasoning for anchor mapping, gold
authoring, admission judgment. Prefer executing harness code over reasoning about it.

CHECKPOINT/RESUME (mandatory): append progress to PROGRESS.md and rewrite bank.json after EVERY 10
admitted questions, so a quota stall loses nothing — if you die and are re-run with this MISSION,
first read PROGRESS.md and bank.json and CONTINUE, never restart. When finished write DONE (one
line: counts + stop reason). A watcher polls for DONE and auto-runs the model baseline.

TERMINATION (hard): stop at 100 admitted questions, OR 20 consecutive admission failures, OR when
PROGRESS.md shows 3 checkpoint rounds with <5 admissions each. Then write DONE. Do not fix the
harness, do not train anything, do not touch files outside handoff/indic-adversarial/.

HARD RULES: never start/stop/restart docker containers or model servers (the harness talks to
:8001/:8005 which are up); be polite to public APIs; totalrecall git — commit ONLY files under
handoff/indic-adversarial/.
