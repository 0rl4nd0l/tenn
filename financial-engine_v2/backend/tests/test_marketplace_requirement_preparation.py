from __future__ import annotations

from pathlib import Path

from app.services.marketplace_mission_service import MarketplaceMissionService
from app.services.marketplace_price_intelligence import MarketplacePriceIntelligenceService
from app.services.marketplace_requirement_preparation import (
    prepare_requirement_driven_mission,
)
from app.services.marketplace_search_builder import (
    build_marketplace_search_pack,
    flatten_marketplace_queries,
)
from cockpit.storage.state import StateStore


def _services(tmp_path: Path) -> tuple[MarketplaceMissionService, MarketplacePriceIntelligenceService]:
    store = StateStore(str(tmp_path / "state.db"))
    return MarketplaceMissionService(store), MarketplacePriceIntelligenceService(store)


def test_prepare_requirement_driven_mission_persists_candidates_and_terms(
    tmp_path: Path,
) -> None:
    mission_service, price_service = _services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "Inference GPU",
            "brief": "Need a 24GB GPU for local inference in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
            "search_config": {"max_queries_per_run": 4},
        }
    )

    prepared = prepare_requirement_driven_mission(
        mission_service,
        price_service,
        mission,
    )

    terms = prepared["deployment_args"]["candidate_search_terms"]
    assert prepared["requirement_profile"]["mode"] == "requirement_driven"
    assert "RTX 3090 24GB" in terms
    assert "RTX 4090 24GB" in terms
    assert "24GB GPU" not in terms

    candidate_keys = {
        candidate["candidate_key"]
        for candidate in mission_service.list_mission_candidate_products(
            mission["mission_id"]
        )
    }
    assert "gpu-nvidia-rtx-3090-24gb" in candidate_keys
    assert "gpu-nvidia-rtx-4070-ti-super-16gb" not in candidate_keys

    search_pack = build_marketplace_search_pack(prepared)
    queries = flatten_marketplace_queries(search_pack, max_queries=4)
    assert any("rtx 3090" in query.lower() for query in queries)
    assert not any(query.lower().startswith("gpu ") for query in queries)


def test_prepare_requirement_driven_mission_bypasses_exact_product(
    tmp_path: Path,
) -> None:
    mission_service, price_service = _services(tmp_path)
    mission = mission_service.create_mission(
        {
            "name": "RTX 4070 Super",
            "brief": "Find RTX 4070 Super 12GB listings in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {
                "include_keywords": ["RTX 4070 Super"],
                "location_names": ["Melbourne"],
            },
        }
    )

    prepared = prepare_requirement_driven_mission(
        mission_service,
        price_service,
        mission,
    )

    assert prepared["requirement_profile"]["mode"] == "exact_product"
    assert "candidate_search_terms" not in prepared["deployment_args"]
    assert mission_service.list_mission_candidate_products(mission["mission_id"]) == []
