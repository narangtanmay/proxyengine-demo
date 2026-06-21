#!/usr/bin/env python3
"""
Start the compensation dashboard on localhost.

Usage (from Implementation folder):
    python start_portal.py

Then open the URL printed in Chrome or Safari.
"""

from __future__ import annotations

import http.server
import socket
import socketserver
import subprocess
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUTS = ROOT / "outputs"
PORT = 8888


def port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def pick_port() -> int:
    for p in (8888, 8889, 8090, 5001, 7000):
        if port_available(p):
            return p
    raise RuntimeError("No free port found. Close other local servers and retry.")


def main():
    print("Building dashboard...")
    subprocess.run([sys.executable, str(ROOT / "build_portal.py")], cwd=ROOT, check=True)

    if not (OUTPUTS / "index.html").exists():
        print("ERROR: Portal not built. Run python run_pipeline.py first.")
        sys.exit(1)

    port = pick_port()
    url = f"http://127.0.0.1:{port}/"

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(OUTPUTS), **kwargs)

        def log_message(self, fmt, *args):
            if args and "200" in str(args[1]):
                print(f"  {args[0]}")

    print(f"\n{'=' * 52}")
    print(f"  DASHBOARD URL:  {url}")
    print(f"  (Use Chrome or Safari — not Cursor preview)")
    print(f"  Press Ctrl+C to stop")
    print(f"{'=' * 52}\n")

    webbrowser.open(url)

    with socketserver.TCPServer(("127.0.0.1", port), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
