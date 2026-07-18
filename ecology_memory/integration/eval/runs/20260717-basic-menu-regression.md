# Basic EBTL menu regression

The opening menu is now an executable contract rather than presentation text.

| Choice | Real typed-Qwen artifact | Result |
|---|---|---|
| Wildlife | `20260717-092145-basic_wildlife_choice.json` | Local four-group faunal survey; detected/older/population boundaries preserved |
| Vegetation | `20260717-092253-basic_vegetation_choice.json` | WorldCover point, analysis bbox and property boundary separated |
| Fire | `20260717-092344-basic_fire_choice.json` | Exact-origin MODIS calls; 2020–2025 history explicitly not forecast |
| Restoration | `20260717-092251-basic_restoration_choice.json` | 250 m NDVI proxy; whole-property and causal claims refused |

The regression bank is `integration/eval/basic_clarification_cases.json`. All four use real Hermes
resumed sessions. A subsequent current-code rerun of all 12 showcase cases produced zero failed
turns and answers identical to the frozen scored epoch.

## Wildlife head-to-head

| Arm | Artifact | Total latency | Critical result |
|---|---|---:|---|
| Typed Qwen 2B | `20260717-092145-basic_wildlife_choice.json` | 24.859 s | None; local survey and evidence boundaries retained |
| Origin DeepSeek-v4 | `20260717-093126-basic_wildlife_choice.json` | 241.713 s | 1,658-key failure, unsupported 271-record breakdown, AOI/property conflation |

Origin's last turn correctly distinguishes occurrence uploads from population, but its earlier
site-specific record counts and species claims are unsupported. Typed is 9.72× faster on this case.
