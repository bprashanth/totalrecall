"use client";

import { CircleCheck, ExternalLink, FlaskConical } from "lucide-react";
import type { AnalysisResponse, DemoData } from "@/lib/types";
import { SiteMap } from "./SiteMap";

function geoPoints(result: AnalysisResponse) {
  const points: Array<{ longitude: number; latitude: number; label?: string }> = [];
  for (const item of result.results) {
    for (const payload of Object.values(item.payloads)) {
      if (
        payload &&
        typeof payload === "object" &&
        (payload as { type?: string }).type === "FeatureCollection"
      ) {
        for (const feature of (payload as { features?: Array<Record<string, unknown>> }).features || []) {
          const geometry = feature.geometry as { type?: string; coordinates?: number[] } | undefined;
          if (geometry?.type === "Point" && geometry.coordinates?.length === 2) {
            points.push({
              longitude: geometry.coordinates[0],
              latitude: geometry.coordinates[1],
              label: String((feature.properties as { label?: string } | undefined)?.label || ""),
            });
          }
        }
      }
    }
  }
  return points;
}

export function LiveFinding({ response, data }: { response: AnalysisResponse; data: DemoData }) {
  const points = geoPoints(response);
  return (
    <section className="live-finding" aria-live="polite">
      <header>
        <div>
          <p className="eyebrow">
            {response.mode === "live" ? "A new reading" : "Preview reading"}
          </p>
          <h2>{response.mode === "live" ? "The landscape answers" : "A useful place to begin"}</h2>
        </div>
        <span className={`mode-badge ${response.mode}`}>
          {response.mode === "live" ? <CircleCheck /> : <FlaskConical />}
          {response.mode === "live" ? "Audited result" : "Preview"}
        </span>
      </header>
      {points.length > 0 && (
        <SiteMap cells={data.cells} aoi={data.site.target_aoi.geometry} livePoints={points} />
      )}
      <div className="finding-copy">
        <p>{response.answer}</p>
        {response.note && <small>{response.note}</small>}
      </div>
      <footer>
        <span>{response.audit_id ? `Audit ${response.audit_id}` : "Aggregated public preview"}</span>
        {response.results[0]?.envelope.audit?.audit_id && (
          <button type="button">
            Why this figure
            <ExternalLink size={14} />
          </button>
        )}
      </footer>
    </section>
  );
}
