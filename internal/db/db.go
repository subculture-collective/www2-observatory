package db

import (
	"database/sql"
	"os"
	"path/filepath"
	"time"

	_ "modernc.org/sqlite"
)

const schema = `
PRAGMA busy_timeout=5000;
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS access_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  host TEXT NOT NULL DEFAULT '',
  event_key TEXT,
  source_id TEXT NOT NULL,
  client_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  method TEXT NOT NULL,
  path TEXT NOT NULL,
  query TEXT NOT NULL DEFAULT '',
  status INTEGER NOT NULL DEFAULT 0,
  user_agent TEXT NOT NULL DEFAULT '',
  accept_header TEXT NOT NULL DEFAULT '',
  referer TEXT NOT NULL DEFAULT '',
  referer_host TEXT NOT NULL DEFAULT '',
  content_type TEXT NOT NULL DEFAULT '',
  response_bytes INTEGER NOT NULL DEFAULT 0,
  automation_score INTEGER NOT NULL DEFAULT 0,
  automation_level TEXT NOT NULL DEFAULT 'low',
  signals_json TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_access_ts ON access_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_access_client_ts ON access_events(client_id, ts DESC);
CREATE INDEX IF NOT EXISTS idx_access_path ON access_events(path);
CREATE INDEX IF NOT EXISTS idx_access_session ON access_events(session_id);

CREATE TABLE IF NOT EXISTS relay_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  event TEXT NOT NULL,
  path TEXT NOT NULL DEFAULT '',
  source_id TEXT NOT NULL DEFAULT '',
  client_id TEXT NOT NULL DEFAULT '',
  content TEXT NOT NULL DEFAULT '',
  content_hash TEXT NOT NULL DEFAULT '',
  metadata_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_relay_ts ON relay_events(ts DESC);
CREATE INDEX IF NOT EXISTS idx_relay_path ON relay_events(path);

CREATE TABLE IF NOT EXISTS ingest_state (
  source TEXT PRIMARY KEY,
  inode INTEGER NOT NULL DEFAULT 0,
  offset INTEGER NOT NULL DEFAULT 0,
  updated_at REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS measurement_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  completed_at REAL NOT NULL,
  revision TEXT NOT NULL,
  matched_records INTEGER NOT NULL
);`

func Connect(path string) (*sql.DB, error) {
	if path != ":memory:" {
		if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
			return nil, err
		}
	}
	conn, err := sql.Open("sqlite", path)
	if err != nil {
		return nil, err
	}
	conn.SetMaxOpenConns(1)
	conn.SetConnMaxLifetime(0)
	if _, err := conn.Exec(schema); err != nil {
		_ = conn.Close()
		return nil, err
	}
	if err := migrateAccessColumns(conn); err != nil {
		_ = conn.Close()
		return nil, err
	}
	return conn, nil
}

func migrateAccessColumns(conn *sql.DB) error {
	rows, err := conn.Query("PRAGMA table_info(access_events)")
	if err != nil {
		return err
	}
	defer rows.Close()
	cols := map[string]bool{}
	for rows.Next() {
		var cid int
		var name, typ string
		var notnull int
		var dflt, pk any
		if err := rows.Scan(&cid, &name, &typ, &notnull, &dflt, &pk); err != nil {
			return err
		}
		cols[name] = true
	}
	if err := rows.Err(); err != nil {
		return err
	}
	if !cols["host"] {
		if _, err := conn.Exec("ALTER TABLE access_events ADD COLUMN host TEXT NOT NULL DEFAULT ''"); err != nil {
			return err
		}
	}
	if !cols["event_key"] {
		if _, err := conn.Exec("ALTER TABLE access_events ADD COLUMN event_key TEXT"); err != nil {
			return err
		}
	}
	for _, col := range []struct{ name, definition string }{
		{"attribution", "TEXT NOT NULL DEFAULT 'legacy-peer-v1'"},
		{"original_source_id", "TEXT NOT NULL DEFAULT ''"},
		{"original_client_id", "TEXT NOT NULL DEFAULT ''"},
		{"original_session_id", "TEXT NOT NULL DEFAULT ''"},
		{"traffic_class", "TEXT NOT NULL DEFAULT 'unclassified'"},
		{"classification_reason", "TEXT NOT NULL DEFAULT ''"},
		{"write_object", "TEXT NOT NULL DEFAULT ''"},
		{"successful_write", "INTEGER NOT NULL DEFAULT 0"},
		{"link_write", "TEXT NOT NULL DEFAULT ''"},
	} {
		if !cols[col.name] {
			if _, err := conn.Exec("ALTER TABLE access_events ADD COLUMN " + col.name + " " + col.definition); err != nil {
				return err
			}
		}
	}
	if _, err = conn.Exec("CREATE UNIQUE INDEX IF NOT EXISTS idx_access_event_key ON access_events(event_key) WHERE event_key IS NOT NULL"); err != nil {
		return err
	}
	rows, err = conn.Query("PRAGMA table_info(relay_events)")
	if err != nil {
		return err
	}
	defer rows.Close()
	hasKey := false
	for rows.Next() {
		var cid int
		var name, typ string
		var notnull int
		var dflt, pk any
		if err := rows.Scan(&cid, &name, &typ, &notnull, &dflt, &pk); err != nil {
			return err
		}
		if name == "event_key" {
			hasKey = true
		}
	}
	if err := rows.Err(); err != nil {
		return err
	}
	if !hasKey {
		if _, err := conn.Exec("ALTER TABLE relay_events ADD COLUMN event_key TEXT"); err != nil {
			return err
		}
	}
	_, err = conn.Exec("CREATE UNIQUE INDEX IF NOT EXISTS idx_relay_event_key ON relay_events(event_key) WHERE event_key IS NOT NULL")
	return err
}

func LastSession(conn *sql.DB, clientID string, ts float64, gapSeconds int) (string, error) {
	var sessionID string
	var prevTS float64
	err := conn.QueryRow("SELECT session_id, ts FROM access_events WHERE client_id=? ORDER BY ts DESC LIMIT 1", clientID).Scan(&sessionID, &prevTS)
	if err == sql.ErrNoRows || ts-prevTS > float64(gapSeconds) {
		return "", nil
	}
	return sessionID, err
}

func State(conn *sql.DB, source string) (inode int64, offset int64, err error) {
	err = conn.QueryRow("SELECT inode, offset FROM ingest_state WHERE source=?", source).Scan(&inode, &offset)
	if err == sql.ErrNoRows {
		return 0, 0, nil
	}
	return inode, offset, err
}

func SetState(conn *sql.DB, source string, inode, offset int64) error {
	_, err := conn.Exec(
		"INSERT INTO ingest_state(source,inode,offset,updated_at) VALUES(?,?,?,?) ON CONFLICT(source) DO UPDATE SET inode=excluded.inode, offset=excluded.offset, updated_at=excluded.updated_at",
		source, inode, offset, float64(time.Now().UnixNano())/1e9,
	)
	return err
}
