import type { ReactNode } from "react";

export interface BarItem {
  label: ReactNode;
  value: number;
  color?: string;
  sub?: ReactNode;
  key?: string;
  onClick?: () => void;
}

/** Horizontal bars with value and share of total. */
export function Bars({ items, total, max: maxOverride, showPct = true }: { items: BarItem[]; total?: number; max?: number; showPct?: boolean }) {
  const sum = total ?? items.reduce((n, i) => n + i.value, 0);
  const max = maxOverride ?? Math.max(1, ...items.map((i) => i.value));
  if (!items.length) return <p className="empty">no records in this window</p>;
  return (
    <div className="bars">
      {items.map((it, i) => (
        <div className={`bar-row ${it.onClick ? "clickable" : ""}`} key={it.key ?? i} onClick={it.onClick} role={it.onClick ? "button" : undefined} tabIndex={it.onClick ? 0 : undefined}>
          <div className="bar-label">
            <span>{it.label}</span>
            <strong>
              {it.value.toLocaleString("en-US")}
              {showPct && sum > 0 && <small> {((it.value / sum) * 100).toFixed(1)}%</small>}
            </strong>
          </div>
          <div className="bar-track" aria-hidden="true">
            <i style={{ width: `${(it.value / max) * 100}%`, background: it.color ?? "var(--accent)" }} />
          </div>
          {it.sub && <div className="bar-sub">{it.sub}</div>}
        </div>
      ))}
    </div>
  );
}
