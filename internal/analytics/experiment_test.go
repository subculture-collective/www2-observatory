package analytics

import (
	"github.com/onnwee/www2-observatory/internal/db"
	"path/filepath"
	"testing"
	"time"
)

func TestExperimentOrderedFunnelAndExclusions(t *testing.T) {
	conn, err := db.Connect(filepath.Join(t.TempDir(), "db.sqlite3"))
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	start := time.Now().Add(-4 * time.Hour).Unix()
	add := func(client, class, attr, method, path, ct, object string, minute, status, write int) {
		t.Helper()
		_, err := conn.Exec(`INSERT INTO access_events(ts,source_id,client_id,session_id,method,path,content_type,attribution,traffic_class,write_object,successful_write,status)
   VALUES(?,?,?,?,?,?,?,?,?,?,?,?)`, start+int64(minute*60), client, client, "session-"+client, method, path, ct, attr, class, object, write, status)
		if err != nil {
			t.Fatal(err)
		}
	}
	for _, client := range []string{"a", "operator", "scanner", "legacy"} {
		class, attr := "engagement", "caddy-client-v2"
		if client == "operator" || client == "scanner" {
			class = client
		}
		if client == "legacy" {
			attr = "legacy-peer-v1"
		}
		add(client, class, attr, "GET", "/", "text/html", "", 0, 200, 0)
		add(client, class, attr, "GET", "/help.txt", "text/plain", "", 1, 200, 0)
		add(client, class, attr, "GET", "/feed.json", "application/json", "", 2, 200, 0)
		add(client, class, attr, "PUT", "/notes/"+client, "application/json", "/notes/"+client, 3, 200, 1)
		add(client, class, attr, "GET", "/notes/"+client, "text/plain", "", 4, 200, 0) // immediate verification is not a return
		add(client, class, attr, "GET", "/notes/"+client, "text/plain", "", 40, 200, 0)
	}
	// A visitor who skips capability discovery must not advance the ordered funnel.
	add("b", "engagement", "caddy-client-v2", "GET", "/", "text/html", "", 0, 200, 0)
	add("b", "engagement", "caddy-client-v2", "GET", "/feed.json", "application/json", "", 2, 200, 0)
	add("b", "engagement", "caddy-client-v2", "GET", "/notes/a", "text/plain", "", 41, 200, 0)
	// A requested format that the server ignored is not a retrieved representation.
	add("c", "engagement", "caddy-client-v2", "GET", "/", "text/html", "", 0, 200, 0)
	add("c", "engagement", "caddy-client-v2", "GET", "/help.txt", "text/plain", "", 1, 200, 0)
	add("c", "engagement", "caddy-client-v2", "GET", "/", "text/html", "", 2, 200, 0)
	if _, err := conn.Exec("UPDATE access_events SET query='format=json' WHERE client_id='c' AND path='/'"); err != nil {
		t.Fatal(err)
	}
	report, err := Experiment(conn, 24, 30)
	if err != nil {
		t.Fatal(err)
	}
	for i, want := range []int{3, 2, 1, 1, 1} {
		if report.Stages[i].Clients != want {
			t.Errorf("stage %d got %d want %d", i, report.Stages[i].Clients, want)
		}
	}
	if report.SuccessfulWrites != 1 || report.ReturningClients != 1 || report.CrossSourceReads != 1 {
		t.Fatalf("unexpected milestones: %+v", report)
	}
	// An operator overwriting the object prevents attribution of later reads to a's old write.
	add("operator", "operator", "caddy-client-v2", "PUT", "/notes/a", "application/json", "/notes/a", 35, 200, 1)
	report, err = Experiment(conn, 24, 30)
	if err != nil {
		t.Fatal(err)
	}
	if report.ReturningClients != 0 || report.CrossSourceReads != 0 || report.Stages[4].Clients != 0 {
		t.Fatalf("attributed a read after an operator overwrite: %+v", report)
	}
}
