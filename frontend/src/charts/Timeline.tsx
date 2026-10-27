import { useMemo, useState } from "react";
import { ParentSize } from "@visx/responsive";
import { AxisBottom, AxisLeft } from "@visx/axis";
import { scaleLinear } from "@visx/scale";
import { TooltipWithBounds, useTooltip } from "@visx/tooltip";
import type { Intervention, TimelineBucket } from "../api/types.ts";

export type Split = "class" | "method" | "representation" | "outcome" | "automation" | "writes";

const SERIES: Record<Split, { key: keyof TimelineBucket; label: string; color: string }[]> = {
  class: [
    { key: "engagement", label: "resource", color: "var(--cyan)" },
    { key: "scanner", label: "scan-shaped", color: "var(--orange)" },
    { key: "operator", label: "operator", color: "var(--magenta)" },
    { key: "other", label: "other", color: "var(--fg-dim)" },
  ],
  method: [
    { key: "m_get", label: "GET", color: "var(--cyan)" },
    { key: "m_head", label: "HEAD", color: "var(--blue)" },
    { key: "m_options", label: "OPTIONS", color: "var(--yellow)" },
    { key: "m_post", label: "POST", color: "var(--orange)" },
    { key: "m_put", label: "PUT", color: "var(--red)" },
    { key: "m_other", label: "other", color: "var(--fg-dim)" },
  ],
  representation: [
    { key: "r_html", label: "html", color: "var(--fg-dim)" },
    { key: "r_text", label: "text", color: "var(--accent)" },
    { key: "r_json", label: "json", color: "var(--cyan)" },
    { key: "r_xml", label: "xml/atom", color: "var(--blue)" },
  ],
  outcome: [
    { key: "s2xx", label: "2xx", color: "var(--accent)" },
    { key: "s3xx", label: "3xx", color: "var(--blue)" },
    { key: "s4xx", label: "4xx", color: "var(--yellow)" },
    { key: "s5xx", label: "5xx", color: "var(--red)" },
  ],
  automation: [
    { key: "low", label: "low", color: "var(--fg-dim)" },
    { key: "medium", label: "medium", color: "var(--yellow)" },
    { key: "high", label: "high", color: "var(--red)" },
  ],
  writes: [
    { key: "writes", label: "writes (http-confirmed)", color: "var(--accent)" },
    { key: "link_writes", label: "of which by link", color: "var(--magenta)" },
  ],
};

export interface Filled {
  ts: number;
  b: TimelineBucket | null;
}

/** Fill every bucket in the window so gaps are visible as zero. */
export function fill(timeline: TimelineBucket[], hours: number, bucket: "hour" | "day"): Filled[] {
  const step = bucket === "day" ? 86400000 : 3600000;
  const end = Math.floor(Date.now() / step) * step;
  const count = bucket === "day" ? Math.ceil(hours / 24) : hours;
  const map = new Map(timeline.map((b) => [Date.parse(b.bucket.replace(" ", "T") + (bucket === "day" ? "T00:00:00Z" : ":00Z")), b]));
  return Array.from({ length: count + 1 }, (_, i) => {
    const ts = end - (count - i) * step;
    return { ts, b: map.get(ts) ?? null };
  });
}

export function Timeline({ timeline, hours, bucket, interventions = [], split: initial = "class" }: {
  timeline: TimelineBucket[];
  hours: number;
  bucket: "hour" | "day";
  interventions?: Intervention[];
  split?: Split;
}) {
  const [split, setSplit] = useState<Split>(initial);
  const series = useMemo(() => fill(timeline, hours, bucket), [timeline, hours, bucket]);
  return (
    <div className="timeline">
      <div className="chart-controls">
        <div className="seg" role="group" aria-label="Stack by">
          {(Object.keys(SERIES) as Split[]).map((k) => (
            <button key={k} className={split === k ? "active" : ""} onClick={() => setSplit(k)} aria-pressed={split === k}>
              {k}
            </button>
          ))}
        </div>
        <div className="legend">
          {SERIES[split].map((s) => (
            <span key={s.key}>
              <i style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
          {interventions.length > 0 && (
            <span>
              <i className="marker" />
              intervention
            </span>
          )}
        </div>
      </div>
      <div className="chart-plot">
        <ParentSize debounceTime={30}>
          {({ width, height }) => <Plot series={series} split={split} width={Math.max(240, width)} height={Math.max(160, height)} bucket={bucket} interventions={interventions} />}
        </ParentSize>
      </div>
    </div>
  );
}

function Plot({ series, split, width, height, bucket, interventions }: { series: Filled[]; split: Split; width: number; height: number; bucket: "hour" | "day"; interventions: Intervention[] }) {
  const { tooltipData, tooltipLeft, tooltipTop, showTooltip, hideTooltip } = useTooltip<Filled>();
  const keys = SERIES[split];
  const left = 44;
  const bottom = 30;
  const totalOf = (f: Filled) => keys.reduce((n, k) => n + Number(f.b?.[k.key] ?? 0), 0);
  const maxY = Math.max(1, ...series.map(totalOf));
  const x = scaleLinear({ domain: [0, series.length - 1], range: [left, width - 10] });
  const y = scaleLinear({ domain: [0, maxY], range: [height - bottom, 10], nice: true });
  const bw = Math.max(1, (width - left - 10) / series.length - 1);
  const step = bucket === "day" ? 86400000 : 3600000;
  const tickIdx = series.map((_, i) => i).filter((i) => (bucket === "day" ? i % Math.max(1, Math.floor(series.length / 8)) === 0 : i % Math.max(1, Math.floor(series.length / 6)) === 0));
  const fmt = (ts: number) => (bucket === "day" ? new Date(ts).toISOString().slice(5, 10) : new Date(ts).toISOString().slice(11, 16));
  const first = series[0]?.ts ?? 0;
  const markers = interventions
    .map((iv) => ({ iv, ts: Date.parse(iv.date + "T12:00:00Z") }))
    .filter((m) => m.ts >= first && m.ts <= (series[series.length - 1]?.ts ?? 0) + step)
    .map((m) => ({ ...m, i: (m.ts - first) / step }));
  return (
    <div className="chart-shell" style={{ width, height }}>
      <svg width={width} height={height} role="img" aria-label={`Requests per ${bucket} stacked by ${split}`}>
        {y
          .ticks(4)
          .filter(Number.isInteger)
          .map((t) => (
            <line key={t} x1={left} x2={width - 10} y1={y(t)} y2={y(t)} stroke="var(--panel-border)" strokeDasharray="2 4" />
          ))}
        <AxisLeft left={left} scale={y} tickValues={y.ticks(4).filter(Number.isInteger)} stroke="var(--panel-border)" tickStroke="var(--panel-border)" tickLabelProps={{ fill: "var(--fg-dim)", fontSize: 9, textAnchor: "end", dy: ".33em", fontFamily: "inherit" }} />
        <AxisBottom top={height - bottom} scale={x} tickValues={tickIdx} tickFormat={(v) => fmt(series[Number(v)]?.ts ?? 0)} stroke="var(--panel-border)" tickStroke="var(--panel-border)" tickLabelProps={{ fill: "var(--fg-dim)", fontSize: 9, textAnchor: "middle", fontFamily: "inherit" }} />
        {series.map((f, i) => {
          let acc = 0;
          return (
            <g key={f.ts}>
              {keys.map((k) => {
                const v = Number(f.b?.[k.key] ?? 0);
                if (!v) return null;
                const y0 = y(acc);
                acc += v;
                const y1 = y(acc);
                return <rect key={k.key} x={x(i) - bw / 2} y={y1} width={bw} height={Math.max(0.5, y0 - y1)} fill={k.color} opacity={tooltipData && tooltipData.ts !== f.ts ? 0.45 : 0.92} className="bar" />;
              })}
            </g>
          );
        })}
        {markers.map((m, idx) => (
          <g key={m.iv.id}>
            <line x1={x(m.i)} x2={x(m.i)} y1={8} y2={height - bottom} stroke="var(--yellow)" strokeDasharray="3 3" />
            <text x={x(m.i) + 3} y={16 + (idx % 6) * 10} fontSize={8} fill="var(--yellow)">
              {m.iv.id}
            </text>
          </g>
        ))}
        {series.map((f, i) => (
          <rect
            key={`h${f.ts}`}
            x={x(i) - bw / 2 - 0.5}
            y={10}
            width={bw + 1}
            height={height - bottom - 10}
            fill="transparent"
            tabIndex={0}
            aria-label={`${fmt(f.ts)}: ${totalOf(f)}`}
            onMouseMove={() => showTooltip({ tooltipData: f, tooltipLeft: Math.min(width - 170, x(i)), tooltipTop: 12 })}
            onFocus={() => showTooltip({ tooltipData: f, tooltipLeft: Math.min(width - 170, x(i)), tooltipTop: 12 })}
            onMouseLeave={hideTooltip}
            onBlur={hideTooltip}
          />
        ))}
      </svg>
      {tooltipData && (
        <TooltipWithBounds left={tooltipLeft} top={tooltipTop} className="tip">
          <strong>{new Date(tooltipData.ts).toISOString().slice(0, bucket === "day" ? 10 : 16).replace("T", " ")}Z</strong>
          <span>{totalOf(tooltipData)} total</span>
          {keys.map((k) => (
            <span key={k.key}>
              <i style={{ background: k.color }} />
              {k.label}: {Number(tooltipData.b?.[k.key] ?? 0)}
            </span>
          ))}
          {tooltipData.b && <span className="dim">{tooltipData.b.clients} fingerprints · {tooltipData.b.sources} sources</span>}
        </TooltipWithBounds>
      )}
    </div>
  );
}
