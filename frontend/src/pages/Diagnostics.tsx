import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.ts";
import type {
  DiagnosticSource,
  MissingPath,
  ProbeFamily,
  DiagnosticsReport,
} from "../api/types.ts";
import { useData } from "../lib/settings.tsx";
import { familyLabels, kindLabels, kindColor } from "../lib/diagnostics.ts";
import { fmtShort, n, pct, short, fmtDuration } from "../lib/format.ts";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { Table, StatusTag, Meter } from "../ui/Table.tsx";
import { Stat } from "../ui/Stat.tsx";
import { Bars } from "../charts/Bars.tsx";
import { DiagnosticTimeline } from "../charts/DiagnosticTimeline.tsx";

export function Diagnostics() {
  const nav = useNavigate();
  const { data: r, error } = useData((h) => api.diagnostics(h));
  if (!r)
    return error ? (
      <ErrorNote error={error} />
    ) : (
      <p className="empty">loading request diagnostics…</p>
    );
  const s = r.summary;
  const sourceMax = Math.max(1, ...r.sources.map((v) => v.requests));
  return (
    <>
      <ErrorNote error={error} />
      <div className="page-intro">
        <div>
          <span className="eyebrow">request forensics // {r.revision}</span>
          <h1>Probes, misses & response health</h1>
        </div>
        <Link to="/events?status=404">inspect 404 events →</Link>
      </div>
      <p className="note">
        Request patterns are evidence of a probe-shaped request, not proof of an
        attacker, a vulnerability, or a successful exploit. User-agent names are
        unverified claims. Source IDs group observed addresses; shared networks
        can combine clients.
      </p>
      {s.pending > 0 && (
        <p className="error-note">
          {n(s.pending)} rows await diagnostic classification. Category counts
          are incomplete until the service backfill completes.
        </p>
      )}
      <div className="stats diagnostic-stats">
        <Stat
          label="probe-shaped requests"
          value={s.probes}
          tone="orange"
          sub={`${pct(s.probes, s.requests)} of all requests · ${r.families.length} families`}
        />
        <Stat
          label="404 responses"
          value={s.missing}
          tone="orange"
          sub={`${pct(s.probe_404, s.missing)} matched probe patterns`}
        />
        <Stat
          label="resource / asset misses"
          value={s.resource_misses + s.asset_misses}
          tone="cyan"
          sub={`${s.resource_misses} public paths · ${s.asset_misses} assets · inspect links`}
        />
        <Stat
          label="probe requests answered 2xx"
          value={s.probe_2xx}
          tone={s.probe_2xx ? "orange" : "dim"}
          sub="review response content; a 2xx is not proof of exposure"
        />
        <Stat
          label="server errors"
          value={s.server_errors}
          tone={s.server_errors ? "red" : "accent"}
          sub={`${s.rate_limited} rate-limited · ${s.rejected} size/content refusals`}
        />
        <Stat
          label="largest source share"
          value={pct(r.sources[0]?.requests ?? 0, s.requests)}
          tone="magenta"
          sub={`${n(r.sources[0]?.requests)} requests · ${n(s.sources)} sources overall`}
        />
      </div>
      <div className="grid">
        <Panel
          id="diagnostics"
          title="Probe / response activity"
          span={3}
          chip={r.hours > 168 ? "daily" : "hourly"}
        >
          <DiagnosticTimeline report={r} />
        </Panel>
        <Panel title="Request diagnostics" span={1} chip="click to inspect">
          <Bars
            total={s.requests}
            items={r.kinds.map((k) => ({
              key: k.kind,
              label: kindLabels[k.kind] ?? k.kind,
              value: k.requests,
              color: kindColor(k.kind),
              sub: `${k.sources} sources · ${k.missing} missing`,
              onClick: () => nav(`/events?kind=${k.kind}`),
            }))}
          />
        </Panel>
        <Panel title="Probe families" span={4} chip="path and query patterns">
          <Table<ProbeFamily>
            rows={r.families}
            rowKey={(v) => v.family}
            initialSort="requests"
            onRow={(v) => nav(`/events?family=${v.family}`)}
            columns={[
              {
                key: "family",
                label: "family",
                render: (v) => (
                  <b className="warn">{familyLabels[v.family] ?? v.family}</b>
                ),
                sort: (v) => v.family,
              },
              {
                key: "requests",
                label: "requests",
                render: (v) => n(v.requests),
                sort: (v) => v.requests,
                align: "right",
              },
              {
                key: "sources",
                label: "sources / fingerprints",
                render: (v) => `${v.sources} / ${v.clients}`,
                sort: (v) => v.sources,
                align: "right",
              },
              {
                key: "paths",
                label: "unique paths",
                render: (v) => v.paths,
                sort: (v) => v.paths,
                align: "right",
              },
              {
                key: "missing",
                label: "404",
                render: (v) => v.missing,
                sort: (v) => v.missing,
                align: "right",
              },
              {
                key: "ok",
                label: "2xx · review",
                render: (v) => (
                  <span className={v.responses_2xx ? "warn" : "dim"}>
                    {v.responses_2xx}
                  </span>
                ),
                sort: (v) => v.responses_2xx,
                align: "right",
              },
              {
                key: "5xx",
                label: "5xx",
                render: (v) => v.server_errors,
                sort: (v) => v.server_errors,
                align: "right",
              },
              {
                key: "seen",
                label: "last seen UTC",
                render: (v) => fmtShort(v.last_seen),
                sort: (v) => v.last_seen,
              },
            ]}
          />
        </Panel>
        <Panel
          title="404 paths & possible broken links"
          span={4}
          chip="top 80 combinations"
        >
          <p className="note">
            An internal referrer can help locate a broken link, but referrer
            headers can be forged. Resource misses also include guessed IDs and
            typos. Click a row for the exact path and diagnostic.
          </p>
          <Table<MissingPath>
            rows={r.misses}
            rowKey={(v) => v.path + v.kind}
            initialSort="requests"
            max={20}
            onRow={(v) =>
              nav(
                `/events?status=404&path=${encodeURIComponent(v.path)}&kind=${v.kind}`,
              )
            }
            columns={[
              {
                key: "path",
                label: "path",
                render: (v) => <code className="path">{v.path}</code>,
                sort: (v) => v.path,
              },
              {
                key: "kind",
                label: "diagnostic",
                render: (v) => (
                  <span style={{ color: kindColor(v.kind) }}>
                    {kindLabels[v.kind] ?? v.kind}
                  </span>
                ),
                sort: (v) => v.kind,
              },
              {
                key: "family",
                label: "family",
                render: (v) => familyLabels[v.family] ?? "—",
                sort: (v) => v.family,
              },
              {
                key: "requests",
                label: "requests",
                render: (v) => n(v.requests),
                sort: (v) => v.requests,
                align: "right",
              },
              {
                key: "sources",
                label: "sources",
                render: (v) => v.sources,
                sort: (v) => v.sources,
                align: "right",
              },
              {
                key: "ref",
                label: "internal referrer",
                render: (v) => (
                  <span className={v.internal_referrers ? "warn" : "dim"}>
                    {v.internal_referrers}
                  </span>
                ),
                sort: (v) => v.internal_referrers,
                align: "right",
              },
              {
                key: "seen",
                label: "last seen UTC",
                render: (v) => fmtShort(v.last_seen),
                sort: (v) => v.last_seen,
              },
            ]}
          />
        </Panel>
        <Panel
          title="Source concentration & user-agent churn"
          span={3}
          chip="top 30 observed sources"
        >
          <Table<DiagnosticSource>
            rows={r.sources}
            rowKey={(v) => v.source_id}
            initialSort="requests"
            max={15}
            onRow={(v) => nav(`/events?client=${v.source_id}`)}
            columns={[
              {
                key: "source",
                label: "source",
                render: (v) => <code>{short(v.source_id, 18)}</code>,
                sort: (v) => v.source_id,
              },
              {
                key: "requests",
                label: "requests",
                render: (v) => <Meter value={v.requests} max={sourceMax} />,
                sort: (v) => v.requests,
              },
              {
                key: "share",
                label: "window share",
                render: (v) => pct(v.requests, s.requests),
                sort: (v) => v.requests,
                align: "right",
              },
              {
                key: "agents",
                label: "UA / fingerprints",
                render: (v) => `${v.user_agents} / ${v.clients}`,
                sort: (v) => v.user_agents,
                align: "right",
                title:
                  "Many user-agent labels on one source can indicate rotation, a shared proxy, or a test client; no authenticated identity.",
              },
              {
                key: "paths",
                label: "paths",
                render: (v) => v.paths,
                sort: (v) => v.paths,
                align: "right",
              },
              {
                key: "probes",
                label: "probes / 404",
                render: (v) => `${v.probes} / ${v.missing}`,
                sort: (v) => v.probes,
                align: "right",
              },
              {
                key: "span",
                label: "active span",
                render: (v) => fmtDuration(v.last_seen - v.first_seen),
                sort: (v) => v.last_seen - v.first_seen,
              },
            ]}
          />
        </Panel>
        <Panel title="Read these outcomes separately" span={1}>
          <dl className="readout-defs">
            <dt>404</dt>
            <dd>Missing resource. Usually correct for a probe.</dd>
            <dt>2xx probe</dt>
            <dd>Inspect the response; it may be a generic page.</dd>
            <dt>5xx</dt>
            <dd>
              Service or upstream error. Prioritise repeated failures on real
              routes.
            </dd>
            <dt>429</dt>
            <dd>Rate limit answered the request.</dd>
            <dt>413 / 414 / 422</dt>
            <dd>Body size, URL size, or content validation refusal.</dd>
            <dt>304</dt>
            <dd>
              Cache validation, not an error. {n(s.revalidated)} in this window.
            </dd>
          </dl>
        </Panel>
        <Panel
          title="Review queue · newest 30"
          span={4}
          chip="2xx probes · 5xx · resource / asset misses"
        >
          <Table<DiagnosticsReport["review"][number]>
            rows={r.review}
            rowKey={(v) => String(v.id)}
            initialSort="ts"
            onRow={(v) => nav(`/events?id=${v.id}`)}
            columns={[
              {
                key: "ts",
                label: "time UTC",
                render: (v) => fmtShort(v.ts),
                sort: (v) => v.ts,
              },
              {
                key: "status",
                label: "status",
                render: (v) => <StatusTag status={v.status} />,
                sort: (v) => v.status,
              },
              {
                key: "path",
                label: "path",
                render: (v) => <code className="path">{v.path}</code>,
              },
              {
                key: "why",
                label: "diagnostic evidence",
                render: (v) => (
                  <span className="wrap">{v.diagnostic_reason}</span>
                ),
              },
              {
                key: "source",
                label: "source",
                render: (v) => <code>{short(v.source_id, 16)}</code>,
              },
            ]}
          />
        </Panel>
      </div>
    </>
  );
}
