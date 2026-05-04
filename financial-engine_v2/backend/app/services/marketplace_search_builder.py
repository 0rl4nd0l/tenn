from __future__ import annotations

import re
from typing import Any


_STOPWORDS = {
    "a",
    "an",
    "and",
    "any",
    "best",
    "buy",
    "find",
    "for",
    "from",
    "good",
    "in",
    "is",
    "it",
    "local",
    "me",
    "my",
    "of",
    "on",
    "or",
    "the",
    "to",
    "under",
    "used",
    "want",
    "with",
}

_SYNONYMS = {
    "bike": ["bicycle", "mtb"],
    "bicycle": ["bike"],
    "couch": ["sofa", "lounge"],
    "dual cab": ["double cab"],
    "sofa": ["couch", "lounge"],
    "ute": ["pickup", "truck"],
    "4x4": ["four wheel drive"],
    "laptop": ["notebook"],
}

_COMPACT_PHRASES = (
    "local inference",
    "deep learning",
    "machine learning",
    "tensor core",
    "single 8-pin",
    "for parts",
    "mining rig",
    "water damaged",
)

_IMPORTANT_TERMS = (
    "artifact",
    "artifacting",
    "broken",
    "faulty",
    "untested",
    "damaged",
    "mining",
)

_MODEL_RE = re.compile(
    r"\b(?:RTX|GTX|RX|ARC|TESLA|QUADRO)\s+[A-Z]?\d{3,4}"
    r"(?:\s+(?:Ti|SUPER|Super|XT))?"
    r"(?:\s+\d{1,2}GB)?\b",
    re.IGNORECASE,
)
_GPU_CAPACITY_RE = re.compile(r"\b(?:GPU|VRAM)\s+\d{1,2}GB\b", re.IGNORECASE)
_ACRONYM_RE = re.compile(r"\b(?:CUDA|NVIDIA|AMD|INTEL|LLM|AI)\b", re.IGNORECASE)
_LOCATION_CLAUSE_RE = re.compile(
    r"\blocations?\s*(?:i\s*(?:want|prefer)|to\s*use)?\s*:\s*([^.;\n]+)",
    re.IGNORECASE,
)
_AUSTRALIA_WIDE_LOCATION_TERMS = {
    "australia",
    "australia wide",
    "australia-wide",
    "nationwide",
    "nation wide",
    "national",
}


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _unique(items: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        cleaned = _clean_text(item)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out


def _brief_keywords(brief: str) -> list[str]:
    words = [
        word
        for word in re.findall(r"[a-z0-9]{3,}", brief.lower())
        if word not in _STOPWORDS
    ]
    out: list[str] = []
    for word in words:
        if word not in out:
            out.append(word)
    return out[:6]


def _compact_keyword_entry(value: str) -> list[str]:
    cleaned = _clean_text(value)
    if not cleaned:
        return []
    words = re.findall(r"[a-z0-9.+-]+", cleaned.lower())
    if len(words) <= 6:
        return [cleaned]

    extracted: list[str] = []
    extracted.extend(match.group(0).strip() for match in _MODEL_RE.finditer(cleaned))
    extracted.extend(match.group(0).strip() for match in _GPU_CAPACITY_RE.finditer(cleaned))
    extracted.extend(match.group(0).strip() for match in _ACRONYM_RE.finditer(cleaned))

    lowered = cleaned.lower()
    for phrase in _COMPACT_PHRASES:
        if phrase in lowered:
            extracted.append(phrase)
    for term in _IMPORTANT_TERMS:
        if re.search(rf"\b{re.escape(term)}\b", lowered):
            extracted.append(term)

    if not extracted:
        meaningful = [word for word in words if word not in _STOPWORDS]
        extracted.extend(meaningful[:4])

    return _unique(extracted)


def _compact_keyword_list(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        out.extend(_compact_keyword_entry(value))
    return _unique(out)


def _brief_location_terms(brief: str) -> list[str]:
    text = _clean_text(brief)
    if not text:
        return []
    out: list[str] = []
    for match in _LOCATION_CLAUSE_RE.finditer(text):
        clause = _clean_text(match.group(1))
        if not clause:
            continue
        parts = re.split(r",|/|\band\b", clause, flags=re.IGNORECASE)
        for part in parts:
            candidate = _clean_text(part).strip("- ")
            if not candidate:
                continue
            if re.search(r"\d", candidate):
                continue
            out.append(candidate)
    return _unique(out)[:4]


def _search_query_location_term(location_name: str) -> str:
    cleaned = _clean_text(location_name)
    lowered = cleaned.lower()
    if lowered in _AUSTRALIA_WIDE_LOCATION_TERMS:
        return ""
    if "melbourne" in lowered:
        return "Melbourne"
    if "victoria" in lowered and "australia" in lowered:
        return "Melbourne"
    return cleaned


def _brand_prefixed(brand: str, term: str) -> str:
    brand = _clean_text(brand)
    term = _clean_text(term)
    if not brand:
        return term
    if not term:
        return brand
    if re.search(rf"\b{re.escape(brand.lower())}\b", term.lower()):
        return term
    return f"{brand} {term}"


def build_marketplace_search_pack(mission: dict[str, Any]) -> dict[str, Any]:
    hard = mission.get("hard_filters") or {}
    soft = mission.get("soft_preferences") or {}
    search = mission.get("search_config") or {}
    deployment_args = mission.get("deployment_args") or {}

    include_keywords = _compact_keyword_list(list(hard.get("include_keywords") or []))
    exclude_terms = _compact_keyword_list(
        list(hard.get("exclude_keywords") or []) + list(hard.get("forbidden_terms") or [])
    )
    brands = _unique(list(soft.get("preferred_brands") or []))
    brief_terms = _brief_keywords(_clean_text(mission.get("brief")))
    category_hint = _clean_text(mission.get("category_hint"))
    max_queries = max(1, int(search.get("max_queries_per_run") or 6))

    requirement_profile = (
        deployment_args.get("requirement_profile")
        if isinstance(deployment_args, dict)
        else None
    )
    candidate_terms = []
    is_requirement_driven = (
        isinstance(requirement_profile, dict)
        and requirement_profile.get("mode") == "requirement_driven"
    )
    if is_requirement_driven:
        candidate_terms = _compact_keyword_list(
            list(deployment_args.get("candidate_search_terms") or [])
        )
        if not candidate_terms:
            raise ValueError(
                "Requirement-driven Marketplace mission is missing candidate_search_terms; "
                "run prepare_requirement_driven_mission before search query generation."
            )
    seed_terms = candidate_terms if is_requirement_driven else include_keywords or brief_terms[:3]
    core_phrase = seed_terms[0].strip() if seed_terms else category_hint or _clean_text(mission.get("name"))

    primary_queries: list[str] = []
    primary_queries.extend(seed_terms[:max_queries] or ([core_phrase] if core_phrase else []))
    for brand in brands:
        if core_phrase:
            primary_queries.append(_brand_prefixed(brand, core_phrase))
        for term in seed_terms[:2]:
            primary_queries.append(_brand_prefixed(brand, term))

    synonym_queries: list[str] = []
    if bool(search.get("query_variants_enabled", True)):
        for term in seed_terms:
            for synonym in _SYNONYMS.get(term.lower(), []):
                synonym_queries.append(synonym)
                if brands:
                    synonym_queries.append(f"{brands[0]} {synonym}")

    brand_model_queries = _unique(
        [
            _brand_prefixed(brand, term)
            for brand in brands
            for term in seed_terms[:3]
        ]
    )

    fallback_queries = []
    if bool(search.get("broadening_enabled", True)):
        if is_requirement_driven:
            fallback_queries.extend(seed_terms[:max_queries])
        else:
            fallback_queries.extend(seed_terms[:3])
            if category_hint:
                fallback_queries.append(category_hint)
            fallback_queries.extend(brief_terms[:2])

    primary_queries = _unique(primary_queries)[:max_queries]
    synonym_queries = _unique(synonym_queries)[:max_queries]
    brand_model_queries = _unique(brand_model_queries)[:max_queries]
    fallback_queries = _unique(fallback_queries)[:max_queries]
    location_terms = _unique(
        list(hard.get("location_names") or [])
        + list(soft.get("preferred_suburbs") or [])
        + _brief_location_terms(_clean_text(mission.get("brief")))
    )

    return {
        "primary_queries": primary_queries,
        "synonym_queries": synonym_queries,
        "brand_model_queries": brand_model_queries,
        "fallback_queries": fallback_queries,
        "exclude_terms": exclude_terms,
        "location_scope": {
            "location_names": location_terms,
            "radius_km": hard.get("radius_km"),
        },
        "price_bounds": {
            "price_min": hard.get("price_min"),
            "price_max": hard.get("price_max"),
        },
    }


def flatten_marketplace_queries(
    search_pack: dict[str, Any],
    *,
    max_queries: int,
) -> list[str]:
    ordered = _unique(
        list(search_pack.get("primary_queries") or [])
        + list(search_pack.get("brand_model_queries") or [])
        + list(search_pack.get("synonym_queries") or [])
        + list(search_pack.get("fallback_queries") or [])
    )
    location_scope = search_pack.get("location_scope") or {}
    location_names = _unique(list(location_scope.get("location_names") or []))
    if not location_names:
        return ordered[: max(1, max_queries)]

    localized_queries: list[str] = []
    query_location_names = _unique(
        [
            location_term
            for location in location_names
            if (location_term := _search_query_location_term(location))
        ]
    )
    if not query_location_names:
        if not ordered:
            return []
        expanded: list[str] = []
        while len(expanded) < max(1, max_queries):
            expanded.append(ordered[len(expanded) % len(ordered)])
        return expanded
    for query in ordered:
        for location in query_location_names[:2]:
            localized_queries.append(f"{query} {location}")

    expanded = _unique(localized_queries + ordered)
    return expanded[: max(1, max_queries)]
