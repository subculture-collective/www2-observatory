import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client.ts";
import type { AccessEvent, SessionRow } from "../api/types.ts";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { Stat } from "../ui/Stat.tsx";
import { ClassBar, ClassTag, MethodTag, StatusTag, Table } from "../ui/Table.tsx";
import { EventDrawer } from "../ui/EventDrawer.tsx";
import { useData } from "../lib/settings.tsx";
import { fmtDuration, fmtShort, fmtTime, n, relative } from "../lib/format.ts";

export function ClientDetailPage() {
  const { id = "" } = useParams();
  const [selected, setSelected] = useState<AccessEvent | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const { data, error } = useData(() => api.client(id, 500), [id]);
  if (error && !data) return <p className="error-note">{error.includes("404") ? "no records for this fingerprint" : error}</p>;
  if (!data) return <p className="empty">loading…</p>;
  const s = data.summary;
  const reached = new Set(data.stages.map((x) => x.stage));
  return (
    <>
      <ErrorNote error={error} />
      <p className="crumbs">
        <Link to="/clients">fingerprints</Link> / <code>{id}</code> <span className="dim">source {s.source_id}</span>
      </p>
      <div className="stats">
        <Stat label="requests" value={s.requests} sub={`${n(s.sessions)} sessions · ${n(s.unique_paths)} distinct paths · ${n(s.errors)} errors`} />
        <Stat label="first seen" value={fmtShort(s.first_seen)} tone="dim" sub={relative(s.first_seen)} />
        <Stat label="last seen" value={fmtShort(s.last_seen)} tone="dim" sub={`${relative(s.last_seen)} · span ${fmtDuration(s.last_seen - s.first_seen)}`} />
        <Stat label="writes" value={s.writes} tone="magenta" sub={`${n(s.link_writes)} by link · ${n(s.write_methods)} write-method requests`} />
        <Stat label="representations" value={`${s.r_html ?? 0}·${s.r_text ?? 0}·${s.r_json ?? 0}`} tone="cyan" sub="html · text · json (2xx)" />
        <Stat label="automation" value={s.max_automation} tone={s.max_automation >= 6 ? "orange" : "dim"} sub={`max score · avg ${s.avg_automation} · ${s.attribution === "caddy-client-v2" ? "verified address" : s.attribution}`} />
      </div>
      <div className="grid">
        <Panel id="funnel" title="Funnel stages reached (90 days, strict order)" span={2}>
          <ol className="stage-list">
            {data.stage_labels.map((st, i) => {
              const ev = data.stages.find((x) => x.stage === st.key);
              return (
                <li key={st.key} className={reached.has(st.key) ? "reached" : ""}>
                  <b>{i + 1}</b>
                  <span>{st.label}</span>
                  {ev ? (
                    <span className="dim">
                      {fmtTime(ev.ts)} · <code>{ev.path}</code> · <Link to={`/events?id=${ev.event_id}`}>#{ev.event_id}</Link>
                    </span>
                  ) : (
                    <span className="dim">not reached</span>
                  )}
                </li>
              );
            })}
          </ol>
        </Panel>
        <Panel title="Class mix and agents" span={1}>
          <ClassBar {...s} />
          <p className="dim small">
            resource {s.engagement} · scan-shaped {s.scanner} · operator {s.operator} · other {s.other}
          </p>
          <ul className="plain">
            {data.user_agents.map((u) => (
              <li key={u.user_agent}>
                <b>{u.hits}</b> <span className="ua" title={u.user_agent}>{u.user_agent || "(empty)"}</span>
              </li>
            ))}
          </ul>
        </Panel>
        <Panel id="objects" title="Objects written" span={1}>
          {data.objects.length ? (
            <ul className="plain">
              {data.objects.map((o) => (
                <li key={o.path}>
                  <Link to={`/events?search=${encodeURIComponent(o.path)}`}>
                    <code>{o.path}</code>
                  </Link>
                  <span className="dim">
                    {" "}
                    {o.writes}× · last {fmtShort(o.last_write)}
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="empty">no durable objects written</p>
          )}
        </Panel>
        <Panel id="sessions" span={4} chip={`${data.sessions.length} sessions`}>
          <Table<SessionRow>
            rows={data.sessions}
            rowKey={(r) => r.session_id}
            initialSort="started"
            onRow={(r) => setOpen(open === r.session_id ? null : r.session_id)}
            columns={[
              { key: "started", label: "started (utc)", render: (r) => fmtTime(r.started), sort: (r) => r.started, width: "170px" },
              { key: "dur", label: "duration", render: (r) => fmtDuration(r.ended - r.started), sort: (r) => r.ended - r.started },
              { key: "req", label: "requests", render: (r) => r.requests, sort: (r) => r.requests, align: "right" },
              { key: "paths", label: "paths", render: (r) => r.unique_paths, sort: (r) => r.unique_paths, align: "right" },
              { key: "writes", label: "writes", render: (r) => (r.writes ? <b>{r.writes}</b> : <span className="dim">0</span>), sort: (r) => r.writes, align: "right" },
              { key: "auto", label: "auto max", render: (r) => r.max_automation, sort: (r) => r.max_automation, align: "right" },
              {
                key: "trail",
                label: "trail (method path?query status)",
                render: (r) => (
                  <pre className={`trail ${open === r.session_id ? "open" : ""}`}>{open === r.session_id ? r.trail : r.trail.split("\n").slice(0, 3).join("\n") + (r.trail.split("\n").length > 3 ? `\n… ${r.trail.split("\n").length - 3} more (click)` : "")}</pre>
                ),
              },
            ]}
          />
        </Panel>
        <Panel id="events" span={4} chip={`newest ${data.events.length}`}>
          <Table<AccessEvent>
            rows={data.events}
            rowKey={(r) => String(r.id)}
            initialSort="ts"
            max={500}
            onRow={setSelected}
            columns={[
              { key: "ts", label: "time (utc)", render: (r) => fmtTime(r.ts), sort: (r) => r.ts, width: "170px" },
              { key: "class", label: "class", render: (r) => <ClassTag cls={r.traffic_class} /> },
              { key: "status", label: "status", render: (r) => <StatusTag status={r.status} />, sort: (r) => r.status },
              { key: "method", label: "method", render: (r) => <MethodTag method={r.method} /> },
              { key: "path", label: "path", render: (r) => <code className="path">{r.path}{r.query && <span className="dim">?{r.query}</span>}</code>, sort: (r) => r.path },
              { key: "ct", label: "served", render: (r) => <span className="dim">{r.content_type.split(";")[0]}</span> },
              { key: "w", label: "write", render: (r) => (r.successful_write ? <span className="tag c-write">{r.link_write ? `link ${r.link_write}=` : "write"}</span> : r.link_write ? <span className="tag c-link">link {r.link_write}= ✕</span> : null) },
              { key: "auto", label: "auto", render: (r) => r.automation_score, sort: (r) => r.automation_score, align: "right" },
            ]}
          />
        </Panel>
      </div>
      {selected && <EventDrawer event={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
