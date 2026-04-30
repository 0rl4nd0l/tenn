from __future__ import annotations

import asyncio
import re
import time
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
from app.services.marketplace_price_intelligence import MarketplacePriceIntelligenceService
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


FACEBOOK_MARKETPLACE_ITEM_RE = re.compile(
    r"/marketplace/item/(?P<listing_id>[0-9A-Za-z]+)/?",
    re.IGNORECASE,
)
DEFAULT_MARKETPLACE_RADIUS_KM = 160
_LOCATION_COORD_OVERRIDES: dict[str, tuple[float, float]] = {
    "victoria, australia": (-37.8136, 144.9631),  # Melbourne CBD anchor
    "melbourne, australia": (-37.8136, 144.9631),
}


def extract_marketplace_listing_id(url: str) -> str | None:
    match = FACEBOOK_MARKETPLACE_ITEM_RE.search(str(url or ""))
    return str(match.group("listing_id")) if match else None


def canonical_marketplace_listing_url(url: str) -> str:
    listing_id = extract_marketplace_listing_id(url)
    if not listing_id:
        return str(url or "").strip()
    return f"https://www.facebook.com/marketplace/item/{listing_id}/"


def _location_slug(location_name: str) -> str:
    normalized = str(location_name or "").strip().lower()
    if "melbourne" in normalized:
        return "melbourne"
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


class MarketplaceScanner:
    def __init__(
        self,
        mission_service: MarketplaceMissionService,
        *,
        price_service: MarketplacePriceIntelligenceService | None = None,
        cdp_url: str | None = None,
        timeout_ms: int | None = None,
    ) -> None:
        self.mission_service = mission_service
        self.price_service = price_service
        self.cdp_url = str(cdp_url or "").strip() or DEFAULT_MARKETPLACE_CDP_URL
        self.timeout_ms = int(timeout_ms or DEFAULT_MARKETPLACE_TIMEOUT_MS)

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

        primary_location = hard_locations[0]
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

        for query in queries:
            self._raise_if_cancelled(cancel_requested)
            if time.monotonic() - scan_started > int(
                mission["scan_config"]["run_time_budget_minutes"]
            ) * 60:
                if log:
                    log("Time budget reached; stopping mission scan.")
                break

            if log:
                radius_suffix = f", radius={radius_km}km" if radius_km is not None else ""
                log(f"  query: {query} (location={primary_location}{radius_suffix})")
            page = await context.new_page()
            try:
                page.set_default_timeout(self.timeout_ms)
                await page.goto(
                    build_marketplace_search_url(
                        query,
                        location_name=primary_location,
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
                    bucket = _rejection_bucket(prefilter.get("prefilter_reasons"))
                    if bucket == "location":
                        rejected_by_location += 1
                    else:
                        rejected_by_requirement_fit += 1
                    continue
                ranked_cards.append({**card, **prefilter})

            ranked_cards.sort(key=lambda item: item["open_priority"], reverse=True)
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
                    continue

                score = evaluate_marketplace_listing(
                    detail,
                    mission,
                    observed_price_band=price_band,
                )
                if log:
                    log(f"      score: {score['score']} ({score['decision_band']})")
                detail_hash = listing_material_hash(detail)
                candidate_resolution: dict[str, Any] | None = None
                post_detail_outcome: dict[str, Any] | None = None
                if score["decision_band"] == "reject":
                    bucket = _rejection_bucket(score.get("reasons_against"))
                    if bucket == "location":
                        rejected_by_location += 1
                    else:
                        rejected_by_requirement_fit += 1
                    if requirement_driven:
                        post_detail_outcome = classify_requirement_detail_outcome(
                            detail,
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
                        detail,
                        candidate_contexts,
                    )
                    if not candidate_resolution.get("matched"):
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
                                "price_text": detail.get("price"),
                                "price_value": parse_marketplace_price(
                                    detail.get("price")
                                ),
                                "location": detail.get("location"),
                                "seller_name": detail.get("seller_name"),
                                "query_text": query,
                                "detail_hash": detail_hash,
                                "raw_snapshot": {
                                    **detail,
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
                    new_price_value=parse_marketplace_price(detail.get("price")),
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
                            "price": detail.get("price"),
                            "price_value": parse_marketplace_price(detail.get("price")),
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
                                "candidate_resolution": _candidate_resolution_metadata(
                                    candidate_resolution
                                ),
                            },
                        }
                    )
                    matches_saved += 1

                    should_alert = score["decision_band"] == "strong_match" or (
                        score["decision_band"] == "candidate"
                        and bool(mission["scan_config"]["aggressive_alerting"])
                    )
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
                            trigger_reason=",".join(material_reasons or ["new_listing"]),
                            metadata={
                                "detail_hash": detail_hash,
                                "query": query,
                                "decision_band": score["decision_band"],
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
                        "price_text": detail.get("price"),
                        "price_value": parse_marketplace_price(detail.get("price")),
                        "location": detail.get("location"),
                        "seller_name": detail.get("seller_name"),
                        "query_text": query,
                        "detail_hash": detail_hash,
                        "raw_snapshot": {
                            **detail,
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
                            str(post_detail_outcome["reason_code"])
                            if post_detail_outcome
                            and score["decision_band"] == "reject"
                            else score["decision_band"]
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
                    if (!/^https?:\/\//i.test(cleaned)) return
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
                      const first = srcSet.split(',')[0]?.trim().split(/\s+/)[0]
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

    def _raise_if_cancelled(
        self,
        cancel_requested: Callable[[], bool] | None,
    ) -> None:
        if cancel_requested and cancel_requested():
            raise MarketplaceScanCancelled("Marketplace scan cancelled by user request.")


class MarketplaceScanCancelled(RuntimeError):
    """Raised when a Marketplace scan is cooperatively cancelled."""
