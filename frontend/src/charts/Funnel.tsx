import type { Stage } from "../api/types.ts";

/** Ordered stages as descending bars; the first stage is the denominator. */
export function Funnel({ stages, eligible }: { stages: Stage[]; eligible: number }) {
  const base = Math.max(1, eligible, stages[0]?.clients ?? 0);
  return (
    <ol className="funnel">
      <li className="funnel-base">
        <span className="funnel-n">{eligible.toLocaleString("en-US")}</span>
        <span className="funnel-label">eligible fingerprints (verified address · resource traffic)</span>
        <div className="funnel-track">
          <i style={{ width: "100%", background: "var(--selection)" }} />
        </div>
      </li>
      {stages.map((s, i) => {
        const prev = i === 0 ? eligible : stages[i - 1].clients;
        return (
          <li key={s.key}>
            <span className="funnel-n">{s.clients.toLocaleString("en-US")}</span>
            <span className="funnel-label">
              <b>{i + 1}</b> {s.label}
              <small>{prev ? `${((s.clients / Math.max(1, prev)) * 100).toFixed(0)}% of previous` : ""}</small>
            </span>
            <div className="funnel-track">
              <i style={{ width: `${(s.clients / base) * 100}%`, background: s.clients ? "var(--accent)" : "transparent" }} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}
