import type { AcousticPoint } from "@/lib/types";

function hourNumber(value: string) {
  const match = value.match(/\d+/);
  return match ? Number(match[0]) : 0;
}

export function AcousticPlot({ rows }: { rows: AcousticPoint[] }) {
  const hours = Array.from(new Set(rows.map((row) => row.hour))).sort(
    (a, b) => hourNumber(a) - hourNumber(b),
  );
  const bands = Array.from(new Set(rows.map((row) => row.frequency_band))).sort((a, b) => a - b);
  const max = Math.max(...rows.map((row) => row.value), 0.01);
  const lookup = new Map(rows.map((row) => [`${row.hour}|${row.frequency_band}`, row]));
  const W = 850;
  const H = 350;
  const LEFT = 72;
  const TOP = 26;
  const RIGHT = 18;
  const BOTTOM = 48;
  const cw = (W - LEFT - RIGHT) / hours.length;
  const ch = (H - TOP - BOTTOM) / bands.length;
  return (
    <div className="acoustic-plot">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Acoustic-space use by hour and frequency band">
        <defs>
          <linearGradient id="acousticLegend">
            <stop offset="0%" stopColor="#f1ead9" />
            <stop offset="45%" stopColor="#87aa93" />
            <stop offset="100%" stopColor="#173e34" />
          </linearGradient>
        </defs>
        {bands.map((band, yi) =>
          hours.map((hour, xi) => {
            const row = lookup.get(`${hour}|${band}`);
            const amount = Math.max(0, Math.min(1, (row?.value || 0) / max));
            const light = 92 - amount * 68;
            const saturation = 20 + amount * 30;
            return (
              <rect
                key={`${hour}-${band}`}
                x={LEFT + xi * cw}
                y={TOP + (bands.length - 1 - yi) * ch}
                width={cw + 0.3}
                height={ch + 0.3}
                fill={`hsl(157 ${saturation}% ${light}%)`}
              >
                <title>{`${hour}, ${band.toFixed(1)}–${(band + 1.5).toFixed(1)} kHz: mean ${
                  row?.value.toFixed(3) || "0"
                }`}</title>
              </rect>
            );
          }),
        )}
        {hours.map((hour, index) =>
          index % 3 === 0 ? (
            <text key={hour} x={LEFT + (index + 0.5) * cw} y={H - 20} textAnchor="middle">
              {String(hourNumber(hour)).padStart(2, "0")}h
            </text>
          ) : null,
        )}
        {bands.map((band, index) =>
          index % 3 === 0 ? (
            <text
              key={band}
              x={LEFT - 10}
              y={TOP + (bands.length - index - 0.5) * ch + 4}
              textAnchor="end"
            >
              {band.toFixed(0)}
            </text>
          ) : null,
        )}
        <text x={17} y={H / 2} transform={`rotate(-90 17 ${H / 2})`} textAnchor="middle" className="axis-title">
          frequency band · kHz
        </text>
      </svg>
      <div className="heat-legend">
        <span>Quieter acoustic space</span>
        <i />
        <span>More occupied acoustic space</span>
      </div>
    </div>
  );
}
