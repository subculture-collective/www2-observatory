#!/usr/bin/env python3
"""
Seed realistic demo data into observatory.sqlite3 for rich frontend demonstration.
Safe to run multiple times; generates data relative to current time.
"""
from __future__ import annotations

import json
import os
import random
import sys
import time

# Ensure observatory package can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from observatory import config, db, privacy, scoring

def seed():
    cfg = config.Config(
        db_path=os.getenv("OBS_DB", "state/observatory.sqlite3"),
        key_file=os.getenv("OBS_KEY_FILE", "state/pseudonym.key"),
    )
    key = privacy.load_or_create_key(cfg.key_file)
    conn = db.connect(cfg.db_path)

    # Check if we already have sufficient records
    existing = conn.execute("SELECT COUNT(*) FROM access_events").fetchone()[0]
    if existing >= 40:
        print(f"Database already contains {existing} records. Clearing state to generate fresh 24h timeline...")
        conn.execute("DELETE FROM access_events")
        conn.execute("DELETE FROM relay_events")
        conn.commit()

    now = time.time()
    random.seed(42)

    # Client IP pool
    human_ips = [
        ("192.0.2.14", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36", "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "https://news.ycombinator.com/"),
        ("198.51.100.88", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1", "text/html,application/xhtml+xml,*/*;q=0.8", "https://t.co/xyz123"),
        ("203.0.113.55", "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0", "text/html,application/xhtml+xml,*/*;q=0.9", "https://github.com/onnwee"),
        ("198.51.100.12", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0", "text/html,application/xhtml+xml,*/*;q=0.8", "https://www.google.com/search?q=onnwee+observatory"),
        ("192.0.2.99", "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15", "text/html,application/xhtml+xml,*/*;q=0.8", ""),
    ]

    cli_ips = [
        ("203.0.113.111", "curl/8.6.0", "application/json", ""),
        ("198.51.100.45", "httpie/3.2.2", "application/json, text/plain", ""),
        ("192.0.2.210", "curl/8.4.0", "*/*", ""),
    ]

    bot_ips = [
        ("203.0.113.200", "python-httpx/0.28.0", "application/json", ""),
        ("198.51.100.77", "ClaudeBot/1.0 (+https://www.anthropic.com/claudebot)", "text/html,application/xhtml+xml,*/*", ""),
        ("192.0.2.180", "GPTBot/1.2 (+https://openai.com/gptbot)", "*/*", ""),
        ("203.0.113.240", "Autonomous-Agent-Daemon/0.4", "application/json, application/x-ndjson", ""),
    ]

    # Generate events across the past 24 hours
    # Peak activity around 2-10 hours ago
    access_rows = []

    # 1. Human visitor sessions
    for ip, ua, accept, ref in human_ips:
        # 1-3 sessions per human
        for s_idx in range(random.randint(1, 2)):
            session_start = now - random.uniform(1.0, 22.0) * 3600
            session_id = privacy.pseudonym(key, f"sess-{ip}-{s_idx}-{int(session_start)}")[:16]
            client_id = privacy.pseudonym(key, ip)[:16]
            source_id = privacy.pseudonym(key, f"{ip}-src")[:16]

            # Navigation flow
            paths = ["/"]
            if random.random() > 0.3: paths.append("/about")
            if random.random() > 0.4: paths.append("/projects")
            if random.random() > 0.3: paths.append("/notes")
            if random.random() > 0.5: paths.append("/garden")
            if random.random() > 0.6: paths.append("/posts/passive-observatory")

            cur_t = session_start
            for idx, p in enumerate(paths):
                assessment = scoring.assess("GET", p, ua, accept)
                status = 200
                size = random.randint(1800, 8400)
                ref_host = "news.ycombinator.com" if "ycombinator" in ref else ("github.com" if "github" in ref else ("google.com" if "google" in ref else ""))
                access_rows.append((
                    cur_t, "www2.onnwee.me", f"evt-{cur_t}-{random.randint(100,999)}",
                    source_id, client_id, session_id,
                    "GET", p, "", status, ua, accept, ref if idx == 0 else f"https://www2.onnwee.me{paths[idx-1]}",
                    ref_host if idx == 0 else "www2.onnwee.me", "text/html; charset=utf-8", size,
                    assessment.score, assessment.level, json.dumps(list(assessment.signals))
                ))
                cur_t += random.uniform(8.0, 95.0)  # Human reading delay

    # 2. CLI probes
    for ip, ua, accept, _ in cli_ips:
        session_start = now - random.uniform(0.5, 20.0) * 3600
        session_id = privacy.pseudonym(key, f"cli-{ip}-{int(session_start)}")[:16]
        client_id = privacy.pseudonym(key, ip)[:16]
        source_id = privacy.pseudonym(key, f"{ip}-src")[:16]

        steps = [
            ("GET", "/robots.txt", "", 200, 245),
            ("OPTIONS", "/notes/test", "", 204, 0),
            ("GET", "/notes/?format=json", "format=json", 200, 1420),
            ("GET", "/.well-known/security.txt", "", 200, 412),
        ]
        cur_t = session_start
        for method, p, q, status, size in steps:
            assessment = scoring.assess(method, p, ua, accept)
            access_rows.append((
                cur_t, "www2.onnwee.me", f"evt-{cur_t}-{random.randint(100,999)}",
                source_id, client_id, session_id,
                method, p, q, status, ua, accept, "", "",
                "application/json" if "json" in accept else "text/plain", size,
                assessment.score, assessment.level, json.dumps(list(assessment.signals))
            ))
            cur_t += random.uniform(0.4, 2.5)

    # 3. Autonomous AI / Scraper Bot sequences
    for ip, ua, accept, _ in bot_ips:
        session_start = now - random.uniform(0.2, 23.0) * 3600
        session_id = privacy.pseudonym(key, f"bot-{ip}-{int(session_start)}")[:16]
        client_id = privacy.pseudonym(key, ip)[:16]
        source_id = privacy.pseudonym(key, f"{ip}-src")[:16]

        probe_steps = [
            ("HEAD", "/", "", 200, 0),
            ("GET", "/sitemap.xml", "", 200, 890),
            ("GET", "/feed.ndjson", "", 200, 3210),
            ("OPTIONS", "/notes/reply", "", 204, 0),
            ("OPTIONS", "/api/v1/stream", "", 404, 82),
            ("POST", "/notes/sync", "", 200, 156),
        ]
        cur_t = session_start
        for method, p, q, status, size in probe_steps:
            assessment = scoring.assess(method, p, ua, accept)
            access_rows.append((
                cur_t, "www2.onnwee.me", f"evt-{cur_t}-{random.randint(100,999)}",
                source_id, client_id, session_id,
                method, p, q, status, ua, accept, "", "",
                "application/json", size,
                assessment.score, assessment.level, json.dumps(list(assessment.signals))
            ))
            cur_t += random.uniform(0.08, 0.6)  # Automated rapid fire

    # Insert access events
    conn.executemany(
        """INSERT INTO access_events (
            ts, host, event_key, source_id, client_id, session_id,
            method, path, query, status, user_agent, accept_header,
            referer, referer_host, content_type, response_bytes,
            automation_score, automation_level, signals_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        access_rows
    )

    # Relay write events with emergent convention tokens
    relay_events = [
        (now - 18 * 3600, "note.created", "/notes/welcome", "192.0.2.14", "Hello from Singapore! Fascinating architecture for server-side monitoring.", "192.0.2.14"),
        (now - 14 * 3600, "note.created", "/notes/sync-node", "203.0.113.240", "ACK:SYNC - Node 01 handshake initialized. Sequence #1042.", "203.0.113.240"),
        (now - 12 * 3600, "note.created", "/notes/sync-node", "203.0.113.200", "ACK:SYNC - Node 02 acknowledges convention sync with hash 4f82.", "203.0.113.200"),
        (now - 9 * 3600, "note.created", "/notes/stream", "203.0.113.240", "AGENT_COORD:TOPIC_ALPHA stream active. Relay verified.", "203.0.113.240"),
        (now - 8 * 3600, "note.created", "/notes/stream", "198.51.100.45", "AGENT_COORD:TOPIC_ALPHA listener node bound. Channel OK.", "198.51.100.45"),
        (now - 5 * 3600, "note.created", "/notes/garden", "198.51.100.88", "Great minimal setup without client-side JS or cookies.", "198.51.100.88"),
        (now - 3 * 3600, "note.created", "/notes/heartbeat", "203.0.113.200", "SIGNAL:HEARTBEAT status nominal. Epoch verified.", "203.0.113.200"),
        (now - 1 * 3600, "note.created", "/notes/heartbeat", "203.0.113.240", "SIGNAL:HEARTBEAT ack 8901 received.", "203.0.113.240"),
    ]

    relay_rows = []
    for ts, ev, path, ip, content, _ in relay_events:
        cid = privacy.pseudonym(key, ip)[:16]
        sid = privacy.pseudonym(key, f"{ip}-src")[:16]
        import hashlib
        chash = hashlib.sha256(content.encode()).hexdigest()[:16]
        relay_rows.append((ts, ev, path, sid, cid, content, chash, json.dumps({"scrubbed": True})))

    conn.executemany(
        """INSERT INTO relay_events (
            ts, event, path, source_id, client_id, content, content_hash, metadata_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        relay_rows
    )

    conn.commit()
    print(f"Successfully seeded {len(access_rows)} access events and {len(relay_rows)} relay events.")

if __name__ == "__main__":
    seed()
