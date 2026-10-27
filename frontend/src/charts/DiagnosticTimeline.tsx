import type { DiagnosticsReport } from "../api/types.ts";
import { useEffect, useRef, useState } from "react";

/** Overlapping series, not a stack: probe requests and 404s can be the same requests. */
export function DiagnosticTimeline({ report }: { report: DiagnosticsReport }) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(1000);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new ResizeObserver(() =>
      setWidth(Math.max(240, el.clientWidth)),
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);
  const step = report.hours > 168 ? 86400000 : 3600000;
  const end = Math.floor(Date.now() / step) * step;
  const count = Math.ceil((report.hours * 3600000) / step) + 1;
  const byTime = new Map(
    report.timeline.map((b) => [
      Date.parse(
        b.bucket.replace(" ", "T") +
          (b.bucket.length === 10 ? "T00:00:00Z" : ":00Z"),
      ),
      b,
    ]),
  );
  const data = Array.from({ length: count }, (_, i) => {
    const ts = end - (count - 1 - i) * step;
    return { ts, ...byTime.get(ts) };
  });
  const max = Math.max(1, ...data.map((b) => b.requests ?? 0));
  const plotWidth = width - 68;
  const x = (i: number) => 48 + (i * plotWidth) / Math.max(1, count - 1),
    y = (n: number) => 172 - (n / max) * 148;
  const series = [
    { key: "requests", color: "var(--cyan)", label: "all requests" },
    { key: "probes", color: "var(--orange)", label: "probe-shaped" },
    { key: "missing", color: "var(--yellow)", label: "404s" },
    { key: "server_errors", color: "var(--bright-red)", label: "5xx" },
  ] as const;
  return (
    <div ref={ref} className="diagnostic-chart">
      <div className="legend">
        {series.map((s) => (
          <span key={s.key}>
            <i style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
        <span>overlapping counts · UTC</span>
      </div>
      <svg
        viewBox={`0 0 ${width} 210`}
        height={210}
        role="img"
        aria-label="Requests, probes, 404s and server errors over the selected time window"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((f) => (
          <g key={f}>
            <line
              x1={48}
              x2={width - 20}
              y1={y(max * f)}
              y2={y(max * f)}
              stroke="var(--panel-border)"
              strokeDasharray="3 5"
            />
            <text
              x={40}
              y={y(max * f) + 3}
              textAnchor="end"
              fill="var(--fg-dim)"
              fontSize={10}
            >
              {Math.round(max * f)}
            </text>
          </g>
        ))}
        {series.map((s) => (
          <path
            key={s.key}
            d={data
              .map((b, i) => `${i ? "L" : "M"}${x(i)},${y(b[s.key] ?? 0)}`)
              .join(" ")}
            fill="none"
            stroke={s.color}
            strokeWidth={s.key === "requests" ? 1.5 : 2.2}
            strokeDasharray={s.key === "missing" ? "5 3" : undefined}
          />
        ))}
        {data.map((b, i) => (
          <g key={b.ts}>
            {i % Math.max(1, Math.ceil(count / (width < 500 ? 4 : 8))) ===
              0 && (
              <text
                x={x(i)}
                y={195}
                textAnchor="middle"
                fill="var(--fg-dim)"
                fontSize={10}
              >
                {new Date(b.ts)
                  .toISOString()
                  .slice(
                    report.hours > 168 ? 5 : 11,
                    report.hours > 168 ? 10 : 16,
                  )}
              </text>
            )}
            <rect
              x={x(i) - plotWidth / count / 2}
              y={10}
              width={plotWidth / count}
              height={165}
              fill="transparent"
              tabIndex={0}
            >
              <title>
                {new Date(b.ts).toISOString()}: {b.requests ?? 0} requests,{" "}
                {b.probes ?? 0} probes, {b.missing ?? 0} missing,{" "}
                {b.server_errors ?? 0} server errors
              </title>
            </rect>
          </g>
        ))}
      </svg>
    </div>
  );
}
