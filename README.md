# www2-observatory

A private, passive observatory for one small website,
[Deadweb Relay](https://github.com/subculture-collective/deadweb-relay) at
`www2.onnwee.me`. It reads the server's existing Caddy access logs, and
optionally the relay's own event logs, and turns them into a dashboard of who
visits, how they find the site, what they probe and what they write.

It adds nothing to the public site. There is no tracking pixel, script, cookie,
extra request or public dashboard route; the observatory never receives a
request from a visitor:

```text
visitor -> Caddy -> www2 application
            |
            +--> JSON access log --> observatory (read-only)
```

It is a personal research tool, built for that one site. The dashboard is meant
to stay private.

## What it records

From Caddy JSON access logs:

- timestamp, method, path, query, status, response size and type
- User-Agent and Accept header, and a cleaned-up referrer
- pseudonymous source and client IDs (keyed HMAC; raw IP addresses are not
  stored)
- reconstructed sessions and navigation trails
- requests for machine-readable versions of pages
- `OPTIONS`, `HEAD` and write-method probing
- referrer and discovery channels
- a transparent automation-likelihood score

From the relay's optional event logs:

- public note, guestbook and wall writes
- cleaned public content, path and content hashes
- repeated tokens and conventions that spread between clients

## Dashboard

A Go service ingests the logs into SQLite and serves an API and a React
dashboard.

| Route | Contents |
| --- | --- |
| `/` | Headline numbers with changes from the previous window, traffic over time, a fingerprint radar, the funnel, newest events and entry pages |
| `/traffic` | Timeline, hour-by-weekday heatmap, status counts, every path, user agent and referring host |
| `/diagnostics` | Probe families, request shapes, 404 paths, possible broken links, source concentration and a review queue |
| `/funnel` | The five ordered stages, with definitions and evidence |
| `/clients`, `/clients/<id>` | One row per fingerprint, and a detail page with sessions, trails, writes and raw events |
| `/writes` | Writes over time, written objects and who read them, relay write events |
| `/events` | Filterable raw event log with NDJSON export |
| `/interventions` | Dated ledger of changes made to the site |
| `/system` | Record age and counts, database size, ingest offsets |
| `/glossary` | What every view shows, what it can and cannot tell you, and where its data comes from |

Every panel has a **?** control with the same description. The time window runs
from 1 hour to 90 days (default 30 days). Probe charts use fixed colors per
probe family; the key is at `/glossary#probe-colors`. Motion follows the
system's reduce-motion setting.

Read [docs/MEASUREMENT.md](docs/MEASUREMENT.md) before treating fingerprints as
participants.

## Quick start

You need Go 1.24 or newer and Node.js with npm.

Try it with synthetic data:

```sh
npm ci --prefix frontend
npm run build --prefix frontend
mkdir -p /tmp/obsdev
python3 scripts/gen_demo_log.py /tmp/obsdev/access.jsonl --days 14
export OBS_CADDY_LOG=/tmp/obsdev/access.jsonl OBS_DB=/tmp/obsdev/obs.sqlite3 \
  OBS_KEY_FILE=/tmp/obsdev/key OBS_TRUST_CADDY_CLIENT_IP=true
go run ./cmd/observatory ingest-once
go run ./cmd/observatory run
```

The dashboard is at <http://127.0.0.1:9099>. For frontend work, run
`npm run dev --prefix frontend` next to the Go service; Vite proxies `/api/*`
and `/healthz` to it. Never ingest demo data into a real database.

Tests and checks:

```sh
go test -race ./...
go vet ./...
python3 -m unittest discover -s tests -v   # Python reference implementation
npm run build --prefix frontend            # typecheck and build
```

The `observatory/` directory holds the original Python implementation, kept as a
reference and test baseline. It needs only Python 3.11 and the standard library
(`python3 -m observatory.main ingest-once`, then `run`).

## Configuration

Copy `.env.example` to `.env`.

| Variable | Purpose |
| --- | --- |
| `CADDY_LOG_DIR` | Host directory holding only this site's Caddy logs; Compose mounts it read-only |
| `OBS_CADDY_LOG` | Path of the access log inside the container (default `/logs/access.jsonl`) |
| `OBS_ALLOWED_HOSTS` | Hostnames to accept from the log (default `www2.onnwee.me`) |
| `OBS_TRUST_CADDY_CLIENT_IP` | Use Caddy's `client_ip`; turn on only when Caddy trusts the right proxy |
| `OBS_RELAY_LOG`, `OBS_RELAY_DIR` | Optional relay event log, or a directory of relay ledgers |
| `OBS_DB`, `OBS_KEY_FILE` | SQLite database and the pseudonym key |
| `OBS_BIND`, `OBS_PORT` | Dashboard address (default `127.0.0.1:9099`) |
| `OBS_TOKEN` | Optional bearer token for `/api/*` and the dashboard |
| `OBS_SESSION_MINUTES` | Gap that ends a session |
| `OBS_CONTENT_MAX` | Maximum public write content kept from relay logs |
| `OBS_STATIC_DIR` | Built frontend directory (default `frontend/dist`) |

[docs/CADDY.md](docs/CADDY.md) shows the Caddy logging setup.

## Deploy

The `Dockerfile` builds the frontend and a static Go binary into a small Alpine
image that runs as an unprivileged user.

```sh
cp .env.example .env
mkdir -p state
docker compose up -d --build
```

Compose mounts `./state` for the database and key, `./backups`, the Caddy log
directory and `./relay-ledger` read-only, and publishes the dashboard on
`127.0.0.1:9099` only. It also joins an external Docker network named
`projects`; create it with `docker network create projects` or remove that block.
Reach the dashboard over an SSH tunnel (`ssh -L 9099:127.0.0.1:9099 your-server`)
or put real authentication in front of it.

The observatory never prunes parsed records. Back up with:

```sh
docker compose exec observatory /app/observatory backup --state /data --output /backups --keep 14
```

That writes a timestamped, integrity-checked snapshot of the database with its
matching key. Keep the key with every backup; without it, pseudonyms cannot be
matched to new records.

## API

All endpoints accept `hours=` (default 24) and, for lists, `limit=`. Times are
Unix seconds, UTC. If `OBS_TOKEN` is set, send `Authorization: Bearer <token>`.

```text
/api/summary          headline counts and splits, with the previous window
/api/timeline         per hour (or bucket=day)
/api/experiment       ordered funnel, evidence, attribution, class totals
/api/clients          one row per fingerprint; class= and order= filters
/api/client?id=       one fingerprint: summary, sessions, events, objects, stages
/api/recent           raw events; method=, level=, status=, class=, client=, link=1, search=
/api/event?id=        one raw event
/api/objects          written objects with reads and readers
/api/link-writes      GET requests carrying post=, body=, set= or append=
/api/representations  2xx responses by media type
/api/heatmap          requests by UTC weekday and hour
/api/entrances        first request of each session
/api/paths            paths with class, method, write and error splits
/api/user-agents      user agents with class, representation and write splits
/api/referrers /api/status /api/methods /api/signals /api/sessions
/api/writes /api/conventions   relay events (when relay logs are mounted)
/api/ingest           record counts, ingest offsets, reconciliation runs
/api/interventions    the intervention ledger
/api/export.ndjson    newest events as NDJSON (limit ≤ 500)
```

## Reading the numbers

The automation score is a heuristic. It says "high automation likelihood", never
which program or model sent a request. A person using `curl` can look highly
automated, and an automated client driving a real browser can look ordinary. The
useful evidence is behavior over time: discovery, return visits, repeated paths
and identities, shared resources, and conventions passing between distinct
pseudonymous clients. A 404 alone does not make a request a probe, and a probe
answered with a 2xx goes to the review queue, not to a count of confirmed
exploits.

See [docs/DETECTION.md](docs/DETECTION.md) and [docs/PRIVACY.md](docs/PRIVACY.md).

## Project layout

```text
cmd/observatory   entry point: run, ingest-once, reconcile-access, backup, healthcheck
internal/         ingestion, parsers, scoring, analytics, API, SQLite, backups
frontend/         Vite + React + TypeScript dashboard
observatory/      Python reference implementation
scripts/          demo log generator and helpers
tests/            Python reference tests
examples/         sample Caddy and relay log lines
```

## Contributing

- Bugs and feature requests: [GitHub issues](https://github.com/subculture-collective/www2-observatory/issues).
- Questions and ideas: [GitHub Discussions](https://github.com/subculture-collective/www2-observatory/discussions).
- Code: open a pull request on GitHub against `main`. CI checks Go formatting,
  runs the Go tests with the race detector, `go vet` and a production build, runs
  the Python reference tests, and typechecks and builds the frontend.

## License

www2-observatory is licensed under the GNU General Public License, version 3 or
later (GPL-3.0-or-later). See [LICENSE](LICENSE).
