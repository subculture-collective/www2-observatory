# Interpreting relay measurements

The funnel page uses the selected window (24 hours by default, up to 90 days). Fingerprint detail pages compute stages over 90 days regardless of the window. A client is an address-plus-user-agent HMAC fingerprint, not an identified person, model, or independent agent.

## Address provenance

`OBS_TRUST_CADDY_CLIENT_IP=true` permits the parser to use Caddy's computed `request.client_ip`. Enable this only after inspecting the running Caddy trusted-proxy policy. The parser never reads a forwarded address directly from client-supplied headers. Invalid or absent computed addresses fall back to the socket peer and are excluded from the experiment funnel.

The explicit `reconcile-access` command matches retained raw log lines to SHA-256 event keys. It preserves event IDs, times, content, and original source/client/session IDs, replaces matched attribution, and rebuilds sessions chronologically. Missing raw records remain unreconciled; do not guess their identities. Stop the ingestor and back up the database plus key before running it. A second run retains the same identities and session IDs. `measurement_runs` records migration time, revision, and matched count.

## Traffic categories

- **Operator-marked:** User-Agent starts with `Deadweb-Operator/`, or the query contains a nonempty `obs_probe`. These markers are self-declared, not authenticated. This does not retroactively identify older testing traffic.
- **Scan-shaped:** An explicit credential, configuration, or exploit-probe path. Browser-shaped user agents do not override this classification. An arbitrary 404 is not sufficient evidence of scanning.
- **Resource request:** A successful request to a recognized relay resource. This does not establish useful intent, an autonomous client, or organic traffic.
- **Other:** Everything outside those rules, including ordinary static assets and unclassified misses.

All records remain in the database, the events page, and the NDJSON export. The events page filters server-side by class, method, automation level, status, fingerprint, link write, and text. The event drawer shows the category, its reason, and address provenance. Original identities remain available in the JSON record for audit.

## Ordered discovery-to-return funnel

One eligible fingerprint must reach the stages in order, at increasing timestamps, within the selected window:

1. Retrieve the homepage, robots file, sitemap, or text index.
2. Retrieve protocol documentation or make an OPTIONS request to a relay resource.
3. Retrieve a JSON, text, or feed representation.
4. Complete a supported write successfully. Rejected writes and probes of unsupported endpoints do not count. Since 2026-09-25 the relay also accepts writes through GET with a parameter (`post=` on the wall, `body=` on the guestbook, `set=` or `append=` on a note). These are recorded in the `link_write` column and count as successful when the relay answered 2xx. Because a deduplicated or refused link write also answers 2xx with an explanatory body, link writes are an upper bound; the objects page separates them from POST/PUT writes.
5. Retrieve the same durable object with GET after the configured session gap (30 minutes by default). A later overwrite invalidates the link to the earlier writer.

Returning clients and successful writes are also reported independently of this ordered sequence. A client can use the site without passing every funnel stage. A form POST's 303 Location can establish an object URL; a JSON response without a logged object URL cannot. Wall collection reads do not prove that a particular entry was read. A different source reading a written object is a lead for review, not proof of communication or independent agency.

Operator-marked requests, scan-shaped requests, other traffic, and unverified address provenance are excluded from the funnel. Unmarked historical operator traffic can remain; do not label the remainder organic. The evidence table contains up to 100 ordered milestone records for inspection.

## Operator practice and interventions

Use `scripts/operator-probe.py` in the parent relay project for public read-only deployment checks. For manual checks, use `User-Agent: Deadweb-Operator/1.0` and a unique `obs_probe` query tag. These are public labels, not credentials. Controlled write/return scenarios belong in isolated fixture databases, never production telemetry.

The reference shelf is webmaster-authored content. Its publication date and text hashes are recorded in the parent project's `docs/INTERVENTIONS.json`, the private dashboard's `/interventions.json`, and the public `/reference/changes.txt`. Future public content or discovery changes need a new dated entry. Do not use authored content or deliberate test traffic as evidence of independent participation.

## Writes by link

`research.LinkWriteParam` names the parameter a GET carried; `WriteObject` derives an object key for note `set`/`append` from the path and for guestbook `body` from the response `Location`. Wall link writes have no object key because the wall is a collection. `robots.txt` on the relay disallows the write parameters, so compliant crawlers should not appear here. A 429 is the relay's write rate limit. The query string is logged, so the attempted text is visible in the events page.

## Descriptions in the interface

Every panel's "?" control and the glossary page describe what a view shows, what it determines, why it is recorded, and its caveats. They are descriptions of the measurement, not evaluations of the traffic. Keep them in `frontend/src/lib/descriptions.ts` next to the code that renders the view.
