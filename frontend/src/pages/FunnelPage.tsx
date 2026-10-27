import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.ts";
import type { Evidence } from "../api/types.ts";
import { Funnel } from "../charts/Funnel.tsx";
import { Bars } from "../charts/Bars.tsx";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { Stat } from "../ui/Stat.tsx";
import { Table } from "../ui/Table.tsx";
import { useData } from "../lib/settings.tsx";
import { classColor, classLabel, fmtTime, n, short } from "../lib/format.ts";

const STAGE_DEFS: [string, string][] = [
  ["1 discovery", "GET or HEAD of /, /robots.txt, /sitemap.xml, or /index.txt."],
  ["2 capability inspection", "GET of /help.txt or /README.TXT, or OPTIONS on a relay resource."],
  ["3 structured/text retrieval", "A GET whose response was served as JSON, text/plain, or Atom."],
  ["4 successful write", "PUT to a note with 2xx; POST that redirected to a created object; wall or guestbook POST success; a write by link answered 2xx."],
  ["5 later object retrieval", "GET (2xx) of the client's own last-written object at least one session gap (30 min) after writing."],
];

export function FunnelPage() {
  const nav = useNavigate();
  const { data: e, error } = useData((h) => api.experiment(h));
  if (!e) return <p className="empty">loading…</p>;
  const total = Object.values(e.traffic).reduce((a, b) => a + b, 0);
  return (
    <>
      <ErrorNote error={error} />
      <div className="stats">
        <Stat label="eligible fingerprints" value={e.eligible_clients} tone="cyan" sub="verified address · resource traffic" />
        <Stat id="writes" label="successful writes" value={e.successful_writes} tone="magenta" sub="HTTP-confirmed, eligible traffic" />
        <Stat id="return" label="returning fingerprints" value={e.returning_clients} sub="read own object after a session gap" />
        <Stat id="return" label="cross-source reads" value={e.cross_source_reads} tone="orange" sub="2xx GET of a written object by another source" />
        <Stat label="address basis" value={`${n(e.attribution["caddy-client-v2"] ?? 0)}`} tone="dim" sub={`verified of ${n(Object.values(e.attribution).reduce((a, b) => a + b, 0))} records · rev ${e.revision}`} />
      </div>
      <div className="grid">
        <Panel id="funnel" span={3} className="depth">
          <Funnel stages={e.stages} eligible={e.eligible_clients} />
          <dl className="defs">
            {STAGE_DEFS.map(([k, v]) => (
              <div key={k}>
                <dt>{k}</dt>
                <dd>{v}</dd>
              </div>
            ))}
          </dl>
        </Panel>
        <Panel title="Traffic classes in window" span={1} chip={`${n(total)} records`}>
          <Bars
            items={Object.entries(e.traffic)
              .sort((a, b) => b[1] - a[1])
              .map(([k, v]) => ({ key: k, label: classLabel[k] ?? k, value: v, color: classColor[k] ?? "var(--muted)", onClick: () => nav(`/events?class=${k}`) }))}
          />
          <p className="note">Only <b>resource</b> records with a verified address are eligible. The others are counted here and excluded from the funnel.</p>
          <h3>address basis</h3>
          <Bars items={Object.entries(e.attribution).map(([k, v]) => ({ key: k, label: k, value: v, color: k === "caddy-client-v2" ? "var(--accent)" : "var(--muted)" }))} />
        </Panel>
        <Panel title="Milestone evidence" span={4} chip={`${e.evidence.length} records (first 100)`}>
          <Table<Evidence>
            rows={e.evidence}
            rowKey={(r) => `${r.event_id}-${r.stage}`}
            initialSort="ts"
            onRow={(r) => nav(`/clients/${r.client}`)}
            columns={[
              { key: "ts", label: "time (utc)", render: (r) => fmtTime(r.ts), sort: (r) => r.ts, width: "170px" },
              { key: "stage", label: "stage", render: (r) => <span className={`tag stage-${r.stage}`}>{r.stage}</span>, sort: (r) => e.stages.findIndex((s) => s.key === r.stage) },
              { key: "path", label: "resource", render: (r) => <code>{r.path}</code>, sort: (r) => r.path },
              { key: "client", label: "fingerprint", render: (r) => <Link to={`/clients/${r.client}`}>{short(r.client, 18)}</Link>, sort: (r) => r.client },
              { key: "event", label: "event", render: (r) => <Link to={`/events?id=${r.event_id}`}>#{r.event_id}</Link>, sort: (r) => r.event_id, align: "right" },
            ]}
            empty="no ordered milestones in this window"
          />
        </Panel>
        <Panel title="Measurement rules" span={4}>
          <ul className="notes">
            {e.notes.map((note) => (
              <li key={note}>{note}</li>
            ))}
          </ul>
        </Panel>
      </div>
    </>
  );
}
