from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit


@dataclass
class AccessRecord:
    ts: float
    host: str
    remote_ip: str
    method: str
    path: str
    query: str
    status: int
    user_agent: str
    accept: str
    referer: str
    content_type: str
    size: int


@dataclass
class RelayRecord:
    ts: float
    event: str
    path: str
    remote_ip: str
    user_agent: str
    content: str
    metadata: dict


def _first(headers: dict, name: str) -> str:
    for k, v in headers.items():
        if k.lower() == name.lower():
            if isinstance(v, list):
                return str(v[0]) if v else ""
            return str(v)
    return ""


def _timestamp(value) -> float:
    if value is None:
        return datetime.now(UTC).timestamp()
    if isinstance(value, (int, float)):
        # Caddy uses unix seconds with decimals.
        return float(value)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value).timestamp()
        except ValueError:
            try:
                return float(value)
            except ValueError:
                pass
    return datetime.now(UTC).timestamp()


def normalize_host(value: str) -> str:
    value = value.strip().lower()
    if not value:
        return ""
    parsed = urlsplit(f"//{value}")
    return (parsed.hostname or "").rstrip(".")


def parse_caddy_line(line: str) -> AccessRecord | None:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    req = obj.get("request") or {}
    headers = req.get("headers") or {}
    uri = req.get("uri") or obj.get("uri") or "/"
    parsed = urlsplit(uri)
    remote_ip = req.get("remote_ip") or req.get("client_ip") or obj.get("remote_ip") or ""
    return AccessRecord(
        ts=_timestamp(obj.get("ts") or obj.get("time")),
        host=normalize_host(str(req.get("host") or _first(headers, "Host"))),
        remote_ip=str(remote_ip),
        method=str(req.get("method") or obj.get("method") or "GET"),
        path=parsed.path or "/",
        query=parsed.query,
        status=int(obj.get("status") or 0),
        user_agent=_first(headers, "User-Agent"),
        accept=_first(headers, "Accept"),
        referer=_first(headers, "Referer"),
        content_type=str((obj.get("resp_headers") or {}).get("Content-Type", [""])[0] if isinstance((obj.get("resp_headers") or {}).get("Content-Type", [""]), list) else (obj.get("resp_headers") or {}).get("Content-Type", "")),
        size=int(obj.get("size") or 0),
    )


def parse_relay_line(line: str) -> RelayRecord | None:
    try:
        obj = json.loads(line)
    except json.JSONDecodeError:
        return None
    event = str(obj.get("event") or obj.get("kind") or "")
    if not event:
        return None
    content = obj.get("content") or obj.get("body") or obj.get("text") or ""
    return RelayRecord(
        ts=_timestamp(obj.get("ts") or obj.get("time")),
        event=event,
        path=str(obj.get("path") or ""),
        remote_ip=str(obj.get("remote_ip") or obj.get("client_ip") or ""),
        user_agent=str(obj.get("user_agent") or ""),
        content=str(content),
        metadata={k: v for k, v in obj.items() if k not in {"ts", "time", "event", "kind", "path", "remote_ip", "client_ip", "user_agent", "content", "body", "text"}},
    )
