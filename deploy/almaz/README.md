# Almaz deployment

`install.py` installs the Caddy route, exact-user Authelia policy, snapshot timer, and restic include. It creates timestamped `before-observatory` copies before changing existing files.

Cloudflare DNS requires credentials for the `onnwee.me` zone and is intentionally not automated with Almaz's restricted Caddy token. Configure these proxied CNAME records to the existing tunnel target:

- `observatory.onnwee.me` → `c90c06cb-92ed-4653-9d8b-57ad5dc5dd87.cfargotunnel.com`
- `auth.onnwee.me` → `c90c06cb-92ed-4653-9d8b-57ad5dc5dd87.cfargotunnel.com`

Remove the accidental records `observatory.onnwee.me.subcult.tv` and `auth.onnwee.me.subcult.tv` if present. They were created by running `cloudflared tunnel route dns` with credentials scoped to the wrong zone.

After updating DNS, confirm that `observatory.onnwee.me` redirects to `auth.onnwee.me` and that `onnwee` can sign in with two-factor authentication.
