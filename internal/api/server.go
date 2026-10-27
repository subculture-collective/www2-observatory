package api

import (
	"database/sql"
	"encoding/json"
	"errors"
	"net/http"
	"os"
	"path/filepath"
	"strconv"
	"strings"

	"github.com/onnwee/www2-observatory/internal/analytics"
	"github.com/onnwee/www2-observatory/internal/config"
	"github.com/onnwee/www2-observatory/internal/db"
)

type Server struct {
	cfg config.Config
}

func NewServer(cfg config.Config) http.Handler {
	return &Server{cfg: cfg}
}

func (s *Server) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	if r.URL.Path == "/healthz" {
		writeJSON(w, map[string]bool{"ok": true}, http.StatusOK)
		return
	}
	if !s.authorized(r) {
		w.Header().Set("WWW-Authenticate", "Bearer")
		http.Error(w, "unauthorized", http.StatusUnauthorized)
		return
	}
	if strings.HasPrefix(r.URL.Path, "/api/") {
		s.handleAPI(w, r)
		return
	}
	s.handleStatic(w, r)
}

func (s *Server) authorized(r *http.Request) bool {
	return s.cfg.Token == "" || r.Header.Get("Authorization") == "Bearer "+s.cfg.Token
}

func (s *Server) handleAPI(w http.ResponseWriter, r *http.Request) {
	conn, err := db.Connect(s.cfg.DBPath)
	if err != nil {
		writeError(w, err)
		return
	}
	defer conn.Close()

	q := r.URL.Query()
	hours := queryInt(q.Get("hours"), 24)
	limit := queryInt(q.Get("limit"), 100)
	var out any
	switch r.URL.Path {
	case "/api/experiment":
		out, err = analytics.Experiment(conn, hours, s.cfg.SessionMinutes)
	case "/api/summary":
		out, err = analytics.SummaryEx(conn, hours)
	case "/api/recent":
		var status *int
		if raw := q.Get("status"); raw != "" {
			value := queryInt(raw, 0)
			status = &value
		}
		out, err = analytics.RecentEx(conn, limit, q.Get("method"), q.Get("level"), status, q.Get("search"), q.Get("class"), q.Get("client"), q.Get("link") == "1")
	case "/api/timeline":
		out, err = analytics.TimelineEx(conn, hours, q.Get("bucket"))
	case "/api/clients":
		out, err = analytics.Clients(conn, hours, limit, q.Get("class"), q.Get("order"))
	case "/api/client":
		out, err = analytics.ClientDetail(conn, q.Get("id"), limit, s.cfg.SessionMinutes)
	case "/api/event":
		out, err = analytics.EventByID(conn, int64(queryInt(q.Get("id"), 0)))
	case "/api/objects":
		out, err = analytics.Objects(conn, hours)
	case "/api/representations":
		out, err = analytics.Representations(conn, hours)
	case "/api/heatmap":
		out, err = analytics.Heatmap(conn, hours)
	case "/api/link-writes":
		out, err = analytics.LinkWrites(conn, hours, limit)
	case "/api/entrances":
		out, err = analytics.Entrances(conn, hours, limit)
	case "/api/ingest":
		out, err = analytics.Ingest(conn)
	case "/api/interventions":
		s.serveInterventions(w)
		return
	case "/api/status":
		out, err = analytics.StatusDistribution(conn, hours)
	case "/api/methods":
		out, err = analytics.MethodDistribution(conn, hours)
	case "/api/user-agents":
		out, err = analytics.UserAgentsEx(conn, hours, limit)
	case "/api/system":
		out, err = analytics.SystemStats(conn)
	case "/api/paths":
		out, err = analytics.PathsEx(conn, hours, limit)
	case "/api/referrers":
		out, err = analytics.Referrers(conn, hours, limit)
	case "/api/signals":
		out, err = analytics.Signals(conn, hours)
	case "/api/sessions":
		out, err = analytics.Sessions(conn, hours, limit)
	case "/api/writes":
		out, err = analytics.Writes(conn, limit)
	case "/api/conventions":
		out, err = analytics.Conventions(conn, hours, limit)
	case "/api/export.ndjson":
		rows, err := analytics.RecentEx(conn, min(limit, 500), "", "", nil, "", q.Get("class"), q.Get("client"), false)
		if err != nil {
			writeError(w, err)
			return
		}
		w.Header().Set("Content-Type", "application/x-ndjson")
		for _, row := range rows {
			_ = json.NewEncoder(w).Encode(row)
		}
		return
	default:
		writeJSON(w, map[string]string{"error": "not found"}, http.StatusNotFound)
		return
	}
	if errors.Is(err, sql.ErrNoRows) {
		writeJSON(w, map[string]string{"error": "not found"}, http.StatusNotFound)
		return
	}
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, out, http.StatusOK)
}

// serveInterventions returns the intervention ledger copied into the static
// directory at build time. It is the same JSON the relay repo keeps in docs/.
func (s *Server) serveInterventions(w http.ResponseWriter) {
	for _, candidate := range []string{filepath.Join(s.cfg.StaticDir, "interventions.json"), "frontend/public/interventions.json"} {
		if b, err := os.ReadFile(candidate); err == nil {
			w.Header().Set("Content-Type", "application/json; charset=utf-8")
			_, _ = w.Write(b)
			return
		}
	}
	writeJSON(w, map[string]string{"error": "interventions ledger not found"}, http.StatusNotFound)
}

func (s *Server) handleStatic(w http.ResponseWriter, r *http.Request) {
	cleanPath := strings.TrimPrefix(filepath.Clean(r.URL.Path), string(filepath.Separator))
	path := filepath.Join(s.cfg.StaticDir, cleanPath)
	if strings.Contains(cleanPath, "..") {
		http.NotFound(w, r)
		return
	}
	// Single-page app: any path that is not an existing file gets index.html
	// so client-side routes such as /clients/<id> survive a reload.
	if info, err := os.Stat(path); r.URL.Path == "/" || err != nil || info.IsDir() {
		path = filepath.Join(s.cfg.StaticDir, "index.html")
	}
	http.ServeFile(w, r, path)
}

func writeJSON(w http.ResponseWriter, value any, status int) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}

func writeError(w http.ResponseWriter, err error) {
	writeJSON(w, map[string]string{"error": err.Error()}, http.StatusInternalServerError)
}

func queryInt(raw string, fallback int) int {
	if raw == "" {
		return fallback
	}
	value, err := strconv.Atoi(raw)
	if err != nil {
		return fallback
	}
	return value
}
