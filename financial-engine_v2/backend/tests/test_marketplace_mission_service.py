from __future__ import annotations

from pathlib import Path

import pytest

from app.services.marketplace_mission_service import MarketplaceMissionService
from cockpit.storage.state import StateStore


def _state_store(tmp_path: Path) -> StateStore:
    return StateStore(str(tmp_path / "state.db"))


def test_marketplace_mission_service_creates_and_updates_missions(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)

    mission = service.create_mission(
        {
            "name": "Dual-cab ute",
            "brief": "Find a reliable 4x4 dual cab under 25k.",
            "hard_filters": {
                "include_keywords": ["dual cab", "4x4"],
                "price_max": 25000,
                "location_names": ["Melbourne"],
            },
            "soft_preferences": {"preferred_brands": ["Toyota"]},
        }
    )

    assert mission["status"] == "active"
    assert mission["hard_filters"]["price_max"] == 25000
    assert service.list_missions()[0]["mission_id"] == mission["mission_id"]

    updated = service.update_mission(
        mission["mission_id"],
        {"status": "paused", "scan_config": {"aggressive_alerting": True}},
    )

    assert updated["status"] == "paused"
    assert updated["scan_config"]["aggressive_alerting"] is True


def test_marketplace_mission_service_links_one_primary_tracked_product(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)
    mission = service.create_mission(
        {
            "name": "GPU mission",
            "brief": "Find a used RTX 4070 Super in Melbourne.",
            "hard_filters": {
                "include_keywords": ["rtx 4070 super"],
                "location_names": ["Melbourne"],
            },
        }
    )

    assert service.get_primary_tracked_product_link(mission["mission_id"]) is None

    first = service.link_primary_tracked_product(mission["mission_id"], "tp_first")
    assert first["tracked_product_id"] == "tp_first"
    assert first["link_type"] == "primary"

    second = service.link_primary_tracked_product(mission["mission_id"], "tp_second")
    assert second["tracked_product_id"] == "tp_second"
    assert service.get_primary_tracked_product_link(mission["mission_id"])["tracked_product_id"] == "tp_second"

    removed = service.unlink_primary_tracked_product(mission["mission_id"])
    assert removed["tracked_product_id"] == "tp_second"
    assert service.get_primary_tracked_product_link(mission["mission_id"]) is None


def test_marketplace_mission_service_persists_requirement_profile_and_candidates(
    tmp_path: Path,
) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)
    mission = service.create_mission(
        {
            "name": "Inference GPU",
            "brief": "24GB GPU for local inference.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
        }
    )

    assert mission["deployment_args"]["requirement_profile"]["mode"] == "requirement_driven"
    assert service.get_mission(mission["mission_id"])["requirement_profile"]["category"] == "gpu"

    candidates = service.replace_mission_candidate_products(
        mission["mission_id"],
        [
            {
                "tracked_product_id": "tp_3090",
                "candidate_key": "gpu-nvidia-rtx-3090-24gb",
                "category": "gpu",
                "candidate_rank": 1,
                "fit_score": 95,
                "fit_label": "strong_fit",
                "hard_constraints_met": ["vram_gb"],
                "soft_preferences_met": ["acceleration_stack"],
                "explanation": "RTX 3090 satisfies the VRAM requirement.",
            }
        ],
    )

    assert candidates[0]["tracked_product_id"] == "tp_3090"
    assert candidates[0]["hard_constraints_met"] == ["vram_gb"]

    deleted = service.delete_mission(mission["mission_id"])
    assert deleted["deleted_mission_candidate_products"] == 1


def test_marketplace_mission_service_persists_seen_matches_and_alerts(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)
    mission = service.create_mission(
        {
            "name": "Workshop tools",
            "brief": "Find used woodworking tools in Melbourne.",
            "hard_filters": {"include_keywords": ["saw"], "location_names": ["Melbourne"]},
        }
    )

    seen = service.upsert_seen_listing(
        mission["mission_id"],
        {
            "listing_id": "123",
            "listing_url": "https://www.facebook.com/marketplace/item/123/",
            "title": "Portable saw",
            "price_text": "$180",
            "price_value": 180,
            "raw_snapshot": {"title": "Portable saw"},
            "last_status": "candidate",
            "last_score": 76,
            "last_decision_band": "candidate",
        },
    )
    assert seen["listing_id"] == "123"
    assert service.price_band(mission["mission_id"]) == {
        "min": 180.0,
        "median": 180.0,
        "max": 180.0,
    }

    match = service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "123",
            "listing_url": "https://www.facebook.com/marketplace/item/123/",
            "title": "Portable saw",
            "price": "$180",
            "price_value": 180,
            "captured_at": "2026-04-18T10:00:00Z",
            "score": 76,
            "decision_band": "candidate",
            "reasons_for": ["Cheap"],
            "reasons_against": [],
            "raw_text_snapshot": "Portable saw",
        }
    )
    alert = service.create_alert(
        mission_id=mission["mission_id"],
        match_id=match["match_id"],
        trigger_reason="new_listing",
    )

    assert service.get_match(match["match_id"])["title"] == "Portable saw"
    assert service.list_alerts()[0]["alert_id"] == alert["alert_id"]


def test_marketplace_match_persists_listing_media_urls(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)
    mission = service.create_mission(
        {
            "name": "GPU finder",
            "brief": "Find a used RTX 3090 in Melbourne.",
            "hard_filters": {"include_keywords": ["rtx 3090"], "location_names": ["Melbourne"]},
        }
    )

    match = service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "gpu-1",
            "listing_url": "https://www.facebook.com/marketplace/item/gpu-1/",
            "title": "RTX 3090 listing",
            "price": "$999",
            "captured_at": "2026-04-22T10:00:00Z",
            "score": 88,
            "decision_band": "strong_match",
            "reasons_for": ["Meets budget"],
            "reasons_against": [],
            "raw_text_snapshot": "RTX 3090 24GB",
            "listing_media": [
                "https://example.com/listing-1.jpg",
                "https://example.com/listing-1.jpg",
                "not-a-url",
                "https://example.com/listing-2.jpg",
            ],
        }
    )

    assert match["listing_media"] == [
        "https://example.com/listing-1.jpg",
        "https://example.com/listing-2.jpg",
    ]


def test_marketplace_match_list_hides_dismissed_by_default(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)
    mission = service.create_mission(
        {
            "name": "GPU finder",
            "brief": "Find a used RTX 3090 in Melbourne.",
            "hard_filters": {"include_keywords": ["rtx 3090"], "location_names": ["Melbourne"]},
        }
    )

    visible = service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "gpu-visible",
            "listing_url": "https://www.facebook.com/marketplace/item/gpu-visible/",
            "title": "RTX 3090 visible",
            "price": "$900",
            "captured_at": "2026-04-22T10:00:00Z",
            "score": 88,
            "decision_band": "strong_match",
            "reasons_for": ["Meets budget"],
            "reasons_against": [],
            "raw_text_snapshot": "RTX 3090 24GB",
        }
    )
    dismissed = service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "gpu-dismissed",
            "listing_url": "https://www.facebook.com/marketplace/item/gpu-dismissed/",
            "title": "RTX 3090 dismissed",
            "price": "$950",
            "captured_at": "2026-04-22T11:00:00Z",
            "score": 82,
            "decision_band": "candidate",
            "reasons_for": ["Meets budget"],
            "reasons_against": [],
            "raw_text_snapshot": "RTX 3090 24GB",
        }
    )
    service.update_match_status(dismissed["match_id"], "dismissed")

    assert [item["match_id"] for item in service.list_matches()] == [visible["match_id"]]
    assert [
        item["match_id"]
        for item in service.list_matches(status="dismissed")
    ] == [dismissed["match_id"]]


def test_marketplace_mission_delete_cleans_related_records(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)
    mission = service.create_mission(
        {
            "name": "Mission cleanup",
            "brief": "Find graphics cards around Melbourne.",
            "hard_filters": {"include_keywords": ["graphics card"], "location_names": ["Melbourne"]},
        }
    )
    match = service.upsert_match(
        {
            "mission_id": mission["mission_id"],
            "listing_id": "cleanup-1",
            "listing_url": "https://www.facebook.com/marketplace/item/cleanup-1/",
            "title": "GPU listing",
            "price": "$800",
            "captured_at": "2026-04-22T11:00:00Z",
            "score": 80,
            "decision_band": "candidate",
            "reasons_for": ["Price is fair"],
            "reasons_against": [],
            "raw_text_snapshot": "Sample listing",
        }
    )
    service.create_alert(
        mission_id=mission["mission_id"],
        match_id=match["match_id"],
        trigger_reason="new_listing",
    )
    store.set_marketplace_match_feedback(match["match_id"], "interested")
    service.upsert_seen_listing(
        mission["mission_id"],
        {
            "listing_id": "cleanup-1",
            "listing_url": "https://www.facebook.com/marketplace/item/cleanup-1/",
            "title": "GPU listing",
            "raw_snapshot": {"title": "GPU listing"},
        },
    )

    deleted = service.delete_mission(mission["mission_id"])

    assert deleted["deleted_missions"] == 1
    assert deleted["deleted_matches"] >= 1
    assert deleted["deleted_match_feedback"] == 1
    assert service.get_mission(mission["mission_id"]) is None
    assert service.get_match(match["match_id"]) is None
    assert store.get_marketplace_match_feedback(match["match_id"]) is None
    assert service.list_alerts(mission_id=mission["mission_id"]) == []


def test_marketplace_mission_service_requires_explicit_location_scope(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)

    with pytest.raises(ValueError, match="location"):
        service.create_mission(
            {
                "name": "Missing location",
                "brief": "Find a reliable 4x4 dual cab under 25k.",
                "hard_filters": {"include_keywords": ["4x4", "dual cab"], "price_max": 25000},
            }
        )


def test_marketplace_mission_service_canonicalizes_victoria_location(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)

    mission = service.create_mission(
        {
            "name": "GPU search",
            "brief": "Find a GPU around victoria.",
            "hard_filters": {"include_keywords": ["gpu"], "location_names": ["victoria"]},
        }
    )

    assert mission["hard_filters"]["location_names"] == ["Victoria, Australia"]
