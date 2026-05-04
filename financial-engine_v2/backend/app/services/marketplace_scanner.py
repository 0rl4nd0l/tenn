from __future__ import annotations

import asyncio
import random
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus, urlencode

from app.services.facebook_marketplace_inspector import (
    DEFAULT_MARKETPLACE_CDP_URL,
    DEFAULT_MARKETPLACE_TIMEOUT_MS,
    MARKETPLACE_CAPTURE_ROOT,
    MarketplaceBrowserProbeTimeout,
    _await_marketplace_probe,
    _marketplace_probe_timeout_detail,
    _probe_timeout_seconds,
)
from app.services.marketplace_browser_profile import (
    check_marketplace_browser_health,
    marketplace_scan_health_allows_execution,
)
from app.services.marketplace_headless_runtime import open_direct_marketplace_context, use_direct_marketplace_runtime
from app.services.marketplace_mission_service import (
    MarketplaceMissionService,
    normalize_marketplace_location_names,
)
from app.services.marketplace_price_intelligence import (
    MarketplacePriceIntelligenceService,
    detect_listing_junk,
    normalize_product_text,
    normalize_tracked_product_category,
)
from app.services.marketplace_requirement_preparation import (
    RequirementMissionPreparationError,
    marketplace_candidate_contexts,
    marketplace_requirement_profile,
    prepare_requirement_driven_mission,
)
from app.services.marketplace_scoring import (
    classify_requirement_detail_outcome,
    evaluate_marketplace_listing,
    listing_material_hash,
    material_change_reasons,
    parse_marketplace_price,
    prefilter_marketplace_card,
)
from app.services.marketplace_search_builder import (
    build_marketplace_search_pack,
    flatten_marketplace_queries,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


FACEBOOK_MARKETPLACE_ITEM_RE = re.compile(
    r"/marketplace/item/(?P<listing_id>[0-9A-Za-z]+)/?",
    re.IGNORECASE,
)
DEFAULT_MARKETPLACE_RADIUS_KM = 160
CALIBRATION_MARKETPLACE_RADIUS_KM = 500
CALIBRATION_MAX_QUERY_VARIANTS = 4
DEFAULT_DETAIL_PACING_SECONDS = (1.5, 4.0)
DEFAULT_DETAIL_TIMEOUT_BACKOFF_SECONDS = (8.0, 15.0)
MAX_DETAIL_TIMEOUT_BACKOFF_SECONDS = 60.0
VALUE_RESALE_MIN_SCORE = 70.0
VALUE_RESALE_MIN_VARIANT_CONFIDENCE = 0.65
VALUE_RESALE_PREFILTER_REASON = (
    "Under-market tracked product candidate prioritized for value review"
)
DETAIL_TIMEOUT_RE = re.compile(r"(timeout|timed out|err_timed_out)", re.IGNORECASE)
_LOCATION_COORD_OVERRIDES: dict[str, tuple[float, float]] = {
    "victoria, australia": (-37.8136, 144.9631),  # Melbourne CBD anchor
    "melbourne, australia": (-37.8136, 144.9631),
    "sydney, australia": (-33.8688, 151.2093),
    "brisbane, australia": (-27.4698, 153.0251),
    "adelaide, australia": (-34.9285, 138.6007),
    "perth, australia": (-31.9523, 115.8613),
    "canberra, australia": (-35.2809, 149.1300),
    "hobart, australia": (-42.8821, 147.3272),
    "darwin, australia": (-12.4634, 130.8456),
}
_AUSTRALIA_WIDE_CITY_ANCHORS: tuple[str, ...] = (
    "Melbourne, Australia",
    "Sydney, Australia",
    "Brisbane, Australia",
    "Adelaide, Australia",
    "Perth, Australia",
    "Canberra, Australia",
    "Hobart, Australia",
    "Darwin, Australia",
)
_AUSTRALIA_WIDE_LOCATION_NAMES = {
    "australia",
    "australia wide",
    "australian wide",
    "nation wide",
    "nationwide",
    "national",
}


def extract_marketplace_listing_id(url: str) -> str | None:
    match = FACEBOOK_MARKETPLACE_ITEM_RE.search(str(url or ""))
    return str(match.group("listing_id")) if match else None


def canonical_marketplace_listing_url(url: str) -> str:
    listing_id = extract_marketplace_listing_id(url)
    if not listing_id:
        return str(url or "").strip()
    return f"https://www.facebook.com/marketplace/item/{listing_id}/"


def _clean_price_text(value: Any) -> str | None:
    cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
    return cleaned or None


def _resolved_price_evidence(
    *,
    card: dict[str, Any],
    detail: dict[str, Any],
) -> dict[str, Any]:
    detail_price = _clean_price_text(detail.get("price"))
    card_price = _clean_price_text(card.get("price"))
    resolved_price = detail_price or card_price
    source = "detail" if detail_price else "search_card" if card_price else "missing"
    evidence: dict[str, Any] = {
        "detail_price_text": detail_price,
        "card_price_text": card_price,
        "resolved_price_text": resolved_price,
        "resolved_price_value": parse_marketplace_price(resolved_price),
        "source": source,
    }
    if source == "search_card":
        evidence["warning"] = "Detail page did not expose a price; preserved search-card price."
    elif source == "missing":
        evidence["warning"] = "No price was exposed by the search card or detail page."
    return evidence


def _detail_with_resolved_price(
    detail: dict[str, Any],
    price_evidence: dict[str, Any],
) -> dict[str, Any]:
    return {
        **detail,
        "price": price_evidence.get("resolved_price_text"),
    }


def _location_slug(location_name: str) -> str:
    normalized = str(location_name or "").strip().lower()
    if "melbourne" in normalized:
        return "melbourne"
    for city in (
        "sydney",
        "brisbane",
        "adelaide",
        "perth",
        "canberra",
        "hobart",
        "darwin",
    ):
        if city in normalized:
            return city
    if "victoria" in normalized and "australia" in normalized:
        return "melbourne"
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def _location_coordinates(location_name: str | None) -> tuple[float, float] | None:
    normalized = str(location_name or "").strip().lower()
    if not normalized:
        return None
    if normalized in _LOCATION_COORD_OVERRIDES:
        return _LOCATION_COORD_OVERRIDES[normalized]
    if "victoria" in normalized and "australia" in normalized:
        return _LOCATION_COORD_OVERRIDES["victoria, australia"]
    if "melbourne" in normalized:
        return _LOCATION_COORD_OVERRIDES["melbourne, australia"]
    return None


def _is_australia_wide_location(location_name: str) -> bool:
    normalized = re.sub(r"[^a-z0-9]+", " ", str(location_name or "").lower()).strip()
    return normalized in _AUSTRALIA_WIDE_LOCATION_NAMES


def _scan_location_anchors(location_names: list[str]) -> list[str]:
    if any(_is_australia_wide_location(location) for location in location_names):
        return list(_AUSTRALIA_WIDE_CITY_ANCHORS)
    return list(location_names)


def _tracked_product_search_query(product: dict[str, Any]) -> str:
    queries = _tracked_product_search_queries(product, limit=1)
    return queries[0] if queries else str(product.get("canonical_key") or "").strip()


def _tracked_product_search_queries(
    product: dict[str, Any],
    *,
    limit: int = CALIBRATION_MAX_QUERY_VARIANTS,
) -> list[str]:
    aliases = product.get("aliases") if isinstance(product.get("aliases"), list) else []
    out: list[str] = []
    seen: set[str] = set()
    for value in [
        " ".join(
            str(part or "").strip()
            for part in [product.get("model_family"), product.get("variant")]
            if str(part or "").strip()
        ),
        *(str(alias or "").strip() for alias in aliases),
        str(product.get("canonical_key") or "").replace("-", " "),
    ]:
        cleaned = re.sub(r"\s+", " ", str(value or "")).strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            out.append(cleaned)
        if len(out) >= max(1, limit):
            return out
    return out


def build_marketplace_search_url(
    query: str,
    *,
    location_name: str | None = None,
    radius_km: float | None = None,
) -> str:
    params: dict[str, str] = {"query": str(query or "").strip()}
    if radius_km is not None:
        try:
            params["radiusKM"] = str(max(1, int(round(float(radius_km)))))
        except (TypeError, ValueError):
            pass
    coords = _location_coordinates(location_name)
    if coords is not None:
        params["latitude"] = f"{coords[0]:.4f}"
        params["longitude"] = f"{coords[1]:.4f}"

    suffix = urlencode(params, quote_via=quote_plus)
    location_slug = _location_slug(location_name or "")
    if location_slug:
        return f"https://www.facebook.com/marketplace/{location_slug}/search?{suffix}"
    return f"https://www.facebook.com/marketplace/search?{suffix}"


def _rejection_bucket(reasons: Any) -> str:
    raw_reasons = [reasons] if isinstance(reasons, str) else list(reasons or [])
    joined = " ".join(str(reason or "") for reason in raw_reasons)
    lowered = joined.lower()
    if "location" in lowered or "mission area" in lowered:
        return "location"
    return "requirement_fit"


def _candidate_resolution_metadata(resolution: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(resolution, dict):
        return None
    candidate = resolution.get("candidate")
    product = resolution.get("tracked_product")
    candidate_payload = candidate if isinstance(candidate, dict) else {}
    product_payload = product if isinstance(product, dict) else {}
    return {
        "matched": bool(resolution.get("matched")),
        "candidate_match_confidence": resolution.get("candidate_match_confidence"),
        "candidate_key": candidate_payload.get("candidate_key"),
        "tracked_product_id": product_payload.get("tracked_product_id"),
        "warning": resolution.get("warning"),
    }


def _increment_detail_reason(counter: dict[str, int], reason_code: str | None) -> None:
    if not reason_code:
        return
    counter[reason_code] = int(counter.get(reason_code, 0)) + 1


def _merge_detail_reasons(target: dict[str, int], source: Any) -> None:
    if not isinstance(source, dict):
        return
    for reason_code, count in source.items():
        try:
            increment = int(count)
        except (TypeError, ValueError):
            continue
        if not reason_code or increment <= 0:
            continue
        target[str(reason_code)] = int(target.get(str(reason_code), 0)) + increment


def _format_detail_reasons(counter: dict[str, int]) -> str:
    if not counter:
        return ""
    return ", ".join(
        f"{reason}={count}"
        for reason, count in sorted(counter.items(), key=lambda item: item[0])
    )


def _marketplace_category(mission: dict[str, Any]) -> str | None:
    profile = marketplace_requirement_profile(mission)
    if isinstance(profile, dict) and profile.get("category"):
        return normalize_tracked_product_category(profile["category"])
    category = str(mission.get("category_hint") or "").strip().lower()
    return normalize_tracked_product_category(category) if category else None


def _listing_product_metadata(mission: dict[str, Any], detail: dict[str, Any]) -> dict[str, Any]:
    category = _marketplace_category(mission)
    if category not in {"gpu", "cpu", "ram", "ssd", "motherboard"}:
        return {}
    text = " ".join(
        str(value or "")
        for value in [
            detail.get("title"),
            detail.get("raw_text_snapshot"),
            detail.get("price"),
        ]
    )
    normalized = normalize_product_text(category, text)
    attributes = normalized.get("attributes")
    if not isinstance(attributes, dict):
        attributes = {}
    metadata: dict[str, Any] = {
        "category": normalized.get("category") or category,
        "canonical_key": normalized.get("canonical_key"),
        "attributes": attributes,
    }
    brand = attributes.get("brand") or attributes.get("vendor")
    if brand:
        metadata["brand"] = brand
    model = attributes.get("model") or attributes.get("chip_model") or attributes.get("exact_sku")
    if model:
        metadata["model"] = model
    return metadata


class MarketplaceScanner:
    def __init__(
        self,
        mission_service: MarketplaceMissionService,
        *,
        price_service: MarketplacePriceIntelligenceService | None = None,
        cdp_url: str | None = None,
        timeout_ms: int | None = None,
        detail_pacing_seconds: tuple[float, float] | None = None,
        detail_timeout_backoff_seconds: tuple[float, float] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.mission_service = mission_service
        self.price_service = price_service
        self.cdp_url = str(cdp_url or "").strip() or DEFAULT_MARKETPLACE_CDP_URL
        self.timeout_ms = int(timeout_ms or DEFAULT_MARKETPLACE_TIMEOUT_MS)
        self.detail_pacing_seconds = self._normalize_delay_range(
            detail_pacing_seconds,
            DEFAULT_DETAIL_PACING_SECONDS,
        )
        self.detail_timeout_backoff_seconds = self._normalize_delay_range(
            detail_timeout_backoff_seconds,
            DEFAULT_DETAIL_TIMEOUT_BACKOFF_SECONDS,
        )
        self._rng = rng or random.Random()

    def run_sync(
        self,
        *,
        mission_id: str | None = None,
        progress: Callable[[str, float | None], None] | None = None,
        log: Callable[[str], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        return asyncio.run(
            self._run_async(
                mission_id=mission_id,
                progress=progress,
                log=log,
                cancel_requested=cancel_requested,
            )
        )

    def calibrate_product_price_sync(
        self,
        *,
        tracked_product_id: str,
        progress: Callable[[str, float | None], None] | None = None,
        log: Callable[[str], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        return asyncio.run(
            self.calibrate_product_price(
                tracked_product_id=tracked_product_id,
                progress=progress,
                log=log,
                cancel_requested=cancel_requested,
            )
        )

    async def calibrate_product_price(
        self,
        *,
        tracked_product_id: str,
        progress: Callable[[str, float | None], None] | None = None,
        log: Callable[[str], None] | None = None,
        cancel_requested: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        self._raise_if_cancelled(cancel_requested)
        price_service = self._price_service()
        product = price_service.get_tracked_product(tracked_product_id)
        if product is None:
            raise ValueError(f"tracked_product_id not found: {tracked_product_id}")

        queries = _tracked_product_search_queries(product)
        query = queries[0] if queries else _tracked_product_search_query(product)
        health = check_marketplace_browser_health(
            cdp_url=self.cdp_url,
            timeout_ms=self.timeout_ms,
        )
        if not marketplace_scan_health_allows_execution(health):
            raise RuntimeError(str(health.get("detail") or health.get("status") or "marketplace browser is not ready"))

        if log:
            log(f"Starting calibration for: {product['canonical_key']} ({tracked_product_id})")

        stats = {
            "tracked_product_id": tracked_product_id,
            "canonical_key": product["canonical_key"],
            "query": query,
            "query_variants": queries,
            "location_anchors_scanned": [],
            "listings_seen": 0,
            "observations_ingested": 0,
            "benchmark_rebuilt": False,
        }

        async def perform_calibration(context: Any):
            if progress:
                progress(f"Searching for {query}", 10.0)
            
            cards: list[dict[str, Any]] = []
            seen_listing_ids: set[str] = set()
            for query_index, search_query in enumerate(queries, start=1):
                if progress:
                    progress(
                        f"Searching for {search_query}",
                        10.0 + ((query_index - 1) / max(len(queries), 1)) * 50.0,
                    )
                for location_name in _scan_location_anchors(["Australia"]):
                    self._raise_if_cancelled(cancel_requested)
                    page = await context.new_page()
                    try:
                        page.set_default_timeout(self.timeout_ms)
                        search_url = build_marketplace_search_url(
                            search_query,
                            location_name=location_name,
                            radius_km=CALIBRATION_MARKETPLACE_RADIUS_KM,
                        )
                        await page.goto(search_url, wait_until="domcontentloaded")
                        await page.wait_for_timeout(2_000)
                        location_cards = await self._collect_cards_for_query(
                            page=page,
                            query=search_query,
                            card_target=12,
                            seen_listing_ids=seen_listing_ids,
                            log=log,
                            cancel_requested=cancel_requested,
                        )
                        cards.extend(location_cards)
                        location_probe = f"{location_name}::{search_query}"
                        stats["location_anchors_scanned"].append(location_probe)
                    finally:
                        try:
                            await page.close()
                        except Exception:
                            pass

            stats["listings_seen"] = len(cards)
            if log:
                log(f"  collected {len(cards)} listings for calibration")

            for card in cards:
                self._raise_if_cancelled(cancel_requested)
                price_value = parse_marketplace_price(card.get("price"))
                if price_value is None or price_value <= 0:
                    continue
                title = str(card.get("title") or "")
                raw_text = " ".join(str(item or "") for item in card.get("text_fragments") or [])
                prefilter = prefilter_marketplace_card(
                    {
                        "title": title,
                        "price": card.get("price"),
                        "location": card.get("location"),
                        "text_fragments": card.get("text_fragments") or [],
                    },
                    {
                        "hard_filters": {
                            "location_names": ["Australia"],
                            "include_keywords": [],
                            "forbidden_terms": [],
                            "exclude_keywords": [],
                        },
                        "soft_preferences": {},
                    },
                )
                if prefilter.get("prefilter_decision") == "reject":
                    continue
                junk = detect_listing_junk(
                    title=f"{title} {raw_text}",
                    price=price_value,
                    category=product["category"],
                )
                if junk["is_junk"]:
                    continue

                # Basic card-level match check
                confidence = price_service.variant_match_confidence(
                    match={
                        "title": title,
                        "raw_text_snapshot": raw_text,
                        "price": card.get("price"),
                    },
                    tracked_product=product,
                )
                
                if confidence >= VALUE_RESALE_MIN_VARIANT_CONFIDENCE:
                    try:
                        observation = price_service.ingest_observation_if_new_or_changed({
                            "tracked_product_id": tracked_product_id,
                            "source": "facebook_calibration",
                            "observed_at": _now_iso(),
                            "source_listing_id": extract_marketplace_listing_id(card["listing_url"]),
                            "title": title,
                            "price": price_value,
                            "url": card["listing_url"],
                            "location": card.get("location"),
                            "match_confidence": confidence,
                            "capture_mode": "scanner",
                            "provenance": {
                                "query": card.get("query") or query,
                                "calibration": True,
                            },
                            "review_state": "pending_review",
                        })
                        if observation.get("created"):
                            stats["observations_ingested"] += 1
                    except Exception as exc:
                        if log:
                            log(f"    failed to ingest calibration observation: {exc}")

            if progress:
                progress("Rebuilding benchmark", 90.0)
            snapshot = price_service.rebuild_benchmark_snapshot(tracked_product_id)
            stats["benchmark_rebuilt"] = True
            stats["benchmark_sample_size"] = snapshot.get("total_sample_size")
            
            if progress:
                progress("Calibration complete", 100.0)

        if use_direct_marketplace_runtime():
            async with open_direct_marketplace_context() as (context, _browser_family, _profile_path):
                await perform_calibration(context)
        else:
            from playwright.async_api import async_playwright
            async with async_playwright() as playwright:
                browser = await _await_marketplace_probe(
                    playwright.chromium.connect_over_cdp(self.cdp_url),
                    stage="CDP attach",
                    timeout_seconds=_probe_timeout_seconds(self.timeout_ms),
                )
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                await perform_calibration(context)

        return stats

    async def _run_async(
        self,
        *,
        mission_id: str | None,
        progress: Callable[[str, float | None], None] | None,
        log: Callable[[str], None] | None,
        cancel_requested: Callable[[], bool] | None,
    ) -> dict[str, Any]:
        self._raise_if_cancelled(cancel_requested)
        health = check_marketplace_browser_health(
            cdp_url=self.cdp_url,
            timeout_ms=self.timeout_ms,
        )
        self._raise_if_cancelled(cancel_requested)
        if not marketplace_scan_health_allows_execution(health):
            raise RuntimeError(str(health.get("detail") or health.get("status") or "marketplace browser is not ready"))

        if mission_id:
            mission = self.mission_service.get_mission(mission_id)
            missions = [mission] if mission else []
        else:
            missions = self.mission_service.list_missions(statuses=["active"])

        if not missions:
            return {
                "missions_scanned": 0,
                "matches_saved": 0,
                "alerts_created": 0,
                "listings_seen": 0,
                "harvested_cards": 0,
                "rejected_by_location": 0,
                "rejected_by_requirement_fit": 0,
                "rejected_by_candidate_mismatch": 0,
                "detail_pages_opened": 0,
                "detail_rejection_reasons": {},
                "missions_aborted": 0,
                "summary": "No active Marketplace missions to scan.",
            }

        total_missions = len(missions)
        aggregate = {
            "missions_scanned": total_missions,
            "matches_saved": 0,
            "alerts_created": 0,
            "listings_seen": 0,
            "harvested_cards": 0,
            "rejected_by_location": 0,
            "rejected_by_requirement_fit": 0,
            "rejected_by_candidate_mismatch": 0,
            "detail_pages_opened": 0,
            "detail_rejection_reasons": {},
            "missions_aborted": 0,
            "mission_summaries": [],
        }

        if use_direct_marketplace_runtime():
            async with open_direct_marketplace_context() as (context, _browser_family, _profile_path):
                for index, mission in enumerate(missions, start=1):
                    self._raise_if_cancelled(cancel_requested)
                    if progress:
                        progress(
                            f"Scanning {mission['name']}",
                            round(((index - 1) / max(total_missions, 1)) * 100, 1),
                        )
                    if log:
                        log(f"[mission {index}/{total_missions}] {mission['name']}")
                    result = await self._scan_mission(
                        context=context,
                        mission=mission,
                        log=log,
                        cancel_requested=cancel_requested,
                    )
                    aggregate["matches_saved"] += result["matches_saved"]
                    aggregate["alerts_created"] += result["alerts_created"]
                    aggregate["listings_seen"] += result["listings_seen"]
                    aggregate["harvested_cards"] += result.get("harvested_cards", 0)
                    aggregate["rejected_by_location"] += result.get(
                        "rejected_by_location",
                        0,
                    )
                    aggregate["rejected_by_requirement_fit"] += result.get(
                        "rejected_by_requirement_fit",
                        0,
                    )
                    aggregate["rejected_by_candidate_mismatch"] += result.get(
                        "rejected_by_candidate_mismatch",
                        0,
                    )
                    aggregate["detail_pages_opened"] += result["detail_pages_opened"]
                    _merge_detail_reasons(
                        aggregate["detail_rejection_reasons"],
                        result.get("detail_rejection_reasons"),
                    )
                    if result.get("scan_status") == "aborted":
                        aggregate["missions_aborted"] += 1
                    aggregate["mission_summaries"].append(result)
                    if result.get("scan_status") != "aborted":
                        self.mission_service.mark_last_scan(mission["mission_id"])
        else:
            try:
                from playwright.async_api import async_playwright
            except Exception as exc:
                raise RuntimeError("Playwright is not installed in this environment.") from exc

            async with async_playwright() as playwright:
                try:
                    self._raise_if_cancelled(cancel_requested)
                    browser = await _await_marketplace_probe(
                        playwright.chromium.connect_over_cdp(self.cdp_url),
                        stage="CDP attach",
                        timeout_seconds=_probe_timeout_seconds(self.timeout_ms),
                    )
                except MarketplaceBrowserProbeTimeout as exc:
                    raise RuntimeError(
                        _marketplace_probe_timeout_detail(
                            cdp_url=self.cdp_url,
                            timeout_ms=self.timeout_ms,
                            stage=exc.stage,
                        )
                    ) from exc
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                for index, mission in enumerate(missions, start=1):
                    self._raise_if_cancelled(cancel_requested)
                    if progress:
                        progress(
                            f"Scanning {mission['name']}",
                            round(((index - 1) / max(total_missions, 1)) * 100, 1),
                        )
                    if log:
                        log(f"[mission {index}/{total_missions}] {mission['name']}")
                    result = await self._scan_mission(
                        context=context,
                        mission=mission,
                        log=log,
                        cancel_requested=cancel_requested,
                    )
                    aggregate["matches_saved"] += result["matches_saved"]
                    aggregate["alerts_created"] += result["alerts_created"]
                    aggregate["listings_seen"] += result["listings_seen"]
                    aggregate["harvested_cards"] += result.get("harvested_cards", 0)
                    aggregate["rejected_by_location"] += result.get(
                        "rejected_by_location",
                        0,
                    )
                    aggregate["rejected_by_requirement_fit"] += result.get(
                        "rejected_by_requirement_fit",
                        0,
                    )
                    aggregate["rejected_by_candidate_mismatch"] += result.get(
                        "rejected_by_candidate_mismatch",
                        0,
                    )
                    aggregate["detail_pages_opened"] += result["detail_pages_opened"]
                    _merge_detail_reasons(
                        aggregate["detail_rejection_reasons"],
                        result.get("detail_rejection_reasons"),
                    )
                    if result.get("scan_status") == "aborted":
                        aggregate["missions_aborted"] += 1
                    aggregate["mission_summaries"].append(result)
                    if result.get("scan_status") != "aborted":
                        self.mission_service.mark_last_scan(mission["mission_id"])

        if progress:
            progress("Marketplace scan complete", 100.0)
        aggregate["summary"] = (
            f"Scanned {aggregate['missions_scanned']} mission(s), saw "
            f"{aggregate['listings_seen']} listings, saved {aggregate['matches_saved']} "
            f"match(es), created {aggregate['alerts_created']} alert(s), "
            f"opened {aggregate['detail_pages_opened']} detail page(s), and "
            f"aborted {aggregate['missions_aborted']} mission(s)."
        )
        detail_reason_summary = _format_detail_reasons(
            aggregate["detail_rejection_reasons"]
        )
        if detail_reason_summary:
            aggregate["summary"] += f" Detail rejections: {detail_reason_summary}."
        return aggregate

    async def _scan_mission(
        self,
        *,
        context: Any,
        mission: dict[str, Any],
        log: Callable[[str], None] | None,
        cancel_requested: Callable[[], bool] | None,
    ) -> dict[str, Any]:
        mission_id = mission["mission_id"]
        try:
            mission = self._prepare_mission_for_scan(mission)
        except RequirementMissionPreparationError as exc:
            if log:
                log(f"  requirement preparation failed: {exc.reason}")
            return self._mission_abort_result(mission, exc.reason)

        feedback_notes = self.mission_service.list_not_interested_feedback_notes(mission_id)
        if feedback_notes:
            mission = {**mission, "_feedback_notes": feedback_notes}
            if log:
                log(f"  loaded {len(feedback_notes)} rejection note(s) into scoring context")

        profile = marketplace_requirement_profile(mission)
        requirement_driven = (
            isinstance(profile, dict)
            and profile.get("mode") == "requirement_driven"
        )
        candidate_contexts = (
            marketplace_candidate_contexts(
                self.mission_service,
                self._price_service(),
                mission_id,
            )
            if requirement_driven
            else []
        )
        search_pack = build_marketplace_search_pack(mission)
        location_scope = search_pack.get("location_scope") or {}
        scope_locations = [
            str(value).strip()
            for value in list(location_scope.get("location_names") or [])
            if str(value).strip()
        ]
        hard_filters = dict(mission.get("hard_filters") or {})
        hard_locations = [
            str(value).strip()
            for value in list(hard_filters.get("location_names") or [])
            if str(value).strip()
        ]
        normalized_hard_locations = normalize_marketplace_location_names(hard_locations)
        if normalized_hard_locations != hard_locations:
            hard_filters["location_names"] = normalized_hard_locations
            mission = self.mission_service.update_mission(
                mission_id,
                {"hard_filters": hard_filters},
            )
            hard_locations = normalized_hard_locations
            if log:
                log(
                    "  normalized mission locations: "
                    + ", ".join(normalized_hard_locations)
                )
        if not hard_locations and scope_locations:
            hard_filters["location_names"] = normalize_marketplace_location_names(
                scope_locations
            )
            mission = self.mission_service.update_mission(
                mission_id,
                {"hard_filters": hard_filters},
            )
            if log:
                log(
                    "  updated mission location scope: "
                    + ", ".join(hard_filters["location_names"])
                )
            hard_locations = list(hard_filters["location_names"])
        if not hard_locations:
            raise RuntimeError(
                f'Mission "{mission["name"]}" is missing location_names. '
                "Set mission locations before scanning."
            )

        search_locations = _scan_location_anchors(hard_locations)
        radius_km = location_scope.get("radius_km")
        if radius_km is None:
            hard_radius_km = hard_filters.get("radius_km")
            radius_km = (
                hard_radius_km
                if hard_radius_km is not None
                else DEFAULT_MARKETPLACE_RADIUS_KM
            )
        prefilter_mission = (
            {**mission, "_requirement_candidate_contexts": candidate_contexts}
            if requirement_driven
            else mission
        )
        queries = flatten_marketplace_queries(
            search_pack,
            max_queries=int(mission["search_config"]["max_queries_per_run"]),
        )
        price_band = self.mission_service.price_band(mission_id)
        seen_ids_this_run: set[str] = set()
        matches_saved = 0
        alerts_created = 0
        listings_seen = 0
        harvested_cards = 0
        rejected_by_location = 0
        rejected_by_requirement_fit = 0
        rejected_by_candidate_mismatch = 0
        detail_pages_opened = 0
        detail_rejection_reasons: dict[str, int] = {}
        scan_started = time.monotonic()
        detail_budget = int(mission["scan_config"]["detail_open_target"])
        detail_used = 0
        consecutive_detail_timeouts = 0

        for query_index, query in enumerate(queries):
            self._raise_if_cancelled(cancel_requested)
            if time.monotonic() - scan_started > int(
                mission["scan_config"]["run_time_budget_minutes"]
            ) * 60:
                if log:
                    log("Time budget reached; stopping mission scan.")
                break

            search_location = search_locations[query_index % len(search_locations)]
            if log:
                radius_suffix = f", radius={radius_km}km" if radius_km is not None else ""
                log(f"  query: {query} (location={search_location}{radius_suffix})")
            page = await context.new_page()
            try:
                page.set_default_timeout(self.timeout_ms)
                await page.goto(
                    build_marketplace_search_url(
                        query,
                        location_name=search_location,
                        radius_km=radius_km,
                    ),
                    wait_until="domcontentloaded",
                )
                await page.wait_for_timeout(1_200)
                cards = await self._collect_cards_for_query(
                    page=page,
                    query=query,
                    card_target=int(mission["scan_config"]["candidate_card_target"]),
                    seen_listing_ids=seen_ids_this_run,
                    log=log,
                    cancel_requested=cancel_requested,
                )
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

            listings_seen += len(cards)
            harvested_cards += len(cards)
            ranked_cards: list[dict[str, Any]] = []
            for card in cards:
                prefilter = prefilter_marketplace_card(card, prefilter_mission)
                if prefilter["prefilter_decision"] != "open":
                    value_candidate = self._resolve_value_resale_candidate(
                        self._card_value_listing(card),
                        mission=mission,
                        candidate_contexts=candidate_contexts,
                    )
                    if (
                        value_candidate is not None
                        and self._allows_value_prefilter_override(prefilter)
                    ):
                        ranked_cards.append(
                            self._value_prefilter_card(
                                {**card, **prefilter},
                                minimum_priority=80,
                            )
                        )
                        continue
                    bucket = _rejection_bucket(prefilter.get("prefilter_reasons"))
                    if bucket == "location":
                        rejected_by_location += 1
                    else:
                        rejected_by_requirement_fit += 1
                    continue
                ranked_cards.append({**card, **prefilter})

            ranked_cards.sort(key=lambda item: item["open_priority"], reverse=True)
            ranked_cards = self._prioritize_value_cards(
                ranked_cards,
                mission=mission,
                candidate_contexts=candidate_contexts,
            )
            for card in ranked_cards:
                self._raise_if_cancelled(cancel_requested)
                if detail_used >= detail_budget:
                    break
                detail_used += 1
                detail_pages_opened += 1
                if log:
                    log(f"    inspecting: {card['title']} ({card['listing_url']})")
                try:
                    detail = await self._inspect_listing_detail(
                        context=context,
                        listing_url=card["listing_url"],
                        mission_id=mission_id,
                        cancel_requested=cancel_requested,
                    )
                except MarketplaceScanCancelled:
                    raise
                except Exception as exc:
                    detail_error = str(exc) or exc.__class__.__name__
                    if self._is_detail_timeout_error(detail_error):
                        consecutive_detail_timeouts += 1
                    else:
                        consecutive_detail_timeouts = 0
                    post_detail_outcome = {
                        "stage": "detail",
                        "reason_code": "detail_inspection_failed",
                        "reason_detail": detail_error,
                        "evidence": {
                            "listing_url": card.get("listing_url"),
                            "title": card.get("title"),
                        },
                    }
                    _increment_detail_reason(
                        detail_rejection_reasons,
                        post_detail_outcome["reason_code"],
                    )
                    if log:
                        log(f"      detail inspection failed: {detail_error}")
                    self.mission_service.upsert_seen_listing(
                        mission_id,
                        {
                            "listing_id": card.get("listing_id")
                            or extract_marketplace_listing_id(card.get("listing_url")),
                            "listing_url": card.get("listing_url"),
                            "title": card.get("title"),
                            "price_text": card.get("price"),
                            "price_value": parse_marketplace_price(card.get("price")),
                            "location": card.get("location"),
                            "query_text": query,
                            "raw_snapshot": {
                                **card,
                                "post_detail_outcome": post_detail_outcome,
                            },
                            "last_status": post_detail_outcome["reason_code"],
                            "last_error": detail_error,
                            "match_id": None,
                        },
                    )
                    if consecutive_detail_timeouts:
                        backoff_seconds = self._detail_timeout_backoff_seconds(
                            consecutive_detail_timeouts
                        )
                        if backoff_seconds > 0:
                            if log:
                                log(
                                    "      backing off after detail timeout "
                                    f"({backoff_seconds:.1f}s)"
                                )
                            await self._sleep_with_cancel(
                                backoff_seconds,
                                cancel_requested,
                            )
                    continue

                consecutive_detail_timeouts = 0
                price_evidence = _resolved_price_evidence(card=card, detail=detail)
                scored_detail = _detail_with_resolved_price(detail, price_evidence)

                score = evaluate_marketplace_listing(
                    scored_detail,
                    mission,
                    observed_price_band=price_band,
                )
                value_resale_candidate = self._resolve_value_resale_candidate(
                    scored_detail,
                    mission=mission,
                    candidate_contexts=candidate_contexts,
                )
                if log:
                    log(f"      score: {score['score']} ({score['decision_band']})")
                detail_hash = listing_material_hash(scored_detail)
                candidate_resolution: dict[str, Any] | None = None
                post_detail_outcome: dict[str, Any] | None = None
                if score["decision_band"] == "reject":
                    if value_resale_candidate is not None and self._allows_value_resale_override(score):
                        score = self._value_resale_score(
                            score,
                            value_resale_candidate,
                        )
                    else:
                        value_resale_candidate = None
                        bucket = _rejection_bucket(score.get("reasons_against"))
                        if bucket == "location":
                            rejected_by_location += 1
                        else:
                            rejected_by_requirement_fit += 1
                    if requirement_driven and value_resale_candidate is None:
                        post_detail_outcome = classify_requirement_detail_outcome(
                            scored_detail,
                            mission,
                            score,
                            candidate_contexts=candidate_contexts,
                        )
                        _increment_detail_reason(
                            detail_rejection_reasons,
                            (post_detail_outcome or {}).get("reason_code"),
                        )
                        if log and post_detail_outcome:
                            log(
                                "      detail rejected: "
                                + str(post_detail_outcome["reason_code"])
                            )
                elif requirement_driven:
                    candidate_resolution = self._resolve_requirement_candidate(
                        scored_detail,
                        candidate_contexts,
                    )
                    if not candidate_resolution.get("matched"):
                        if value_resale_candidate is not None:
                            score = self._value_resale_score(
                                score,
                                value_resale_candidate,
                            )
                        else:
                            rejected_by_candidate_mismatch += 1
                            post_detail_outcome = {
                                "stage": "detail",
                                "reason_code": "detail_candidate_unmatched",
                                "reason_detail": str(
                                    candidate_resolution.get("warning")
                                    or "Listing did not match a requirement candidate."
                                ),
                                "evidence": _candidate_resolution_metadata(
                                    candidate_resolution
                                )
                                or {},
                            }
                            _increment_detail_reason(
                                detail_rejection_reasons,
                                post_detail_outcome["reason_code"],
                            )
                            if log:
                                log(
                                    "      candidate mismatch: "
                                    + str(
                                        candidate_resolution.get("warning")
                                        or "listing did not match a requirement candidate"
                                    )
                                )
                            self.mission_service.upsert_seen_listing(
                                mission_id,
                                {
                                    "listing_id": detail["listing_id"],
                                    "listing_url": detail["listing_url"],
                                    "title": detail["title"],
                                    "price_text": scored_detail.get("price"),
                                    "price_value": parse_marketplace_price(
                                        scored_detail.get("price")
                                    ),
                                    "location": detail.get("location"),
                                    "seller_name": detail.get("seller_name"),
                                    "query_text": query,
                                    "detail_hash": detail_hash,
                                    "raw_snapshot": {
                                        **detail,
                                        "price_evidence": price_evidence,
                                        "score": score,
                                        "candidate_resolution": candidate_resolution,
                                        "post_detail_outcome": post_detail_outcome,
                                    },
                                    "last_status": "candidate_unmatched",
                                    "last_score": score["score"],
                                    "last_decision_band": score["decision_band"],
                                    "last_error": str(
                                        candidate_resolution.get("warning")
                                        or "candidate mismatch"
                                    ),
                                    "match_id": None,
                                },
                            )
                            continue
                previous_seen = self.mission_service.get_seen_listing(
                    mission_id, detail["listing_id"]
                )
                previous_match = None
                if previous_seen and previous_seen.get("match_id"):
                    previous_match = self.mission_service.get_match(previous_seen["match_id"])
                material_reasons = material_change_reasons(
                    previous_seen,
                    new_hash=detail_hash,
                    new_price_value=parse_marketplace_price(scored_detail.get("price")),
                    new_score=int(score["score"]),
                    new_band=str(score["decision_band"]),
                )

                match_record = None
                alert_record = None
                if score["decision_band"] in {"candidate", "strong_match"}:
                    match_status = "new"
                    if previous_match is not None:
                        previous_status = str(previous_match.get("status") or "new")
                        if previous_status == "dismissed" and not material_reasons:
                            match_status = "dismissed"
                        elif material_reasons:
                            match_status = "new"
                        else:
                            match_status = previous_status
                    match_record = self.mission_service.upsert_match(
                        {
                            "mission_id": mission_id,
                            "listing_id": detail["listing_id"],
                            "listing_url": detail["listing_url"],
                            "title": detail["title"],
                            "price": scored_detail.get("price"),
                            "price_value": parse_marketplace_price(
                                scored_detail.get("price")
                            ),
                            "location": detail.get("location"),
                            "seller_name": detail.get("seller_name"),
                            "captured_at": detail["captured_at"],
                            "score": score["score"],
                            "decision_band": score["decision_band"],
                            "reasons_for": score["reasons_for"],
                            "reasons_against": score["reasons_against"],
                            "confidence": score["confidence"],
                            "raw_text_snapshot": detail["raw_text_snapshot"],
                            "screenshot_path": detail["screenshot_path"],
                            "listing_media": detail.get("listing_media") or [],
                            "status": match_status,
                            "metadata": {
                                "query": query,
                                "material_change_reasons": material_reasons,
                                "detail_hash": detail_hash,
                                "price_evidence": price_evidence,
                                **_listing_product_metadata(mission, scored_detail),
                                "candidate_resolution": _candidate_resolution_metadata(
                                    candidate_resolution
                                ),
                                **(
                                    {
                                        "value_resale_candidate": self._value_resale_metadata(
                                            value_resale_candidate
                                        )
                                    }
                                    if value_resale_candidate is not None
                                    else {}
                                ),
                            },
                        }
                    )
                    matches_saved += 1
                    if value_resale_candidate is not None:
                        self._persist_value_resale_assessment(
                            match_record,
                            value_resale_candidate,
                            log=log,
                        )
                    self._persist_match_price_observation(
                        match_record=match_record,
                        mission=mission,
                        candidate_resolution=candidate_resolution,
                        value_resale_candidate=value_resale_candidate,
                        price_evidence=price_evidence,
                        query=query,
                        log=log,
                    )

                    should_alert = score["decision_band"] == "strong_match" or (
                        score["decision_band"] == "candidate"
                        and bool(mission["scan_config"]["aggressive_alerting"])
                    ) or value_resale_candidate is not None
                    latest_alert = (
                        self.mission_service.latest_alert_for_match(match_record["match_id"])
                        if match_record
                        else None
                    )
                    if should_alert and (
                        previous_seen is None or material_reasons or latest_alert is None
                    ):
                        alert_record = self.mission_service.create_alert(
                            mission_id=mission_id,
                            match_id=match_record["match_id"],
                            trigger_reason=(
                                "value_resale_candidate"
                                if value_resale_candidate is not None
                                else ",".join(material_reasons or ["new_listing"])
                            ),
                            metadata={
                                "detail_hash": detail_hash,
                                "query": query,
                                "decision_band": score["decision_band"],
                                "price_evidence": price_evidence,
                                **(
                                    {
                                        "value_resale_candidate": self._value_resale_metadata(
                                            value_resale_candidate
                                        )
                                    }
                                    if value_resale_candidate is not None
                                    else {}
                                ),
                            },
                        )
                        alerts_created += 1
                        if log:
                            log(
                                f"    alert: {match_record['title']} ({score['decision_band']}, score={score['score']})"
                            )

                self.mission_service.upsert_seen_listing(
                    mission_id,
                    {
                        "listing_id": detail["listing_id"],
                        "listing_url": detail["listing_url"],
                        "title": detail["title"],
                        "price_text": scored_detail.get("price"),
                        "price_value": parse_marketplace_price(scored_detail.get("price")),
                        "location": detail.get("location"),
                        "seller_name": detail.get("seller_name"),
                        "query_text": query,
                        "detail_hash": detail_hash,
                        "raw_snapshot": {
                            **detail,
                            "price_evidence": price_evidence,
                            "score": score,
                            "candidate_resolution": candidate_resolution,
                            "material_change_reasons": material_reasons,
                            **(
                                {"post_detail_outcome": post_detail_outcome}
                                if post_detail_outcome
                                else {}
                            ),
                        },
                        "last_status": (
                            "value_resale_candidate"
                            if value_resale_candidate is not None
                            else (
                                str(post_detail_outcome["reason_code"])
                                if post_detail_outcome
                                and score["decision_band"] == "reject"
                                else score["decision_band"]
                            )
                        ),
                        "last_score": score["score"],
                        "last_decision_band": score["decision_band"],
                        "last_error": (
                            str(post_detail_outcome["reason_detail"])
                            if post_detail_outcome
                            and score["decision_band"] == "reject"
                            else None
                        ),
                        "match_id": match_record["match_id"] if match_record else None,
                    },
                )

        return {
            "mission_id": mission_id,
            "mission_name": mission["name"],
            "queries": queries,
            "scan_status": "completed",
            "matches_saved": matches_saved,
            "alerts_created": alerts_created,
            "listings_seen": listings_seen,
            "harvested_cards": harvested_cards,
            "rejected_by_location": rejected_by_location,
            "rejected_by_requirement_fit": rejected_by_requirement_fit,
            "rejected_by_candidate_mismatch": rejected_by_candidate_mismatch,
            "detail_pages_opened": detail_pages_opened,
            "detail_rejection_reasons": detail_rejection_reasons,
        }

    def _prepare_mission_for_scan(self, mission: dict[str, Any]) -> dict[str, Any]:
        profile = marketplace_requirement_profile(mission)
        if isinstance(profile, dict) and profile.get("mode") != "requirement_driven":
            return mission

        prepared = prepare_requirement_driven_mission(
            self.mission_service,
            self._price_service(),
            mission,
        )
        profile = marketplace_requirement_profile(prepared)
        if not (
            isinstance(profile, dict)
            and profile.get("mode") == "requirement_driven"
        ):
            return prepared

        deployment_args = (
            prepared.get("deployment_args")
            if isinstance(prepared.get("deployment_args"), dict)
            else {}
        )
        if not list(deployment_args.get("candidate_search_terms") or []):
            raise RequirementMissionPreparationError(
                str(prepared.get("mission_id") or mission.get("mission_id") or ""),
                "no candidate search terms generated",
            )
        if not self.mission_service.list_mission_candidate_products(
            str(prepared.get("mission_id") or "")
        ):
            raise RequirementMissionPreparationError(
                str(prepared.get("mission_id") or mission.get("mission_id") or ""),
                "no candidate products generated",
            )
        return prepared

    def _price_service(self) -> MarketplacePriceIntelligenceService:
        if self.price_service is None:
            state_store = getattr(self.mission_service, "state_store", None)
            if state_store is None:
                raise RequirementMissionPreparationError(
                    "unknown",
                    "price intelligence service unavailable",
                )
            self.price_service = MarketplacePriceIntelligenceService(state_store)
        return self.price_service

    def _mission_abort_result(
        self,
        mission: dict[str, Any],
        reason: str,
    ) -> dict[str, Any]:
        return {
            "mission_id": mission.get("mission_id"),
            "mission_name": mission.get("name"),
            "queries": [],
            "scan_status": "aborted",
            "abort_reason": reason,
            "matches_saved": 0,
            "alerts_created": 0,
            "listings_seen": 0,
            "harvested_cards": 0,
            "rejected_by_location": 0,
            "rejected_by_requirement_fit": 0,
            "rejected_by_candidate_mismatch": 0,
            "detail_pages_opened": 0,
            "detail_rejection_reasons": {},
        }

    def _resolve_requirement_candidate(
        self,
        detail: dict[str, Any],
        candidate_contexts: list[dict[str, Any]],
    ) -> dict[str, Any]:
        return self._price_service().resolve_match_candidate(
            {
                "title": detail.get("title"),
                "raw_text_snapshot": detail.get("raw_text_snapshot"),
                "price": detail.get("price"),
            },
            candidate_contexts,
        )

    def _prioritize_value_cards(
        self,
        cards: list[dict[str, Any]],
        *,
        mission: dict[str, Any],
        candidate_contexts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        prioritized: list[dict[str, Any]] = []
        for card in cards:
            value_candidate = self._resolve_value_resale_candidate(
                self._card_value_listing(card),
                mission=mission,
                candidate_contexts=candidate_contexts,
            )
            if value_candidate is None:
                prioritized.append(card)
                continue
            prioritized.append(self._value_prefilter_card(card))
        prioritized.sort(key=lambda item: item["open_priority"], reverse=True)
        return prioritized

    @staticmethod
    def _card_value_listing(card: dict[str, Any]) -> dict[str, Any]:
        return {
            "title": card.get("title"),
            "price": card.get("price"),
            "price_value": parse_marketplace_price(card.get("price")),
            "raw_text_snapshot": " ".join(
                str(item) for item in card.get("text_fragments") or []
            ),
        }

    @staticmethod
    def _value_prefilter_card(
        card: dict[str, Any],
        *,
        minimum_priority: int = 0,
    ) -> dict[str, Any]:
        reasons = list(card.get("prefilter_reasons") or [])
        if VALUE_RESALE_PREFILTER_REASON not in reasons:
            reasons.append(VALUE_RESALE_PREFILTER_REASON)
        return {
            **card,
            "open_priority": max(
                minimum_priority,
                min(100, int(card.get("open_priority") or 0) + 30),
            ),
            "prefilter_reasons": reasons,
        }

    def _resolve_value_resale_candidate(
        self,
        listing: dict[str, Any],
        *,
        mission: dict[str, Any],
        candidate_contexts: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        best: dict[str, Any] | None = None
        for context in self._value_candidate_contexts(
            mission=mission,
            candidate_contexts=candidate_contexts,
        ):
            product = context.get("tracked_product")
            if not isinstance(product, dict):
                continue
            value_context = self._price_service().assess_match_value(
                match=listing,
                tracked_product=product,
                snapshot=(
                    context.get("benchmark_snapshot")
                    if isinstance(context.get("benchmark_snapshot"), dict)
                    else None
                ),
            )
            if not self._is_value_resale_candidate(value_context):
                continue
            ranked = {
                **context,
                "value_context": value_context,
                "_sort_key": (
                    float(value_context.get("value_score") or 0.0),
                    float(value_context.get("variant_match_confidence") or 0.0),
                    float(value_context.get("used_median") or 0.0),
                ),
            }
            if best is None or ranked["_sort_key"] > best["_sort_key"]:
                best = ranked
        if best is None:
            return None
        best.pop("_sort_key", None)
        return best

    def _value_candidate_contexts(
        self,
        *,
        mission: dict[str, Any],
        candidate_contexts: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        contexts: list[dict[str, Any]] = []
        seen_product_ids: set[str] = set()

        def append_context(
            product: dict[str, Any] | None,
            *,
            source: str,
            candidate: dict[str, Any] | None = None,
            snapshot: dict[str, Any] | None = None,
        ) -> None:
            if not isinstance(product, dict):
                return
            product_id = str(product.get("tracked_product_id") or "")
            if not product_id or product_id in seen_product_ids:
                return
            seen_product_ids.add(product_id)
            contexts.append(
                {
                    "tracked_product": product,
                    "candidate": candidate or {},
                    "benchmark_snapshot": (
                        snapshot
                        if isinstance(snapshot, dict)
                        else self._price_service().latest_benchmark_snapshot(product_id)
                    ),
                    "value_source": source,
                }
            )

        for context in candidate_contexts:
            if not isinstance(context, dict):
                continue
            append_context(
                context.get("tracked_product"),
                source="requirement_candidate_benchmark",
                candidate=(
                    context.get("candidate")
                    if isinstance(context.get("candidate"), dict)
                    else None
                ),
                snapshot=(
                    context.get("benchmark_snapshot")
                    if isinstance(context.get("benchmark_snapshot"), dict)
                    else None
                ),
            )

        mission_id = str(mission.get("mission_id") or "")
        if mission_id:
            link = self.mission_service.get_primary_tracked_product_link(mission_id)
            if link is not None:
                append_context(
                    self._price_service().get_tracked_product(
                        str(link.get("tracked_product_id") or "")
                    ),
                    source="primary_tracked_product_benchmark",
                )

        category = _marketplace_category(mission)
        if category:
            for product in self._price_service().list_tracked_products(
                status="active",
                category=category,
            ):
                append_context(product, source="tracked_product_benchmark")

        return contexts

    @staticmethod
    def _is_value_resale_candidate(value_context: dict[str, Any]) -> bool:
        if value_context.get("state") != "scored":
            return False
        variant_confidence = float(
            value_context.get("variant_match_confidence") or 0.0
        )
        if variant_confidence < VALUE_RESALE_MIN_VARIANT_CONFIDENCE:
            return False
        value_score = value_context.get("value_score")
        used_median = value_context.get("used_median")
        listing_price = parse_marketplace_price(value_context.get("listing_price"))
        if value_score is None or used_median is None or listing_price is None:
            return False
        if float(value_score) < VALUE_RESALE_MIN_SCORE:
            return False
        fair_low = value_context.get("fair_low")
        return listing_price < float(used_median) or (
            fair_low is not None and listing_price <= float(fair_low)
        )

    @staticmethod
    def _allows_value_resale_override(score: dict[str, Any]) -> bool:
        reasons = " ".join(str(item) for item in score.get("reasons_against") or [])
        lowered = reasons.lower()
        blocked_signals = (
            "location",
            "mission area",
            "forbidden",
            "condition",
            "parts",
            "repair",
            "broken",
            "not working",
        )
        return not any(signal in lowered for signal in blocked_signals)

    @staticmethod
    def _allows_value_prefilter_override(prefilter: dict[str, Any]) -> bool:
        reasons = " ".join(
            str(item) for item in prefilter.get("prefilter_reasons") or []
        ).lower()
        if "price filter" not in reasons:
            return False
        blocked_signals = (
            "location",
            "excluded",
            "forbidden",
            "obvious junk",
            "condition",
            "parts",
            "repair",
            "broken",
            "not working",
        )
        return not any(signal in reasons for signal in blocked_signals)

    @staticmethod
    def _value_resale_score(
        score: dict[str, Any],
        value_candidate: dict[str, Any],
    ) -> dict[str, Any]:
        value_context = value_candidate["value_context"]
        value_score = int(float(value_context.get("value_score") or 0.0))
        product = value_candidate.get("tracked_product") or {}
        reason = (
            "Potential buy/resell candidate: listing is under the tracked product "
            f"used-market median for {product.get('canonical_key') or 'the matched product'}"
        )
        return {
            **score,
            "eligibility": "pass",
            "score": max(int(score.get("score") or 0), min(84, value_score)),
            "decision_band": (
                score.get("decision_band")
                if score.get("decision_band") in {"candidate", "strong_match"}
                else "candidate"
            ),
            "reasons_for": [*list(score.get("reasons_for") or []), reason],
            "reasons_against": [
                *list(score.get("reasons_against") or []),
                "Explicit mission fit still requires manual review",
            ],
            "confidence": max(float(score.get("confidence") or 0.0), 0.65),
        }

    @staticmethod
    def _value_resale_metadata(value_candidate: dict[str, Any]) -> dict[str, Any]:
        product = value_candidate.get("tracked_product") or {}
        value_context = value_candidate.get("value_context") or {}
        return {
            "flag": "value_resale_candidate",
            "value_source": value_candidate.get("value_source"),
            "tracked_product_id": product.get("tracked_product_id"),
            "tracked_product_name": product.get("canonical_key"),
            "benchmark_snapshot_id": value_context.get("benchmark_snapshot_id"),
            "value_score": value_context.get("value_score"),
            "value_label": value_context.get("value_label"),
            "value_confidence": value_context.get("value_confidence"),
            "used_median": value_context.get("used_median"),
            "fair_low": value_context.get("fair_low"),
            "fair_high": value_context.get("fair_high"),
            "variant_match_confidence": value_context.get("variant_match_confidence"),
        }

    def _persist_value_resale_assessment(
        self,
        match_record: dict[str, Any],
        value_candidate: dict[str, Any],
        *,
        log: Callable[[str], None] | None,
    ) -> None:
        product = value_candidate.get("tracked_product")
        if not isinstance(product, dict):
            return
        try:
            self._price_service().upsert_match_value_assessment(
                match=match_record,
                tracked_product=product,
                snapshot=(
                    value_candidate.get("benchmark_snapshot")
                    if isinstance(value_candidate.get("benchmark_snapshot"), dict)
                    else None
                ),
                context={
                    "value_source": "resale_candidate_benchmark",
                    "resale_candidate": True,
                    "matched_resale_tracked_product_id": product.get(
                        "tracked_product_id"
                    ),
                    "matched_resale_product_name": product.get("canonical_key"),
                    "candidate_match_confidence": (
                        value_candidate.get("value_context") or {}
                    ).get("variant_match_confidence"),
                    "requirement_fit_label": "resale_review",
                    "requirement_explanation": (
                        "Listing was saved because it appears under-market for a "
                        "tracked product, even though explicit mission fit may need "
                        "manual review."
                    ),
                },
            )
        except Exception as exc:
            if log:
                log(f"      value assessment persistence failed: {exc}")

    def _persist_match_price_observation(
        self,
        *,
        match_record: dict[str, Any],
        mission: dict[str, Any],
        candidate_resolution: dict[str, Any] | None,
        value_resale_candidate: dict[str, Any] | None,
        price_evidence: dict[str, Any],
        query: str,
        log: Callable[[str], None] | None,
    ) -> None:
        resolved = self._resolve_price_observation_product(
            match_record=match_record,
            mission=mission,
            candidate_resolution=candidate_resolution,
            value_resale_candidate=value_resale_candidate,
        )
        if resolved is None:
            return
        product, product_source = resolved
        price_value = match_record.get("price_value")
        if price_value is None:
            price_value = parse_marketplace_price(match_record.get("price"))
        if price_value is None:
            return
        try:
            observation = self._price_service().ingest_observation_if_new_or_changed(
                {
                    "tracked_product_id": product["tracked_product_id"],
                    "source": "facebook",
                    "observed_at": match_record.get("captured_at"),
                    "source_listing_id": match_record.get("listing_id"),
                    "title": match_record.get("title"),
                    "price": price_value,
                    "currency": "AUD",
                    "url": match_record.get("listing_url"),
                    "location": match_record.get("location"),
                    "seller_type": "private",
                    "match_confidence": match_record.get("confidence"),
                    "capture_mode": "scanner",
                    "provenance": {
                        "mission_id": match_record.get("mission_id"),
                        "match_id": match_record.get("match_id"),
                        "decision_band": match_record.get("decision_band"),
                        "score": match_record.get("score"),
                        "query": query,
                        "price_evidence": price_evidence,
                        "product_resolution": product_source,
                    },
                }
            )
            if observation.get("created"):
                self._price_service().rebuild_benchmark_snapshot(
                    product["tracked_product_id"]
                )
        except Exception as exc:
            if log:
                log(f"      price observation persistence failed: {exc}")

    def _resolve_price_observation_product(
        self,
        *,
        match_record: dict[str, Any],
        mission: dict[str, Any],
        candidate_resolution: dict[str, Any] | None,
        value_resale_candidate: dict[str, Any] | None,
    ) -> tuple[dict[str, Any], str] | None:
        if value_resale_candidate is not None:
            product = value_resale_candidate.get("tracked_product")
            if isinstance(product, dict):
                return product, "value_resale_candidate"

        if isinstance(candidate_resolution, dict) and candidate_resolution.get("matched"):
            product = candidate_resolution.get("tracked_product")
            if isinstance(product, dict):
                return product, "requirement_candidate"

        mission_id = str(mission.get("mission_id") or "")
        if not mission_id:
            return None
        link = self.mission_service.get_primary_tracked_product_link(mission_id)
        if link is None:
            return None
        product = self._price_service().get_tracked_product(
            str(link.get("tracked_product_id") or "")
        )
        if not isinstance(product, dict):
            return None
        confidence = self._price_service().variant_match_confidence(
            match=match_record,
            tracked_product=product,
        )
        if confidence < VALUE_RESALE_MIN_VARIANT_CONFIDENCE:
            return None
        return product, "primary_tracked_product"

    async def _collect_cards_for_query(
        self,
        *,
        page: Any,
        query: str,
        card_target: int,
        seen_listing_ids: set[str],
        log: Callable[[str], None] | None,
        cancel_requested: Callable[[], bool] | None,
    ) -> list[dict[str, Any]]:
        cards: list[dict[str, Any]] = []
        cards_by_id: dict[str, dict[str, Any]] = {}
        duplicate_hits = 0
        idle_rounds = 0

        while len(cards_by_id) < card_target and idle_rounds < 3 and duplicate_hits < 80:
            self._raise_if_cancelled(cancel_requested)
            snapshot = await page.evaluate(
                """
                () => {
                  const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim()
                  const priceRe = /(?:A\\$|AU\\$|USD\\s*\\$|\\$)\\s?\\d[\\d,]*(?:\\.\\d{2})?/
                  const rows = []
                  const anchors = Array.from(document.querySelectorAll('a[href*="/marketplace/item/"]'))
                  for (const anchor of anchors) {
                    const href = anchor.href || ''
                    const text = clean(anchor.innerText || anchor.textContent || '')
                    if (!href || !text) continue
                    const lines = text.split(/\\n+/).map(clean).filter(Boolean).slice(0, 8)
                    const price = lines.find((line) => priceRe.test(line)) || null
                    const title =
                      lines.find((line) => !priceRe.test(line) && line.length >= 3) ||
                      clean(anchor.getAttribute('aria-label') || '')
                    const location =
                      lines.find((line) => /vic|nsw|qld|sa|wa|tas|act|nt|km|location/i.test(line) && !priceRe.test(line)) ||
                      null
                    rows.push({
                      listing_url: href,
                      title,
                      price,
                      location,
                      text_fragments: lines,
                    })
                  }
                  return rows
                }
                """
            )
            new_cards = 0
            for raw in snapshot:
                listing_url = canonical_marketplace_listing_url(raw.get("listing_url"))
                listing_id = extract_marketplace_listing_id(listing_url)
                if not listing_id:
                    continue
                if listing_id in seen_listing_ids or listing_id in cards_by_id:
                    duplicate_hits += 1
                    continue
                cards_by_id[listing_id] = {
                    "listing_id": listing_id,
                    "listing_url": listing_url,
                    "title": str(raw.get("title") or "").strip(),
                    "price": str(raw.get("price") or "").strip() or None,
                    "location": str(raw.get("location") or "").strip() or None,
                    "text_fragments": list(raw.get("text_fragments") or []),
                    "query": query,
                }
                seen_listing_ids.add(listing_id)
                new_cards += 1
            if new_cards == 0:
                idle_rounds += 1
            else:
                idle_rounds = 0
            await page.mouse.wheel(0, 2200)
            await page.wait_for_timeout(1_100)

        cards.extend(cards_by_id.values())
        if log:
            log(f"    harvested {len(cards)} card(s) from search results")
        return cards

    async def _inspect_listing_detail(
        self,
        *,
        context: Any,
        listing_url: str,
        mission_id: str,
        cancel_requested: Callable[[], bool] | None,
    ) -> dict[str, Any]:
        self._raise_if_cancelled(cancel_requested)
        await self._sleep_with_cancel(
            self._detail_pacing_seconds(),
            cancel_requested,
        )
        page = await context.new_page()
        page.set_default_timeout(self.timeout_ms)
        screenshot_dir = MARKETPLACE_CAPTURE_ROOT / "missions" / mission_id
        screenshot_dir.mkdir(parents=True, exist_ok=True)
        captured_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        try:
            await page.goto(listing_url, wait_until="domcontentloaded")
            await page.wait_for_timeout(1_200)
            self._raise_if_cancelled(cancel_requested)
            extracted = await page.evaluate(
                """
                () => {
                  const clean = (value) => (value || '').replace(/\\s+/g, ' ').trim()
                  const dedupe = (items) => {
                    const out = []
                    const seen = new Set()
                    for (const item of items) {
                      const cleaned = clean(item)
                      if (!cleaned) continue
                      const key = cleaned.toLowerCase()
                      if (seen.has(key)) continue
                      seen.add(key)
                      out.push(cleaned)
                    }
                    return out
                  }
                  const collect = (selector) =>
                    Array.from(document.querySelectorAll(selector)).map((el) =>
                      clean(el.innerText || el.textContent || '')
                    )
                  const mediaUrls = []
                  const seenMedia = new Set()
                  const pushMedia = (value) => {
                    const cleaned = clean(value)
                    if (!cleaned) return
                    if (!/^https?:[/][/]/i.test(cleaned)) return
                    const key = cleaned.toLowerCase()
                    if (seenMedia.has(key)) return
                    seenMedia.add(key)
                    mediaUrls.push(cleaned)
                  }
                  const candidateImgs = Array.from(
                    document.querySelectorAll('img[src], img[data-src], img[srcset], img[data-srcset]')
                  )
                  for (const img of candidateImgs) {
                    const width = Number(img.naturalWidth || img.width || 0)
                    const height = Number(img.naturalHeight || img.height || 0)
                    if (width > 0 && width < 160) continue
                    if (height > 0 && height < 120) continue
                    pushMedia(img.currentSrc || img.src || '')
                    const srcSet = clean(img.getAttribute('srcset') || img.getAttribute('data-srcset') || '')
                    if (srcSet) {
                      const first = srcSet.split(',')[0]?.trim().split(/\\s+/)[0]
                      pushMedia(first)
                    }
                    if (mediaUrls.length >= 12) break
                  }
                  const ogImage = clean(document.querySelector('meta[property="og:image"]')?.content)
                  pushMedia(ogImage)
                  const visible = dedupe(
                    collect('h1,h2,h3,span,div,p,a,li').filter(
                      (text) => text.length >= 2 && text.length <= 280
                    )
                  )
                  const byHeading = (heading) => {
                    const index = visible.findIndex(
                      (text) => text.toLowerCase() === heading
                    )
                    if (index < 0) return null
                    for (let i = index + 1; i < Math.min(visible.length, index + 6); i += 1) {
                      const candidate = visible[i]
                      if (candidate && candidate.toLowerCase() !== heading) {
                        return candidate
                      }
                    }
                    return null
                  }
                  const title =
                    clean(document.querySelector('meta[property="og:title"]')?.content) ||
                    clean(document.querySelector('h1')?.textContent) ||
                    clean(document.title) ||
                    ''
                  const price =
                    visible.find((text) => /(?:A\\$|AU\\$|USD\\s*\\$|\\$)\\s?\\d[\\d,]*(?:\\.\\d{2})?/.test(text)) ||
                    clean(document.querySelector('meta[property="product:price:amount"]')?.content) ||
                    null
                  const description =
                    byHeading('description') ||
                    clean(document.querySelector('meta[property="og:description"]')?.content) ||
                    visible.find((text) => text.length >= 80) ||
                    null
                  const location =
                    visible.find((text) => /^location is approximate/i.test(text)) ||
                    byHeading('location') ||
                    null
                  const seller =
                    byHeading('seller details') ||
                    byHeading('seller information') ||
                    byHeading('seller') ||
                    null
                  return {
                    finalUrl: window.location.href || '',
                    title,
                    price,
                    description,
                    location,
                    seller,
                    rawTextLines: visible.slice(0, 120),
                    listingMedia: mediaUrls.slice(0, 12),
                  }
                }
                """
            )

            final_url = canonical_marketplace_listing_url(
                str(extracted.get("finalUrl") or listing_url)
            )
            listing_id = extract_marketplace_listing_id(final_url)
            if not listing_id:
                raise RuntimeError("Failed to resolve Marketplace listing id")
            screenshot_path = screenshot_dir / f"{listing_id}.png"
            await page.screenshot(path=str(screenshot_path), full_page=True)
            raw_text_lines = list(extracted.get("rawTextLines") or [])
            description = str(extracted.get("description") or "").strip() or None
            return {
                "listing_id": listing_id,
                "listing_url": final_url,
                "captured_at": captured_at,
                "title": str(extracted.get("title") or "Facebook Marketplace listing").strip(),
                "price": str(extracted.get("price") or "").strip() or None,
                "seller_name": str(extracted.get("seller") or "").strip() or None,
                "location": str(extracted.get("location") or "").strip() or None,
                "description": description,
                "raw_text_lines": raw_text_lines,
                "raw_text_snapshot": "\n".join(
                    line for line in [description or "", *raw_text_lines[:60]] if line
                ).strip(),
                "screenshot_path": str(screenshot_path),
                "listing_media": list(extracted.get("listingMedia") or []),
            }
        finally:
            try:
                await page.close()
            except Exception:
                pass

    @staticmethod
    def _normalize_delay_range(
        value: tuple[float, float] | None,
        default: tuple[float, float],
    ) -> tuple[float, float]:
        raw_low, raw_high = value if value is not None else default
        low = max(0.0, float(raw_low))
        high = max(0.0, float(raw_high))
        if high < low:
            low, high = high, low
        return (low, high)

    def _detail_pacing_seconds(self) -> float:
        return self._random_delay_seconds(self.detail_pacing_seconds)

    def _detail_timeout_backoff_seconds(self, consecutive_timeouts: int) -> float:
        base_seconds = self._random_delay_seconds(self.detail_timeout_backoff_seconds)
        multiplier = 2 ** max(0, consecutive_timeouts - 1)
        return min(MAX_DETAIL_TIMEOUT_BACKOFF_SECONDS, base_seconds * multiplier)

    def _random_delay_seconds(self, delay_range: tuple[float, float]) -> float:
        low, high = delay_range
        if high <= 0:
            return 0.0
        if low == high:
            return low
        return self._rng.uniform(low, high)

    @staticmethod
    def _is_detail_timeout_error(detail_error: str) -> bool:
        return bool(DETAIL_TIMEOUT_RE.search(detail_error or ""))

    async def _sleep_with_cancel(
        self,
        seconds: float,
        cancel_requested: Callable[[], bool] | None,
    ) -> None:
        if seconds <= 0:
            return
        deadline = time.monotonic() + seconds
        while True:
            self._raise_if_cancelled(cancel_requested)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            await asyncio.sleep(min(remaining, 0.5))

    def _raise_if_cancelled(
        self,
        cancel_requested: Callable[[], bool] | None,
    ) -> None:
        if cancel_requested and cancel_requested():
            raise MarketplaceScanCancelled("Marketplace scan cancelled by user request.")


class MarketplaceScanCancelled(RuntimeError):
    """Raised when a Marketplace scan is cooperatively cancelled."""
