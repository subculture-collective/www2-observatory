import { useEffect, useRef, type ReactNode } from "react";
import { Link } from "react-router-dom";
import type { AccessEvent } from "../api/types.ts";
import { fmtBytes, fmtTime } from "../lib/format.ts";
import { ClassTag, MethodTag, StatusTag } from "./Table.tsx";

/** Right-hand slide-over showing one access record in full. */
export function EventDrawer({ event, onClose }: { event: AccessEvent; onClose: () => void }) {
  const closeRef = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    closeRef.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);
  let signals: string[] = [];
  try {
    const parsed: unknown = JSON.parse(event.signals_json);
    if (Array.isArray(parsed)) signals = parsed.filter((v): v is string => typeof v === "string");
  } catch {
    /* keep malformed rows readable */
  }
  const row = (k: string, v: ReactNode) => (
    <div className="kv" key={k}>
      <span>{k}</span>
      <b>{v || "—"}</b>
    </div>
  );
  return (
    <aside className="drawer" role="dialog" aria-modal="true" aria-label={`Event ${event.id}`}>
      <header className="drawer-head">
        <span>
          event #{event.id} <span className="dim">{fmtTime(event.ts)}</span>
        </span>
        <button ref={closeRef} className="drawer-close" onClick={onClose} aria-label="Close">
          ✕
        </button>
      </header>
      <div className="drawer-body">
        <div className="drawer-line">
          <MethodTag method={event.method} /> <StatusTag status={event.status} /> <ClassTag cls={event.traffic_class} />
          <code className="path">
            {event.path}
            {event.query && <span className="dim">?{event.query}</span>}
          </code>
        </div>
        <h3>request</h3>
        {row("host", event.host)}
        {row("user-agent", event.user_agent)}
        {row("accept", event.accept_header)}
        {row("referer", event.referer)}
        <h3>response</h3>
        {row("content-type", event.content_type)}
        {row("bytes", fmtBytes(event.response_bytes))}
        {row("write object", event.write_object)}
        {row("successful write", event.successful_write ? "yes (HTTP-confirmed)" : "no")}
        {row("write by link", event.link_write ? `${event.link_write}=` : "no")}
        <h3>classification</h3>
        {row("class", event.traffic_class)}
        {row("reason", event.classification_reason)}
        {row("address basis", event.attribution)}
        {row("automation", `${event.automation_score} (${event.automation_level})`)}
        {row(
          "signals",
          signals.length ? (
            <span className="signals">
              {signals.map((s) => (
                <span key={s} className="tag">
                  {s}
                </span>
              ))}
            </span>
          ) : (
            "none"
          ),
        )}
        <h3>pseudonyms (HMAC-SHA256, truncated)</h3>
        {row(
          "client",
          <Link to={`/clients/${event.client_id}`} onClick={onClose}>
            {event.client_id}
          </Link>,
        )}
        {row("source", event.source_id)}
        {row("session", event.session_id)}
        {event.original_client_id && row("original client", event.original_client_id)}
        {row("event key", <span className="mono small">{event.event_key}</span>)}
      </div>
    </aside>
  );
}
