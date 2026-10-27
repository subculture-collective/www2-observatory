package analytics

// Aggregations added for the multi-page observatory (2026-09-25). Every
// function here is a read over access_events; none evaluates intent. Column
// names are stable because the frontend types mirror them.

import (
	"database/sql"
	"fmt"
	"strings"
	"time"

	"github.com/onnwee/www2-observatory/internal/research"
)

// classCase yields SUM expressions for the four traffic classes.
const classSums = `
  SUM(CASE WHEN traffic_class='engagement' THEN 1 ELSE 0 END) engagement,
  SUM(CASE WHEN traffic_class='scanner' THEN 1 ELSE 0 END) scanner,
  SUM(CASE WHEN traffic_class='operator' THEN 1 ELSE 0 END) operator,
  SUM(CASE WHEN traffic_class NOT IN ('engagement','scanner','operator') THEN 1 ELSE 0 END) other`

const methodSums = `
  SUM(CASE WHEN method='GET' THEN 1 ELSE 0 END) m_get,
  SUM(CASE WHEN method='HEAD' THEN 1 ELSE 0 END) m_head,
  SUM(CASE WHEN method='OPTIONS' THEN 1 ELSE 0 END) m_options,
  SUM(CASE WHEN method='POST' THEN 1 ELSE 0 END) m_post,
  SUM(CASE WHEN method='PUT' THEN 1 ELSE 0 END) m_put,
  SUM(CASE WHEN method NOT IN ('GET','HEAD','OPTIONS','POST','PUT') THEN 1 ELSE 0 END) m_other`

const representationSums = `
  SUM(CASE WHEN content_type LIKE '%json%' THEN 1 ELSE 0 END) r_json,
  SUM(CASE WHEN content_type LIKE 'text/plain%' THEN 1 ELSE 0 END) r_text,
  SUM(CASE WHEN content_type LIKE 'text/html%' THEN 1 ELSE 0 END) r_html,
  SUM(CASE WHEN content_type LIKE '%atom%' OR content_type LIKE '%xml%' OR content_type LIKE '%opml%' THEN 1 ELSE 0 END) r_xml`

const writeSums = `
  SUM(CASE WHEN successful_write<>0 THEN 1 ELSE 0 END) writes,
  SUM(CASE WHEN link_write<>'' THEN 1 ELSE 0 END) link_writes,
  SUM(CASE WHEN method IN ('POST','PUT','PATCH','DELETE') THEN 1 ELSE 0 END) write_methods`

// TimelineEx buckets the window by hour or day with class, method,
// representation, write, and outcome breakdowns. Empty buckets are omitted;
// the frontend fills them with zeros so gaps stay visible.
func TimelineEx(conn *sql.DB, hours int, bucket string) ([]map[string]any, error) {
	format := "%Y-%m-%d %H:00"
	if bucket == "day" {
		format = "%Y-%m-%d"
	}
	return rowsSince(conn, hours, fmt.Sprintf(`SELECT strftime('%s', ts, 'unixepoch') as bucket,
  COUNT(*) as total, COUNT(DISTINCT client_id) clients, COUNT(DISTINCT source_id) sources,
  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) as high,
  SUM(CASE WHEN automation_level='medium' THEN 1 ELSE 0 END) as medium,
  SUM(CASE WHEN automation_level='low' THEN 1 ELSE 0 END) as low,
  SUM(CASE WHEN status >= 200 AND status < 300 THEN 1 ELSE 0 END) as s2xx,
  SUM(CASE WHEN status >= 300 AND status < 400 THEN 1 ELSE 0 END) as s3xx,
  SUM(CASE WHEN status >= 400 AND status < 500 THEN 1 ELSE 0 END) as s4xx,
  SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) as s5xx,
  COALESCE(SUM(response_bytes), 0) as bytes,%s,%s,%s,%s
  FROM access_events WHERE ts >= ? GROUP BY bucket ORDER BY bucket ASC`, format, classSums, methodSums, representationSums, writeSums))
}

// SummaryEx extends Summary with class, write, and representation totals and
// the previous window for each headline number.
func SummaryEx(conn *sql.DB, hours int) (map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	row, err := scanOne(conn, `SELECT COUNT(*) requests, COUNT(DISTINCT client_id) clients, COUNT(DISTINCT source_id) sources, COUNT(DISTINCT session_id) sessions,
  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) high_auto,
  SUM(CASE WHEN automation_level='medium' THEN 1 ELSE 0 END) med_auto,
  SUM(CASE WHEN automation_level='low' THEN 1 ELSE 0 END) low_auto,
  COALESCE(ROUND(AVG(automation_score), 1), 0) avg_score,
  COALESCE(SUM(response_bytes), 0) total_bytes,
  SUM(CASE WHEN status >= 400 THEN 1 ELSE 0 END) errors,`+classSums+`,`+writeSums+`,`+representationSums+`,
  SUM(CASE WHEN attribution='caddy-client-v2' THEN 1 ELSE 0 END) verified_address
  FROM access_events WHERE ts>=?`, since)
	if err != nil {
		return nil, err
	}
	prev, err := scanOne(conn, `SELECT COUNT(*) prev_requests, COUNT(DISTINCT client_id) prev_clients,
  SUM(CASE WHEN successful_write<>0 THEN 1 ELSE 0 END) prev_writes,
  SUM(CASE WHEN traffic_class='engagement' THEN 1 ELSE 0 END) prev_engagement,
  SUM(CASE WHEN traffic_class='scanner' THEN 1 ELSE 0 END) prev_scanner
  FROM access_events WHERE ts>=? AND ts<?`, since-float64(hours*3600), since)
	if err != nil {
		return nil, err
	}
	for key, value := range prev {
		row[key] = value
	}
	row["hours"] = hours
	return row, nil
}

const clientColumns = `client_id, MIN(source_id) source_id, MIN(ts) first_seen, MAX(ts) last_seen, COUNT(*) requests,
  COUNT(DISTINCT session_id) sessions, COUNT(DISTINCT path) unique_paths,
  MAX(automation_score) max_automation, ROUND(AVG(automation_score),1) avg_automation,
  SUM(CASE WHEN status >= 400 THEN 1 ELSE 0 END) errors,
  MIN(attribution) attribution, SUBSTR(MAX(user_agent),1,240) user_agent,` + classSums + `,` + methodSums + `,` + representationSums + `,` + writeSums

// Clients lists one row per client fingerprint active in the window. class,
// when set, keeps only clients with at least one request in that class.
func Clients(conn *sql.DB, hours, limit int, class, order string) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	having := ""
	args := []any{since}
	switch class {
	case "engagement", "scanner", "operator", "other":
		having = " HAVING " + class + " > 0"
	case "writers":
		having = " HAVING writes > 0"
	case "verified":
		having = " HAVING attribution = 'caddy-client-v2'"
	}
	orderBy := "last_seen DESC"
	switch order {
	case "requests":
		orderBy = "requests DESC"
	case "writes":
		orderBy = "writes DESC, requests DESC"
	case "automation":
		orderBy = "max_automation DESC, requests DESC"
	case "first_seen":
		orderBy = "first_seen ASC"
	}
	args = append(args, clamp(limit, 1, 1000))
	return scanRows(conn, "SELECT "+clientColumns+" FROM access_events WHERE ts>=? GROUP BY client_id"+having+" ORDER BY "+orderBy+" LIMIT ?", args...)
}

// ClientDetail returns everything recorded about one fingerprint: the
// aggregate row, its sessions, the funnel stages it reached (whole history),
// and its most recent events.
func ClientDetail(conn *sql.DB, clientID string, limit, gapMinutes int) (map[string]any, error) {
	summary, err := scanOne(conn, "SELECT "+clientColumns+" FROM access_events WHERE client_id=? GROUP BY client_id", clientID)
	if err != nil {
		return nil, err
	}
	if len(summary) == 0 {
		return nil, sql.ErrNoRows
	}
	sessions, err := scanRows(conn, `SELECT session_id, MIN(ts) started, MAX(ts) ended, COUNT(*) requests, COUNT(DISTINCT path) unique_paths,
  MAX(automation_score) max_automation, SUM(CASE WHEN successful_write<>0 THEN 1 ELSE 0 END) writes,
  GROUP_CONCAT(method || ' ' || path || CASE WHEN query<>'' THEN '?' || query ELSE '' END || ' ' || status, char(10)) trail
  FROM access_events WHERE client_id=? GROUP BY session_id ORDER BY started DESC LIMIT 100`, clientID)
	if err != nil {
		return nil, err
	}
	for _, row := range sessions {
		if trail, ok := row["trail"].(string); ok && len(trail) > 6000 {
			row["trail"] = trail[:6000]
		}
	}
	events, err := scanRows(conn, "SELECT * FROM access_events WHERE client_id=? ORDER BY ts DESC LIMIT ?", clientID, clamp(limit, 1, 1000))
	if err != nil {
		return nil, err
	}
	agents, err := scanRows(conn, "SELECT user_agent, COUNT(*) hits FROM access_events WHERE client_id=? GROUP BY user_agent ORDER BY hits DESC LIMIT 5", clientID)
	if err != nil {
		return nil, err
	}
	objects, err := scanRows(conn, "SELECT write_object path, COUNT(*) writes, MIN(ts) first_write, MAX(ts) last_write FROM access_events WHERE client_id=? AND write_object<>'' GROUP BY write_object ORDER BY last_write DESC", clientID)
	if err != nil {
		return nil, err
	}
	report, err := Experiment(conn, 24*90, gapMinutes)
	if err != nil {
		return nil, err
	}
	stages := []ExperimentEvidence{}
	for _, e := range report.Evidence {
		if e.Client == clientID {
			stages = append(stages, e)
		}
	}
	return map[string]any{"summary": summary, "sessions": sessions, "events": events, "user_agents": agents, "objects": objects, "stages": stages, "stage_labels": report.Stages}, nil
}

// RecentEx is Recent with traffic-class and client filters.
func RecentEx(conn *sql.DB, limit int, method, level string, status *int, search, class, client string, linkOnly bool) ([]map[string]any, error) {
	clauses := []string{}
	args := []any{}
	if method != "" {
		clauses = append(clauses, "method = ?")
		args = append(args, strings.ToUpper(method))
	}
	if level != "" {
		clauses = append(clauses, "automation_level = ?")
		args = append(args, strings.ToLower(level))
	}
	if status != nil {
		if *status < 10 {
			clauses = append(clauses, "status >= ? AND status < ?")
			args = append(args, *status*100, *status*100+100)
		} else {
			clauses = append(clauses, "status = ?")
			args = append(args, *status)
		}
	}
	if class != "" {
		if class == "other" {
			clauses = append(clauses, "traffic_class NOT IN ('engagement','scanner','operator')")
		} else {
			clauses = append(clauses, "traffic_class = ?")
			args = append(args, class)
		}
	}
	if client != "" {
		clauses = append(clauses, "(client_id = ? OR source_id = ? OR session_id = ?)")
		args = append(args, client, client, client)
	}
	if linkOnly {
		clauses = append(clauses, "link_write <> ''")
	}
	if search != "" {
		clauses = append(clauses, "(path LIKE ? OR query LIKE ? OR user_agent LIKE ? OR client_id LIKE ? OR referer LIKE ?)")
		pattern := "%" + search + "%"
		args = append(args, pattern, pattern, pattern, pattern, pattern)
	}
	where := ""
	if len(clauses) > 0 {
		where = " WHERE " + strings.Join(clauses, " AND ")
	}
	args = append(args, clamp(limit, 1, 1000))
	return scanRows(conn, "SELECT * FROM access_events"+where+" ORDER BY ts DESC, id DESC LIMIT ?", args...)
}

func EventByID(conn *sql.DB, id int64) (map[string]any, error) {
	row, err := scanOne(conn, "SELECT * FROM access_events WHERE id=?", id)
	if err != nil {
		return nil, err
	}
	if len(row) == 0 {
		return nil, sql.ErrNoRows
	}
	return row, nil
}

// Objects lists every durable object that a write created or changed, with
// who wrote it and how it was read afterwards. A read by a different source
// than the last writer is the "cross-source" count; it is the closest this
// data comes to one party seeing what another party left.
func Objects(conn *sql.DB, hours int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	writes, err := scanRows(conn, `SELECT write_object path, MIN(ts) first_write, MAX(ts) last_write, COUNT(*) writes,
  COUNT(DISTINCT client_id) writers, COUNT(DISTINCT source_id) writer_sources,
  SUM(CASE WHEN link_write<>'' THEN 1 ELSE 0 END) link_writes,
  SUM(CASE WHEN traffic_class='operator' THEN 1 ELSE 0 END) operator_writes
  FROM access_events WHERE write_object<>'' AND ts>=? GROUP BY write_object ORDER BY last_write DESC`, since)
	if err != nil {
		return nil, err
	}
	if len(writes) == 0 {
		return writes, nil
	}
	type reads struct {
		reads, readers, sources, cross int
		last                           float64
	}
	byPath := map[string]*reads{}
	writerSource := map[string]string{}
	firstWrite := map[string]float64{}
	for _, w := range writes {
		p := fmt.Sprint(w["path"])
		byPath[p] = &reads{}
		firstWrite[p] = toFloat(w["first_write"])
	}
	// Last writer's source per object, for the cross-source comparison.
	rows, err := conn.Query(`SELECT write_object, source_id FROM access_events WHERE write_object<>'' AND ts>=? ORDER BY ts ASC`, since)
	if err != nil {
		return nil, err
	}
	for rows.Next() {
		var p, src string
		if err := rows.Scan(&p, &src); err != nil {
			rows.Close()
			return nil, err
		}
		writerSource[p] = src
	}
	rows.Close()
	rows, err = conn.Query(`SELECT path, ts, client_id, source_id FROM access_events WHERE method='GET' AND status>=200 AND status<300 AND write_object='' AND ts>=? AND (path LIKE '/notes/%' OR path LIKE '/guestbook/%' OR path LIKE '/files/%')`, since)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	readers := map[string]map[string]bool{}
	sources := map[string]map[string]bool{}
	for rows.Next() {
		var p, client, src string
		var ts float64
		if err := rows.Scan(&p, &ts, &client, &src); err != nil {
			return nil, err
		}
		key := research.ReadObject(p)
		r := byPath[key]
		if r == nil || ts < firstWrite[key] {
			continue
		}
		r.reads++
		if readers[key] == nil {
			readers[key] = map[string]bool{}
			sources[key] = map[string]bool{}
		}
		readers[key][client] = true
		sources[key][src] = true
		if src != writerSource[key] {
			r.cross++
		}
		if ts > r.last {
			r.last = ts
		}
	}
	stored := map[string]int{}
	srows, err := conn.Query("SELECT path, COUNT(*) FROM relay_events WHERE event LIKE 'stored:%' AND ts>=? GROUP BY path", since)
	if err != nil {
		return nil, err
	}
	for srows.Next() {
		var p string
		var n int
		if err := srows.Scan(&p, &n); err != nil {
			srows.Close()
			return nil, err
		}
		stored[p] = n
	}
	srows.Close()
	for _, w := range writes {
		p := fmt.Sprint(w["path"])
		r := byPath[p]
		w["stored"] = stored[p]
		w["reads"] = r.reads
		w["readers"] = len(readers[p])
		w["reader_sources"] = len(sources[p])
		w["cross_source_reads"] = r.cross
		w["last_read"] = r.last
	}
	return writes, rows.Err()
}

// Representations groups successful responses by the media type family that
// was served, per client, so a preference for text or JSON over HTML shows.
func Representations(conn *sql.DB, hours int) ([]map[string]any, error) {
	return rowsSince(conn, hours, `SELECT CASE
    WHEN content_type LIKE 'text/html%' THEN 'html'
    WHEN content_type LIKE '%json%' THEN 'json'
    WHEN content_type LIKE 'text/plain%' THEN 'text'
    WHEN content_type LIKE '%atom%' THEN 'atom'
    WHEN content_type LIKE '%xml%' OR content_type LIKE '%opml%' THEN 'xml'
    WHEN content_type LIKE 'image/%' THEN 'image'
    WHEN content_type LIKE 'text/css%' THEN 'css'
    WHEN content_type='' THEN 'none'
    ELSE 'other' END family,
  COUNT(*) responses, COUNT(DISTINCT client_id) clients,
  SUM(CASE WHEN traffic_class='engagement' THEN 1 ELSE 0 END) engagement,
  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) high
  FROM access_events WHERE ts>=? AND status>=200 AND status<300 GROUP BY family ORDER BY responses DESC`)
}

// Heatmap counts requests per UTC weekday and hour.
func Heatmap(conn *sql.DB, hours int) ([]map[string]any, error) {
	return rowsSince(conn, hours, `SELECT CAST(strftime('%w', ts, 'unixepoch') AS INTEGER) dow, CAST(strftime('%H', ts, 'unixepoch') AS INTEGER) hour,
  COUNT(*) total, COUNT(DISTINCT client_id) clients,
  SUM(CASE WHEN traffic_class='engagement' THEN 1 ELSE 0 END) engagement,
  SUM(CASE WHEN traffic_class='scanner' THEN 1 ELSE 0 END) scanner,
  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) high,
  SUM(CASE WHEN successful_write<>0 THEN 1 ELSE 0 END) writes
  FROM access_events WHERE ts>=? GROUP BY dow, hour`)
}

// LinkWrites lists GET requests that carried a write-by-link parameter.
func LinkWrites(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, `SELECT id, ts, client_id, source_id, session_id, path, query, status, link_write, write_object, successful_write, traffic_class, attribution, automation_score, SUBSTR(user_agent,1,160) user_agent
  FROM access_events WHERE link_write<>'' AND ts>=? ORDER BY ts DESC LIMIT ?`, since, clamp(limit, 1, 1000))
}

// Entrances counts the first request of every session by path and referrer
// host: where visitors land and where they came from.
func Entrances(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, `SELECT path, referer_host, COUNT(*) sessions, COUNT(DISTINCT client_id) clients,
  SUM(CASE WHEN traffic_class='engagement' THEN 1 ELSE 0 END) engagement,
  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) high
  FROM access_events a WHERE ts>=? AND id = (SELECT MIN(id) FROM access_events b WHERE b.session_id=a.session_id)
  GROUP BY path, referer_host ORDER BY sessions DESC LIMIT ?`, since, clamp(limit, 1, 500))
}

// PathsEx is TopPaths with class and method splits.
func PathsEx(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, `SELECT path, COUNT(*) hits, COUNT(DISTINCT client_id) clients, ROUND(AVG(automation_score),1) avg_automation,
  SUM(CASE WHEN status>=400 THEN 1 ELSE 0 END) errors,`+classSums+`,`+methodSums+`,`+writeSums+`
  FROM access_events WHERE ts>=? GROUP BY path ORDER BY hits DESC LIMIT ?`, since, clamp(limit, 1, 1000))
}

// UserAgentsEx is UABreakdown with class and write splits.
func UserAgentsEx(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, `SELECT user_agent, COUNT(*) hits, COUNT(DISTINCT client_id) clients, COUNT(DISTINCT source_id) sources,
  ROUND(AVG(automation_score),1) avg_auto, MIN(ts) first_seen, MAX(ts) last_seen,`+classSums+`,`+representationSums+`,`+writeSums+`
  FROM access_events WHERE ts>=? GROUP BY user_agent ORDER BY hits DESC LIMIT ?`, since, clamp(limit, 1, 1000))
}

// Ingest reports how current the data is: newest record age and the stored
// ingest offsets.
func Ingest(conn *sql.DB) (map[string]any, error) {
	out, err := SystemStats(conn)
	if err != nil {
		return nil, err
	}
	states, err := scanRows(conn, "SELECT source, inode, offset, updated_at FROM ingest_state ORDER BY source")
	if err != nil {
		return nil, err
	}
	out["ingest_state"] = states
	runs, err := scanRows(conn, "SELECT completed_at, revision, matched_records FROM measurement_runs ORDER BY completed_at DESC LIMIT 5")
	if err != nil {
		return nil, err
	}
	out["measurement_runs"] = runs
	classes, err := scanRows(conn, "SELECT traffic_class, COUNT(*) records FROM access_events GROUP BY traffic_class")
	if err != nil {
		return nil, err
	}
	out["classes"] = classes
	attribution, err := scanRows(conn, "SELECT attribution, COUNT(*) records FROM access_events GROUP BY attribution")
	if err != nil {
		return nil, err
	}
	out["attribution"] = attribution
	out["now"] = float64(time.Now().Unix())
	return out, nil
}

func toFloat(value any) float64 {
	switch v := value.(type) {
	case float64:
		return v
	case int64:
		return float64(v)
	case int:
		return float64(v)
	default:
		return 0
	}
}
