import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client.ts";
import type { AccessEvent } from "../api/types.ts";
import { Panel, ErrorNote } from "../ui/Panel.tsx";
import { ClassTag, MethodTag, StatusTag, Table } from "../ui/Table.tsx";
import { EventDrawer } from "../ui/EventDrawer.tsx";
import { useData } from "../lib/settings.tsx";
import { fmtBytes, fmtTime, short } from "../lib/format.ts";

const CLASSES = ["", "engagement", "scanner", "operator", "other"];
const METHODS = ["", "GET", "HEAD", "OPTIONS", "POST", "PUT"];
const LEVELS = ["", "high", "medium", "low"];
const STATUSES = ["", "2", "3", "4", "5", "200", "204", "303", "304", "404", "405", "422", "429", "500"];

export function Events() {
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
    () =>
      api.recent({
        limit,
        class: get("class"),
        method: get("method"),
        level: get("level"),
        status: get("status") ? Number(get("status")) : undefined,
        client: get("client"),
        search: get("search"),
        link: get("link") ? 1 : undefined,
      }),
    [params.toString()],
  );
  const id = get("id");
  useEffect(() => {
    if (!id) return;
    api.event(Number(id)).then(setSelected).catch(() => undefined);
  }, [id]);

  const seg = (k: string, opts: string[], label: (o: string) => string = (o) => o || "all") => (
    <div className="seg" role="group" aria-label={k}>
      {opts.map((o) => (
        <button key={o} className={get(k) === o ? "active" : ""} onClick={() => set(k, o)} aria-pressed={get(k) === o}>
          {label(o)}
        </button>
      ))}
    </div>
  );
  return (
    <>
      <ErrorNote error={error} />
      <Panel id="events" span={4} chip={<a href={api.exportUrl(500)} download>export newest 500 as ndjson</a>}>
        <div className="filters">
          <label>
            class {seg("class", CLASSES, (o) => ({ "": "all", engagement: "resource", scanner: "scan", operator: "op", other: "other" })[o] ?? o)}
          </label>
          <label>method {seg("method", METHODS)}</label>
          <label>automation {seg("level", LEVELS)}</label>
          <label>status {seg("status", STATUSES, (o) => (o.length === 1 ? `${o}xx` : o || "all"))}</label>
          <label>
            writes
            <div className="seg">
              <button className={get("link") ? "active" : ""} onClick={() => set("link", get("link") ? "" : "1")} aria-pressed={!!get("link")}>
                by link only
              </button>
            </div>
          </label>
          <label>
            limit
            <div className="seg">
              {["100", "200", "500", "1000"].map((o) => (
                <button key={o} className={String(limit) === o ? "active" : ""} onClick={() => set("limit", o)}>
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
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="path, query, user-agent, fingerprint, referer" aria-label="Search" />
            <button type="submit">search</button>
            {get("client") && (
              <button type="button" onClick={() => set("client", "")}>
                clear fingerprint {short(get("client"), 10)}
              </button>
            )}
          </form>
        </div>
        {data && (
          <Table<AccessEvent>
            rows={data}
            rowKey={(r) => String(r.id)}
            initialSort="ts"
            onRow={setSelected}
            columns={[
              { key: "id", label: "#", render: (r) => <span className="dim">{r.id}</span>, sort: (r) => r.id, width: "70px" },
              { key: "ts", label: "time (utc)", render: (r) => fmtTime(r.ts), sort: (r) => r.ts, width: "170px" },
              { key: "class", label: "class", render: (r) => <ClassTag cls={r.traffic_class} />, sort: (r) => r.traffic_class },
              { key: "status", label: "status", render: (r) => <StatusTag status={r.status} />, sort: (r) => r.status },
              { key: "method", label: "method", render: (r) => <MethodTag method={r.method} />, sort: (r) => r.method },
              { key: "path", label: "path", render: (r) => <code className="path">{r.path}{r.query && <span className="dim">?{r.query}</span>}</code>, sort: (r) => r.path },
              { key: "ct", label: "served", render: (r) => <span className="dim">{r.content_type.split(";")[0] || "—"}</span>, sort: (r) => r.content_type },
              { key: "bytes", label: "bytes", render: (r) => <span className="dim">{fmtBytes(r.response_bytes)}</span>, sort: (r) => r.response_bytes, align: "right" },
              { key: "w", label: "write", render: (r) => (r.successful_write ? <span className="tag c-write">{r.link_write ? `link ${r.link_write}=` : "write"}</span> : r.link_write ? <span className="tag c-link">link ✕</span> : null), sort: (r) => r.successful_write },
              { key: "auto", label: "auto", render: (r) => <span className={r.automation_level === "high" ? "warn" : "dim"}>{r.automation_score}</span>, sort: (r) => r.automation_score, align: "right" },
              { key: "client", label: "fingerprint", render: (r) => <Link to={`/clients/${r.client_id}`} onClick={(e) => e.stopPropagation()}>{short(r.client_id, 12)}</Link>, sort: (r) => r.client_id },
              { key: "ua", label: "user-agent", render: (r) => <span className="ua" title={r.user_agent}>{r.user_agent}</span> },
            ]}
            empty="no events match these filters"
          />
        )}
      </Panel>
      {selected && <EventDrawer event={selected} onClose={() => { setSelected(null); if (id) set("id", ""); }} />}
    </>
  );
}
