from __future__ import annotations

from types import SimpleNamespace

import app.services.marketplace_scanner as scanner
import pytest


def test_extract_marketplace_listing_id_and_canonical_url() -> None:
    url = "https://www.facebook.com/marketplace/item/1234567890/?ref=search"

    assert scanner.extract_marketplace_listing_id(url) == "1234567890"
    assert (
        scanner.canonical_marketplace_listing_url(url)
        == "https://www.facebook.com/marketplace/item/1234567890/"
    )


def test_scanner_returns_no_active_missions_without_browser_work(monkeypatch) -> None:
    mission_service = SimpleNamespace(
        list_missions=lambda statuses=None: [],
        get_mission=lambda mission_id: None,
    )
    marketplace_scanner = scanner.MarketplaceScanner(mission_service)
    monkeypatch.setattr(
        scanner,
        "check_marketplace_browser_health",
        lambda cdp_url=None, timeout_ms=None: {"status": "ready"},
    )

    result = marketplace_scanner.run_sync()

    assert result["missions_scanned"] == 0
    assert result["matches_saved"] == 0


def test_scanner_honors_cancel_request_before_browser_work(monkeypatch) -> None:
    mission_service = SimpleNamespace(
        list_missions=lambda statuses=None: [
            {
                "mission_id": "mp-1",
                "name": "GPU mission",
                "search_config": {"max_queries_per_run": 6},
                "scan_config": {
                    "detail_open_target": 10,
                    "run_time_budget_minutes": 20,
                    "candidate_card_target": 100,
                    "aggressive_alerting": False,
                },
            }
        ],
        get_mission=lambda mission_id: None,
    )
    marketplace_scanner = scanner.MarketplaceScanner(mission_service)

    with pytest.raises(scanner.MarketplaceScanCancelled):
        marketplace_scanner.run_sync(cancel_requested=lambda: True)
