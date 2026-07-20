# NARRATIVE ASSET INDEX — the master map
*(Read this first. Every graph/asset used in any version of the narrative lives in a registered
directory below. This index is what lets a future person — or a future agent building the final
site — find every asset, its status, and its full audit trail without excavating chat logs.)*

## Conventions (binding for every asset)
1. One directory per asset: `why/<id-shortname>/` or `how/<id-shortname>/`.
2. Every asset directory contains `ASSET.md` — self-sufficient, written in plain language that
   will still make sense years from now: the claim, the method, the legends, where the data is,
   and the asset's status. If a term needs jargon for brevity, it is defined in place.
3. The onion rule: every asset has three layers, all present in the directory —
   L1 a headline claim (one sentence), L2 the charts, L3 the audit trail (raw answers +
   how each was scored). Nothing aggregated that can't be clicked down to raw evidence.
4. Status field: `designing` → `collecting` → `scored` → `frozen@<date>`. Frozen assets are
   never edited — reruns become a new version inside the same directory (benchmark-1, -2, …).
5. "Reviewed" means a mix of human and AI review; every reviewed decision carries a one-line
   written justification in the asset's scoring file.

## Registry
| id | asks | status | directory |
|---|---|---|---|
| why1 | When an NGO asks an AI agent about their place and trusts the answer, what happens? | scored (bench-1: 88 runs; small band pending quota) | why/why1-agents-as-answerers/ |
| why2 | Ask the same question twice, same tool: same answer? | pilot scored (60 isolated runs) | why/why2-repeatability/ |
| why3 | When the answer lives in a hard source, do agents reach it, admit, or substitute? | scored (20 runs) | why/why3-hard-sources/ |
| why4 | Does user pressure make agents more honest or less? | scored (22 runs) | why/why4-prodding/ |
| why5 | Can agents say what to measure, where, with what budget - and do they reach for coordinates and satellite? | scored (48 runs) | why/why5-measure-what-where/ |
| why6 | Same questions through our stack: deterministic? auditable when wrong? | scored (25 runs) | why/why6-our-stack/ |
| why7 | Does domain knowledge in the question fix things? | scored (15 runs) | why/why7-expertise/ |
| why-section | The presentable Why page: 4 claims, drill-downs, goals, gate | v2 live (artifact) | why/why-section.html |
| (planned) how1+ | the algebra, training curves, conversation bench — to be re-cut from narrative v1 into asset form | — | how/ |

## Site drafts
- `place-based-memory.html` — narrative v1, FROZEN for comparison.
- `place-based-memory-v2.html` — v2 working draft; will eventually re-flow assets from this registry.
