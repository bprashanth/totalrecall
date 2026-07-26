"use client";

import { useEffect, useRef, useState } from "react";
import {
  AudioLines,
  BookOpenText,
  ChevronDown,
  CircleDot,
  CloudSun,
  Database,
  ExternalLink,
  FileSearch,
  FlaskConical,
  Leaf,
  Map,
  Menu,
  Mountain,
  ScanSearch,
  Sprout,
  X,
} from "lucide-react";
import type { AnalysisResponse, DemoData, MethodReading, ResultAction } from "@/lib/types";
import { AcousticPlot } from "./AcousticPlot";
import { FigureCard } from "./FigureCard";
import { LiveFinding } from "./LiveFinding";
import { MethodWorkbench } from "./MethodWorkbench";
import { QuestionComposer } from "./QuestionComposer";
import { RestorationPlot } from "./RestorationPlot";
import { SeasonalPlot } from "./SeasonalPlot";
import { SiteMap } from "./SiteMap";

const NAV = [
  ["landscape", "Landscape", Map],
  ["seasons", "Seasons", CloudSun],
  ["restoration", "Restoration", Sprout],
  ["soundscape", "Soundscape", AudioLines],
  ["methods", "Paper methods", BookOpenText],
] as const;

function format(value: number) {
  return new Intl.NumberFormat("en-IN", { notation: value > 99_999 ? "compact" : "standard" }).format(
    value,
  );
}

export function Studio({ data }: { data: DemoData }) {
  const [active, setActive] = useState("landscape");
  const [finding, setFinding] = useState<AnalysisResponse | null>(null);
  const [busy, setBusy] = useState(false);
  const [live, setLive] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const sessionId = useRef("");

  function activeSessionId() {
    if (sessionId.current) return sessionId.current;
    const existing = window.sessionStorage.getItem("fieldnote-session");
    sessionId.current = existing || `fieldnote-${crypto.randomUUID()}`;
    window.sessionStorage.setItem("fieldnote-session", sessionId.current);
    return sessionId.current;
  }

  useEffect(() => {
    fetch("/api/status")
      .then((response) => response.json())
      .then((body) => setLive(Boolean(body.live)))
      .catch(() => setLive(false));
    const sections = NAV.map(([id]) => document.getElementById(id)).filter(Boolean) as HTMLElement[];
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
        if (visible?.target.id) setActive(visible.target.id);
      },
      { rootMargin: "-18% 0px -64% 0px", threshold: [0.1, 0.35] },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  async function ask(question: string) {
    setBusy(true);
    try {
      const response = await fetch("/api/analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, session_id: activeSessionId() }),
      });
      const body = (await response.json()) as AnalysisResponse;
      setFinding(body);
      window.setTimeout(() => {
        document.getElementById("new-finding")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 80);
    } finally {
      setBusy(false);
    }
  }

  async function runResultAction(action: ResultAction) {
    setBusy(true);
    try {
      const response = await fetch("/api/analysis", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          capability_id: action.capability_id,
          arguments: action.arguments,
          question: action.label,
          request_id: `${activeSessionId()}-${action.action_id}-${crypto.randomUUID()}`,
        }),
      });
      const body = (await response.json()) as AnalysisResponse;
      setFinding(body);
      window.setTimeout(() => {
        document.getElementById("new-finding")?.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 80);
    } finally {
      setBusy(false);
    }
  }

  function focusMethod(kind: MethodReading["suggested_visual"]) {
    const target =
      kind === "seasonal"
        ? "seasons"
        : kind === "acoustic"
          ? "soundscape"
          : kind === "restoration"
            ? "restoration"
            : "landscape";
    document.getElementById(target)?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <div className="studio">
      <header className="masthead">
        <a className="brand" href="#top" aria-label="Fieldnote home">
          <span className="brand-mark">
            <Leaf />
          </span>
          <span>
            <strong>Fieldnote</strong>
            <small>Valparai Plateau</small>
          </span>
        </a>
        <div className="mast-context">
          <span className={`connection-dot ${live ? "live" : ""}`} />
          {live ? "Valparai field index connected" : "Public field atlas"}
        </div>
        <nav className="mast-actions">
          <button
            type="button"
            onClick={() => document.getElementById("methods")?.scrollIntoView({ behavior: "smooth" })}
          >
            <FileSearch size={17} />
            Read a paper
          </button>
          <button className="mobile-menu" type="button" onClick={() => setNavOpen(!navOpen)}>
            {navOpen ? <X /> : <Menu />}
          </button>
        </nav>
      </header>

      <aside className={`chapter-nav ${navOpen ? "open" : ""}`} aria-label="Field chapters">
        <p>Field chapters</p>
        {NAV.map(([id, label, Icon], index) => (
          <a
            key={id}
            href={`#${id}`}
            className={active === id ? "active" : ""}
            onClick={() => setNavOpen(false)}
          >
            <span>{String(index + 1).padStart(2, "0")}</span>
            <Icon />
            {label}
          </a>
        ))}
        <div className="nav-source">
          <Database size={16} />
          <span>
            {data.summary.sources} admitted sources
            <small>Field, satellite, weather & literature</small>
          </span>
        </div>
      </aside>

      <main id="top">
        <section className="opening">
          <div className="opening-kicker">
            <span>Field atlas · July 2026</span>
            <i />
            <span>Western Ghats</span>
          </div>
          <h1>
            Read the landscape
            <em>before asking it to explain itself.</em>
          </h1>
          <p className="opening-deck">
            Valparai is rainforest and tea, ridgeline and stream, field plot and birdsong. Begin
            with what has been seen. Keep sight of where people looked. Then follow the question.
          </p>
          <div className="opening-actions">
            <button type="button" onClick={() => void ask("Tell me about this site, starting with the map.")}>
              <ScanSearch size={17} />
              Take a guided first look
            </button>
            <a href="#landscape">
              Open the atlas
              <ChevronDown size={16} />
            </a>
          </div>
        </section>

        {finding && (
          <div id="new-finding" className="finding-anchor">
            <LiveFinding
              response={finding}
              data={data}
              busy={busy}
              onAction={(action) => void runResultAction(action)}
            />
          </div>
        )}

        <section id="landscape" className="chapter">
          <FigureCard
            number="01"
            eyebrow="The landscape"
            title="Where the record gathers—and where it thins"
            deck="A first map of source-linked observations across the study envelope and its wider context."
            reading="a map of evidence coverage. Gold cells hold more records; switch to survey effort to see where structured looking is visible."
            limit="records and effort come from different studies and protocols. Empty or pale cells cannot be read as ecological absence."
            action="Ask about a named species"
            onAction={() => void ask("Where have lion-tailed macaques been recorded, and where did people actually look?")}
            className="hero-figure"
          >
            <SiteMap cells={data.cells} aoi={data.site.target_aoi.geometry} />
          </FigureCard>

          <div className="field-ledger">
            <div>
              <span className="ledger-icon">
                <CircleDot />
              </span>
              <strong>{format(data.summary.mapped_records)}</strong>
              <p>mapped records</p>
              <small>Source-linked observations with usable locations</small>
            </div>
            <div>
              <span className="ledger-icon">
                <Leaf />
              </span>
              <strong>{format(data.summary.entities)}</strong>
              <p>named entities</p>
              <small>Resolved and retained labels across sources</small>
            </div>
            <div>
              <span className="ledger-icon">
                <Mountain />
              </span>
              <strong>{format(data.summary.locations)}</strong>
              <p>field locations</p>
              <small>Plots, routes, recorders and named sites</small>
            </div>
            <div>
              <span className="ledger-icon">
                <FlaskConical />
              </span>
              <strong>{format(data.summary.effort_rows)}</strong>
              <p>effort entries</p>
              <small>Where a survey denominator was explicit</small>
            </div>
          </div>
        </section>

        <section id="seasons" className="chapter split-chapter">
          <FigureCard
            number="02"
            eyebrow="The seasons"
            title="A year of greenness, with the clouds left visible"
            deck="Median Sentinel-2 greenness across the available cells in 2024."
            reading="a seasonal surface profile. The shaded span shows how differently the cells behaved, not uncertainty around a single mean."
            limit="July is missing and October is sparse. One year describes rhythm; it cannot establish a long-term trend or a field event such as flowering."
            action="Ask what field observations would help"
            onAction={() => void ask("What field observations would help us interpret this greenness seasonally?")}
          >
            <SeasonalPlot points={data.seasonal_ndvi} />
          </FigureCard>
          <aside className="chapter-note">
            <span className="note-number">Field note 02</span>
            <blockquote>
              The monsoon does not simply make one green line rise. Clouds hide the ground, places
              respond differently, and a satellite sees leaf-light—not the arrival of a flower or
              a seedling.
            </blockquote>
            <div className="next-observations">
              <p>Useful field companions</p>
              <ul>
                <li>Dated leaf-flush observations</li>
                <li>Flowering and fruiting records</li>
                <li>Repeat canopy photographs</li>
              </ul>
            </div>
          </aside>
        </section>

        <section id="restoration" className="chapter">
          <FigureCard
            number="03"
            eyebrow="Forest recovery"
            title="Young trees are one chapter of recovery"
            deck="Plot-level indicators across the comparison classes reported by the restoration source."
            reading="the spread among individual plots. Each dot is a plot; the median helps orient the eye without hiding variation."
            limit="these are descriptive groups. Without dates, repeated visits and a matched comparison, the figure does not say that an intervention caused the difference."
            action="What would a stronger ANR study need?"
            onAction={() => void ask("What would a stronger assisted natural regeneration study need in Valparai?")}
          >
            <RestorationPlot rows={data.restoration} />
          </FigureCard>
        </section>

        <section id="soundscape" className="chapter split-chapter acoustic-chapter">
          <aside className="chapter-note sound-note">
            <span className="note-number">Field note 04</span>
            <h3>The forest is never silent.</h3>
            <p>
              Dawn, cicada-hours, rain and night each occupy different bands of sound. The pattern
              can reveal when a site is acoustically full. Naming the voices is another task.
            </p>
            <button type="button" onClick={() => void ask("What can this soundscape tell us, and what can it not tell us?")}>
              Ask the soundscape
              <ExternalLink size={14} />
            </button>
          </aside>
          <FigureCard
            number="04"
            eyebrow="The soundscape"
            title="A day heard across frequencies"
            deck="Mean acoustic-space use across 43 recorder sites, grouped into readable frequency bands."
            reading="when the recorded soundscape occupied more of each frequency band. Darker cells indicate greater acoustic-space use."
            limit="this is not a species count and the admitted snapshot contains no playable WAV clips. Identified calls are needed before naming species."
          >
            <AcousticPlot rows={data.acoustic} />
          </FigureCard>
        </section>

        <div>
          <MethodWorkbench data={data} sessionId={sessionId} onFocus={focusMethod} />
        </div>

        <section className="source-room">
          <div>
            <p className="eyebrow">The source room</p>
            <h2>Every figure keeps a path back.</h2>
            <p>
              The atlas begins quickly, but it does not ask you to trust a picture blindly.
              Connected results retain the source version, calculation, limits and contributing
              rows behind each mark.
            </p>
          </div>
          <div className="source-stack">
            {data.sources.slice(0, 5).map((source, index) => (
              <article key={source.source_id} style={{ "--i": index } as React.CSSProperties}>
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{source.title}</p>
                <small>{source.license || "Rights recorded at source"}</small>
              </article>
            ))}
          </div>
        </section>
      </main>

      <QuestionComposer
        busy={busy}
        onAsk={(question) => void ask(question)}
        onPaper={() => document.getElementById("methods")?.scrollIntoView({ behavior: "smooth" })}
      />
    </div>
  );
}
