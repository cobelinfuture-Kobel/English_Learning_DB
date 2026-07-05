from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.r2_local import HOST, pack

PORT = 8781


class H(BaseHTTPRequestHandler):
    def js(self, value):
        body = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/pack":
            query = parse_qs(parsed.query)
            limit = int(query.get("limit", ["10"])[0])
            self.js(pack(limit=limit))
            return
        if parsed.path == "/api/status":
            self.js({"status": "ok", "host": HOST})
            return
        self.send_error(404)


def run(host=HOST, port=PORT):
    if host != HOST:
        raise ValueError("host must be 127.0.0.1")
    ThreadingHTTPServer((host, port), H).serve_forever()


if __name__ == "__main__":
    run()
