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
    assert any("preston" in query.lower() for query in queries)


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


def test_requirement_driven_search_pack_uses_candidate_terms_first() -> None:
    mission = {
        "name": "Inference GPU",
        "brief": "24GB GPU for local inference.",
        "hard_filters": {
            "include_keywords": ["24GB GPU local inference"],
            "location_names": ["Melbourne"],
        },
        "soft_preferences": {},
        "search_config": {"max_queries_per_run": 4},
        "deployment_args": {
            "requirement_profile": {"mode": "requirement_driven", "category": "gpu"},
            "candidate_search_terms": ["RTX 3090 24GB", "RTX 4090 24GB"],
        },
    }

    pack = build_marketplace_search_pack(mission)
    queries = flatten_marketplace_queries(pack, max_queries=4)

    assert pack["primary_queries"][:2] == ["RTX 3090 24GB", "RTX 4090 24GB"]
    assert any("rtx 3090" in query.lower() for query in queries)


def test_requirement_driven_search_queries_anchor_victoria_scope_to_melbourne() -> None:
    mission = {
        "name": "Inference GPU",
        "brief": "24GB GPU for local inference in Victoria.",
        "hard_filters": {
            "include_keywords": ["GPU", "24GB VRAM"],
            "location_names": ["Victoria, Australia"],
        },
        "soft_preferences": {},
        "search_config": {"max_queries_per_run": 4},
        "deployment_args": {
            "requirement_profile": {"mode": "requirement_driven", "category": "gpu"},
            "candidate_search_terms": ["RTX 3090 24GB", "RTX 4090 24GB"],
        },
    }

    pack = build_marketplace_search_pack(mission)
    queries = flatten_marketplace_queries(pack, max_queries=4)

    assert pack["location_scope"]["location_names"] == ["Victoria, Australia"]
    assert any(query == "RTX 3090 24GB Melbourne" for query in queries)
    assert not any("victoria, australia" in query.lower() for query in queries)


def test_requirement_driven_australia_wide_queries_do_not_duplicate_scope_or_brand() -> None:
    mission = {
        "name": "ASUS Pro WS X570-ACE motherboard hunt",
        "brief": "ASUS Pro WS X570-ACE motherboard Australia-wide.",
        "hard_filters": {
            "include_keywords": ["ASUS Pro WS X570-ACE", "X570-ACE"],
            "location_names": ["Australia"],
        },
        "soft_preferences": {"preferred_brands": ["ASUS"]},
        "search_config": {"max_queries_per_run": 8},
        "deployment_args": {
            "requirement_profile": {
                "mode": "requirement_driven",
                "category": "motherboard",
            },
            "candidate_search_terms": [
                "Pro WS X570-ACE AM4 X570",
                "ASUS Pro WS X570-ACE",
                "X570-ACE",
            ],
        },
    }

    pack = build_marketplace_search_pack(mission)
    queries = flatten_marketplace_queries(pack, max_queries=8)

    assert all(not query.lower().endswith(" australia") for query in queries)
    assert not any("asus asus" in query.lower() for query in queries)
    assert "ASUS Pro WS X570-ACE" in queries


def test_requirement_driven_search_pack_fails_closed_without_candidate_terms() -> None:
    mission = {
        "name": "Inference GPU",
        "brief": "24GB GPU for local inference.",
        "hard_filters": {
            "include_keywords": ["24GB GPU local inference"],
            "location_names": ["Melbourne"],
        },
        "soft_preferences": {},
        "search_config": {"max_queries_per_run": 4},
        "deployment_args": {
            "requirement_profile": {"mode": "requirement_driven", "category": "gpu"},
        },
    }

    try:
        build_marketplace_search_pack(mission)
    except ValueError as exc:
        assert "candidate_search_terms" in str(exc)
    else:
        raise AssertionError("requirement-driven search pack should fail closed")


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


def test_build_marketplace_search_pack_uses_preferred_suburbs_for_location_scope() -> None:
    mission = {
        "name": "Used GPU",
        "brief": "Find an NVIDIA GPU.",
        "hard_filters": {
            "include_keywords": ["RTX 3090"],
            "location_names": ["Melbourne"],
        },
        "soft_preferences": {"preferred_suburbs": ["Richmond"]},
        "search_config": {"max_queries_per_run": 6},
    }

    pack = build_marketplace_search_pack(mission)
    queries = flatten_marketplace_queries(pack, max_queries=6)

    assert pack["location_scope"]["location_names"] == ["Melbourne", "Richmond"]
    assert any("melbourne" in query.lower() for query in queries)


def test_build_marketplace_search_pack_extracts_location_clause_from_brief() -> None:
    mission = {
        "name": "Inference GPU",
        "brief": "Locations I want: Melbourne, eastern suburbs, south-east suburbs, nearby metro areas.",
        "hard_filters": {"include_keywords": ["RTX 3090"]},
        "soft_preferences": {},
        "search_config": {"max_queries_per_run": 6, "query_variants_enabled": False, "broadening_enabled": False},
    }

    pack = build_marketplace_search_pack(mission)

    assert pack["location_scope"]["location_names"] == [
        "Melbourne",
        "eastern suburbs",
        "south-east suburbs",
        "nearby metro areas",
    ]
