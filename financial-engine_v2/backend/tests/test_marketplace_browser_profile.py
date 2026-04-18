from __future__ import annotations

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
