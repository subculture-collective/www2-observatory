from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AutomationAssessment:
    score: int
    level: str
    signals: tuple[str, ...]


BOT_UA_PARTS = (
    "bot", "crawler", "spider", "curl/", "wget/", "python-requests", "python-httpx",
    "go-http-client", "libwww-perl", "httpie/", "feedfetcher", "validator",
)
BROWSER_UA_PARTS = ("mozilla/5.0", "chrome/", "safari/", "firefox/", "edg/")


def assess(method: str, path: str, user_agent: str, accept: str) -> AutomationAssessment:
    score = 0
    signals: list[str] = []
    m = method.upper()
    p = path.lower()
    ua = user_agent.lower()
    ac = accept.lower()

    if m == "OPTIONS":
        score += 4; signals.append("capability-probe")
    elif m == "HEAD":
        score += 2; signals.append("head-probe")
    elif m in {"PUT", "PATCH", "DELETE"}:
        score += 3; signals.append("programmatic-write-method")

    if any(part in ua for part in BOT_UA_PARTS):
        score += 4; signals.append("automation-user-agent")
    elif ua and not any(part in ua for part in BROWSER_UA_PARTS):
        score += 1; signals.append("non-browser-user-agent")

    if "application/json" in ac and "text/html" not in ac:
        score += 2; signals.append("json-preference")
    if "text/plain" in ac and "text/html" not in ac:
        score += 2; signals.append("plain-text-preference")

    if p.endswith((".json", ".ndjson", ".txt", ".xml", ".atom")):
        score += 1; signals.append("machine-friendly-representation")
    if p.startswith("/.well-known/") or p in {"/robots.txt", "/sitemap.xml", "/feed.json", "/feed.ndjson", "/feed.atom"}:
        score += 1; signals.append("discovery-resource")

    if any(part in ua for part in BROWSER_UA_PARTS) and "text/html" in ac and m == "GET":
        score -= 1

    score = max(score, 0)
    level = "high" if score >= 6 else "medium" if score >= 3 else "low"
    return AutomationAssessment(score, level, tuple(signals))
