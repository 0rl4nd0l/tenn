from __future__ import annotations

from app.services.marketplace_scoring import (
    classify_requirement_detail_outcome,
    evaluate_marketplace_listing,
    material_change_reasons,
    prefilter_marketplace_card,
)


def _mission() -> dict:
    return {
        "hard_filters": {
            "include_keywords": ["4x4", "dual cab"],
            "exclude_keywords": ["wrecking"],
            "price_max": 25000,
            "forbidden_terms": ["stat write-off"],
            "location_names": ["Preston VIC"],
        },
        "soft_preferences": {
            "preferred_brands": ["Toyota"],
            "preferred_condition_terms": ["service history"],
            "nice_to_have_terms": ["canopy"],
            "negotiation_expected": True,
        },
        "scan_config": {
            "strong_match_threshold": 85,
            "candidate_threshold": 70,
            "aggressive_alerting": False,
        },
    }


def _requirement_gpu_mission() -> dict:
    return {
        "category_hint": "gpu",
        "hard_filters": {
            "include_keywords": ["24GB GPU local inference"],
            "location_names": ["Melbourne"],
            "price_max": 1000,
        },
        "soft_preferences": {},
        "deployment_args": {
            "requirement_profile": {
                "mode": "requirement_driven",
                "category": "gpu",
                "hard_constraints": [
                    {
                        "field": "vram_gb",
                        "operator": ">=",
                        "value": 24,
                        "unit": "GB",
                    }
                ],
            },
            "candidate_search_terms": [
                "RTX 3090 24GB",
                "RTX 3090",
                "RTX 3090 Ti 24GB",
                "RTX 4090 24GB",
            ],
        },
        "scan_config": {
            "strong_match_threshold": 85,
            "candidate_threshold": 70,
            "aggressive_alerting": False,
        },
    }


def test_prefilter_marketplace_card_rejects_forbidden_term() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "Toyota Hilux dual cab",
            "price": "$21,000",
            "location": "Preston VIC",
            "text_fragments": ["stat write-off"],
        },
        _mission(),
    )

    assert result["prefilter_decision"] == "reject"


def test_prefilter_requirement_card_opens_on_strong_candidate_model_evidence() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "RTX 3090",
            "price": "$900",
            "location": "Melbourne",
            "text_fragments": ["RTX 3090", "$900"],
        },
        _requirement_gpu_mission(),
    )

    assert result["prefilter_decision"] == "open"
    assert result["open_priority"] >= 70
    assert any("Strong requirement candidate" in reason for reason in result["prefilter_reasons"])
    assert any("Detailed requirement proof deferred" in reason for reason in result["prefilter_reasons"])


def test_prefilter_requirement_card_softens_weak_candidate_location() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "NVIDIA 3090",
            "price": "$900",
            "location": "Victoria",
            "text_fragments": ["NVIDIA 3090", "$900", "Victoria"],
        },
        _requirement_gpu_mission(),
    )

    assert result["prefilter_decision"] == "open"
    assert any("Location evidence is weak" in reason for reason in result["prefilter_reasons"])


def test_prefilter_requirement_card_keeps_obvious_junk_rejected() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "WTB RTX 3090 box only swap",
            "price": "$1",
            "location": "Melbourne",
            "text_fragments": ["wanted", "swap", "box only"],
        },
        _requirement_gpu_mission(),
    )

    assert result["prefilter_decision"] == "reject"
    assert result["prefilter_reasons"][0].startswith("Rejected by obvious junk")


def test_prefilter_exact_product_still_rejects_outside_location() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "RTX 4070 Super",
            "price": "$700",
            "location": "Victoria",
            "text_fragments": ["RTX 4070 Super", "$700", "Victoria"],
        },
        {
            **_requirement_gpu_mission(),
            "hard_filters": {
                **_requirement_gpu_mission()["hard_filters"],
                "include_keywords": ["RTX 4070 Super"],
            },
            "deployment_args": {
                "requirement_profile": {
                    "mode": "exact_product",
                    "category": "gpu",
                    "exact_product_hint": "RTX 4070 Super",
                },
            },
        },
    )

    assert result["prefilter_decision"] == "reject"
    assert result["prefilter_reasons"] == ["Rejected by location filter"]


def test_prefilter_marketplace_card_rejects_outside_location() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "Toyota Hilux dual cab",
            "price": "$21,000",
            "location": "San Francisco, CA",
            "text_fragments": ["Toyota", "dual cab", "4x4"],
        },
        _mission(),
    )

    assert result["prefilter_decision"] == "reject"
    assert result["prefilter_reasons"] == ["Rejected by location filter"]


def test_prefilter_marketplace_card_allows_missing_location_when_scope_required() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "Toyota Hilux dual cab",
            "price": "$21,000",
            "location": None,
            "text_fragments": ["Toyota", "dual cab", "4x4"],
        },
        _mission(),
    )

    assert result["prefilter_decision"] == "open"


def test_prefilter_marketplace_card_allows_distance_only_location_when_scope_required() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "Nvidia GPU",
            "price": "$500",
            "location": "22 km away",
            "text_fragments": ["Nvidia GPU", "$500", "22 km away"],
        },
        {
            **_mission(),
            "hard_filters": {
                **_mission()["hard_filters"],
                "include_keywords": ["GPU"],
                "location_names": ["Victoria, Australia"],
                "price_max": 700,
            },
        },
    )

    assert result["prefilter_decision"] == "open"


def test_prefilter_marketplace_card_rejects_bc_when_scope_is_victoria_au() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "Nvidia GPU",
            "price": "$150",
            "location": "Victoria, BC",
            "text_fragments": ["Nvidia GPU", "Victoria, BC"],
        },
        _mission(),
    )

    assert result["prefilter_decision"] == "reject"
    assert result["prefilter_reasons"] == ["Rejected by location filter"]


def test_prefilter_marketplace_card_rejects_foreign_signal_in_title_when_location_missing() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "3060ti GPU, $180, Walnut Creek, CA",
            "price": "$180",
            "location": None,
            "text_fragments": ["3060ti GPU", "$180", "Walnut Creek, CA"],
        },
        _mission(),
    )

    assert result["prefilter_decision"] == "reject"
    assert result["prefilter_reasons"] == ["Rejected by location filter"]


def test_prefilter_marketplace_card_rejects_full_california_name_for_au_scope() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "No GPU 5950x PC",
            "price": "$580",
            "location": "Fairfield, California",
            "text_fragments": ["No GPU 5950x PC", "$580", "Fairfield, California"],
        },
        {
            **_mission(),
            "hard_filters": {
                **_mission()["hard_filters"],
                "include_keywords": ["GPU"],
                "location_names": ["Victoria, Australia"],
                "price_max": 700,
            },
        },
    )

    assert result["prefilter_decision"] == "reject"
    assert result["prefilter_reasons"] == ["Rejected by location filter"]


def test_prefilter_marketplace_card_allows_matching_location() -> None:
    result = prefilter_marketplace_card(
        {
            "title": "Toyota Hilux dual cab",
            "price": "$21,000",
            "location": "Preston VIC",
            "text_fragments": ["Toyota", "dual cab", "4x4"],
        },
        _mission(),
    )

    assert result["prefilter_decision"] == "open"


def test_evaluate_marketplace_listing_allows_weak_approximate_location() -> None:
    result = evaluate_marketplace_listing(
        {
            "title": "Toyota Hilux dual cab 4x4",
            "price": "$21,000",
            "location": "Location is approximate",
            "description": "Toyota Hilux dual cab with 4x4 and service history.",
            "raw_text_lines": ["Location is approximate"],
        },
        _mission(),
    )

    assert result["eligibility"] != "reject"
    assert (
        "Listing location is outside the allowed mission area"
        not in result["reasons_against"]
    )


def test_evaluate_marketplace_listing_still_rejects_clear_foreign_location() -> None:
    result = evaluate_marketplace_listing(
        {
            "title": "Toyota Hilux dual cab 4x4",
            "price": "$21,000",
            "location": "Vancouver, BC, Canada",
            "description": "Toyota Hilux dual cab with 4x4.",
            "raw_text_lines": ["Vancouver, BC, Canada"],
        },
        _mission(),
    )

    assert result["eligibility"] == "reject"
    assert result["reasons_against"] == [
        "Listing location is outside the allowed mission area"
    ]


def test_classify_requirement_detail_outcome_wrong_vram() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA RTX 3080 Ti 12GB",
            "price": "$650",
            "location": "Melbourne",
            "description": "Good working 12GB GPU with 32GB system RAM.",
            "raw_text_lines": ["RTX 3080 Ti 12GB", "32GB system RAM"],
        },
        _requirement_gpu_mission(),
        {"decision_band": "reject", "score": 63, "reasons_against": []},
    )

    assert outcome["reason_code"] == "detail_wrong_vram"
    assert outcome["evidence"]["required_vram_gb"] == 24
    assert outcome["evidence"]["listing_vram_gb"] == 12


def test_classify_requirement_detail_outcome_location_failed() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "location": "Vancouver, BC, Canada",
            "description": "Working GPU.",
            "raw_text_lines": ["RTX 3090 24GB"],
        },
        _requirement_gpu_mission(),
        {
            "decision_band": "reject",
            "score": 0,
            "reasons_against": [
                "Listing location is outside the allowed mission area"
            ],
        },
    )

    assert outcome["reason_code"] == "detail_location_failed"


def test_classify_requirement_detail_outcome_weak_location_is_insufficient_evidence() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$900",
            "location": "Location is approximate",
            "description": "Working GPU.",
            "raw_text_lines": ["RTX 3090 24GB", "Location is approximate"],
        },
        _requirement_gpu_mission(),
        {
            "decision_band": "reject",
            "score": 0,
            "reasons_against": [
                "Listing location is outside the allowed mission area"
            ],
        },
    )

    assert outcome["reason_code"] == "detail_insufficient_evidence"


def test_classify_requirement_detail_outcome_price_failed() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA RTX 3090 24GB",
            "price": "$2,000",
            "location": "Melbourne",
            "description": "Working GPU.",
            "raw_text_lines": ["RTX 3090 24GB"],
        },
        _requirement_gpu_mission(),
        {
            "decision_band": "reject",
            "score": 0,
            "reasons_against": ["Listing price is above the allowed maximum"],
        },
    )

    assert outcome["reason_code"] == "detail_price_failed"


def test_classify_requirement_detail_outcome_wrong_model() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA RTX 3060 Ti",
            "price": "$350",
            "location": "Melbourne",
            "description": "Working GPU.",
            "raw_text_lines": ["RTX 3060 Ti"],
        },
        _requirement_gpu_mission(),
        {"decision_band": "reject", "score": 63, "reasons_against": []},
    )

    assert outcome["reason_code"] == "detail_wrong_model"


def test_classify_requirement_detail_outcome_parts_or_condition() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA RTX 3090",
            "price": "$500",
            "location": "Melbourne",
            "description": "Not working, for parts only.",
            "raw_text_lines": ["for parts only"],
        },
        _requirement_gpu_mission(),
        {
            "decision_band": "reject",
            "score": 33,
            "reasons_against": ["Parts/repair risk signals present: parts"],
        },
    )

    assert outcome["reason_code"] == "detail_parts_or_condition_failed"


def test_classify_requirement_detail_outcome_insufficient_evidence() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA graphics card",
            "price": "$600",
            "location": "Melbourne",
            "description": "Working GPU, exact specs unknown.",
            "raw_text_lines": ["working GPU"],
        },
        _requirement_gpu_mission(),
        {"decision_band": "reject", "score": 63, "reasons_against": []},
    )

    assert outcome["reason_code"] == "detail_insufficient_evidence"


def test_classify_requirement_detail_outcome_exact_product_returns_none() -> None:
    outcome = classify_requirement_detail_outcome(
        {
            "title": "NVIDIA RTX 4070 Super",
            "price": "$700",
            "location": "Melbourne",
            "description": "Working GPU.",
            "raw_text_lines": ["RTX 4070 Super"],
        },
        {
            **_requirement_gpu_mission(),
            "deployment_args": {
                "requirement_profile": {
                    "mode": "exact_product",
                    "category": "gpu",
                    "exact_product_hint": "RTX 4070 Super",
                }
            },
        },
        {"decision_band": "reject", "score": 63, "reasons_against": []},
    )

    assert outcome is None


def test_evaluate_marketplace_listing_returns_strong_match() -> None:
    result = evaluate_marketplace_listing(
        {
            "title": "2014 Toyota Hilux dual cab 4x4",
            "price": "$21,500",
            "location": "Preston VIC",
            "seller_name": "Seller A",
            "description": "Full service history, canopy, negotiable.",
            "raw_text_lines": ["Toyota", "dual cab", "4x4", "service history"],
        },
        _mission(),
        observed_price_band={"min": 21000, "median": 24000, "max": 29000},
    )

    assert result["decision_band"] == "strong_match"
    assert result["eligibility"] == "pass"
    assert result["score"] >= 85


def test_evaluate_marketplace_listing_allows_distance_only_location() -> None:
    result = evaluate_marketplace_listing(
        {
            "title": "Nvidia GPU for local AI",
            "price": "$500",
            "location": "22 km away",
            "seller_name": "Seller A",
            "description": "Good working GPU, negotiable.",
            "raw_text_lines": ["Nvidia GPU", "$500", "22 km away"],
        },
        {
            **_mission(),
            "hard_filters": {
                **_mission()["hard_filters"],
                "include_keywords": ["GPU"],
                "location_names": ["Victoria, Australia"],
                "price_max": 700,
            },
        },
    )

    assert result["decision_band"] == "candidate"
    assert result["eligibility"] == "pass"


def test_material_change_reasons_detect_price_change() -> None:
    reasons = material_change_reasons(
        {
            "detail_hash": "abc",
            "price_value": 180.0,
            "last_score": 70,
            "last_decision_band": "candidate",
        },
        new_hash="def",
        new_price_value=150.0,
        new_score=88,
        new_band="strong_match",
    )

    assert "price_changed" in reasons
    assert "crossed_into_strong_match" in reasons
