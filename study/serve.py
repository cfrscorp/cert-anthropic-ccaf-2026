#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Serve the CCAF study app locally.

Runs a tiny standard-library HTTP server rooted at this ``study/`` directory so
the browser can ``fetch()`` the JSON data files (which it cannot do from a raw
``file://`` page), then opens the app at ``/web/``. Stdlib only — no third-party
dependencies — so ``uv run study/serve.py`` provisions and runs it directly.

Prefer a downloaded single binary instead? Any static file server works, e.g.:
    caddy file-server --root . --listen :8000     # then open /web/
    static-web-server -d . -p 8000
    miniserve . -p 8000
"""

from __future__ import annotations

import argparse
import contextlib
import functools
import http.server
import socket
import sys
import threading
import webbrowser
from pathlib import Path

__version__ = "1.0.0"

STUDY_ROOT = Path(__file__).resolve().parent


def _find_open_port(preferred: int) -> int:
    """Return ``preferred`` if free, else an OS-assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="serve.py",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Serve the CCAF study app on http://localhost and open it in your browser.",
        epilog=(
            "Examples:\n"
            "  # Start the app (auto-opens the browser at /web/):\n"
            "  uv run study/serve.py\n\n"
            "  # Use a specific port:\n"
            "  uv run study/serve.py --port 8123\n\n"
            "  # Start the server but do not open a browser (e.g. headless):\n"
            "  uv run study/serve.py --no-browser\n\n"
            "  # Print the version:\n"
            "  uv run study/serve.py --version\n"
        ),
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Preferred port (default: 8000; falls back to a free port if taken).",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host/interface to bind (default: 127.0.0.1, i.e. local only).",
    )
    parser.add_argument(
        "--no-browser", action="store_true",
        help="Do not automatically open the browser.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    port = _find_open_port(args.port)
    url = f"http://{args.host}:{port}/web/"

    handler = functools.partial(
        http.server.SimpleHTTPRequestHandler, directory=str(STUDY_ROOT)
    )
    # Suppress the default per-request logging noise; keep it quiet and friendly.
    handler.log_message = lambda *a, **k: None  # type: ignore[assignment]

    with http.server.ThreadingHTTPServer((args.host, port), handler) as httpd:
        print(f"CCAF study app serving {STUDY_ROOT}")
        print(f"  → {url}")
        print("Press Ctrl+C to stop.")
        if not args.no_browser:
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        with contextlib.suppress(KeyboardInterrupt):
            httpd.serve_forever()
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
