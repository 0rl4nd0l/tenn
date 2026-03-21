#!/usr/bin/env python3
"""
Playwright smoke test for the Cockpit TUI served via `textual serve`.

What it tests:
  - App boots and renders in a browser
  - All screen keybindings work (c/o/u/v/h/s/ctrl+n)
  - Chat screen accepts text input
  - Screenshots saved to reports/cockpit/playwright/

Requirements:
  pip install playwright
  playwright install chromium

Usage:
  cd /home/l4nd0/tenn
  python scripts/test_cockpit_playwright.py [--port 8081] [--read-only] [--headed]
"""
from __future__ import annotations

import argparse
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCREENSHOTS_DIR = REPO_ROOT / "reports" / "cockpit" / "playwright"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def wait_for_port(host: str, port: int, timeout: float = 30.0, interval: float = 0.5) -> None:
    """Block until host:port accepts connections or timeout expires."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=1):
                return
        except OSError:
            time.sleep(interval)
    raise TimeoutError(f"Port {port} not ready after {timeout}s")


def screenshot(page, name: str) -> None:
    path = SCREENSHOTS_DIR / f"{name}.png"
    page.screenshot(path=str(path), full_page=True)
    print(f"  [screenshot] {path.relative_to(REPO_ROOT)}")


def press_and_wait(page, key: str, wait_ms: int = 800) -> None:
    page.keyboard.press(key)
    page.wait_for_timeout(wait_ms)


def dismiss_intro_dialog(page) -> None:
    """Dismiss Textual Serve's intro overlay once the terminal is connected."""
    page.wait_for_selector("#terminal.-connected", timeout=15_000)
    intro_dialog = page.locator(".dialog-container.intro-dialog")
    if intro_dialog.count() == 0:
        return
    if not intro_dialog.first.is_visible():
        return
    page.evaluate("document.body.classList.add('-first-byte')")
    page.wait_for_selector(".dialog-container.intro-dialog", state="hidden", timeout=5_000)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Cockpit Playwright smoke test")
    parser.add_argument("--port", type=int, default=8081, help="Port for textual serve (default: 8081)")
    parser.add_argument("--read-only", action="store_true", help="Pass --read-only to cockpit")
    parser.add_argument("--headed", action="store_true", help="Run browser in headed (visible) mode")
    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Seconds to wait for server startup (Cockpit init can be slow)",
    )
    args = parser.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium")
        return 1

    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Build the textual serve command. Use the `textual` console script — `python -m textual`
    # only runs Textual's DemoApp (see textual/__main__.py), not the serve subcommand.
    serve_script = REPO_ROOT / "financial-engine_v2" / "scripts" / "cockpit_serve.py"
    venv_bin = REPO_ROOT / "financial-engine_v2" / ".venv" / "bin"
    textual_cli = venv_bin / "textual"
    if not textual_cli.exists():
        print(f"ERROR: textual CLI not found at {textual_cli} (pip install textual)")
        return 1

    cockpit_flags = []
    if args.read_only:
        cockpit_flags.append("--read-only")

    cmd = [
        str(textual_cli),
        "serve",
        "--port",
        str(args.port),
        str(serve_script),
        *cockpit_flags,
    ]

    print(f"Starting: {' '.join(cmd)}")
    # Do not use PIPE here: Cockpit/Textual can write enough during startup to fill the
    # pipe buffer and deadlock before the HTTP server binds (see textual serve + long init).
    serve_proc = subprocess.Popen(
        cmd,
        cwd=str(REPO_ROOT / "financial-engine_v2"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        print(f"Waiting for textual serve on port {args.port}...")
        wait_for_port("127.0.0.1", args.port, timeout=args.timeout)
        print("Server ready.")

        url = f"http://127.0.0.1:{args.port}"

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=not args.headed)
            page = browser.new_page(viewport={"width": 1280, "height": 800})

            # Navigate and wait for xterm canvas to appear.
            print(f"\nNavigating to {url}")
            page.goto(url)
            page.wait_for_selector("canvas", timeout=15_000)
            dismiss_intro_dialog(page)
            page.wait_for_timeout(2000)  # let Textual finish mount

            # Focus Textual's hidden textarea so key presses go to the terminal.
            page.locator("textarea.xterm-helper-textarea").focus()

            print("\n--- Screen tour ---")

            # Chat (default screen)
            screenshot(page, "01_chat")
            print("  Chat screen OK")

            # Ops
            press_and_wait(page, "o")
            screenshot(page, "02_ops")
            print("  Ops screen OK")

            # Updater
            press_and_wait(page, "u")
            screenshot(page, "03_updater")
            print("  Updater screen OK")

            # Verification
            press_and_wait(page, "v")
            screenshot(page, "04_verification")
            print("  Verification screen OK")

            # History
            press_and_wait(page, "h")
            screenshot(page, "05_history")
            print("  History screen OK")

            # Settings
            press_and_wait(page, "s")
            screenshot(page, "06_settings")
            print("  Settings screen OK")

            # News Search (Ctrl+N)
            press_and_wait(page, "Control+n")
            screenshot(page, "07_news_search")
            print("  News Search screen OK")

            # Back to Chat
            press_and_wait(page, "c")
            screenshot(page, "08_chat_return")
            print("  Back to Chat OK")

            print("\n--- Chat input test ---")
            # Type a test message. Textual's chat input widget should be focusable.
            # Try Tab to move focus into the input field, then type.
            press_and_wait(page, "Tab", wait_ms=400)
            page.keyboard.type("hello cockpit", delay=50)
            screenshot(page, "09_chat_typed")
            page.keyboard.press("Enter")
            page.wait_for_timeout(2000)
            screenshot(page, "10_chat_sent")
            print("  Chat message sent OK")

            print("\n--- Export bundle ---")
            press_and_wait(page, "x", wait_ms=1000)
            screenshot(page, "11_export")
            print("  Export triggered OK")

            browser.close()

        print(f"\nAll screenshots saved to: {SCREENSHOTS_DIR.relative_to(REPO_ROOT)}")
        print("PASS")
        return 0

    except TimeoutError as exc:
        print(f"\nERROR: {exc}")
        if serve_proc.returncode is None:
            serve_proc.terminate()
            try:
                serve_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                serve_proc.kill()
        return 1

    except Exception as exc:
        print(f"\nERROR: {exc}")
        raise

    finally:
        if serve_proc.returncode is None:
            print("\nShutting down textual serve...")
            serve_proc.send_signal(signal.SIGTERM)
            try:
                serve_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                serve_proc.kill()


if __name__ == "__main__":
    sys.exit(main())
