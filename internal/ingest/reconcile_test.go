package ingest

import (
	"github.com/onnwee/www2-observatory/internal/config"
	"github.com/onnwee/www2-observatory/internal/db"
	"os"
	"path/filepath"
	"testing"
)

func TestReconcilePreservesOriginalsAndIsIdempotent(t *testing.T) {
	dir := t.TempDir()
	log := filepath.Join(dir, "access.jsonl")
	lines := []byte("{\"ts\":1000,\"request\":{\"host\":\"www2.onnwee.me\",\"remote_ip\":\"172.20.0.249\",\"client_ip\":\"203.0.113.42\",\"uri\":\"/\",\"method\":\"GET\"},\"status\":200}\n" +
		"{\"ts\":3000,\"request\":{\"host\":\"www2.onnwee.me\",\"remote_ip\":\"172.20.0.249\",\"client_ip\":\"203.0.113.43\",\"uri\":\"/help.txt\",\"method\":\"GET\"},\"status\":200}\n")
	if err := os.WriteFile(log, lines, 0600); err != nil {
		t.Fatal(err)
	}
	cfg := config.Config{DBPath: filepath.Join(dir, "db.sqlite3"), CaddyLog: log, AllowedHosts: "www2.onnwee.me", SessionMinutes: 30}
	i := New(cfg, []byte("test-key"))
	if _, err := i.IngestOnce(); err != nil {
		t.Fatal(err)
	}
	conn, err := db.Connect(cfg.DBPath)
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	var before string
	conn.QueryRow("SELECT source_id FROM access_events ORDER BY id LIMIT 1").Scan(&before)
	i.cfg.TrustCaddyClientIP = true
	result, err := i.ReconcileAccess()
	if err != nil {
		t.Fatal(err)
	}
	if result["matched"] != 2 {
		t.Fatal(result)
	}
	var count int
	conn.QueryRow("SELECT COUNT(DISTINCT source_id) FROM access_events").Scan(&count)
	if count != 2 {
		t.Fatal("proxy sources not separated")
	}
	var original, session string
	conn.QueryRow("SELECT original_source_id,session_id FROM access_events ORDER BY id LIMIT 1").Scan(&original, &session)
	if original != before {
		t.Fatal("original evidence lost")
	}
	if _, err := i.ReconcileAccess(); err != nil {
		t.Fatal(err)
	}
	var again string
	conn.QueryRow("SELECT session_id FROM access_events ORDER BY id LIMIT 1").Scan(&again)
	if again != session {
		t.Fatal("session replay is not idempotent")
	}
	if _, err := i.IngestOnce(); err != nil {
		t.Fatal(err)
	}
	conn.QueryRow("SELECT COUNT(*) FROM access_events").Scan(&count)
	if count != 2 {
		t.Fatal("replay duplicated records")
	}
}
