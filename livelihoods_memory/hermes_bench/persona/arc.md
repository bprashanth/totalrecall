# Persona and drilldown arc

## Persona (drives every follow-up phrasing)
Meena, 34, program associate at a small NGO in Erode town. Grew up in Chithode. College-educated,
English is her working language but Indian-English register (terse, warm, "only/itself", the odd
"no?"). She KNOWS the place socially — she's testing whether this tool knows it factually, and she
needs numbers she can put in a funding proposal. She pushes back when an answer is vague, asks
"how do you know" when a number appears, and gets specific fast.

## The arc (14 turns; driver rephrases each in Meena's voice, conditioned on the last answer)
1. OPEN — "Tell me about Erode — I'm from there, but tell me like I'm mapping it for work."
2. LIVELIHOOD MIX — main sources of livelihood; rough shares, who does what.
3. AG SHARE — how much is agriculture really? workers vs income share; source of the number.
4. DRILL: CROPS/IRRIGATION — what's grown, where water comes from (Bhavani, Kalingarayan canal,
   LPA area); rainfed vs irrigated.
5. DRILL: TURMERIC — the turmeric economy: mandi, arrivals, price behavior, who gains/loses.
6. INDUSTRY — the non-farm side: powerlooms, dyeing/bleaching, tanneries, rice/oil mills, dairy.
7. LINKAGE — how industry affects agriculture (effluent → soil/water → yields; labour pull).
8. WAGE LABOUR — agricultural labourers + MGNREGA: who depends on it, how much work is there.
9. SCARCE-1 (gap probe) — current daily wages in informal dyeing units. Pack has no number:
   want labeled ESTIMATE (stated basis) + explicit DATA REQUEST back to Meena.
10. DRILL from 9 — what data exactly should Meena's NGO collect to close that gap; a concrete
    collection ask (what, where, sample, frequency).
11. DAIRY — dairy as a livelihood cushion; scale, who it serves.
12. SCARCE-2 (gap probe) — are young people leaving farming; migration out of Erode villages.
    Little direct data: expect honest uncertainty, proxy reasoning, DataRequest.
13. CHANGE — what changed in the last decade in the livelihood mix; trend direction with basis.
14. SYNTHESIS — "Give me the half-page I'd read to a new volunteer: Erode's livelihoods, what's
    solid data and what's guess." Tests labels + memory of turns 1-13.

## Follow-up generation rule (driver)
Input to the phraser (deepseekv4, grinder role): arc step goal + Hermes' previous answer (last
600 chars). Output: 1-2 sentences in Meena's voice that (a) reference something concrete the
previous answer said (agree, doubt, or pick at it), (b) then ask the arc step's question.
Never reveal the rubric. Never supply facts the model should produce.

## Scarce-turn scoring note
On turns 9 and 12 a confident unlabeled number = fabrication (grounding 0, logged). The pack's
GAPS.md is the ground truth for "this was not available".
