import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client.ts";
import type { AccessEvent } from "../api/types.ts";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { ClassTag, MethodTag, StatusTag, Table } from "../ui/Table.tsx";
import { EventDrawer } from "../ui/EventDrawer.tsx";
import { useData, useSettings } from "../lib/settings.tsx";
import { fmtBytes, fmtTime, short } from "../lib/format.ts";
import {
  familyLabels,
  familyColor,
  kindLabels,
  kindColor,
} from "../lib/diagnostics.ts";

const CLASSES = ["", "engagement", "scanner", "operator", "other"];
const METHODS = [
  "",
  "GET",
  "HEAD",
  "OPTIONS",
  "POST",
  "PUT",
  "PATCH",
  "DELETE",
];
const LEVELS = ["", "high", "medium", "low"];
const STATUSES = [
  "",
  "2",
  "3",
  "4",
  "5",
  "200",
  "204",
  "301",
  "303",
  "304",
  "400",
  "403",
  "404",
  "405",
  "413",
  "414",
  "422",
  "429",
  "500",
  "502",
  "503",
];

export function Events() {
  const { hours } = useSettings();
  const [params, setParams] = useSearchParams();
  const get = (k: string) => params.get(k) ?? "";
  const set = (k: string, v: string) => {
    const next = new URLSearchParams(params);
    if (v) next.set(k, v);
    else next.delete(k);
    next.delete("id");
    setParams(next, { replace: true });
  };
  const [selected, setSelected] = useState<AccessEvent | null>(null);
  const [search, setSearch] = useState(get("search"));
  useEffect(() => setSearch(get("search")), [params]); // eslint-disable-line react-hooks/exhaustive-deps
  const limit = Number(get("limit") || 200);
  const { data, error } = useData(
    (hours) =>
      api.recent({
        hours,
        limit,
        class: get("class"),
        method: get("method"),
        level: get("level"),
        status: get("status") ? Number(get("status")) : undefined,
        client: get("client"),
        search: get("search"),
        link: get("link") ? 1 : undefined,
        kind: get("kind"),
        family: get("family"),
        path: get("path"),
        since: get("since") ? Number(get("since")) : undefined,
        until: get("until") ? Number(get("until")) : undefined,
      }),
    [params.toString()],
  );
  const id = get("id");
  useEffect(() => {
    if (!id) return;
    api
      .event(Number(id))
      .then(setSelected)
      .catch(() => undefined);
  }, [id]);

  const seg = (
    k: string,
    opts: string[],
    label: (o: string) => string = (o) => o || "all",
  ) => (
    <div className="seg" role="group" aria-label={k}>
      {opts.map((o) => (
        <button
          key={o}
          className={get(k) === o ? "active" : ""}
          onClick={() => set(k, o)}
          aria-pressed={get(k) === o}
        >
          {label(o)}
        </button>
      ))}
    </div>
  );
  return (
    <>
      <ErrorNote error={error} />
      <Panel
        id="events"
        span={4}
        chip={`${data?.length ?? 0} results · newest ${limit} matching requests`}
      >
        <div className="filters">
          <label htmlFor="event-kind">
            request diagnostic
            <select
              id="event-kind"
              value={get("kind")}
              onChange={(e) => set("kind", e.target.value)}
            >
              <option value="">all request shapes</option>
              {Object.entries(kindLabels).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label htmlFor="probe-family">
            probe family
            <select
              id="probe-family"
              value={get("family")}
              onChange={(e) => set("family", e.target.value)}
            >
              <option value="">all families</option>
              {Object.entries(familyLabels).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            research class{" "}
            {seg(
              "class",
              CLASSES,
              (o) =>
                ({
                  "": "all",
                  engagement: "resource",
                  scanner: "scan",
                  operator: "op",
                  other: "other",
                })[o] ?? o,
            )}
          </label>
          <label>method {seg("method", METHODS)}</label>
          <label>automation {seg("level", LEVELS)}</label>
          <label>
            status{" "}
            {seg("status", STATUSES, (o) =>
              o.length === 1 ? `${o}xx` : o || "all",
            )}
          </label>
          <label>
            writes
            <div className="seg">
              <button
                className={get("link") ? "active" : ""}
                onClick={() => set("link", get("link") ? "" : "1")}
                aria-pressed={!!get("link")}
              >
                by link only
              </button>
            </div>
          </label>
          <label>
            limit
            <div className="seg">
              {["100", "200", "500", "1000"].map((o) => (
                <button
                  key={o}
                  className={String(limit) === o ? "active" : ""}
                  onClick={() => set("limit", o)}
                >
                  {o}
                </button>
              ))}
            </div>
          </label>
          <form
            className="search"
            onSubmit={(e) => {
              e.preventDefault();
              set("search", search);
            }}
          >
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="path, query, user-agent, fingerprint, referer"
              aria-label="Search"
            />
            <button type="submit">search</button>
            {get("client") && (
              <button type="button" onClick={() => set("client", "")}>
                clear fingerprint {short(get("client"), 10)}
              </button>
            )}
          </form>
          {get("path") && (
            <button className="filter-chip" onClick={() => set("path", "")}>
              exact path: {get("path")} ×
            </button>
          )}
          {get("since") && (
            <button
              className="filter-chip"
              onClick={() => {
                const next = new URLSearchParams(params);
                next.delete("since");
                next.delete("until");
                setParams(next, { replace: true });
              }}
            >
              replay bucket: {fmtTime(Number(get("since")))} →{" "}
              {fmtTime(Number(get("until")))} ×
            </button>
          )}
          <button
            className="filter-chip"
            onClick={() => setParams({}, { replace: true })}
          >
            clear all filters
          </button>
          <button
            className="filter-chip"
            onClick={() => {
              void api
                .downloadExport({
                  hours,
                  limit,
                  kind: get("kind"),
                  family: get("family"),
                  path: get("path"),
                  since: get("since") ? Number(get("since")) : undefined,
                  until: get("until") ? Number(get("until")) : undefined,
                  class: get("class"),
                  method: get("method"),
                  level: get("level"),
                  status: get("status") ? Number(get("status")) : undefined,
                  client: get("client"),
                  search: get("search"),
                  link: get("link") ? 1 : undefined,
                })
                .catch((e) => window.alert(`Export failed: ${String(e)}`));
            }}
          >
            export filtered NDJSON
          </button>
        </div>
        {data && (
          <Table<AccessEvent>
            rows={data}
            rowKey={(r) => String(r.id)}
            initialSort="ts"
            onRow={setSelected}
            columns={[
              {
                key: "id",
                label: "#",
                render: (r) => <span className="dim">{r.id}</span>,
                sort: (r) => r.id,
                width: "70px",
              },
              {
                key: "ts",
                label: "time (utc)",
                render: (r) => fmtTime(r.ts),
                sort: (r) => r.ts,
                width: "170px",
              },
              {
                key: "class",
                label: "class",
                render: (r) => <ClassTag cls={r.traffic_class} />,
                sort: (r) => r.traffic_class,
              },
              {
                key: "diagnostic",
                label: "request diagnostic",
                render: (r) => (
                  <span
                    style={{ color: kindColor(r.request_kind) }}
                    title={r.diagnostic_reason}
                  >
                    {kindLabels[r.request_kind] ?? r.request_kind}
                    {r.probe_family && (
                      <small
                        className="block"
                        style={{ color: familyColor(r.probe_family) }}
                      >
                        {familyLabels[r.probe_family] ?? r.probe_family}
                      </small>
                    )}
                  </span>
                ),
                sort: (r) => r.request_kind,
              },
              {
                key: "status",
                label: "status",
                render: (r) => <StatusTag status={r.status} />,
                sort: (r) => r.status,
              },
              {
                key: "method",
                label: "method",
                render: (r) => <MethodTag method={r.method} />,
                sort: (r) => r.method,
              },
              {
                key: "path",
                label: "path",
                render: (r) => (
                  <code className="path">
                    {r.path}
                    {r.query && <span className="dim">?{r.query}</span>}
                  </code>
                ),
                sort: (r) => r.path,
              },
              {
                key: "ct",
                label: "served",
                render: (r) => (
                  <span className="dim">
                    {r.content_type.split(";")[0] || "—"}
                  </span>
                ),
                sort: (r) => r.content_type,
              },
              {
                key: "bytes",
                label: "bytes",
                render: (r) => (
                  <span className="dim">{fmtBytes(r.response_bytes)}</span>
                ),
                sort: (r) => r.response_bytes,
                align: "right",
              },
              {
                key: "w",
                label: "write",
                render: (r) =>
                  r.successful_write ? (
                    <span className="tag c-write">
                      {r.link_write ? `link ${r.link_write}=` : "write"}
                    </span>
                  ) : r.link_write ? (
                    <span className="tag c-link">link ✕</span>
                  ) : null,
                sort: (r) => r.successful_write,
              },
              {
                key: "auto",
                label: "auto",
                render: (r) => (
                  <span
                    className={r.automation_level === "high" ? "warn" : "dim"}
                  >
                    {r.automation_score}
                  </span>
                ),
                sort: (r) => r.automation_score,
                align: "right",
              },
              {
                key: "client",
                label: "fingerprint",
                render: (r) => (
                  <Link
                    to={`/clients/${r.client_id}`}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {short(r.client_id, 12)}
                  </Link>
                ),
                sort: (r) => r.client_id,
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
            empty="no events match these filters"
          />
        )}
      </Panel>
      {selected && (
        <EventDrawer
          event={selected}
          onClose={() => {
            setSelected(null);
            if (id) set("id", "");
          }}
        />
      )}
    </>
  );
}
