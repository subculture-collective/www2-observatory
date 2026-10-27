from __future__ import annotations

import unittest
import time

from observatory import analytics, views
from observatory.db import connect

class WebViewsTests(unittest.TestCase):
    def setUp(self):
        self.conn = connect(":memory:")
        # Insert a sample event
        self.conn.execute(
            """INSERT INTO access_events (
                ts, host, event_key, source_id, client_id, session_id,
                method, path, query, status, user_agent, accept_header,
                referer, referer_host, content_type, response_bytes,
                automation_score, automation_level, signals_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                time.time() - 60, "www2.onnwee.me", "evt-1", "src-1", "client-1", "sess-1",
                "GET", "/notes", "format=json", 200, "curl/8.6", "application/json",
                "", "", "application/json", 1024, 7, "high", '["capability-probe","json-preference"]'
            )
        )
        self.conn.commit()

    def tearDown(self):
        self.conn.close()

    def test_render_dashboard(self):
        html = views.render_dashboard(self.conn)
        self.assertIn("<!doctype html>", html)
        self.assertIn("WWW2 OBSERVATORY", html)
        self.assertIn("TELEMETRY OSCILLOSCOPE", html)
        self.assertIn("PACKET TELEMETRY INSPECTOR", html)
        self.assertIn("REAL-TIME PACKET WIRE", html)
        self.assertIn("/notes", html)
        self.assertIn("client-1", html)

    def test_analytics_endpoints(self):
        s = analytics.summary(self.conn, 24)
        self.assertEqual(s["requests"], 1)
        self.assertEqual(s["high_auto"], 1)

        tl = analytics.timeline(self.conn, 24)
        self.assertGreaterEqual(len(tl), 1)

        recent = analytics.recent(self.conn, 10)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["method"], "GET")

if __name__ == "__main__":
    unittest.main()
