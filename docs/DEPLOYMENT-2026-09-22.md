# WWW2 Observatory deployment — 2026-09-22

Deployed on Almaz at 22:14 CDT (2026-09-23 03:14 UTC). The Go runtime and Vite TypeScript React frontend replace the Python runtime at https://observatory.onnwee.me. Public access still redirects to Authelia. No fresh authenticated public login was performed; browser checks used a private SSH tunnel to the live service.

## Artifact and source

- Runtime directory: `/opt/server/projects/www2-observatory` on Almaz.
- Image: `www2-observatory-observatory:latest`.
- Verified running image ID: `sha256:3bd6cf679ed7c5f1f4f39df8fb67eee9d0060285d73659dc1c5c8b4d6ee81b84`.
- Source copied from Kvant's `/home/onnwee/Work/Subcult/deadweb-relay/www2-observatory`. Its Git repository has no commits or configured remote, so this deployment has an image identity but no source commit identity.
- Production `.env`, state, backups, log mount, loopback port binding, and projects network were retained.

## Repair and verification

A browser check exposed intermittent SQLite lock failures during concurrent startup requests. `internal/db/db.go` now sets a 5000 ms busy timeout before schema initialization. The regression test fails without this setting and passes with it. All Go tests and the containerized TypeScript/Vite build passed. After repair, three candidate restarts with 800 concurrent API requests each produced no HTTP errors.

The production container reports healthy. All 15 health/API endpoint probes passed. HUD, Ops, Exec, Forensics, and Hub navigation worked in the live browser. The remaining browser console error is a missing `/favicon.ico` (404).

The pre-cutover database contained 422 access events; the live database contained 423 after verification. Relay events remained at zero. SQLite integrity_check returned `ok`; the pseudonym key matched the pre-cutover backup byte-for-byte. Verification traffic is operator activity, not evidence of organic discovery.

The systemd backup command now invokes `/app/observatory backup`. A manual systemd run succeeded and the timer remains active. Its verified snapshot is `backups/20260923T031426Z`. The public relay health endpoint also passed.

## Rollback

The prior Python image is retained as `www2-observatory:rollback-20260922`. Prior Compose, Dockerfile, backup service, and source archive are under `/opt/server/projects/www2-observatory-rollback-20260922`. Pre-cutover database/key snapshot: `/opt/server/projects/www2-observatory/backups/20260923T031343Z`.

To roll back the runtime, restore the saved Compose and Dockerfile, tag the rollback image as `www2-observatory-observatory:latest`, and run `docker compose up -d --no-build --wait` from the runtime directory. Restore the saved systemd backup service and run `systemctl daemon-reload`. Retain current state unless a separate data restore is needed; restoring the old snapshot would discard newer records. Check health, dashboard, and backup execution afterward.

## Candidate 4 correction and favicon — 22:27 CDT

The initial React deployment did not preserve the selected candidate 4 frontend. Corrected it by porting the original `observatory/views/dashboard.py` HUD to TypeScript/React, preserving the acid-green/purple palette and six-pane layout. Candidate 4 is now the default at `/` and `/4`; legacy preview routes also resolve to this selected interface. The relay remains on its existing Go/server-rendered stack, with its retro appearance and HTML/text contracts unchanged.

The corrected image is `www2-observatory:candidate4-20260922`; the running container and host image both report `sha256:9e4e2ae7ec72ff43ed4a8e86269e41491ded9ef6c2504bd397439832bc648376`. Compose reports healthy. The database still contains 423 access records and zero relay events at readback.

TypeScript/Vite and container builds passed. Compared desktop screenshots against the original Python HUD rendered from a production snapshot. Browser assertions passed for palette persistence, CRT toggle, pane controls and keyboard shortcuts, packet inspector, command filtering, NDJSON download, 15-second refresh, and mobile overflow at 390px. Live checks confirmed candidate 4 at `/` and `/4`, palette changes, and packet inspection with zero console errors. Public HTTPS still redirects to Authelia; fresh public authentication was not repeated.

Added matching acid-green/purple radar favicons: SVG and ICO (16, 32, and 48px). Both production responses match the authored files byte-for-byte, resolving the earlier favicon 404. Refresh now updates data without resetting the chosen filter, palette, pane, or inspector. Heuristic labels describe high/medium/low scores rather than claiming a request was made by a bot or human.

The immediately previous frontend image is retained as `www2-observatory:before-candidate4-20260922`. For a frontend-only rollback, retag that image as `www2-observatory-observatory:latest` and recreate with `docker compose up -d --no-build --wait`; retain state and the Go backup service. The older Python rollback described above is also retained.
