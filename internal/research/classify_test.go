package research

import (
	"github.com/onnwee/www2-observatory/internal/parsers"
	"testing"
)

func TestClassification(t *testing.T) {
	for _, tc := range []struct {
		path, ua, query string
		status          int
		want            string
	}{
		{"/.env.production", "Mozilla/5.0", "", 404, "scanner"},
		{"/notes/.env", "curl/8", "", 200, "engagement"},
		{"/missing.json", "curl/8", "", 404, "other"},
		{"/help.txt", "Deadweb-Operator/1.0", "", 200, "operator"},
		{"/", "Mozilla/5.0", "obs_probe=deployment", 200, "operator"},
		{"/notes/", "curl/8", "", 200, "engagement"},
	} {
		got, _ := Classify(&parsers.AccessRecord{Path: tc.path, UserAgent: tc.ua, Query: tc.query, Status: tc.status, Method: "GET"})
		if got != tc.want {
			t.Errorf("%s got %s want %s", tc.path, got, tc.want)
		}
	}
}

func TestSuccessfulWriteRequiresSupportedSuccess(t *testing.T) {
	for _, tc := range []struct {
		method, path, location string
		status                 int
		success                bool
		object                 string
	}{
		{"POST", "/guestbook/", "/guestbook/123", 303, true, "/guestbook/123"},
		{"PUT", "/notes/a", "", 200, true, "/notes/a"},
		{"POST", "/notes/", "/notes/a", 303, true, "/notes/a"},
		{"POST", "/guestbook/", "https://other.example/guestbook/123", 303, false, ""},
		{"POST", "/wall/", "/wall/", 303, true, ""},
		{"POST", "/guestbook/", "", 200, true, ""},
		{"PUT", "/notes/a", "", 422, false, ""},
		{"POST", "/.env", "", 200, false, ""},
	} {
		r := &parsers.AccessRecord{Method: tc.method, Path: tc.path, Location: tc.location, Status: tc.status}
		if SuccessfulWrite(r) != tc.success || WriteObject(r) != tc.object {
			t.Errorf("%+v got success %v object %s", tc, SuccessfulWrite(r), WriteObject(r))
		}
	}
}

func TestLinkWritesAreRecognisedAsWrites(t *testing.T) {
	wall := &parsers.AccessRecord{Method: "GET", Path: "/wall/", Query: "name=x&post=hello", Status: 200}
	if LinkWriteParam(wall) != "post" || !SuccessfulWrite(wall) || WriteObject(wall) != "" {
		t.Fatalf("wall link write: param=%q success=%v object=%q", LinkWriteParam(wall), SuccessfulWrite(wall), WriteObject(wall))
	}
	note := &parsers.AccessRecord{Method: "GET", Path: "/notes/board/today", Query: "append=line", Status: 200}
	if WriteObject(note) != "/notes/board/today" || !SuccessfulWrite(note) {
		t.Fatalf("note link write not recognised")
	}
	gb := &parsers.AccessRecord{Method: "GET", Path: "/guestbook/", Query: "body=hi", Status: 200, Location: "/guestbook/123"}
	if WriteObject(gb) != "/guestbook/123" {
		t.Fatalf("guestbook link write object = %q", WriteObject(gb))
	}
	for _, r := range []*parsers.AccessRecord{
		{Method: "GET", Path: "/wall/", Query: "after=5", Status: 200},
		{Method: "GET", Path: "/notes/board/", Query: "set=x", Status: 200},
		{Method: "HEAD", Path: "/wall/", Query: "post=x", Status: 200},
		{Method: "GET", Path: "/wall/", Query: "post=x", Status: 429},
	} {
		if SuccessfulWrite(r) || WriteObject(r) != "" {
			t.Fatalf("%s %s?%s %d should not count as a write", r.Method, r.Path, r.Query, r.Status)
		}
	}
	if !IsResource("/chat/") {
		t.Fatal("/chat/ is a relay resource")
	}
}
