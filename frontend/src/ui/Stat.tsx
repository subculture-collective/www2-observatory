import type { ReactNode } from "react";
import { Info } from "./Panel.tsx";
import { D } from "../lib/descriptions.ts";
import { delta } from "../lib/format.ts";
import { Sparkline } from "../charts/Sparkline.tsx";

/** A headline number with previous-window delta and an optional sparkline. */
export function Stat({ id, label, value, sub, previous, spark, tone = "accent", unit }: {
  id?: keyof typeof D;
  label: string;
  value: number | string;
  sub?: ReactNode;
  previous?: number | null;
  spark?: number[];
  tone?: "accent" | "cyan" | "orange" | "red" | "magenta" | "dim";
  unit?: string;
}) {
  const d = typeof value === "number" && previous !== undefined ? delta(value, previous) : null;
  return (
    <div className={`stat tone-${tone}`}>
      <div className="stat-head">
        <span>{label}</span>
        {id && <Info desc={D[id]} inline />}
      </div>
      <div className="stat-value">
        <strong>{typeof value === "number" ? value.toLocaleString("en-US") : value}</strong>
        {unit && <small>{unit}</small>}
        {d && <em className={`delta ${d.dir}`} title="change against the previous window of equal length">{d.text}</em>}
      </div>
      {spark && spark.length > 1 && <Sparkline values={spark} />}
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}
