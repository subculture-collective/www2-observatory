import { useState } from "react";

export interface Slice {
  label: string;
  value: number;
  color: string;
}

/** Ring chart with the total in the middle and a hover readout. Pure SVG. */
export function Donut({ slices, size = 150, label }: { slices: Slice[]; size?: number; label?: string }) {
  const [hover, setHover] = useState<Slice | null>(null);
  const total = slices.reduce((n, s) => n + s.value, 0);
  const r = size / 2 - 8;
  const c = 2 * Math.PI * r;
  let offset = 0;
  return (
    <div className="donut">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} role="img" aria-label={label}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--panel-lighter)" strokeWidth={12} />
        {total > 0 &&
          slices
            .filter((s) => s.value > 0)
            .map((s) => {
              const len = (s.value / total) * c;
              const el = (
                <circle
                  key={s.label}
                  cx={size / 2}
                  cy={size / 2}
                  r={r}
                  fill="none"
                  stroke={s.color}
                  strokeWidth={hover?.label === s.label ? 16 : 12}
                  strokeDasharray={`${len} ${c - len}`}
                  strokeDashoffset={-offset}
                  transform={`rotate(-90 ${size / 2} ${size / 2})`}
                  className="donut-seg"
                  onMouseEnter={() => setHover(s)}
                  onMouseLeave={() => setHover(null)}
                />
              );
              offset += len;
              return el;
            })}
        <text x="50%" y="47%" textAnchor="middle" fill="var(--fg)" fontSize={size / 8} fontWeight={700}>
          {(hover ? hover.value : total).toLocaleString("en-US")}
        </text>
        <text x="50%" y="60%" textAnchor="middle" fill="var(--fg-dim)" fontSize={size / 15}>
          {hover ? `${hover.label} · ${total ? ((hover.value / total) * 100).toFixed(1) : 0}%` : (label ?? "total")}
        </text>
      </svg>
      <ul className="donut-legend">
        {slices.map((s) => (
          <li key={s.label} onMouseEnter={() => setHover(s)} onMouseLeave={() => setHover(null)}>
            <i style={{ background: s.color }} />
            <span>{s.label}</span>
            <b>{s.value.toLocaleString("en-US")}</b>
          </li>
        ))}
      </ul>
    </div>
  );
}
