"use client";

import { useMemo, useState } from "react";
import { LocateFixed } from "lucide-react";
import type {
  Cell,
  GeoJsonFeature,
  GeoJsonGeometry,
  MapResultLayer,
} from "@/lib/types";

type Point = { longitude: number; latitude: number; label?: string };

type SiteMapProps = {
  cells: Cell[];
  aoi: GeoJSON.Polygon;
  livePoints?: Point[];
  liveLayers?: MapResultLayer[];
  initialMode?: "records" | "effort";
};

const WIDTH = 980;
const HEIGHT = 610;
const PAD = 30;

const LAYER_COLOURS = {
  derived: "#f3c55f",
  observed: "#91d8c4",
  reported: "#f7f2e5",
  modelled: "#e98d69",
  inferred: "#d6a8e8",
  requested: "#f2a7a0",
  external: "#97bde3",
  unknown: "#e8e1cf",
} as const;

function coordinatePairs(value: unknown): Array<[number, number]> {
  if (!Array.isArray(value)) return [];
  if (
    value.length >= 2 &&
    typeof value[0] === "number" &&
    typeof value[1] === "number"
  ) {
    return [[value[0], value[1]]];
  }
  return value.flatMap(coordinatePairs);
}

function geometryParts(geometry: GeoJsonGeometry): Array<Array<[number, number]>> {
  const coordinates = geometry.coordinates;
  if (!Array.isArray(coordinates)) return [];
  if (geometry.type === "Point") return [coordinatePairs(coordinates)];
  if (geometry.type === "MultiPoint" || geometry.type === "LineString") {
    return [coordinatePairs(coordinates)];
  }
  if (geometry.type === "MultiLineString" || geometry.type === "Polygon") {
    return coordinates.map(coordinatePairs);
  }
  if (geometry.type === "MultiPolygon") {
    return coordinates.flatMap((polygon) =>
      Array.isArray(polygon) ? polygon.map(coordinatePairs) : [],
    );
  }
  return [];
}

function featureLabel(feature: GeoJsonFeature, fallback: string): string {
  const properties = feature.properties || {};
  return String(
    properties.label ||
      properties.role ||
      properties.subject ||
      properties.name ||
      feature.id ||
      fallback,
  );
}

export function SiteMap({
  cells,
  aoi,
  livePoints = [],
  liveLayers = [],
  initialMode = "records",
}: SiteMapProps) {
  const [mode, setMode] = useState<"records" | "effort">(initialMode);
  const [hovered, setHovered] = useState<Cell | null>(null);
  const [liveHovered, setLiveHovered] = useState<{
    label: string;
    properties: Record<string, unknown>;
  } | null>(null);
  const hasLiveMap = liveLayers.length > 0 || livePoints.length > 0;
  const bounds = useMemo(() => {
    const framingLayers = liveLayers.filter(
      (layer) =>
        layer.styleHint.emphasis === "primary" ||
        layer.evidenceClass === "reported",
    );
    const liveCoordinates = (framingLayers.length > 0 ? framingLayers : liveLayers).flatMap((layer) =>
      layer.data.features.flatMap((feature) =>
        feature.geometry ? coordinatePairs(feature.geometry.coordinates) : [],
      ),
    );
    const aoiCoordinates = coordinatePairs(aoi.coordinates);
    const coordinates =
      hasLiveMap && liveCoordinates.length > 0
        ? [...liveCoordinates, ...aoiCoordinates]
        : cells.flatMap((cell) => [
            [cell.west, cell.south] as [number, number],
            [cell.east, cell.north] as [number, number],
          ]);
    const xs = coordinates.map(([longitude]) => longitude);
    const ys = coordinates.map(([, latitude]) => latitude);
    const west = Math.min(...xs);
    const east = Math.max(...xs);
    const south = Math.min(...ys);
    const north = Math.max(...ys);
    const xPad = Math.max((east - west) * 0.035, 0.002);
    const yPad = Math.max((north - south) * 0.035, 0.002);
    return {
      west: west - xPad,
      east: east + xPad,
      south: south - yPad,
      north: north + yPad,
    };
  }, [aoi.coordinates, cells, hasLiveMap, liveLayers]);
  const project = (lon: number, lat: number) => {
    const x = PAD + ((lon - bounds.west) / (bounds.east - bounds.west)) * (WIDTH - PAD * 2);
    const y =
      HEIGHT -
      PAD -
      ((lat - bounds.south) / (bounds.north - bounds.south)) * (HEIGHT - PAD * 2);
    return [x, y] as const;
  };
  const maxRecords = Math.max(...cells.map((cell) => cell.records), 1);
  const maxEffort = Math.max(...cells.map((cell) => cell.effort_visits), 1);
  const polygon = aoi.coordinates[0]
    .map(([lon, lat]) => project(lon, lat).join(","))
    .join(" ");
  const liveLegend = liveLayers.map((layer, index) => ({
    ...layer,
    colour:
      LAYER_COLOURS[
        (layer.evidenceClass in LAYER_COLOURS
          ? layer.evidenceClass
          : "unknown") as keyof typeof LAYER_COLOURS
      ],
    series: Number(layer.styleHint.series || index),
  }));

  return (
    <div className={`site-map-shell ${hasLiveMap ? "has-live-layers" : ""}`}>
      {!hasLiveMap && (
        <div className="map-controls" aria-label="Map layer">
          <button className={mode === "records" ? "active" : ""} onClick={() => setMode("records")}>
            Records
          </button>
          <button className={mode === "effort" ? "active" : ""} onClick={() => setMode("effort")}>
            Survey effort
          </button>
        </div>
      )}
      <svg
        className="site-map"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={
          hasLiveMap
            ? "Map of the returned analytical layers"
            : `Valparai map coloured by ${mode === "records" ? "record density" : "survey effort"}`
        }
      >
        <defs>
          <linearGradient id="terrain" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#183d33" />
            <stop offset="48%" stopColor="#31594a" />
            <stop offset="100%" stopColor="#8c8463" />
          </linearGradient>
          <filter id="soft">
            <feGaussianBlur stdDeviation="16" />
          </filter>
          <pattern id="grain" width="8" height="8" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r=".7" fill="#fff" opacity=".08" />
            <circle cx="6" cy="4" r=".5" fill="#061811" opacity=".12" />
          </pattern>
        </defs>
        <rect width={WIDTH} height={HEIGHT} fill="url(#terrain)" rx="18" />
        <path
          d="M-20 390 C150 315 225 440 392 362 S720 235 1020 325"
          fill="none"
          stroke="#d9d2ad"
          strokeWidth="90"
          opacity=".08"
          filter="url(#soft)"
        />
        <path
          d="M-20 145 C170 245 300 40 520 145 S790 260 1020 95"
          fill="none"
          stroke="#0a251d"
          strokeWidth="58"
          opacity=".35"
          filter="url(#soft)"
        />
        {[95, 155, 235, 315, 410, 500].map((y, index) => (
          <path
            key={y}
            d={`M-30 ${y} C180 ${y - 70 + index * 8} 260 ${y + 80} 490 ${y - 8} S790 ${
              y - 60
            } 1020 ${y + 15}`}
            fill="none"
            stroke="#eae5d2"
            strokeWidth="1"
            opacity=".16"
          />
        ))}
        <rect width={WIDTH} height={HEIGHT} fill="url(#grain)" rx="18" />
        {cells.map((cell) => {
          const [x1, y1] = project(cell.west, cell.north);
          const [x2, y2] = project(cell.east, cell.south);
          const value =
            mode === "records"
              ? Math.log1p(cell.records) / Math.log1p(maxRecords)
              : Math.sqrt(cell.effort_visits / maxEffort);
          const fill =
            mode === "records"
              ? `rgba(238, 196, 96, ${0.05 + value * 0.82})`
              : `rgba(120, 207, 189, ${0.04 + value * 0.86})`;
          return (
            <rect
              key={cell.cell_id}
              x={x1}
              y={y1}
              width={Math.max(1.4, x2 - x1)}
              height={Math.max(1.4, y2 - y1)}
              fill={fill}
              opacity={hasLiveMap ? 0.15 : 1}
              stroke={cell.target_role === "target" ? "rgba(255,255,255,.3)" : "transparent"}
              strokeWidth=".55"
              onMouseEnter={() => setHovered(cell)}
              onMouseLeave={() => setHovered(null)}
            />
          );
        })}
        <polygon
          points={polygon}
          fill="none"
          stroke="#fffdf4"
          strokeWidth="2.2"
          strokeDasharray="8 6"
          opacity={hasLiveMap ? ".38" : ".92"}
        />
        {liveLegend.map((layer) =>
          layer.data.features.slice(0, 1600).flatMap((feature, featureIndex) => {
            if (!feature.geometry) return [];
            const render = String(layer.styleHint.render || "fill");
            const isPrimary = layer.styleHint.emphasis === "primary";
            const colour =
              layer.evidenceClass === "observed" && layer.series > 0
                ? layer.series % 2 === 0
                  ? "#9fc4ef"
                  : "#91d8c4"
                : layer.colour;
            const hover = {
              label: featureLabel(feature, layer.label),
              properties: feature.properties || {},
            };
            if (feature.geometry.type === "Point" || feature.geometry.type === "MultiPoint") {
              return coordinatePairs(feature.geometry.coordinates).map(([lon, lat], pointIndex) => {
                const [x, y] = project(lon, lat);
                return (
                  <circle
                    className="result-map-feature"
                    key={`${layer.layerId}-${featureIndex}-${pointIndex}`}
                    cx={x}
                    cy={y}
                    r={isPrimary ? 5 : 3.3}
                    fill={colour}
                    stroke="#102e26"
                    strokeWidth="1"
                    opacity={isPrimary ? ".95" : ".78"}
                    onMouseEnter={() => setLiveHovered(hover)}
                    onMouseLeave={() => setLiveHovered(null)}
                  />
                );
              });
            }
            return geometryParts(feature.geometry).map((part, partIndex) => {
              const points = part.map(([lon, lat]) => project(lon, lat).join(",")).join(" ");
              const isLine =
                feature.geometry?.type === "LineString" ||
                feature.geometry?.type === "MultiLineString";
              return isLine ? (
                <polyline
                  className="result-map-feature"
                  key={`${layer.layerId}-${featureIndex}-${partIndex}`}
                  points={points}
                  fill="none"
                  stroke={colour}
                  strokeWidth={isPrimary ? "3.2" : "1.5"}
                  opacity={isPrimary ? ".95" : ".72"}
                  onMouseEnter={() => setLiveHovered(hover)}
                  onMouseLeave={() => setLiveHovered(null)}
                />
              ) : (
                <polygon
                  className="result-map-feature"
                  key={`${layer.layerId}-${featureIndex}-${partIndex}`}
                  points={points}
                  fill={render === "outline" ? "none" : colour}
                  fillOpacity={isPrimary ? ".72" : ".24"}
                  stroke={colour}
                  strokeWidth={isPrimary ? "2.1" : "1.15"}
                  strokeDasharray={layer.evidenceClass === "reported" ? "8 5" : undefined}
                  opacity={isPrimary ? ".98" : ".76"}
                  onMouseEnter={() => setLiveHovered(hover)}
                  onMouseLeave={() => setLiveHovered(null)}
                />
              );
            });
          }),
        )}
        {livePoints.slice(0, 800).map((point, index) => {
          const [x, y] = project(point.longitude, point.latitude);
          return <circle key={`${x}-${y}-${index}`} cx={x} cy={y} r="3.2" fill="#f5ede0" opacity=".82" />;
        })}
      </svg>
      <div className="map-place">
        <LocateFixed size={16} />
        <span>Valparai Plateau</span>
        <small>
          {bounds.south.toFixed(2)}–{bounds.north.toFixed(2)}° N
        </small>
      </div>
      {hasLiveMap ? (
        <div className="result-layer-legend" aria-label="Result map layers">
          {liveLegend.map((layer) => (
            <span key={layer.layerId}>
              <i
                style={{
                  background:
                    String(layer.styleHint.render || "fill") === "outline"
                      ? "transparent"
                      : layer.colour,
                  borderColor: layer.colour,
                }}
              />
              {layer.label}
              <small>{layer.evidenceClass}</small>
            </span>
          ))}
        </div>
      ) : (
        <div className="map-legend">
          <span>{mode === "records" ? "Fewer records" : "Less recorded effort"}</span>
          <i className={mode} />
          <span>{mode === "records" ? "More records" : "More recorded effort"}</span>
        </div>
      )}
      {hovered && (
        <div className="map-tooltip">
          <strong>{hovered.target_role === "target" ? "Study-area cell" : "Context cell"}</strong>
          <span>{hovered.records.toLocaleString("en-IN")} records</span>
          <span>{hovered.entities.toLocaleString("en-IN")} named entities</span>
          <span>{hovered.effort_visits.toLocaleString("en-IN")} effort entries</span>
        </div>
      )}
      {liveHovered && (
        <div className="map-tooltip result-tooltip">
          <strong>{liveHovered.label}</strong>
          {Object.entries(liveHovered.properties)
            .filter(([, value]) => ["string", "number", "boolean"].includes(typeof value))
            .slice(0, 4)
            .map(([key, value]) => (
              <span key={key}>
                {key.replaceAll("_", " ")}: {String(value)}
              </span>
            ))}
        </div>
      )}
    </div>
  );
}
