export function fmtBytes(value: number): string {
  if (!value) return "0 B";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MiB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(2)} GiB`;
}

/** UTC timestamp, seconds resolution. All observatory times are UTC. */
export function fmtTime(ts: number | null | undefined): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toISOString().replace("T", " ").slice(0, 19) + "Z";
}

export function fmtShort(ts: number | null | undefined): string {
  if (!ts) return "—";
  return new Date(ts * 1000).toISOString().slice(5, 16).replace("T", " ");
}

export function relative(ts: number | null | undefined, now = Date.now() / 1000): string {
  if (!ts) return "—";
  const s = Math.max(0, Math.floor(now - ts));
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400) return `${Math.floor(s / 3600)}h ${Math.floor((s % 3600) / 60)}m ago`;
  return `${Math.floor(s / 86400)}d ${Math.floor((s % 86400) / 3600)}h ago`;
}

export function fmtDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${Math.round(seconds % 60)}s`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  return `${Math.floor(seconds / 86400)}d ${Math.floor((seconds % 86400) / 3600)}h`;
}

export function pct(part: number, total: number, digits = 1): string {
  if (!total) return "0%";
  return `${((part / total) * 100).toFixed(digits)}%`;
}

export function n(value: number | null | undefined): string {
  return (value ?? 0).toLocaleString("en-US");
}

/** Signed change between two windows. Returns null when the previous window is empty. */
export function delta(current: number, previous: number | null | undefined): { text: string; dir: "up" | "down" | "flat" } | null {
  if (previous === null || previous === undefined) return null;
  if (previous === 0) return current === 0 ? { text: "±0", dir: "flat" } : { text: "new", dir: "up" };
  const change = ((current - previous) / previous) * 100;
  if (Math.abs(change) < 0.5) return { text: "±0%", dir: "flat" };
  return { text: `${change > 0 ? "+" : ""}${change.toFixed(0)}%`, dir: change > 0 ? "up" : "down" };
}

export function short(id: string, len = 10): string {
  return id.length > len ? id.slice(0, len) : id;
}

export function windowLabel(hours: number): string {
  if (hours % 24 === 0) return `${hours / 24}d`;
  return `${hours}h`;
}

export const classLabel: Record<string, string> = {
  engagement: "resource",
  scanner: "scan-shaped",
  operator: "operator",
  other: "other",
  unclassified: "unclassified",
};

export const classColor: Record<string, string> = {
  engagement: "var(--cyan)",
  scanner: "var(--orange)",
  operator: "var(--magenta)",
  other: "var(--fg-dim)",
  unclassified: "var(--muted)",
};
