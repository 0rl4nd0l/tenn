from __future__ import annotations

import re
from typing import Any


SUPPORTED_REQUIREMENT_CATEGORIES = {"gpu", "cpu", "ram", "ssd", "motherboard"}
REQUIREMENT_MODES = {"exact_product", "requirement_driven"}

_GPU_EXACT_RE = re.compile(
    r"\b(?:nvidia\s+|geforce\s+)?(?:rtx|gtx)\s*(?:20|30|40|50)\d{2}\s*(?:ti|super)?\b"
    r"|\b(?:amd\s+|radeon\s+)?rx\s*[5679]\d{3}\s*(?:xtx|xt)?\b",
    re.IGNORECASE,
)
_CPU_EXACT_RE = re.compile(
    r"\b(?:ryzen\s*[3579]\s*)?\d{4}x3d\b"
    r"|\bryzen\s*[3579]\s*\d{4}[a-z0-9]*\b"
    r"|\b(?:core\s*)?i[3579][-\s]*\d{4,5}[a-z]*\b",
    re.IGNORECASE,
)
_SSD_EXACT_RE = re.compile(
    r"\b(?:990\s*pro|980\s*pro|sn850x|sn770|p3\s*plus|p5\s*plus|kc3000|t500|p44\s*pro)\b",
    re.IGNORECASE,
)
_RAM_EXACT_RE = re.compile(
    r"\b(?:trident\s*z5|vengeance|fury\s*beast|dominator|ripjaws)\b",
    re.IGNORECASE,
)
_MOTHERBOARD_EXACT_RE = re.compile(
    r"\b(?:asus\s+)?(?:pro\s*ws\s*)?x570[-\s]*ace\b",
    re.IGNORECASE,
)

_COMMON_NEGATIVE_TERMS = [
    "wanted",
    "wtb",
    "swap",
    "trade",
    "box only",
    "broken",
    "for parts",
    "not working",
    "gaming pc",
    "full pc",
]

_GPU_CANDIDATES: list[dict[str, Any]] = [
    {
        "canonical_key": "gpu-nvidia-rtx-3090-24gb",
        "category": "gpu",
        "brand": "NVIDIA",
        "model_family": "RTX 3090",
        "variant": "24GB",
        "attributes": {
            "vendor": "NVIDIA",
            "chip_model": "RTX 3090",
            "vram_gb": 24,
            "acceleration_stack": "CUDA",
        },
        "aliases": ["RTX 3090", "RTX3090", "RTX 3090 24GB", "3090 24GB", "NVIDIA RTX 3090"],
        "availability_rank": 1,
    },
    {
        "canonical_key": "gpu-nvidia-rtx-3090-ti-24gb",
        "category": "gpu",
        "brand": "NVIDIA",
        "model_family": "RTX 3090 Ti",
        "variant": "24GB",
        "attributes": {
            "vendor": "NVIDIA",
            "chip_model": "RTX 3090",
            "suffix": "TI",
            "vram_gb": 24,
            "acceleration_stack": "CUDA",
        },
        "aliases": ["RTX 3090 Ti", "RTX 3090Ti", "RTX 3090 Ti 24GB"],
        "availability_rank": 2,
    },
    {
        "canonical_key": "gpu-nvidia-rtx-4090-24gb",
        "category": "gpu",
        "brand": "NVIDIA",
        "model_family": "RTX 4090",
        "variant": "24GB",
        "attributes": {
            "vendor": "NVIDIA",
            "chip_model": "RTX 4090",
            "vram_gb": 24,
            "acceleration_stack": "CUDA",
        },
        "aliases": ["RTX 4090", "RTX 4090 24GB", "NVIDIA RTX 4090"],
        "availability_rank": 3,
    },
    {
        "canonical_key": "gpu-nvidia-rtx-4070-ti-super-16gb",
        "category": "gpu",
        "brand": "NVIDIA",
        "model_family": "RTX 4070 Ti SUPER",
        "variant": "16GB",
        "attributes": {
            "vendor": "NVIDIA",
            "chip_model": "RTX 4070",
            "suffix": "TI SUPER",
            "vram_gb": 16,
            "acceleration_stack": "CUDA",
        },
        "aliases": ["RTX 4070 Ti Super", "4070 Ti Super 16GB"],
        "availability_rank": 4,
    },
]

_CPU_CANDIDATES: list[dict[str, Any]] = [
    {
        "canonical_key": "cpu-amd-ryzen-9-5950x-am4",
        "category": "cpu",
        "brand": "AMD",
        "model_family": "Ryzen 9",
        "variant": "5950X AM4",
        "attributes": {"vendor": "AMD", "exact_sku": "Ryzen 9 5950X", "socket": "AM4"},
        "aliases": ["Ryzen 9 5950X", "5950X"],
        "availability_rank": 1,
    },
    {
        "canonical_key": "cpu-amd-ryzen-9-5900x-am4",
        "category": "cpu",
        "brand": "AMD",
        "model_family": "Ryzen 9",
        "variant": "5900X AM4",
        "attributes": {"vendor": "AMD", "exact_sku": "Ryzen 9 5900X", "socket": "AM4"},
        "aliases": ["Ryzen 9 5900X", "5900X"],
        "availability_rank": 2,
    },
    {
        "canonical_key": "cpu-amd-ryzen-7-5800x3d-am4",
        "category": "cpu",
        "brand": "AMD",
        "model_family": "Ryzen 7",
        "variant": "5800X3D AM4",
        "attributes": {"vendor": "AMD", "exact_sku": "Ryzen 7 5800X3D", "socket": "AM4"},
        "aliases": ["Ryzen 7 5800X3D", "5800X3D"],
        "availability_rank": 3,
    },
    {
        "canonical_key": "cpu-amd-ryzen-7-7800x3d-am5",
        "category": "cpu",
        "brand": "AMD",
        "model_family": "Ryzen 7",
        "variant": "7800X3D AM5",
        "attributes": {"vendor": "AMD", "exact_sku": "Ryzen 7 7800X3D", "socket": "AM5"},
        "aliases": ["Ryzen 7 7800X3D", "7800X3D"],
        "availability_rank": 1,
    },
    {
        "canonical_key": "cpu-amd-ryzen-7-7700-am5",
        "category": "cpu",
        "brand": "AMD",
        "model_family": "Ryzen 7",
        "variant": "7700 AM5",
        "attributes": {"vendor": "AMD", "exact_sku": "Ryzen 7 7700", "socket": "AM5"},
        "aliases": ["Ryzen 7 7700", "7700 AM5"],
        "availability_rank": 2,
    },
    {
        "canonical_key": "cpu-amd-ryzen-5-7600-am5",
        "category": "cpu",
        "brand": "AMD",
        "model_family": "Ryzen 5",
        "variant": "7600 AM5",
        "attributes": {"vendor": "AMD", "exact_sku": "Ryzen 5 7600", "socket": "AM5"},
        "aliases": ["Ryzen 5 7600", "7600 AM5"],
        "availability_rank": 3,
    },
]

_SSD_CANDIDATES: list[dict[str, Any]] = [
    {
        "canonical_key": "ssd-kingston-nv2-2tb-gen4",
        "category": "ssd",
        "brand": "Kingston",
        "model_family": "NV2",
        "variant": "2TB Gen4",
        "attributes": {"brand": "Kingston", "model": "NV2", "capacity_gb": 2000, "pcie_generation": 4, "interface": "NVMe"},
        "aliases": ["Kingston NV2 2TB", "NV2 2TB"],
        "availability_rank": 1,
    },
    {
        "canonical_key": "ssd-crucial-p3-plus-2tb-gen4",
        "category": "ssd",
        "brand": "Crucial",
        "model_family": "P3 Plus",
        "variant": "2TB Gen4",
        "attributes": {"brand": "Crucial", "model": "P3 PLUS", "capacity_gb": 2000, "pcie_generation": 4, "interface": "NVMe"},
        "aliases": ["Crucial P3 Plus 2TB", "P3 Plus 2TB"],
        "availability_rank": 2,
    },
    {
        "canonical_key": "ssd-samsung-990-pro-2tb-gen4",
        "category": "ssd",
        "brand": "Samsung",
        "model_family": "990 PRO",
        "variant": "2TB Gen4",
        "attributes": {"brand": "Samsung", "model": "990 PRO", "capacity_gb": 2000, "pcie_generation": 4, "interface": "NVMe"},
        "aliases": ["Samsung 990 Pro 2TB", "990 Pro 2TB"],
        "availability_rank": 3,
    },
    {
        "canonical_key": "ssd-wd-sn850x-2tb-gen4",
        "category": "ssd",
        "brand": "WD",
        "model_family": "SN850X",
        "variant": "2TB Gen4",
        "attributes": {"brand": "WD", "model": "SN850X", "capacity_gb": 2000, "pcie_generation": 4, "interface": "NVMe"},
        "aliases": ["WD SN850X 2TB", "WD Black SN850X 2TB"],
        "availability_rank": 4,
    },
    {
        "canonical_key": "ssd-crucial-t500-2tb-gen4",
        "category": "ssd",
        "brand": "Crucial",
        "model_family": "T500",
        "variant": "2TB Gen4",
        "attributes": {"brand": "Crucial", "model": "T500", "capacity_gb": 2000, "pcie_generation": 4, "interface": "NVMe"},
        "aliases": ["Crucial T500 2TB", "T500 2TB"],
        "availability_rank": 5,
    },
]

_RAM_CANDIDATES: list[dict[str, Any]] = [
    {
        "canonical_key": "ram-corsair-vengeance-lpx-32gb-ddr4-3200",
        "category": "ram",
        "brand": "Corsair",
        "model_family": "Vengeance LPX",
        "variant": "32GB DDR4-3200",
        "attributes": {"ddr_generation": 4, "total_capacity_gb": 32, "speed_mhz": 3200},
        "aliases": ["Corsair Vengeance LPX 32GB DDR4 3200", "Vengeance LPX DDR4 3200 32GB"],
        "availability_rank": 1,
    },
    {
        "canonical_key": "ram-gskill-ripjaws-v-32gb-ddr4-3200",
        "category": "ram",
        "brand": "G.Skill",
        "model_family": "Ripjaws V",
        "variant": "32GB DDR4-3200",
        "attributes": {"ddr_generation": 4, "total_capacity_gb": 32, "speed_mhz": 3200},
        "aliases": ["G.Skill Ripjaws 32GB DDR4 3200", "Ripjaws DDR4 3200 32GB"],
        "availability_rank": 2,
    },
    {
        "canonical_key": "ram-kingston-fury-beast-32gb-ddr4-3200",
        "category": "ram",
        "brand": "Kingston",
        "model_family": "Fury Beast",
        "variant": "32GB DDR4-3200",
        "attributes": {"ddr_generation": 4, "total_capacity_gb": 32, "speed_mhz": 3200},
        "aliases": ["Kingston Fury Beast 32GB DDR4 3200", "Fury Beast DDR4 3200 32GB"],
        "availability_rank": 3,
    },
    {
        "canonical_key": "ram-gskill-trident-z5-neo-32gb-ddr5-6000-cl30",
        "category": "ram",
        "brand": "G.Skill",
        "model_family": "Trident Z5 Neo",
        "variant": "32GB DDR5-6000 CL30",
        "attributes": {"ddr_generation": 5, "total_capacity_gb": 32, "speed_mhz": 6000, "cas_latency": 30},
        "aliases": ["G.Skill Trident Z5 Neo 32GB 6000", "DDR5 6000 CL30 32GB"],
        "availability_rank": 4,
    },
    {
        "canonical_key": "ram-corsair-vengeance-32gb-ddr5-6000",
        "category": "ram",
        "brand": "Corsair",
        "model_family": "Vengeance",
        "variant": "32GB DDR5-6000",
        "attributes": {"ddr_generation": 5, "total_capacity_gb": 32, "speed_mhz": 6000},
        "aliases": ["Corsair Vengeance 32GB DDR5 6000", "Vengeance DDR5 6000 32GB"],
        "availability_rank": 5,
    },
]

_MOTHERBOARD_CANDIDATES: list[dict[str, Any]] = [
    {
        "canonical_key": "motherboard-asus-pro-ws-x570-ace-am4",
        "category": "motherboard",
        "brand": "ASUS",
        "model_family": "Pro WS X570-ACE",
        "variant": "AM4 X570",
        "attributes": {
            "brand": "ASUS",
            "model": "PRO WS X570-ACE",
            "chipset": "X570",
            "socket": "AM4",
            "workstation_class": True,
        },
        "aliases": [
            "ASUS Pro WS X570-ACE",
            "Pro WS X570 ACE",
            "X570-ACE",
        ],
        "availability_rank": 1,
    },
]

_CATALOGUE = {
    "gpu": _GPU_CANDIDATES,
    "cpu": _CPU_CANDIDATES,
    "ssd": _SSD_CANDIDATES,
    "ram": _RAM_CANDIDATES,
    "motherboard": _MOTHERBOARD_CANDIDATES,
}


def _clean(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _lower(value: Any) -> str:
    return _clean(value).lower()


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list | tuple):
        raw = value
    elif isinstance(value, str):
        raw = re.split(r"[,;\n]", value)
    elif value is None:
        raw = []
    else:
        raw = [value]
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        cleaned = _clean(item)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
    return out


def _combined_text(payload: dict[str, Any]) -> str:
    hard = payload.get("hard_filters") if isinstance(payload.get("hard_filters"), dict) else {}
    soft = payload.get("soft_preferences") if isinstance(payload.get("soft_preferences"), dict) else {}
    parts = [
        payload.get("name"),
        payload.get("brief"),
        payload.get("user_goal"),
        payload.get("category_hint"),
        hard.get("include_keywords"),
        hard.get("required_terms"),
        soft.get("preferred_brands"),
        soft.get("nice_to_have_terms"),
    ]
    flattened: list[str] = []
    for part in parts:
        if isinstance(part, list | tuple):
            flattened.extend(_clean(item) for item in part)
        else:
            flattened.append(_clean(part))
    return " ".join(item for item in flattened if item)


def _infer_category(text: str, category_hint: Any) -> str | None:
    hint = _lower(category_hint)
    if hint in SUPPORTED_REQUIREMENT_CATEGORIES:
        return hint
    lowered = text.lower()
    if re.search(r"\b(gpu|graphics\s*card|vram|rtx|gtx|radeon|rx\s*\d{4}|cuda)\b", lowered):
        return "gpu"
    if re.search(r"\b(cpu|processor|am5|ryzen|core\s*i[3579]|7800x3d|7600x)\b", lowered):
        return "cpu"
    if re.search(r"\b(nvme|m\.?2|ssd|gen\s*[345]|pcie)\b", lowered):
        return "ssd"
    if re.search(r"\b(ram|memory|ddr\s*[45]|mt/s|mhz|cl\d{2})\b", lowered):
        return "ram"
    if re.search(r"\b(motherboard|mainboard|mobo|x570[-\s]*ace|x570s?|am4|pro\s*ws)\b", lowered):
        return "motherboard"
    return hint or None


def _parse_budget(text: str, hard_filters: dict[str, Any]) -> dict[str, Any]:
    price_min = hard_filters.get("price_min")
    price_max = hard_filters.get("price_max")
    budget: dict[str, Any] = {
        "min": float(price_min) if isinstance(price_min, int | float) else None,
        "max": float(price_max) if isinstance(price_max, int | float) else None,
        "source": "hard_filters" if price_min is not None or price_max is not None else None,
    }
    if budget["max"] is None:
        under = re.search(r"\b(?:under|below|max(?:imum)?|budget)\s*(?:aud|au)?\$?\s*([0-9][0-9,]*)\b", text, re.IGNORECASE)
        around = re.search(r"\b(?:around|about|near)\s*(?:aud|au)?\$?\s*([0-9][0-9,]*)\b", text, re.IGNORECASE)
        match = under or around
        if match:
            value = float(match.group(1).replace(",", ""))
            budget["max"] = value if match is under else round(value * 1.1, 2)
            budget["source"] = "brief"
    return budget


def _exact_product_hint(category: str | None, text: str) -> str | None:
    if category == "gpu":
        match = _GPU_EXACT_RE.search(text)
    elif category == "cpu":
        match = _CPU_EXACT_RE.search(text)
    elif category == "ssd":
        match = _SSD_EXACT_RE.search(text)
    elif category == "ram":
        match = _RAM_EXACT_RE.search(text)
    elif category == "motherboard":
        match = _MOTHERBOARD_EXACT_RE.search(text)
    else:
        match = None
    return _clean(match.group(0)) if match else None


def build_requirement_profile(payload: dict[str, Any]) -> dict[str, Any]:
    hard = payload.get("hard_filters") if isinstance(payload.get("hard_filters"), dict) else {}
    soft = payload.get("soft_preferences") if isinstance(payload.get("soft_preferences"), dict) else {}
    text = _combined_text(payload)
    lowered = text.lower()
    category = _infer_category(text, payload.get("category_hint"))
    hard_constraints: list[dict[str, Any]] = []
    soft_preferences: list[dict[str, Any]] = []
    performance_tier_hints: list[str] = []
    intended_use: str | None = None

    if re.search(r"\b(local\s+inference|llm|ai\s+inference|machine\s+learning|deep\s+learning)\b", lowered):
        intended_use = "local_inference"
        soft_preferences.append(
            {
                "field": "acceleration_stack",
                "value": "CUDA/NVIDIA",
                "reason": "local inference generally benefits from CUDA-compatible NVIDIA GPUs",
            }
        )

    if category == "gpu":
        vram = re.search(r"\b(?:at\s+least|min(?:imum)?\s*)?(\d{1,2})\s*gb\s*(?:vram|gpu|graphics)?\b", lowered)
        if vram and "ddr" not in lowered:
            hard_constraints.append(
                {
                    "field": "vram_gb",
                    "operator": ">=",
                    "value": int(vram.group(1)),
                    "unit": "GB",
                    "source": "brief",
                }
            )
    elif category == "cpu":
        if "am4" in lowered:
            hard_constraints.append(
                {"field": "socket", "operator": "=", "value": "AM4", "source": "brief"}
            )
        if "am5" in lowered:
            hard_constraints.append(
                {"field": "socket", "operator": "=", "value": "AM5", "source": "brief"}
            )
        if "x3d" in lowered or "gaming" in lowered:
            performance_tier_hints.append("gaming_or_cache_sensitive")
    elif category == "ssd":
        capacity = re.search(r"\b(\d+(?:\.\d+)?)\s*tb\b", lowered)
        if capacity:
            hard_constraints.append(
                {
                    "field": "capacity_gb",
                    "operator": ">=",
                    "value": int(float(capacity.group(1)) * 1000),
                    "unit": "GB",
                    "source": "brief",
                }
            )
        if "gen4" in lowered or "gen 4" in lowered or "pcie 4" in lowered:
            hard_constraints.append(
                {"field": "pcie_generation", "operator": ">=", "value": 4, "source": "brief"}
            )
        if "nvme" in lowered:
            hard_constraints.append(
                {"field": "interface", "operator": "=", "value": "NVMe", "source": "brief"}
            )
    elif category == "ram":
        capacity = re.search(r"\b(\d{2,3})\s*gb\b", lowered)
        if capacity:
            hard_constraints.append(
                {
                    "field": "total_capacity_gb",
                    "operator": ">=",
                    "value": int(capacity.group(1)),
                    "unit": "GB",
                    "source": "brief",
                }
            )
        ddr = re.search(r"\bddr\s*([45])\b", lowered)
        if ddr:
            hard_constraints.append(
                {"field": "ddr_generation", "operator": "=", "value": int(ddr.group(1)), "source": "brief"}
            )
        speed = re.search(r"\b([56][0-9]{3})\s*(?:mt/s|mhz)?\b", lowered)
        if speed:
            soft_preferences.append(
                {"field": "speed_mhz", "value": int(speed.group(1)), "reason": "requested memory speed"}
            )
    elif category == "motherboard":
        if "am4" in lowered:
            hard_constraints.append(
                {"field": "socket", "operator": "=", "value": "AM4", "source": "brief"}
            )
        if "x570" in lowered:
            hard_constraints.append(
                {"field": "chipset", "operator": "=", "value": "X570", "source": "brief"}
            )
        if "pro ws" in lowered or "workstation" in lowered:
            soft_preferences.append(
                {
                    "field": "workstation_class",
                    "value": True,
                    "reason": "requested workstation-class X570 board",
                }
            )

    exact_hint = _exact_product_hint(category, text)
    requirement_cue = bool(
        re.search(
            r"\b(best|around|about|under|budget|deal|deals|hunt|trigger|suitable|"
            r"requirement|need|at\s+least|min(?:imum)?|for\s+local|equivalent|alternatives?)\b",
            lowered,
        )
    )
    exact_product_intent = bool(exact_hint and not requirement_cue)
    mode = (
        "requirement_driven"
        if category
        and (hard_constraints or intended_use or requirement_cue)
        and not exact_product_intent
        else "exact_product"
    )

    return {
        "mode": mode,
        "category": category,
        "intended_use": intended_use,
        "budget": _parse_budget(lowered, hard),
        "local_area": (_string_list(hard.get("location_names")) or _string_list(soft.get("preferred_suburbs")) or [None])[0],
        "hard_constraints": hard_constraints,
        "soft_preferences": soft_preferences,
        "performance_tier_hints": performance_tier_hints,
        "exact_product_hint": exact_hint,
        "extracted_terms": _string_list(hard.get("include_keywords")),
        "unsupported_reason": None if category in SUPPORTED_REQUIREMENT_CATEGORIES or category is None else "unsupported_category",
    }


def _constraint_value(profile: dict[str, Any], field: str) -> Any:
    for item in profile.get("hard_constraints") or []:
        if isinstance(item, dict) and item.get("field") == field:
            return item.get("value")
    return None


def _candidate_fits(candidate: dict[str, Any], profile: dict[str, Any]) -> tuple[bool, list[str], list[str]]:
    attributes = candidate.get("attributes") if isinstance(candidate.get("attributes"), dict) else {}
    met: list[str] = []
    missing: list[str] = []
    for constraint in profile.get("hard_constraints") or []:
        if not isinstance(constraint, dict):
            continue
        field = str(constraint.get("field") or "")
        expected = constraint.get("value")
        operator = str(constraint.get("operator") or "=")
        actual = attributes.get(field)
        ok = False
        if operator == ">=":
            try:
                ok = float(actual) >= float(expected)
            except (TypeError, ValueError):
                ok = False
        elif operator == "=":
            ok = str(actual).lower() == str(expected).lower()
        if ok:
            met.append(field)
        else:
            missing.append(field)
    return not missing, met, missing


def generate_requirement_candidate_specs(
    profile: dict[str, Any],
    *,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if profile.get("mode") != "requirement_driven":
        return []
    category = _lower(profile.get("category"))
    if category not in _CATALOGUE:
        return []

    scored: list[dict[str, Any]] = []
    for candidate in _CATALOGUE[category]:
        fits, met, missing = _candidate_fits(candidate, profile)
        if not fits:
            continue
        score = 78.0
        score += max(0, 4 - int(candidate.get("availability_rank") or 4)) * 3
        if profile.get("intended_use") == "local_inference":
            vendor = str(candidate.get("attributes", {}).get("vendor") or candidate.get("brand") or "").lower()
            score += 8 if vendor == "nvidia" else -15
        if category == "gpu":
            min_vram = _constraint_value(profile, "vram_gb")
            vram = candidate.get("attributes", {}).get("vram_gb")
            if isinstance(min_vram, int | float) and isinstance(vram, int | float):
                score += min(8.0, max(0.0, float(vram) - float(min_vram)) * 0.5)
        fit_label = "strong_fit" if score >= 88 else "fit"
        scored.append(
            {
                **candidate,
                "negative_terms": list(_COMMON_NEGATIVE_TERMS),
                "fit_score": round(min(100.0, score), 1),
                "fit_label": fit_label,
                "hard_constraints_met": met,
                "hard_constraints_missing": missing,
                "soft_preferences_met": [
                    item.get("field")
                    for item in profile.get("soft_preferences") or []
                    if isinstance(item, dict)
                ],
                "explanation": _candidate_explanation(candidate, profile, met),
            }
        )

    scored.sort(key=lambda item: (-float(item["fit_score"]), int(item.get("availability_rank") or 99)))
    return scored[: max(1, min(limit, 8))]


def candidate_search_terms(candidates: list[dict[str, Any]], *, limit: int = 8) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    primary_batches = [
        [
            f"{candidate.get('model_family') or ''} {candidate.get('variant') or ''}",
            candidate.get("model_family"),
        ]
        for candidate in candidates
    ]
    alias_batches = [candidate.get("aliases") or [] for candidate in candidates]
    for terms in [*primary_batches, *alias_batches]:
        for term in terms:
            cleaned = _clean(term)
            key = cleaned.lower()
            if cleaned and key not in seen:
                seen.add(key)
                out.append(cleaned)
            if len(out) >= limit:
                return out
    return out


def _candidate_explanation(candidate: dict[str, Any], profile: dict[str, Any], met: list[str]) -> str:
    name = " ".join(
        item for item in [candidate.get("brand"), candidate.get("model_family"), candidate.get("variant")] if item
    )
    if profile.get("category") == "gpu" and "vram_gb" in met:
        return f"{name} satisfies the VRAM requirement and keeps its own benchmark identity."
    if met:
        return f"{name} satisfies {', '.join(met)} and keeps its own benchmark identity."
    return f"{name} is a bounded candidate for this requirement profile."
