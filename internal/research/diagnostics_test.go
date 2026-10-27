package research

import (
	"github.com/onnwee/www2-observatory/internal/parsers"
	"testing"
)

func TestDiagnosticPatternsAndPublicContentBoundaries(t *testing.T) {
	for _, tc := range []struct {
		path, query, method, accept, kind, family string
		status                                    int
	}{
		{"/admin/.env", "", "GET", "", "secret-probe", "sensitive-files", 404},
		{"/build/.env.production", "", "GET", "", "secret-probe", "sensitive-files", 404},
		{"/api/orders/../../.env", "", "GET", "", "exploit-probe", "path-traversal", 404},
		{"/fetch", "file=%252e%252e%252fetc%252fpasswd", "GET", "", "exploit-probe", "path-traversal", 404},
		{"/%252e%252e/etc/passwd", "", "GET", "", "exploit-probe", "path-traversal", 404},
		{"/api", "", "POST", "text/x-component", "platform-probe", "react-server-components", 404},
		{"/__vite_rsc_findSourceMapURL", "", "GET", "", "platform-probe", "framework", 404},
		{"/wp-login.php", "", "GET", "", "platform-probe", "wordpress", 404},
		{"/.well-known/security.txt", "", "GET", "", "discovery-miss", "", 404},
		{"/favicon.ico", "", "GET", "", "asset-miss", "", 404},
		{"/notes/typo", "", "GET", "", "resource-miss", "", 404},
		{"/wall/123", "", "GET", "", "resource-miss", "", 404},
		{"/not-a-route", "", "GET", "", "unknown-miss", "", 404},
		{"/notes/.env", "", "GET", "", "resource", "", 200},
		{"/notes/reader", "set=union+select+%3Cscript%3E+..%2Fetc%2Fpasswd", "GET", "", "resource", "", 200},
		{"/wall.txt", "post=%24%7Bjndi%3Aldap%3A%2F%2Fexample%7D", "GET", "", "resource", "", 200},
		{"/search", "q=union+select", "GET", "", "resource", "", 200},
		{"/api/search", "q=union+select", "GET", "", "exploit-probe", "injection", 200},
	} {
		r := &parsers.AccessRecord{Path: tc.path, Query: tc.query, Method: tc.method, Accept: tc.accept, Status: tc.status}
		d := Diagnose(r)
		if d.Kind != tc.kind || d.Family != tc.family {
			t.Errorf("%s?%s: %+v want %s/%s", tc.path, tc.query, d, tc.kind, tc.family)
		}
	}
}

func TestOperatorDiagnosticPreservesMarkerPriority(t *testing.T) {
	d := Diagnose(&parsers.AccessRecord{Path: "/.env", Query: "obs_probe=qa", Status: 404})
	if d.Kind != "operator" || d.Family != "" {
		t.Fatalf("operator marker: %+v", d)
	}
}
