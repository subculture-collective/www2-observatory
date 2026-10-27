package analytics

import (
	"database/sql"
	"fmt"
	"time"

	"github.com/onnwee/www2-observatory/internal/research"
)

// Diagnostics exposes request shapes and HTTP outcomes, never compromise or
// verified crawler identity. All aggregates use the selected window.
func Diagnostics(conn *sql.DB, hours int) (map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	summary, err := scanOne(conn, `SELECT COUNT(*) requests, COUNT(DISTINCT source_id) sources,
 COALESCE(SUM(probe_family<>''),0) probes,
 COALESCE(SUM(probe_family<>'' AND status>=200 AND status<300),0) probe_2xx,
 COALESCE(SUM(status=404),0) missing,
 COALESCE(SUM(status=404 AND probe_family<>''),0) probe_404,
 COALESCE(SUM(request_kind='resource-miss'),0) resource_misses,
 COALESCE(SUM(request_kind='asset-miss'),0) asset_misses,
 COALESCE(SUM(status>=500),0) server_errors,
 COALESCE(SUM(status=429),0) rate_limited,
 COALESCE(SUM(status IN (413,414,422)),0) rejected,
 COALESCE(SUM(status=304),0) revalidated,
 COALESCE(SUM(diagnostic_revision<>?),0) pending
 FROM access_events WHERE ts>=?`, research.DiagnosticRevision, since)
	if err != nil {
		return nil, err
	}
	out := map[string]any{"summary": summary, "revision": research.DiagnosticRevision, "hours": hours}
	queries := []struct{ key, query string }{
		{"kinds", `SELECT request_kind kind, COUNT(*) requests, COUNT(DISTINCT source_id) sources, SUM(status=404) missing, SUM(status>=500) server_errors FROM access_events WHERE ts>=? GROUP BY request_kind ORDER BY requests DESC`},
		{"families", `SELECT probe_family family, COUNT(*) requests, COUNT(DISTINCT source_id) sources, COUNT(DISTINCT client_id) clients, COUNT(DISTINCT path) paths, SUM(status=404) missing, SUM(status>=200 AND status<300) responses_2xx, SUM(status>=500) server_errors, MAX(ts) last_seen FROM access_events WHERE ts>=? AND probe_family<>'' GROUP BY probe_family ORDER BY requests DESC`},
		{"sources", `SELECT source_id, COUNT(*) requests, COUNT(DISTINCT client_id) clients, COUNT(DISTINCT user_agent) user_agents, COUNT(DISTINCT path) paths, SUM(probe_family<>'') probes, SUM(status=404) missing, SUM(status>=500) server_errors, MIN(ts) first_seen, MAX(ts) last_seen FROM access_events WHERE ts>=? GROUP BY source_id ORDER BY requests DESC LIMIT 30`},
		{"misses", `SELECT path,request_kind kind,probe_family family,COUNT(*) requests,COUNT(DISTINCT source_id) sources,SUM(referer_host<>'' AND referer_host=host) internal_referrers,MAX(ts) last_seen FROM access_events WHERE ts>=? AND status=404 GROUP BY path,request_kind,probe_family ORDER BY requests DESC LIMIT 80`},
		{"review", `SELECT id,ts,path,status,request_kind,probe_family,source_id,diagnostic_reason FROM access_events WHERE ts>=? AND ((probe_family<>'' AND status>=200 AND status<300) OR status>=500 OR (status=404 AND request_kind IN ('resource-miss','asset-miss'))) ORDER BY ts DESC LIMIT 30`},
	}
	for _, q := range queries {
		value, err := scanRows(conn, q.query, since)
		if err != nil {
			return nil, err
		}
		out[q.key] = value
	}
	format := "%Y-%m-%d %H:00"
	if hours > 168 {
		format = "%Y-%m-%d"
	}
	timeline, err := scanRows(conn, fmt.Sprintf(`SELECT strftime('%s',ts,'unixepoch') bucket, COUNT(*) requests, SUM(probe_family<>'') probes, SUM(status=404) missing, SUM(status>=500) server_errors, COUNT(DISTINCT source_id) sources FROM access_events WHERE ts>=? GROUP BY bucket ORDER BY bucket`, format), since)
	if err != nil {
		return nil, err
	}
	out["timeline"] = timeline
	return out, nil
}
