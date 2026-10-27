# www2-observatory

A private, passive observatory exclusively for `www2.onnwee.me`.

It watches **existing server-side logs**. It does not add anything to the public page and does not need a route on the monitored domain.

## What it records

From ordinary Caddy JSON access logs:

- timestamp
- HTTP method, path, query, status, response size/type
- User-Agent and Accept header
- sanitized referrer
- pseudonymous source/client IDs
- reconstructed sessions and navigation trails
- machine-friendly representation discovery
- `OPTIONS` / `HEAD` / write-method probing
- referrer/discovery channels
- a transparent automation-likelihood score

Optional application event logs can add:

- public note/guestbook/wall write events
- scrubbed public content
- path/content hashes
- repeated token / convention candidates

Raw IP addresses are **not persisted** in the observatory database.

## Why this is invisible to the public site

The normal request path remains:

```text
visitor -> Caddy -> www2 application
            |
            +--> ordinary JSON access log
                         |
                         +--> observatory (read-only)
```

The observatory never has to receive a request from a visitor. There is no tracking pixel, injected script, analytics cookie, extra API request, or public dashboard route.

## Current implementation

The production runtime uses a **Go API/runtime** plus a **Vite TypeScript React** frontend. The Go binary handles log ingestion, SQLite analytics, `/api/*`, `/healthz`, NDJSON export, and serving the compiled React app from `frontend/dist`. Client-side routes fall back to `index.html`.

The interface was redesigned on 2026-09-25 as a set of pages rather than one dashboard. It uses the Evangelion-rice palette (`theme/colors.toml` in that repository): monospace, small-caps labels, thin bordered panels with an inset accent bar, optional scanlines, and one deliberately theatrical element per page that still encodes real data (the fingerprint radar, the tilted timeline). There is no branding copy; every label is a fact or a control.

Every panel has a **?** control that opens a description with five parts: what the view shows, what it determines, why it is recorded, caveats, and the API source. The same text is collected on the glossary page and lives in `frontend/src/lib/descriptions.ts`.

Pages:

| Route | Contents |
| --- | --- |
| `/` overview | Headline numbers with previous-window deltas and sparklines; traffic over time stacked by class, method, representation, outcome, automation, or writes, with intervention markers; fingerprint radar; ordered funnel; outcome and representation rings; newest events; entrances |
| `/traffic` | Timeline; hour × weekday heatmap; exact status counts; every path with class, method, write, and error splits; every user agent; referring hosts |
| `/funnel` | Eligible fingerprints, writes, returns, cross-source reads; the five ordered stages with definitions; class and address-basis totals; milestone evidence; measurement rules |
| `/clients` | One row per fingerprint, filterable (resource, wrote, verified, scan-shaped, operator, other), sortable; radar |
| `/clients/<id>` | One fingerprint: aggregate, stages reached with the evidence event, sessions with full trails, objects written, agents, raw events |
| `/writes` | Writes over time; written objects with readers and cross-source reads; writes by link; relay write events and repeated tokens when the relay log is mounted |
| `/events` | Raw event log with class, method, automation, status, link-write, fingerprint, and text filters; row drawer; NDJSON export |
| `/interventions` | The dated ledger with scope tags and resource hashes |
| `/system` | Newest record age, record counts, database size, whole-database class and address-basis totals, automation signals, ingest offsets, reconciliation runs |
| `/glossary` | All view descriptions in one place |

Top rail: time window (1h to 90d), refresh interval, scanlines, motion, depth, UTC clock. Bottom rail: newest record age, record counts, verified-address share, database size, last refresh. Settings persist in `localStorage`.

The original Python implementation remains in the repository as a parity reference and test baseline. Its `views/dashboard.py` is the previous visual reference and is no longer what the frontend renders.

See [measurement definitions and operator practice](docs/MEASUREMENT.md) before interpreting fingerprints as participants.

## Quick start

### 1. Configure Caddy JSON logging

See [`docs/CADDY.md`](docs/CADDY.md).

### 2. Configure the observatory

```sh
cp .env.example .env
mkdir -p state
```

Create the dedicated host directory configured by `CADDY_LOG_DIR` and adjust that narrow mount if needed. On Almaz it is `/opt/server/management/data/caddy/logs/www2`. Do not mount the shared Caddy log directory.

### 3. Run

```sh
docker compose up -d --build
```

The dashboard is available only on the server's loopback interface:

```text
http://127.0.0.1:9099
```

Use an SSH tunnel to view it from another machine:

```sh
ssh -L 9099:127.0.0.1:9099 your-server
```

Then browse to `http://127.0.0.1:9099` locally.

## Run without Docker

Go 1.24+ and Node.js/npm are required for the new runtime.

```sh
npm install --prefix frontend
npm run build --prefix frontend
go run ./cmd/observatory ingest-once
go run ./cmd/observatory run
```

For local development, run the Go API on `127.0.0.1:9099` and the Vite dev server separately:

```sh
go run ./cmd/observatory run
npm run dev --prefix frontend
```

The Vite dev server proxies `/api/*` and `/healthz` to the Go API.

### Legacy Python reference

Python 3.11+ and the standard library are sufficient.

```sh
export OBS_CADDY_LOG="$PWD/examples/caddy-access.jsonl"
export OBS_RELAY_LOG="$PWD/examples/relay-events.jsonl"
export OBS_DB="$PWD/state/observatory.sqlite3"
export OBS_KEY_FILE="$PWD/state/pseudonym.key"
python3 -m observatory.main ingest-once
python3 -m observatory.main run
```

No third-party Python packages are required.

## Retention and backup

Observatory never prunes parsed records. Caddy keeps the bounded raw-log window described in [`docs/CADDY.md`](docs/CADDY.md). Back up `state/observatory.sqlite3` using SQLite's online backup command rather than copying only the live database file, and preserve `state/pseudonym.key` with every backup. Verify restored databases with `PRAGMA integrity_check`.

After the service has created its state, run `docker compose exec observatory /app/observatory backup --state /data --output /backups --keep 14`. It writes a timestamped, integrity-checked database snapshot and matching key under the host's `backups/` directory. The Almaz timer runs this before the nightly restic job, which keeps longer version history.

## Local development with synthetic data

`scripts/gen_demo_log.py` writes a fictional Caddy JSON log shaped like the real mix (browsers with referrers, crawlers, scan-shaped probes, operator probes, fetch-only clients that walk the funnel and write by PUT or by link). Ingest it into a throwaway database:

```sh
python3 scripts/gen_demo_log.py /tmp/obsdev/access.jsonl --days 14
OBS_CADDY_LOG=/tmp/obsdev/access.jsonl OBS_DB=/tmp/obsdev/obs.sqlite3 OBS_KEY_FILE=/tmp/obsdev/key \
  OBS_TRUST_CADDY_CLIENT_IP=true go run ./cmd/observatory ingest-once
OBS_CADDY_LOG=/tmp/obsdev/access.jsonl OBS_DB=/tmp/obsdev/obs.sqlite3 OBS_KEY_FILE=/tmp/obsdev/key \
  OBS_TRUST_CADDY_CLIENT_IP=true OBS_STATIC_DIR=frontend/dist go run ./cmd/observatory run
```

Never ingest that file into the production database.

## API

All endpoints accept `hours=` (default 24) and, where a list is returned, `limit=`. Times are Unix seconds, UTC.

```text
/api/summary          headline counts, class/method/representation/write splits, previous window
/api/timeline         per hour (or bucket=day) with the same splits; empty buckets omitted
/api/experiment       ordered funnel, evidence, attribution, class totals
/api/clients          one row per fingerprint; class=engagement|scanner|operator|other|writers|verified; order=requests|writes|automation|first_seen
/api/client?id=       one fingerprint: summary, sessions, events, user agents, objects, stages
/api/recent           raw events; method=, level=, status= (exact or 2–5 for a class), class=, client=, link=1, search=
/api/event?id=        one raw event
/api/objects          written objects with reads, readers, cross-source reads
/api/link-writes      GET requests carrying post=, body=, set=, or append=
/api/representations  2xx responses by media-type family
/api/heatmap          requests by UTC weekday and hour
/api/entrances        first request of each session by path and referring host
/api/paths            paths with class, method, write, and error splits
/api/user-agents      agents with class, representation, and write splits
/api/referrers /api/status /api/methods /api/signals /api/sessions
/api/writes /api/conventions   relay application events (when the relay log is mounted)
/api/ingest           record counts, newest record, ingest offsets, reconciliation runs, class and attribution totals
/api/interventions    the ledger copied from the relay repo's docs/INTERVENTIONS.json
/api/export.ndjson    newest events as NDJSON (limit ≤ 500; class= and client= filters)
```

If `OBS_TOKEN` is set, send:

```text
Authorization: Bearer <token>
```

## Important interpretation note

The automation score is a heuristic. It deliberately says things like "high automation likelihood," not "this was Claude" or "this was an AI agent." A person using `curl` can look highly automated, and an autonomous system using Chrome can look completely ordinary.

The valuable evidence is usually **behavior over time**: discovery, return visits, repeated identity/path usage, coordination through shared resources, and conventions propagating between distinct pseudonymous clients.

See [`docs/DETECTION.md`](docs/DETECTION.md) and [`docs/PRIVACY.md`](docs/PRIVACY.md).
