from __future__ import annotations

import argparse
from dataclasses import replace
import signal
import threading

from .config import Config
from .db import connect
from .ingest import Ingestor
from .privacy import load_or_create_key
from .web import ObservatoryServer


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="www2-observatory")
    p.add_argument("--port", type=int, default=None, help="Port to listen on")
    p.add_argument("--bind", type=str, default=None, help="Address to bind to")
    sub = p.add_subparsers(dest="cmd", required=False)
    run_parser = sub.add_parser("run")
    run_parser.add_argument("--port", type=int, default=None, help="Port to listen on")
    run_parser.add_argument("--bind", type=str, default=None, help="Address to bind to")
    sub.add_parser("ingest-once")
    args = p.parse_args(argv)

    cfg = Config()
    port = getattr(args, "port", None)
    bind = getattr(args, "bind", None)
    if port is not None:
        cfg = replace(cfg, port=port)
    if bind is not None:
        cfg = replace(cfg, bind=bind)

    connect(cfg.db_path).close()
    key = load_or_create_key(cfg.key_file)
    ing = Ingestor(cfg, key)

    if args.cmd == "ingest-once":
        print(ing.ingest_once())
        return

    t = threading.Thread(target=ing.run_forever, name="ingest", daemon=True)
    t.start()
    server = ObservatoryServer((cfg.bind, cfg.port), cfg)

    def stop(*_):
        ing.stop()
        server.shutdown()
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)
    print(f"observatory listening on http://{cfg.bind}:{cfg.port}")
    try:
        server.serve_forever(poll_interval=0.5)
    finally:
        ing.stop()
        server.server_close()
        t.join(timeout=2)


if __name__ == "__main__":
    main()
