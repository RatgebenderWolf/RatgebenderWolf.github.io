#!/usr/bin/env python3
"""
Website lokal ansehen.

    python3 tools/serve.py          -> http://localhost:8000

Wie  python3 -m http.server 8000 , aber ohne Browser-Cache: Der Browser
holt CSS und JavaScript bei jedem Neuladen frisch, Aenderungen sind also
sofort sichtbar (sonst braucht es Strg+Shift+R).
"""

import functools
import http.server
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000


class OhneCache(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(
        ("", PORT), functools.partial(OhneCache, directory=ROOT))
    print(f"http://localhost:{PORT}  —  beenden mit Strg+C")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
