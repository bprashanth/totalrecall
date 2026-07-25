"use client";

import { useRef, useState } from "react";
import {
  BookOpenText,
  Check,
  ChevronRight,
  FileText,
  FlaskConical,
  LoaderCircle,
  Upload,
  X,
} from "lucide-react";
import type { DemoData, MethodReading } from "@/lib/types";

type PaperResponse = {
  mode: "live" | "preview";
  filename: string;
  characters_read: number;
  reading: MethodReading;
  commentary: string;
};

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
  const [rPlot, setRPlot] = useState<{ mode: string; svg?: string; note?: string } | null>(null);

  async function readPaper(file: File) {
    setBusy(true);
    setError("");
    setPaper(null);
    setRPlot(null);
    const form = new FormData();
    form.set("paper", file);
    form.set("session_id", sessionId);
    try {
      const response = await fetch("/api/paper", { method: "POST", body: form });
      const body = await response.json();
      if (!response.ok) throw new Error(body.error || "Could not read that paper.");
      setPaper(body);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not read that paper.");
    } finally {
      setBusy(false);
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
            <small>PDF or plain text · the paper is not treated as local evidence</small>
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
              void readPaper(example);
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
