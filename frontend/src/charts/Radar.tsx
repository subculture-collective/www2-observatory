import { useState } from "react";
import { useNavigate } from "react-router-dom";
import type { ClientRow } from "../api/types.ts";
import { classColor, relative, short } from "../lib/format.ts";

/**
 * The parody piece that still encodes data: fingerprints as blips on a
 * sweeping radar. Angle = recency (newest at 12 o'clock, older clockwise
 * through the window), radius = log requests, size = writes, colour =
 * dominant traffic class. Same rows as the fingerprint table.
 */
export function Radar({ clients, hours, size = 300 }: { clients: ClientRow[]; hours: number; size?: number }) {
  const [hover, setHover] = useState<ClientRow | null>(null);
  const nav = useNavigate();
  const now = Date.now() / 1000;
  const R = size / 2 - 14;
  const cx = size / 2;
  const maxReq = Math.max(2, ...clients.map((c) => c.requests));
  const dominant = (c: ClientRow) => {
    const e: [string, number][] = [["engagement", c.engagement], ["scanner", c.scanner], ["operator", c.operator], ["other", c.other]];
    return e.sort((a, b) => b[1] - a[1])[0][0];
  };
  const pos = (c: ClientRow) => {
    const age = Math.min(1, Math.max(0, (now - c.last_seen) / (hours * 3600)));
    const a = age * 2 * Math.PI - Math.PI / 2;
    const r = 18 + (Math.log1p(c.requests) / Math.log1p(maxReq)) * (R - 18);
    return { x: cx + Math.cos(a) * r, y: cx + Math.sin(a) * r };
  };
  return (
    <div className="radar-wrap">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="radar" role="img" aria-label="Fingerprints by recency and request volume">
        {[0.25, 0.5, 0.75, 1].map((f) => (
          <circle key={f} cx={cx} cy={cx} r={R * f} fill="none" stroke="var(--panel-border)" strokeWidth={f === 1 ? 1.2 : 0.6} />
        ))}
        <line x1={cx} x2={cx} y1={cx - R} y2={cx + R} stroke="var(--panel-border)" strokeWidth={0.6} />
        <line x1={cx - R} x2={cx + R} y1={cx} y2={cx} stroke="var(--panel-border)" strokeWidth={0.6} />
        <g className="sweep" style={{ transformOrigin: `${cx}px ${cx}px` }}>
          <path d={`M${cx},${cx} L${cx},${cx - R} A${R},${R} 0 0,1 ${cx + R * Math.sin(0.6)},${cx - R * Math.cos(0.6)} Z`} fill="var(--accent)" opacity={0.18} />
          <line x1={cx} y1={cx} x2={cx} y2={cx - R} stroke="var(--accent)" strokeWidth={1.2} />
        </g>
        {clients.map((c) => {
          const p = pos(c);
          const rr = 2.5 + Math.min(6, Math.sqrt(c.writes) * 2.2);
          return (
            <circle
              key={c.client_id}
              cx={p.x}
              cy={p.y}
              r={rr}
              fill={classColor[dominant(c)]}
              opacity={hover && hover !== c ? 0.35 : 0.9}
              className="blip"
              onMouseEnter={() => setHover(c)}
              onMouseLeave={() => setHover(null)}
              onClick={() => nav(`/clients/${c.client_id}`)}
              style={{ cursor: "pointer" }}
            >
              <title>{`${short(c.client_id, 14)} · ${c.requests} req · ${c.writes} writes · ${relative(c.last_seen, now)}`}</title>
            </circle>
          );
        })}
        <text x={cx} y={12} textAnchor="middle" fontSize={8} fill="var(--fg-dim)">
          now
        </text>
        <text x={cx + R + 2} y={cx + 3} fontSize={8} fill="var(--fg-dim)">
          ¼
        </text>
        <text x={cx} y={size - 3} textAnchor="middle" fontSize={8} fill="var(--fg-dim)">
          ½ window
        </text>
      </svg>
      <div className="radar-readout">
        {hover ? (
          <>
            <b>{short(hover.client_id, 16)}</b>
            <span>{hover.requests} requests · {hover.sessions} sessions · {hover.unique_paths} paths</span>
            <span>{hover.writes} writes ({hover.link_writes} by link) · automation max {hover.max_automation}</span>
            <span>last seen {relative(hover.last_seen, now)}</span>
            <span className="dim">{hover.user_agent}</span>
          </>
        ) : (
          <>
            <b>{clients.length} fingerprints</b>
            <span>angle: recency, clockwise from now · radius: requests (log) · size: writes</span>
            <span className="legend">
              <span>
                <i style={{ background: "var(--cyan)" }} />
                resource
              </span>
              <span>
                <i style={{ background: "var(--orange)" }} />
                scan-shaped
              </span>
              <span>
                <i style={{ background: "var(--magenta)" }} />
                operator
              </span>
              <span>
                <i style={{ background: "var(--fg-dim)" }} />
                other
              </span>
            </span>
          </>
        )}
      </div>
    </div>
  );
}
