from __future__ import annotations

from app.services.marketplace_search_builder import (
    build_marketplace_search_pack,
    flatten_marketplace_queries,
)


def test_build_marketplace_search_pack_prefers_keywords_and_brands() -> None:
    mission = {
        "name": "Dual-cab ute",
        "brief": "Find a reliable 4x4 dual cab under 25k.",
        "hard_filters": {
            "include_keywords": ["dual cab", "4x4"],
            "exclude_keywords": ["wrecking"],
            "forbidden_terms": ["stat write-off"],
            "location_names": ["Preston"],
            "price_max": 25000,
        },
        "soft_preferences": {"preferred_brands": ["Toyota", "Isuzu"]},
        "search_config": {"max_queries_per_run": 4, "query_variants_enabled": True},
    }

    pack = build_marketplace_search_pack(mission)

    assert "wrecking" in pack["exclude_terms"]
    assert any("Toyota" in query for query in pack["primary_queries"])
    assert pack["location_scope"]["location_names"] == ["Preston"]

    queries = flatten_marketplace_queries(pack, max_queries=4)
    assert len(queries) <= 4
    assert queries[0]


def test_build_marketplace_search_pack_uses_brief_terms_when_keywords_missing() -> None:
    mission = {
        "name": "Workshop heater",
        "brief": "Find a compact garage heater for a small workshop.",
        "hard_filters": {},
        "soft_preferences": {},
        "search_config": {"max_queries_per_run": 3},
    }

    pack = build_marketplace_search_pack(mission)

    assert pack["primary_queries"]
    assert any("heater" in query.lower() for query in pack["primary_queries"] + pack["fallback_queries"])


def test_build_marketplace_search_pack_compacts_long_keyword_blobs() -> None:
    mission = {
        "name": "Used GPU for local inference",
        "brief": "Find an NVIDIA GPU with at least 12GB VRAM for local inference.",
        "hard_filters": {
            "include_keywords": [
                "RTX 3060 12GB RTX 3080 12GB RTX 3080 Ti RTX 3090 RTX A2000 12GB RTX A4000 12GB GPU 16GB GPU 24GB GPU CUDA AI LLM local inference deep learning machine learning NVIDIA"
            ],
            "exclude_keywords": [
                "AMD RX GTX 1060 GTX 1070 GTX 1080 1660 2060 6GB 3060 8GB broken faulty artifact untested for parts mining rig water damaged"
            ],
        },
        "soft_preferences": {},
        "search_config": {"max_queries_per_run": 6, "query_variants_enabled": False, "broadening_enabled": False},
    }

    pack = build_marketplace_search_pack(mission)
    queries = flatten_marketplace_queries(pack, max_queries=6)

    assert "RTX 3060 12GB" in pack["primary_queries"]
    assert "RTX 3090" in pack["primary_queries"]
    assert "GTX 1060" in pack["exclude_terms"]
    assert "untested" in [term.lower() for term in pack["exclude_terms"]]
    assert len(queries) == 6
    assert all(len(query.split()) <= 4 for query in queries)
