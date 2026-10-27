import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { api } from "../api/client.ts";
import type { IngestStats } from "../api/types.ts";
import { fmtBytes, relative, windowLabel } from "../lib/format.ts";
import { useSettings, WINDOWS } from "../lib/settings.tsx";

const NAV = [
  ["/", "overview"],
  ["/traffic", "traffic"],
  ["/diagnostics", "probes & misses"],
  ["/funnel", "funnel"],
  ["/clients", "fingerprints"],
  ["/writes", "writes"],
  ["/events", "events"],
  ["/interventions", "interventions"],
  ["/system", "system"],
  ["/glossary", "glossary"],
] as const;

/** Page frame: top rail with window and refresh controls, nav, content, bottom rail with ingest state. */
export function Shell() {
  const s = useSettings();
  const [ingest, setIngest] = useState<IngestStats | null>(null);
  const [clock, setClock] = useState(() => new Date());
  const [booted, setBooted] = useState(
    () => sessionStorage.getItem("obs_booted") === "1" || !s.motion,
  );

  useEffect(() => {
    api
      .ingest()
      .then(setIngest)
      .catch(() => undefined);
  }, [s.tick]);
  useEffect(() => {
    const id = window.setInterval(() => setClock(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);
  useEffect(() => {
    if (booted) return;
    const id = window.setTimeout(() => {
      sessionStorage.setItem("obs_booted", "1");
      setBooted(true);
    }, 1400);
    return () => window.clearTimeout(id);
  }, [booted]);

  const age = ingest ? ingest.now - ingest.last_ts : null;
  const ageState =
    age === null ? "" : age < 900 ? "ok" : age < 7200 ? "warn" : "bad";

  return (
    <>
      {!booted && (
        <div className="boot" aria-hidden="true">
          <div>
            <b>OBSERVATORY</b>
            <span>loading ingest state // {windowLabel(s.hours)} window</span>
            <i />
          </div>
        </div>
      )}
      <header className="rail top">
        <div className="rail-cell brand">
          <span className="rail-label">observatory</span>
          <b>www2 access logs</b>
        </div>
        <div className="rail-cell">
          <span className="rail-label">window</span>
          <div className="seg" role="group" aria-label="Time window">
            {WINDOWS.map((w) => (
              <button
                key={w.hours}
                className={s.hours === w.hours ? "active" : ""}
                onClick={() => s.setHours(w.hours)}
                aria-pressed={s.hours === w.hours}
              >
                {w.label}
              </button>
            ))}
          </div>
        </div>
        <div className="rail-cell">
          <span className="rail-label">refresh</span>
          <div className="seg" role="group" aria-label="Refresh interval">
            {[0, 15, 30, 60, 300].map((v) => (
              <button
                key={v}
                className={s.refreshSeconds === v ? "active" : ""}
                onClick={() => s.setRefreshSeconds(v)}
                aria-pressed={s.refreshSeconds === v}
              >
                {v === 0 ? "off" : v < 60 ? `${v}s` : `${v / 60}m`}
              </button>
            ))}
            <button onClick={s.refreshNow} title="Refresh now">
              ↻
            </button>
          </div>
        </div>
        <div className="rail-cell">
          <span className="rail-label">display</span>
          <div className="seg">
            <button
              className={s.crt ? "active" : ""}
              onClick={() => s.setCrt(!s.crt)}
              aria-pressed={s.crt}
            >
              scanlines
            </button>
            <span
              className="motion-state"
              title="Follows your system’s Reduce Motion preference"
            >
              motion {s.motion ? "on" : "reduced"}
            </span>
          </div>
        </div>
        <div className="rail-cell clock">
          <span className="rail-label">utc / local {localOffset(clock)}</span>
          <b>
            {clock.toISOString().slice(11, 19)} <small>Z</small>
          </b>
          <span
            className="local-clock"
            title={Intl.DateTimeFormat().resolvedOptions().timeZone}
          >
            {clock.toLocaleTimeString([], { hour12: false })} local
          </span>
        </div>
      </header>
      <nav className="nav" aria-label="Pages">
        {NAV.map(([to, label], i) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <i>{String(i + 1).padStart(2, "0")}</i>
            {label}
          </NavLink>
        ))}
      </nav>
      <main className="content">
        <Outlet />
      </main>
      <footer className="rail bottom">
        <div className="rail-cell">
          <span className="rail-label">newest record</span>
          <b className={ageState}>
            {ingest ? relative(ingest.last_ts, ingest.now) : "…"}
          </b>
        </div>
        <div className="rail-cell">
          <span className="rail-label">records</span>
          <b>
            {ingest ? ingest.access_records.toLocaleString("en-US") : "…"}{" "}
            access ·{" "}
            {ingest ? ingest.relay_records.toLocaleString("en-US") : "…"} relay
          </b>
        </div>
        <div className="rail-cell">
          <span className="rail-label">verified address</span>
          <b>{ingest ? verifiedPct(ingest) : "…"}</b>
        </div>
        <div className="rail-cell">
          <span className="rail-label">database</span>
          <b>
            {ingest
              ? `${fmtBytes(ingest.db_size_bytes)} · ${ingest.journal_mode}`
              : "…"}
          </b>
        </div>
        <div className="rail-cell">
          <span className="rail-label">last refresh</span>
          <b>{new Date(s.lastRefresh).toISOString().slice(11, 19)}Z</b>
        </div>
        <div className="rail-cell">
          <span className="rail-label">identity</span>
          <b>HMAC pseudonyms · raw addresses discarded at ingest</b>
        </div>
      </footer>
    </>
  );
}

function localOffset(date: Date): string {
  const minutes = -date.getTimezoneOffset();
  return `${minutes >= 0 ? "+" : "−"}${String(Math.floor(Math.abs(minutes) / 60)).padStart(2, "0")}:${String(Math.abs(minutes) % 60).padStart(2, "0")}`;
}

function verifiedPct(i: IngestStats): string {
  const total = i.attribution.reduce((n, a) => n + a.records, 0);
  const v =
    i.attribution.find((a) => a.attribution === "caddy-client-v2")?.records ??
    0;
  return total
    ? `${((v / total) * 100).toFixed(1)}% of ${total.toLocaleString("en-US")}`
    : "—";
}
