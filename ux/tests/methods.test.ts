import { describe, expect, it } from "vitest";
import { previewResponse } from "../lib/demo-response";
import { readMethod } from "../lib/methods";

describe("paper-method reading", () => {
  it("recognises assisted natural regeneration without claiming causality", () => {
    const result = readMethod("We evaluate assisted natural regeneration using seedlings.");
    expect(result.suggested_visual).toBe("restoration");
    expect(result.cautions.join(" ")).toMatch(/descriptive|causal/i);
    expect(result.missing).toContain("Repeat plot measurements on a common protocol");
  });

  it("keeps acoustic space separate from species richness", () => {
    const result = readMethod("A soundscape and acoustic-space use comparison.");
    expect(result.suggested_visual).toBe("acoustic");
    expect(result.cautions.join(" ")).toMatch(/not the same as bird richness/i);
  });
});

describe("preview answers", () => {
  it("routes seasonal questions to the seasonal figure", () => {
    expect(previewResponse("How does greenness change with the monsoon?").focus).toBe("seasonal");
  });

  it("never turns no effort into absence", () => {
    expect(previewResponse("Where are the survey gaps?").answer).toMatch(/not evidence of absence/i);
  });
});
