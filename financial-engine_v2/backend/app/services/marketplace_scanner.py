from __future__ import annotations

import asyncio
import re
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote_plus

from app.services.facebook_marketplace_inspector import (
    DEFAULT_MARKETPLACE_CDP_URL,
    DEFAULT_MARKETPLACE_TIMEOUT_MS,
    MARKETPLACE_CAPTURE_ROOT,
    MarketplaceBrowserProbeTimeout,
    _await_marketplace_probe,
    _marketplace_probe_timeout_detail,
    _probe_timeout_seconds,
)
from app.services.marketplace_browser_profile import check_marketplace_browser_health
from app.services.marketplace_headless_runtime import open_direct_marketplace_context, use_direct_marketplace_runtime
from app.services.marketplace_mission_service import MarketplaceMissionService
from app.services.marketplace_scoring import (
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


def extract_marketplace_listing_id(url: str) -> str | None:
    match = FACEBOOK_MARKETPLACE_ITEM_RE.search(str(url or ""))
    return str(match.group("listing_id")) if match else None


def canonical_marketplace_listing_url(url: str) -> str:
    listing_id = extract_marketplace_listing_id(url)
    if not listing_id:
        return str(url or "").strip()
    return f"https://www.facebook.com/marketplace/item/{listing_id}/"


def build_marketplace_search_url(query: str) -> str:
    return f"https://www.facebook.com/marketplace/search?query={quote_plus(query)}"


class MarketplaceScanner:
    def __init__(
        self,
        mission_service: MarketplaceMissionService,
        *,
        cdp_url: str | None = None,
        timeout_ms: int | None = None,
    ) -> None:
        self.mission_service = mission_service
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
        if str(health.get("status")) != "ready":
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
                "detail_pages_opened": 0,
                "summary": "No active Marketplace missions to scan.",
            }

        total_missions = len(missions)
        aggregate = {
            "missions_scanned": total_missions,
            "matches_saved": 0,
            "alerts_created": 0,
            "listings_seen": 0,
            "detail_pages_opened": 0,
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
                    aggregate["detail_pages_opened"] += result["detail_pages_opened"]
                    aggregate["mission_summaries"].append(result)
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
                    aggregate["detail_pages_opened"] += result["detail_pages_opened"]
                    aggregate["mission_summaries"].append(result)
                    self.mission_service.mark_last_scan(mission["mission_id"])

        if progress:
            progress("Marketplace scan complete", 100.0)
        aggregate["summary"] = (
            f"Scanned {aggregate['missions_scanned']} mission(s), saw "
            f"{aggregate['listings_seen']} listings, saved {aggregate['matches_saved']} "
            f"match(es), and created {aggregate['alerts_created']} alert(s)."
        )
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
        search_pack = build_marketplace_search_pack(mission)
        queries = flatten_marketplace_queries(
            search_pack,
            max_queries=int(mission["search_config"]["max_queries_per_run"]),
        )
        price_band = self.mission_service.price_band(mission_id)
        seen_ids_this_run: set[str] = set()
        matches_saved = 0
        alerts_created = 0
        listings_seen = 0
        detail_pages_opened = 0
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
                log(f"  query: {query}")
            page = await context.new_page()
            try:
                page.set_default_timeout(self.timeout_ms)
                await page.goto(build_marketplace_search_url(query), wait_until="domcontentloaded")
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
            ranked_cards: list[dict[str, Any]] = []
            for card in cards:
                prefilter = prefilter_marketplace_card(card, mission)
                if prefilter["prefilter_decision"] != "open":
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
                detail = await self._inspect_listing_detail(
                    context=context,
                    listing_url=card["listing_url"],
                    mission_id=mission_id,
                    cancel_requested=cancel_requested,
                )

                score = evaluate_marketplace_listing(
                    detail,
                    mission,
                    observed_price_band=price_band,
                )
                if log:
                    log(f"      score: {score['score']} ({score['decision_band']})")
                detail_hash = listing_material_hash(detail)
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
                            "status": match_status,
                            "metadata": {
                                "query": query,
                                "material_change_reasons": material_reasons,
                                "detail_hash": detail_hash,
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
                            "material_change_reasons": material_reasons,
                        },
                        "last_status": score["decision_band"],
                        "last_score": score["score"],
                        "last_decision_band": score["decision_band"],
                        "last_error": None,
                        "match_id": match_record["match_id"] if match_record else None,
                    },
                )

        return {
            "mission_id": mission_id,
            "mission_name": mission["name"],
            "queries": queries,
            "matches_saved": matches_saved,
            "alerts_created": alerts_created,
            "listings_seen": listings_seen,
            "detail_pages_opened": detail_pages_opened,
        }

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
