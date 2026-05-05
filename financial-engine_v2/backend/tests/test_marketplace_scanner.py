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


class _FakeDetailPage(_FakeSearchPage):
    async def evaluate(self, script: str) -> dict[str, object]:
        self.evaluation_script = script
        return {
            "finalUrl": "https://www.facebook.com/marketplace/item/detail1/",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "description": "Used RTX 3090 24GB GPU in working condition.",
            "location": "Melbourne",
            "seller": "Seller",
            "rawTextLines": ["Used RTX 3090 24GB GPU in working condition."],
            "listingMedia": [],
        }

    async def screenshot(self, path: str, full_page: bool) -> None:
        self.screenshot_path = path
        self.full_page = full_page


class _FakeContext:
    def __init__(self, page_cls: type[_FakeSearchPage] = _FakeSearchPage) -> None:
        self.page_cls = page_cls
        self.pages: list[_FakeSearchPage] = []

    async def new_page(self) -> _FakeSearchPage:
        page = self.page_cls()
        self.pages.append(page)
        return page


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

    assert url.startswith("https://www.facebook.com/marketplace/melbourne/search?")
    assert "query=RTX+3090" in url
    assert "radiusKM=25" in url
    assert "latitude=-37.8136" in url
    assert "longitude=144.9631" in url


def test_build_marketplace_search_url_anchors_victoria_scope_to_melbourne_slug() -> None:
    url = scanner.build_marketplace_search_url(
        "RTX 3090",
        location_name="Victoria, Australia",
        radius_km=160,
    )

    assert url.startswith("https://www.facebook.com/marketplace/melbourne/search?")
    assert "query=RTX+3090" in url
    assert "radiusKM=160" in url
    assert "latitude=-37.8136" in url
    assert "longitude=144.9631" in url


def test_build_marketplace_search_url_anchors_sydney_scope() -> None:
    url = scanner.build_marketplace_search_url(
        "RTX 3090",
        location_name="Sydney, Australia",
        radius_km=160,
    )

    assert url.startswith("https://www.facebook.com/marketplace/sydney/search?")
    assert "query=RTX+3090" in url
    assert "radiusKM=160" in url
    assert "latitude=-33.8688" in url
    assert "longitude=151.2093" in url


def test_snapshot_price_band_uses_only_current_supported_benchmarks() -> None:
    band = scanner.MarketplaceScanner._snapshot_price_band(
        {
            "snapshot_id": "bench_good",
            "total_sample_size": 12,
            "freshness_status": "fresh",
            "used_median": 1700,
            "fair_range_low": 1450,
            "fair_range_high": 1750,
        },
        source="primary_tracked_product_benchmark",
    )

    assert band == {
        "median": 1700.0,
        "used_median": 1700.0,
        "average_source": "primary_tracked_product_benchmark",
        "benchmark_sample_size": 12,
        "fair_low": 1450.0,
        "fair_range_low": 1450.0,
        "fair_high": 1750.0,
        "fair_range_high": 1750.0,
        "benchmark_snapshot_id": "bench_good",
    }
    assert (
        scanner.MarketplaceScanner._snapshot_price_band(
            {
                "total_sample_size": 0,
                "freshness_status": "no_data",
                "used_median": None,
            },
            source="primary_tracked_product_benchmark",
        )
        is None
    )


@pytest.mark.parametrize("scope", ["Australia", "Australia-wide", "Nationwide"])
def test_scan_location_anchors_expands_australia_wide_scope(scope: str) -> None:
    anchors = scanner._scan_location_anchors([scope])

    assert anchors[:3] == [
        "Melbourne, Australia",
        "Sydney, Australia",
        "Brisbane, Australia",
    ]
    assert len(anchors) == 8


def test_scan_location_anchors_keeps_state_scope_single_anchor() -> None:
    assert scanner._scan_location_anchors(["Victoria, Australia"]) == [
        "Victoria, Australia"
    ]


def test_tracked_product_search_query_prefers_readable_product_name() -> None:
    query = scanner._tracked_product_search_query(
        {
            "canonical_key": "motherboard-asus-pro-ws-x570-ace-am4",
            "model_family": "Pro WS X570-ACE",
            "variant": "AM4 X570",
            "aliases": ["ASUS Pro WS X570-ACE"],
        }
    )

    assert query == "Pro WS X570-ACE AM4 X570"
    assert query != "motherboard-asus-pro-ws-x570-ace-am4"


def test_tracked_product_search_queries_include_exact_aliases() -> None:
    queries = scanner._tracked_product_search_queries(
        {
            "canonical_key": "motherboard-asus-pro-ws-x570-ace-am4",
            "model_family": "Pro WS X570-ACE",
            "variant": "AM4 X570",
            "aliases": [
                "ASUS Pro WS X570-ACE",
                "PRO-WS-X570-ACE",
                "WS X570-ACE",
            ],
        }
    )

    assert queries == [
        "Pro WS X570-ACE AM4 X570",
        "ASUS Pro WS X570-ACE",
        "PRO-WS-X570-ACE",
        "WS X570-ACE",
    ]


def test_detail_timeout_backoff_scales_for_consecutive_timeouts() -> None:
    marketplace_scanner = scanner.MarketplaceScanner(
        SimpleNamespace(),
        detail_timeout_backoff_seconds=(2.0, 2.0),
    )

    assert marketplace_scanner._detail_timeout_backoff_seconds(1) == 2.0
    assert marketplace_scanner._detail_timeout_backoff_seconds(2) == 4.0
    assert marketplace_scanner._detail_timeout_backoff_seconds(3) == 8.0


def test_inspect_listing_detail_waits_before_opening_page(
    tmp_path: Path,
    monkeypatch,
) -> None:
    marketplace_scanner = scanner.MarketplaceScanner(
        SimpleNamespace(),
        detail_pacing_seconds=(2.0, 2.0),
    )
    context = _FakeContext(_FakeDetailPage)
    delay_calls: list[float] = []

    async def fake_sleep(seconds, cancel_requested):
        delay_calls.append(seconds)
        assert context.pages == []

    monkeypatch.setattr(scanner, "MARKETPLACE_CAPTURE_ROOT", tmp_path)
    monkeypatch.setattr(marketplace_scanner, "_sleep_with_cancel", fake_sleep)

    detail = asyncio.run(
        marketplace_scanner._inspect_listing_detail(
            context=context,
            listing_url="https://www.facebook.com/marketplace/item/detail1/",
            mission_id="mission-1",
            cancel_requested=None,
        )
    )

    assert delay_calls == [2.0]
    assert detail["listing_id"] == "detail1"
    assert context.pages[0].url == "https://www.facebook.com/marketplace/item/detail1/"
    assert context.pages[0].closed is True


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
    context = _FakeContext()
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=context,
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    prepared = mission_service.get_mission(mission["mission_id"])
    assert result["scan_status"] == "completed"
    assert any("rtx 3090" in query.lower() for query in result["queries"])
    assert context.pages
    assert f"radiusKM={scanner.DEFAULT_MARKETPLACE_RADIUS_KM}" in context.pages[0].url
    assert "candidate_search_terms" in prepared["deployment_args"]
    assert mission_service.list_mission_candidate_products(mission["mission_id"])


def test_scanner_rotates_australia_wide_scope_across_city_anchors(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "Australia-wide GPU",
            "brief": "Find RTX cards nationwide.",
            "category_hint": "gpu",
            "hard_filters": {
                "include_keywords": ["RTX 3090", "RTX 4090", "RTX 4080"],
                "location_names": ["Australia"],
            },
            "search_config": {"max_queries_per_run": 6},
            "scan_config": {
                "detail_open_target": 1,
                "candidate_card_target": 1,
                "run_time_budget_minutes": 20,
            },
            "deployment_args": {"requirement_profile": {"mode": "exact_product"}},
        }
    )

    async def fake_collect(self, **kwargs):
        return []

    monkeypatch.setattr(scanner.MarketplaceScanner, "_collect_cards_for_query", fake_collect)

    marketplace_scanner = scanner.MarketplaceScanner(
        mission_service,
        price_service=price_service,
    )
    context = _FakeContext()
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=context,
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    urls = [page.url for page in context.pages]
    assert result["scan_status"] == "completed"
    assert len(urls) == 6
    assert any("/marketplace/melbourne/search?" in url for url in urls)
    assert any("/marketplace/sydney/search?" in url for url in urls)
    assert any("/marketplace/brisbane/search?" in url for url in urls)
    assert any("latitude=-37.8136" in url and "longitude=144.9631" in url for url in urls)
    assert any("latitude=-33.8688" in url and "longitude=151.2093" in url for url in urls)


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


def test_requirement_scanner_flags_under_market_resale_candidate(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    resale_product = price_service.create_tracked_product(
        {
            "category": "gpu",
            "brand": "NVIDIA",
            "model_family": "RTX 4070",
            "variant": "Super 12GB",
            "aliases": ["RTX 4070 Super", "4070 Super 12GB"],
        }
    )
    for idx, price in enumerate([1500, 1700, 1800, 1900, 2000]):
        price_service.ingest_observation(
            {
                "tracked_product_id": resale_product["tracked_product_id"],
                "source": "facebook",
                "observed_at": f"2026-04-2{idx}T10:00:00+00:00",
                "source_listing_id": f"rtx-4070-market-{idx}",
                "title": f"RTX 4070 Super 12GB listing {idx}",
                "price": price,
                "review_state": "accepted",
            }
        )
    snapshot = price_service.rebuild_benchmark_snapshot(
        resale_product["tracked_product_id"]
    )
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU",
            "brief": "Need a 24GB GPU for local inference under $1000 in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"], "price_max": 1000},
            "search_config": {"max_queries_per_run": 1},
            "scan_config": {
                "candidate_threshold": 70,
                "strong_match_threshold": 85,
                "detail_open_target": 1,
                "candidate_card_target": 1,
                "run_time_budget_minutes": 20,
            },
        }
    )

    async def fake_collect(self, **kwargs):
        return [
            {
                "listing_id": "resale",
                "listing_url": "https://www.facebook.com/marketplace/item/resale/",
                "title": "NVIDIA RTX 4070 Super 12GB",
                "price": "$1250",
                "location": "Melbourne",
                "text_fragments": ["NVIDIA RTX 4070 Super 12GB", "$1250", "Melbourne"],
            }
        ]

    inspected_urls: list[str] = []

    async def fake_inspect(self, **kwargs):
        inspected_urls.append(kwargs["listing_url"])
        return {
            "listing_id": "resale",
            "listing_url": "https://www.facebook.com/marketplace/item/resale/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 4070 Super 12GB",
            "price": "$1250",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Used RTX 4070 Super 12GB working condition.",
            "raw_text_lines": ["Used RTX 4070 Super 12GB working condition."],
            "raw_text_snapshot": "Used RTX 4070 Super 12GB working condition.",
            "screenshot_path": "/tmp/resale.png",
            "listing_media": [],
        }

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

    matches = mission_service.list_matches(mission_id=mission["mission_id"])
    assert result["matches_saved"] == 1
    assert result["alerts_created"] == 1
    assert result["rejected_by_requirement_fit"] == 0
    assert result["rejected_by_candidate_mismatch"] == 0
    assert inspected_urls == ["https://www.facebook.com/marketplace/item/resale/"]
    assert matches[0]["listing_id"] == "resale"
    assert matches[0]["price_value"] == 1250
    assert matches[0]["decision_band"] == "candidate"
    assert any("buy/resell candidate" in reason for reason in matches[0]["reasons_for"])
    resale_metadata = matches[0]["metadata"]["value_resale_candidate"]
    assert resale_metadata["flag"] == "value_resale_candidate"
    assert resale_metadata["tracked_product_id"] == resale_product["tracked_product_id"]
    assert resale_metadata["benchmark_snapshot_id"] == snapshot["snapshot_id"]
    assert resale_metadata["used_median"] == 1800
    seen = mission_service.get_seen_listing(mission["mission_id"], "resale")
    assert seen["last_status"] == "value_resale_candidate"
    alerts = mission_service.list_alerts(mission_id=mission["mission_id"])
    assert alerts[0]["trigger_reason"] == "value_resale_candidate"
    value = price_service.get_match_value_assessment(matches[0]["match_id"])
    assert value["resale_candidate"] is True
    assert value["value_source"] == "resale_candidate_benchmark"
    assert value["value_label"] == "excellent"


def test_scanner_preserves_card_price_when_detail_omits_price(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "NVMe storage",
            "brief": "CUSU SSD listing watch.",
            "category_hint": "ssd",
            "hard_filters": {
                "include_keywords": ["2TB", "Gen4", "NVMe", "M.2", "SSD"],
                "location_names": ["Melbourne"],
                "price_max": 500,
            },
            "soft_preferences": {"preferred_condition_terms": ["new"]},
            "search_config": {"max_queries_per_run": 1},
            "scan_config": {
                "candidate_threshold": 50,
                "strong_match_threshold": 70,
                "detail_open_target": 1,
                "candidate_card_target": 1,
                "aggressive_alerting": True,
            },
        }
    )
    mission["deployment_args"] = {"requirement_profile": {"mode": "exact_product"}}

    async def fake_collect(self, **kwargs):
        return [
            {
                "listing_id": "cusussd",
                "listing_url": "https://www.facebook.com/marketplace/item/cusussd/",
                "title": "CUSU SSD 2TB Brand New in Box",
                "price": "AU$298",
                "location": "Melbourne",
                "text_fragments": [
                    "CUSU SSD 2TB Brand New in Box",
                    "AU$298",
                    "Melbourne",
                ],
            }
        ]

    async def fake_inspect(self, **kwargs):
        return {
            "listing_id": "cusussd",
            "listing_url": "https://www.facebook.com/marketplace/item/cusussd/",
            "captured_at": "2026-05-01T00:00:00Z",
            "title": "CUSU SSD 2TB Brand New in Box",
            "price": None,
            "seller_name": None,
            "location": "Melbourne",
            "description": "New CUSU CV5000 2TB PCIe Gen4x4 NVMe M.2 SSD.",
            "raw_text_lines": ["New CUSU CV5000 2TB PCIe Gen4x4 NVMe M.2 SSD."],
            "raw_text_snapshot": "New CUSU CV5000 2TB PCIe Gen4x4 NVMe M.2 SSD.",
            "screenshot_path": "/tmp/cusussd.png",
            "listing_media": [],
        }

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

    matches = mission_service.list_matches(mission_id=mission["mission_id"])
    assert result["matches_saved"] == 1
    assert matches[0]["price"] == "AU$298"
    assert matches[0]["price_value"] == 298
    assert matches[0]["metadata"]["price_evidence"]["source"] == "search_card"
    assert (
        matches[0]["metadata"]["price_evidence"]["warning"]
        == "Detail page did not expose a price; preserved search-card price."
    )
    seen = mission_service.get_seen_listing(mission["mission_id"], "cusussd")
    assert seen["price_text"] == "AU$298"
    assert seen["price_value"] == 298
    assert seen["raw_snapshot"]["price_evidence"]["detail_price_text"] is None


def test_requirement_scanner_records_detail_inspection_failures(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU detail timeout",
            "brief": "Need a 24GB GPU for local inference under $1000 in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"], "price_max": 1000},
            "search_config": {"max_queries_per_run": 1},
            "scan_config": {
                "candidate_threshold": 50,
                "strong_match_threshold": 85,
                "detail_open_target": 2,
                "candidate_card_target": 2,
                "run_time_budget_minutes": 20,
            },
        }
    )
    cards = [
        {
            "listing_id": "timeout",
            "listing_url": "https://www.facebook.com/marketplace/item/timeout/",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 3090 24GB", "$900", "Melbourne"],
        },
        {
            "listing_id": "ok",
            "listing_url": "https://www.facebook.com/marketplace/item/ok/",
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "location": "Melbourne",
            "text_fragments": ["NVIDIA RTX 3090 24GB", "$900", "Melbourne"],
        },
    ]

    async def fake_collect(self, **kwargs):
        return cards

    inspected_urls: list[str] = []

    async def fake_inspect(self, **kwargs):
        inspected_urls.append(kwargs["listing_url"])
        if kwargs["listing_url"].endswith("/timeout/"):
            raise RuntimeError("Page.goto: Timeout 20000ms exceeded.")
        return {
            "listing_id": "ok",
            "listing_url": "https://www.facebook.com/marketplace/item/ok/",
            "captured_at": "2026-04-29T00:00:00Z",
            "title": "NVIDIA RTX 3090 24GB GPU",
            "price": "$900",
            "seller_name": "Seller",
            "location": "Melbourne",
            "description": "Used RTX 3090 24GB GPU with 24GB VRAM, working condition.",
            "raw_text_lines": ["Used RTX 3090 24GB GPU with 24GB VRAM."],
            "raw_text_snapshot": "Used RTX 3090 24GB GPU with 24GB VRAM.",
            "screenshot_path": "/tmp/ok.png",
            "listing_media": [],
        }

    monkeypatch.setattr(scanner.MarketplaceScanner, "_collect_cards_for_query", fake_collect)
    monkeypatch.setattr(scanner.MarketplaceScanner, "_inspect_listing_detail", fake_inspect)

    marketplace_scanner = scanner.MarketplaceScanner(
        mission_service,
        price_service=price_service,
        detail_timeout_backoff_seconds=(2.0, 2.0),
    )
    backoff_calls: list[float] = []

    async def fake_sleep(seconds, cancel_requested):
        backoff_calls.append(seconds)

    monkeypatch.setattr(marketplace_scanner, "_sleep_with_cancel", fake_sleep)
    result = asyncio.run(
        marketplace_scanner._scan_mission(
            context=_FakeContext(),
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )

    failed_seen = mission_service.get_seen_listing(mission["mission_id"], "timeout")
    assert result["scan_status"] == "completed"
    assert result["detail_pages_opened"] == 2
    assert inspected_urls == [
        "https://www.facebook.com/marketplace/item/timeout/",
        "https://www.facebook.com/marketplace/item/ok/",
    ]
    assert backoff_calls == [2.0]
    assert result["detail_rejection_reasons"]["detail_inspection_failed"] == 1
    assert failed_seen["last_status"] == "detail_inspection_failed"
    assert "Timeout 20000ms" in failed_seen["last_error"]
    assert (
        failed_seen["raw_snapshot"]["post_detail_outcome"]["reason_code"]
        == "detail_inspection_failed"
    )


def test_requirement_scanner_preserves_cancel_during_detail_inspection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    mission_service, price_service = _state_services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU detail cancel",
            "brief": "Need a 24GB GPU for local inference under $1000 in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"], "price_max": 1000},
            "search_config": {"max_queries_per_run": 1},
            "scan_config": {
                "candidate_threshold": 70,
                "strong_match_threshold": 85,
                "detail_open_target": 1,
                "candidate_card_target": 1,
                "run_time_budget_minutes": 20,
            },
        }
    )

    async def fake_collect(self, **kwargs):
        return [
            {
                "listing_id": "cancel",
                "listing_url": "https://www.facebook.com/marketplace/item/cancel/",
                "title": "NVIDIA RTX 3090 24GB",
                "price": "$900",
                "location": "Melbourne",
                "text_fragments": ["NVIDIA RTX 3090 24GB", "$900", "Melbourne"],
            }
        ]

    async def fake_inspect(self, **kwargs):
        raise scanner.MarketplaceScanCancelled("Marketplace scan cancelled by user request.")

    monkeypatch.setattr(scanner.MarketplaceScanner, "_collect_cards_for_query", fake_collect)
    monkeypatch.setattr(scanner.MarketplaceScanner, "_inspect_listing_detail", fake_inspect)

    marketplace_scanner = scanner.MarketplaceScanner(
        mission_service,
        price_service=price_service,
    )

    with pytest.raises(scanner.MarketplaceScanCancelled):
        asyncio.run(
            marketplace_scanner._scan_mission(
                context=_FakeContext(),
                mission=mission,
                log=None,
                cancel_requested=None,
            )
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
    tracked_product = price_service.create_tracked_product(
        {
            "category": "gpu",
            "brand": "NVIDIA",
            "model_family": "RTX 4070",
            "variant": "Super",
            "aliases": ["NVIDIA RTX 4070 Super"],
        }
    )
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
    mission_service.link_primary_tracked_product(
        mission["mission_id"],
        tracked_product["tracked_product_id"],
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

    observations = price_service.list_observations(
        tracked_product_id=tracked_product["tracked_product_id"]
    )
    snapshot = price_service.latest_benchmark_snapshot(
        tracked_product["tracked_product_id"]
    )
    assert len(observations) == 1
    assert observations[0]["source_listing_id"] == "exact"
    assert observations[0]["capture_mode"] == "scanner"
    assert observations[0]["price"] == 700
    assert observations[0]["provenance"]["mission_id"] == mission["mission_id"]
    assert observations[0]["provenance"]["product_resolution"] == "primary_tracked_product"
    assert snapshot is not None
    assert snapshot["total_sample_size"] == 1

    asyncio.run(
        marketplace_scanner._scan_mission(
            context=_FakeContext(),
            mission=mission,
            log=None,
            cancel_requested=None,
        )
    )
    assert (
        len(
            price_service.list_observations(
                tracked_product_id=tracked_product["tracked_product_id"]
            )
        )
        == 1
    )
