"use client";

import { useMemo, useState } from "react";
import type { RestorationPoint } from "@/lib/types";

const METRICS = [
  ["regeneration_tree_species_richness", "Young-tree richness"],
  ["regeneration_old_growth_species_richness", "Old-growth recruits"],
  ["adult_tree_species_richness", "Adult-tree richness"],
  ["adult_basal_area_per_ha", "Basal area"],
] as const;

const COLOURS: Record<string, string> = {
  Fragment: "#315c4c",
  Restoration: "#d58b57",
  Reference: "#6d8f9d",
  Plantation: "#9c7c58",
};

function hash(value: string) {
  let number = 0;
  for (const char of value) number = (number * 31 + char.charCodeAt(0)) >>> 0;
  return number;
}

export function RestorationPlot({ rows }: { rows: RestorationPoint[] }) {
  const [metric, setMetric] = useState(METRICS[0][0]);
  const selected = useMemo(() => rows.filter((row) => row.metric === metric), [rows, metric]);
  const categories = Array.from(new Set(selected.map((row) => row.comparison_class || "Unlabelled")));
  const max = Math.max(...selected.map((row) => row.value), 1);
  const medians = Object.fromEntries(
    categories.map((category) => {
      const values = selected
        .filter((row) => (row.comparison_class || "Unlabelled") === category)
        .map((row) => row.value)
        .sort((a, b) => a - b);
      return [category, values[Math.floor(values.length / 2)] || 0];
    }),
  );
  const W = 850;
  const H = 340;
  const LEFT = 135;
  const RIGHT = 38;
  const TOP = 40;
  const rowHeight = (H - TOP - 25) / Math.max(categories.length, 1);
  const x = (value: number) => LEFT + (value / max) * (W - LEFT - RIGHT);

  return (
    <div className="restoration-plot">
      <div className="metric-tabs" aria-label="Restoration measure">
        {METRICS.map(([id, label]) => (
          <button key={id} className={metric === id ? "active" : ""} onClick={() => setMetric(id)}>
            {label}
          </button>
        ))}
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Plot indicators by source-reported comparison class">
        {categories.map((category, index) => {
          const cy = TOP + index * rowHeight + rowHeight / 2;
          const items = selected.filter(
            (row) => (row.comparison_class || "Unlabelled") === category,
          );
          return (
            <g key={category}>
              <line x1={LEFT} y1={cy} x2={W - RIGHT} y2={cy} stroke="#ddd8ca" />
              <text x={LEFT - 15} y={cy + 5} textAnchor="end" className="category-label">
                {category}
              </text>
              {items.map((row) => {
                const jitter = ((hash(row.plot_id) % 100) / 100 - 0.5) * Math.min(32, rowHeight * 0.6);
                return (
                  <circle
                    key={`${row.plot_id}-${row.value}`}
                    cx={x(row.value)}
                    cy={cy + jitter}
                    r="4.2"
                    fill={COLOURS[category] || "#7a8179"}
                    opacity=".5"
                  >
                    <title>{`${row.plot_id}: ${row.value.toFixed(1)} ${row.unit}`}</title>
                  </circle>
                );
              })}
              <line
                x1={x(medians[category])}
                y1={cy - rowHeight * 0.33}
                x2={x(medians[category])}
                y2={cy + rowHeight * 0.33}
                stroke={COLOURS[category] || "#273b34"}
                strokeWidth="4"
              />
              <text x={x(medians[category]) + 7} y={cy - rowHeight * 0.28} className="median-label">
                median {medians[category].toFixed(1)}
              </text>
            </g>
          );
        })}
        <line x1={LEFT} y1={H - 22} x2={W - RIGHT} y2={H - 22} stroke="#897f6e" />
        {[0, 0.25, 0.5, 0.75, 1].map((part) => (
          <g key={part}>
            <line x1={x(max * part)} y1={H - 22} x2={x(max * part)} y2={H - 17} stroke="#897f6e" />
            <text x={x(max * part)} y={H - 3} textAnchor="middle">
              {(max * part).toFixed(max < 20 ? 1 : 0)}
            </text>
          </g>
        ))}
      </svg>
      <p className="plot-footnote">
        Each dot is one source-linked plot. The short dark stroke is the group median. Categories
        are those reported by the source, not treatments assigned by this interface.
      </p>
    </div>
  );
}
