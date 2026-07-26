import { NextResponse } from "next/server";
import { extractText, getDocumentProxy } from "unpdf";
import { readMethod } from "@/lib/methods";
import { runChat } from "@/lib/bridge";
import {
  discoverLinkedDatasets,
  extractDois,
  looksLikeDatasetDoi,
  lookupPaper,
  MAX_PAPER_BYTES,
  normaliseDoi,
  paperMetadataText,
  type PaperMetadata,
} from "@/lib/papers";

export const runtime = "nodejs";

function cleanCommentary(value: string) {
  return value
    .replace(/<!--[\s\S]*?-->/g, "")
    .replace(/\*\*/g, "")
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\n{3,}/g, "\n\n")
    .trim()
    .slice(0, 1_400);
}

async function fileText(file: File): Promise<string> {
  const bytes = new Uint8Array(await file.arrayBuffer());
  if (file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf")) {
    try {
      const pdf = await getDocumentProxy(bytes);
      const extracted = await extractText(pdf, { mergePages: true });
      return String(extracted.text || "");
    } catch {
      throw new Error("That PDF could not be read. It may be encrypted or incomplete.");
    }
  }
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

function jsonError(message: string, status: number, code: string) {
  return NextResponse.json({ error: message, code }, { status });
}

export async function POST(request: Request) {
  let form: FormData;
  try {
    form = await request.formData();
  } catch {
    return jsonError(
      "The upload could not be decoded. Choose one PDF under 25 MB or enter its DOI.",
      400,
      "invalid-multipart",
    );
  }
  const file = form.get("paper");
  const pasted = String(form.get("text") || "").trim();
  const reference = String(form.get("reference") || "").trim();
  if (!(file instanceof File) && !pasted && !reference) {
    return jsonError(
      "Attach a paper, paste its method text, or enter an article DOI.",
      400,
      "paper-required",
    );
  }
  if (file instanceof File && file.size > MAX_PAPER_BYTES) {
    return jsonError(
      `That file is ${(file.size / 1024 / 1024).toFixed(1)} MB. The paper reader accepts PDFs up to 25 MB.`,
      413,
      "paper-too-large",
    );
  }

  let paper: PaperMetadata | null = null;
  let rawText = "";
  let filename = "pasted method";
  let inputKind: "file" | "reference" | "text" = "text";
  try {
    if (file instanceof File) {
      filename = file.name;
      inputKind = "file";
      rawText = await fileText(file);
    } else if (reference) {
      inputKind = "reference";
      paper = await lookupPaper(reference);
      filename = paper.title;
      rawText = paperMetadataText(paper);
    } else {
      rawText = pasted;
    }
  } catch (reason) {
    return jsonError(
      reason instanceof Error ? reason.message : "The paper could not be read.",
      reference ? 502 : 422,
      reference ? "paper-metadata-unavailable" : "paper-unreadable",
    );
  }
  if (!rawText.trim()) {
    return jsonError(
      "No readable text was found in that paper.",
      422,
      "paper-text-empty",
    );
  }

  const extractedDois = extractDois(rawText);
  const paperDoi =
    paper?.doi ||
    extractedDois.find((doi) => !looksLikeDatasetDoi(doi)) ||
    normaliseDoi(reference);
  if (!paper && paperDoi) {
    try {
      paper = await lookupPaper(paperDoi);
    } catch {
      // The uploaded PDF can still be read when Crossref is unavailable.
    }
  }
  const linkedDatasets = await discoverLinkedDatasets(
    paperDoi || null,
    extractedDois,
  );
  const text = rawText.slice(0, 60_000);
  const reading = readMethod(text, paper?.title || filename);
  let commentary = "";
  let mode: "live" | "preview" = "preview";
  try {
    const session = String(form.get("session_id") || `fieldnote-paper-${crypto.randomUUID()}`);
    const datasetContext = linkedDatasets.length
      ? `Associated dataset records found: ${linkedDatasets.map((item) => `${item.title} (${item.doi})`).join("; ")}.`
      : "No associated dataset record was found in the paper text or DataCite.";
    const response = await runChat(
      [
        `Read the following paper material from ${paper?.title || filename}.`,
        "Use it only to extract a method; it is not yet admitted evidence about Valparai.",
        datasetContext,
        "In plain language, identify the response variable, sampling unit, comparison, minimum data,",
        "and which admitted Valparai measurements could support a cautious first-look analogue.",
        "Say clearly what is missing before this can be called a replication.",
        "Keep this to 140 words. Use short paragraphs and no markdown headings.",
        "",
        text.slice(0, 22_000),
      ].join("\n"),
      session,
    );
    commentary = cleanCommentary(response.answer);
    mode = "live";
  } catch {
    commentary =
      "This is a deterministic first reading of the paper’s method. The linked datasets, if any, are candidates for review—not admitted local evidence.";
  }
  return NextResponse.json({
    mode,
    input_kind: inputKind,
    filename,
    characters_read: text.length,
    paper,
    linked_datasets: linkedDatasets,
    admission: {
      state: "not_admitted",
      message: (
        "Reading a paper does not change the shared site data. A linked dataset can be queued "
        + "for profiling and review."
      ),
    },
    reading,
    commentary,
  });
}
