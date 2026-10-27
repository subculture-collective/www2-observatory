// Package research defines conservative observable milestones, not agent identity.
package research

import (
	"github.com/onnwee/www2-observatory/internal/parsers"
	"net/url"
	"strings"
)

func IsResource(path string) bool {
	switch path {
	case "/", "/robots.txt", "/sitemap.xml", "/sitemap.txt", "/sitemap.html", "/index.txt", "/README.TXT", "/help.txt", "/search", "/links.html", "/links.txt", "/blogroll.opml", "/about.html", "/now.html", "/whatsnew.html", "/recent.txt", "/buttons.html", "/webring/", "/uptime.txt", "/humans.txt", "/feed.json", "/feed.ndjson", "/feed.atom", "/opensearch.xml", "/manifest.json", "/wall.txt", "/wall.json", "/nodeinfo/2.1":
		return true
	}
	for _, prefix := range []string{"/notes/", "/guestbook/", "/wall/", "/chat/", "/files/", "/archive/", "/tmp/", "/reference/", "/.well-known/", "/cgi-bin/"} {
		if strings.HasPrefix(path, prefix) {
			return true
		}
	}
	return false
}

func Classify(r *parsers.AccessRecord) (string, string) {
	q, _ := url.ParseQuery(r.Query)
	if strings.HasPrefix(r.UserAgent, "Deadweb-Operator/") || q.Get("obs_probe") != "" {
		return "operator", "self-declared operator marker; not authenticated identity"
	}
	p := strings.ToLower(r.Path)
	for _, prefix := range []string{"/.env", "/.aws/", "/.ssh/", "/.git/", "/.docker/", "/.vscode/", "/wp-admin", "/wp-login", "/vendor/phpunit/", "/cgi-bin/.%", "/actuator/"} {
		if strings.HasPrefix(p, prefix) {
			return "scanner", "known credential or exploit-probe path"
		}
	}
	for _, exact := range []string{"/config.json", "/api/config", "/.bash_history", "/.bashrc", "/phpinfo.php", "/server-status"} {
		if p == exact {
			return "scanner", "known configuration or diagnostic-probe path"
		}
	}
	if IsResource(r.Path) && ((r.Status >= 200 && r.Status < 300) || WriteObject(r) != "") {
		return "engagement", "successful request to a relay resource; intent unverified"
	}
	return "other", "unclassified traffic; a 404 alone is not scanning evidence"
}

// LinkWriteParam reports which write-by-link query parameter a GET carries:
// "post" on the wall, "body" on the guestbook, "set" or "append" on a note.
// The relay added these on 2026-09-25. Only the HTTP outcome is observable
// here; the relay may still have deduplicated or refused the content.
func LinkWriteParam(r *parsers.AccessRecord) string {
	if strings.ToUpper(r.Method) != "GET" || r.Query == "" {
		return ""
	}
	q, err := url.ParseQuery(r.Query)
	if err != nil {
		return ""
	}
	switch {
	case (r.Path == "/wall/" || r.Path == "/wall.txt" || r.Path == "/wall.json" || r.Path == "/chat/") && q.Get("post") != "":
		return "post"
	case (r.Path == "/guestbook/" || r.Path == "/cgi-bin/guestbook.cgi") && q.Get("body") != "":
		return "body"
	case strings.HasPrefix(r.Path, "/notes/") && len(r.Path) > len("/notes/") && !strings.HasSuffix(r.Path, "/"):
		if q.Has("set") {
			return "set"
		}
		if q.Get("append") != "" {
			return "append"
		}
	}
	return ""
}

// WriteObject requires a supported successful write. Collection reads cannot prove
// that a particular wall entry was retrieved, so wall writes have no object key.
func WriteObject(r *parsers.AccessRecord) string {
	method := strings.ToUpper(r.Method)
	if method == "PUT" && strings.HasPrefix(r.Path, "/notes/") && len(r.Path) > len("/notes/") && r.Status >= 200 && r.Status < 300 {
		return r.Path
	}
	if param := LinkWriteParam(r); param != "" && r.Status >= 200 && r.Status < 300 {
		switch param {
		case "set", "append":
			return r.Path
		case "body":
			if loc, err := url.Parse(r.Location); err == nil && !loc.IsAbs() && strings.HasPrefix(loc.Path, "/guestbook/") && len(loc.Path) > len("/guestbook/") {
				return loc.Path
			}
		}
		return ""
	}
	if method != "POST" || r.Status != 303 {
		return ""
	}
	prefix := ""
	switch r.Path {
	case "/notes/":
		prefix = "/notes/"
	case "/guestbook/", "/cgi-bin/guestbook.cgi":
		prefix = "/guestbook/"
	case "/files/":
		prefix = "/files/"
	}
	if prefix == "" {
		return ""
	}
	loc, err := url.Parse(r.Location)
	if err != nil || loc.IsAbs() || loc.Host != "" || !strings.HasPrefix(loc.Path, prefix) || len(loc.Path) <= len(prefix) {
		return ""
	}
	return loc.Path
}

// SuccessfulWrite is true for HTTP-confirmed writes. For writes by link it means
// the relay answered 2xx; a deduplicated or refused link write also answers 2xx
// with an explanatory body, so link writes are an upper bound. The link_write
// column keeps them separable.
func SuccessfulWrite(r *parsers.AccessRecord) bool {
	if WriteObject(r) != "" {
		return true
	}
	if LinkWriteParam(r) != "" {
		return r.Status >= 200 && r.Status < 300
	}
	if r.Method != "POST" {
		return false
	}
	switch r.Path {
	case "/wall/", "/guestbook/", "/cgi-bin/guestbook.cgi":
		return r.Status >= 200 && r.Status < 300 || r.Status == 303 && r.Location == "/wall/" && r.Path == "/wall/"
	}
	return false
}

func ReadObject(path string) string {
	if strings.HasPrefix(path, "/guestbook/") {
		path = strings.TrimSuffix(strings.TrimSuffix(path, ".json"), ".txt")
	}
	return path
}
