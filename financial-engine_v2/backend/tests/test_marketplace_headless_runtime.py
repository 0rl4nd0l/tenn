from __future__ import annotations

from pathlib import Path

import app.services.marketplace_headless_runtime as runtime


def test_resolve_marketplace_browser_prefers_explicit_executable(monkeypatch, tmp_path: Path) -> None:
    browser_path = tmp_path / "chrome"
    browser_path.write_text("", encoding="utf-8")
    browser_path.chmod(0o755)

    monkeypatch.setenv(runtime.EXECUTABLE_PATH_ENV, str(browser_path))

    family, resolved = runtime.resolve_marketplace_browser()

    assert family == "chrome"
    assert resolved == str(browser_path.resolve())


def test_resolve_marketplace_browser_falls_back_to_playwright(monkeypatch) -> None:
    monkeypatch.delenv(runtime.EXECUTABLE_PATH_ENV, raising=False)
    monkeypatch.setattr(runtime.shutil, "which", lambda candidate: None)
    monkeypatch.setattr(
        runtime,
        "_resolve_playwright_browser_path",
        lambda: "/root/.cache/ms-playwright/chromium-1234/chrome-linux/chrome",
    )

    family, resolved = runtime.resolve_marketplace_browser()

    assert family == "chrome"
    assert resolved == "/root/.cache/ms-playwright/chromium-1234/chrome-linux/chrome"
