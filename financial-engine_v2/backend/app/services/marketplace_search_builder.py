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


def build_marketplace_search_pack(mission: dict[str, Any]) -> dict[str, Any]:
    hard = mission.get("hard_filters") or {}
    soft = mission.get("soft_preferences") or {}
    search = mission.get("search_config") or {}

    include_keywords = _compact_keyword_list(list(hard.get("include_keywords") or []))
    exclude_terms = _compact_keyword_list(
        list(hard.get("exclude_keywords") or []) + list(hard.get("forbidden_terms") or [])
    )
    brands = _unique(list(soft.get("preferred_brands") or []))
    brief_terms = _brief_keywords(_clean_text(mission.get("brief")))
    category_hint = _clean_text(mission.get("category_hint"))
    max_queries = max(1, int(search.get("max_queries_per_run") or 6))

    seed_terms = include_keywords or brief_terms[:3]
    core_phrase = seed_terms[0].strip() if seed_terms else category_hint or _clean_text(mission.get("name"))

    primary_queries: list[str] = []
    primary_queries.extend(seed_terms[:max_queries] or ([core_phrase] if core_phrase else []))
    for brand in brands:
        if core_phrase:
            primary_queries.append(f"{brand} {core_phrase}")
        for term in seed_terms[:2]:
            primary_queries.append(f"{brand} {term}")

    synonym_queries: list[str] = []
    if bool(search.get("query_variants_enabled", True)):
        for term in seed_terms:
            for synonym in _SYNONYMS.get(term.lower(), []):
                synonym_queries.append(synonym)
                if brands:
                    synonym_queries.append(f"{brands[0]} {synonym}")

    brand_model_queries = _unique(
        [
            f"{brand} {term}"
            for brand in brands
            for term in seed_terms[:3]
        ]
    )

    fallback_queries = []
    if bool(search.get("broadening_enabled", True)):
        fallback_queries.extend(seed_terms[:3])
        if category_hint:
            fallback_queries.append(category_hint)
        fallback_queries.extend(brief_terms[:2])

    primary_queries = _unique(primary_queries)[:max_queries]
    synonym_queries = _unique(synonym_queries)[:max_queries]
    brand_model_queries = _unique(brand_model_queries)[:max_queries]
    fallback_queries = _unique(fallback_queries)[:max_queries]

    return {
        "primary_queries": primary_queries,
        "synonym_queries": synonym_queries,
        "brand_model_queries": brand_model_queries,
        "fallback_queries": fallback_queries,
        "exclude_terms": exclude_terms,
        "location_scope": {
            "location_names": _unique(list(hard.get("location_names") or [])),
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
    return ordered[: max(1, max_queries)]
