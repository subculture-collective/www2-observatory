import { useMemo, useState, type ReactNode } from "react";

export interface Column<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
  sort?: (row: T) => number | string;
  align?: "left" | "right";
  width?: string;
  title?: string;
}

/** Sortable, dense data table. Click a header to sort; click again to flip. */
export function Table<T>({
  rows,
  columns,
  rowKey,
  onRow,
  initialSort,
  initialDesc = true,
  max,
  empty = "no rows",
}: {
  rows: T[];
  columns: Column<T>[];
  rowKey: (row: T) => string;
  onRow?: (row: T) => void;
  initialSort?: string;
  initialDesc?: boolean;
  max?: number;
  empty?: string;
}) {
  const [sortKey, setSortKey] = useState(initialSort ?? "");
  const [desc, setDesc] = useState(initialDesc);
  const [visible, setVisible] = useState(max ?? Infinity);
  const sorted = useMemo(() => {
    const col = columns.find((c) => c.key === sortKey);
    if (!col?.sort) return rows;
    const s = col.sort;
    return [...rows].sort((a, b) => {
      const x = s(a);
      const y = s(b);
      const r =
        typeof x === "number" && typeof y === "number"
          ? x - y
          : String(x).localeCompare(String(y));
      return desc ? -r : r;
    });
  }, [rows, columns, sortKey, desc]);
  const shown = sorted.slice(0, visible);
  if (!rows.length) return <p className="empty">{empty}</p>;
  return (
    <div className="table-wrap">
      <table className="data">
        <thead>
          <tr>
            {columns.map((c) => (
              <th
                key={c.key}
                style={{ width: c.width, textAlign: c.align ?? "left" }}
                title={c.title}
                aria-sort={
                  sortKey === c.key
                    ? desc
                      ? "descending"
                      : "ascending"
                    : "none"
                }
              >
                {c.sort ? (
                  <button
                    className={`sort ${sortKey === c.key ? "active" : ""}`}
                    onClick={() => {
                      if (sortKey === c.key) setDesc((d) => !d);
                      else {
                        setSortKey(c.key);
                        setDesc(true);
                      }
                    }}
                  >
                    {c.label}
                    {sortKey === c.key && (
                      <span aria-hidden="true">{desc ? " ▾" : " ▴"}</span>
                    )}
                  </button>
                ) : (
                  c.label
                )}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {shown.map((row) => (
            <tr
              key={rowKey(row)}
              className={onRow ? "clickable" : ""}
              onClick={onRow ? () => onRow(row) : undefined}
              tabIndex={onRow ? 0 : undefined}
              onKeyDown={
                onRow
                  ? (e) => {
                      if (
                        e.target === e.currentTarget &&
                        (e.key === "Enter" || e.key === " ")
                      ) {
                        e.preventDefault();
                        onRow(row);
                      }
                    }
                  : undefined
              }
            >
              {columns.map((c) => (
                <td key={c.key} style={{ textAlign: c.align ?? "left" }}>
                  {c.render(row)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {max && rows.length > max && (
        <div className="table-more">
          showing {Math.min(visible, rows.length)} of {rows.length} loaded rows{" "}
          <div className="seg">
            {visible < rows.length && (
              <button onClick={() => setVisible((v) => v + max)}>
                show {Math.min(max, rows.length - visible)} more
              </button>
            )}
            {visible > max && (
              <button onClick={() => setVisible(max)}>collapse</button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** Small inline meter used inside table cells. */
export function Meter({
  value,
  max,
  color = "var(--accent)",
  label,
}: {
  value: number;
  max: number;
  color?: string;
  label?: string;
}) {
  const w = max > 0 ? Math.max(0, Math.min(100, (value / max) * 100)) : 0;
  return (
    <span className="meter" title={label}>
      <i style={{ width: `${w}%`, background: color }} />
      <b>{value.toLocaleString("en-US")}</b>
    </span>
  );
}

/** Class mix as a tiny stacked bar. */
export function ClassBar({
  engagement,
  scanner,
  operator,
  other,
}: {
  engagement: number;
  scanner: number;
  operator: number;
  other: number;
}) {
  const total = engagement + scanner + operator + other || 1;
  const seg = (v: number, c: string, t: string) =>
    v > 0 ? (
      <i
        key={t}
        style={{ width: `${(v / total) * 100}%`, background: c }}
        title={`${t}: ${v}`}
      />
    ) : null;
  return (
    <span
      className="classbar"
      aria-label={`resource ${engagement}, scan-shaped ${scanner}, operator ${operator}, other ${other}`}
    >
      {seg(engagement, "var(--cyan)", "resource")}
      {seg(scanner, "var(--orange)", "scan-shaped")}
      {seg(operator, "var(--magenta)", "operator")}
      {seg(other, "var(--fg-dim)", "other")}
    </span>
  );
}

export function Tag({
  children,
  tone = "",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={`tag ${tone}`}>{children}</span>;
}

export function StatusTag({ status }: { status: number }) {
  return <Tag tone={`s${Math.floor(status / 100)}`}>{status}</Tag>;
}

export function ClassTag({ cls }: { cls: string }) {
  const label: Record<string, string> = {
    engagement: "RES",
    scanner: "SCAN",
    operator: "OP",
    other: "OTHER",
    unclassified: "—",
  };
  return <Tag tone={`c-${cls}`}>{label[cls] ?? cls}</Tag>;
}

export function MethodTag({ method }: { method: string }) {
  return <Tag tone={`m-${method.toLowerCase()}`}>{method}</Tag>;
}
