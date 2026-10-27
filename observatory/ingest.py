from __future__ import annotations

import gzip
import hashlib
import json
import os
import secrets
import sqlite3
import threading
from pathlib import Path

from . import db
from .config import Config
from .parsers import parse_caddy_line, parse_relay_line
from .privacy import pseudonym, sanitize_referrer, scrub_text
from .scoring import assess


class Ingestor:
    def __init__(self, cfg: Config, key: bytes):
        self.cfg = cfg
        self.key = key
        self.allowed_hosts = {
            host.strip().lower().rstrip(".")
            for host in cfg.allowed_hosts.split(",")
            if host.strip()
        }
        self.stop_event = threading.Event()

    def stop(self) -> None:
        self.stop_event.set()

    def run_forever(self) -> None:
        while not self.stop_event.is_set():
            self.ingest_once()
            self.stop_event.wait(self.cfg.poll_seconds)

    def ingest_once(self) -> dict[str, int]:
        counts = {"access": 0, "relay": 0}
        conn = db.connect(self.cfg.db_path)
        try:
            if self.cfg.caddy_log:
                counts["access"] = sum(
                    self._tail_file(conn, path, "access")
                    for path in self._log_files(self.cfg.caddy_log)
                )
            if self.cfg.relay_log:
                counts["relay"] = self._tail_file(conn, self.cfg.relay_log, "relay")
        finally:
            conn.close()
        return counts

    @staticmethod
    def _log_files(active_path: str) -> list[str]:
        active = Path(active_path)
        paths = set(active.parent.glob(active.name + "*"))
        paths.update(active.parent.glob(f"{active.stem}-*{active.suffix}*"))
        candidates = [path for path in paths if path.is_file()]
        candidates.sort(key=lambda path: (path == active, path.stat().st_mtime_ns, path.name))
        return [str(path) for path in candidates]

    def _tail_file(self, conn: sqlite3.Connection, path: str, kind: str) -> int:
        try:
            st = os.stat(path)
        except FileNotFoundError:
            return 0
        inode = int(st.st_ino)
        source = f"{kind}:{st.st_dev}:{inode}"
        _old_inode, offset = db.state(conn, source)
        if not path.endswith(".gz") and st.st_size < offset:
            offset = 0
        count = 0
        opener = gzip.open if path.endswith(".gz") else open
        with opener(path, "rb") as f:
            f.seek(offset)
            while True:
                line_offset = f.tell()
                raw_line = f.readline()
                if not raw_line:
                    break
                if not raw_line.endswith(b"\n"):
                    f.seek(line_offset)
                    break
                line = raw_line.decode("utf-8", "replace")
                if kind == "access":
                    count += self._ingest_access(conn, line, raw_line)
                else:
                    count += self._ingest_relay(conn, line)
            offset = f.tell()
        db.set_state(conn, source, inode, offset)
        conn.commit()
        return count

    def _ids(self, remote_ip: str, user_agent: str) -> tuple[str, str]:
        # Raw network addresses are used only transiently to derive irreversible local pseudonyms.
        source_id = pseudonym(self.key, remote_ip or "unknown", "src")
        client_id = pseudonym(self.key, f"{remote_ip or 'unknown'}\x00{user_agent}", "cli")
        return source_id, client_id

    def _ingest_access(self, conn: sqlite3.Connection, line: str, raw_line: bytes | None = None) -> int:
        rec = parse_caddy_line(line)
        if rec is None or rec.host not in self.allowed_hosts:
            return 0
        event_key = hashlib.sha256(raw_line or line.encode("utf-8", "replace")).hexdigest()
        source_id, client_id = self._ids(rec.remote_ip, rec.user_agent)
        session_id = db.last_session(conn, client_id, rec.ts, self.cfg.session_minutes * 60)
        if not session_id:
            session_id = "ses_" + secrets.token_hex(8)
        assessment = assess(rec.method, rec.path, rec.user_agent, rec.accept)
        clean_ref, ref_host = sanitize_referrer(rec.referer, {"www2.onnwee.me", "onnwee.me"})
        cursor = conn.execute(
            """INSERT OR IGNORE INTO access_events(
                ts,host,event_key,source_id,client_id,session_id,method,path,query,status,user_agent,accept_header,
                referer,referer_host,content_type,response_bytes,automation_score,automation_level,signals_json
            ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                rec.ts, rec.host, event_key, source_id, client_id, session_id, rec.method.upper(), rec.path[:2048], rec.query[:2048],
                rec.status, rec.user_agent[:1024], rec.accept[:1024], clean_ref, ref_host,
                rec.content_type[:255], rec.size, assessment.score, assessment.level,
                json.dumps(assessment.signals),
            ),
        )
        return cursor.rowcount

    def _ingest_relay(self, conn: sqlite3.Connection, line: str) -> int:
        rec = parse_relay_line(line)
        if rec is None:
            return 0
        source_id, client_id = self._ids(rec.remote_ip, rec.user_agent) if (rec.remote_ip or rec.user_agent) else ("", "")
        content = scrub_text(rec.content, self.cfg.content_max)
        digest = hashlib.sha256(rec.content.encode("utf-8", "replace")).hexdigest() if rec.content else ""
        conn.execute(
            "INSERT INTO relay_events(ts,event,path,source_id,client_id,content,content_hash,metadata_json) VALUES(?,?,?,?,?,?,?,?)",
            (rec.ts, rec.event[:128], rec.path[:2048], source_id, client_id, content, digest, json.dumps(rec.metadata, ensure_ascii=False)[:8192]),
        )
        return 1
