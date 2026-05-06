from __future__ import annotations

from app.services.marketplace_requirement_resolver import (
    build_requirement_profile,
    candidate_search_terms,
    generate_requirement_candidate_specs,
)


def test_requirement_resolver_classifies_24gb_inference_gpu_request() -> None:
    profile = build_requirement_profile(
        {
            "name": "Inference GPU",
            "brief": "24GB GPU for local inference around Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
            "soft_preferences": {},
        }
    )

    assert profile["mode"] == "requirement_driven"
    assert profile["category"] == "gpu"
    assert profile["intended_use"] == "local_inference"
    assert profile["hard_constraints"] == [
        {
            "field": "vram_gb",
            "operator": ">=",
            "value": 24,
            "unit": "GB",
            "source": "brief",
        }
    ]


def test_requirement_resolver_keeps_plain_exact_gpu_request_exact() -> None:
    profile = build_requirement_profile(
        {
            "name": "4070 Super",
            "brief": "Find RTX 4070 Super 12GB listings in Melbourne.",
            "category_hint": "gpu",
            "hard_filters": {"include_keywords": ["RTX 4070 Super"], "location_names": ["Melbourne"]},
            "soft_preferences": {},
        }
    )

    assert profile["mode"] == "exact_product"
    assert profile["exact_product_hint"].lower() == "rtx 4070 super"


def test_requirement_resolver_classifies_storage_hunt_as_requirement_driven() -> None:
    profile = build_requirement_profile(
        {
            "name": "2TB-4TB Gen4 NVMe storage hunt",
            "brief": "Find 2TB Gen4 NVMe SSD deals in Melbourne.",
            "category_hint": "ssd",
            "hard_filters": {
                "include_keywords": ["2TB", "Gen4", "NVMe", "SSD"],
                "location_names": ["Melbourne"],
            },
            "soft_preferences": {},
        }
    )

    assert profile["mode"] == "requirement_driven"
    candidates = generate_requirement_candidate_specs(profile)
    candidate_keys = {candidate["canonical_key"] for candidate in candidates}
    assert "ssd-kingston-nv2-4tb-gen4" in candidate_keys
    assert "ssd-samsung-990-pro-4tb-gen4" in candidate_keys
    assert any(candidate["attributes"]["capacity_gb"] == 4000 for candidate in candidates)
    assert candidates[0]["attributes"]["capacity_gb"] >= 4000
    terms = candidate_search_terms(candidates)
    assert any("4TB" in term for term in terms)
    assert any("2TB" in term for term in terms)


def test_requirement_resolver_classifies_am4_cpu_trigger_as_requirement_driven() -> None:
    profile = build_requirement_profile(
        {
            "name": "Ryzen 9 AM4 CPU trigger",
            "brief": "Watch for Ryzen 9 AM4 CPU deals.",
            "category_hint": "cpu",
            "hard_filters": {
                "include_keywords": ["Ryzen 9", "AM4"],
                "location_names": ["Melbourne"],
            },
            "soft_preferences": {},
        }
    )

    assert profile["mode"] == "requirement_driven"
    candidates = generate_requirement_candidate_specs(profile)
    candidate_keys = {candidate["canonical_key"] for candidate in candidates}
    assert "cpu-amd-ryzen-9-5950x-am4" in candidate_keys
    assert "cpu-amd-ryzen-9-5900x-am4" in candidate_keys


def test_requirement_candidate_generation_is_bounded_and_excludes_12gb_mismatch() -> None:
    profile = build_requirement_profile(
        {
            "name": "Inference GPU",
            "brief": "Need a 24GB GPU for local inference.",
            "category_hint": "gpu",
            "hard_filters": {"location_names": ["Melbourne"]},
            "soft_preferences": {},
        }
    )

    candidates = generate_requirement_candidate_specs(profile)

    assert 1 <= len(candidates) <= 5
    assert [candidate["canonical_key"] for candidate in candidates] == [
        "gpu-nvidia-rtx-3090-24gb",
        "gpu-nvidia-rtx-3090-ti-24gb",
        "gpu-nvidia-rtx-4090-24gb",
    ]
    assert all(candidate["attributes"]["vram_gb"] >= 24 for candidate in candidates)
    assert "gpu-nvidia-rtx-4070-ti-super-16gb" not in {
        candidate["canonical_key"] for candidate in candidates
    }

    terms = candidate_search_terms(candidates)
    assert "RTX 3090 24GB" in terms
    assert "RTX 4090 24GB" in terms
