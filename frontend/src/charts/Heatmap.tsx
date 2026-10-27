import { useState } from "react";
import type { HeatCell } from "../api/types.ts";

const DAYS = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"];
type Metric = "total" | "engagement" | "scanner" | "high" | "writes" | "clients";

export function Heatmap({ cells }: { cells: HeatCell[] }) {
  const [metric, setMetric] = useState<Metric>("total");
  const grid = new Map(cells.map((c) => [`${c.dow}-${c.hour}`, c]));
  const max = Math.max(1, ...cells.map((c) => c[metric]));
  const color = (v: number) => {
    if (!v) return "transparent";
    const t = Math.log1p(v) / Math.log1p(max);
    return `color-mix(in srgb, var(--accent) ${Math.round(12 + t * 88)}%, transparent)`;
  };
  return (
    <div className="heat">
      <div className="chart-controls">
        <div className="seg" role="group" aria-label="Metric">
          {(["total", "engagement", "scanner", "high", "writes", "clients"] as Metric[]).map((m) => (
            <button key={m} className={metric === m ? "active" : ""} onClick={() => setMetric(m)} aria-pressed={metric === m}>
              {m === "engagement" ? "resource" : m === "scanner" ? "scan" : m}
            </button>
          ))}
        </div>
        <span className="legend">
          <span className="dim">max {max.toLocaleString("en-US")} · utc</span>
        </span>
      </div>
      <div className="heat-grid" role="table" aria-label={`Requests by weekday and hour, metric ${metric}`}>
        <div className="heat-corner" />
        {Array.from({ length: 24 }, (_, h) => (
          <div key={h} className="heat-h">
            {h % 3 === 0 ? String(h).padStart(2, "0") : ""}
          </div>
        ))}
        {DAYS.map((d, dow) => (
          <div key={d} className="heat-row" role="row">
            <div className="heat-d">{d}</div>
            {Array.from({ length: 24 }, (_, h) => {
              const c = grid.get(`${dow}-${h}`);
              const v = c ? c[metric] : 0;
              return <div key={h} className="heat-c" role="cell" style={{ background: color(v) }} title={`${d} ${String(h).padStart(2, "0")}:00Z · ${v} ${metric}${c ? ` · ${c.clients} fingerprints` : ""}`} />;
            })}
          </div>
        ))}
      </div>
    </div>
  );
}
