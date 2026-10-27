package analytics

import (
	"path/filepath"
	"testing"
	"time"

	"github.com/onnwee/www2-observatory/internal/db"
)

func TestExploreAggregationsCountLinkWritesAndReads(t *testing.T) {
	conn, err := db.Connect(filepath.Join(t.TempDir(), "db.sqlite3"))
	if err != nil {
		t.Fatal(err)
	}
	defer conn.Close()
	start := time.Now().Add(-3 * time.Hour).Unix()
	add := func(client, source, method, path, query, ct, class, object, link string, minute, status, write int) {
		t.Helper()
		if _, err := conn.Exec(`INSERT INTO access_events(ts,source_id,client_id,session_id,method,path,query,content_type,attribution,traffic_class,write_object,successful_write,link_write,status,user_agent)
   VALUES(?,?,?,?,?,?,?,?,'caddy-client-v2',?,?,?,?,?,'ua/'||?)`, start+int64(minute*60), source, client, "s-"+client, method, path, query, ct, class, object, write, link, status, client); err != nil {
			t.Fatal(err)
		}
	}
	// writer: reads help, writes a note by link twice, wall by link once
	add("w", "srcw", "GET", "/help.txt", "", "text/plain", "engagement", "", "", 0, 200, 0)
	add("w", "srcw", "GET", "/notes/board/x", "set=hi", "text/plain", "engagement", "/notes/board/x", "set", 1, 200, 1)
	add("w", "srcw", "GET", "/notes/board/x", "append=more", "text/plain", "engagement", "/notes/board/x", "append", 2, 200, 1)
	add("w", "srcw", "GET", "/wall/", "post=hey", "text/html", "engagement", "", "post", 3, 200, 1)
	// refused link write
	add("z", "srcz", "GET", "/wall/", "post=spam", "", "other", "", "post", 4, 429, 0)
	// reader from another source, and a scanner
	add("r", "srcr", "GET", "/notes/board/x", "", "text/plain", "engagement", "", "", 10, 200, 0)
	add("r", "srcr", "GET", "/notes/board/x", "", "text/plain", "engagement", "", "", 11, 200, 0)
	add("s", "srcs", "GET", "/.env", "", "", "scanner", "", "", 12, 404, 0)

	sum, err := SummaryEx(conn, 24)
	if err != nil {
		t.Fatal(err)
	}
	if toInt64(sum["writes"]) != 3 || toInt64(sum["link_writes"]) != 4 || toInt64(sum["scanner"]) != 1 || toInt64(sum["engagement"]) != 6 {
		t.Fatalf("summary = %v", sum)
	}

	tl, err := TimelineEx(conn, 24, "hour")
	if err != nil {
		t.Fatal(err)
	}
	var writes, linkWrites int64
	for _, b := range tl {
		writes += toInt64(b["writes"])
		linkWrites += toInt64(b["link_writes"])
	}
	if writes != 3 || linkWrites != 4 {
		t.Fatalf("timeline writes=%d link=%d", writes, linkWrites)
	}

	clients, err := Clients(conn, 24, 50, "writers", "writes")
	if err != nil {
		t.Fatal(err)
	}
	if len(clients) != 1 || clients[0]["client_id"] != "w" || toInt64(clients[0]["link_writes"]) != 3 {
		t.Fatalf("writers = %v", clients)
	}
	if all, _ := Clients(conn, 24, 50, "", ""); len(all) != 4 {
		t.Fatalf("all clients = %d", len(all))
	}

	objects, err := Objects(conn, 24)
	if err != nil {
		t.Fatal(err)
	}
	if len(objects) != 1 {
		t.Fatalf("objects = %v", objects)
	}
	o := objects[0]
	if o["path"] != "/notes/board/x" || toInt64(o["writes"]) != 2 || o["reads"] != 2 || o["readers"] != 1 || o["cross_source_reads"] != 2 {
		t.Fatalf("object = %v", o)
	}

	links, err := LinkWrites(conn, 24, 10)
	if err != nil || len(links) != 4 {
		t.Fatalf("link writes = %d %v", len(links), err)
	}

	recent, err := RecentEx(conn, 50, "", "", nil, "", "engagement", "", true)
	if err != nil || len(recent) != 3 {
		t.Fatalf("recent engagement link writes = %d %v", len(recent), err)
	}
	four := 4
	if refused, _ := RecentEx(conn, 50, "", "", &four, "", "", "", false); len(refused) != 2 {
		t.Fatalf("4xx filter = %d", len(refused))
	}

	detail, err := ClientDetail(conn, "w", 50, 30)
	if err != nil {
		t.Fatal(err)
	}
	if len(detail["sessions"].([]map[string]any)) != 1 || len(detail["objects"].([]map[string]any)) != 1 {
		t.Fatalf("detail = %v", detail)
	}
	if _, err := ClientDetail(conn, "nobody", 10, 30); err == nil {
		t.Fatal("unknown client should error")
	}

	reps, err := Representations(conn, 24)
	if err != nil || len(reps) == 0 {
		t.Fatalf("representations = %v %v", reps, err)
	}
	if _, err := Heatmap(conn, 24); err != nil {
		t.Fatal(err)
	}
	if _, err := Entrances(conn, 24, 10); err != nil {
		t.Fatal(err)
	}
	ing, err := Ingest(conn)
	if err != nil || toInt64(ing["access_records"]) != 8 {
		t.Fatalf("ingest = %v %v", ing, err)
	}
}
