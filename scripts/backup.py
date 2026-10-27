from __future__ import annotations

import argparse
import shutil
import re
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a verified Observatory snapshot")
    parser.add_argument("--state", type=Path, default=Path("state"))
    parser.add_argument("--output", type=Path, default=Path("backups"))
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = args.output / stamp
    destination.mkdir(parents=True, exist_ok=False)

    source_db = args.state / "observatory.sqlite3"
    key = args.state / "pseudonym.key"
    if not source_db.is_file() or not key.is_file():
        raise FileNotFoundError("observatory database and pseudonym key must both exist")
    backup_db = destination / "observatory.sqlite3"
    with sqlite3.connect(source_db) as source, sqlite3.connect(backup_db) as backup:
        source.backup(backup)
        result = backup.execute("PRAGMA integrity_check").fetchone()
        if not result or result[0] != "ok":
            raise RuntimeError(f"backup integrity check failed: {result}")

    shutil.copy2(key, destination / key.name)
    os.chmod(destination / key.name, 0o600)
    (destination / "VERIFIED").write_text(f"created={stamp}\nintegrity=ok\n", encoding="utf-8")
    print(destination)

    snapshots = sorted(path for path in args.output.iterdir()
                       if path.is_dir() and not path.is_symlink()
                       and re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", path.name)
                       and (path / "VERIFIED").is_file()
                       and (path / "observatory.sqlite3").is_file()
                       and (path / "pseudonym.key").is_file())
    for expired in snapshots[:-max(args.keep, 1)]:
        shutil.rmtree(expired)


if __name__ == "__main__":
    main()