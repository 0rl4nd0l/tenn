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
_SSD_EVIDENCE_RE = re.compile(
    r"\b(ssd|nvme|m\.?\s*2|pcie|gen\s*[345])\b", re.IGNORECASE
)
_SSD_WRONG_CATEGORY_RE = re.compile(
    r"\b(hdd|hhd|hard\s*drive|usb\s+storage|game\s+drive|time\s+capsule|"
    r"portable|external|enclosure|passport|t7(?:\s*shield)?)\b",
    re.IGNORECASE,
)
_SSD_MODEL_RE = re.compile(
    r"\b(nv2|9[789]0\s*pro|sn[0-9]{3,4}x?|p[0-9]\s*plus|p5\s*plus|"
    r"mx500|t500|kc3000|firecuda\s*[0-9]+|mp600(?:\s*elite)?|"
    r"gammix\s*s70(?:\s*blade)?|s70\s*blade)\b",
    re.IGNORECASE,
)
_SSD_PCIE_GEN_RE = re.compile(
    r"\b(?:pcie\s*)?gen\s*([345])\b|\bpcie\s*([345])(?:\.0)?\b", re.IGNORECASE
)
_RAM_MODEL_RE = re.compile(
    r"\b(vengeance|ripjaws|fury\s*beast|trident|dominator|ballistix)\b",
    re.IGNORECASE,
)
_RAM_GENERATION_RE = re.compile(r"\bddr\s*([345])\b", re.IGNORECASE)
_MOTHERBOARD_EVIDENCE_RE = re.compile(
    r"\b(motherboard|mainboard|mobo|x570|am4|pro\s*ws|x570[-\s]*ace)\b",
    re.IGNORECASE,
)
_MOTHERBOARD_MODEL_RE = re.compile(
    r"\bx570[-\s]*ace\b",
    re.IGNORECASE,
)
_MOTHERBOARD_WRONG_CATEGORY_RE = re.compile(
    r"\b(gpu|graphics\s*card|rtx|gtx|radeon|cpu|processor|ryzen|ssd|nvme|"
    r"ram|memory\s+kit|gaming\s+pc|full\s+pc|complete\s+pc)\b",
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
_DEAL_RANKED_CATEGORIES = {"gpu", "ssd", "ram", "motherboard"}
_GOOD_DEAL_DISCOUNT_PCT = 0.05
_STRONG_DEAL_DISCOUNT_PCT = 0.15
_ABOVE_MARKET_PREMIUM_PCT = 0.10
_POOR_DEAL_PREMIUM_PCT = 0.25
_VERY_POOR_DEAL_PREMIUM_PCT = 0.50
_SSD_CAPACITY_VALUE_PCT = 0.12


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
    if is_au_scope and any(
        re.search(pattern, location) for pattern in _FOREIGN_LOCATION_PATTERNS
    ):
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

    if is_au_scope and re.search(
        r"\b(australia|au|vic|nsw|qld|sa|wa|tas|act|nt)\b", location
    ):
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


def _tracked_category(value: Any) -> str:
    normalized = _normalize(value)
    aliases = {
        "graphics": "gpu",
        "graphics_card": "gpu",
        "processor": "cpu",
        "memory": "ram",
        "ram_kit": "ram",
        "nvme": "ssd",
        "nvme_m2": "ssd",
        "mainboard": "motherboard",
        "mobo": "motherboard",
        "workstation_board": "motherboard",
    }
    return aliases.get(normalized, normalized)


def _requirement_category(mission: dict[str, Any]) -> str:
    profile = _requirement_profile(mission)
    if isinstance(profile, dict) and profile.get("category"):
        return _tracked_category(profile.get("category"))
    return _tracked_category(mission.get("category_hint"))


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


def _has_asus_pro_ws_x570_ace_evidence(normalized_text: str) -> bool:
    if not _MOTHERBOARD_MODEL_RE.search(normalized_text):
        return False
    return bool(
        re.search(r"\basus\b", normalized_text)
        or re.search(r"\bpro[-\s]*ws\b", normalized_text)
        or re.search(r"\bws[-\s]*x570[-\s]*ace\b", normalized_text)
    )


def _phrase_matches_text(phrase: str, normalized_text: str) -> bool:
    tokens = re.findall(r"[a-z0-9]+", phrase.lower())
    if not tokens:
        return False
    pattern = r"\b" + r"[\s\-_]*".join(re.escape(token) for token in tokens) + r"\b"
    return bool(re.search(pattern, normalized_text))


def _term_matches_text(term: str, normalized_text: str) -> bool:
    lowered = term.lower()
    return lowered in normalized_text or _phrase_matches_text(term, normalized_text)


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
                if (
                    category == "motherboard"
                    and _MOTHERBOARD_MODEL_RE.search(variant)
                    and not _has_asus_pro_ws_x570_ace_evidence(normalized_text)
                ):
                    continue
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
    if any(
        re.search(pattern, normalized_text) for pattern in _FOREIGN_LOCATION_PATTERNS
    ):
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
    return bool(
        mission_states
        and location_states
        and not mission_states.intersection(location_states)
    )


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


def _storage_capacity_gb(text: str) -> int | None:
    match = re.search(r"\b(\d+(?:\.\d+)?)\s*(tb|gb)\b", text, re.IGNORECASE)
    if not match:
        return None
    value = float(match.group(1))
    unit = match.group(2).lower()
    return int(value * 1000) if unit == "tb" else int(value)


def _format_capacity_gb(value: int | float) -> str:
    capacity = int(value)
    if capacity >= 1000 and capacity % 1000 == 0:
        return f"{capacity // 1000}TB"
    return f"{capacity}GB"


def _canonical_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _gpu_model_label(value: str) -> str:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    if not tokens:
        return value.upper()
    if tokens[0] in {"nvidia", "geforce", "amd", "radeon"}:
        tokens = tokens[1:]
    if tokens and tokens[0] in {"rtx", "gtx", "rx"}:
        prefix = tokens[0].upper()
        rest = " ".join(
            token.upper() if token in {"ti", "super", "xt", "xtx"} else token
            for token in tokens[1:]
        )
        return f"{prefix} {rest}".strip()
    return " ".join(
        token.upper() if token in {"ti", "super", "xt", "xtx"} else token
        for token in tokens
    )


def _ssd_interface_label(normalized_text: str) -> str:
    if re.search(r"\b(nvme|m\.?\s*2|pcie)\b", normalized_text):
        return "NVMe"
    if re.search(r"\bsata\b", normalized_text):
        return "SATA"
    return "SSD"


def _ssd_generation_label(normalized_text: str) -> str | None:
    match = _SSD_PCIE_GEN_RE.search(normalized_text)
    if not match:
        return None
    generation = match.group(1) or match.group(2)
    return f"Gen{generation}" if generation else None


def _comparable_group(category: str, normalized_text: str) -> dict[str, Any] | None:
    normalized_category = _tracked_category(category)
    basis: list[str] = []
    labels: list[str] = []

    if normalized_category == "ssd":
        labels.append("SSD")
        interface = _ssd_interface_label(normalized_text)
        if interface != "SSD":
            basis.append("interface")
            labels.append(interface)
        generation = _ssd_generation_label(normalized_text)
        if generation:
            basis.append("generation")
            labels.append(generation)
        capacity = _storage_capacity_gb(normalized_text)
        if capacity is not None:
            basis.append("capacity")
            labels.append(_format_capacity_gb(capacity))
        model = _SSD_MODEL_RE.search(normalized_text)
        if model:
            basis.append("model")
            labels.append(_clean_text(model.group(0)).upper())
        if len(labels) == 1:
            return None
        label = " / ".join(labels)
        return {
            "key": "ssd:" + ":".join(_canonical_token(part) for part in labels[1:]),
            "label": label,
            "category": "ssd",
            "basis": basis,
        }

    if normalized_category == "gpu":
        model = _GPU_MODEL_RE.search(normalized_text)
        if not model:
            return None
        model_label = _gpu_model_label(model.group(0))
        labels = ["GPU", model_label]
        basis.append("model")
        vram = _explicit_gpu_vram_gb(normalized_text)
        if vram is not None:
            basis.append("vram")
            labels.append(f"{vram}GB")
        return {
            "key": "gpu:" + ":".join(_canonical_token(part) for part in labels[1:]),
            "label": " / ".join(labels),
            "category": "gpu",
            "basis": basis,
        }

    if normalized_category == "ram":
        capacity = _storage_capacity_gb(normalized_text)
        generation = _RAM_GENERATION_RE.search(normalized_text)
        model = _RAM_MODEL_RE.search(normalized_text)
        if capacity is None and generation is None and model is None:
            return None
        labels = ["RAM"]
        if capacity is not None:
            basis.append("capacity")
            labels.append(_format_capacity_gb(capacity))
        if generation is not None:
            basis.append("generation")
            labels.append(f"DDR{generation.group(1)}")
        if model is not None:
            basis.append("model")
            labels.append(_clean_text(model.group(0)).title())
        return {
            "key": "ram:" + ":".join(_canonical_token(part) for part in labels[1:]),
            "label": " / ".join(labels),
            "category": "ram",
            "basis": basis,
        }

    if normalized_category == "motherboard":
        model = _MOTHERBOARD_MODEL_RE.search(normalized_text)
        if not model:
            return None
        label = _clean_text(model.group(0)).upper().replace(" ", "-")
        return {
            "key": "motherboard:" + _canonical_token(label),
            "label": f"Motherboard / {label}",
            "category": "motherboard",
            "basis": ["model"],
        }

    return None


def _mission_storage_capacity_targets(mission: dict[str, Any]) -> set[int]:
    hard = mission.get("hard_filters") or {}
    targets: set[int] = set()
    for term in [
        *_string_list(hard.get("include_keywords")),
        *_string_list(hard.get("required_terms")),
    ]:
        capacity = _storage_capacity_gb(term.lower())
        if capacity is not None:
            targets.add(capacity)
    minimum_capacity = _minimum_requirement_value(mission, "capacity_gb")
    if minimum_capacity is not None:
        targets.add(int(minimum_capacity))
    return targets


def _category_fit_rejection(
    normalized_text: str, mission: dict[str, Any]
) -> str | None:
    category = _requirement_category(mission)
    if category != "ssd":
        if category == "motherboard":
            if _MOTHERBOARD_WRONG_CATEGORY_RE.search(normalized_text):
                return "Listing appears outside the requested motherboard category"
            if not _MOTHERBOARD_EVIDENCE_RE.search(normalized_text):
                return "Required motherboard/X570 evidence was not found"
            if _MOTHERBOARD_MODEL_RE.search(
                normalized_text
            ) and not _has_asus_pro_ws_x570_ace_evidence(normalized_text):
                return (
                    "Listing X570 ACE model is not the requested ASUS Pro WS X570-ACE"
                )
            hard = mission.get("hard_filters") or {}
            target_terms = " ".join(
                _string_list(hard.get("include_keywords"))
                + _string_list(hard.get("required_terms"))
            ).lower()
            if "x570" in target_terms and re.search(
                r"\b(b550|x470|x670|b650|am5)\b", normalized_text
            ):
                return "Listing chipset/socket does not match target X570/AM4 board"
        return None
    if _SSD_WRONG_CATEGORY_RE.search(normalized_text):
        return "Listing appears outside the requested internal NVMe SSD category"
    if not _SSD_EVIDENCE_RE.search(normalized_text):
        return "Required SSD/NVMe evidence was not found"
    targets = _mission_storage_capacity_targets(mission)
    listing_capacity = _storage_capacity_gb(normalized_text)
    if targets and listing_capacity is not None:
        minimum_target = min(targets)
        if listing_capacity < minimum_target:
            return (
                "Listing capacity is below target capacity: "
                f"at least {_format_capacity_gb(minimum_target)}"
            )
    return None


def _strong_category_identity_evidence(
    normalized_text: str, mission: dict[str, Any]
) -> bool:
    category = _requirement_category(mission)
    if category == "ssd":
        return bool(_SSD_MODEL_RE.search(normalized_text)) or bool(
            _strong_candidate_model_evidence(normalized_text, mission)
        )
    if category == "ram":
        return bool(_RAM_MODEL_RE.search(normalized_text)) or bool(
            _strong_candidate_model_evidence(normalized_text, mission)
        )
    if category == "motherboard":
        return _has_asus_pro_ws_x570_ace_evidence(normalized_text) or bool(
            _strong_candidate_model_evidence(normalized_text, mission)
        )
    return True


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

    if (
        "price" in reasons_text
        or "allowed minimum" in reasons_text
        or "allowed maximum" in reasons_text
    ):
        return _detail_reason(
            "detail_price_failed",
            "Detail page price failed the mission price constraints.",
            evidence={
                "reasons_against": reasons_against,
                "price": listing.get("price"),
            },
        )

    junk_reason = _obvious_requirement_junk_reason(
        normalized, price_value, classifier_mission
    )
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


def _band_price(value: dict[str, Any] | None, *keys: str) -> float | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        try:
            candidate = value.get(key)
            if candidate is None:
                continue
            parsed = float(candidate)
        except (TypeError, ValueError):
            continue
        if parsed > 0:
            return parsed
    return None


def _band_capacity_gb(value: dict[str, Any] | None) -> int | None:
    parsed = _band_price(value, "capacity_gb", "benchmark_capacity_gb")
    return int(parsed) if parsed is not None else None


def _candidate_price_bands(value: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(value, dict):
        return []
    bands = value.get("candidate_bands")
    if not isinstance(bands, list):
        return []
    return [band for band in bands if isinstance(band, dict)]


def _capacity_adjusted_price_band(
    band: dict[str, Any],
    *,
    listing_capacity_gb: int,
) -> dict[str, Any]:
    benchmark_capacity_gb = _band_capacity_gb(band)
    if benchmark_capacity_gb is None or benchmark_capacity_gb <= 0:
        return dict(band)
    scale = listing_capacity_gb / benchmark_capacity_gb
    if scale <= 0 or scale > 8:
        return dict(band)
    adjusted = dict(band)
    adjusted["capacity_gb"] = float(listing_capacity_gb)
    adjusted["capacity_adjusted_from_gb"] = float(benchmark_capacity_gb)
    adjusted["capacity_scale"] = round(scale, 4)
    for key in (
        "median",
        "used_median",
        "fair_low",
        "fair_range_low",
        "fair_high",
        "fair_range_high",
        "retail_anchor_price",
    ):
        value = _band_price(band, key)
        if value is not None:
            adjusted[key] = value * scale
    return adjusted


def _price_band_for_listing(
    observed_price_band: dict[str, Any] | None,
    *,
    category: str,
    normalized_text: str,
) -> dict[str, Any] | None:
    if not isinstance(observed_price_band, dict):
        return None
    if category != "ssd":
        return observed_price_band
    listing_capacity = _storage_capacity_gb(normalized_text)
    if listing_capacity is None:
        return observed_price_band

    candidates = _candidate_price_bands(observed_price_band)
    capacity_candidates = [
        candidate
        for candidate in candidates
        if _band_capacity_gb(candidate) is not None
    ]
    selected: dict[str, Any] = observed_price_band
    if capacity_candidates:
        selected = min(
            capacity_candidates,
            key=lambda item: abs(
                (_band_capacity_gb(item) or listing_capacity) - listing_capacity
            ),
        )
    return _capacity_adjusted_price_band(
        selected,
        listing_capacity_gb=listing_capacity,
    )


def _format_pct(value: float) -> str:
    return f"{abs(value) * 100:.1f}%"


def _price_delta_payload(
    listing_price: float | None,
    anchor_price: float | None,
) -> dict[str, float | None]:
    if listing_price is None or anchor_price is None or anchor_price <= 0:
        return {"amount": None, "percent": None}
    amount = listing_price - anchor_price
    return {
        "amount": round(amount, 2),
        "percent": round((amount / anchor_price) * 100, 1),
    }


def _benchmark_health(price_band: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(price_band, dict):
        return None
    sample_size = int(_band_price(price_band, "benchmark_sample_size") or 0)
    freshness = _clean_text(price_band.get("freshness_status")).lower() or "unknown"
    confidence = _clean_text(price_band.get("benchmark_confidence_label")).lower()
    source_diversity = int(_band_price(price_band, "source_diversity") or 0)
    warnings: list[str] = []

    confidence_rank = {"low": 0, "medium": 1, "high": 2}.get(confidence, 1)
    if sample_size <= 0:
        label = "unknown"
        warnings.append("No benchmark sample size is available.")
    elif sample_size < 3:
        label = "low"
        warnings.append("Benchmark has fewer than three observations.")
    elif freshness in {"stale", "no_data"}:
        label = "low"
        warnings.append("Benchmark is stale or unavailable.")
    else:
        label = "high" if sample_size >= 8 and confidence_rank >= 2 else "medium"
        if sample_size < 5 or (bool(confidence) and confidence_rank <= 0):
            label = "low"

    if freshness in {"aging", "low_data"} and label == "high":
        label = "medium"
    if source_diversity == 1 and sample_size >= 3:
        if label == "high":
            label = "medium"
        warnings.append("Benchmark currently comes from one source.")
    elif source_diversity == 0 and sample_size > 0:
        warnings.append("Benchmark source diversity is unknown.")

    return _clean_metric_payload(
        {
            "label": label,
            "sample_size": sample_size,
            "freshness_status": freshness,
            "confidence_label": confidence or None,
            "source_diversity": source_diversity if source_diversity > 0 else None,
            "warnings": warnings,
        }
    )


def _deal_label(score: float | None) -> str:
    if score is None:
        return "unscored"
    if score >= 85:
        return "excellent_value"
    if score >= 70:
        return "good_value"
    if score >= 50:
        return "fair_value"
    return "poor_value"


def _price_deal_score(
    *,
    listing_price: float | None,
    used_median: float | None,
    fair_low: float | None,
    fair_high: float | None,
    retail_anchor: float | None,
    capacity_value_delta: float | None = None,
) -> float | None:
    if listing_price is None:
        return None
    score: float | None = None
    if used_median is not None and used_median > 0:
        discount_pct = (used_median - listing_price) / used_median
        score = 55.0 + discount_pct * 120.0
        if fair_low is not None and listing_price <= fair_low:
            score = max(score, 86.0)
        if fair_high is not None and listing_price > fair_high:
            score = min(score, 48.0)
    elif retail_anchor is not None and retail_anchor > 0:
        retail_discount_pct = (retail_anchor - listing_price) / retail_anchor
        score = 50.0 + retail_discount_pct * 80.0

    if score is None:
        return None
    if capacity_value_delta is not None:
        score += max(-30.0, min(18.0, capacity_value_delta * 60.0))
    if retail_anchor is not None and retail_anchor > 0:
        if listing_price >= retail_anchor:
            score = min(score, 48.0)
        elif listing_price > retail_anchor * 0.9:
            score = min(score, 68.0)
    return round(max(0.0, min(100.0, score)), 1)


def _clean_metric_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


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


def prefilter_marketplace_card(
    card: dict[str, Any], mission: dict[str, Any]
) -> dict[str, Any]:
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
        if _term_matches_text(term, normalized):
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
        reasons.append(
            f"Strong requirement candidate matched: {strong_candidate_match}"
        )
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
    {
        "to",
        "too",
        "the",
        "an",
        "a",
        "is",
        "it",
        "in",
        "on",
        "at",
        "and",
        "or",
        "not",
        "no",
        "for",
        "of",
        "with",
        "this",
        "that",
        "was",
        "be",
    }
)
_FEEDBACK_SIGNAL_PATTERNS: tuple[tuple[str, str, str], ...] = (
    (
        "too_expensive",
        "price",
        r"\b(expensive|overpriced|too\s+high|price\s+high|retail|not\s+cheap)\b",
    ),
    (
        "wrong_model",
        "fit",
        r"\b(wrong\s+model|wrong\s+brand|not\s+the\s+right|different\s+model|mismatch)\b",
    ),
    (
        "low_capacity",
        "capacity",
        r"\b(low\s+capacity|too\s+small|not\s+enough\s+(?:storage|capacity)|1tb)\b",
    ),
    (
        "seller_risk",
        "seller",
        r"\b(scam|dodgy|seller|no\s+receipt|no\s+invoice|warranty|fake)\b",
    ),
    (
        "bad_location",
        "location",
        r"\b(too\s+far|far\s+away|location|pickup|interstate|shipping)\b",
    ),
    (
        "poor_condition",
        "condition",
        r"\b(broken|damaged|used\s+hard|scratched|faulty|parts|repair)\b",
    ),
    (
        "missing_photos",
        "evidence",
        r"\b(no\s+photo|missing\s+photo|photos?|picture|image)\b",
    ),
)


def _feedback_note_signals(notes: list[str]) -> list[dict[str, Any]]:
    signals: list[dict[str, Any]] = []
    seen: set[str] = set()
    for note in notes:
        normalized_note = _normalize(note)
        if not normalized_note:
            continue
        for code, field, pattern in _FEEDBACK_SIGNAL_PATTERNS:
            if code in seen or not re.search(pattern, normalized_note):
                continue
            seen.add(code)
            signals.append(
                {
                    "code": code,
                    "field": field,
                    "label": code.replace("_", " "),
                }
            )
    return signals


def _feedback_signal_penalty(
    signals: list[dict[str, Any]],
    *,
    category: str,
    listing_capacity: int | None,
    capacity_targets: set[int],
    price_value: float | None,
    median_price: float | None,
    retail_anchor: float | None,
    strong_identity: bool,
) -> tuple[int, list[str]]:
    total_penalty = 0
    reasons: list[str] = []
    signal_codes = {str(signal.get("code") or "") for signal in signals}

    if "too_expensive" in signal_codes and price_value is not None:
        price_risky = False
        if median_price is not None and median_price > 0:
            price_risky = price_value > median_price * (1 - _GOOD_DEAL_DISCOUNT_PCT)
        if retail_anchor is not None and retail_anchor > 0:
            price_risky = price_risky or price_value > retail_anchor * 0.9
        if price_risky:
            total_penalty += 8
            reasons.append(
                "Feedback learning: previous rejects often cited price too high"
            )

    if (
        "low_capacity" in signal_codes
        and category == "ssd"
        and listing_capacity is not None
        and capacity_targets
        and listing_capacity <= min(capacity_targets)
    ):
        total_penalty += 6
        reasons.append("Feedback learning: similar SSD rejects cited capacity")

    if "wrong_model" in signal_codes and not strong_identity:
        total_penalty += 6
        reasons.append("Feedback learning: previous rejects often cited model mismatch")

    if "seller_risk" in signal_codes:
        total_penalty += 3
        reasons.append("Feedback learning: previous rejects cited seller risk")

    return min(total_penalty, 16), reasons


def _feedback_note_penalty(
    normalized_listing: str,
    notes: list[str],
) -> tuple[int, list[str]]:
    listing_tokens = _terms(normalized_listing)
    total_penalty = 0
    reasons: list[str] = []
    for note in notes:
        note_tokens = {
            t
            for t in _terms(_normalize(note))
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
    observed_price_band: dict[str, Any] | None = None,
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
    combined = "\n".join(
        [title, description, location, seller_name, " ".join(raw_text_lines)]
    )
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
    for term in _string_list(hard.get("exclude_keywords")) + _string_list(
        hard.get("forbidden_terms")
    ):
        if _term_matches_text(term, normalized):
            return reject(f"Forbidden term present: {term}")

    if include_keywords and not any(
        term.lower() in normalized for term in include_keywords
    ):
        return reject("Required include keywords were not found")

    for term in _string_list(hard.get("required_terms")):
        if term.lower() not in normalized:
            return reject(f"Required term missing: {term}")

    if price_value is not None:
        price_min = hard.get("price_min")
        price_max = hard.get("price_max")
        if price_min is not None and price_value < float(price_min):
            return reject("Listing price is below the allowed minimum")
        if price_max is not None and price_value > float(price_max):
            return reject("Listing price is above the allowed maximum")

    required_conditions = _string_list(hard.get("condition_required"))
    if required_conditions and not any(
        term.lower() in normalized for term in required_conditions
    ):
        return reject("Required condition terms were not found")

    category_rejection = _category_fit_rejection(normalized, mission)
    if category_rejection:
        return reject(category_rejection)

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

    category = _requirement_category(mission)
    price_band = _price_band_for_listing(
        observed_price_band,
        category=category,
        normalized_text=normalized,
    )
    median_price = _band_price(price_band, "used_median", "median")
    fair_low = _band_price(price_band, "fair_low", "fair_range_low")
    fair_high = _band_price(price_band, "fair_high", "fair_range_high")
    retail_anchor = _band_price(price_band, "retail_anchor_price", "retail_anchor")
    benchmark_sample_size = _band_price(price_band, "benchmark_sample_size")
    listing_capacity = _storage_capacity_gb(normalized) if category == "ssd" else None
    band_capacity = _band_capacity_gb(price_band) if category == "ssd" else None
    comparable_group = _comparable_group(category, normalized)
    benchmark_health = _benchmark_health(price_band)
    capacity_targets = (
        _mission_storage_capacity_targets(mission) if category == "ssd" else set()
    )
    ssd_capacity_value_delta: float | None = None
    deal_metrics: dict[str, Any] = {}
    if price_value is not None:
        deal_metrics = _clean_metric_payload(
            {
                "state": "scored"
                if median_price is not None or retail_anchor is not None
                else "missing_benchmark",
                "listing_price": round(price_value, 2),
                "used_market_median": round(median_price, 2)
                if median_price is not None
                else None,
                "fair_low": round(fair_low, 2) if fair_low is not None else None,
                "fair_high": round(fair_high, 2) if fair_high is not None else None,
                "retail_anchor_price": round(retail_anchor, 2)
                if retail_anchor is not None
                else None,
                "delta_vs_used_median": _price_delta_payload(
                    price_value,
                    median_price,
                ),
                "delta_vs_retail_anchor": _price_delta_payload(
                    price_value,
                    retail_anchor,
                ),
                "benchmark_sample_size": int(benchmark_sample_size)
                if benchmark_sample_size is not None
                else None,
                "average_source": price_band.get("average_source")
                if isinstance(price_band, dict)
                else None,
                "benchmark_snapshot_id": price_band.get("benchmark_snapshot_id")
                if isinstance(price_band, dict)
                else None,
                "benchmark_capacity_gb": band_capacity,
                "capacity_gb": listing_capacity,
                "comparable_group": comparable_group,
                "benchmark_health": benchmark_health,
            }
        )
    score_cap: int | None = None
    if benchmark_health and benchmark_health.get("label") == "low":
        score_cap = min(score_cap or 100, 84)
        reasons_against.append(
            "Benchmark health is low; strong deal ranking needs fresher or broader data"
        )

    if price_value is not None:
        mission_cap = hard.get("price_max")
        if median_price:
            discount_pct = (median_price - price_value) / median_price
            if fair_low is not None and price_value <= fair_low:
                score += 24
                reasons_for.append(
                    "Good deal: listing is at or below the benchmark fair-value low"
                )
            elif discount_pct >= _STRONG_DEAL_DISCOUNT_PCT:
                score += 24
                reasons_for.append(
                    f"Good deal: {_format_pct(discount_pct)} below the used-market average"
                )
            elif discount_pct >= _GOOD_DEAL_DISCOUNT_PCT:
                score += 16
                reasons_for.append(
                    f"Below the used-market average by {_format_pct(discount_pct)}"
                )
            elif price_value <= median_price:
                score += 4
                reasons_for.append("Near the used-market average")
            elif fair_high is not None and price_value > fair_high:
                premium_pct = (price_value - median_price) / median_price
                penalty = 60 if premium_pct >= _VERY_POOR_DEAL_PREMIUM_PCT else 48
                score -= penalty
                score_cap = 44 if premium_pct >= _VERY_POOR_DEAL_PREMIUM_PCT else 56
                reasons_against.append(
                    f"Poor deal: {_format_pct(premium_pct)} above the used-market average and above fair range"
                )
            elif price_value > median_price * (1 + _VERY_POOR_DEAL_PREMIUM_PCT):
                score -= 60
                score_cap = 44
                premium_pct = (price_value - median_price) / median_price
                reasons_against.append(
                    f"Very poor deal: {_format_pct(premium_pct)} above the used-market average"
                )
            elif price_value > median_price * (1 + _POOR_DEAL_PREMIUM_PCT):
                score -= 48
                score_cap = 56
                premium_pct = (price_value - median_price) / median_price
                reasons_against.append(
                    f"Poor deal: {_format_pct(premium_pct)} above the used-market average"
                )
            elif price_value > median_price * (1 + _ABOVE_MARKET_PREMIUM_PCT):
                score -= 34
                score_cap = 64
                premium_pct = (price_value - median_price) / median_price
                reasons_against.append(
                    f"Above the used-market average by {_format_pct(premium_pct)}"
                )
            else:
                score -= 8
                premium_pct = (price_value - median_price) / median_price
                reasons_against.append(
                    f"Slightly above the used-market average by {_format_pct(premium_pct)}"
                )
        elif mission_cap is not None:
            mission_cap = float(mission_cap)
            if price_value <= mission_cap * 0.85:
                score += 10
                reasons_for.append("Comfortably below the mission price cap")
            elif price_value <= mission_cap:
                score += 5
                reasons_for.append("Within the mission price cap")

        if retail_anchor is not None and retail_anchor > 0:
            retail_delta_pct = (price_value - retail_anchor) / retail_anchor
            if retail_delta_pct >= _ABOVE_MARKET_PREMIUM_PCT:
                score -= 42
                score_cap = min(score_cap or 100, 48)
                reasons_against.append(
                    f"Poor deal: {_format_pct(retail_delta_pct)} above the retail anchor"
                )
            elif retail_delta_pct >= 0:
                score -= 30
                score_cap = min(score_cap or 100, 56)
                reasons_against.append("At or above the retail anchor price")
            elif retail_delta_pct > -0.10:
                score -= 18
                score_cap = min(score_cap or 100, 68)
                reasons_against.append("Too close to retail price for a used listing")

        if category == "ssd":
            if listing_capacity is not None:
                capacity_tb = max(listing_capacity / 1000, 0.1)
                price_per_tb = price_value / capacity_tb
                deal_metrics["price_per_tb"] = round(price_per_tb, 2)
                if band_capacity is not None and median_price:
                    benchmark_per_tb = median_price / max(band_capacity / 1000, 0.1)
                    value_delta = (benchmark_per_tb - price_per_tb) / benchmark_per_tb
                    ssd_capacity_value_delta = value_delta
                    deal_metrics["benchmark_price_per_tb"] = round(benchmark_per_tb, 2)
                    deal_metrics["capacity_value_delta_percent"] = round(
                        value_delta * 100,
                        1,
                    )
                    if value_delta >= _SSD_CAPACITY_VALUE_PCT:
                        score += 18
                        reasons_for.append(
                            "Capacity-adjusted SSD value: "
                            f"${price_per_tb:.0f}/TB beats the benchmark by {_format_pct(value_delta)}"
                        )
                    elif value_delta >= _GOOD_DEAL_DISCOUNT_PCT:
                        score += 10
                        reasons_for.append(
                            f"SSD price per TB is {_format_pct(value_delta)} below benchmark"
                        )
                    elif value_delta <= -_POOR_DEAL_PREMIUM_PCT:
                        score -= 36
                        score_cap = min(score_cap or 100, 56)
                        reasons_against.append(
                            "Poor SSD value: "
                            f"${price_per_tb:.0f}/TB is {_format_pct(abs(value_delta))} above benchmark"
                        )

                if capacity_targets:
                    minimum_target = min(capacity_targets)
                    if listing_capacity > minimum_target:
                        capacity_bonus = min(
                            12,
                            int(((listing_capacity / minimum_target) - 1.0) * 8),
                        )
                        if capacity_bonus > 0:
                            score += capacity_bonus
                            reasons_for.append(
                                "Higher-capacity SSD than the minimum target: "
                                f"{_format_capacity_gb(listing_capacity)}"
                            )

        if deal_metrics:
            deal_score = _price_deal_score(
                listing_price=price_value,
                used_median=median_price,
                fair_low=fair_low,
                fair_high=fair_high,
                retail_anchor=retail_anchor,
                capacity_value_delta=ssd_capacity_value_delta,
            )
            deal_metrics["deal_score"] = deal_score
            deal_metrics["deal_label"] = _deal_label(deal_score)

    better_price_already_seen = False
    strong_price_not_good_enough = False
    if category in _DEAL_RANKED_CATEGORIES:
        if price_value is None:
            better_price_already_seen = True
            reasons_against.append(
                "Strong match requires a captured price for deal ranking"
            )
        else:
            median_price = _band_price(price_band, "used_median", "median")
            fair_low = _band_price(price_band, "fair_low", "fair_range_low")
            fair_high = _band_price(price_band, "fair_high", "fair_range_high")
            if median_price:
                good_discount_price = median_price * (1 - _GOOD_DEAL_DISCOUNT_PCT)
                if price_value > good_discount_price and (
                    fair_low is None or price_value > fair_low
                ):
                    strong_price_not_good_enough = True
                    reasons_against.append(
                        "Strong match requires a real discount versus the used-market average"
                    )
                if fair_high is not None and price_value > fair_high:
                    strong_price_not_good_enough = True
            best_seen_price = _band_price(price_band, "min", "best_seen")
            if (
                best_seen_price is not None
                and best_seen_price > 0
                and price_value > best_seen_price
            ):
                better_price_already_seen = True
                reasons_against.append(
                    "Cheaper comparable listing already seen in this mission"
                )

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
    feedback_signals = _feedback_note_signals(feedback_notes)
    if feedback_notes:
        note_penalty, note_reasons = _feedback_note_penalty(normalized, feedback_notes)
        if note_penalty > 0:
            score -= note_penalty
            reasons_against.extend(note_reasons)
        signal_penalty, signal_reasons = _feedback_signal_penalty(
            feedback_signals,
            category=category,
            listing_capacity=listing_capacity,
            capacity_targets=capacity_targets,
            price_value=price_value,
            median_price=median_price,
            retail_anchor=retail_anchor,
            strong_identity=_strong_category_identity_evidence(normalized, mission),
        )
        if signal_penalty > 0:
            score -= signal_penalty
            reasons_against.extend(signal_reasons)
        if deal_metrics and feedback_signals:
            deal_metrics["feedback_signals"] = feedback_signals[:5]

    candidate_threshold = int(scan_config.get("candidate_threshold") or 70)
    strong_threshold = int(scan_config.get("strong_match_threshold") or 85)
    if score_cap is not None:
        score = min(score, score_cap)
    score = max(0, min(100, score))
    confidence = max(0.2, min(0.95, confidence))

    if score >= strong_threshold:
        band = "strong_match"
    elif score >= candidate_threshold:
        band = "candidate"
    else:
        band = "reject"

    if band == "strong_match" and not _strong_category_identity_evidence(
        normalized, mission
    ):
        band = "candidate"
        score = min(score, strong_threshold - 1)
        reasons_against.append(
            "Strong match requires model or series evidence for this product category"
        )
    if band == "strong_match" and better_price_already_seen:
        band = "candidate"
        score = min(score, strong_threshold - 1)
    if band == "strong_match" and strong_price_not_good_enough:
        band = "candidate"
        score = min(score, strong_threshold - 1)

    return {
        "eligibility": "pass" if band != "reject" else "reject",
        "score": score,
        "decision_band": band,
        "reasons_for": reasons_for or ["No hard-filter conflicts found"],
        "reasons_against": reasons_against,
        "deal_metrics": deal_metrics or None,
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
