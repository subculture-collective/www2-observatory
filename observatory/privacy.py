from __future__ import annotations

import hashlib
import hmac
import os
import re
from urllib.parse import urlsplit, urlunsplit

_SECRET_PATTERNS = [
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[A-Za-z0-9._~+/=-]{12,}"),
    re.compile(r"(?i)((?:api[_-]?key|token|password|passwd|secret)\s*[:=]\s*)[^\s,;]{8,}"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    re.compile(r"\b(?:sk|rk|pk)-[A-Za-z0-9_-]{20,}\b"),
]


def load_or_create_key(path: str) -> bytes:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    try:
        with open(path, "rb") as f:
            key = f.read().strip()
            if len(key) >= 32:
                return key
    except FileNotFoundError:
        pass
    key = os.urandom(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(key)
    return key


def pseudonym(key: bytes, value: str, prefix: str = "p") -> str:
    digest = hmac.new(key, value.encode("utf-8", "replace"), hashlib.sha256).hexdigest()
    return f"{prefix}_{digest[:20]}"


def scrub_text(text: str, max_len: int = 8192) -> str:
    out = text[:max_len]
    for pattern in _SECRET_PATTERNS:
        out = pattern.sub(lambda m: (m.group(1) if m.lastindex else "") + "[REDACTED]", out)
    return out


def sanitize_referrer(raw: str, own_hosts: set[str] | None = None) -> tuple[str, str]:
    if not raw:
        return "", ""
    own_hosts = own_hosts or set()
    try:
        u = urlsplit(raw)
    except ValueError:
        return "", ""
    host = (u.hostname or "").lower()
    # Preserve query only for our own site; external query strings often contain tracking or private data.
    query = u.query if host in own_hosts else ""
    clean = urlunsplit((u.scheme, u.netloc, u.path, query, ""))
    return clean[:2048], host[:255]
