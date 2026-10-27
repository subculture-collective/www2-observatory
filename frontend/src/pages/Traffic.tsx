import { useNavigate } from "react-router-dom";
import { api } from "../api/client.ts";
import type { PathRow, UserAgentRow } from "../api/types.ts";
import { Timeline } from "../charts/Timeline.tsx";
import { Heatmap } from "../charts/Heatmap.tsx";
import { Bars } from "../charts/Bars.tsx";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { ClassBar, Meter, Table } from "../ui/Table.tsx";
import { useData, useSettings } from "../lib/settings.tsx";
import { fmtShort, n } from "../lib/format.ts";
import { useState } from "react";

export function Traffic() {
  const { hours } = useSettings();
  const bucket = hours > 168 ? "day" : "hour";
  const nav = useNavigate();
  const [pathSearch, setPathSearch] = useState("");
  const [pathFilter, setPathFilter] = useState("all");
  const { data, error } = useData(
    async (h) => {
      const [
        timeline,
        heatmap,
        paths,
        agents,
        referrers,
        status,
        interventions,
      ] = await Promise.all([
        api.timeline(h, bucket),
        api.heatmap(h),
        api.paths(h, 80),
        api.userAgents(h, 60),
        api.referrers(h, 30),
        api.status(h),
        api
          .interventions()
          .catch(() => ({ version: 0, timezone: "", changes: [] })),
      ]);
      return {
        timeline,
        heatmap,
        paths,
        agents,
        referrers,
        status,
        interventions,
      };
    },
    [bucket],
  );
  if (!data)
    return error ? (
      <ErrorNote error={error} />
    ) : (
      <p className="empty">loading…</p>
    );
  const maxHits = Math.max(1, ...data.paths.map((p) => p.hits));
  const maxUA = Math.max(1, ...data.agents.map((p) => p.hits));
  return (
    <>
      <ErrorNote error={error} />
      <div className="grid">
        <Panel id="timeline" span={4} chip={`${bucket}ly · utc`}>
          <Timeline
            timeline={data.timeline}
            hours={hours}
            bucket={bucket}
            interventions={data.interventions.changes}
            split="method"
          />
        </Panel>
        <Panel id="heatmap" span={3}>
          <Heatmap cells={data.heatmap} />
        </Panel>
        <Panel id="outcomes" span={1} chip="exact status">
          <Bars
            items={data.status.map((s) => ({
              key: String(s.status),
              label: (
                <span className={`tag s${Math.floor(s.status / 100)}`}>
                  {s.status}
                </span>
              ),
              value: s.count,
              color:
                [
                  "",
                  "",
                  "var(--accent)",
                  "var(--blue)",
                  "var(--yellow)",
                  "var(--red)",
                ][Math.floor(s.status / 100)] ?? "var(--fg-dim)",
              onClick: () => nav(`/events?status=${s.status}`),
            }))}
          />
        </Panel>
        <Panel
          id="paths"
          span={4}
          chip={`top ${data.paths.length} paths loaded`}
        >
          <div className="filters">
            <label>
              filter loaded paths
              <input
                className="text-filter"
                value={pathSearch}
                onChange={(e) => setPathSearch(e.target.value)}
                placeholder="path contains…"
              />
            </label>
            <div className="seg" role="group" aria-label="Path subset">
              {["all", "probes", "errors"].map((v) => (
                <button
                  key={v}
                  aria-pressed={pathFilter === v}
                  className={pathFilter === v ? "active" : ""}
                  onClick={() => setPathFilter(v)}
                >
                  {v}
                </button>
              ))}
            </div>
            <a href="/diagnostics">probe families & 404 details →</a>
          </div>
          <Table<PathRow>
            rows={data.paths.filter(
              (p) =>
                p.path.toLowerCase().includes(pathSearch.toLowerCase()) &&
                (pathFilter !== "probes" || p.probes > 0) &&
                (pathFilter !== "errors" || p.errors > 0),
            )}
            rowKey={(r) => r.path}
            initialSort="hits"
            max={60}
            onRow={(r) => nav(`/events?search=${encodeURIComponent(r.path)}`)}
            columns={[
              {
                key: "path",
                label: "path",
                render: (r) => <code>{r.path}</code>,
                sort: (r) => r.path,
              },
              {
                key: "hits",
                label: "hits",
                render: (r) => <Meter value={r.hits} max={maxHits} />,
                sort: (r) => r.hits,
                width: "180px",
              },
              {
                key: "clients",
                label: "fingerprints",
                render: (r) => n(r.clients),
                sort: (r) => r.clients,
                align: "right",
              },
              {
                key: "class",
                label: "class mix",
                render: (r) => <ClassBar {...r} />,
                width: "120px",
              },
              {
                key: "probes",
                label: "probes",
                render: (r) => (
                  <span className={r.probes ? "warn" : "dim"}>
                    {n(r.probes)}
                  </span>
                ),
                sort: (r) => r.probes,
                align: "right",
              },
              {
                key: "methods",
                label: "methods",
                render: (r) => <span className="dim">{methods(r)}</span>,
              },
              {
                key: "writes",
                label: "writes",
                render: (r) =>
                  r.writes ? (
                    <b>
                      {r.writes}
                      {r.link_writes ? (
                        <small className="dim"> ({r.link_writes} link)</small>
                      ) : null}
                    </b>
                  ) : (
                    <span className="dim">0</span>
                  ),
                sort: (r) => r.writes,
                align: "right",
              },
              {
                key: "errors",
                label: "errors",
                render: (r) =>
                  r.errors ? (
                    <span className="warn">{r.errors}</span>
                  ) : (
                    <span className="dim">0</span>
                  ),
                sort: (r) => r.errors,
                align: "right",
              },
              {
                key: "auto",
                label: "avg auto",
                render: (r) => r.avg_automation,
                sort: (r) => r.avg_automation,
                align: "right",
                title: "average automation score",
              },
            ]}
          />
        </Panel>
        <Panel id="agents" span={3} chip={`${data.agents.length} agents`}>
          <Table<UserAgentRow>
            rows={data.agents}
            rowKey={(r) => r.user_agent}
            initialSort="hits"
            max={40}
            onRow={(r) =>
              nav(
                `/events?search=${encodeURIComponent(r.user_agent.slice(0, 40))}`,
              )
            }
            columns={[
              {
                key: "ua",
                label: "user-agent",
                render: (r) => (
                  <span className="ua" title={r.user_agent}>
                    {r.user_agent || "(empty)"}
                  </span>
                ),
                sort: (r) => r.user_agent,
              },
              {
                key: "hits",
                label: "hits",
                render: (r) => <Meter value={r.hits} max={maxUA} />,
                sort: (r) => r.hits,
                width: "150px",
              },
              {
                key: "clients",
                label: "fp / src",
                render: (r) => `${r.clients} / ${r.sources}`,
                sort: (r) => r.clients,
                align: "right",
                title: "fingerprints / sources",
              },
              {
                key: "class",
                label: "class mix",
                render: (r) => <ClassBar {...r} />,
                width: "110px",
              },
              {
                key: "probes",
                label: "probes",
                render: (r) => n(r.probes),
                sort: (r) => r.probes,
                align: "right",
              },
              {
                key: "rep",
                label: "html·text·json·xml",
                render: (r) => (
                  <span className="dim">
                    {r.r_html}·{r.r_text}·{r.r_json}·{r.r_xml}
                  </span>
                ),
              },
              {
                key: "writes",
                label: "writes",
                render: (r) =>
                  r.writes ? <b>{r.writes}</b> : <span className="dim">0</span>,
                sort: (r) => r.writes,
                align: "right",
              },
              {
                key: "auto",
                label: "auto",
                render: (r) => r.avg_auto,
                sort: (r) => r.avg_auto,
                align: "right",
              },
              {
                key: "span",
                label: "first · last",
                render: (r) => (
                  <span className="dim">
                    {fmtShort(r.first_seen)} · {fmtShort(r.last_seen)}
                  </span>
                ),
                sort: (r) => r.last_seen,
              },
            ]}
          />
        </Panel>
        <Panel
          id="entrances"
          title="Referring hosts"
          span={1}
          chip="referer header"
        >
          <Bars
            items={data.referrers.map((r) => ({
              key: r.referer_host,
              label: r.referer_host,
              value: r.hits,
              color: "var(--cyan)",
              sub: `${r.clients} fingerprints`,
            }))}
          />
        </Panel>
      </div>
    </>
  );
}

function methods(r: PathRow): string {
  return [
    ["GET", r.m_get],
    ["HEAD", r.m_head],
    ["OPT", r.m_options],
    ["POST", r.m_post],
    ["PUT", r.m_put],
  ]
    .filter(([, v]) => (v as number) > 0)
    .map(([k, v]) => `${k} ${v}`)
    .join(" · ");
}
