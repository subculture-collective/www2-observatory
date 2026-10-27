import gzip
import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from observatory.config import Config
from observatory.ingest import Ingestor


def event(ts: float, host: str = "www2.onnwee.me", path: str = "/") -> bytes:
    return (json.dumps({
        "ts": ts,
        "request": {
            "host": host,
            "remote_ip": "203.0.113.4",
            "method": "GET",
            "uri": path,
            "headers": {"User-Agent": ["test"]},
        },
        "status": 200,
    }, separators=(",", ":")) + "\n").encode()


class IngestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.log = self.root / "access.jsonl"
        self.db = self.root / "state.sqlite3"
        self.cfg = replace(
            Config(),
            caddy_log=str(self.log),
            relay_log="",
            db_path=str(self.db),
            allowed_hosts="www2.onnwee.me",
        )
        self.ingestor = Ingestor(self.cfg, b"x" * 32)

    def tearDown(self):
        self.temp.cleanup()

    def rows(self):
        with sqlite3.connect(self.db) as conn:
            return conn.execute("SELECT ts, host, path FROM access_events ORDER BY ts").fetchall()

    def test_rejects_other_and_missing_hosts(self):
        self.log.write_bytes(event(1) + event(2, "other.example") + event(3, ""))
        self.assertEqual(self.ingestor.ingest_once()["access"], 1)
        self.assertEqual(self.rows(), [(1.0, "www2.onnwee.me", "/")])

    def test_rotation_restart_and_duplicate_suppression(self):
        self.log.write_bytes(event(1, path="/one"))
        self.assertEqual(self.ingestor.ingest_once()["access"], 1)
        rotated = self.root / "access-2026-09-21T10-00-00.000.jsonl"
        self.log.rename(rotated)
        self.log.write_bytes(event(2, path="/two"))
        os.utime(rotated, ns=(1, 1))
        self.assertEqual(self.ingestor.ingest_once()["access"], 1)

        compressed = self.root / "access-2026-09-21T10-00-00.000.jsonl.gz"
        with gzip.open(compressed, "wb") as output:
            output.write(rotated.read_bytes())
        rotated.unlink()
        restarted = Ingestor(self.cfg, b"x" * 32)
        self.assertEqual(restarted.ingest_once()["access"], 0)
        self.assertEqual([row[2] for row in self.rows()], ["/one", "/two"])

    def test_partial_line_waits_for_completion(self):
        complete = event(1)
        self.log.write_bytes(complete[:-1])
        self.assertEqual(self.ingestor.ingest_once()["access"], 0)
        with self.log.open("ab") as output:
            output.write(b"\n")
        self.assertEqual(self.ingestor.ingest_once()["access"], 1)

    def test_copytruncate_and_legitimate_repeated_requests(self):
        self.log.write_bytes(event(1, path="/same"))
        self.assertEqual(self.ingestor.ingest_once()["access"], 1)
        self.log.write_bytes(b"")
        self.assertEqual(self.ingestor.ingest_once()["access"], 0)
        self.log.write_bytes(event(2, path="/same"))
        self.assertEqual(self.ingestor.ingest_once()["access"], 1)
        self.assertEqual(len(self.rows()), 2)


if __name__ == "__main__":
    unittest.main()