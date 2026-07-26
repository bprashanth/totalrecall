import { mkdir, writeFile } from "node:fs/promises";
import path from "node:path";
import { NextResponse } from "next/server";
import {
  normaliseDoi,
  type LinkedDataset,
  type PaperMetadata,
} from "@/lib/papers";

export const runtime = "nodejs";

const clean = (value: unknown, limit = 500) =>
  String(value ?? "").replace(/\s+/g, " ").trim().slice(0, limit);

async function digest(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(JSON.stringify(value));
  const hashed = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hashed)]
    .map((item) => item.toString(16).padStart(2, "0"))
    .join("");
}

export async function POST(request: Request) {
  let body: {
    paper?: Partial<PaperMetadata>;
    dataset?: Partial<LinkedDataset>;
    session_id?: string;
  };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "A paper and dataset candidate are required." }, { status: 400 });
  }
  const datasetDoi = normaliseDoi(clean(body.dataset?.doi));
  const paperDoi = normaliseDoi(clean(body.paper?.doi));
  if (!datasetDoi) {
    return NextResponse.json({ error: "The dataset candidate needs a DOI." }, { status: 400 });
  }
  const candidate = {
    schema_version: "paper-source-candidate/1",
    state: "pending_profile_review",
    site_id: "valparai",
    created_at: new Date().toISOString(),
    session_id: clean(body.session_id, 120) || null,
    paper: {
      doi: paperDoi,
      title: clean(body.paper?.title),
      url: clean(body.paper?.url, 1_000),
      metadata_source: clean(body.paper?.metadata_source),
    },
    dataset: {
      doi: datasetDoi,
      title: clean(body.dataset?.title),
      repository: clean(body.dataset?.repository),
      url: clean(body.dataset?.url, 1_000) || `https://doi.org/${datasetDoi}`,
      size: clean(body.dataset?.size),
      license: clean(body.dataset?.license),
      relationship: clean(body.dataset?.relationship),
      metadata_source: clean(body.dataset?.metadata_source),
    },
    requested_next_steps: [
      "acquire immutable repository version and manifest",
      "profile files, tables, codebooks, units and identifiers",
      "propose canonical mappings and source-specific adapters",
      "review rights, mappings and failed rows before admission",
      "rebuild the site index and run capability probes after approval",
    ],
    note: "This is an intake request, not an admitted source and not evidence about the site.",
  };
  const requestId = `paper-${(await digest(candidate)).slice(0, 20)}`;
  const intakeRoot = process.env.PAPER_INTAKE_DIR;
  let persisted = false;
  if (intakeRoot) {
    try {
      await mkdir(intakeRoot, { recursive: true });
      await writeFile(
        path.join(intakeRoot, `${requestId}.json`),
        `${JSON.stringify({ request_id: requestId, ...candidate }, null, 2)}\n`,
        { encoding: "utf-8", flag: "wx" },
      ).catch((reason: NodeJS.ErrnoException) => {
        if (reason.code !== "EEXIST") throw reason;
      });
      persisted = true;
    } catch {
      persisted = false;
    }
  }
  return NextResponse.json({
    request_id: requestId,
    state: candidate.state,
    persisted,
    message: persisted
      ? "Queued for profiling and source review. The shared site data has not changed."
      : "Candidate prepared, but this deployment has no persistent intake queue. The shared site data has not changed.",
    candidate,
  });
}
