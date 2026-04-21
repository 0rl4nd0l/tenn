from __future__ import annotations

import hashlib
import re
from typing import Any


_PRICE_RE = re.compile(r"(?:A\$|AU\$|USD\s*\$|\$)\s*([0-9][0-9,]*(?:\.[0-9]{2})?)")
_RESELLER_TERMS = {"dealer", "wholesale", "abn", "gst", "invoice", "reseller"}
_JUNK_TERMS = {"parts", "repair", "wreck", "damaged", "spares", "not working"}
_NEGOTIABLE_TERMS = {"negotiable", "ono", "obo"}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _normalize(value: Any) -> str:
    return _clean_text(value).lower()


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{2,}", text.lower()))


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    elif isinstance(value, str):
        raw_items = re.split(r"[,;\n]", value)
    elif value is None:
        raw_items = []
    else:
        raw_items = [value]
    out: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def parse_marketplace_price(value: Any) -> float | None:
    text = _clean_text(value)
    if not text:
        return None
    match = _PRICE_RE.search(text)
    if match:
        target = match.group(1)
    else:
        fallback = re.search(r"([0-9][0-9,]*(?:\.[0-9]{2})?)", text)
        if fallback is None:
            return None
        target = fallback.group(1)
    try:
        return float(target.replace(",", ""))
    except ValueError:
        return None


def listing_material_hash(payload: dict[str, Any]) -> str:
    text = "\n".join(
        [
            _clean_text(payload.get("title")),
            _clean_text(payload.get("price")),
            _clean_text(payload.get("location")),
            _clean_text(payload.get("seller_name")),
            _clean_text(payload.get("description")),
            " ".join(_string_list(payload.get("raw_text_lines"))),
        ]
    )
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]


def prefilter_marketplace_card(card: dict[str, Any], mission: dict[str, Any]) -> dict[str, Any]:
    hard = mission.get("hard_filters") or {}
    soft = mission.get("soft_preferences") or {}

    title = _clean_text(card.get("title"))
    text = " ".join(
        [
            title,
            _clean_text(card.get("price")),
            _clean_text(card.get("location")),
            " ".join(_string_list(card.get("text_fragments"))),
        ]
    )
    normalized = _normalize(text)
    price_value = parse_marketplace_price(card.get("price"))
    reasons: list[str] = []

    for term in _string_list(hard.get("exclude_keywords")) + _string_list(
        hard.get("forbidden_terms")
    ):
        if term.lower() in normalized:
            return {
                "prefilter_decision": "reject",
                "open_priority": 0,
                "prefilter_reasons": [f"Rejected by excluded term: {term}"],
            }

    if price_value is not None:
        price_min = hard.get("price_min")
        price_max = hard.get("price_max")
        if price_min is not None and price_value < float(price_min):
            return {
                "prefilter_decision": "reject",
                "open_priority": 0,
                "prefilter_reasons": ["Rejected by minimum price filter"],
            }
        if price_max is not None and price_value > float(price_max):
            return {
                "prefilter_decision": "reject",
                "open_priority": 0,
                "prefilter_reasons": ["Rejected by maximum price filter"],
            }

    priority = 40
    include_hits = 0
    for term in _string_list(hard.get("include_keywords")):
        if term.lower() in normalized:
            include_hits += 1
            priority += 14
            reasons.append(f"Include keyword matched: {term}")
    for brand in _string_list(soft.get("preferred_brands")):
        if brand.lower() in normalized:
            priority += 8
            reasons.append(f"Preferred brand matched: {brand}")
            break

    if price_value is not None and hard.get("price_max") is not None:
        if price_value <= float(hard["price_max"]):
            priority += 6
            reasons.append("Price is inside mission cap")
    if _NEGOTIABLE_TERMS & _terms(normalized):
        priority += 4
        reasons.append("Negotiation-friendly language found")
    if (_RESELLER_TERMS | _JUNK_TERMS) & _terms(normalized):
        priority -= 15
        reasons.append("Reseller or junk signals present")

    decision = "open"
    if include_hits == 0 and _string_list(hard.get("include_keywords")):
        priority -= 8
        reasons.append("Missing primary include keywords on the card")
    if priority < 20:
        decision = "reject"

    return {
        "prefilter_decision": decision,
        "open_priority": max(0, min(100, priority)),
        "prefilter_reasons": reasons or ["No hard-filter conflicts on the card"],
    }


def evaluate_marketplace_listing(
    listing: dict[str, Any],
    mission: dict[str, Any],
    *,
    observed_price_band: dict[str, float] | None = None,
) -> dict[str, Any]:
    hard = mission.get("hard_filters") or {}
    soft = mission.get("soft_preferences") or {}
    scan_config = mission.get("scan_config") or {}

    title = _clean_text(listing.get("title"))
    description = _clean_text(listing.get("description"))
    location = _clean_text(listing.get("location"))
    seller_name = _clean_text(listing.get("seller_name"))
    price_text = _clean_text(listing.get("price"))
    raw_text_lines = _string_list(listing.get("raw_text_lines"))
    price_value = parse_marketplace_price(price_text)
    combined = "\n".join([title, description, location, seller_name, " ".join(raw_text_lines)])
    normalized = _normalize(combined)
    tokens = _terms(normalized)

    reasons_for: list[str] = []
    reasons_against: list[str] = []

    def reject(reason: str) -> dict[str, Any]:
        return {
            "eligibility": "reject",
            "score": 0,
            "decision_band": "reject",
            "reasons_for": [],
            "reasons_against": [reason],
            "confidence": 0.9,
        }

    include_keywords = _string_list(hard.get("include_keywords"))
    if include_keywords and not any(term.lower() in normalized for term in include_keywords):
        return reject("Required include keywords were not found")

    for term in _string_list(hard.get("required_terms")):
        if term.lower() not in normalized:
            return reject(f"Required term missing: {term}")

    for term in _string_list(hard.get("exclude_keywords")) + _string_list(
        hard.get("forbidden_terms")
    ):
        if term.lower() in normalized:
            return reject(f"Forbidden term present: {term}")

    if price_value is not None:
        price_min = hard.get("price_min")
        price_max = hard.get("price_max")
        if price_min is not None and price_value < float(price_min):
            return reject("Listing price is below the allowed minimum")
        if price_max is not None and price_value > float(price_max):
            return reject("Listing price is above the allowed maximum")

    required_conditions = _string_list(hard.get("condition_required"))
    if required_conditions and not any(term.lower() in normalized for term in required_conditions):
        return reject("Required condition terms were not found")

    location_names = _string_list(hard.get("location_names"))
    if location_names and location:
        if not any(term.lower() in location.lower() for term in location_names):
            return reject("Listing location is outside the allowed mission area")

    score = 58
    confidence = 0.45

    for term in include_keywords:
        if term.lower() in normalized:
            score += 10
            confidence += 0.04
            reasons_for.append(f"Matched mission keyword: {term}")

    for brand in _string_list(soft.get("preferred_brands")):
        if brand.lower() in normalized:
            score += 8
            confidence += 0.04
            reasons_for.append(f"Preferred brand matched: {brand}")
            break

    for term in _string_list(soft.get("nice_to_have_terms")):
        if term.lower() in normalized:
            score += 4
            confidence += 0.02
            reasons_for.append(f"Nice-to-have term matched: {term}")

    for term in _string_list(soft.get("preferred_condition_terms")):
        if term.lower() in normalized:
            score += 5
            confidence += 0.03
            reasons_for.append(f"Preferred condition signal found: {term}")

    if location and any(
        suburb.lower() in location.lower()
        for suburb in _string_list(soft.get("preferred_suburbs"))
    ):
        score += 5
        reasons_for.append("Preferred suburb matched")

    if price_value is not None:
        mission_cap = hard.get("price_max")
        if observed_price_band and observed_price_band.get("median"):
            median_price = float(observed_price_band["median"])
            if price_value <= median_price * 0.85:
                score += 15
                reasons_for.append("Well below the observed local median")
            elif price_value <= median_price:
                score += 8
                reasons_for.append("Below the observed local median")
            elif price_value > median_price * 1.15:
                score -= 10
                reasons_against.append("Above the observed local median")
        elif mission_cap is not None:
            mission_cap = float(mission_cap)
            if price_value <= mission_cap * 0.85:
                score += 10
                reasons_for.append("Comfortably below the mission price cap")
            elif price_value <= mission_cap:
                score += 5
                reasons_for.append("Within the mission price cap")

    if _NEGOTIABLE_TERMS & tokens and bool(soft.get("negotiation_expected")):
        score += 4
        reasons_for.append("Negotiation language supports the mission")

    junk_hits = sorted((_JUNK_TERMS & tokens))
    if junk_hits:
        score -= 30
        reasons_against.append(
            f"Parts/repair risk signals present: {', '.join(junk_hits[:3])}"
        )

    reseller_hits = sorted((_RESELLER_TERMS & tokens))
    if reseller_hits:
        score -= 18
        reasons_against.append(
            f"Reseller/dealer signals present: {', '.join(reseller_hits[:3])}"
        )

    if "kms" in tokens or "kilometres" in tokens or "kilometers" in tokens:
        reasons_against.append("Mileage should be checked manually")

    candidate_threshold = int(scan_config.get("candidate_threshold") or 70)
    strong_threshold = int(scan_config.get("strong_match_threshold") or 85)
    score = max(0, min(100, score))
    confidence = max(0.2, min(0.95, confidence))

    if score >= strong_threshold:
        band = "strong_match"
    elif score >= candidate_threshold:
        band = "candidate"
    else:
        band = "reject"

    return {
        "eligibility": "pass" if band != "reject" else "reject",
        "score": score,
        "decision_band": band,
        "reasons_for": reasons_for or ["No hard-filter conflicts found"],
        "reasons_against": reasons_against,
        "confidence": round(confidence, 2),
    }


def material_change_reasons(
    previous_seen: dict[str, Any] | None,
    *,
    new_hash: str,
    new_price_value: float | None,
    new_score: int,
    new_band: str,
) -> list[str]:
    if previous_seen is None:
        return ["new_listing"]

    reasons: list[str] = []
    old_hash = _clean_text(previous_seen.get("detail_hash"))
    old_price = previous_seen.get("price_value")
    old_score = previous_seen.get("last_score")
    old_band = _clean_text(previous_seen.get("last_decision_band"))

    if old_hash and old_hash != new_hash:
        reasons.append("listing_text_changed")
    if (
        old_price is not None
        and new_price_value is not None
        and float(old_price) != float(new_price_value)
    ):
        reasons.append("price_changed")
    if old_band != new_band and new_band == "strong_match":
        reasons.append("crossed_into_strong_match")
    if old_score is not None and new_score > int(old_score) + 7:
        reasons.append("score_improved")
    return reasons
