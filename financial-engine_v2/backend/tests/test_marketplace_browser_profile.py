from __future__ import annotations

import asyncio

import app.services.marketplace_browser_profile as browser_profile


def test_browser_health_reports_helper_ready_when_backend_has_no_display(monkeypatch) -> None:
    monkeypatch.setattr(browser_profile, "_fetch_cdp_version", lambda *args, **kwargs: None)
    monkeypatch.setattr(browser_profile, "_has_graphical_desktop_session", lambda: False)
    monkeypatch.setattr(
        browser_profile,
        "_fetch_helper_health",
        lambda *args, **kwargs: {
            "ok": True,
            "display_available": True,
            "browser_family": "chrome",
            "profile_path": "/home/l4nd0/.tenn/browser_profiles/facebook-marketplace-chrome",
            "detail": "Marketplace desktop helper is ready to launch the browser.",
        },
    )

    health = browser_profile.check_marketplace_browser_health()

    assert health["status"] == "browser_not_running"
    assert health["profile_path"] == "/home/l4nd0/.tenn/browser_profiles/facebook-marketplace-chrome"
    assert "desktop helper" in str(health["detail"]).lower()


def test_browser_health_keeps_desktop_session_missing_without_helper(monkeypatch) -> None:
    monkeypatch.setattr(browser_profile, "_fetch_cdp_version", lambda *args, **kwargs: None)
    monkeypatch.setattr(browser_profile, "_has_graphical_desktop_session", lambda: False)
    monkeypatch.setattr(browser_profile, "_fetch_helper_health", lambda *args, **kwargs: None)

    health = browser_profile.check_marketplace_browser_health()

    assert health["status"] == "desktop_session_missing"
    assert "no graphical desktop session" in str(health["detail"]).lower()


def test_browser_health_fails_fast_when_cdp_attach_stalls(monkeypatch) -> None:
    import playwright.async_api as playwright_async_api

    class _FakeChromium:
        async def connect_over_cdp(self, cdp_url: str):
            await asyncio.sleep(60)

    class _FakePlaywrightContext:
        def __init__(self) -> None:
            self.chromium = _FakeChromium()

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(
        browser_profile,
        "_fetch_cdp_version",
        lambda *args, **kwargs: {
            "Browser": "Chrome/146.0.7680.153",
            "User-Agent": "Mozilla/5.0 HeadlessChrome/146.0.0.0 Safari/537.36",
        },
    )
    monkeypatch.setattr(browser_profile, "_probe_timeout_seconds", lambda *args, **kwargs: 0.01)
    monkeypatch.setattr(
        playwright_async_api,
        "async_playwright",
        lambda: _FakePlaywrightContext(),
    )

    health = browser_profile.check_marketplace_browser_health(timeout_ms=1)

    assert health["status"] == "browser_unavailable"
    assert "timed out during cdp attach" in str(health["detail"]).lower()
    assert "headless mode" in str(health["detail"]).lower()
