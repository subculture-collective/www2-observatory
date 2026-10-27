package api

import (
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"strings"
	"testing"
	"time"

	"github.com/onnwee/www2-observatory/internal/config"
	"github.com/onnwee/www2-observatory/internal/db"
)

func TestDiagnosticAPIAndExportShareFiltersAndAuth(t *testing.T) {
	cfg := config.Config{DBPath: filepath.Join(t.TempDir(), "qa.db"), Token: "test-only", SessionMinutes: 30}
	conn, err := db.Connect(cfg.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	for _, row := range []struct {
		path string
		age  time.Duration
	}{{"/.env", time.Hour}, {"/.env", 48 * time.Hour}, {"/notes/missing", time.Hour}} {
		_, err = conn.Exec(`INSERT INTO access_events(ts,source_id,client_id,session_id,method,path,status) VALUES(?,'src-test','cli-test','ses-test','GET',?,404)`, float64(time.Now().Add(-row.age).Unix()), row.path)
		if err != nil {
			t.Fatal(err)
		}
	}
	if err = db.RefreshDiagnostics(conn); err != nil {
		t.Fatal(err)
	}
	conn.Close()
	h := NewServer(cfg)
	for _, path := range []string{"/api/recent?hours=24&kind=secret-probe&status=404", "/api/export.ndjson?hours=24&kind=secret-probe&status=404"} {
		r := httptest.NewRequest("GET", path, nil)
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != http.StatusUnauthorized {
			t.Fatalf("unprotected %s = %d", path, w.Code)
		}
		r.Header.Set("Authorization", "Bearer test-only")
		w = httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != 200 {
			t.Fatalf("%s = %d %s", path, w.Code, w.Body.String())
		}
		if strings.Contains(path, "export") {
			var row map[string]any
			if err := json.Unmarshal(w.Body.Bytes(), &row); err != nil || row["path"] != "/.env" {
				t.Fatalf("export did not match single filtered row: %s", w.Body.String())
			}
		} else {
			var rows []map[string]any
			if err := json.Unmarshal(w.Body.Bytes(), &rows); err != nil || len(rows) != 1 {
				t.Fatalf("filtered list: %s", w.Body.String())
			}
		}
	}
	r := httptest.NewRequest("GET", "/api/diagnostics?hours=24", nil)
	r.Header.Set("Authorization", "Bearer test-only")
	w := httptest.NewRecorder()
	h.ServeHTTP(w, r)
	var report struct {
		Summary struct{ Requests, Probes int }
	}
	if err := json.Unmarshal(w.Body.Bytes(), &report); err != nil || report.Summary.Requests != 2 || report.Summary.Probes != 1 {
		t.Fatalf("diagnostics: %s", w.Body.String())
	}
	for _, query := range []string{"since=NaN", "since=-1", "since=200&until=100", "until=Infinity"} {
		r := httptest.NewRequest("GET", "/api/recent?"+query, nil)
		r.Header.Set("Authorization", "Bearer test-only")
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != 400 {
			t.Errorf("invalid replay range %s = %d", query, w.Code)
		}
	}
}
