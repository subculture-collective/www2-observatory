from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import sqlite3
from urllib.parse import parse_qs, urlsplit

from . import analytics, db, views
from .config import Config


class Handler(BaseHTTPRequestHandler):
    server_version = "Observatory/0.2"

    @property
    def cfg(self) -> Config:
        return self.server.cfg  # type: ignore[attr-defined]

    def _authorized(self) -> bool:
        if not self.cfg.token:
            return True
        return self.headers.get("Authorization", "") == f"Bearer {self.cfg.token}"

    def _deny(self):
        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", "Bearer")
        self.end_headers()

    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, page_html: str):
        raw = page_html.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_HEAD(self):
        if not self._authorized():
            return self._deny()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        if not self._authorized():
            return self._deny()
        u = urlsplit(self.path)
        q = parse_qs(u.query)
        conn = db.connect(self.cfg.db_path)
        try:
            if u.path.startswith("/api/"):
                return self._api(conn, u.path, q)
            if u.path == "/healthz":
                return self._json({"ok": True})
            if u.path in ("/1", "/1/"):
                return self._html(views.render_option1(conn))
            if u.path in ("/2", "/2/"):
                return self._html(views.render_option2(conn))
            if u.path in ("/3", "/3/"):
                return self._html(views.render_option3(conn))
            if u.path in ("/hub", "/hub/"):
                return self._html(views.render_hub(conn))
            # Primary application dashboard
            return self._html(views.render_dashboard(conn))
        finally:
            conn.close()

    def _api(self, conn: sqlite3.Connection, path: str, q: dict[str, list[str]]):
        hours = int(q.get("hours", [24])[0])
        limit = int(q.get("limit", [100])[0])
        method = q.get("method", [None])[0]
        level = q.get("level", [None])[0]
        status_q = q.get("status", [None])[0]
        search = q.get("search", [None])[0]

        if path == "/api/summary":
            return self._json(analytics.summary(conn, hours))
        if path == "/api/recent":
            return self._json(analytics.recent(conn, limit, method, level, int(status_q) if status_q else None, search))
        if path == "/api/timeline":
            return self._json(analytics.timeline(conn, hours))
        if path == "/api/status":
            return self._json(analytics.status_distribution(conn, hours))
        if path == "/api/methods":
            return self._json(analytics.method_distribution(conn, hours))
        if path == "/api/user-agents":
            return self._json(analytics.ua_breakdown(conn, hours, limit))
        if path == "/api/system":
            return self._json(analytics.system_stats(conn))
        if path == "/api/paths":
            return self._json(analytics.top_paths(conn, hours, limit))
        if path == "/api/referrers":
            return self._json(analytics.referrers(conn, hours, limit))
        if path == "/api/signals":
            return self._json(analytics.signals(conn, hours))
        if path == "/api/sessions":
            return self._json(analytics.sessions(conn, hours, limit))
        if path == "/api/writes":
            return self._json(analytics.writes(conn, limit))
        if path == "/api/conventions":
            return self._json(analytics.conventions(conn, hours, limit))
        if path == "/api/export.ndjson":
            rows = analytics.recent(conn, min(limit, 500))
            data = ("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        return self._json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):
        # Keep dashboard requests out of noisy stdout unless debugging is needed.
        return


class ObservatoryServer(ThreadingHTTPServer):
    def __init__(self, addr, cfg: Config):
        super().__init__(addr, Handler)
        self.cfg = cfg

