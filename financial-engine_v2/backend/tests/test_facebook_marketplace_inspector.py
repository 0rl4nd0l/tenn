from __future__ import annotations

import app.services.facebook_marketplace_inspector as marketplace


def test_browser_unavailable_detail_mentions_headless_linux_shell(monkeypatch) -> None:
    monkeypatch.setattr(marketplace.sys, "platform", "linux")
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.delenv("WAYLAND_DISPLAY", raising=False)

    detail = marketplace._browser_unavailable_detail("http://127.0.0.1:9222")

    assert "Could not connect to a local Brave/Chrome debugging session." in detail
    assert "no X/Wayland desktop session" in detail
    assert "--remote-debugging-port=9222" in detail
    assert "logged into Facebook" not in detail


def test_listing_evaluation_no_longer_reports_login_state() -> None:
    assert "login_required" not in marketplace._MARKETPLACE_LISTING_EVALUATION_SCRIPT
    assert "loginPromptVisible" not in marketplace._MARKETPLACE_LISTING_EVALUATION_SCRIPT


def test_listing_content_guard_allows_public_item_content() -> None:
    assert (
        marketplace._has_listing_content(
            {
                "title": "2017 Audi Q7 3.0T Quattro Premium Sport Utility 4D",
                "price": "$9,300",
                "seller_name": None,
                "location": "Fairfield, CA",
                "description": "Clean title, runs well, priced to sell.",
            },
            final_url="https://www.facebook.com/marketplace/item/1234567890/",
        )
        is True
    )


def test_listing_content_guard_blocks_redirected_homepage() -> None:
    assert (
        marketplace._has_listing_content(
            {
                "title": "Facebook Marketplace: buy and sell items locally or shipped | Facebook",
                "price": None,
                "seller_name": None,
                "location": None,
                "description": "Marketplace Browse all Your account Create new listing",
            },
            final_url="https://www.facebook.com/marketplace/",
        )
        is False
    )
