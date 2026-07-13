# Tick 004 — neutral unseen bank

## Admission

Seventeen of eighteen neutrally generated livelihoods questions passed frontier gold validation.
Before parsing them, manual review caught the OSM 200-row ceiling masquerading as complete data.
The connector now probes beyond a 500-row cap and returns a DataRequest on truncation. Re-execution
changed several supposed totals and proved the guard necessary.

## First contact

The local 2B scored 1.000 on all 17 unseen parses. Manual synthesis review then caught a ranking
whose values were copied correctly but whose order and “highest” claim contradicted execution.
Mechanical synthesis scoring had called it perfect. Ranking prose now must preserve executor order;
otherwise a deterministic rendering replaces it. This tick reinforces the project rule that green
structure is necessary but not sufficient—source completeness and answer surfaces both need guards.
