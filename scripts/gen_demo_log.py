#!/usr/bin/env python3
"""Generate a synthetic Caddy JSON access log for local observatory development.

The output is fictional traffic shaped like the real site's mix: browsers with
referrers, search crawlers, scan-shaped probes, operator-marked probes, and a
few fetch-only clients that walk the discovery funnel, write by PUT or by
link, and return later. Nothing here is real data; never ingest it into the
production database. Deterministic for a given seed.

Usage: gen_demo_log.py OUT.jsonl [--days 14] [--seed 7]
"""
from __future__ import annotations

import argparse
import json
import random
import time

HOST = "www2.onnwee.me"
BROWSER_UA = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/152.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 Mobile/15E148 Safari/604.1",
    "Lynx/2.9.2 libwww-FM/2.14 SSL-MM/1.4.1 OpenSSL/3.3.1",
]
CRAWLER_UA = [
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; MarginaliaBot/1.0; +https://search.marginalia.nu)",
    "WibyBot/1.0",
    "Mozilla/5.0 (compatible; Applebot/0.1; +http://www.apple.com/go/applebot)",
]
FETCHER_UA = [
    "python-requests/2.32.3",
    "python-httpx/0.28.1",
    "Go-http-client/2.0",
    "node-fetch/1.0 (+https://github.com/bitinn/node-fetch)",
    "curl/8.9.1",
    "Wget/1.24.5",
    "axios/1.7.7",
]
SCANNER_UA = ["Mozilla/5.0 zgrab/0.x", "python-requests/2.25.1", "Mozilla/5.0 (compatible; CensysInspect/1.1)", "masscan/1.3"]
HUMAN_PAGES = ["/", "/guestbook/", "/wall/", "/chat/", "/notes/", "/links.html", "/whatsnew.html", "/now.html", "/buttons.html", "/cgi-bin/", "/webring/", "/archive/", "/files/", "/about.html", "/reference/"]
STATIC = ["/static/style.css", "/static/stars.svg", "/static/skull.svg", "/static/btn-site.svg", "/static/button.png"]
REFERRERS = ["https://hotlinewebring.club/", "https://search.marginalia.nu/", "https://wiby.me/", "https://www.google.com/", "https://forum.melonland.net/", "https://32bit.cafe/", "", "", "", ""]
SCAN_PATHS = ["/.env", "/wp-login.php", "/.git/config", "/wp-admin/setup-config.php", "/.aws/credentials", "/vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php", "/actuator/health", "/config.json", "/phpinfo.php", "/server-status"]
TEXT_RESOURCES = ["/help.txt", "/README.TXT", "/index.txt", "/recent.txt", "/wall.txt", "/links.txt", "/uptime.txt", "/cgi-bin/time.cgi", "/cgi-bin/fortune.cgi"]
JSON_RESOURCES = ["/feed.json", "/wall.json", "/guestbook/?format=json", "/notes/?format=json", "/.well-known/site-meta.json", "/feed.ndjson"]


def ip(rng: random.Random) -> str:
    return f"{rng.choice([203, 198, 192, 45, 104, 172, 35, 52, 20, 13])}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"


def line(ts: float, client_ip: str, method: str, uri: str, status: int, ua: str, accept: str = "*/*", referer: str = "", ctype: str = "", size: int | None = None, location: str = "") -> str:
    headers = {"User-Agent": [ua], "Accept": [accept]}
    if referer:
        headers["Referer"] = [referer]
    resp = {}
    if ctype:
        resp["Content-Type"] = [ctype]
    if location:
        resp["Location"] = [location]
    return json.dumps({
        "ts": round(ts, 3),
        "request": {"host": HOST, "remote_ip": "172.20.0.249", "client_ip": client_ip, "method": method, "uri": uri, "headers": headers},
        "status": status,
        "size": size if size is not None else (random.randint(300, 14000) if status < 400 else random.randint(120, 600)),
        "resp_headers": resp,
    }, separators=(",", ":"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    rng = random.Random(args.seed)
    random.seed(args.seed)
    now = time.time()
    start = now - args.days * 86400
    rows: list[tuple[float, str]] = []

    def add(ts, *a, **k):
        ts = min(ts, now - 60)  # never emit records from the future
        rows.append((ts, line(ts, *a, **k)))

    # Browsers: 120 visits, daytime-weighted, a few sign the guestbook.
    for _ in range(120):
        day = rng.random() * args.days
        hour = min(23.9, max(0, rng.gauss(15, 4)))
        t = start + day * 86400 + hour * 3600
        addr, ua, ref = ip(rng), rng.choice(BROWSER_UA), rng.choice(REFERRERS)
        pages = rng.sample(HUMAN_PAGES, rng.randint(1, 5))
        if rng.random() < 0.6:
            pages[0] = "/"
        for i, p in enumerate(pages):
            add(t, addr, "GET", p, 200, ua, "text/html,application/xhtml+xml", ref if i == 0 else f"https://{HOST}{pages[i-1]}", "text/html; charset=utf-8")
            if "Lynx" not in ua:
                for s in rng.sample(STATIC, 2):
                    add(t + 0.4, addr, "GET", s, 200, ua, "*/*", f"https://{HOST}{p}", "text/css" if s.endswith(".css") else "image/svg+xml")
            t += rng.uniform(8, 90)
        if rng.random() < 0.15:
            gid = rng.randint(1790300000000, 1790399999999)
            add(t, addr, "POST", "/guestbook/", 303, ua, "text/html", f"https://{HOST}/guestbook/", "", 0, f"/guestbook/{gid}")
            add(t + 0.8, addr, "GET", f"/guestbook/{gid}", 200, ua, "text/html", f"https://{HOST}/guestbook/", "text/html; charset=utf-8")

    # Crawlers: each has a stable address, comes daily, walks robots/sitemap/pages.
    for ua in CRAWLER_UA:
        addr = ip(rng)
        for d in range(args.days):
            t = start + d * 86400 + rng.uniform(0, 86400)
            add(t, addr, "GET", "/robots.txt", 200, ua, "*/*", "", "text/plain; charset=utf-8")
            add(t + 2, addr, "GET", "/sitemap.xml", 200, ua, "*/*", "", "application/xml; charset=utf-8")
            for p in rng.sample(HUMAN_PAGES + TEXT_RESOURCES, rng.randint(3, 9)):
                t += rng.uniform(5, 40)
                add(t, addr, "GET", p, 200, ua, "*/*", "", "text/plain; charset=utf-8" if p.endswith(".txt") or p.endswith(".cgi") else "text/html; charset=utf-8")

    # Scanners: many addresses, short bursts of known probe paths, mostly 404.
    for _ in range(70):
        t = start + rng.random() * args.days * 86400
        addr, ua = ip(rng), rng.choice(SCANNER_UA)
        for p in rng.sample(SCAN_PATHS, rng.randint(1, 5)):
            add(t, addr, rng.choice(["GET", "GET", "POST"]), p, 404, ua, "*/*")
            t += rng.uniform(0.2, 3)

    # Operator probes: marked, read-only.
    for d in range(0, args.days, 2):
        t = start + d * 86400 + 4 * 3600
        addr = "10.0.0.50"
        for p in ["/", "/help.txt", "/feed.json", "/reference/"]:
            add(t, addr, "GET", f"{p}?obs_probe=qualification-{d:02d}", 200, "Deadweb-Operator/1.0", "*/*", "", "text/plain; charset=utf-8" if p.endswith(".txt") else "text/html; charset=utf-8")
            t += 1

    # Fetch-only clients: the interesting part. Nine of them with different depth.
    for k in range(9):
        addr, ua = ip(rng), rng.choice(FETCHER_UA)
        t = start + rng.uniform(1, args.days - 2) * 86400
        add(t, addr, "GET", rng.choice(["/", "/robots.txt", "/index.txt"]), 200, ua, "*/*", rng.choice(["", "https://search.marginalia.nu/"]), "text/html; charset=utf-8")
        t += rng.uniform(2, 30)
        if k >= 1:
            add(t, addr, "GET", "/help.txt", 200, ua, "*/*", "", "text/plain; charset=utf-8")
            t += rng.uniform(2, 20)
            if rng.random() < 0.5:
                add(t, addr, "OPTIONS", "/notes/", 204, ua, "*/*", "", "", 0)
                t += 1
        if k >= 2:
            for p in rng.sample(JSON_RESOURCES + TEXT_RESOURCES, rng.randint(1, 4)):
                add(t, addr, "GET", p, 200, ua, "application/json" if "json" in p else "text/plain", "", "application/json; charset=utf-8" if "json" in p else "text/plain; charset=utf-8")
                t += rng.uniform(1, 15)
        obj = None
        if k >= 4:
            name = f"/notes/{rng.choice(['board','scratch','inbox','agents','test'])}/{rng.choice(['a1','today','hello','sync','x'])}{k}"
            if k % 2 == 0:
                add(t, addr, "PUT", name, 200, ua, "application/json", "", "application/json; charset=utf-8")
            else:
                add(t, addr, "GET", f"{name}?set=hello+from+{k}", 200, ua, "*/*", "", "text/plain; charset=utf-8")
                t += rng.uniform(3, 30)
                add(t, addr, "GET", f"{name}?append=second+line", 200, ua, "*/*", "", "text/plain; charset=utf-8")
            obj = name
            t += rng.uniform(1, 10)
            add(t, addr, "GET", name, 200, ua, "*/*", "", "text/plain; charset=utf-8")
            if rng.random() < 0.5:
                t += 2
                add(t, addr, "GET", "/wall.txt?name=bot&post=hello+wall", 200, ua, "*/*", "", "text/plain; charset=utf-8")
        if k >= 6 and obj:
            t += rng.uniform(3600, 86400 * 2)  # return after the session gap
            add(t, addr, "GET", obj, 200, ua, "*/*", "", "text/plain; charset=utf-8")
            add(t + 4, addr, "GET", "/recent.txt", 200, ua, "*/*", "", "text/plain; charset=utf-8")
        if k >= 7 and obj:
            other = ip(rng)
            t += rng.uniform(600, 86400)
            add(t, other, "GET", "/recent.txt", 200, rng.choice(FETCHER_UA), "*/*", "", "text/plain; charset=utf-8")
            add(t + 3, other, "GET", obj, 200, rng.choice(FETCHER_UA), "*/*", "", "text/plain; charset=utf-8")
            if k == 8:
                add(t + 9, other, "GET", f"{obj}?append=ack+from+another+source", 200, rng.choice(FETCHER_UA), "*/*", "", "text/plain; charset=utf-8")

    # A few 429s and 5xx to keep the outcome chart honest.
    for _ in range(6):
        add(start + rng.random() * args.days * 86400, ip(rng), "GET", "/wall/?post=spam", 429, rng.choice(FETCHER_UA), "*/*")
    for _ in range(2):
        add(start + rng.random() * args.days * 86400, ip(rng), "GET", "/search?q=" + "x" * 40, 500, rng.choice(BROWSER_UA), "text/html")

    rows.sort(key=lambda r: r[0])
    with open(args.out, "w", encoding="utf-8") as f:
        for _, l in rows:
            f.write(l + "\n")
    print(f"wrote {len(rows)} lines to {args.out}")


if __name__ == "__main__":
    main()
