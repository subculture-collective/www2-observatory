# Caddy integration

The observatory does not need to be proxied through the public site. It only needs read access to the normal Caddy JSON access log.

Example Caddyfile fragment:

```caddyfile
www2.onnwee.me {
    log {
        output file /data/logs/www2/access.jsonl {
            mode 0640
            roll_size 50mb
            roll_keep 100
            roll_keep_for 720h
        }
        format json
    }

    reverse_proxy 127.0.0.1:8080
}
```

On Almaz this maps to `/opt/server/management/data/caddy/logs/www2`. Mount only that directory read-only into the observatory container. The dedicated directory and the `OBS_ALLOWED_HOSTS=www2.onnwee.me` check prevent other virtual hosts from entering the database. Nothing about this changes the response sent to a visitor.

## Rotation

The tailer reads timestamped Caddy rotations oldest-first and the active file last. It supports gzip-compressed rotations, persists offsets by file identity, waits for partial lines to be completed, and suppresses duplicate records when a rotated file is recreated during compression.

The configuration above keeps raw logs for up to 30 days and 100 files of 50 MiB (about 5 GiB). Parsed records in Observatory's SQLite database are not automatically deleted.

## Dashboard exposure

`docker-compose.yml` publishes the dashboard only on `127.0.0.1:9099`. On Almaz, expose `observatory.onnwee.me` through Caddy with the existing Authelia forward-auth endpoint, and restrict the Authelia policy to user `onnwee` with two-factor authentication. Keep Observatory's own access log outside `/data/logs/www2`.

Both `observatory.onnwee.me` and the Authelia portal `auth.onnwee.me` need proxied DNS records targeting Almaz's existing Cloudflare Tunnel. See `deploy/almaz/README.md`.

Without that edge route, use an SSH tunnel or your existing private VPN:

```sh
ssh -L 9099:127.0.0.1:9099 your-server
```

Then open `http://127.0.0.1:9099` locally.
