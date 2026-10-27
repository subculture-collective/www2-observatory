from __future__ import annotations

import os
import sqlite3
import time

SCHEMA = """
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
"""


def connect(path: str) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    conn = sqlite3.connect(path, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    columns = {str(row["name"]) for row in conn.execute("PRAGMA table_info(access_events)")}
    if "host" not in columns:
        conn.execute("ALTER TABLE access_events ADD COLUMN host TEXT NOT NULL DEFAULT ''")
    if "event_key" not in columns:
        conn.execute("ALTER TABLE access_events ADD COLUMN event_key TEXT")
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_access_event_key "
        "ON access_events(event_key) WHERE event_key IS NOT NULL"
    )
    conn.commit()
    return conn


def last_session(conn: sqlite3.Connection, client_id: str, ts: float, gap_seconds: int) -> str | None:
    row = conn.execute(
        "SELECT session_id, ts FROM access_events WHERE client_id=? ORDER BY ts DESC LIMIT 1",
        (client_id,),
    ).fetchone()
    if row and ts - float(row["ts"]) <= gap_seconds:
        return str(row["session_id"])
    return None


def state(conn: sqlite3.Connection, source: str) -> tuple[int, int]:
    row = conn.execute("SELECT inode, offset FROM ingest_state WHERE source=?", (source,)).fetchone()
    return (int(row["inode"]), int(row["offset"])) if row else (0, 0)


def set_state(conn: sqlite3.Connection, source: str, inode: int, offset: int) -> None:
    conn.execute(
        "INSERT INTO ingest_state(source,inode,offset,updated_at) VALUES(?,?,?,?) "
        "ON CONFLICT(source) DO UPDATE SET inode=excluded.inode, offset=excluded.offset, updated_at=excluded.updated_at",
        (source, inode, offset, time.time()),
    )
    conn.commit()
