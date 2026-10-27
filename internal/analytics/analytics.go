package analytics

import (
	"database/sql"
	"encoding/json"
	"regexp"
	"sort"
	"strings"
	"time"
)

var tokenRE = regexp.MustCompile(`(?U)(?:\b[A-Z][A-Z0-9:_-]{2,}\b|\b[a-zA-Z][a-zA-Z0-9_-]{3,}\b)`)

var stop = map[string]bool{
	"this": true, "that": true, "with": true, "from": true, "have": true, "will": true, "your": true, "what": true, "when": true, "where": true, "there": true, "here": true, "http": true, "https": true,
	"notes": true, "guestbook": true, "wall": true, "text": true, "html": true, "json": true, "www2": true, "onnwee": true, "content": true, "public": true, "server": true, "page": true, "pages": true,
}

func Summary(conn *sql.DB, hours int) (map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	row, err := scanOne(conn, `SELECT COUNT(*) requests, COUNT(DISTINCT client_id) clients, COUNT(DISTINCT session_id) sessions,
                  SUM(CASE WHEN method IN ('POST','PUT','PATCH','DELETE') THEN 1 ELSE 0 END) writes,
                  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) high_auto,
                  SUM(CASE WHEN automation_level='medium' THEN 1 ELSE 0 END) med_auto,
                  SUM(CASE WHEN automation_level='low' THEN 1 ELSE 0 END) low_auto,
                  COALESCE(ROUND(AVG(automation_score), 1), 0) avg_score,
                  COALESCE(SUM(response_bytes), 0) total_bytes
           FROM access_events WHERE ts>=?`, since)
	if err != nil {
		return nil, err
	}
	prevSince := since - float64(hours*3600)
	prev, err := scanOne(conn, `SELECT COUNT(*) prev_requests, COUNT(DISTINCT client_id) prev_clients FROM access_events WHERE ts>=? AND ts<?`, prevSince, since)
	if err != nil {
		return nil, err
	}
	for key, value := range prev {
		row[key] = value
	}
	row["hours"] = hours
	return row, nil
}

func Recent(conn *sql.DB, limit int, method, level string, status *int, search string) ([]map[string]any, error) {
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
		clauses = append(clauses, "status = ?")
		args = append(args, *status)
	}
	if search != "" {
		clauses = append(clauses, "(path LIKE ? OR user_agent LIKE ? OR client_id LIKE ? OR referer LIKE ?)")
		pattern := "%" + search + "%"
		args = append(args, pattern, pattern, pattern, pattern)
	}
	where := ""
	if len(clauses) > 0 {
		where = " WHERE " + strings.Join(clauses, " AND ")
	}
	args = append(args, clamp(limit, 1, 500))
	return scanRows(conn, "SELECT * FROM access_events"+where+" ORDER BY ts DESC LIMIT ?", args...)
}

func Timeline(conn *sql.DB, hours int) ([]map[string]any, error) {
	return rowsSince(conn, hours, `SELECT strftime('%Y-%m-%d %H:00', ts, 'unixepoch') as bucket,
                  COUNT(*) as total,
                  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) as high,
                  SUM(CASE WHEN automation_level='medium' THEN 1 ELSE 0 END) as medium,
                  SUM(CASE WHEN automation_level='low' THEN 1 ELSE 0 END) as low,
                  SUM(CASE WHEN status >= 200 AND status < 300 THEN 1 ELSE 0 END) as s2xx,
                  SUM(CASE WHEN status >= 300 AND status < 400 THEN 1 ELSE 0 END) as s3xx,
                  SUM(CASE WHEN status >= 400 AND status < 500 THEN 1 ELSE 0 END) as s4xx,
                  SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) as s5xx,
                  COALESCE(SUM(response_bytes), 0) as bytes
           FROM access_events WHERE ts >= ? GROUP BY bucket ORDER BY bucket ASC`)
}

func TopPaths(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, `SELECT path, COUNT(*) hits, COUNT(DISTINCT client_id) clients, ROUND(AVG(automation_score),2) avg_automation
           FROM access_events WHERE ts>=? GROUP BY path ORDER BY hits DESC LIMIT ?`, since, limit)
}

func Referrers(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, `SELECT referer_host, COUNT(*) hits, COUNT(DISTINCT client_id) clients
           FROM access_events WHERE ts>=? AND referer_host<>'' GROUP BY referer_host ORDER BY hits DESC LIMIT ?`, since, limit)
}

func StatusDistribution(conn *sql.DB, hours int) ([]map[string]any, error) {
	return rowsSince(conn, hours, `SELECT status, COUNT(*) as count FROM access_events WHERE ts>=? GROUP BY status ORDER BY count DESC`)
}

func MethodDistribution(conn *sql.DB, hours int) ([]map[string]any, error) {
	return rowsSince(conn, hours, `SELECT method, COUNT(*) as count FROM access_events WHERE ts>=? GROUP BY method ORDER BY count DESC`)
}

func UABreakdown(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, `SELECT user_agent, COUNT(*) as hits, COUNT(DISTINCT client_id) as clients, ROUND(AVG(automation_score), 1) as avg_auto
           FROM access_events WHERE ts>=? GROUP BY user_agent ORDER BY hits DESC LIMIT ?`, since, limit)
}

func Signals(conn *sql.DB, hours int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	rows, err := conn.Query("SELECT signals_json,client_id FROM access_events WHERE ts>=?", since)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	counter := map[string]int{}
	clients := map[string]map[string]bool{}
	for rows.Next() {
		var raw, clientID string
		if err := rows.Scan(&raw, &clientID); err != nil {
			return nil, err
		}
		var signals []string
		_ = json.Unmarshal([]byte(raw), &signals)
		for _, signal := range signals {
			counter[signal]++
			if clients[signal] == nil {
				clients[signal] = map[string]bool{}
			}
			clients[signal][clientID] = true
		}
	}
	keys := make([]string, 0, len(counter))
	for key := range counter {
		keys = append(keys, key)
	}
	sort.Slice(keys, func(i, j int) bool { return counter[keys[i]] > counter[keys[j]] })
	out := []map[string]any{}
	for _, key := range keys {
		out = append(out, map[string]any{"signal": key, "events": counter[key], "clients": len(clients[key])})
	}
	return out, rows.Err()
}

func Sessions(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	rows, err := scanRows(conn, `SELECT session_id,client_id,MIN(ts) started,MAX(ts) ended,COUNT(*) requests,
                  COUNT(DISTINCT path) unique_paths,MAX(automation_score) max_automation,
                  GROUP_CONCAT(method || ' ' || path, ' → ') trail
           FROM access_events WHERE ts>=? GROUP BY session_id ORDER BY ended DESC LIMIT ?`, since, limit)
	if err != nil {
		return nil, err
	}
	for _, row := range rows {
		if trail, ok := row["trail"].(string); ok && len(trail) > 4000 {
			row["trail"] = trail[:4000]
		}
	}
	return rows, nil
}

func Writes(conn *sql.DB, limit int) ([]map[string]any, error) {
	return scanRows(conn, "SELECT * FROM relay_events ORDER BY ts DESC LIMIT ?", clamp(limit, 1, 500))
}

func Conventions(conn *sql.DB, hours, limit int) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	rows, err := conn.Query("SELECT ts,client_id,path,content FROM relay_events WHERE ts>=?", since)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	type candidate struct {
		token string
		uses  int
		first float64
		last  float64
		set   map[string]bool
	}
	candidates := map[string]*candidate{}
	for rows.Next() {
		var ts float64
		var clientID, path, content string
		if err := rows.Scan(&ts, &clientID, &path, &content); err != nil {
			return nil, err
		}
		seen := map[string]bool{}
		for _, token := range tokenRE.FindAllString(path+" "+content, -1) {
			key := token
			if key != strings.ToUpper(key) {
				key = strings.ToLower(key)
			}
			if stop[strings.ToLower(key)] || len(key) > 48 {
				continue
			}
			c := candidates[key]
			if c == nil {
				c = &candidate{token: key, first: ts, last: ts, set: map[string]bool{}}
				candidates[key] = c
			}
			c.uses++
			if ts < c.first {
				c.first = ts
			}
			if ts > c.last {
				c.last = ts
			}
			seen[key] = true
		}
		for key := range seen {
			if clientID != "" {
				candidates[key].set[clientID] = true
			}
		}
	}
	list := []*candidate{}
	for _, c := range candidates {
		if c.uses >= 2 {
			list = append(list, c)
		}
	}
	sort.Slice(list, func(i, j int) bool {
		if len(list[i].set) == len(list[j].set) {
			return list[i].uses > list[j].uses
		}
		return len(list[i].set) > len(list[j].set)
	})
	if len(list) > limit {
		list = list[:limit]
	}
	out := []map[string]any{}
	for _, c := range list {
		out = append(out, map[string]any{"token": c.token, "uses": c.uses, "clients": len(c.set), "first_seen": c.first, "last_seen": c.last})
	}
	return out, rows.Err()
}

func SystemStats(conn *sql.DB) (map[string]any, error) {
	out := map[string]any{}
	queries := map[string]string{
		"access_records": "SELECT COUNT(*) FROM access_events",
		"relay_records":  "SELECT COUNT(*) FROM relay_events",
		"first_ts":       "SELECT COALESCE(MIN(ts), 0) FROM access_events",
		"last_ts":        "SELECT COALESCE(MAX(ts), 0) FROM access_events",
		"page_size":      "PRAGMA page_size",
		"page_count":     "PRAGMA page_count",
		"journal_mode":   "PRAGMA journal_mode",
	}
	for key, query := range queries {
		row, err := scanOne(conn, query)
		if err != nil {
			return nil, err
		}
		for _, value := range row {
			out[key] = value
		}
	}
	out["db_size_bytes"] = toInt64(out["page_size"]) * toInt64(out["page_count"])
	delete(out, "page_size")
	delete(out, "page_count")
	return out, nil
}

func rowsSince(conn *sql.DB, hours int, query string) ([]map[string]any, error) {
	since := float64(time.Now().Unix()) - float64(hours*3600)
	return scanRows(conn, query, since)
}

func scanOne(conn *sql.DB, query string, args ...any) (map[string]any, error) {
	rows, err := scanRows(conn, query, args...)
	if err != nil || len(rows) == 0 {
		return map[string]any{}, err
	}
	return rows[0], nil
}

func scanRows(conn *sql.DB, query string, args ...any) ([]map[string]any, error) {
	rows, err := conn.Query(query, args...)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	cols, err := rows.Columns()
	if err != nil {
		return nil, err
	}
	out := []map[string]any{}
	for rows.Next() {
		values := make([]any, len(cols))
		ptrs := make([]any, len(cols))
		for i := range values {
			ptrs[i] = &values[i]
		}
		if err := rows.Scan(ptrs...); err != nil {
			return nil, err
		}
		row := map[string]any{}
		for i, col := range cols {
			row[col] = normalizeValue(values[i])
		}
		out = append(out, row)
	}
	return out, rows.Err()
}

func normalizeValue(value any) any {
	switch v := value.(type) {
	case []byte:
		return string(v)
	case nil:
		return nil
	default:
		return v
	}
}

func toInt64(value any) int64 {
	switch v := value.(type) {
	case int64:
		return v
	case int:
		return int64(v)
	case float64:
		return int64(v)
	default:
		return 0
	}
}

func clamp(value, min, max int) int {
	if value < min {
		return min
	}
	if value > max {
		return max
	}
	return value
}
