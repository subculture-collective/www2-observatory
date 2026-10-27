import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.ts";
import type { ClientRow } from "../api/types.ts";
import { Radar } from "../charts/Radar.tsx";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { ClassBar, Meter, Table } from "../ui/Table.tsx";
import { useData, useSettings } from "../lib/settings.tsx";
import { fmtDuration, fmtShort, n, relative, short } from "../lib/format.ts";

const FILTERS = [
  ["", "all"],
  ["engagement", "resource"],
  ["writers", "wrote"],
  ["verified", "verified addr"],
  ["scanner", "scan-shaped"],
  ["probes", "probe-shaped"],
  ["operator", "operator"],
  ["other", "other"],
];

export function Clients() {
  const { hours } = useSettings();
  const nav = useNavigate();
  const [cls, setCls] = useState("");
  const { data, error } = useData((h) => api.clients(h, 1000, cls), [cls]);
  if (!data)
    return error ? (
      <ErrorNote error={error} />
    ) : (
      <p className="empty">loading…</p>
    );
  const maxReq = Math.max(1, ...data.map((c) => c.requests));
  const now = Date.now() / 1000;
  return (
    <>
      <ErrorNote error={error} />
      <div className="grid">
        <Panel
          id="clientsTable"
          span={3}
          chip={`${n(data.length)} fingerprints`}
        >
          <div className="chart-controls">
            <div className="seg" role="group" aria-label="Filter">
              {FILTERS.map(([k, label]) => (
                <button
                  key={k}
                  className={cls === k ? "active" : ""}
                  onClick={() => setCls(k)}
                  aria-pressed={cls === k}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <Table<ClientRow>
            rows={data}
            rowKey={(r) => r.client_id}
            initialSort="last_seen"
            max={300}
            onRow={(r) => nav(`/clients/${r.client_id}`)}
            columns={[
              {
                key: "client",
                label: "fingerprint",
                render: (r) => (
                  <Link
                    to={`/clients/${r.client_id}`}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {short(r.client_id, 14)}
                  </Link>
                ),
                sort: (r) => r.client_id,
              },
              {
                key: "last_seen",
                label: "last seen",
                render: (r) => (
                  <span title={fmtShort(r.last_seen)}>
                    {relative(r.last_seen, now)}
                  </span>
                ),
                sort: (r) => r.last_seen,
              },
              {
                key: "span",
                label: "active span",
                render: (r) => (
                  <span className="dim">
                    {fmtDuration(r.last_seen - r.first_seen)}
                  </span>
                ),
                sort: (r) => r.last_seen - r.first_seen,
              },
              {
                key: "requests",
                label: "requests",
                render: (r) => <Meter value={r.requests} max={maxReq} />,
                sort: (r) => r.requests,
                width: "150px",
              },
              {
                key: "sessions",
                label: "sess / paths",
                render: (r) => `${r.sessions} / ${r.unique_paths}`,
                sort: (r) => r.sessions,
                align: "right",
              },
              {
                key: "class",
                label: "class mix",
                render: (r) => <ClassBar {...r} />,
                width: "110px",
              },
              {
                key: "probes",
                label: "probe requests",
                render: (r) => (
                  <span className={r.probes ? "warn" : "dim"}>
                    {n(r.probes)}
                  </span>
                ),
                sort: (r) => r.probes,
                align: "right",
              },
              {
                key: "rep",
                label: "html·text·json",
                render: (r) => (
                  <span className="dim">
                    {r.r_html}·{r.r_text}·{r.r_json}
                  </span>
                ),
                sort: (r) => (r.r_text ?? 0) + (r.r_json ?? 0),
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
                key: "auto",
                label: "auto max",
                render: (r) => (
                  <span className={r.max_automation >= 6 ? "warn" : ""}>
                    {r.max_automation}
                  </span>
                ),
                sort: (r) => r.max_automation,
                align: "right",
              },
              {
                key: "attr",
                label: "addr",
                render: (r) => (
                  <span
                    className={`tag ${r.attribution === "caddy-client-v2" ? "ok" : "dim"}`}
                  >
                    {r.attribution === "caddy-client-v2"
                      ? "verified"
                      : r.attribution}
                  </span>
                ),
                sort: (r) => r.attribution,
              },
              {
                key: "ua",
                label: "user-agent",
                render: (r) => (
                  <span className="ua" title={r.user_agent}>
                    {r.user_agent}
                  </span>
                ),
              },
            ]}
          />
        </Panel>
        <Panel id="radar" span={1}>
          <Radar clients={data} hours={hours} size={260} />
        </Panel>
      </div>
    </>
  );
}
