"""Background research tasks — watchlist scanner.

Periodically scans watchlist tickers for material changes:
price moves, new announcements, significant news.
Writes alerts to ~/.tenn/memory/alerts/pending.jsonl.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from worker_app.celery_app import celery

logger = logging.getLogger(__name__)

_SCAN_STATE_PATH = Path.home() / ".tenn" / "memory" / "research_scan_state.json"
_WATCHLIST_PATH = Path.home() / ".tenn" / "state" / "watchlist.json"
_PRICE_CHANGE_THRESHOLD = 0.03  # 3% move triggers alert


def _load_watchlist() -> list[str]:
    """Load watchlist tickers from state file."""
    # Try cockpit state store format.
    for path in (_WATCHLIST_PATH, Path.home() / ".financial_engine_cockpit" / "watchlist.json"):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return [str(t).strip().upper() for t in data if t]
                if isinstance(data, dict):
                    return [str(t).strip().upper() for t in data.get("tickers", []) if t]
            except Exception:
                continue
    return []


def _load_scan_state() -> dict[str, Any]:
    """Load per-ticker scan state (last prices, timestamps)."""
    if _SCAN_STATE_PATH.exists():
        try:
            return json.loads(_SCAN_STATE_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_scan_state(state: dict[str, Any]) -> None:
    _SCAN_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SCAN_STATE_PATH.write_text(
        json.dumps(state, default=str, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


@celery.task(name="watchlist_research_scan")
def watchlist_research_scan() -> dict[str, Any]:
    """Scan watchlist tickers for material changes.

    Called on a schedule (3x daily) or manually via:
        celery call watchlist_research_scan

    Also runs thesis expiration (90-day stale check) and auto-reflection
    for decisions older than 30 days that haven't been reflected on.
    """
    tickers = _load_watchlist()
    if not tickers:
        return {"ok": True, "scanned": 0, "message": "watchlist is empty"}

    scan_state = _load_scan_state()
    scanned = 0
    alerts_created = 0

    for ticker in tickers:
        try:
            result = _scan_ticker(ticker, scan_state)
            scanned += 1
            alerts_created += result.get("alerts", 0)
        except Exception as exc:
            logger.warning("watchlist scan failed for %s: %s", ticker, exc)

    _save_scan_state(scan_state)

    # Thesis expiration — mark stale active theses as expired.
    expired_count = 0
    try:
        from cockpit.core.research.thesis import ThesisService

        thesis_service = ThesisService()
        expire_result = thesis_service.expire_stale(days=90)
        expired_count = expire_result.get("expired_count", 0)
        if expired_count:
            logger.info(
                "watchlist_research_scan: expired %d stale theses", expired_count,
            )
    except Exception as exc:
        logger.warning("watchlist_research_scan: thesis expiration failed: %s", exc)

    # Auto-reflection — reflect on decisions older than 30 days.
    reflections = 0
    try:
        from cockpit.core.research.reflection import ReflectionService
        from cockpit.core.research.situation_memory import SituationMemory

        memory = SituationMemory()
        reflection_service = ReflectionService(situation_memory=memory)
        open_decisions = reflection_service.review_open_decisions()

        for decision in open_decisions:
            decision_ticker = decision.get("ticker", "")
            try:
                result = reflection_service.reflect_and_learn(decision_ticker)
                if result.get("ok"):
                    reflections += 1
            except Exception as exc:
                logger.warning(
                    "watchlist_research_scan: reflection failed for %s: %s",
                    decision_ticker, exc,
                )
        if reflections:
            logger.info(
                "watchlist_research_scan: reflected on %d decisions", reflections,
            )
    except Exception as exc:
        logger.warning("watchlist_research_scan: auto-reflection failed: %s", exc)

    logger.info(
        "watchlist_research_scan: scanned %d tickers, %d alerts, %d expired, %d reflections",
        scanned, alerts_created, expired_count, reflections,
    )
    return {
        "ok": True,
        "scanned": scanned,
        "alerts": alerts_created,
        "expired_theses": expired_count,
        "reflections": reflections,
    }


def _scan_ticker(ticker: str, scan_state: dict[str, Any]) -> dict[str, Any]:
    """Scan a single ticker for material changes."""
    from cockpit.core.research.alerts import AlertReader

    alerts = 0
    prev = scan_state.get(ticker, {})
    now_iso = datetime.now(timezone.utc).isoformat()

    # Price check via backend API.
    try:
        import httpx

        backend_url = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
        resp = httpx.get(
            f"{backend_url}/api/price",
            params={"ticker": ticker, "exchange": "ASX", "range": "1mo"},
            timeout=10.0,
        )
        if resp.status_code == 200:
            price_data = resp.json()
            current_price = price_data.get("current_price") or price_data.get("close")
            if current_price and prev.get("last_price"):
                change = (float(current_price) - float(prev["last_price"])) / float(prev["last_price"])
                if abs(change) >= _PRICE_CHANGE_THRESHOLD:
                    direction = "up" if change > 0 else "down"
                    pct = f"{abs(change)*100:.1f}%"
                    AlertReader.write_alert(
                        ticker=ticker,
                        alert_type="price_move",
                        message=f"{ticker} moved {direction} {pct} since last scan",
                        data={"current": current_price, "previous": prev["last_price"], "change_pct": round(change, 4)},
                    )
                    alerts += 1
            if current_price:
                scan_state.setdefault(ticker, {})["last_price"] = float(current_price)
    except Exception as exc:
        logger.debug("price check failed for %s: %s", ticker, exc)

    # Web news check via Brave Search.
    try:
        from cockpit.integrations.brave_search import BraveSearchClient

        brave = BraveSearchClient()
        if brave.available:
            web = brave.search(f"{ticker} ASX news", count=3, news_only=True)
            new_results = web.get("results", [])
            if new_results:
                # Simple: alert if there's any news result we haven't seen.
                prev_urls = set(prev.get("seen_urls", []))
                new_urls = [r["url"] for r in new_results if r.get("url") and r["url"] not in prev_urls]
                if new_urls:
                    titles = [r.get("title", "")[:80] for r in new_results if r.get("url") in set(new_urls)]
                    AlertReader.write_alert(
                        ticker=ticker,
                        alert_type="news",
                        message=f"{len(new_urls)} new article(s) for {ticker}: {titles[0] if titles else ''}",
                        data={"urls": new_urls[:3], "titles": titles[:3]},
                    )
                    alerts += 1
                all_urls = list(prev_urls | set(r["url"] for r in new_results if r.get("url")))
                scan_state.setdefault(ticker, {})["seen_urls"] = all_urls[-50:]  # cap
    except Exception as exc:
        logger.debug("web news check failed for %s: %s", ticker, exc)

    scan_state.setdefault(ticker, {})["last_scan"] = now_iso
    return {"alerts": alerts}
