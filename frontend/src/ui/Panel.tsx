import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { D, type Description } from "../lib/descriptions.ts";

/**
 * A bordered panel with a small-caps title, an optional right-side chip, and
 * an "?" control that opens the view's description: what it shows, what it
 * determines, why it is recorded, caveats, and the API source.
 */
export function Panel({ id, title, chip, children, className = "", span, tone }: {
  id?: keyof typeof D;
  title?: string;
  chip?: ReactNode;
  children: ReactNode;
  className?: string;
  span?: 1 | 2 | 3 | 4;
  tone?: "accent" | "cyan" | "orange" | "red" | "magenta";
}) {
  const desc = id ? D[id] : undefined;
  return (
    <section className={`panel ${className} ${span ? `span-${span}` : ""} ${tone ? `tone-${tone}` : ""}`} aria-label={title ?? desc?.title}>
      {(title || desc || chip) && (
        <header className="panel-head">
          <h2>{title ?? desc?.title}</h2>
          <div className="panel-tools">
            {chip && <span className="chip">{chip}</span>}
            {desc && <Info desc={desc} />}
          </div>
        </header>
      )}
      <div className="panel-body">{children}</div>
    </section>
  );
}

export function Info({ desc, inline }: { desc: Description; inline?: boolean }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const labelId = useId();
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);
  return (
    <div className={`info ${inline ? "info-inline" : ""}`} ref={ref}>
      <button className="info-btn" aria-expanded={open} aria-controls={labelId} onClick={() => setOpen((v) => !v)} title="What am I looking at?">
        ?
      </button>
      {open && (
        <div className="info-pop" id={labelId} role="dialog" aria-label={`About ${desc.title}`}>
          <div className="info-title">{desc.title}</div>
          <dl>
            <dt>what this shows</dt>
            <dd>{desc.what}</dd>
            <dt>what it determines</dt>
            <dd>{desc.determines}</dd>
            <dt>why it is recorded</dt>
            <dd>{desc.why}</dd>
            <dt>caveats</dt>
            <dd>
              <ul>
                {desc.caveats.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </dd>
            <dt>source</dt>
            <dd>
              <code>{desc.source}</code>
            </dd>
          </dl>
        </div>
      )}
    </div>
  );
}

export function Empty({ children = "no records in this window" }: { children?: ReactNode }) {
  return <p className="empty">{children}</p>;
}

export function ErrorNote({ error }: { error: string }) {
  if (!error) return null;
  return (
    <p className="error-note" role="alert">
      request failed: {error}. showing the last successful response.
    </p>
  );
}
