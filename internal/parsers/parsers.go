package parsers

import (
	"encoding/json"
	"fmt"
	"net/netip"
	"net/url"
	"strconv"
	"strings"
	"time"
)

type AccessRecord struct {
	TS          float64
	Host        string
	RemoteIP    string
	Method      string
	Path        string
	Query       string
	Status      int
	UserAgent   string
	Accept      string
	Referer     string
	ContentType string
	Size        int64
	Attribution string
	Location    string
}

type RelayRecord struct {
	TS        float64
	Event     string
	Path      string
	RemoteIP  string
	UserAgent string
	Content   string
	Metadata  map[string]any
}

func ParseCaddyLine(line string) (*AccessRecord, error) {
	return ParseCaddyLineWithPolicy(line, false)
}

// Trust only Caddy's computed field after verifying the server's trusted-proxy policy.
// Never interpret client-supplied forwarding headers here.
func ParseCaddyLineWithPolicy(line string, trustClientIP bool) (*AccessRecord, error) {
	var obj map[string]any
	if err := json.Unmarshal([]byte(line), &obj); err != nil {
		return nil, err
	}
	req := asMap(obj["request"])
	headers := asMap(req["headers"])
	uri := firstString(req["uri"], obj["uri"])
	if uri == "" {
		uri = "/"
	}
	parsed, err := url.Parse(uri)
	if err != nil {
		return nil, fmt.Errorf("invalid request URI: %w", err)
	}
	remoteIP := firstString(req["remote_ip"], obj["remote_ip"])
	attribution := "peer-v1"
	if trustClientIP {
		if addr, err := netip.ParseAddr(firstString(req["client_ip"])); err == nil {
			remoteIP, attribution = addr.Unmap().String(), "caddy-client-v2"
		}
	}
	return &AccessRecord{
		TS:          timestamp(firstAny(obj["ts"], obj["time"])),
		Host:        NormalizeHost(firstString(req["host"], headerFirst(headers, "Host"))),
		RemoteIP:    remoteIP,
		Method:      valueOr(firstString(req["method"], obj["method"]), "GET"),
		Path:        valueOr(parsed.Path, "/"),
		Query:       parsed.RawQuery,
		Status:      intNumber(obj["status"]),
		UserAgent:   headerFirst(headers, "User-Agent"),
		Accept:      headerFirst(headers, "Accept"),
		Referer:     headerFirst(headers, "Referer"),
		ContentType: responseHeaderFirst(asMap(obj["resp_headers"]), "Content-Type"),
		Size:        int64Number(obj["size"]),
		Attribution: attribution,
		Location:    responseHeaderFirst(asMap(obj["resp_headers"]), "Location"),
	}, nil
}

func ParseRelayLine(line string) (*RelayRecord, error) {
	var obj map[string]any
	if err := json.Unmarshal([]byte(line), &obj); err != nil {
		return nil, err
	}
	event := firstString(obj["event"], obj["kind"])
	if event == "" {
		return nil, fmt.Errorf("missing event")
	}
	content := firstString(obj["content"], obj["body"], obj["text"])
	metadata := map[string]any{}
	for k, v := range obj {
		if k != "ts" && k != "time" && k != "event" && k != "kind" && k != "path" && k != "remote_ip" && k != "client_ip" && k != "user_agent" && k != "content" && k != "body" && k != "text" {
			metadata[k] = v
		}
	}
	return &RelayRecord{
		TS:        timestamp(firstAny(obj["ts"], obj["time"])),
		Event:     event,
		Path:      firstString(obj["path"]),
		RemoteIP:  firstString(obj["remote_ip"], obj["client_ip"]),
		UserAgent: firstString(obj["user_agent"]),
		Content:   content,
		Metadata:  metadata,
	}, nil
}

func NormalizeHost(value string) string {
	value = strings.TrimSpace(strings.ToLower(value))
	if value == "" {
		return ""
	}
	parsed, err := url.Parse("//" + value)
	if err == nil && parsed.Hostname() != "" {
		return strings.TrimSuffix(parsed.Hostname(), ".")
	}
	return strings.TrimSuffix(value, ".")
}

func timestamp(value any) float64 {
	switch v := value.(type) {
	case nil:
		return float64(time.Now().UnixNano()) / 1e9
	case float64:
		return v
	case int64:
		return float64(v)
	case int:
		return float64(v)
	case string:
		if parsed, err := time.Parse(time.RFC3339Nano, v); err == nil {
			return float64(parsed.UnixNano()) / 1e9
		}
		if f, err := strconv.ParseFloat(v, 64); err == nil {
			return f
		}
	}
	return float64(time.Now().UnixNano()) / 1e9
}

func headerFirst(headers map[string]any, name string) string {
	for key, value := range headers {
		if strings.EqualFold(key, name) {
			return firstString(value)
		}
	}
	return ""
}

func responseHeaderFirst(headers map[string]any, name string) string {
	return headerFirst(headers, name)
}

func asMap(value any) map[string]any {
	if m, ok := value.(map[string]any); ok {
		return m
	}
	return map[string]any{}
}

func firstString(values ...any) string {
	for _, value := range values {
		switch v := value.(type) {
		case string:
			if v != "" {
				return v
			}
		case []any:
			if len(v) > 0 {
				if s := firstString(v[0]); s != "" {
					return s
				}
			}
		case []string:
			if len(v) > 0 && v[0] != "" {
				return v[0]
			}
		case float64:
			return strconv.FormatFloat(v, 'f', -1, 64)
		case int:
			return strconv.Itoa(v)
		}
	}
	return ""
}

func firstAny(values ...any) any {
	for _, value := range values {
		if value != nil {
			return value
		}
	}
	return nil
}

func valueOr(value, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}

func intNumber(value any) int {
	return int(int64Number(value))
}

func int64Number(value any) int64 {
	switch v := value.(type) {
	case float64:
		return int64(v)
	case int64:
		return v
	case int:
		return int64(v)
	case string:
		i, _ := strconv.ParseInt(v, 10, 64)
		return i
	default:
		return 0
	}
}

// ParseRelayLedgerLine reads one line of the relay's own append-only ledgers
// (data/guestbook.jsonl, wall.jsonl, notes.jsonl, files.jsonl) or its request
// event log (data/events.jsonl, only lines carrying write_type). Ledger lines
// are the stored result of a write; event lines say which HTTP request stored
// it. Non-write event lines return nil, nil.
func ParseRelayLedgerLine(ledger, line string) (*RelayRecord, error) {
	var obj map[string]any
	if err := json.Unmarshal([]byte(line), &obj); err != nil {
		return nil, err
	}
	ts := timestamp(firstAny(obj["time"], obj["ts"]))
	meta := func(keys ...string) map[string]any {
		m := map[string]any{"ledger": ledger}
		for _, k := range keys {
			if v, ok := obj[k]; ok && v != nil && v != "" {
				m[k] = v
			}
		}
		return m
	}
	switch ledger {
	case "guestbook":
		return &RelayRecord{TS: ts, Event: "guestbook", Path: "/guestbook/" + numberString(obj["id"]), Content: firstString(obj["body"]), Metadata: meta("id", "name", "website", "mood", "reply_to")}, nil
	case "wall":
		return &RelayRecord{TS: ts, Event: "wall", Path: "/wall/", Content: firstString(obj["body"]), Metadata: meta("id", "name")}, nil
	case "notes":
		return &RelayRecord{TS: ts, Event: "note", Path: "/notes/" + firstString(obj["path"]), Content: firstString(obj["body"]), Metadata: meta("version", "content_type")}, nil
	case "files":
		return &RelayRecord{TS: ts, Event: "file", Path: "/files/" + numberString(obj["id"]) + "/" + firstString(obj["name"]), Content: "", Metadata: meta("id", "name", "content_type", "size", "sha256")}, nil
	case "events":
		wt := firstString(obj["write_type"])
		if wt == "" {
			return nil, nil
		}
		object := firstString(obj["object_id"])
		path := firstString(obj["path"])
		switch wt {
		case "note":
			path = "/notes/" + object
		case "guestbook":
			path = "/guestbook/" + object
		case "wall":
			path = "/wall/"
		case "file":
			path = "/files/" + object
		}
		m := meta("request_id", "method", "status", "remote_hash", "object_id", "write_type")
		m["request_path"] = firstString(obj["path"])
		return &RelayRecord{TS: ts, Event: "stored:" + wt, Path: path, UserAgent: firstString(obj["user_agent"]), Metadata: m}, nil
	}
	return nil, fmt.Errorf("unknown ledger %q", ledger)
}

func numberString(v any) string {
	switch n := v.(type) {
	case float64:
		return strconv.FormatInt(int64(n), 10)
	case string:
		return n
	default:
		return ""
	}
}
