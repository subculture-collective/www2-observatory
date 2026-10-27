# Privacy model

This project is deliberately passive.

It does **not** add JavaScript, cookies, tracking pixels, browser fingerprinting, hidden resources, redirects, or public observatory endpoints to the monitored site.

Normal server access logs necessarily contain a source address while the request is being processed. During ingestion, the observatory derives keyed HMAC pseudonyms and discards the raw address rather than writing it to its database.

Access-log ingestion is restricted to normalized host `www2.onnwee.me`. Production mounts only that site's dedicated Caddy log directory; records with another or missing host are rejected as a second layer of isolation.

External referrer query strings are stripped. Optional public write content is passed through a basic credential/private-key scrubber and truncated before storage.

The resulting IDs are useful for reconstructing repeat visits on this one installation but are not portable identifiers and cannot be correlated with another installation without the local secret key.

Normalized records are retained indefinitely. Raw Caddy logs remain outside Observatory and use the bounded retention configured in `docs/CADDY.md`. Backups must keep `observatory.sqlite3` and `pseudonym.key` together; loss of the key changes future pseudonyms and prevents continuity with restored history.

The default dashboard binding is localhost/private-host only. If you expose it elsewhere, put authentication and TLS in front of it or set `OBS_TOKEN`.
