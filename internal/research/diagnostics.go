package research

import (
	"net/url"
	"path"
	"strings"

	"github.com/onnwee/www2-observatory/internal/parsers"
)

const DiagnosticRevision = "request-shape-v1"

type Diagnostic struct{ Kind, Family, Reason string }

// Diagnose describes observable request shapes, independently of the stored
// research class. It never authenticates a crawler or asserts exploitation.
// Public message text is deliberately excluded from payload-pattern matching.
func Diagnose(r *parsers.AccessRecord) Diagnostic {
	q, _ := url.ParseQuery(r.Query)
	if strings.HasPrefix(r.UserAgent, "Deadweb-Operator/") || q.Get("obs_probe") != "" {
		return Diagnostic{"operator", "", "self-declared operator marker"}
	}
	p := strings.ToLower(r.Path)
	for i := 0; i < 2; i++ {
		decoded, err := url.PathUnescape(p)
		if err != nil || decoded == p {
			break
		}
		p = decoded
	}
	p = strings.ReplaceAll(p, `\`, "/")
	payload := p
	// Notes, wall messages and guestbook bodies can discuss these patterns.
	if !IsResource(r.Path) && r.Path != "/search" {
		for key, values := range q {
			if key != "obs_probe" {
				value := strings.ToLower(strings.Join(values, " "))
				for i := 0; i < 2; i++ {
					decoded, err := url.PathUnescape(value)
					if err != nil || decoded == value {
						break
					}
					value = decoded
				}
				payload += " " + strings.ReplaceAll(value, `\`, "/")
			}
		}
	}
	probe := func(kind, family, reason string) Diagnostic { return Diagnostic{kind, family, reason} }
	for _, marker := range []string{"../", "/etc/passwd", "/proc/self/environ", "/etc/shadow", "c:/windows/", "file:///"} {
		if strings.Contains(payload, marker) {
			return probe("exploit-probe", "path-traversal", "path or query contains a traversal or local-file-read pattern")
		}
	}
	for _, marker := range []string{"${jndi:", "union select", "union+select", "<script", "<?php", ";wget ", ";curl ", "|wget ", "$(id)", "php://filter", "php://input"} {
		if strings.Contains(payload, marker) {
			return probe("exploit-probe", "injection", "path or non-content query contains an injection-shaped payload")
		}
	}
	// Visitor namespaces can contain arbitrary filenames; a note named .env is
	// not evidence of a credential search.
	publicNamespace := false
	for _, prefix := range []string{"/notes/", "/guestbook/", "/wall/", "/files/", "/reference/", "/archive/", "/tmp/"} {
		publicNamespace = publicNamespace || strings.HasPrefix(p, prefix)
	}
	if !publicNamespace {
		for _, segment := range strings.Split(p, "/") {
			if strings.HasPrefix(segment, ".env.") || strings.HasPrefix(segment, ".env:") || sensitiveFilename(segment) {
				return probe("secret-probe", "sensitive-files", "request targets a credential, repository, or server-configuration filename")
			}
		}
	}
	for _, prefix := range []string{"/wp-admin", "/wp-login", "/wp-content/", "/xmlrpc.php", "/wordpress/"} {
		if strings.HasPrefix(p, prefix) {
			return probe("platform-probe", "wordpress", "request targets a WordPress route absent from this relay")
		}
	}
	for _, marker := range []string{"/vendor/phpunit/", "/phpmyadmin", "/phpinfo.php", "/cgi-bin/."} {
		if strings.Contains(p, marker) {
			return probe("exploit-probe", "php-cgi", "request targets diagnostic tooling or a known PHP/CGI probe route")
		}
	}
	for _, prefix := range []string{"/@fs/", "/__vite", "/_next/", "/_nuxt/", "/actuator/", "/api/proc/", "/api/fs/", "/api/system/fileview", "/api/console/"} {
		if strings.HasPrefix(p, prefix) {
			return probe("platform-probe", "framework", "request targets framework internals or a diagnostic/file-access API")
		}
	}
	if r.Method == "POST" && (p == "/" || p == "/app" || p == "/api") && strings.Contains(strings.ToLower(r.Accept), "text/x-component") {
		return probe("platform-probe", "react-server-components", "POST asks a non-React relay route for a React component representation")
	}
	for _, prefix := range []string{"/admin", "/manager/", "/console/", "/boaform/", "/hnap1", "/server-status"} {
		if p == prefix || strings.HasPrefix(p, prefix+"/") || (strings.HasSuffix(prefix, "/") && strings.HasPrefix(p, prefix)) {
			return probe("platform-probe", "admin-discovery", "request guesses an administrative or device-management route")
		}
	}
	if r.Status == 404 {
		switch p {
		case "/.well-known/security.txt", "/security.txt", "/robots.txt", "/sitemap.xml", "/sitemap_index.xml", "/llms.txt", "/ads.txt", "/app-ads.txt":
			return Diagnostic{"discovery-miss", "", "missing conventional discovery or policy file"}
		}
		switch path.Ext(p) {
		case ".ico", ".png", ".svg", ".css", ".js", ".woff", ".woff2", ".jpg", ".webp":
			return Diagnostic{"asset-miss", "", "missing asset; inspect the referrer for a broken site link"}
		}
		if IsResource(r.Path) {
			return Diagnostic{"resource-miss", "", "missing path in a public namespace; may be a typo, guessed object, or broken link"}
		}
		return Diagnostic{"unknown-miss", "", "missing unrecognised path; a 404 alone does not establish scanning"}
	}
	if IsResource(r.Path) || p == "/llms.txt" || p == "/write-by-get.txt" || p == "/write-by-get.html" || strings.HasPrefix(p, "/static/") {
		return Diagnostic{"resource", "", "request to a public resource; inspect status separately"}
	}
	return Diagnostic{"unclassified", "", "no diagnostic request-shape rule matched"}
}

func sensitiveFilename(name string) bool {
	switch name {
	case ".env", ".git", ".git-credentials", ".aws", ".ssh", ".bash_history", ".bashrc", ".zshrc", ".htpasswd", ".npmrc", ".dev.vars", ".dockerenv", ".gitlab-ci.yml", "secrets.json", "secrets.yml", "secrets.yaml", "credentials.json", "id_rsa", "wp-config.php", "web.config", "config.json", "config.yaml", "config.yml", "appsettings.json", "docker-compose.yml", "docker-compose.yaml", "dockerfile":
		return true
	}
	return false
}
