"""HTTP server: JSON API plus static frontend files."""

import json
import logging
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import unquote, urlsplit

from .config import load
from .tracker import Tracker

log = logging.getLogger(__name__)

STATIC_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static"))

CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".json": "application/json",
    ".ico": "image/x-icon",
}


def make_handler(tracker):
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def do_GET(self):
            path = unquote(urlsplit(self.path).path)
            if path == "/api/aircraft":
                self._send_json(tracker.snapshot())
            else:
                self._send_static(path)

        def _send_json(self, obj):
            body = json.dumps(obj).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_static(self, path):
            if path == "/":
                path = "/index.html"
            # Resolve safely inside STATIC_DIR; reject traversal.
            full = os.path.normpath(
                os.path.join(STATIC_DIR, path.lstrip("/")))
            if os.path.commonpath([STATIC_DIR, full]) != STATIC_DIR:
                self._send_error(403, "Forbidden")
                return
            if not os.path.isfile(full):
                self._send_error(404, "Not Found")
                return
            ext = os.path.splitext(full)[1].lower()
            ctype = CONTENT_TYPES.get(ext, "application/octet-stream")
            with open(full, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_error(self, code, message):
            body = message.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, fmt, *args):
            log.debug("%s %s", self.address_string(), fmt % args)

    return Handler


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    config = load()
    tracker = Tracker(config)
    tracker.start()
    server = ThreadingHTTPServer(("", config.port), make_handler(tracker))
    log.info("overhead tracker serving at http://0.0.0.0:%d/ "
             "(source=%s, station=%.4f,%.4f, radius=%.0f km)",
             config.port, getattr(tracker.source, "name", "unknown"),
             config.lat, config.lon, config.radius_km)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("shutting down")
    finally:
        tracker.stop()
        server.server_close()


if __name__ == "__main__":
    main()
