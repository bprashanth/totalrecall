"use client";

import { useMemo, useState } from "react";
import { LocateFixed } from "lucide-react";
import type { Cell } from "@/lib/types";

type Point = { longitude: number; latitude: number; label?: string };

type SiteMapProps = {
  cells: Cell[];
  aoi: GeoJSON.Polygon;
  livePoints?: Point[];
  initialMode?: "records" | "effort";
};

const WIDTH = 980;
const HEIGHT = 610;
const PAD = 30;

export function SiteMap({ cells, aoi, livePoints = [], initialMode = "records" }: SiteMapProps) {
  const [mode, setMode] = useState<"records" | "effort">(initialMode);
  const [hovered, setHovered] = useState<Cell | null>(null);
  const bounds = useMemo(() => {
    const xs = cells.flatMap((cell) => [cell.west, cell.east]);
    const ys = cells.flatMap((cell) => [cell.south, cell.north]);
    return {
      west: Math.min(...xs),
      east: Math.max(...xs),
      south: Math.min(...ys),
      north: Math.max(...ys),
    };
  }, [cells]);
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

  return (
    <div className="site-map-shell">
      <div className="map-controls" aria-label="Map layer">
        <button className={mode === "records" ? "active" : ""} onClick={() => setMode("records")}>
          Records
        </button>
        <button className={mode === "effort" ? "active" : ""} onClick={() => setMode("effort")}>
          Survey effort
        </button>
      </div>
      <svg
        className="site-map"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        role="img"
        aria-label={`Valparai map coloured by ${mode === "records" ? "record density" : "survey effort"}`}
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
          opacity=".92"
        />
        {livePoints.slice(0, 800).map((point, index) => {
          const [x, y] = project(point.longitude, point.latitude);
          return <circle key={`${x}-${y}-${index}`} cx={x} cy={y} r="3.2" fill="#f5ede0" opacity=".82" />;
        })}
      </svg>
      <div className="map-place">
        <LocateFixed size={16} />
        <span>Valparai Plateau</span>
        <small>10.16–12.94° N</small>
      </div>
      <div className="map-legend">
        <span>{mode === "records" ? "Fewer records" : "Less recorded effort"}</span>
        <i className={mode} />
        <span>{mode === "records" ? "More records" : "More recorded effort"}</span>
      </div>
      {hovered && (
        <div className="map-tooltip">
          <strong>{hovered.target_role === "target" ? "Study-area cell" : "Context cell"}</strong>
          <span>{hovered.records.toLocaleString("en-IN")} records</span>
          <span>{hovered.entities.toLocaleString("en-IN")} named entities</span>
          <span>{hovered.effort_visits.toLocaleString("en-IN")} effort entries</span>
        </div>
      )}
    </div>
  );
}
