export type AutomationLevel = "low" | "medium" | "high";
export type TrafficClass = "engagement" | "scanner" | "operator" | "other";

/** Shared breakdown columns emitted by SummaryEx, TimelineEx, Clients, Paths, UserAgents. */
export interface Breakdown {
  engagement: number;
  scanner: number;
  operator: number;
  other: number;
  probes: number;
  m_get?: number;
  m_head?: number;
  m_options?: number;
  m_post?: number;
  m_put?: number;
  m_other?: number;
  r_json?: number;
  r_text?: number;
  r_html?: number;
  r_xml?: number;
  writes: number;
  link_writes: number;
  write_methods: number;
}

export interface Summary extends Breakdown {
  requests: number;
  clients: number;
  sources: number;
  sessions: number;
  high_auto: number;
  med_auto: number;
  low_auto: number;
  avg_score: number;
  total_bytes: number;
  errors: number;
  verified_address: number;
  prev_requests: number;
  prev_clients: number;
  prev_writes: number | null;
  prev_engagement: number | null;
  prev_scanner: number | null;
  hours: number;
}

export interface TimelineBucket extends Breakdown {
  bucket: string;
  total: number;
  clients: number;
  sources: number;
  high: number;
  medium: number;
  low: number;
  s2xx: number;
  s3xx: number;
  s4xx: number;
  s5xx: number;
  bytes: number;
}

export interface AccessEvent {
  id: number;
  ts: number;
  host: string;
  event_key: string;
  source_id: string;
  client_id: string;
  session_id: string;
  method: string;
  path: string;
  query: string;
  status: number;
  user_agent: string;
  accept_header: string;
  referer: string;
  referer_host: string;
  content_type: string;
  response_bytes: number;
  automation_score: number;
  automation_level: AutomationLevel;
  signals_json: string;
  attribution: string;
  original_source_id: string;
  original_client_id: string;
  original_session_id: string;
  traffic_class: string;
  classification_reason: string;
  write_object: string;
  successful_write: number;
  link_write: string;
  request_kind: string;
  probe_family: string;
  diagnostic_reason: string;
  diagnostic_revision: string;
}

export interface DiagnosticSummary {
  requests: number;
  sources: number;
  probes: number;
  probe_2xx: number;
  missing: number;
  probe_404: number;
  resource_misses: number;
  asset_misses: number;
  server_errors: number;
  rate_limited: number;
  rejected: number;
  revalidated: number;
  pending: number;
}
export interface ProbeFamily {
  family: string;
  requests: number;
  sources: number;
  clients: number;
  paths: number;
  missing: number;
  responses_2xx: number;
  server_errors: number;
  last_seen: number;
}
export interface DiagnosticSource {
  source_id: string;
  requests: number;
  clients: number;
  user_agents: number;
  paths: number;
  probes: number;
  missing: number;
  server_errors: number;
  first_seen: number;
  last_seen: number;
}
export interface MissingPath {
  path: string;
  kind: string;
  family: string;
  requests: number;
  sources: number;
  internal_referrers: number;
  last_seen: number;
}
export interface DiagnosticsReport {
  hours: number;
  revision: string;
  summary: DiagnosticSummary;
  kinds: {
    kind: string;
    requests: number;
    sources: number;
    missing: number;
    server_errors: number;
  }[];
  families: ProbeFamily[];
  sources: DiagnosticSource[];
  misses: MissingPath[];
  review: Pick<
    AccessEvent,
    | "id"
    | "ts"
    | "path"
    | "status"
    | "request_kind"
    | "probe_family"
    | "source_id"
    | "diagnostic_reason"
  >[];
  timeline: {
    bucket: string;
    requests: number;
    probes: number;
    missing: number;
    server_errors: number;
    sources: number;
  }[];
}

export interface ClientRow extends Breakdown {
  client_id: string;
  source_id: string;
  first_seen: number;
  last_seen: number;
  requests: number;
  sessions: number;
  unique_paths: number;
  max_automation: number;
  avg_automation: number;
  errors: number;
  attribution: string;
  user_agent: string;
}

export interface SessionRow {
  session_id: string;
  started: number;
  ended: number;
  requests: number;
  unique_paths: number;
  max_automation: number;
  writes: number;
  trail: string;
}

export interface Evidence {
  client: string;
  stage: string;
  event_id: number;
  path: string;
  ts: number;
}

export interface Stage {
  key: string;
  label: string;
  clients: number;
}

export interface ClientDetail {
  summary: ClientRow;
  sessions: SessionRow[];
  events: AccessEvent[];
  user_agents: { user_agent: string; hits: number }[];
  objects: {
    path: string;
    writes: number;
    first_write: number;
    last_write: number;
  }[];
  stages: Evidence[];
  stage_labels: Stage[];
}

export interface ObjectRow {
  path: string;
  first_write: number;
  last_write: number;
  writes: number;
  writers: number;
  writer_sources: number;
  link_writes: number;
  operator_writes: number;
  reads: number;
  readers: number;
  reader_sources: number;
  cross_source_reads: number;
  last_read: number;
  stored: number;
}

export interface RepresentationRow {
  family: string;
  responses: number;
  clients: number;
  engagement: number;
  high: number;
}

export interface HeatCell {
  dow: number;
  hour: number;
  total: number;
  clients: number;
  engagement: number;
  scanner: number;
  high: number;
  writes: number;
}

export interface LinkWriteRow {
  id: number;
  ts: number;
  client_id: string;
  source_id: string;
  session_id: string;
  path: string;
  query: string;
  status: number;
  link_write: string;
  write_object: string;
  successful_write: number;
  traffic_class: string;
  attribution: string;
  automation_score: number;
  user_agent: string;
}

export interface EntranceRow {
  path: string;
  referer_host: string;
  sessions: number;
  clients: number;
  engagement: number;
  high: number;
}

export interface PathRow extends Breakdown {
  path: string;
  hits: number;
  clients: number;
  avg_automation: number;
  errors: number;
}

export interface UserAgentRow extends Breakdown {
  user_agent: string;
  hits: number;
  clients: number;
  sources: number;
  avg_auto: number;
  first_seen: number;
  last_seen: number;
}

export interface StatusSlice {
  status: number;
  count: number;
}
export interface MethodSlice {
  method: string;
  count: number;
}
export interface SignalStat {
  signal: string;
  events: number;
  clients: number;
}
export interface ReferrerRow {
  referer_host: string;
  hits: number;
  clients: number;
}

export interface WriteEvent {
  id: number;
  ts: number;
  event: string;
  path: string;
  source_id: string;
  client_id: string;
  content: string;
  content_hash: string;
  metadata_json: string;
}

export interface ConventionStat {
  token: string;
  uses: number;
  clients: number;
  first_seen: number;
  last_seen: number;
}

export interface IngestStats {
  access_records: number;
  relay_records: number;
  first_ts: number;
  last_ts: number;
  journal_mode: string;
  db_size_bytes: number;
  now: number;
  ingest_state: {
    source: string;
    inode: number;
    offset: number;
    updated_at: number;
  }[];
  measurement_runs: {
    completed_at: number;
    revision: string;
    matched_records: number;
  }[];
  classes: { traffic_class: string; records: number }[];
  attribution: { attribution: string; records: number }[];
}

export interface ExperimentReport {
  hours: number;
  revision: string;
  attribution: Record<string, number>;
  traffic: Record<string, number>;
  eligible_clients: number;
  successful_writes: number;
  returning_clients: number;
  cross_source_reads: number;
  stages: Stage[];
  evidence: Evidence[];
  notes: string[];
}

export interface Intervention {
  id: string;
  date: string;
  scope: string;
  description: string;
  resources?: { path: string; sha256: string }[];
}
export interface Interventions {
  version: number;
  timezone: string;
  changes: Intervention[];
}
