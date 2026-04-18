#!/usr/bin/env python3
"""Serve the repo root and proxy /api/* to the local Tenn backend.

This is for interactive docs pages that need backend-authoritative JSON while still
being opened from a simple static server origin.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


REPO_ROOT = Path(__file__).resolve().parent.parent
HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


class RepoDocsProxyHandler(SimpleHTTPRequestHandler):
    backend_base: str = "http://127.0.0.1:8000"

    def do_GET(self) -> None:  # noqa: N802 - stdlib signature
        if self.path.startswith("/api/"):
            self._proxy_request()
            return
        super().do_GET()

    def do_HEAD(self) -> None:  # noqa: N802 - stdlib signature
        if self.path.startswith("/api/"):
            self._proxy_request(head_only=True)
            return
        super().do_HEAD()

    def log_message(self, format: str, *args) -> None:
        super().log_message(format, *args)

    def _copy_request_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        for key, value in self.headers.items():
            lower = key.lower()
            if lower in HOP_BY_HOP_HEADERS or lower == "host":
                continue
            headers[key] = value
        return headers

    def _send_backend_response(self, status: int, headers: dict[str, str], body: bytes, *, head_only: bool) -> None:
        self.send_response(status)
        for key, value in headers.items():
            lower = key.lower()
            if lower in HOP_BY_HOP_HEADERS:
                continue
            self.send_header(key, value)
        self.end_headers()
        if not head_only and body:
            self.wfile.write(body)

    def _proxy_request(self, *, head_only: bool = False) -> None:
        target = f"{self.backend_base}{self.path}"
        request = Request(
            target,
            method=self.command,
            headers=self._copy_request_headers(),
        )

        try:
            with urlopen(request, timeout=60) as response:
                body = b"" if head_only else response.read()
                headers = dict(response.headers.items())
                self._send_backend_response(response.status, headers, body, head_only=head_only)
        except HTTPError as exc:
            body = b"" if head_only else exc.read()
            headers = dict(exc.headers.items())
            self._send_backend_response(exc.code, headers, body, head_only=head_only)
        except URLError as exc:
            message = f"Upstream backend unavailable: {exc.reason}\n".encode("utf-8")
            self.send_response(502, "Bad Gateway")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            if not head_only:
                self.wfile.write(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8766, help="Port to listen on (default: 8766)")
    parser.add_argument(
        "--backend-base",
        default="http://127.0.0.1:8000",
        help="Backend base URL for proxied /api requests (default: http://127.0.0.1:8000)",
    )
    parser.add_argument(
        "--directory",
        default=str(REPO_ROOT),
        help=f"Directory to serve statically (default: {REPO_ROOT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    RepoDocsProxyHandler.backend_base = args.backend_base.rstrip("/")
    handler_cls = partial(
        RepoDocsProxyHandler,
        directory=args.directory,
    )

    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler_cls)
    print(f"Serving {args.directory} on http://127.0.0.1:{args.port}")
    print(f"Proxying /api/* to {RepoDocsProxyHandler.backend_base}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
