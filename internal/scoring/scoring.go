package scoring

import "strings"

type AutomationAssessment struct {
	Score   int
	Level   string
	Signals []string
}

var botUAParts = []string{"bot", "crawler", "spider", "curl/", "wget/", "python-requests", "python-httpx", "go-http-client", "libwww-perl", "httpie/", "feedfetcher", "validator"}
var browserUAParts = []string{"mozilla/5.0", "chrome/", "safari/", "firefox/", "edg/"}

func Assess(method, path, userAgent, accept string) AutomationAssessment {
	score := 0
	signals := []string{}
	m := strings.ToUpper(method)
	p := strings.ToLower(path)
	ua := strings.ToLower(userAgent)
	ac := strings.ToLower(accept)

	switch {
	case m == "OPTIONS":
		score += 4
		signals = append(signals, "capability-probe")
	case m == "HEAD":
		score += 2
		signals = append(signals, "head-probe")
	case m == "PUT" || m == "PATCH" || m == "DELETE":
		score += 3
		signals = append(signals, "programmatic-write-method")
	}

	if containsAny(ua, botUAParts) {
		score += 4
		signals = append(signals, "automation-user-agent")
	} else if ua != "" && !containsAny(ua, browserUAParts) {
		score += 1
		signals = append(signals, "non-browser-user-agent")
	}

	if strings.Contains(ac, "application/json") && !strings.Contains(ac, "text/html") {
		score += 2
		signals = append(signals, "json-preference")
	}
	if strings.Contains(ac, "text/plain") && !strings.Contains(ac, "text/html") {
		score += 2
		signals = append(signals, "plain-text-preference")
	}

	for _, suffix := range []string{".json", ".ndjson", ".txt", ".xml", ".atom"} {
		if strings.HasSuffix(p, suffix) {
			score++
			signals = append(signals, "machine-friendly-representation")
			break
		}
	}
	if strings.HasPrefix(p, "/.well-known/") || p == "/robots.txt" || p == "/sitemap.xml" || p == "/feed.json" || p == "/feed.ndjson" || p == "/feed.atom" {
		score++
		signals = append(signals, "discovery-resource")
	}

	if containsAny(ua, browserUAParts) && strings.Contains(ac, "text/html") && m == "GET" {
		score--
	}
	if score < 0 {
		score = 0
	}
	level := "low"
	if score >= 6 {
		level = "high"
	} else if score >= 3 {
		level = "medium"
	}
	return AutomationAssessment{Score: score, Level: level, Signals: signals}
}

func containsAny(value string, parts []string) bool {
	for _, part := range parts {
		if strings.Contains(value, part) {
			return true
		}
	}
	return false
}
