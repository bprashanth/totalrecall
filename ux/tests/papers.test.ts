import { describe, expect, it } from "vitest";
import {
  discoverLinkedDatasets,
  extractDois,
  lookupPaper,
  normaliseDoi,
} from "../lib/papers";

describe("paper metadata", () => {
  it("normalises DOI URLs and trims citation punctuation", () => {
    expect(normaliseDoi("https://doi.org/10.1002/ecs2.2860.")).toBe("10.1002/ecs2.2860");
    expect(
      extractDois("Article 10.1002/ecs2.2860; data: 10.5061/dryad.g7j45sn."),
    ).toEqual(["10.1002/ecs2.2860", "10.5061/dryad.g7j45sn"]);
  });

  it("turns a Crossref work into bounded paper metadata", async () => {
    const fetcher = async () =>
      new Response(
        JSON.stringify({
          message: {
            title: ["Recovery of tropical forest after assisted natural regeneration"],
            author: [{ given: "A", family: "Researcher" }],
            published: { "date-parts": [[2019, 8, 1]] },
            "container-title": ["Ecosphere"],
            URL: "https://doi.org/10.1002/ecs2.2860",
            abstract: "<jats:p>A field comparison.</jats:p>",
          },
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );

    const paper = await lookupPaper("10.1002/ecs2.2860", fetcher as typeof fetch);
    expect(paper.title).toMatch(/Recovery/);
    expect(paper.authors).toEqual(["A Researcher"]);
    expect(paper.year).toBe(2019);
    expect(paper.abstract).toBe("A field comparison.");
  });
});

describe("linked dataset discovery", () => {
  it("requires an exact related DOI and keeps the dataset outside admission", async () => {
    const seen: string[] = [];
    const fetcher = async (input: RequestInfo | URL) => {
      seen.push(String(input));
      return new Response(
        JSON.stringify({
          data: [
            {
              id: "10.5061/dryad.g7j45sn",
              attributes: {
                doi: "10.5061/dryad.g7j45sn",
                types: { resourceTypeGeneral: "Dataset" },
                titles: [{ title: "Data from a forest recovery study" }],
                publisher: "Dryad",
                publicationYear: 2019,
                sizes: ["120578 bytes"],
                rightsList: [{ rightsIdentifier: "CC0-1.0" }],
                relatedIdentifiers: [
                  {
                    relationType: "IsSupplementTo",
                    relatedIdentifier: "10.1002/ecs2.2860",
                  },
                ],
              },
            },
            {
              id: "10.5061/dryad.unrelated",
              attributes: {
                doi: "10.5061/dryad.unrelated",
                types: { resourceTypeGeneral: "Dataset" },
                titles: [{ title: "Unrelated data" }],
                relatedIdentifiers: [
                  {
                    relationType: "IsSupplementTo",
                    relatedIdentifier: "10.1002/other",
                  },
                ],
              },
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      );
    };

    const result = await discoverLinkedDatasets(
      "10.1002/ecs2.2860",
      [],
      fetcher as typeof fetch,
    );

    expect(seen[0]).toContain("api.datacite.org/dois?");
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      doi: "10.5061/dryad.g7j45sn",
      repository: "Dryad",
      relationship: "registered-related-dataset",
      metadata_source: "DataCite",
    });
  });
});
