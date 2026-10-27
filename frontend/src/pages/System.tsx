import { api } from "../api/client.ts";
import { Bars } from "../charts/Bars.tsx";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { Stat } from "../ui/Stat.tsx";
import { useData } from "../lib/settings.tsx";
import { classColor, classLabel, fmtBytes, fmtTime, n, relative } from "../lib/format.ts";

export function System() {
  const { data, error } = useData(async (h) => {
    const [ingest, signals] = await Promise.all([api.ingest(), api.signals(h)]);
    return { ingest, signals };
  });
  if (!data) return <p className="empty">loading…</p>;
  const i = data.ingest;
  const age = i.now - i.last_ts;
  return (
    <>
      <ErrorNote error={error} />
      <div className="stats">
        <Stat id="ingest" label="newest record" value={relative(i.last_ts, i.now)} tone={age < 900 ? "accent" : age < 7200 ? "orange" : "red"} sub={fmtTime(i.last_ts)} />
        <Stat label="oldest record" value={fmtTime(i.first_ts).slice(0, 10)} tone="dim" sub={fmtTime(i.first_ts)} />
        <Stat label="access records" value={i.access_records} sub="one per logged request" />
        <Stat label="relay records" value={i.relay_records} tone="dim" sub={i.relay_records ? "application log mounted" : "relay log not mounted"} />
        <Stat label="database" value={fmtBytes(i.db_size_bytes)} tone="cyan" sub={`sqlite · journal ${i.journal_mode}`} />
      </div>
      <div className="grid">
        <Panel title="Traffic classes, whole database" span={1}>
          <Bars items={i.classes.map((c) => ({ key: c.traffic_class, label: classLabel[c.traffic_class] ?? c.traffic_class, value: c.records, color: classColor[c.traffic_class] ?? "var(--muted)" }))} />
        </Panel>
        <Panel title="Address basis, whole database" span={1}>
          <Bars items={i.attribution.map((a) => ({ key: a.attribution, label: a.attribution, value: a.records, color: a.attribution === "caddy-client-v2" ? "var(--accent)" : "var(--muted)" }))} />
          <p className="note">Only caddy-client-v2 rows carry the address Caddy computed from the trusted proxy path. Older rows keep their original pseudonyms and are excluded from the funnel.</p>
        </Panel>
        <Panel id="signals" span={2}>
          <Bars items={data.signals.map((s) => ({ key: s.signal, label: s.signal, value: s.events, color: "var(--yellow)", sub: `${s.clients} fingerprints` }))} />
        </Panel>
        <Panel title="Ingest offsets" span={2}>
          <table className="data">
            <thead>
              <tr>
                <th>source</th>
                <th>inode</th>
                <th style={{ textAlign: "right" }}>offset</th>
                <th>updated</th>
              </tr>
            </thead>
            <tbody>
              {i.ingest_state.map((s) => (
                <tr key={s.source}>
                  <td>
                    <code>{s.source}</code>
                  </td>
                  <td className="dim">{s.inode}</td>
                  <td style={{ textAlign: "right" }}>{fmtBytes(s.offset)}</td>
                  <td>{relative(s.updated_at, i.now)}</td>
                </tr>
              ))}
              {!i.ingest_state.length && (
                <tr>
                  <td colSpan={4} className="dim">
                    no ingest state yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </Panel>
        <Panel title="Measurement runs" span={2}>
          <table className="data">
            <thead>
              <tr>
                <th>completed</th>
                <th>revision</th>
                <th style={{ textAlign: "right" }}>matched</th>
              </tr>
            </thead>
            <tbody>
              {i.measurement_runs.map((r) => (
                <tr key={r.completed_at}>
                  <td>{fmtTime(r.completed_at)}</td>
                  <td>
                    <code>{r.revision}</code>
                  </td>
                  <td style={{ textAlign: "right" }}>{n(r.matched_records)}</td>
                </tr>
              ))}
              {!i.measurement_runs.length && (
                <tr>
                  <td colSpan={3} className="dim">
                    no reconciliation runs recorded
                  </td>
                </tr>
              )}
            </tbody>
          </table>
          <p className="note">A reconciliation run re-attributes historical rows from retained logs, preserving the original pseudonyms.</p>
        </Panel>
      </div>
    </>
  );
}
