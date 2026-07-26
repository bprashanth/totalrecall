export const MAX_PAPER_BYTES = 25 * 1024 * 1024;

export type PaperMetadata = {
  doi: string;
  title: string;
  authors: string[];
  journal?: string;
  year?: number;
  url: string;
  abstract?: string;
  license?: string;
  metadata_source: "Crossref";
};

export type LinkedDataset = {
  doi: string;
  title: string;
  repository?: string;
  year?: number;
  url: string;
  size?: string;
  license?: string;
  relationship: "mentioned-in-paper" | "registered-related-dataset";
  metadata_source: "paper-text" | "DataCite";
};

const DOI_PATTERN = /10\.\d{4,9}\/[-._;()/:a-z0-9]+/gi;
const DATASET_DOI = /^(10\.5061\/dryad\.|10\.5281\/zenodo\.|10\.15468\/)/i;

const text = (value: unknown) => String(value ?? "").replace(/\s+/g, " ").trim();

export function stripMarkup(value: unknown): string {
  return text(
    String(value ?? "")
      .replace(/<[^>]+>/g, " ")
      .replace(/&nbsp;|&#160;/gi, " ")
      .replace(/&amp;/gi, "&")
      .replace(/&lt;/gi, "<")
      .replace(/&gt;/gi, ">")
      .replace(/&quot;/gi, '"')
      .replace(/&#39;|&apos;/gi, "'"),
  );
}

export function extractDois(value: string): string[] {
  const decoded = (() => {
    try {
      return decodeURIComponent(value);
    } catch {
      return value;
    }
  })();
  const found = decoded.match(DOI_PATTERN) || [];
  return [...new Set(found.map((doi) => doi.replace(/[.,;:\])}]+$/g, "").toLowerCase()))];
}

export function normaliseDoi(value: string): string | null {
  return extractDois(value)[0] || null;
}

export function looksLikeDatasetDoi(doi: string): boolean {
  return DATASET_DOI.test(doi);
}

async function fetchJson(url: string, fetcher: typeof fetch): Promise<unknown> {
  const response = await fetcher(url, {
    headers: {
      Accept: "application/json",
      "User-Agent": "Fieldnote/0.1 (paper and dataset metadata lookup)",
    },
    signal: AbortSignal.timeout(12_000),
  });
  if (!response.ok) {
    throw new Error(`Metadata service returned ${response.status}.`);
  }
  return response.json();
}

export async function lookupPaper(
  reference: string,
  fetcher: typeof fetch = fetch,
): Promise<PaperMetadata> {
  const doi = normaliseDoi(reference);
  if (!doi || looksLikeDatasetDoi(doi)) {
    throw new Error("Enter an article DOI or a DOI URL.");
  }
  const payload = (await fetchJson(
    `https://api.crossref.org/works/${encodeURIComponent(doi)}`,
    fetcher,
  )) as {
    message?: Record<string, unknown>;
  };
  const record = payload.message || {};
  const title = text((record.title as unknown[])?.[0]);
  if (!title) throw new Error("Crossref did not return a title for that DOI.");
  const authors = Array.isArray(record.author)
    ? record.author.slice(0, 20).map((author) => {
        const item = author as Record<string, unknown>;
        return text(`${item.given || ""} ${item.family || ""}`);
      }).filter(Boolean)
    : [];
  const dateParts = (
    (record.published as { "date-parts"?: number[][] } | undefined)?.["date-parts"] || []
  )[0];
  const licences = Array.isArray(record.license)
    ? record.license as Array<Record<string, unknown>>
    : [];
  return {
    doi,
    title,
    authors,
    journal: text((record["container-title"] as unknown[])?.[0]) || undefined,
    year: Number(dateParts?.[0]) || undefined,
    url: text(record.URL) || `https://doi.org/${doi}`,
    abstract: stripMarkup(record.abstract) || undefined,
    license: text(licences[0]?.URL) || undefined,
    metadata_source: "Crossref",
  };
}

function datasetFromDataCite(item: Record<string, unknown>): LinkedDataset | null {
  const attributes = (item.attributes || {}) as Record<string, unknown>;
  const doi = normaliseDoi(text(attributes.doi || item.id));
  if (!doi) return null;
  const types = (attributes.types || {}) as Record<string, unknown>;
  if (text(types.resourceTypeGeneral).toLowerCase() !== "dataset") return null;
  const titles = Array.isArray(attributes.titles)
    ? attributes.titles as Array<Record<string, unknown>>
    : [];
  const rights = Array.isArray(attributes.rightsList)
    ? attributes.rightsList as Array<Record<string, unknown>>
    : [];
  const sizes = Array.isArray(attributes.sizes) ? attributes.sizes : [];
  return {
    doi,
    title: text(titles[0]?.title) || `Dataset ${doi}`,
    repository: text(attributes.publisher) || undefined,
    year: Number(attributes.publicationYear) || undefined,
    url: `https://doi.org/${doi}`,
    size: text(sizes[0]) || undefined,
    license: text(rights[0]?.rightsIdentifier || rights[0]?.rightsUri) || undefined,
    relationship: "registered-related-dataset",
    metadata_source: "DataCite",
  };
}

async function lookupDataset(
  doi: string,
  fetcher: typeof fetch,
): Promise<LinkedDataset | null> {
  try {
    const payload = (await fetchJson(
      `https://api.datacite.org/dois/${encodeURIComponent(doi)}`,
      fetcher,
    )) as { data?: Record<string, unknown> };
    const dataset = payload.data ? datasetFromDataCite(payload.data) : null;
    return dataset ? { ...dataset, relationship: "mentioned-in-paper" } : null;
  } catch {
    return {
      doi,
      title: `Dataset ${doi}`,
      url: `https://doi.org/${doi}`,
      relationship: "mentioned-in-paper",
      metadata_source: "paper-text",
    };
  }
}

export async function discoverLinkedDatasets(
  paperDoi: string | null,
  doisInPaper: string[] = [],
  fetcher: typeof fetch = fetch,
): Promise<LinkedDataset[]> {
  const datasets = new Map<string, LinkedDataset>();
  for (const doi of doisInPaper.filter(looksLikeDatasetDoi).slice(0, 8)) {
    const found = await lookupDataset(doi, fetcher);
    if (found) datasets.set(found.doi, found);
  }
  if (paperDoi) {
    const parameters = new URLSearchParams({
      query: `relatedIdentifiers.relatedIdentifier:"${paperDoi}"`,
      "page[size]": "20",
    });
    try {
      const payload = (await fetchJson(
        `https://api.datacite.org/dois?${parameters.toString()}`,
        fetcher,
      )) as { data?: Array<Record<string, unknown>> };
      for (const item of payload.data || []) {
        const attributes = (item.attributes || {}) as Record<string, unknown>;
        const related = Array.isArray(attributes.relatedIdentifiers)
          ? attributes.relatedIdentifiers as Array<Record<string, unknown>>
          : [];
        const exact = related.some(
          (relation) => normaliseDoi(text(relation.relatedIdentifier)) === paperDoi,
        );
        const dataset = exact ? datasetFromDataCite(item) : null;
        if (dataset) datasets.set(dataset.doi, dataset);
      }
    } catch {
      // A paper can still be read when DataCite is unavailable.
    }
  }
  return [...datasets.values()];
}

export function paperMetadataText(paper: PaperMetadata): string {
  return [
    paper.title,
    paper.authors.join(", "),
    paper.journal,
    paper.year,
    paper.abstract,
  ].filter(Boolean).join("\n\n");
}
