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


def test_browser_health_uses_direct_runtime(monkeypatch) -> None:
    calls: dict[str, object] = {}

    class _FakePage:
        def set_default_timeout(self, timeout_ms: int) -> None:
            self.timeout_ms = timeout_ms

        async def goto(self, url: str, wait_until: str, timeout: int):
            calls["url"] = url
            calls["wait_until"] = wait_until
            calls["timeout"] = timeout
            return None

        async def wait_for_timeout(self, timeout_ms: int):
            calls["wait_for_timeout"] = timeout_ms
            return None

        async def evaluate(self, script: str):
            assert "publicMarketplaceVisible" in script
            return {
                "challengeDetected": False,
                "loginRequired": False,
                "publicMarketplaceVisible": True,
                "finalUrl": "https://www.facebook.com/marketplace/",
            }

    class _FakeContextManager:
        async def __aenter__(self):
            return type("Ctx", (), {"pages": [_FakePage()]})(), "chrome", "/tmp/direct-profile"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(browser_profile, "use_direct_marketplace_runtime", lambda: True)
    monkeypatch.setattr(
        browser_profile,
        "open_direct_marketplace_context",
        lambda: _FakeContextManager(),
    )

    health = browser_profile.check_marketplace_browser_health(timeout_ms=1000)

    assert health["status"] == "ready"
    assert health["profile_path"] == "/tmp/direct-profile"
    assert health["browser_family"] == "chrome"
    assert calls["wait_until"] == "commit"
    assert calls["timeout"] == 1000
    assert calls["wait_for_timeout"] == 1000


def test_browser_health_direct_runtime_reports_navigation_timeout_cleanly(monkeypatch) -> None:
    class _FakePage:
        def set_default_timeout(self, timeout_ms: int) -> None:
            self.timeout_ms = timeout_ms

        async def goto(self, url: str, wait_until: str, timeout: int):
            raise RuntimeError(
                "Page.goto: Timeout 5000ms exceeded. Call log: "
                '- navigating to "https://www.facebook.com/marketplace/", '
                'waiting until "domcontentloaded"'
            )

        async def wait_for_timeout(self, timeout_ms: int):
            return None

        async def evaluate(self, script: str):
            return {}

    class _FakeContextManager:
        async def __aenter__(self):
            return type("Ctx", (), {"pages": [_FakePage()]})(), "chrome", "/tmp/direct-profile"

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(browser_profile, "use_direct_marketplace_runtime", lambda: True)
    monkeypatch.setattr(
        browser_profile,
        "open_direct_marketplace_context",
        lambda: _FakeContextManager(),
    )

    health = browser_profile.check_marketplace_browser_health(timeout_ms=5000)

    assert health["status"] == "browser_unavailable"
    assert health["profile_path"] == "/tmp/direct-profile"
    assert "probe timed out during marketplace navigation" in str(health["detail"]).lower()
    assert "launch failed" not in str(health["detail"]).lower()


def test_browser_health_sync_wrapper_works_inside_running_loop(monkeypatch) -> None:
    async def _fake_async_health(*, cdp_url=None, timeout_ms=None):
        return {
            "status": "ready",
            "cdp_url": cdp_url or "http://127.0.0.1:9222",
            "browser_family": "chrome",
            "profile_path": "/tmp/direct-profile",
        }

    monkeypatch.setattr(
        browser_profile,
        "check_marketplace_browser_health_async",
        _fake_async_health,
    )

    async def _call_sync_wrapper():
        return browser_profile.check_marketplace_browser_health(timeout_ms=1000)

    health = asyncio.run(_call_sync_wrapper())

    assert health["status"] == "ready"
    assert health["profile_path"] == "/tmp/direct-profile"
