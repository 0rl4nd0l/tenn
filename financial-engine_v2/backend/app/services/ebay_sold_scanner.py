from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import Any, Callable
from urllib.parse import quote_plus

from app.services.marketplace_headless_runtime import open_direct_marketplace_context, use_direct_marketplace_runtime
from app.services.marketplace_price_intelligence import (
    MarketplacePriceIntelligenceService,
    detect_listing_junk,
)

logger = logging.getLogger(__name__)

def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _price_value(value: Any) -> float | None:
    match = re.search(r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)", str(value or ""))
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", ""))
    except ValueError:
        return None


class EbaySoldScanner:
    def __init__(
        self,
        price_service: MarketplacePriceIntelligenceService,
        timeout_ms: int = 30000,
    ) -> None:
        self.price_service = price_service
        self.timeout_ms = timeout_ms

    async def scrape_sold_items(
        self,
        tracked_product_id: str,
        query: str,
        log: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        product = self.price_service.get_tracked_product(tracked_product_id)
        if product is None:
            raise ValueError(f"tracked_product_id not found: {tracked_product_id}")

        # eBay search for sold items: LH_Sold=1, LH_Complete=1
        encoded_query = quote_plus(query)
        search_url = f"https://www.ebay.com.au/sch/i.html?_nkw={encoded_query}&LH_Sold=1&LH_Complete=1"
        
        if log:
            log(f"Starting eBay sold scrape for: {query} ({tracked_product_id})")

        stats = {
            "tracked_product_id": tracked_product_id,
            "query": query,
            "listings_seen": 0,
            "observations_ingested": 0,
        }

        async def perform_scrape(context: Any):
            page = await context.new_page()
            try:
                page.set_default_timeout(self.timeout_ms)
                if log:
                    log(f"Navigating to eBay: {search_url}")
                await page.goto(search_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(2_000)
                
                # Scrape logic - handle both legacy .s-item and current .s-card result DOMs.
                items = await page.evaluate(
                    """
                    () => {
                        const results = [];
                        const elements = document.querySelectorAll('.s-item__wrapper, .s-card');
                        for (const el of elements) {
                            const titleEl = el.querySelector('.s-item__title');
                            const priceEl = el.querySelector('.s-item__price');
                            const dateEl = el.querySelector('.s-item__title--tagblock .POSITIVE, .s-item__caption .POSITIVE');
                            const linkEl = el.querySelector('.s-item__link');
                            const rawText = (el.innerText || '').trim();
                            if (!rawText) continue;
                            if (rawText.toLowerCase().includes('shop on ebay')) continue;

                            const lines = rawText.split('\\n').map((line) => line.trim()).filter(Boolean);
                            const soldLine = lines.find((line) => /^sold\\b/i.test(line));
                            const priceLine = lines.find((line) => /(?:AU\\s*)?\\$\\s*[0-9]/i.test(line));
                            const fallbackTitle = (() => {
                                const soldIndex = soldLine ? lines.indexOf(soldLine) : -1;
                                for (const line of lines.slice(Math.max(0, soldIndex + 1))) {
                                    if (/opens in a new window|pre-owned|brand new|parts only|or best offer|^au\\s*\\$/i.test(line)) continue;
                                    if (/^sold\\b/i.test(line)) continue;
                                    if (/(?:AU\\s*)?\\$\\s*[0-9]/i.test(line)) continue;
                                    const cleaned = line.replace(/^NEW LISTING/i, '').trim();
                                    if (cleaned) return cleaned;
                                }
                                return '';
                            })();
                            const title = (titleEl ? titleEl.innerText.trim() : fallbackTitle).replace(/^NEW LISTING/i, '').trim();
                            if (!title) continue;
                            const priceText = priceEl ? priceEl.innerText.trim() : (priceLine || '');
                            if (!priceText) continue;
                            const dateSold = soldLine ? soldLine.replace(/^Sold/i, '').trim() : (dateEl ? dateEl.innerText.replace('Sold', '').trim() : null);
                            const url = linkEl ? linkEl.href : (el.querySelector('a') ? el.querySelector('a').href : null);
                            
                            results.push({
                                title,
                                price: priceText,
                                date_sold: dateSold,
                                url: url,
                                raw_text: rawText
                            });
                        }
                        return results.slice(0, 50);
                    }
                    """
                )
            finally:
                try:
                    await page.close()
                except Exception:
                    pass

            stats["listings_seen"] = len(items)
            if log:
                log(f"Found {len(items)} sold items on eBay")

            for item in items:
                raw_text = str(item.get("raw_text") or item["title"])
                if re.search(
                    r"\bfrom\s+(united states|united kingdom|china|hong kong|japan|canada|germany)\b",
                    raw_text,
                    re.IGNORECASE,
                ):
                    continue
                junk = detect_listing_junk(
                    title=raw_text,
                    price=_price_value(item["price"]),
                    category=product["category"],
                )
                if junk["is_junk"]:
                    continue

                # Basic match check using existing service logic
                confidence = self.price_service.variant_match_confidence(
                    match={
                        "title": item["title"],
                        "raw_text_snapshot": raw_text,
                        "price": item["price"],
                    },
                    tracked_product=product,
                )
                
                # We want transactional data to be fairly high confidence
                if confidence >= 0.65:
                    try:
                        observation = self.price_service.ingest_observation_if_new_or_changed({
                            "tracked_product_id": tracked_product_id,
                            "source": "ebay_sold",
                            "observed_at": _now_iso(),
                            "title": item["title"],
                            "price": item["price"],
                            "url": item["url"],
                            "match_confidence": confidence,
                            "capture_mode": "scanner",
                            "is_transactional": True,
                            "provenance": {
                                "query": query,
                                "ebay_sold_date": item["date_sold"],
                                "raw_text": raw_text,
                            },
                            "review_state": "accepted"
                        })
                        if observation.get("created"):
                            stats["observations_ingested"] += 1
                    except Exception as exc:
                        if log:
                            log(f"Failed to ingest eBay observation: {exc}")

            if stats["observations_ingested"] > 0:
                self.price_service.rebuild_benchmark_snapshot(tracked_product_id)

        if use_direct_marketplace_runtime():
            async with open_direct_marketplace_context() as (context, _, _):
                await perform_scrape(context)
        else:
            from playwright.async_api import async_playwright
            async with async_playwright() as playwright:
                browser = await playwright.chromium.launch(headless=True)
                context = await browser.new_context()
                await perform_scrape(context)
                await browser.close()

        return stats
