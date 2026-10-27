from __future__ import annotations

import os
from dataclasses import dataclass


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass(frozen=True)
class Config:
    caddy_log: str = os.getenv("OBS_CADDY_LOG", "/logs/access.jsonl")
    allowed_hosts: str = os.getenv("OBS_ALLOWED_HOSTS", "www2.onnwee.me")
    relay_log: str = os.getenv("OBS_RELAY_LOG", "")
    db_path: str = os.getenv(
        "OBS_DB",
        "state/observatory.sqlite3" if os.path.exists("state/observatory.sqlite3") else "/data/observatory.sqlite3",
    )
    key_file: str = os.getenv(
        "OBS_KEY_FILE",
        "state/pseudonym.key" if os.path.exists("state/pseudonym.key") else "/data/pseudonym.key",
    )
    bind: str = os.getenv("OBS_BIND", "127.0.0.1")
    port: int = _int("OBS_PORT", 9099)
    token: str = os.getenv("OBS_TOKEN", "")
    session_minutes: int = _int("OBS_SESSION_MINUTES", 30)
    content_max: int = _int("OBS_CONTENT_MAX", 8192)
    poll_seconds: float = float(os.getenv("OBS_POLL_SECONDS", "1.0"))
