from __future__ import annotations

from pathlib import Path

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
            "hard_filters": {"include_keywords": ["dual cab", "4x4"], "price_max": 25000},
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


def test_marketplace_mission_service_persists_seen_matches_and_alerts(tmp_path: Path) -> None:
    store = _state_store(tmp_path)
    service = MarketplaceMissionService(store)
    mission = service.create_mission(
        {
            "name": "Workshop tools",
            "brief": "Find used woodworking tools in Melbourne.",
            "hard_filters": {"include_keywords": ["saw"]},
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
