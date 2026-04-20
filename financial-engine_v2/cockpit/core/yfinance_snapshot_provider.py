"""yfinance_snapshot_provider.py — Yahoo Finance snapshot adapter.

Implements the `Callable[[str], TickerSnapshot | None]` contract expected by
`MarketUpdateOrchestrator`. Performs price/volume/pct_change retrieval via
`yfinance` (lazy-imported to keep cockpit boot offline-tolerant) and
optionally enriches the snapshot with cockpit-side news count, alert
status, and freshness flags.

Constraints:
    * No LLM, no GPU, no model loading.
    * yfinance is a network call — wrapped in a broad except so a single
      ticker failure can't kill an orchestrator run.
    * Returns None on import or fetch failure; orchestrator records this
      as a per-ticker error and continues.

Default ticker suffix is ``.AX`` (ASX). Override via constructor for
other Yahoo Finance markets (`.L` for London, no suffix for US, etc.).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from cockpit.core.significance_score import TickerSnapshot

logger = logging.getLogger(__name__)

__all__ = ["YFinanceSnapshotProvider"]


class YFinanceSnapshotProvider:
    """Adapter from a ticker symbol to a `TickerSnapshot`.

    Parameters
    ----------
    ticker_suffix:
        Suffix appended to the ticker for the Yahoo symbol. Default
        ``".AX"`` for ASX listings.
    news_count_provider:
        Optional callable mapping ticker → 24h news count. Failures are
        swallowed (snapshot still returned with news_count_24h=0).
    alerts_provider:
        Optional callable mapping ticker → bool indicating active alerts.
    freshness_tracker:
        Optional object exposing ``is_stale(ticker) -> bool`` (e.g., a
        `NewsFreshnessTracker`). Used to set `stale_news`.
    """

    def __init__(
        self,
        *,
        ticker_suffix: str = ".AX",
        news_count_provider: Callable[[str], int] | None = None,
        alerts_provider: Callable[[str], bool] | None = None,
        freshness_tracker: Any | None = None,
    ) -> None:
        self._suffix = ticker_suffix
        self._news_count_provider = news_count_provider
        self._alerts_provider = alerts_provider
        self._freshness_tracker = freshness_tracker

    def __call__(self, ticker: str) -> TickerSnapshot | None:
        upper_ticker = ticker.upper()
        symbol = f"{upper_ticker}{self._suffix}"

        try:
            import yfinance as yf  # noqa: PLC0415 — lazy import keeps boot fast
        except ImportError:
            logger.warning(
                "yfinance unavailable; cannot snapshot %s", symbol
            )
            return None

        try:
            yticker = yf.Ticker(symbol)
            hist = yticker.history(period="2d")
        except Exception:  # noqa: BLE001 — network/library faults are recoverable
            logger.exception("yfinance snapshot failed for %s", symbol)
            return None

        if hist is None or getattr(hist, "empty", True) or len(hist) == 0:
            return None

        try:
            last = hist.iloc[-1]
            price = float(last["Close"])
            raw_volume = last["Volume"]
            volume = int(raw_volume) if raw_volume else None

            pct_change: float | None = None
            if len(hist) >= 2:
                prev_close = float(hist.iloc[-2]["Close"])
                if prev_close != 0:
                    pct_change = ((price - prev_close) / prev_close) * 100.0
        except Exception:  # noqa: BLE001 — defensive: malformed response
            logger.exception("yfinance row parse failed for %s", symbol)
            return None

        news_count = self._safe_news_count(upper_ticker)
        has_alerts = self._safe_alerts(upper_ticker)
        stale_news = self._safe_stale(upper_ticker)

        return TickerSnapshot(
            ticker=upper_ticker,
            price=price,
            pct_change=pct_change,
            volume=volume,
            news_count_24h=news_count,
            has_alerts=has_alerts,
            stale_news=stale_news,
        )

    def _safe_news_count(self, ticker: str) -> int:
        if self._news_count_provider is None:
            return 0
        try:
            return int(self._news_count_provider(ticker))
        except Exception:  # noqa: BLE001 — enrichment is best-effort
            logger.exception("news_count_provider failed for %s", ticker)
            return 0

    def _safe_alerts(self, ticker: str) -> bool:
        if self._alerts_provider is None:
            return False
        try:
            return bool(self._alerts_provider(ticker))
        except Exception:  # noqa: BLE001 — enrichment is best-effort
            logger.exception("alerts_provider failed for %s", ticker)
            return False

    def _safe_stale(self, ticker: str) -> bool:
        if self._freshness_tracker is None:
            return False
        try:
            return bool(self._freshness_tracker.is_stale(ticker))
        except Exception:  # noqa: BLE001 — enrichment is best-effort
            logger.exception("freshness_tracker failed for %s", ticker)
            return False
