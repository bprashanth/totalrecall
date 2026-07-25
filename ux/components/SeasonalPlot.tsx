"use client";

import type { SeasonalPoint } from "@/lib/types";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const W = 760;
const H = 320;
const LEFT = 44;
const TOP = 28;
const RIGHT = 18;
const BOTTOM = 42;

export function SeasonalPlot({ points }: { points: SeasonalPoint[] }) {
  const x = (index: number) => LEFT + (index / 11) * (W - LEFT - RIGHT);
  const y = (value: number) => TOP + (1 - (value - 0.3) / 0.6) * (H - TOP - BOTTOM);
  const valid = points.filter((point) => point.median !== null);
  const lineSegments: SeasonalPoint[][] = [];
  let segment: SeasonalPoint[] = [];
  for (const point of points) {
    if (point.median === null) {
      if (segment.length) lineSegments.push(segment);
      segment = [];
    } else segment.push(point);
  }
  if (segment.length) lineSegments.push(segment);
  const area = valid
    .map((point) => `${x(point.month - 1)},${y(point.p90 ?? point.median ?? 0)}`)
    .concat(
      [...valid]
        .reverse()
        .map((point) => `${x(point.month - 1)},${y(point.p10 ?? point.median ?? 0)}`),
    )
    .join(" ");
  return (
    <div className="chart-wrap">
      <svg className="seasonal-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Monthly greenness profile">
        {[0.4, 0.6, 0.8].map((tick) => (
          <g key={tick}>
            <line x1={LEFT} y1={y(tick)} x2={W - RIGHT} y2={y(tick)} stroke="#d6d1c4" />
            <text x={LEFT - 10} y={y(tick) + 4} textAnchor="end">
              {tick.toFixed(1)}
            </text>
          </g>
        ))}
        <polygon points={area} fill="#a6c6a5" opacity=".32" />
        {lineSegments.map((items, index) => (
          <polyline
            key={index}
            points={items.map((point) => `${x(point.month - 1)},${y(point.median!)}`).join(" ")}
            fill="none"
            stroke="#17473b"
            strokeWidth="3"
            strokeLinejoin="round"
            strokeLinecap="round"
          />
        ))}
        <line x1={x(5)} y1={y(points[5].median ?? 0.3)} x2={x(7)} y2={y(points[7].median ?? 0.3)} stroke="#8c5f43" strokeDasharray="5 5" />
        {points.map((point, index) => (
          <g key={point.month}>
            <text x={x(index)} y={H - 14} textAnchor="middle">
              {MONTHS[index]}
            </text>
            {point.median !== null ? (
              <circle cx={x(index)} cy={y(point.median)} r="4.5" fill="#f7f4eb" stroke="#17473b" strokeWidth="2.5">
                <title>{`${MONTHS[index]} median ${point.median.toFixed(2)} across ${point.cells} cells`}</title>
              </circle>
            ) : (
              <g>
                <circle cx={x(index)} cy={H / 2} r="11" fill="#f2e2d7" />
                <text x={x(index)} y={H / 2 + 4} textAnchor="middle" className="gap-mark">
                  ×
                </text>
              </g>
            )}
          </g>
        ))}
        <text x={LEFT} y={15} className="axis-title">
          median greenness · shaded band is the 10th–90th percentile
        </text>
      </svg>
      <div className="chart-note">
        <span className="gap-dot" />
        July has no usable cells; October has only 60 of 302.
      </div>
    </div>
  );
}
