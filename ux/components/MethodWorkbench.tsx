"use client";

import { useRef, useState } from "react";
import {
  BookOpenText,
  Check,
  ChevronRight,
  Database,
  ExternalLink,
  FileText,
  FlaskConical,
  LoaderCircle,
  Upload,
  X,
} from "lucide-react";
import type { DemoData, MethodReading } from "@/lib/types";
import {
  MAX_PAPER_BYTES,
  type LinkedDataset,
  type PaperMetadata,
} from "@/lib/papers";

type PaperResponse = {
  mode: "live" | "preview";
  input_kind: "file" | "reference" | "text";
  filename: string;
  characters_read: number;
  paper: PaperMetadata | null;
  linked_datasets: LinkedDataset[];
  admission: {
    state: "not_admitted";
    message: string;
  };
  reading: MethodReading;
  commentary: string;
};

type StageResponse = {
  request_id: string;
  state: string;
  persisted: boolean;
  message: string;
};

async function responseJson(response: Response): Promise<Record<string, unknown>> {
  const contentType = response.headers.get("content-type") || "";
  const content = await response.text();
  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(content) as Record<string, unknown>;
    } catch {
      throw new Error(`The paper service returned invalid JSON (${response.status}).`);
    }
  }
  throw new Error(
    response.status === 413
      ? "That paper is larger than this reader accepts."
      : content.trim() || `The paper service returned ${response.status}.`,
  );
}

export function MethodWorkbench({
  data,
  sessionId,
  onFocus,
}: {
  data: DemoData;
  sessionId: string;
  onFocus: (focus: MethodReading["suggested_visual"]) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [paper, setPaper] = useState<PaperResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [reference, setReference] = useState("");
  const [staging, setStaging] = useState("");
  const [stageResult, setStageResult] = useState<StageResponse | null>(null);
  const [rPlot, setRPlot] = useState<{ mode: string; svg?: string; note?: string } | null>(null);

  async function submitPaper(form: FormData) {
    setBusy(true);
    setError("");
    setPaper(null);
    setStageResult(null);
    setRPlot(null);
    form.set("session_id", sessionId);
    try {
      const response = await fetch("/api/paper", { method: "POST", body: form });
      const body = await responseJson(response);
      if (!response.ok) throw new Error(String(body.error || "Could not read that paper."));
      setPaper(body as PaperResponse);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not read that paper.");
    } finally {
      setBusy(false);
    }
  }

  async function readPaper(file: File) {
    if (file.size > MAX_PAPER_BYTES) {
      setError(
        `That file is ${(file.size / 1024 / 1024).toFixed(1)} MB. Choose a PDF under 25 MB or enter its DOI.`,
      );
      return;
    }
    const form = new FormData();
    form.set("paper", file);
    await submitPaper(form);
  }

  async function readReference() {
    if (!reference.trim()) return;
    const form = new FormData();
    form.set("reference", reference.trim());
    await submitPaper(form);
  }

  async function stageDataset(dataset: LinkedDataset) {
    if (!paper) return;
    setStaging(dataset.doi);
    setStageResult(null);
    try {
      const response = await fetch("/api/paper/stage", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ paper: paper.paper, dataset, session_id: sessionId }),
      });
      const body = await responseJson(response);
      if (!response.ok) throw new Error(String(body.error || "Could not queue this dataset."));
      setStageResult(body as StageResponse);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not queue this dataset.");
    } finally {
      setStaging("");
    }
  }

  async function drawInR() {
    if (!paper) return;
    setBusy(true);
    onFocus(paper.reading.suggested_visual);
    const kind =
      paper.reading.suggested_visual === "map" ? "restoration" : paper.reading.suggested_visual;
    const plotData =
      kind === "seasonal"
        ? data.seasonal_ndvi
        : kind === "acoustic"
          ? data.acoustic
          : data.restoration.filter(
              (row) => row.metric === "regeneration_tree_species_richness",
            );
    try {
      const response = await fetch("/api/r-plot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, data: plotData }),
      });
      setRPlot(await response.json());
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="method-workbench" id="methods">
      <div className="method-intro">
        <p className="eyebrow">Paper → field method</p>
        <h2>Bring a paper. Ask what it would take here.</h2>
        <p>
          We read the method, match it against what Valparai already carries, and make the first
          honest figure. A close analogue is labelled as one; a true replication has to earn its
          name.
        </p>
        <button className="paper-drop" type="button" onClick={() => input.current?.click()}>
          <span className="paper-icon">
            {busy ? <LoaderCircle className="spin" /> : <Upload />}
          </span>
          <span>
            <strong>{busy ? "Reading the method…" : "Drop a paper or choose a PDF"}</strong>
            <small>PDF or plain text up to 25 MB · this does not alter the site data</small>
          </span>
          <ChevronRight />
        </button>
        <input
          ref={input}
          type="file"
          accept=".pdf,.txt,text/plain,application/pdf"
          hidden
          onChange={(event) => {
            const file = event.target.files?.[0];
            if (file) void readPaper(file);
          }}
        />
        <div className="paper-or"><span>or</span></div>
        <form
          className="paper-reference-form"
          onSubmit={(event) => {
            event.preventDefault();
            void readReference();
          }}
        >
          <label htmlFor="paper-reference">Use an article DOI</label>
          <div>
            <input
              id="paper-reference"
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              placeholder="10.1002/ecs2.2860"
              inputMode="url"
            />
            <button type="submit" disabled={busy || !reference.trim()}>
              Read
            </button>
          </div>
          <small>We look up article metadata and registered related datasets.</small>
        </form>
        {error && <p className="paper-error">{error}</p>}
        {!paper && !busy && (
          <button
            type="button"
            className="example-paper"
            onClick={() => {
              const example = new File(
                [
                  "We evaluate assisted natural regeneration using permanent plots. We measure seedling and sapling richness, old-growth recruits, canopy cover and basal area, and compare restored sites with reference forest through repeated surveys.",
                ],
                "ANR-method-example.txt",
                { type: "text/plain" },
              );
              const form = new FormData();
              form.set("paper", example);
              void submitPaper(form);
            }}
          >
            <BookOpenText size={16} />
            Try an assisted natural regeneration example
          </button>
        )}
      </div>
      <div className={`method-result ${paper ? "has-paper" : ""}`}>
        {!paper ? (
          <div className="method-placeholder">
            <FileText />
            <p>The method reading will appear here.</p>
            <ul>
              <li>What the paper measures</li>
              <li>What this landscape already holds</li>
              <li>What still needs fieldwork</li>
              <li>The closest responsible first figure</li>
            </ul>
          </div>
        ) : (
          <>
            <div className="paper-title">
              <span>
                <FileText size={17} />
                {paper.filename}
              </span>
              <small>
                {paper.mode === "live" ? "Bridge-assisted reading" : "First deterministic reading"}
              </small>
            </div>
            {paper.paper && (
              <div className="paper-metadata">
                <div>
                  <span>{paper.paper.journal || "Article"}</span>
                  {paper.paper.year && <span>{paper.paper.year}</span>}
                  <span>{paper.paper.doi}</span>
                </div>
                <a href={paper.paper.url} target="_blank" rel="noreferrer">
                  Article record <ExternalLink size={13} />
                </a>
              </div>
            )}
            <h3>{paper.reading.method}</h3>
            <p className="method-summary">{paper.reading.plain_summary}</p>
            <div className="method-columns">
              <div>
                <h4>
                  <Check /> Already here
                </h4>
                <ul>
                  {paper.reading.available.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
              <div>
                <h4>
                  <X /> Still needed
                </h4>
                <ul>
                  {paper.reading.missing.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </div>
            </div>
            <div className="method-caution">
              {paper.reading.cautions.map((item) => (
                <p key={item}>{item}</p>
              ))}
            </div>
            {paper.commentary && <p className="bridge-commentary">{paper.commentary}</p>}
            <section className="linked-datasets">
              <div className="linked-datasets-heading">
                <div>
                  <Database size={17} />
                  <span>Datasets associated with or mentioned by this paper</span>
                </div>
                <small>{paper.admission.message}</small>
              </div>
              {paper.linked_datasets.length ? (
                paper.linked_datasets.map((dataset) => (
                  <article key={dataset.doi}>
                    <div>
                      <strong>{dataset.title}</strong>
                      <span>
                        {[
                          dataset.relationship === "registered-related-dataset"
                            ? "Registered as related"
                            : "Mentioned in paper text",
                          dataset.repository,
                          dataset.size,
                          dataset.license,
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                      </span>
                      <a href={dataset.url} target="_blank" rel="noreferrer">
                        {dataset.doi} <ExternalLink size={11} />
                      </a>
                    </div>
                    <button
                      type="button"
                      disabled={Boolean(staging)}
                      onClick={() => void stageDataset(dataset)}
                    >
                      {staging === dataset.doi ? (
                        <LoaderCircle className="spin" size={14} />
                      ) : (
                        <Database size={14} />
                      )}
                      Queue for source review
                    </button>
                  </article>
                ))
              ) : (
                <p className="no-linked-data">
                  No registered related dataset was found. The paper can still be read as a
                  method, but it has not added local observations.
                </p>
              )}
              {stageResult && (
                <div className={`stage-result ${stageResult.persisted ? "persisted" : ""}`}>
                  <strong>{stageResult.persisted ? "Queued locally" : "Candidate prepared"}</strong>
                  <p>{stageResult.message}</p>
                  <span>{stageResult.request_id}</span>
                </div>
              )}
            </section>
            <button className="primary-button" type="button" onClick={() => void drawInR()}>
              <FlaskConical size={17} />
              Draw the first-look analogue in R
            </button>
            {rPlot?.svg && (
              <div className="r-plot" dangerouslySetInnerHTML={{ __html: rPlot.svg }} />
            )}
            {rPlot?.note && <p className="r-note">{rPlot.note}</p>}
          </>
        )}
      </div>
    </section>
  );
}
