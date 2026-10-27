package analytics

import (
	"github.com/onnwee/www2-observatory/internal/db"
	"path/filepath"
	"testing"
	"time"
)

func TestDiagnosticBackfillCountsFiltersAndPreservesResearchEvidence(t *testing.T) {
	conn, err := db.Connect(filepath.Join(t.TempDir(), "test.db"))
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	for _, r := range []struct {
		path, query, source, ua string
		status                  int
		age                     time.Duration
	}{
		{"/admin/.env", "", "a", "claimed-crawler/1", 404, time.Hour},
		{"/api/orders/../.env", "", "a", "claimed-crawler/2", 200, time.Hour},
		{"/favicon.ico", "", "b", "browser", 404, time.Hour},
		{"/notes/missing", "", "b", "browser", 404, time.Hour},
		{"/notes/x", "set=union+select", "c", "curl", 200, time.Hour},
		{"/help.txt", "", "c", "curl", 502, time.Hour},
		{"/.env", "", "old", "old", 404, 48 * time.Hour},
	} {
		_, err := conn.Exec(`INSERT INTO access_events(ts,source_id,client_id,session_id,method,path,query,status,user_agent,traffic_class,classification_reason,attribution) VALUES(?,?,?,?,?,?,?,?,?,'other','preserve this','caddy-client-v2')`, float64(time.Now().Add(-r.age).Unix()), r.source, r.source+r.ua, "s"+r.source, "GET", r.path, r.query, r.status, r.ua)
		if err != nil {
			t.Fatal(err)
		}
	}
	for j := 0; j < 2; j++ {
		if err := db.RefreshDiagnostics(conn); err != nil {
			t.Fatal(err)
		}
	}
	var retained int
	if err := conn.QueryRow(`SELECT COUNT(*) FROM access_events WHERE traffic_class='other' AND classification_reason='preserve this' AND attribution='caddy-client-v2'`).Scan(&retained); err != nil || retained != 7 {
		t.Fatalf("changed historical evidence %d %v", retained, err)
	}
	r, err := Diagnostics(conn, 24)
	if err != nil {
		t.Fatal(err)
	}
	s := r["summary"].(map[string]any)
	for k, want := range map[string]int64{"requests": 6, "probes": 2, "probe_2xx": 1, "missing": 3, "probe_404": 1, "asset_misses": 1, "resource_misses": 1, "server_errors": 1, "pending": 0} {
		if toInt64(s[k]) != want {
			t.Errorf("%s = %v want %d", k, s[k], want)
		}
	}
	for _, option := range []EventOptions{{Hours: 24, Kind: "secret-probe"}, {Hours: 24, Family: "path-traversal"}, {Hours: 24, Path: "/favicon.ico"}} {
		rows, err := RecentEx(conn, 100, "", "", nil, "", "", "", false, option)
		if err != nil || len(rows) != 1 {
			t.Errorf("filter %+v = %v %v", option, rows, err)
		}
	}
	rows, err := RecentEx(conn, 100, "", "", nil, "", "", "", false, EventOptions{Hours: 24})
	if err != nil || len(rows) != 6 {
		t.Fatalf("window filter %d %v", len(rows), err)
	}
	var boundary float64
	if err := conn.QueryRow("SELECT ts FROM access_events WHERE path='/favicon.ico'").Scan(&boundary); err != nil {
		t.Fatal(err)
	}
	atBoundary, err := RecentEx(conn, 100, "", "", nil, "", "", "", false, EventOptions{Hours: 24, Path: "/favicon.ico", Since: boundary, Until: boundary + 1})
	if err != nil || len(atBoundary) != 1 {
		t.Fatalf("inclusive replay start: %v %v", atBoundary, err)
	}
	beforeBoundary, err := RecentEx(conn, 100, "", "", nil, "", "", "", false, EventOptions{Hours: 24, Path: "/favicon.ico", Since: boundary - 1, Until: boundary})
	if err != nil || len(beforeBoundary) != 0 {
		t.Fatalf("exclusive replay end: %v %v", beforeBoundary, err)
	}
}
