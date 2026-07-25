import type { MethodReading } from "./types";

const includesAny = (text: string, values: string[]) =>
  values.some((value) => text.includes(value));

export function readMethod(text: string, filename = "paper"): MethodReading {
  const source = `${filename} ${text}`.toLowerCase();
  if (
    includesAny(source, [
      "assisted natural regeneration",
      "natural regeneration",
      "regeneration",
      "restoration",
      "anr",
    ])
  ) {
    return {
      method: "Restoration and natural regeneration",
      plain_summary:
        "The paper appears to judge recovery through young trees, forest structure and a comparison through time or against reference forest.",
      outcomes: [
        "Regenerating tree abundance and species richness",
        "Old-growth and animal-dispersed tree representation",
        "Canopy cover, basal area and adult-tree structure",
      ],
      available: [
        "132 source-linked restoration and reference plots",
        "Regeneration and adult-tree richness indicators",
        "Canopy cover, basal area, height and carbon measures",
        "2024 monthly greenness surfaces for landscape context",
      ],
      missing: [
        "Intervention start and management-history dates for every plot",
        "Repeat plot measurements on a common protocol",
        "A declared untreated or reference comparison matching the paper",
      ],
      cautions: [
        "Satellite greenness is context, not proof of tree recruitment.",
        "Differences among plot classes are descriptive until the study design supports a causal claim.",
      ],
      suggested_visual: "restoration",
    };
  }
  if (includesAny(source, ["acoustic", "soundscape", "bioacoustic", "birdsong"])) {
    return {
      method: "Soundscape and acoustic-space comparison",
      plain_summary:
        "The paper appears to compare the timing or frequency structure of sound across sites.",
      outcomes: ["Acoustic-space use", "Daily timing of sound", "Recorder-site differences"],
      available: [
        "43 recorder sites",
        "Hourly acoustic-space values across 128 frequency bins",
        "Source-reported restoration categories",
      ],
      missing: [
        "Raw WAV clips in the admitted snapshot",
        "A common species-level call classifier",
        "Recorder-specific effort and failure history",
      ],
      cautions: [
        "Occupied acoustic space is not the same as bird richness.",
        "Named species require identified calls or an admitted classifier.",
      ],
      suggested_visual: "acoustic",
    };
  }
  if (includesAny(source, ["phenology", "leaf flush", "flowering", "fruiting", "ndvi"])) {
    return {
      method: "Seasonal vegetation rhythm",
      plain_summary:
        "The paper appears to follow vegetation through seasons and relate peaks or lulls to field events.",
      outcomes: ["Seasonal peak", "Timing of change", "Field–satellite agreement"],
      available: [
        "Monthly Sentinel-2 greenness for 2024",
        "Daily weather measurements",
        "Cell-level coverage and missing-support flags",
      ],
      missing: [
        "Several years on one processing baseline",
        "Dated flowering, fruiting or leaf-flush observations",
        "July coverage and stronger cloudy-season support",
      ],
      cautions: [
        "One year is a seasonal profile, not a long-term trend.",
        "Greenness cannot identify flowering or recruitment without field observations.",
      ],
      suggested_visual: "seasonal",
    };
  }
  if (includesAny(source, ["occupancy", "detection probability", "camera trap", "presence absence"])) {
    return {
      method: "Detection-history or occupancy study",
      plain_summary:
        "The paper appears to separate whether a species used a place from whether the survey detected it.",
      outcomes: ["Site use or occupancy", "Detection probability", "Predictor relationships"],
      available: [
        "Source-linked occurrence records",
        "Some explicit survey effort and camera detections",
        "Environmental cell features",
      ],
      missing: [
        "Repeated sampling occasions on one consistent design",
        "Complete detector uptime or visit histories",
        "An agreed target species and spatial sampling unit",
      ],
      cautions: [
        "Opportunistic points cannot be silently turned into non-detections.",
        "An occupancy model must fail closed without repeated detection histories.",
      ],
      suggested_visual: "map",
    };
  }
  return {
    method: "Method to be translated",
    plain_summary:
      "I can see a study method, but its outcome and comparison need one short clarification before matching it to Valparai data.",
    outcomes: ["Primary response variable", "Sampling unit", "Comparison or counterfactual"],
    available: [
      "Source-linked records, measurements and survey effort",
      "Plot, recorder and spatial-cell locations",
      "Weather, vegetation and environmental context",
    ],
    missing: [
      "The paper's exact outcome definition",
      "Its minimum sampling design",
      "The intended Valparai question",
    ],
    cautions: ["A plausible visual is not yet a replication of the paper."],
    suggested_visual: "map",
  };
}
