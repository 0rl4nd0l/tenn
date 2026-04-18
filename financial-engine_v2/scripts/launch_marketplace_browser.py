#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_URL = "https://www.facebook.com/marketplace/"
DEFAULT_PORT = 9222
DEFAULT_PROFILE_ROOT = Path.home() / ".tenn" / "browser_profiles"
DEFAULT_HELPER_URL = "http://127.0.0.1:9233"

_BROWSER_CANDIDATES: dict[str, tuple[str, ...]] = {
    "brave": ("brave-browser", "brave"),
    "chrome": (
        "google-chrome",
        "google-chrome-stable",
        "chromium-browser",
        "chromium",
    ),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Launch a dedicated Brave/Chrome profile with remote debugging enabled "
            "for Facebook Marketplace capture."
        )
    )
    parser.add_argument("--url", default=DEFAULT_URL, help="Page to open after launch.")
    parser.add_argument(
        "--browser",
        default="auto",
        choices=("auto", "brave", "chrome"),
        help="Browser family to prefer.",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help="Remote debugging port to expose.",
    )
    parser.add_argument(
        "--fresh-profile",
        action="store_true",
        help="Delete the dedicated Marketplace browser profile before launch.",
    )
    return parser.parse_args()


def _resolve_browser(browser: str) -> tuple[str, str]:
    families = ("brave", "chrome") if browser == "auto" else (browser,)
    for family in families:
        for candidate in _BROWSER_CANDIDATES[family]:
            resolved = shutil.which(candidate)
            if resolved:
                return family, resolved
    searched = ", ".join(
        candidate
        for family in families
        for candidate in _BROWSER_CANDIDATES[family]
    )
    raise RuntimeError(
        "No supported browser binary was found. "
        f"Searched: {searched}."
    )


def _profile_dir(family: str) -> Path:
    return DEFAULT_PROFILE_ROOT / f"facebook-marketplace-{family}"


def _helper_base_url() -> str:
    return str(os.environ.get("MARKETPLACE_BROWSER_HELPER_URL") or DEFAULT_HELPER_URL).strip().rstrip("/")


def _helper_headers(*, include_content_type: bool = False) -> dict[str, str]:
    headers: dict[str, str] = {}
    token = str(os.environ.get("MARKETPLACE_BROWSER_HELPER_TOKEN") or "").strip()
    if token:
        headers["X-Marketplace-Helper-Token"] = token
    if include_content_type:
        headers["Content-Type"] = "application/json"
    return headers


def _helper_request(
    *,
    method: str,
    path: str,
    payload: dict[str, object] | None = None,
    timeout_seconds: float = 3.0,
) -> dict[str, object] | None:
    base_url = _helper_base_url()
    if not base_url:
        return None
    body = (
        json.dumps(payload).encode("utf-8")
        if payload is not None
        else None
    )
    request = Request(
        f"{base_url}{path}",
        data=body,
        headers=_helper_headers(include_content_type=payload is not None),
        method=method,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8"))
        except Exception:
            return {"ok": False, "detail": f"Desktop helper request failed with HTTP {exc.code}."}
        if isinstance(payload, dict):
            payload.setdefault("ok", False)
            return payload
        return {"ok": False, "detail": f"Desktop helper request failed with HTTP {exc.code}."}
    except (OSError, URLError, ValueError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _wait_for_cdp(port: int, timeout_seconds: float = 15.0) -> dict[str, object] | None:
    deadline = time.time() + timeout_seconds
    url = f"http://127.0.0.1:{port}/json/version"
    while time.time() < deadline:
        try:
            with urlopen(url, timeout=1.5) as response:  # noqa: S310
                payload = json.loads(response.read().decode("utf-8"))
            if isinstance(payload, dict) and payload.get("Browser"):
                return payload
        except (OSError, URLError, ValueError, json.JSONDecodeError):
            time.sleep(0.5)
    return None


def _has_graphical_desktop_session() -> bool:
    if not sys.platform.startswith("linux"):
        return True
    return bool(
        str(os.environ.get("DISPLAY") or "").strip()
        or str(os.environ.get("WAYLAND_DISPLAY") or "").strip()
    )


def _already_ready_message(port: int, payload: dict[str, object]) -> str:
    browser_name = str(payload.get("Browser") or "Chrome/Brave").strip()
    return (
        "Marketplace browser already ready.\n"
        f"Browser: {browser_name}\n"
        f"Debugging URL: http://127.0.0.1:{port}\n"
        "Paste the listing URL into Cockpit again."
    )


def _launch_browser_locally(
    *,
    browser: str,
    port: int,
    url: str,
    fresh_profile: bool,
) -> tuple[int, str, bool]:
    existing_payload = _wait_for_cdp(port, timeout_seconds=0.5)
    if existing_payload is not None:
        return 0, _already_ready_message(port, existing_payload), False

    try:
        family, browser_binary = _resolve_browser(browser)
    except RuntimeError as exc:
        return 1, f"marketplace_browser_launch_failed: {exc}", True

    profile_dir = _profile_dir(family)
    if fresh_profile and profile_dir.exists():
        shutil.rmtree(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)

    command = [
        browser_binary,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={profile_dir}",
        "--no-first-run",
        "--no-default-browser-check",
        "--new-window",
        str(url or DEFAULT_URL),
    ]

    try:
        subprocess.Popen(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
    except OSError as exc:
        return (
            1,
            f"marketplace_browser_launch_failed: Could not start {browser_binary}: {exc}",
            True,
        )

    payload = _wait_for_cdp(port)
    if payload is None:
        return (
            1,
            "marketplace_browser_launch_failed: Browser started, but the remote "
            f"debugging endpoint on port {port} did not become ready.",
            True,
        )

    browser_name = str(payload.get("Browser") or browser_binary).strip()
    return (
        0,
        "Marketplace browser ready.\n"
        f"Browser: {browser_name}\n"
        f"Debugging URL: http://127.0.0.1:{port}\n"
        f"Profile: {profile_dir}\n"
        "Log into Facebook in that window if needed, then paste the listing URL into Cockpit again.",
        False,
    )


def _launch_with_helper(
    *,
    browser: str,
    port: int,
    url: str,
    fresh_profile: bool,
) -> tuple[int, str, bool] | None:
    helper_result = _helper_request(
        method="POST",
        path="/launch",
        payload={
            "browser": browser,
            "port": port,
            "url": url,
            "fresh_profile": fresh_profile,
        },
        timeout_seconds=20.0,
    )
    if helper_result is None:
        return None

    detail = str(helper_result.get("result") or helper_result.get("detail") or "").strip()
    if helper_result.get("ok"):
        return 0, detail or "Marketplace browser ready via desktop helper.", False
    return 1, detail or "marketplace_browser_launch_failed: Desktop helper launch failed.", True


def main() -> int:
    args = _parse_args()

    existing_payload = _wait_for_cdp(args.port, timeout_seconds=0.5)
    if existing_payload is not None:
        print(_already_ready_message(args.port, existing_payload))
        return 0

    if not _has_graphical_desktop_session():
        helper_result = _launch_with_helper(
            browser=args.browser,
            port=args.port,
            url=str(args.url or DEFAULT_URL),
            fresh_profile=bool(args.fresh_profile),
        )
        if helper_result is not None:
            exit_code, message, is_error = helper_result
            print(message, file=sys.stderr if is_error else sys.stdout)
            return exit_code
        print(
            "marketplace_browser_launch_failed: No graphical desktop session is available "
            "in this shell. Chrome/Brave cannot start because $DISPLAY/$WAYLAND_DISPLAY "
            "are unset. Launch the browser from a graphical desktop login on the same "
            "machine, start marketplace_browser_helper.py there, or enable "
            "--remote-debugging-port=9222 manually, then retry the Marketplace capture.",
            file=sys.stderr,
        )
        return 1

    exit_code, message, is_error = _launch_browser_locally(
        browser=args.browser,
        port=args.port,
        url=str(args.url or DEFAULT_URL),
        fresh_profile=bool(args.fresh_profile),
    )
    print(message, file=sys.stderr if is_error else sys.stdout)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
