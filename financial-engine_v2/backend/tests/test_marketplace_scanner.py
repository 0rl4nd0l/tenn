from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import app.services.marketplace_scanner as scanner
import pytest
from app.services.marketplace_mission_service import MarketplaceMissionService
from app.services.marketplace_price_intelligence import MarketplacePriceIntelligenceService
from app.services.marketplace_requirement_preparation import (
    RequirementMissionPreparationError,
)
from cockpit.storage.state import StateStore


class _FakeSearchPage:
    def set_default_timeout(self, timeout_ms: int) -> None:
        self.timeout_ms = timeout_ms

    async def goto(self, url: str, wait_until: str | None = None) -> None:
        self.url = url
        self.wait_until = wait_until

    async def wait_for_timeout(self, timeout_ms: int) -> None:
        self.wait_timeout_ms = timeout_ms

    async def close(self) -> None:
        self.closed = True


class _FakeContext:
    async def new_page(self) -> _FakeSearchPage:
        return _FakeSearchPage()


def _state_services(
    tmp_path: Path,
) -> tuple[MarketplaceMissionService, MarketplacePriceIntelligenceService]:
    store = StateStore(str(tmp_path / "state.db"))
    return MarketplaceMissionService(store), MarketplacePriceIntelligenceService(store)


def test_extract_marketplace_listing_id_and_canonical_url() -> None:
    url = "https://www.facebook.com/marketplace/item/1234567890/?ref=search"

    assert scanner.extract_marketplace_listing_id(url) == "1234567890"
    assert (
        scanner.canonical_marketplace_listing_url(url)
        == "https://www.facebook.com/marketplace/item/1234567890/"
    )


def test_build_marketplace_search_url_scopes_location_and_radius() -> None:
    url = scanner.build_marketplace_search_url(
        "RTX 3090",
        location_name="Melbourne, VIC",
        radius_km=25,
    )

    assert url.startswith("https://www.facebook.com/marketplace/melbourne-vic/search?")
    assert "query=RTX+3090" in url
    assert "radiusKM=25" in url
    assert "latitude=-37.8136" in url
    assert "longitude=144.9631" in url


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


def test_scanner_allows_ready_status_without_login_state(monkeypatch) -> None:
    mission_service = SimpleNamespace(
        list_missions=lambda statuses=None: [],
        get_mission=lambda mission_id: None,
    )
    marketplace_scanner = scanner.MarketplaceScanner(mission_service)
    monkeypatch.setattr(
        scanner,
        "check_marketplace_browser_health",
        lambda cdp_url=None, timeout_ms=None: {
            "status": "ready",
            "detail": "Marketplace browser profile is ready.",
        },
    )

    result = marketplace_scanner.run_sync()

    assert result["missions_scanned"] == 0
    assert result["matches_saved"] == 0


def test_scanner_blocks_when_browser_unavailable(monkeypatch) -> None:
    mission_service = SimpleNamespace(
        list_missions=lambda statuses=None: [],
        get_mission=lambda mission_id: None,
    )
    marketplace_scanner = scanner.MarketplaceScanner(mission_service)
    monkeypatch.setattr(
        scanner,
        "check_marketplace_browser_health",
        lambda cdp_url=None, timeout_ms=None: {
            "status": "browser_unavailable",
            "detail": "No browser is listening on the configured remote debugging port.",
        },
    )

    with pytest.raises(RuntimeError, match="No browser is listening"):
        marketplace_scanner.run_sync()


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


def test_scanner_preflight_prepares_requirement_candidates_before_queries(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU",
            "brief": "Need a 24GB GPU for local inference in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
            "search_config": {"max_queries_per_run": 2},
            "scan_config": {"detail_open_target": 1, "candidate_card_target": 1},
        }
    )

    async def fake_collect(self, **kwargs):
        return []

    monkeypatch.setattr(scanner.MarketplaceScanner, "_collect_cards_for_query", fake_collect)

    marketplace_scanner = scanner.MarketplaceScanner(
        mission_service,
        price_service=price_service,
    )
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=_FakeContext(),
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    prepared = mission_service.get_mission(mission["mission_id"])
    assert result["scan_status"] == "completed"
    assert any("rtx 3090" in query.lower() for query in result["queries"])
    assert "candidate_search_terms" in prepared["deployment_args"]
    assert mission_service.list_mission_candidate_products(mission["mission_id"])


def test_scanner_fails_closed_when_requirement_preparation_fails(monkeypatch) -> None:
    mission = {
        "mission_id": "mp-1",
        "name": "Broken requirement mission",
        "deployment_args": {
            "requirement_profile": {"mode": "requirement_driven", "category": "gpu"},
        },
    }

    def fail_prepare(*args, **kwargs):
        raise RequirementMissionPreparationError("mp-1", "no candidate products generated")

    monkeypatch.setattr(scanner, "prepare_requirement_driven_mission", fail_prepare)
    marketplace_scanner = scanner.MarketplaceScanner(
        SimpleNamespace(),
        price_service=SimpleNamespace(),
    )
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=_FakeContext(),
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    assert result["scan_status"] == "aborted"
    assert result["abort_reason"] == "no candidate products generated"
    assert result["queries"] == []
    assert result["matches_saved"] == 0


def test_requirement_scanner_reports_rejection_counters(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU",
            "brief": "Need a 24GB GPU for local inference under $1000 in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"], "price_max": 1000},
            "search_config": {"max_queries_per_run": 1},
            "scan_config": {
                "candidate_threshold": 50,
                "strong_match_threshold": 85,
                "detail_open_target": 10,
                "candidate_card_target": 10,
                "run_time_budget_minutes": 20,
            },
        }
    )
    cards = [
        {
            "listing_id": "loc",
            "listing_url": "https://www.facebook.com/marketplace/item/loc/",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "location": "Vancouver, BC, Canada",
            "text_fragments": ["NVIDIA RTX 3090 24GB", "$900", "Vancouver, BC"],
        },
        {
            "listing_id": "fit",
            "listing_url": "https://www.facebook.com/marketplace/item/fit/",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$2,000",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 3090 24GB", "$2,000", "Melbourne"],
        },
        {
            "listing_id": "ok",
            "listing_url": "https://www.facebook.com/marketplace/item/ok/",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 3090 24GB", "$900", "Melbourne"],
        },
        {
            "listing_id": "weak-loc",
            "listing_url": "https://www.facebook.com/marketplace/item/weak-loc/",
            "title": "NVIDIA RTX 3090",
            "price": "$900",
            "location": "Victoria",
            "text_fragments": ["NVIDIA RTX 3090", "$900", "Victoria"],
        },
        {
            "listing_id": "junk",
            "listing_url": "https://www.facebook.com/marketplace/item/junk/",
            "title": "WTB RTX 3090 box only swap",
            "price": "$1",
            "location": "Melbourne",
            "text_fragments": ["wanted", "swap", "box only"],
        },
        {
            "listing_id": "mismatch",
            "listing_url": "https://www.facebook.com/marketplace/item/mismatch/",
            "title": "NVIDIA RTX 4070 Super 12GB",
            "price": "$700",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 4070 Super 12GB", "$700", "Melbourne"],
        },
    ]
    details = {
        "https://www.facebook.com/marketplace/item/ok/": {
            "listing_id": "ok",
            "listing_url": "https://www.facebook.com/marketplace/item/ok/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Used RTX 3090 24GB working condition.",
            "raw_text_lines": ["Used RTX 3090 24GB working condition."],
            "raw_text_snapshot": "Used RTX 3090 24GB working condition.",
            "screenshot_path": "/tmp/ok.png",
            "listing_media": [],
        },
        "https://www.facebook.com/marketplace/item/weak-loc/": {
            "listing_id": "weak-loc",
            "listing_url": "https://www.facebook.com/marketplace/item/weak-loc/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Used RTX 3090 24GB working condition.",
            "raw_text_lines": ["Used RTX 3090 24GB working condition."],
            "raw_text_snapshot": "Used RTX 3090 24GB working condition.",
            "screenshot_path": "/tmp/weak-loc.png",
            "listing_media": [],
        },
        "https://www.facebook.com/marketplace/item/mismatch/": {
            "listing_id": "mismatch",
            "listing_url": "https://www.facebook.com/marketplace/item/mismatch/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 4070 Super 12GB",
            "price": "$700",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Used RTX 4070 Super 12GB working condition.",
            "raw_text_lines": ["Used RTX 4070 Super 12GB working condition."],
            "raw_text_snapshot": "Used RTX 4070 Super 12GB working condition.",
            "screenshot_path": "/tmp/mismatch.png",
            "listing_media": [],
        },
    }

    async def fake_collect(self, **kwargs):
        return cards

    inspected_urls: list[str] = []

    async def fake_inspect(self, **kwargs):
        inspected_urls.append(kwargs["listing_url"])
        return details[kwargs["listing_url"]]

    monkeypatch.setattr(scanner.MarketplaceScanner, "_collect_cards_for_query", fake_collect)
    monkeypatch.setattr(scanner.MarketplaceScanner, "_inspect_listing_detail", fake_inspect)

    marketplace_scanner = scanner.MarketplaceScanner(
        mission_service,
        price_service=price_service,
    )
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=_FakeContext(),
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    assert result["harvested_cards"] == 6
    assert result["listings_seen"] == 6
    assert result["rejected_by_location"] == 1
    assert result["rejected_by_requirement_fit"] == 2
    assert result["rejected_by_candidate_mismatch"] == 1
    assert result["detail_pages_opened"] == 3
    assert result["matches_saved"] == 2
    assert inspected_urls == [
        "https://www.facebook.com/marketplace/item/ok/",
        "https://www.facebook.com/marketplace/item/weak-loc/",
        "https://www.facebook.com/marketplace/item/mismatch/",
    ]
    mismatch_seen = mission_service.get_seen_listing(
        mission["mission_id"],
        "mismatch",
    )
    assert mismatch_seen["last_status"] == "candidate_unmatched"
    assert mismatch_seen["match_id"] is None
    assert result["detail_rejection_reasons"] == {"detail_candidate_unmatched": 1}
    assert (
        mismatch_seen["raw_snapshot"]["post_detail_outcome"]["reason_code"]
        == "detail_candidate_unmatched"
    )


def test_requirement_scanner_reports_structured_detail_rejection_reasons(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU detail reasons",
            "brief": "Need a 24GB GPU for local inference under $1000 in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"], "price_max": 1000},
            "search_config": {"max_queries_per_run": 1},
            "scan_config": {
                "candidate_threshold": 70,
                "strong_match_threshold": 85,
                "detail_open_target": 10,
                "candidate_card_target": 10,
                "run_time_budget_minutes": 20,
            },
        }
    )
    cards = [
        {
            "listing_id": "wrong-vram",
            "listing_url": "https://www.facebook.com/marketplace/item/wrong-vram/",
            "title": "NVIDIA RTX 3080 Ti 12GB",
            "price": "$650",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 3080 Ti 12GB", "$650", "Melbourne"],
        },
        {
            "listing_id": "wrong-model",
            "listing_url": "https://www.facebook.com/marketplace/item/wrong-model/",
            "title": "NVIDIA RTX 3060 Ti",
            "price": "$350",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 3060 Ti", "$350", "Melbourne"],
        },
        {
            "listing_id": "condition",
            "listing_url": "https://www.facebook.com/marketplace/item/condition/",
            "title": "NVIDIA RTX 3090",
            "price": "$500",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 3090", "$500", "Melbourne"],
        },
        {
            "listing_id": "insufficient",
            "listing_url": "https://www.facebook.com/marketplace/item/insufficient/",
            "title": "NVIDIA graphics card",
            "price": "$600",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA graphics card", "$600", "Melbourne"],
        },
    ]
    details = {
        "https://www.facebook.com/marketplace/item/wrong-vram/": {
            "listing_id": "wrong-vram",
            "listing_url": "https://www.facebook.com/marketplace/item/wrong-vram/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 3080 Ti 12GB",
            "price": "$650",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Good working 12GB card.",
            "raw_text_lines": ["RTX 3080 Ti 12GB"],
            "raw_text_snapshot": "RTX 3080 Ti 12GB",
            "screenshot_path": "/tmp/wrong-vram.png",
            "listing_media": [],
        },
        "https://www.facebook.com/marketplace/item/wrong-model/": {
            "listing_id": "wrong-model",
            "listing_url": "https://www.facebook.com/marketplace/item/wrong-model/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 3060 Ti",
            "price": "$350",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Working GPU.",
            "raw_text_lines": ["RTX 3060 Ti"],
            "raw_text_snapshot": "RTX 3060 Ti",
            "screenshot_path": "/tmp/wrong-model.png",
            "listing_media": [],
        },
        "https://www.facebook.com/marketplace/item/condition/": {
            "listing_id": "condition",
            "listing_url": "https://www.facebook.com/marketplace/item/condition/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 3090",
            "price": "$500",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Not working, for parts only.",
            "raw_text_lines": ["Not working", "for parts only"],
            "raw_text_snapshot": "Not working, for parts only.",
            "screenshot_path": "/tmp/condition.png",
            "listing_media": [],
        },
        "https://www.facebook.com/marketplace/item/insufficient/": {
            "listing_id": "insufficient",
            "listing_url": "https://www.facebook.com/marketplace/item/insufficient/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA graphics card",
            "price": "$600",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Working GPU, exact specs unknown.",
            "raw_text_lines": ["working GPU"],
            "raw_text_snapshot": "Working GPU, exact specs unknown.",
            "screenshot_path": "/tmp/insufficient.png",
            "listing_media": [],
        },
    }

    async def fake_collect(self, **kwargs):
        return cards

    async def fake_inspect(self, **kwargs):
        return details[kwargs["listing_url"]]

    monkeypatch.setattr(scanner.MarketplaceScanner, "_collect_cards_for_query", fake_collect)
    monkeypatch.setattr(scanner.MarketplaceScanner, "_inspect_listing_detail", fake_inspect)

    marketplace_scanner = scanner.MarketplaceScanner(
        mission_service,
        price_service=price_service,
    )
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=_FakeContext(),
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    assert result["detail_pages_opened"] == 4
    assert result["matches_saved"] == 0
    assert result["rejected_by_requirement_fit"] == 4
    assert result["detail_rejection_reasons"] == {
        "detail_insufficient_evidence": 1,
        "detail_parts_or_condition_failed": 1,
        "detail_wrong_model": 1,
        "detail_wrong_vram": 1,
    }
    for listing_id, reason_code in {
        "wrong-vram": "detail_wrong_vram",
        "wrong-model": "detail_wrong_model",
        "condition": "detail_parts_or_condition_failed",
        "insufficient": "detail_insufficient_evidence",
    }.items():
        seen = mission_service.get_seen_listing(mission["mission_id"], listing_id)
        assert seen["last_status"] == reason_code
        assert seen["match_id"] is None
        assert seen["raw_snapshot"]["post_detail_outcome"]["reason_code"] == reason_code


def test_exact_product_scanner_bypasses_requirement_candidate_resolution(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "RTX 4070 Super",
            "brief": "Find an RTX 4070 Super in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {
                "include_keywords": ["RTX 4070 Super"],
                "location_names": ["Melbourne"],
            },
            "search_config": {"max_queries_per_run": 1},
            "scan_config": {
                "candidate_threshold": 50,
                "strong_match_threshold": 85,
                "detail_open_target": 1,
                "candidate_card_target": 1,
                "run_time_budget_minutes": 20,
            },
        }
    )
    card = {
        "listing_id": "exact",
        "listing_url": "https://www.facebook.com/marketplace/item/exact/",
        "title": "NVIDIA RTX 4070 Super",
        "price": "$700",
        "location": "Melbourne",
        "text_fragments": ["NVIDIA RTX 4070 Super", "$700", "Melbourne"],
    }
    detail = {
        "listing_id": "exact",
        "listing_url": "https://www.facebook.com/marketplace/item/exact/",
        "captured_at": "2026-04-29T00:00:00Z",
        "title": "NVIDIA RTX 4070 Super",
        "price": "$700",
        "seller_name": "Seller",
        "location": "Melbourne",
        "description": "Used RTX 4070 Super working condition.",
        "raw_text_lines": ["Used RTX 4070 Super working condition."],
        "raw_text_snapshot": "Used RTX 4070 Super working condition.",
        "screenshot_path": "/tmp/exact.png",
        "listing_media": [],
    }

    async def fake_collect(self, **kwargs):
        return [card]

    async def fake_inspect(self, **kwargs):
        return detail

    def fail_resolve(self, *args, **kwargs):
        raise AssertionError("exact-product missions must not resolve requirement candidates")

    monkeypatch.setattr(scanner.MarketplaceScanner, "_collect_cards_for_query", fake_collect)
    monkeypatch.setattr(scanner.MarketplaceScanner, "_inspect_listing_detail", fake_inspect)
    monkeypatch.setattr(
        scanner.MarketplaceScanner,
        "_resolve_requirement_candidate",
        fail_resolve,
    )

    marketplace_scanner = scanner.MarketplaceScanner(
        mission_service,
        price_service=price_service,
    )
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=_FakeContext(),
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    assert result["detail_pages_opened"] == 1
    assert result["matches_saved"] == 1
    assert result["rejected_by_candidate_mismatch"] == 0
    assert result["detail_rejection_reasons"] == {}
