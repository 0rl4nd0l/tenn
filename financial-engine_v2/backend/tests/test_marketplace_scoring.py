from __future__ import annotations

from app.services.marketplace_scoring import (
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
