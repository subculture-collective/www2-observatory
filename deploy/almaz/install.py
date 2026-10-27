from __future__ import annotations

import datetime
import pathlib
import shutil


PROJECT = pathlib.Path("/opt/server/projects/www2-observatory")
CADDY = pathlib.Path("/opt/server/management/config/caddy")
AUTHELIA = pathlib.Path("/opt/server/management/config/authelia/configuration.yml")
RESTIC = pathlib.Path("/usr/local/sbin/almaz-router-restic-backup.sh")
SYSTEMD = pathlib.Path("/etc/systemd/system")
STAMP = datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def backup(path: pathlib.Path) -> None:
    destination = path.with_name(f"{path.name}.before-observatory-{STAMP}")
    if not destination.exists():
        shutil.copy2(path, destination)


def insert_once(path: pathlib.Path, marker: str, addition: str, sentinel: str) -> None:
    text = path.read_text(encoding="utf-8")
    if sentinel in text:
        return
    if marker not in text:
        raise RuntimeError(f"marker not found in {path}: {marker!r}")
    backup(path)
    path.write_text(text.replace(marker, addition + marker, 1), encoding="utf-8")


def main() -> None:
    site_source = PROJECT / "deploy/almaz/observatory.Caddyfile"
    site_target = CADDY / "sites/observatory.Caddyfile"
    if not site_target.exists() or site_target.read_bytes() != site_source.read_bytes():
        if site_target.exists():
            backup(site_target)
        shutil.copy2(site_source, site_target)

    deadweb = CADDY / "sites/deadweb-relay.Caddyfile"
    deadweb_text = deadweb.read_text(encoding="utf-8")
    if "/data/logs/www2/access.jsonl" not in deadweb_text:
        marker = "http://www2.onnwee.me {\n"
        if marker not in deadweb_text:
            raise RuntimeError(f"www2 site marker not found in {deadweb}")
        backup(deadweb)
        log_block = (
            "    log {\n"
            "        output file /data/logs/www2/access.jsonl {\n"
            "            mode 0640\n"
            "            roll_size 50mb\n"
            "            roll_keep 100\n"
            "            roll_keep_for 720h\n"
            "        }\n"
            "        format json\n"
            "    }\n"
        )
        deadweb.write_text(
            deadweb_text.replace(marker, marker + log_block, 1),
            encoding="utf-8",
        )

    caddyfile = CADDY / "Caddyfile"
    import_line = "import /etc/caddy/sites/observatory.Caddyfile"
    if import_line not in caddyfile.read_text(encoding="utf-8"):
        backup(caddyfile)
        with caddyfile.open("a", encoding="utf-8") as output:
            output.write(f"\n# Private www2 Observatory\n{import_line}\n")

    auth_rules = (
        "    # Observatory authentication portal and exact-user policy\n"
        "    - domain: auth.onnwee.me\n"
        "      policy: bypass\n"
        "    - domain: observatory.onnwee.me\n"
        "      subject: \"user:onnwee\"\n"
        "      policy: two_factor\n"
        "    - domain: observatory.onnwee.me\n"
        "      policy: deny\n\n"
    )
    insert_once(
        AUTHELIA,
        "    # Public project domains — no auth\n",
        auth_rules,
        "domain: observatory.onnwee.me",
    )
    cookie = (
        "    - domain: onnwee.me\n"
        "      authelia_url: https://auth.onnwee.me\n"
    )
    insert_once(
        AUTHELIA,
        "storage:\n",
        cookie + "\n",
        "authelia_url: https://auth.onnwee.me",
    )

    restic_include = (
        "  [[ -e /opt/server/projects/www2-observatory/backups ]] "
        "&& printf '%s\\n' /opt/server/projects/www2-observatory/backups >> \"$list\"\n"
    )
    insert_once(
        RESTIC,
        "}\ndump_optional_postgres()",
        restic_include,
        "printf '%s\\n' /opt/server/projects/www2-observatory/backups",
    )

    for name in ("www2-observatory-backup.service", "www2-observatory-backup.timer"):
        shutil.copy2(PROJECT / "deploy/almaz" / name, SYSTEMD / name)


if __name__ == "__main__":
    main()