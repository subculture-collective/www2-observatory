import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.ts";
import type { ConventionStat, LinkWriteRow, ObjectRow, WriteEvent } from "../api/types.ts";
import { Timeline } from "../charts/Timeline.tsx";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { Stat } from "../ui/Stat.tsx";
import { ClassTag, StatusTag, Table } from "../ui/Table.tsx";
import { useData, useSettings } from "../lib/settings.tsx";
import { fmtShort, fmtTime, n, short } from "../lib/format.ts";

function metaLine(raw: string): string {
  try {
    const m = JSON.parse(raw) as Record<string, unknown>;
    return [m.method, m.request_path, m.status].filter(Boolean).join(" ");
  } catch {
    return raw;
  }
}

export function Writes() {
  const { hours } = useSettings();
  const bucket = hours > 168 ? "day" : "hour";
  const nav = useNavigate();
  const { data, error } = useData(
    async (h) => {
      const [objects, linkWrites, relay, conventions, timeline, summary] = await Promise.all([api.objects(h), api.linkWrites(h, 500), api.writes(100), api.conventions(h, 40), api.timeline(h, bucket), api.summary(h)]);
      return { objects, linkWrites, relay, conventions, timeline, summary };
    },
    [bucket],
  );
  if (!data) return <p className="empty">loading…</p>;
  const s = data.summary;
  const okLinks = data.linkWrites.filter((l) => l.status >= 200 && l.status < 300).length;
  const cross = data.objects.reduce((a, o) => a + o.cross_source_reads, 0);
  return (
    <>
      <ErrorNote error={error} />
      <div className="stats">
        <Stat id="writes" label="successful writes" value={s.writes} previous={s.prev_writes} tone="magenta" sub={`${n(s.write_methods)} write-method requests of any status`} />
        <Stat id="linkWrites" label="writes by link" value={data.linkWrites.length} tone="magenta" sub={`${n(okLinks)} answered 2xx · ${n(data.linkWrites.length - okLinks)} refused or limited`} />
        <Stat id="objects" label="objects written" value={data.objects.length} tone="cyan" sub={`${n(data.objects.filter((o) => o.reads > 0).length)} read afterwards`} />
        <Stat id="return" label="cross-source reads" value={cross} tone="orange" sub="reads of an object by a source other than its last writer" />
        <Stat id="relayStream" label="relay ledger events" value={data.relay.length} tone="dim" sub={data.relay.length ? "synced from the relay's data directory" : "no ledger rows yet; sync runs every minute"} />
      </div>
      <div className="grid">
        <Panel id="timeline" title="Writes over time" span={4} className="depth" chip={`${bucket}ly`}>
          <Timeline timeline={data.timeline} hours={hours} bucket={bucket} split="writes" />
        </Panel>
        <Panel id="objects" span={4} chip={`${data.objects.length} objects`}>
          <Table<ObjectRow>
            rows={data.objects}
            rowKey={(r) => r.path}
            initialSort="last_write"
            max={200}
            onRow={(r) => nav(`/events?search=${encodeURIComponent(r.path)}`)}
            columns={[
              { key: "path", label: "object", render: (r) => <code>{r.path}</code>, sort: (r) => r.path },
              { key: "writes", label: "writes", render: (r) => <>{r.writes}{r.link_writes ? <small className="dim"> ({r.link_writes} link)</small> : null}{r.operator_writes ? <small className="warn"> op {r.operator_writes}</small> : null}</>, sort: (r) => r.writes, align: "right" },
              { key: "stored", label: "stored", render: (r) => (r.stored ? <b className="ok">{r.stored}</b> : <span className="dim" title="no relay ledger confirmation in this window">—</span>), sort: (r) => r.stored, align: "right", title: "confirmations from the relay's own ledger" },
              { key: "writers", label: "writers fp / src", render: (r) => `${r.writers} / ${r.writer_sources}`, sort: (r) => r.writers, align: "right" },
              { key: "first", label: "first write", render: (r) => fmtShort(r.first_write), sort: (r) => r.first_write },
              { key: "last_write", label: "last write", render: (r) => fmtShort(r.last_write), sort: (r) => r.last_write },
              { key: "reads", label: "reads after", render: (r) => (r.reads ? <b>{r.reads}</b> : <span className="dim">0</span>), sort: (r) => r.reads, align: "right" },
              { key: "readers", label: "readers fp / src", render: (r) => `${r.readers} / ${r.reader_sources}`, sort: (r) => r.readers, align: "right" },
              { key: "cross", label: "cross-source", render: (r) => (r.cross_source_reads ? <b className="hot">{r.cross_source_reads}</b> : <span className="dim">0</span>), sort: (r) => r.cross_source_reads, align: "right" },
              { key: "last_read", label: "last read", render: (r) => fmtShort(r.last_read), sort: (r) => r.last_read },
            ]}
            empty="no durable objects were written in this window"
          />
        </Panel>
        <Panel id="linkWrites" span={4} chip={`${data.linkWrites.length} requests`}>
          <Table<LinkWriteRow>
            rows={data.linkWrites}
            rowKey={(r) => String(r.id)}
            initialSort="ts"
            max={300}
            onRow={(r) => nav(`/events?id=${r.id}`)}
            columns={[
              { key: "ts", label: "time (utc)", render: (r) => fmtTime(r.ts), sort: (r) => r.ts, width: "170px" },
              { key: "status", label: "status", render: (r) => <StatusTag status={r.status} />, sort: (r) => r.status },
              { key: "param", label: "param", render: (r) => <span className="tag c-link">{r.link_write}=</span>, sort: (r) => r.link_write },
              { key: "path", label: "target", render: (r) => <code className="path">{r.path}<span className="dim">?{r.query}</span></code>, sort: (r) => r.path },
              { key: "obj", label: "object key", render: (r) => (r.write_object ? <code>{r.write_object}</code> : <span className="dim">none (collection)</span>) },
              { key: "class", label: "class", render: (r) => <ClassTag cls={r.traffic_class} /> },
              { key: "client", label: "fingerprint", render: (r) => <Link to={`/clients/${r.client_id}`} onClick={(e) => e.stopPropagation()}>{short(r.client_id, 14)}</Link>, sort: (r) => r.client_id },
              { key: "ua", label: "user-agent", render: (r) => <span className="ua" title={r.user_agent}>{r.user_agent}</span> },
            ]}
            empty="no writes by link in this window"
          />
        </Panel>
        <Panel id="relayStream" span={2} chip={`${data.relay.length} events`}>
          <Table<WriteEvent>
            rows={data.relay}
            rowKey={(r) => String(r.id)}
            initialSort="ts"
            max={100}
            columns={[
              { key: "ts", label: "time", render: (r) => fmtShort(r.ts), sort: (r) => r.ts },
              { key: "event", label: "kind", render: (r) => <span className="tag">{r.event}</span> },
              { key: "path", label: "path", render: (r) => <code>{r.path}</code> },
              { key: "content", label: "content (scrubbed) / request", render: (r) => <span className="ua" title={r.content || r.metadata_json}>{r.content ? r.content.slice(0, 120) : metaLine(r.metadata_json)}</span> },
              { key: "hash", label: "sha-256", render: (r) => <span className="mono dim">{r.content_hash.slice(0, 12)}</span> },
            ]}
            empty="no relay ledger events in this window. the ledger is synced from Dozor every minute; the access log above is the request-side view."
          />
        </Panel>
        <Panel id="conventions" span={2} chip={`${data.conventions.length} tokens`}>
          <Table<ConventionStat>
            rows={data.conventions}
            rowKey={(r) => r.token}
            initialSort="clients"
            max={40}
            columns={[
              { key: "token", label: "token", render: (r) => <code>{r.token}</code>, sort: (r) => r.token },
              { key: "uses", label: "uses", render: (r) => r.uses, sort: (r) => r.uses, align: "right" },
              { key: "clients", label: "fingerprints", render: (r) => r.clients, sort: (r) => r.clients, align: "right" },
              { key: "first", label: "first", render: (r) => fmtShort(r.first_seen), sort: (r) => r.first_seen },
              { key: "last", label: "last", render: (r) => fmtShort(r.last_seen), sort: (r) => r.last_seen },
            ]}
            empty="needs relay write events; none recorded"
          />
        </Panel>
      </div>
    </>
  );
}
