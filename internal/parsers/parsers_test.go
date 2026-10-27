package parsers

import "testing"

func TestCaddy(t *testing.T) {
	line := `{"ts":1727000000.5,"request":{"host":"WWW2.ONNWEE.ME.:443","remote_ip":"203.0.113.4","method":"GET","uri":"/search?q=coffee","headers":{"User-Agent":["curl/8.0"],"Accept":["application/json"],"Referer":["https://example.org/a?secret=x"]}},"status":200,"size":123}`
	r, err := ParseCaddyLine(line)
	if err != nil {
		t.Fatal(err)
	}
	if r.Host != "www2.onnwee.me" || r.Path != "/search" || r.Query != "q=coffee" || r.UserAgent != "curl/8.0" {
		t.Fatalf("unexpected parse: %#v", r)
	}
}

func TestCaddyHostHeaderFallback(t *testing.T) {
	r, err := ParseCaddyLine(`{"request":{"uri":"/","headers":{"Host":["www2.onnwee.me"]}}}`)
	if err != nil {
		t.Fatal(err)
	}
	if r.Host != "www2.onnwee.me" {
		t.Fatalf("host = %q", r.Host)
	}
}

func TestRelay(t *testing.T) {
	r, err := ParseRelayLine(`{"ts":"2026-09-21T00:00:00Z","event":"note.created","path":"/notes/x","content":"hello"}`)
	if err != nil {
		t.Fatal(err)
	}
	if r.Event != "note.created" || r.Content != "hello" {
		t.Fatalf("unexpected parse: %#v", r)
	}
}

func TestCaddyAttributionPolicy(t *testing.T) {
	line := `{"request":{"remote_ip":"172.20.0.249","client_ip":"203.0.113.42","uri":"/","headers":{"CF-Connecting-IP":["198.51.100.99"]}}}`
	peer, _ := ParseCaddyLine(line)
	client, _ := ParseCaddyLineWithPolicy(line, true)
	if peer.RemoteIP != "172.20.0.249" || client.RemoteIP != "203.0.113.42" || client.Attribution != "caddy-client-v2" {
		t.Fatalf("attribution policy mismatch: %#v %#v", peer, client)
	}
	missing, _ := ParseCaddyLineWithPolicy(`{"request":{"remote_ip":"172.20.0.249","client_ip":"invalid","headers":{"CF-Connecting-IP":["198.51.100.99"]}}}`, true)
	if missing.RemoteIP != "172.20.0.249" || missing.Attribution != "peer-v1" {
		t.Fatal("invalid computed client must fall back to peer, never headers")
	}
	if _, err := ParseCaddyLine(`{"request":{"uri":"/%zz"}}`); err == nil {
		t.Fatal("invalid URI accepted")
	}
}

func TestParseRelayLedgerLines(t *testing.T) {
	gb, err := ParseRelayLedgerLine("guestbook", `{"id":1790354946140,"time":"2026-09-25T16:49:07Z","name":"tester","body":"nice page","website":"https://example.test/","mood":";-)"}`)
	if err != nil || gb.Event != "guestbook" || gb.Path != "/guestbook/1790354946140" || gb.Content != "nice page" || gb.Metadata["mood"] != ";-)" {
		t.Fatalf("guestbook = %+v %v", gb, err)
	}
	note, err := ParseRelayLedgerLine("notes", `{"path":"board/today","time":"2026-09-25T17:11:33Z","body":"first\nsecond","content_type":"text/plain","version":5}`)
	if err != nil || note.Path != "/notes/board/today" || note.Event != "note" || note.Content != "first\nsecond" {
		t.Fatalf("note = %+v %v", note, err)
	}
	stored, err := ParseRelayLedgerLine("events", `{"time":"2026-09-25T17:11:33Z","request_id":"abc","method":"GET","path":"/notes/board/today?set=first","status":200,"remote_hash":"c6ec","write_type":"note","object_id":"board/today"}`)
	if err != nil || stored.Event != "stored:note" || stored.Path != "/notes/board/today" || stored.Metadata["method"] != "GET" {
		t.Fatalf("stored = %+v %v", stored, err)
	}
	if plain, err := ParseRelayLedgerLine("events", `{"time":"2026-09-25T17:11:33Z","method":"GET","path":"/","status":200}`); err != nil || plain != nil {
		t.Fatalf("non-write event should be skipped: %+v %v", plain, err)
	}
	if _, err := ParseRelayLedgerLine("bogus", `{}`); err == nil {
		t.Fatal("unknown ledger should error")
	}
}
