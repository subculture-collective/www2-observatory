import type {
  AccessEvent,
  DiagnosticsReport,
  ClientDetail,
  ClientRow,
  ConventionStat,
  EntranceRow,
  ExperimentReport,
  HeatCell,
  IngestStats,
  Interventions,
  LinkWriteRow,
  MethodSlice,
  ObjectRow,
  PathRow,
  ReferrerRow,
  RepresentationRow,
  SignalStat,
  StatusSlice,
  Summary,
  TimelineBucket,
  UserAgentRow,
  WriteEvent,
} from "./types.ts";

async function getJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: authHeaders() });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText} for ${path}`);
  }
  return (await response.json()) as T;
}

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("obs_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

const qs = (params: Record<string, string | number | undefined>) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
    .join("&");

export interface RecentFilter {
  limit?: number;
  method?: string;
  level?: string;
  status?: number;
  search?: string;
  class?: string;
  client?: string;
  link?: 1;
  hours?: number;
  kind?: string;
  family?: string;
  path?: string;
  since?: number;
  until?: number;
}

export const api = {
  downloadExport: async (filter: RecentFilter) => {
    const response = await fetch(api.exportUrl(filter), {
      headers: authHeaders(),
    });
    if (!response.ok)
      throw new Error(`${response.status} ${response.statusText}`);
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = "observatory-filtered-events.ndjson";
    link.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  },
  diagnostics: (hours: number) =>
    getJson<DiagnosticsReport>(`/api/diagnostics?hours=${hours}`),
  summary: (hours: number) => getJson<Summary>(`/api/summary?hours=${hours}`),
  timeline: (hours: number, bucket: "hour" | "day" = "hour") =>
    getJson<TimelineBucket[]>(`/api/timeline?hours=${hours}&bucket=${bucket}`),
  experiment: (hours: number) =>
    getJson<ExperimentReport>(`/api/experiment?hours=${hours}`),
  recent: (f: RecentFilter = {}) =>
    getJson<AccessEvent[]>(
      `/api/recent?${qs({ limit: f.limit ?? 100, ...f })}`,
    ),
  event: (id: number) => getJson<AccessEvent>(`/api/event?id=${id}`),
  clients: (hours: number, limit = 200, cls = "", order = "") =>
    getJson<ClientRow[]>(
      `/api/clients?${qs({ hours, limit, class: cls, order })}`,
    ),
  client: (id: string, limit = 300) =>
    getJson<ClientDetail>(`/api/client?${qs({ id, limit })}`),
  objects: (hours: number) =>
    getJson<ObjectRow[]>(`/api/objects?hours=${hours}`),
  representations: (hours: number) =>
    getJson<RepresentationRow[]>(`/api/representations?hours=${hours}`),
  heatmap: (hours: number) =>
    getJson<HeatCell[]>(`/api/heatmap?hours=${hours}`),
  linkWrites: (hours: number, limit = 200) =>
    getJson<LinkWriteRow[]>(`/api/link-writes?hours=${hours}&limit=${limit}`),
  entrances: (hours: number, limit = 40) =>
    getJson<EntranceRow[]>(`/api/entrances?hours=${hours}&limit=${limit}`),
  paths: (hours: number, limit = 60) =>
    getJson<PathRow[]>(`/api/paths?hours=${hours}&limit=${limit}`),
  userAgents: (hours: number, limit = 60) =>
    getJson<UserAgentRow[]>(`/api/user-agents?hours=${hours}&limit=${limit}`),
  referrers: (hours: number, limit = 40) =>
    getJson<ReferrerRow[]>(`/api/referrers?hours=${hours}&limit=${limit}`),
  status: (hours: number) =>
    getJson<StatusSlice[]>(`/api/status?hours=${hours}`),
  methods: (hours: number) =>
    getJson<MethodSlice[]>(`/api/methods?hours=${hours}`),
  signals: (hours: number) =>
    getJson<SignalStat[]>(`/api/signals?hours=${hours}`),
  writes: (limit = 50, hours = 720) =>
    getJson<WriteEvent[]>(`/api/writes?limit=${limit}&hours=${hours}`),
  conventions: (hours: number, limit = 40) =>
    getJson<ConventionStat[]>(`/api/conventions?hours=${hours}&limit=${limit}`),
  ingest: () => getJson<IngestStats>("/api/ingest"),
  interventions: () => getJson<Interventions>("/api/interventions"),
  exportUrl: (filter: RecentFilter = {}) =>
    `/api/export.ndjson?${qs({ limit: 1000, ...filter })}`,
};
