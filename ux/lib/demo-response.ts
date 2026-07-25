import type { AnalysisResponse } from "./types";

export function previewResponse(question: string): AnalysisResponse {
  const q = question.toLowerCase();
  if (/lion.?tailed|macaque|species|record|where.*seen/.test(q)) {
    return {
      mode: "preview",
      focus: "records",
      results: [],
      answer:
        "Start with the record map, then read it beside survey effort. A bright cell means many source-linked records were made there; it does not, by itself, mean more animals lived there.",
      note: "Connect the local Valparai bridge to retrieve named-species points and their audit.",
    };
  }
  if (/green|ndvi|season|phenolog|monsoon|satellite/.test(q)) {
    return {
      mode: "preview",
      focus: "seasonal",
      results: [],
      answer:
        "The 2024 satellite sequence is greenest at the bookends of the year in the available cells. July is absent and October is thin, so this is a seasonal picture with cloudy-season gaps—not a trend.",
    };
  }
  if (/restor|regener|anr|natural regeneration|tree|canopy/.test(q)) {
    return {
      mode: "preview",
      focus: "restoration",
      results: [],
      answer:
        "The pack can begin with plot-level regeneration richness, old-growth species, basal area and canopy measures. To say whether assisted natural regeneration caused recovery, we would still need intervention dates, repeat visits and a defensible comparison.",
    };
  }
  if (/sound|acoustic|song|bird|chorus|frequency/.test(q)) {
    return {
      mode: "preview",
      focus: "acoustic",
      results: [],
      answer:
        "The soundscape figure shows when different frequency bands were occupied across recorder sites. It describes acoustic space use, not a species count. Pair it with identified calls before naming the singers.",
    };
  }
  if (/effort|survey|absence|gap|looked|sample/.test(q)) {
    return {
      mode: "preview",
      focus: "effort",
      results: [],
      answer:
        "Map where people looked before interpreting empty cells. Some quiet-looking parts of the landscape have little explicit survey effort; those are data gaps, not evidence of absence.",
    };
  }
  return {
    mode: "preview",
    focus: "site",
    results: [],
    answer:
      "Begin with the landscape: where observations gather, where effort is visible, and where the map falls quiet. From there we can follow a species, a season, a restoration question or a paper method.",
  };
}
