#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import launch_marketplace_browser as launcher


DEFAULT_HELPER_HOST = "127.0.0.1"
DEFAULT_HELPER_PORT = 9233


def _helper_host() -> str:
    return str(os.environ.get("MARKETPLACE_BROWSER_HELPER_HOST") or DEFAULT_HELPER_HOST).strip() or DEFAULT_HELPER_HOST


def _helper_port() -> int:
    raw = str(os.environ.get("MARKETPLACE_BROWSER_HELPER_PORT") or "").strip()
    if not raw:
        return DEFAULT_HELPER_PORT
    try:
        parsed = int(raw)
    except ValueError:
        return DEFAULT_HELPER_PORT
    return parsed if parsed > 0 else DEFAULT_HELPER_PORT


def _helper_token() -> str:
    return str(os.environ.get("MARKETPLACE_BROWSER_HELPER_TOKEN") or "").strip()


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Serve a local desktop-session helper so a headless/backend process can "
            "request Facebook Marketplace browser launches on this logged-in desktop."
        )
    )
    parser.add_argument("--host", default=_helper_host(), help="Bind host. Use 127.0.0.1 only.")
    parser.add_argument("--port", type=int, default=_helper_port(), help="Bind port for the helper API.")
    return parser.parse_args()


def _json_response(
    handler: BaseHTTPRequestHandler,
    *,
    status_code: int,
    payload: dict[str, object],
) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    content_length = int(handler.headers.get("Content-Length") or "0")
    if content_length <= 0:
        return {}
    raw_body = handler.rfile.read(content_length)
    if not raw_body:
        return {}
    payload = json.loads(raw_body.decode("utf-8"))
    return payload if isinstance(payload, dict) else {}


def _build_health_payload() -> dict[str, object]:
    display_available = launcher._has_graphical_desktop_session()
    cdp_payload = launcher._wait_for_cdp(launcher.DEFAULT_PORT, timeout_seconds=0.25)
    helper_user = (
        str(os.environ.get("USER") or "").strip()
        or str(os.environ.get("LOGNAME") or "").strip()
        or "unknown"
    )
    if cdp_payload is not None:
        detail = "Marketplace browser is already reachable on the configured remote debugging port."
    elif display_available:
        detail = "Marketplace desktop helper is ready to launch the browser."
    else:
        detail = "No graphical desktop session is available in this helper process."
    return {
        "ok": True,
        "display_available": display_available,
        "cdp_ready": cdp_payload is not None,
        "cdp_url": f"http://127.0.0.1:{launcher.DEFAULT_PORT}",
        "browser_family": "chrome",
        "profile_path": str(launcher._profile_dir("chrome")),
        "helper_user": helper_user,
        "detail": detail,
    }


class MarketplaceBrowserHelperHandler(BaseHTTPRequestHandler):
    server_version = "MarketplaceBrowserHelper/1.0"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        sys.stderr.write(
            "[marketplace_browser_helper] "
            + format % args
            + "\n"
        )

    def _authorize(self) -> bool:
        expected = _helper_token()
        if not expected:
            return True
        provided = str(self.headers.get("X-Marketplace-Helper-Token") or "").strip()
        if provided == expected:
            return True
        _json_response(
            self,
            status_code=403,
            payload={"ok": False, "detail": "Unauthorized marketplace helper request."},
        )
        return False

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/health":
            _json_response(
                self,
                status_code=404,
                payload={"ok": False, "detail": f"Unknown helper path: {self.path}"},
            )
            return
        if not self._authorize():
            return
        _json_response(self, status_code=200, payload=_build_health_payload())

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/launch":
            _json_response(
                self,
                status_code=404,
                payload={"ok": False, "detail": f"Unknown helper path: {self.path}"},
            )
            return
        if not self._authorize():
            return
        try:
            payload = _read_json_body(self)
        except json.JSONDecodeError as exc:
            _json_response(
                self,
                status_code=400,
                payload={"ok": False, "detail": f"Invalid JSON payload: {exc}"},
            )
            return

        if not launcher._has_graphical_desktop_session():
            _json_response(
                self,
                status_code=503,
                payload={
                    "ok": False,
                    "detail": (
                        "marketplace_browser_launch_failed: The desktop helper itself has no "
                        "graphical desktop session. Start it from a GUI login shell."
                    ),
                },
            )
            return

        browser = str(payload.get("browser") or "auto").strip() or "auto"
        url = str(payload.get("url") or launcher.DEFAULT_URL).strip() or launcher.DEFAULT_URL
        try:
            port = int(payload.get("port") or launcher.DEFAULT_PORT)
        except (TypeError, ValueError):
            port = launcher.DEFAULT_PORT
        fresh_profile = bool(payload.get("fresh_profile"))

        exit_code, message, is_error = launcher._launch_browser_locally(
            browser=browser,
            port=port,
            url=url,
            fresh_profile=fresh_profile,
        )
        _json_response(
            self,
            status_code=200 if exit_code == 0 else 500,
            payload={
                "ok": exit_code == 0 and not is_error,
                "result": None if is_error else message,
                "detail": message if is_error else None,
                "cdp_url": f"http://127.0.0.1:{port}",
                "browser_family": "chrome",
                "profile_path": str(launcher._profile_dir("chrome")),
            },
        )


def main() -> int:
    args = _parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MarketplaceBrowserHelperHandler)
    print(
        "Marketplace browser helper listening.\n"
        f"Bind: http://{args.host}:{args.port}\n"
        "Keep this process running in a graphical desktop session so the backend can "
        "request Marketplace browser launches.",
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Marketplace browser helper stopped.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
