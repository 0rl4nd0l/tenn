from __future__ import annotations

import hashlib
import re
from typing import Any


_PRICE_RE = re.compile(r"(?:A\$|AU\$|USD\s*\$|\$)\s*([0-9][0-9,]*(?:\.[0-9]{2})?)")
_RESELLER_TERMS = {"dealer", "wholesale", "abn", "gst", "invoice", "reseller"}
_JUNK_TERMS = {"parts", "repair", "wreck", "damaged", "spares", "not working"}
_NEGOTIABLE_TERMS = {"negotiable", "ono", "obo"}
_OBVIOUS_JUNK_PATTERNS: tuple[tuple[str, str], ...] = (
    ("wanted/WTB", r"\b(wanted|wtb|want to buy|looking for)\b"),
    ("swap/trade", r"\b(swap only|trade only|swap|swapping|trade for)\b"),
    (
        "broken/parts",
        r"\b(broken|faulty|for parts|parts only|not working|dead gpu|dead cpu|repair)\b",
    ),
    (
        "box/accessory only",
        r"\b(box only|empty box|packaging only|accessory only|bracket only|cable only|waterblock only)\b",
    ),
    ("wrong category", r"\b(full pc|gaming pc|complete pc|whole setup|desktop pc)\b"),
)
_AU_SCOPE_HINTS = {
    "australia",
    "victoria",
    "new south wales",
    "queensland",
    "south australia",
    "western australia",
    "tasmania",
    "australian capital territory",
    "northern territory",
}
_STATE_ALIAS_PATTERNS: dict[str, str] = {
    "victoria": r"\b(victoria|vic)\b",
    "new south wales": r"\b(new south wales|nsw)\b",
    "queensland": r"\b(queensland|qld)\b",
    "south australia": r"\b(south australia|sa)\b",
    "western australia": r"\b(western australia|wa)\b",
    "tasmania": r"\b(tasmania|tas)\b",
    "australian capital territory": r"\b(australian capital territory|act)\b",
    "northern territory": r"\b(northern territory|nt)\b",
}
_FOREIGN_LOCATION_PATTERNS = (
    r"\bbritish columbia\b",
    r"\bcanada\b",
    r"\busa\b",
    r"\bunited states\b",
    r",\s*bc\b",
    r",\s*ca\b",
    r",\s*california\b",
)
_DISTANCE_ONLY_LOCATION_RE = re.compile(
    r"^\s*(?:less than\s+)?\d+(?:\.\d+)?\s*(?:km|kilomet(?:er|re)s?|mi|mile)s?\s*(?:away)?\s*$",
    re.IGNORECASE,
)
_WEAK_LOCATION_PATTERNS = (
    r"\blocation\s+is\s+approximate\b",
    r"\bapproximate\s+location\b",
    r"\blocation\s+approximate\b",
    r"\bapprox(?:\.|imate)?\s+location\b",
)
_GPU_MODEL_RE = re.compile(
    r"\b(?:nvidia\s+|geforce\s+)?(?:rtx|gtx)\s*[2345]0[0-9]{2}(?:\s*(?:ti|super))?\b"
    r"|\b(?:amd\s+|radeon\s+)?rx\s*[5679][0-9]{3}(?:\s*(?:xtx|xt))?\b",
    re.IGNORECASE,
)
_CITY_STATE_HINTS: dict[str, str] = {
    "melbourne": "victoria",
    "geelong": "victoria",
    "sydney": "new south wales",
    "newcastle": "new south wales",
    "brisbane": "queensland",
    "gold coast": "queensland",
    "adelaide": "south australia",
    "perth": "western australia",
    "hobart": "tasmania",
    "canberra": "australian capital territory",
    "darwin": "northern territory",
}


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


def _is_australia_scoped(location_names: list[str]) -> bool:
    for name in location_names:
        lowered = name.lower()
        if any(hint in lowered for hint in _AU_SCOPE_HINTS):
            return True
        if re.search(r"\b(vic|nsw|qld|sa|wa|tas|act|nt)\b", lowered):
            return True
    return False


def _weak_location_evidence(card_location: str) -> bool:
    location = _normalize(card_location)
    if not location:
        return True
    if _DISTANCE_ONLY_LOCATION_RE.match(location):
        return True
    return any(re.search(pattern, location) for pattern in _WEAK_LOCATION_PATTERNS)


def _location_matches_scope(card_location: str, location_names: list[str]) -> bool:
    if not location_names:
        return True
    location = _normalize(card_location)
    if _weak_location_evidence(location):
        return True

    is_au_scope = _is_australia_scoped(location_names)
    if is_au_scope and any(re.search(pattern, location) for pattern in _FOREIGN_LOCATION_PATTERNS):
        return False

    for name in location_names:
        target = _normalize(name)
        if not target or target == "australia":
            continue
        if target in location:
            return True
        for scope, pattern in _STATE_ALIAS_PATTERNS.items():
            if scope in target and re.search(pattern, location):
                return True

    if is_au_scope and re.search(r"\b(australia|au|vic|nsw|qld|sa|wa|tas|act|nt)\b", location):
        return True
    return False


def _requirement_profile(mission: dict[str, Any]) -> dict[str, Any] | None:
    profile = mission.get("requirement_profile")
    if isinstance(profile, dict):
        return profile
    deployment_args = mission.get("deployment_args")
    if isinstance(deployment_args, dict) and isinstance(
        deployment_args.get("requirement_profile"),
        dict,
    ):
        return deployment_args["requirement_profile"]
    return None


def _is_requirement_driven_mission(mission: dict[str, Any]) -> bool:
    profile = _requirement_profile(mission)
    return isinstance(profile, dict) and profile.get("mode") == "requirement_driven"


def _requirement_category(mission: dict[str, Any]) -> str:
    profile = _requirement_profile(mission)
    if isinstance(profile, dict):
        return _normalize(profile.get("category"))
    return _normalize(mission.get("category_hint"))


def _candidate_identity_values(mission: dict[str, Any]) -> list[str]:
    out: list[str] = []
    deployment_args = mission.get("deployment_args")
    if isinstance(deployment_args, dict):
        out.extend(_string_list(deployment_args.get("candidate_search_terms")))

    contexts = mission.get("_requirement_candidate_contexts")
    if isinstance(contexts, list):
        for context in contexts:
            if not isinstance(context, dict):
                continue
            product = context.get("tracked_product")
            candidate = context.get("candidate")
            for payload in [product, candidate]:
                if not isinstance(payload, dict):
                    continue
                model_family = _clean_text(payload.get("model_family"))
                variant = _clean_text(payload.get("variant"))
                if model_family:
                    out.append(model_family)
                if model_family and variant:
                    out.append(f"{model_family} {variant}")
                out.extend(_string_list(payload.get("aliases")))
    return _string_list(out)


def _candidate_variants(term: str, category: str) -> list[str]:
    cleaned = _clean_text(term)
    if not cleaned:
        return []
    variants = [cleaned]
    without_capacity = re.sub(r"\b\d{1,3}\s*gb\b", "", cleaned, flags=re.IGNORECASE)
    if _clean_text(without_capacity):
        variants.append(_clean_text(without_capacity))

    if category == "gpu":
        for match in re.finditer(
            r"\b(?P<prefix>rtx|gtx)\s*(?P<model>[2345]0[0-9]{2})(?:\s*(?P<suffix>ti|super))?\b",
            cleaned,
            re.IGNORECASE,
        ):
            prefix = match.group("prefix").upper()
            model = match.group("model")
            suffix = _clean_text(match.group("suffix")).upper()
            model_phrase = f"{prefix} {model}" + (f" {suffix}" if suffix else "")
            variants.extend([model_phrase, model])
            if suffix:
                variants.append(f"{model} {suffix}")
        for match in re.finditer(
            r"\brx\s*(?P<model>[5679][0-9]{3})(?:\s*(?P<suffix>xtx|xt))?\b",
            cleaned,
            re.IGNORECASE,
        ):
            model = match.group("model")
            suffix = _clean_text(match.group("suffix")).upper()
            variants.append(f"RX {model}" + (f" {suffix}" if suffix else ""))
            variants.append(model)

    return _string_list(variants)


def _phrase_matches_text(phrase: str, normalized_text: str) -> bool:
    tokens = re.findall(r"[a-z0-9]+", phrase.lower())
    if not tokens:
        return False
    pattern = r"\b" + r"[\s\-_]*".join(re.escape(token) for token in tokens) + r"\b"
    return bool(re.search(pattern, normalized_text))


def _strong_candidate_model_evidence(
    normalized_text: str,
    mission: dict[str, Any],
) -> str | None:
    category = _requirement_category(mission)
    for term in _candidate_identity_values(mission):
        for variant in _candidate_variants(term, category):
            variant_tokens = re.findall(r"[a-z0-9]+", variant.lower())
            if not any(any(ch.isdigit() for ch in token) for token in variant_tokens):
                continue
            numeric_only = len(variant_tokens) == 1 and variant_tokens[0].isdigit()
            if numeric_only and category != "gpu":
                continue
            if _phrase_matches_text(variant, normalized_text):
                return variant
    return None


def _location_states(value: str) -> set[str]:
    lowered = _normalize(value)
    states: set[str] = set()
    for state, pattern in _STATE_ALIAS_PATTERNS.items():
        if state in lowered or re.search(pattern, lowered):
            states.add(state)
    for city, state in _CITY_STATE_HINTS.items():
        if re.search(rf"\b{re.escape(city)}\b", lowered):
            states.add(state)
    return states


def _clear_location_conflict(
    normalized_text: str,
    card_location: str,
    location_names: list[str],
) -> bool:
    if any(re.search(pattern, normalized_text) for pattern in _FOREIGN_LOCATION_PATTERNS):
        return True
    location = _normalize(card_location)
    if not location or _DISTANCE_ONLY_LOCATION_RE.match(location):
        return False
    if _location_matches_scope(location, location_names):
        return False
    mission_states: set[str] = set()
    for name in location_names:
        mission_states.update(_location_states(name))
    location_states = _location_states(location)
    return bool(mission_states and location_states and not mission_states.intersection(location_states))


def _obvious_requirement_junk_reason(
    normalized_text: str,
    price_value: float | None,
    mission: dict[str, Any],
) -> str | None:
    hard = mission.get("hard_filters") or {}
    allow_broken = bool(
        hard.get("allow_broken")
        or hard.get("allow_parts")
        or hard.get("allow_parts_or_repair")
    )
    for label, pattern in _OBVIOUS_JUNK_PATTERNS:
        if label == "broken/parts" and allow_broken:
            continue
        if re.search(pattern, normalized_text):
            return label
    if price_value is not None and price_value <= 5:
        return "placeholder price"
    return None


def _minimum_requirement_value(mission: dict[str, Any], field: str) -> float | None:
    profile = _requirement_profile(mission)
    if not isinstance(profile, dict):
        return None
    for constraint in profile.get("hard_constraints") or []:
        if not isinstance(constraint, dict):
            continue
        if str(constraint.get("field") or "") != field:
            continue
        operator = str(constraint.get("operator") or "").strip()
        if operator not in {">=", ">", "="}:
            continue
        try:
            return float(constraint.get("value"))
        except (TypeError, ValueError):
            return None
    return None


def _explicit_gpu_vram_gb(normalized_text: str) -> int | None:
    contextual_values: list[int] = []
    fallback_values: list[int] = []
    for match in re.finditer(r"\b(\d{1,2})\s*gb\b", normalized_text):
        value = int(match.group(1))
        window = normalized_text[
            max(0, match.start() - 32) : min(len(normalized_text), match.end() + 32)
        ]
        if re.search(r"\b(system\s+ram|ddr[345]|memory\s+kit)\b", window):
            continue
        fallback_values.append(value)
        if re.search(
            r"\b(vram|gpu|graphics|gddr|card|rtx|gtx|radeon|rx)\b",
            window,
        ):
            contextual_values.append(value)
    if contextual_values:
        return max(contextual_values)
    if not fallback_values:
        return None
    return min(fallback_values)


def _detail_reason(
    reason_code: str,
    reason_detail: str,
    *,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "stage": "detail",
        "reason_code": reason_code,
        "reason_detail": reason_detail,
        "evidence": evidence or {},
    }


def classify_requirement_detail_outcome(
    listing: dict[str, Any],
    mission: dict[str, Any],
    score: dict[str, Any],
    *,
    candidate_contexts: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    """Classify requirement-driven detail rejects without changing save eligibility."""

    if not _is_requirement_driven_mission(mission):
        return None

    classifier_mission = (
        {**mission, "_requirement_candidate_contexts": candidate_contexts}
        if candidate_contexts is not None
        else mission
    )
    title = _clean_text(listing.get("title"))
    description = _clean_text(listing.get("description"))
    location = _clean_text(listing.get("location"))
    raw_text_lines = _string_list(listing.get("raw_text_lines"))
    combined = "\n".join([title, description, location, " ".join(raw_text_lines)])
    normalized = _normalize(combined)
    price_value = parse_marketplace_price(listing.get("price"))
    reasons_against = _string_list(score.get("reasons_against"))
    reasons_text = " ".join(reasons_against).lower()

    if "location" in reasons_text or "mission area" in reasons_text:
        if _weak_location_evidence(location):
            return _detail_reason(
                "detail_insufficient_evidence",
                "Detail page has only weak or approximate location evidence.",
                evidence={"reasons_against": reasons_against, "location": location},
            )
        return _detail_reason(
            "detail_location_failed",
            "Detail page location evidence is outside the allowed mission area.",
            evidence={"reasons_against": reasons_against, "location": location},
        )

    if "price" in reasons_text or "allowed minimum" in reasons_text or "allowed maximum" in reasons_text:
        return _detail_reason(
            "detail_price_failed",
            "Detail page price failed the mission price constraints.",
            evidence={"reasons_against": reasons_against, "price": listing.get("price")},
        )

    junk_reason = _obvious_requirement_junk_reason(normalized, price_value, classifier_mission)
    if junk_reason == "placeholder price":
        return _detail_reason(
            "detail_price_failed",
            "Detail page price looked like a placeholder.",
            evidence={"price": listing.get("price")},
        )
    if junk_reason:
        return _detail_reason(
            "detail_parts_or_condition_failed",
            "Detail page contains disallowed condition, parts-only, accessory-only, or junk signals.",
            evidence={"junk_reason": junk_reason},
        )

    category = _requirement_category(classifier_mission)
    strong_candidate = _strong_candidate_model_evidence(normalized, classifier_mission)
    if category == "gpu":
        required_vram = _minimum_requirement_value(classifier_mission, "vram_gb")
        listing_vram = _explicit_gpu_vram_gb(normalized)
        if (
            required_vram is not None
            and listing_vram is not None
            and float(listing_vram) < float(required_vram)
        ):
            return _detail_reason(
                "detail_wrong_vram",
                "Detail page shows less VRAM than the requirement allows.",
                evidence={
                    "required_vram_gb": required_vram,
                    "listing_vram_gb": listing_vram,
                },
            )
        if not strong_candidate and _GPU_MODEL_RE.search(normalized):
            return _detail_reason(
                "detail_wrong_model",
                "Detail page model evidence does not match any requirement candidate strongly enough.",
                evidence={"detected_model": _GPU_MODEL_RE.search(normalized).group(0)},
            )

    if not strong_candidate:
        return _detail_reason(
            "detail_insufficient_evidence",
            "Detail page did not provide enough candidate or requirement evidence.",
            evidence={"reasons_against": reasons_against},
        )

    if score.get("decision_band") == "reject":
        return _detail_reason(
            "detail_threshold_not_met",
            "Detail page passed hard checks but did not meet the scanner save threshold.",
            evidence={
                "score": score.get("score"),
                "candidate_threshold": (mission.get("scan_config") or {}).get(
                    "candidate_threshold"
                ),
                "reasons_against": reasons_against,
            },
        )

    return None


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
    requirement_driven = _is_requirement_driven_mission(mission)

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
    strong_candidate_match = (
        _strong_candidate_model_evidence(normalized, mission)
        if requirement_driven
        else None
    )

    for term in _string_list(hard.get("exclude_keywords")) + _string_list(
        hard.get("forbidden_terms")
    ):
        if term.lower() in normalized:
            return {
                "prefilter_decision": "reject",
                "open_priority": 0,
                "prefilter_reasons": [f"Rejected by excluded term: {term}"],
            }

    if requirement_driven:
        junk_reason = _obvious_requirement_junk_reason(
            normalized,
            price_value,
            mission,
        )
        if junk_reason:
            return {
                "prefilter_decision": "reject",
                "open_priority": 0,
                "prefilter_reasons": [f"Rejected by obvious junk: {junk_reason}"],
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

    location_names = _string_list(hard.get("location_names"))
    card_location = _clean_text(card.get("location"))
    if location_names:
        if requirement_driven and strong_candidate_match:
            if _clear_location_conflict(normalized, card_location, location_names):
                return {
                    "prefilter_decision": "reject",
                    "open_priority": 0,
                    "prefilter_reasons": ["Rejected by location filter"],
                }
            if not _location_matches_scope(card_location, location_names):
                reasons.append(
                    "Location evidence is weak; deferring location check to detail page"
                )
        else:
            if _is_australia_scoped(location_names) and any(
                re.search(pattern, normalized) for pattern in _FOREIGN_LOCATION_PATTERNS
            ):
                return {
                    "prefilter_decision": "reject",
                    "open_priority": 0,
                    "prefilter_reasons": ["Rejected by location filter"],
                }
            if not _location_matches_scope(card_location, location_names):
                return {
                    "prefilter_decision": "reject",
                    "open_priority": 0,
                    "prefilter_reasons": ["Rejected by location filter"],
                }

    priority = 40
    include_hits = 0
    if strong_candidate_match:
        priority += 35
        reasons.append(f"Strong requirement candidate matched: {strong_candidate_match}")
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
        if requirement_driven and strong_candidate_match:
            reasons.append("Detailed requirement proof deferred to listing detail")
        else:
            priority -= 8
            reasons.append("Missing primary include keywords on the card")
    if priority < 20:
        decision = "reject"

    return {
        "prefilter_decision": decision,
        "open_priority": max(0, min(100, priority)),
        "prefilter_reasons": reasons or ["No hard-filter conflicts on the card"],
    }


_NOTE_STOPWORDS = frozenset(
    {"to", "too", "the", "an", "a", "is", "it", "in", "on", "at", "and", "or", "not", "no", "for", "of", "with", "this", "that", "was", "be"}
)


def _feedback_note_penalty(
    normalized_listing: str,
    notes: list[str],
) -> tuple[int, list[str]]:
    listing_tokens = _terms(normalized_listing)
    total_penalty = 0
    reasons: list[str] = []
    for note in notes:
        note_tokens = {
            t for t in _terms(_normalize(note))
            if len(t) >= 3 and t not in _NOTE_STOPWORDS
        }
        if not note_tokens:
            continue
        overlap = note_tokens & listing_tokens
        threshold = 1 if len(note_tokens) == 1 else 2
        if len(overlap) >= threshold:
            penalty = min(12, 5 * len(overlap))
            total_penalty += penalty
            reasons.append(
                f"Similar to a previous rejection ({', '.join(sorted(overlap)[:3])})"
            )
    return min(total_penalty, 20), reasons


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
        if not _location_matches_scope(location, location_names):
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

    feedback_notes = _string_list(mission.get("_feedback_notes"))
    if feedback_notes:
        note_penalty, note_reasons = _feedback_note_penalty(normalized, feedback_notes)
        if note_penalty > 0:
            score -= note_penalty
            reasons_against.extend(note_reasons)

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
