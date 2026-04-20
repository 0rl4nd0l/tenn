from __future__ import annotations

import asyncio
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


def test_resolve_marketplace_browser_prefers_supplied_playwright_executable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    browser_path = tmp_path / "playwright-chrome"
    browser_path.write_text("", encoding="utf-8")
    browser_path.chmod(0o755)

    monkeypatch.delenv(runtime.EXECUTABLE_PATH_ENV, raising=False)
    monkeypatch.setattr(runtime.shutil, "which", lambda candidate: None)
    monkeypatch.setattr(
        runtime,
        "_resolve_playwright_browser_path",
        lambda: (_ for _ in ()).throw(AssertionError("sync resolver should not run")),
    )

    family, resolved = runtime.resolve_marketplace_browser(
        playwright_executable_path=str(browser_path),
    )

    assert family == "chrome"
    assert resolved == str(browser_path.resolve())


def test_normalize_runtime_launch_error_reports_profile_in_use() -> None:
    exc = RuntimeError("Failed to create a ProcessSingleton for your profile directory. SingletonLock: File exists")

    normalized = runtime._normalize_runtime_launch_error(
        exc,
        "/home/l4nd0/.tenn/browser_profiles/facebook-marketplace-chrome",
    )

    assert "profile is already in use" in str(normalized).lower()
    assert "facebook-marketplace-chrome" in str(normalized)


def test_open_direct_marketplace_context_fails_fast_when_profile_lock_busy(monkeypatch) -> None:
    class _BusyLock:
        def acquire(self, blocking: bool = True, timeout: float = -1) -> bool:
            return False

        def release(self) -> None:  # pragma: no cover - defensive
            raise AssertionError("release should not be called when acquire fails")

    monkeypatch.setattr(runtime, "_DIRECT_RUNTIME_PROFILE_LOCK", _BusyLock())

    async def _run() -> str:
        try:
            async with runtime.open_direct_marketplace_context():
                raise AssertionError("context should not open when lock is busy")
        except RuntimeError as exc:
            return str(exc)

    message = asyncio.run(_run())

    assert "profile is already in use" in message.lower()


def test_open_direct_marketplace_context_uses_async_playwright_executable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    browser_path = tmp_path / "playwright-chrome"
    browser_path.write_text("", encoding="utf-8")
    browser_path.chmod(0o755)

    monkeypatch.delenv(runtime.EXECUTABLE_PATH_ENV, raising=False)
    monkeypatch.setattr(runtime.shutil, "which", lambda candidate: None)
    monkeypatch.setattr(
        runtime,
        "_resolve_playwright_browser_path",
        lambda: (_ for _ in ()).throw(AssertionError("sync resolver should not run")),
    )

    launch_kwargs: dict[str, object] = {}

    class _FakeContext:
        pages: list[object] = []

        async def close(self) -> None:
            return None

    class _FakeChromium:
        executable_path = str(browser_path)

        async def launch_persistent_context(self, **kwargs):
            launch_kwargs.update(kwargs)
            return _FakeContext()

    class _FakePlaywright:
        def __init__(self) -> None:
            self.chromium = _FakeChromium()

    class _FakeAsyncPlaywright:
        async def __aenter__(self) -> _FakePlaywright:
            return _FakePlaywright()

        async def __aexit__(self, exc_type, exc, tb) -> None:
            return None

    import playwright.async_api as async_api

    monkeypatch.setattr(async_api, "async_playwright", lambda: _FakeAsyncPlaywright())

    async def _run() -> tuple[str, str]:
        async with runtime.open_direct_marketplace_context() as (_context, family, profile_path):
            return family, profile_path

    family, profile_path = asyncio.run(_run())

    assert family == "chrome"
    assert profile_path.endswith("facebook-marketplace-chrome")
    assert launch_kwargs["executable_path"] == str(browser_path.resolve())
