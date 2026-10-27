from __future__ import annotations

from collections import Counter, defaultdict
import json
import re
import sqlite3
import time

TOKEN_RE = re.compile(r"(?u)(?:\b[A-Z][A-Z0-9:_-]{2,}\b|\b[a-zA-Z][a-zA-Z0-9_-]{3,}\b)")
STOP = {
    "this","that","with","from","have","will","your","what","when","where","there","here","http","https",
    "notes","guestbook","wall","text","html","json","www2","onnwee","content","public","server","page","pages",
}


def summary(conn: sqlite3.Connection, hours: int = 24) -> dict:
    since = time.time() - hours * 3600
    row = conn.execute(
        """SELECT COUNT(*) requests, COUNT(DISTINCT client_id) clients, COUNT(DISTINCT session_id) sessions,
                  SUM(CASE WHEN method IN ('POST','PUT','PATCH','DELETE') THEN 1 ELSE 0 END) writes,
                  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) high_auto,
                  SUM(CASE WHEN automation_level='medium' THEN 1 ELSE 0 END) med_auto,
                  SUM(CASE WHEN automation_level='low' THEN 1 ELSE 0 END) low_auto,
                  COALESCE(ROUND(AVG(automation_score), 1), 0) avg_score,
                  COALESCE(SUM(response_bytes), 0) total_bytes
           FROM access_events WHERE ts>=?""", (since,)
    ).fetchone()
    d = dict(row)
    prev_since = since - hours * 3600
    prev_row = conn.execute(
        """SELECT COUNT(*) prev_requests, COUNT(DISTINCT client_id) prev_clients
           FROM access_events WHERE ts>=? AND ts<?""", (prev_since, since)
    ).fetchone()
    d["prev_requests"] = prev_row["prev_requests"] if prev_row else 0
    d["prev_clients"] = prev_row["prev_clients"] if prev_row else 0
    return d | {"hours": hours}


def recent(
    conn: sqlite3.Connection,
    limit: int = 100,
    method: str | None = None,
    level: str | None = None,
    status: int | None = None,
    search: str | None = None,
) -> list[dict]:
    clauses = []
    params: list[object] = []
    if method:
        clauses.append("method = ?")
        params.append(method.upper())
    if level:
        clauses.append("automation_level = ?")
        params.append(level.lower())
    if status:
        clauses.append("status = ?")
        params.append(int(status))
    if search:
        clauses.append("(path LIKE ? OR user_agent LIKE ? OR client_id LIKE ? OR referer LIKE ?)")
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(max(1, min(limit, 500)))
    rows = conn.execute(f"SELECT * FROM access_events{where} ORDER BY ts DESC LIMIT ?", params).fetchall()
    return [dict(r) for r in rows]


def top_paths(conn: sqlite3.Connection, hours: int = 24, limit: int = 30) -> list[dict]:
    since = time.time() - hours * 3600
    rows = conn.execute(
        """SELECT path, COUNT(*) hits, COUNT(DISTINCT client_id) clients,
                  ROUND(AVG(automation_score),2) avg_automation
           FROM access_events WHERE ts>=? GROUP BY path ORDER BY hits DESC LIMIT ?""",
        (since, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def referrers(conn: sqlite3.Connection, hours: int = 168, limit: int = 30) -> list[dict]:
    since = time.time() - hours * 3600
    rows = conn.execute(
        """SELECT referer_host, COUNT(*) hits, COUNT(DISTINCT client_id) clients
           FROM access_events WHERE ts>=? AND referer_host<>''
           GROUP BY referer_host ORDER BY hits DESC LIMIT ?""",
        (since, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def signals(conn: sqlite3.Connection, hours: int = 168) -> list[dict]:
    since = time.time() - hours * 3600
    counter: Counter[str] = Counter()
    clients: defaultdict[str, set] = defaultdict(set)
    for row in conn.execute("SELECT signals_json,client_id FROM access_events WHERE ts>=?", (since,)):
        try:
            ss = json.loads(row["signals_json"])
        except Exception:
            ss = []
        for s in ss:
            counter[s] += 1
            clients[s].add(row["client_id"])
    return [{"signal": s, "events": n, "clients": len(clients[s])} for s, n in counter.most_common()]


def sessions(conn: sqlite3.Connection, hours: int = 168, limit: int = 100) -> list[dict]:
    since = time.time() - hours * 3600
    rows = conn.execute(
        """SELECT session_id,client_id,MIN(ts) started,MAX(ts) ended,COUNT(*) requests,
                  COUNT(DISTINCT path) unique_paths,MAX(automation_score) max_automation,
                  GROUP_CONCAT(method || ' ' || path, ' → ') trail
           FROM access_events WHERE ts>=? GROUP BY session_id
           ORDER BY ended DESC LIMIT ?""", (since, limit)
    ).fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        d["trail"]=(d.get("trail") or "")[:4000]
        out.append(d)
    return out


def writes(conn: sqlite3.Connection, limit: int = 100) -> list[dict]:
    rows = conn.execute("SELECT * FROM relay_events ORDER BY ts DESC LIMIT ?", (max(1,min(limit,500)),)).fetchall()
    return [dict(r) for r in rows]


def conventions(conn: sqlite3.Connection, hours: int = 720, limit: int = 50) -> list[dict]:
    since = time.time() - hours * 3600
    counts: Counter[str] = Counter()
    clients: defaultdict[str, set] = defaultdict(set)
    first: dict[str,float] = {}
    last: dict[str,float] = {}
    rows = conn.execute("SELECT ts,client_id,path,content FROM relay_events WHERE ts>=?", (since,)).fetchall()
    for r in rows:
        text = f"{r['path']} {r['content']}"
        seen=set()
        for token in TOKEN_RE.findall(text):
            key=token if token.isupper() else token.lower()
            if key.lower() in STOP or len(key) > 48:
                continue
            counts[key]+=1
            seen.add(key)
            first[key]=min(first.get(key,float(r['ts'])),float(r['ts']))
            last[key]=max(last.get(key,float(r['ts'])),float(r['ts']))
        for key in seen:
            if r['client_id']:
                clients[key].add(r['client_id'])
    candidates=[]
    for token,n in counts.items():
        if n < 2:
            continue
        candidates.append({"token":token,"uses":n,"clients":len(clients[token]),"first_seen":first[token],"last_seen":last[token]})
    candidates.sort(key=lambda x:(x["clients"],x["uses"]),reverse=True)
    return candidates[:limit]


def timeline(conn: sqlite3.Connection, hours: int = 24) -> list[dict]:
    since = time.time() - hours * 3600
    rows = conn.execute(
        """SELECT strftime('%Y-%m-%d %H:00', ts, 'unixepoch') as bucket,
                  COUNT(*) as total,
                  SUM(CASE WHEN automation_level='high' THEN 1 ELSE 0 END) as high,
                  SUM(CASE WHEN automation_level='medium' THEN 1 ELSE 0 END) as medium,
                  SUM(CASE WHEN automation_level='low' THEN 1 ELSE 0 END) as low,
                  SUM(CASE WHEN status >= 200 AND status < 300 THEN 1 ELSE 0 END) as s2xx,
                  SUM(CASE WHEN status >= 300 AND status < 400 THEN 1 ELSE 0 END) as s3xx,
                  SUM(CASE WHEN status >= 400 AND status < 500 THEN 1 ELSE 0 END) as s4xx,
                  SUM(CASE WHEN status >= 500 THEN 1 ELSE 0 END) as s5xx,
                  COALESCE(SUM(response_bytes), 0) as bytes
           FROM access_events WHERE ts >= ?
           GROUP BY bucket ORDER BY bucket ASC""",
        (since,),
    ).fetchall()
    return [dict(r) for r in rows]


def status_distribution(conn: sqlite3.Connection, hours: int = 24) -> list[dict]:
    since = time.time() - hours * 3600
    rows = conn.execute(
        """SELECT status, COUNT(*) as count
           FROM access_events WHERE ts>=?
           GROUP BY status ORDER BY count DESC""",
        (since,),
    ).fetchall()
    return [dict(r) for r in rows]


def method_distribution(conn: sqlite3.Connection, hours: int = 24) -> list[dict]:
    since = time.time() - hours * 3600
    rows = conn.execute(
        """SELECT method, COUNT(*) as count
           FROM access_events WHERE ts>=?
           GROUP BY method ORDER BY count DESC""",
        (since,),
    ).fetchall()
    return [dict(r) for r in rows]


def ua_breakdown(conn: sqlite3.Connection, hours: int = 24, limit: int = 15) -> list[dict]:
    since = time.time() - hours * 3600
    rows = conn.execute(
        """SELECT user_agent, COUNT(*) as hits, COUNT(DISTINCT client_id) as clients,
                  ROUND(AVG(automation_score), 1) as avg_auto
           FROM access_events WHERE ts>=?
           GROUP BY user_agent ORDER BY hits DESC LIMIT ?""",
        (since, limit),
    ).fetchall()
    return [dict(r) for r in rows]


def system_stats(conn: sqlite3.Connection) -> dict:
    access_cnt = conn.execute("SELECT COUNT(*) FROM access_events").fetchone()[0]
    relay_cnt = conn.execute("SELECT COUNT(*) FROM relay_events").fetchone()[0]
    first_ts = conn.execute("SELECT MIN(ts) FROM access_events").fetchone()[0]
    last_ts = conn.execute("SELECT MAX(ts) FROM access_events").fetchone()[0]
    page_size = conn.execute("PRAGMA page_size").fetchone()[0]
    page_count = conn.execute("PRAGMA page_count").fetchone()[0]
    journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    return {
        "access_records": access_cnt,
        "relay_records": relay_cnt,
        "db_size_bytes": page_size * page_count,
        "journal_mode": str(journal_mode),
        "first_ts": first_ts or 0,
        "last_ts": last_ts or 0,
    }
