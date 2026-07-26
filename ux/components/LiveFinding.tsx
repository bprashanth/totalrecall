"use client";

import { useState } from "react";
import { CircleCheck, ExternalLink, FlaskConical, MoveRight, TriangleAlert } from "lucide-react";
import type {
  AnalysisResponse,
  DemoData,
  GeoJsonFeatureCollection,
  MapResultLayer,
  ResultAction,
} from "@/lib/types";
import { SiteMap } from "./SiteMap";

function mapLayers(result: AnalysisResponse): MapResultLayer[] {
  const layers: MapResultLayer[] = [];
  for (const item of result.results) {
    for (const visual of item.envelope.visuals || []) {
      if (visual.visual_type !== "map") continue;
      for (const layer of visual.layers || []) {
        const handle = layer.data_ref?.handle;
        const payload = handle ? item.payloads[handle] : undefined;
        if (
          handle &&
          payload &&
          typeof payload === "object" &&
          (payload as { type?: string }).type === "FeatureCollection"
        ) {
          layers.push({
            layerId: layer.layer_id || handle,
            label: layer.legend?.label || layer.layer_id || "Result layer",
            evidenceClass: layer.evidence_class || "unknown",
            geometryType: layer.geometry_type,
            styleHint: layer.style_hint || {},
            data: payload as GeoJsonFeatureCollection,
          });
        }
      }
    }
  }
  return layers;
}

export function LiveFinding({
  response,
  data,
  busy = false,
  onAction,
}: {
  response: AnalysisResponse;
  data: DemoData;
  busy?: boolean;
  onAction?: (action: ResultAction) => void;
}) {
  const [showWhy, setShowWhy] = useState(false);
  const layers = mapLayers(response);
  const actions = response.results.flatMap((item) => item.envelope.actions || []).slice(0, 4);
  const limitations = response.results
    .flatMap((item) => item.envelope.limitations || [])
    .filter((limitation, index, all) => {
      const key = limitation.code || limitation.message;
      return all.findIndex((item) => (item.code || item.message) === key) === index;
    })
    .slice(0, 3);
  const sourceVersions = response.results.flatMap(
    (item) => item.envelope.audit?.source_versions || [],
  );
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
      {layers.length > 0 && (
        <SiteMap cells={data.cells} aoi={data.site.target_aoi.geometry} liveLayers={layers} />
      )}
      <div className="finding-copy">
        <p>{response.answer}</p>
        {response.note && <small>{response.note}</small>}
      </div>
      {limitations.length > 0 && (
        <aside className="finding-limitations">
          <TriangleAlert size={17} />
          <div>
            <strong>Read this map with care</strong>
            {limitations.map((limitation) => (
              <p key={limitation.code || limitation.message}>{limitation.message}</p>
            ))}
          </div>
        </aside>
      )}
      {actions.length > 0 && onAction && (
        <div className="finding-actions" aria-label="Refine this finding">
          <p>Follow the finding</p>
          <div>
            {actions.map((action) => (
              <button
                key={action.action_id}
                type="button"
                disabled={busy}
                onClick={() => onAction(action)}
              >
                {action.label}
                <MoveRight size={15} />
              </button>
            ))}
          </div>
        </div>
      )}
      {showWhy && (
        <div className="finding-audit">
          <strong>Why this figure</strong>
          <p>
            {sourceVersions.length
              ? `${sourceVersions.length} versioned source${sourceVersions.length === 1 ? "" : "s"} contributed to this result.`
              : "This result retains its source and capability lineage."}
          </p>
          {sourceVersions.slice(0, 6).map((source, index) => (
            <span key={`${source.source_id || source.title}-${index}`}>
              {source.title || source.source_id || "Versioned source"}
            </span>
          ))}
        </div>
      )}
      <footer>
        <span>{response.audit_id ? `Audit ${response.audit_id}` : "Aggregated public preview"}</span>
        {response.results[0]?.envelope.audit?.audit_id && (
          <button type="button" onClick={() => setShowWhy(!showWhy)} aria-expanded={showWhy}>
            {showWhy ? "Hide figure audit" : "Why this figure"}
            <ExternalLink size={14} />
          </button>
        )}
      </footer>
    </section>
  );
}
