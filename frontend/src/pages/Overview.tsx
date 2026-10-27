import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client.ts";
import type { AccessEvent } from "../api/types.ts";
import { Timeline, fill } from "../charts/Timeline.tsx";
import { Funnel } from "../charts/Funnel.tsx";
import { Radar } from "../charts/Radar.tsx";
import { Donut } from "../charts/Donut.tsx";
import { Bars } from "../charts/Bars.tsx";
import { Panel, Empty, ErrorNote } from "../ui/Panel.tsx";
import { Stat } from "../ui/Stat.tsx";
import { ClassTag, MethodTag, StatusTag } from "../ui/Table.tsx";
import { useData, useSettings } from "../lib/settings.tsx";
import { fmtBytes, fmtShort, n, pct, short } from "../lib/format.ts";
import { useState } from "react";
import { EventDrawer } from "../ui/EventDrawer.tsx";
import { TelemetryCore } from "../charts/TelemetryCore.tsx";
import { TrafficReplay } from "../charts/TrafficReplay.tsx";
import { DiagnosticTimeline } from "../charts/DiagnosticTimeline.tsx";
import { familyLabels, kindColor, kindLabels } from "../lib/diagnostics.ts";

export function Overview() {
  const { hours } = useSettings();
  const bucket = hours > 168 ? "day" : "hour";
  const nav = useNavigate();
  const [selected, setSelected] = useState<AccessEvent | null>(null);
  const { data, error } = useData(
    async (h) => {
      const [
        summary,
        timeline,
        experiment,
        clients,
        recent,
        entrances,
        representations,
        interventions,
        diagnostics,
      ] = await Promise.all([
        api.summary(h),
        api.timeline(h, bucket),
        api.experiment(h),
        api.clients(h, 400),
        api.recent({ limit: 18, hours: h }),
        api.entrances(h, 8),
        api.representations(h),
        api
          .interventions()
          .catch(() => ({ version: 0, timezone: "", changes: [] })),
        api.diagnostics(h),
      ]);
      return {
        summary,
        timeline,
        experiment,
        clients,
        recent,
        entrances,
        representations,
        interventions,
        diagnostics,
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
  const s = data.summary;
  const filled = fill(data.timeline, hours, bucket);
  const spark = (k: "total" | "engagement" | "writes" | "clients") =>
    filled.map((f) => Number(f.b?.[k] ?? 0));
  const e = data.experiment;
  return (
    <>
      <ErrorNote error={error} />
      <div className="command-grid">
        <TelemetryCore report={data.diagnostics} />
        <Panel
          id="radar"
          className="command-radar"
          chip={`${data.clients.length}${data.clients.length === 400 ? " shown" : " active"}`}
        >
          <Radar clients={data.clients} hours={hours} size={300} />
          <p className="note">
            {data.clients.length === 400
              ? "Newest 400 fingerprints shown; open fingerprints for up to 1,000."
              : "Observed fingerprints, not verified visitors or agents."}
          </p>
        </Panel>
        <div className="command-side">
          <Panel title="Signal composition" chip="actual requests">
            <Donut
              label="requests"
              slices={data.diagnostics.kinds.map((k) => ({
                label: kindLabels[k.kind] ?? k.kind,
                value: k.requests,
                color: kindColor(k.kind),
              }))}
            />
          </Panel>
          <Panel
            title="Response watch"
            tone="orange"
            chip={<Link to="/diagnostics">inspect →</Link>}
          >
            <div className="watch-readout">
              <b>
                {pct(
                  data.diagnostics.summary.probe_404,
                  data.diagnostics.summary.missing,
                )}
              </b>
              <span>of 404s matched a probe pattern</span>
            </div>
            <div className="watch-grid">
              <Link to="/events?status=5">
                {n(data.diagnostics.summary.server_errors)}
                <small>server errors</small>
              </Link>
              <Link to="/events?kind=resource-miss">
                {n(data.diagnostics.summary.resource_misses)}
                <small>resource misses</small>
              </Link>
              <Link to="/events?kind=asset-miss">
                {n(data.diagnostics.summary.asset_misses)}
                <small>asset misses</small>
              </Link>
              <Link to="/events?status=429">
                {n(data.diagnostics.summary.rate_limited)}
                <small>rate limits</small>
              </Link>
            </div>
          </Panel>
        </div>
      </div>
      <div className="stats overview-stats">
        <Stat
          id="requests"
          label="requests"
          value={s.requests}
          previous={s.prev_requests}
          spark={spark("total")}
          sub={`${n(data.diagnostics.summary.missing)} missing · ${fmtBytes(s.total_bytes)} sent`}
        />
        <Stat
          id="clients"
          label="fingerprints"
          value={s.clients}
          previous={s.prev_clients}
          spark={spark("clients")}
          tone="cyan"
          sub={`${n(s.sources)} sources · ${n(s.sessions)} sessions`}
        />
        <Stat
          id="resource"
          label="resource requests"
          value={s.engagement}
          previous={s.prev_engagement}
          spark={spark("engagement")}
          tone="cyan"
          sub={`${pct(s.engagement, s.requests)} of requests · ${n(s.operator)} operator-marked`}
        />
        <Stat
          id="writes"
          label="HTTP write outcomes"
          value={s.writes}
          previous={s.prev_writes}
          spark={spark("writes")}
          tone="magenta"
          sub={`${n(s.link_writes)} GET attempts · stored changes may be fewer`}
        />
        <Stat
          label="funnel · furthest stage"
          value={furthest(e.stages)}
          tone="accent"
          sub={`${n(e.returning_clients)} returning · ${n(e.cross_source_reads)} cross-source reads`}
        />
        <Stat
          label="high automation"
          value={s.high_auto}
          tone="orange"
          sub={`${n(s.med_auto)} medium · ${n(s.low_auto)} low · avg score ${s.avg_score}`}
        />
        <Stat
          label="probe-shaped requests"
          value={data.diagnostics.summary.probes}
          tone="orange"
          sub={`${pct(data.diagnostics.summary.probes, s.requests)} of traffic · patterns, not verified intent`}
        />
        <Stat
          label="source concentration"
          value={pct(data.diagnostics.sources[0]?.requests ?? 0, s.requests)}
          tone="magenta"
          sub="share of requests from the largest source"
        />
      </div>

      <div className="grid">
        <TrafficReplay report={data.diagnostics} />
        <Panel id="timeline" span={4} chip={`${bucket}ly · utc`}>
          <Timeline
            timeline={data.timeline}
            hours={hours}
            bucket={bucket}
            interventions={data.interventions.changes}
          />
        </Panel>
        <Panel
          id="diagnostics"
          title="Probe / response activity"
          span={3}
          chip={<Link to="/diagnostics">full diagnostic report →</Link>}
        >
          <DiagnosticTimeline report={data.diagnostics} />
        </Panel>
        <Panel title="Probe families" span={1} chip="click to inspect">
          <Bars
            items={data.diagnostics.families.map((f) => ({
              key: f.family,
              label: familyLabels[f.family] ?? f.family,
              value: f.requests,
              color: "var(--orange)",
              sub: `${f.sources} sources · ${f.paths} paths`,
              onClick: () => nav(`/events?family=${f.family}`),
            }))}
          />
        </Panel>

        <Panel id="funnel" span={2} chip={<Link to="/funnel">detail →</Link>}>
          <Funnel stages={e.stages} eligible={e.eligible_clients} />
        </Panel>
        <Panel id="outcomes" span={1}>
          <Donut
            label="responses"
            slices={[
              {
                label: "2xx",
                value: sum(filled, "s2xx"),
                color: "var(--accent)",
              },
              {
                label: "3xx",
                value: sum(filled, "s3xx"),
                color: "var(--blue)",
              },
              {
                label: "4xx",
                value: sum(filled, "s4xx"),
                color: "var(--yellow)",
              },
              { label: "5xx", value: sum(filled, "s5xx"), color: "var(--red)" },
            ]}
          />
        </Panel>
        <Panel id="representations" span={1}>
          <Donut
            label="2xx served"
            slices={data.representations.map((r) => ({
              label: r.family,
              value: r.responses,
              color:
                (
                  {
                    html: "var(--fg-dim)",
                    text: "var(--accent)",
                    json: "var(--cyan)",
                    xml: "var(--blue)",
                    atom: "var(--blue)",
                    css: "var(--muted)",
                    image: "var(--muted)",
                  } as Record<string, string>
                )[r.family] ?? "var(--selection)",
            }))}
          />
        </Panel>

        <Panel
          id="events"
          span={2}
          chip={<Link to="/events">all events →</Link>}
        >
          {data.recent.length ? (
            <ul className="wire">
              {data.recent.map((ev) => (
                <li key={ev.id}>
                  <button onClick={() => setSelected(ev)}>
                    <span className="dim">{fmtShort(ev.ts)}</span>
                    <ClassTag cls={ev.traffic_class} />
                    <StatusTag status={ev.status} />
                    <MethodTag method={ev.method} />
                    <span className="mono dim">{short(ev.client_id, 12)}</span>
                    <code className="path">
                      {ev.path}
                      {ev.query && <span className="dim">?{ev.query}</span>}
                    </code>
                    {ev.link_write && <span className="tag c-link">link</span>}
                    {ev.successful_write ? (
                      <span className="tag c-write">write</span>
                    ) : null}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <Empty />
          )}
        </Panel>
        <Panel
          id="entrances"
          span={2}
          chip={<Link to="/traffic">traffic →</Link>}
        >
          <Bars
            items={data.entrances.map((r) => ({
              key: `${r.path}|${r.referer_host}`,
              label: (
                <>
                  <code>{r.path}</code>
                  {r.referer_host && (
                    <span className="dim"> ← {r.referer_host}</span>
                  )}
                </>
              ),
              value: r.sessions,
              color: r.high > r.sessions / 2 ? "var(--orange)" : "var(--cyan)",
              sub: `${r.clients} fingerprints · ${r.engagement} resource · ${r.high} high-automation`,
              onClick: () =>
                nav(`/events?search=${encodeURIComponent(r.path)}`),
            }))}
          />
        </Panel>
      </div>
      {selected && (
        <EventDrawer event={selected} onClose={() => setSelected(null)} />
      )}
    </>
  );
}

function sum(
  filled: ReturnType<typeof fill>,
  k: "s2xx" | "s3xx" | "s4xx" | "s5xx",
) {
  return filled.reduce((a, f) => a + Number(f.b?.[k] ?? 0), 0);
}
function furthest(stages: { label: string; clients: number }[]): string {
  const reached = [...stages].reverse().find((s) => s.clients > 0);
  return reached
    ? `${stages.indexOf(reached) + 1}/${stages.length} ${reached.label.toLowerCase()}`
    : "none";
}
