"""market_update_orchestrator.py — Bounded v1 verbal market-update runs.

Orchestrates the cockpit's verbal market-update pipeline:

    resolve tickers -> snapshot each -> score each -> persist report
    -> queue follow-ups for high-significance tickers.

Design constraints (P5, bounded v1):
    * No LLM narrative — headlines are template-based.
    * No GPU work, no model loading, no live llama-server contention.
    * No new persistence path — uses existing `state_store` market-update
      tables (P2). See SYSTEM_CONTRACT §1.2: cockpit is client + orchestrator
      only, never an independent store of truth.
    * All dependencies injected via constructor kwargs for testability.

The orchestrator is intentionally tolerant of per-ticker failures: a single
broken `snapshot_provider` call does not abort the run. If every ticker
fails, the report is persisted with status="failed" so the operator can
inspect the cause via `/market-update`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from cockpit.core.significance_score import (
    TickerScore,
    TickerSnapshot,
    compute_significance,
)

logger = logging.getLogger(__name__)

__all__ = [
    "MarketUpdateOrchestrator",
    "RunResult",
]

_VALID_RUN_TYPES = ("noon", "final", "manual")


@dataclass(frozen=True)
class RunResult:
    """Summary of a single market-update orchestrator run."""

    report_id: str | None
    run_type: str
    status: str  # "complete", "partial", "failed", "skipped"
    gathered_tickers: int
    queued_followups: int
    errors: tuple[str, ...] = field(default_factory=tuple)
    started_at: str = ""
    finished_at: str = ""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MarketUpdateOrchestrator:
    """Coordinate a bounded verbal market-update run.

    Parameters
    ----------
    state_store:
        Cockpit `StateStore` (or compatible) exposing
        `save_market_update_report`, `add_market_update_followup`,
        `list_watch_tickers`.
    snapshot_provider:
        Callable mapping a ticker symbol to a `TickerSnapshot` (or None
        when no snapshot is available — treated as a recoverable error).
    scorer:
        Optional pure scorer; defaults to `compute_significance`.
    followup_threshold:
        Minimum significance to queue a "review" follow-up. Default 0.5.
    clock:
        Optional callable returning a tz-aware datetime. Defaults to
        `datetime.now(timezone.utc)`.
    """

    def __init__(
        self,
        *,
        state_store: Any,
        snapshot_provider: Callable[[str], TickerSnapshot | None],
        scorer: Callable[[TickerSnapshot], TickerScore] | None = None,
        followup_threshold: float = 0.5,
        clock: Callable[[], datetime] | None = None,
        market_universe_loader: Callable[[], list[str]] | None = None,
    ) -> None:
        self._store = state_store
        self._snapshot = snapshot_provider
        self._scorer = scorer or compute_significance
        self._followup_threshold = float(followup_threshold)
        self._clock = clock or _utc_now
        self._market_universe_loader = market_universe_loader

    def run(
        self,
        run_type: str,
        *,
        tickers: list[str] | None = None,
    ) -> RunResult:
        """Execute a market-update run.

        `tickers` may be supplied explicitly. When None, the orchestrator
        falls back to `state_store.list_watch_tickers()`. An empty resolved
        list short-circuits to status="skipped" without persisting a report.
        """
        if run_type not in _VALID_RUN_TYPES:
            raise ValueError(
                f"run_type must be one of {_VALID_RUN_TYPES}, got {run_type!r}"
            )

        started_dt = self._clock()
        started = started_dt.isoformat()

        scan = self._resolve_tickers(run_type, tickers)
        if not scan:
            finished = self._clock().isoformat()
            return RunResult(
                report_id=None,
                run_type=run_type,
                status="skipped",
                gathered_tickers=0,
                queued_followups=0,
                errors=(),
                started_at=started,
                finished_at=finished,
            )

        gathered: list[tuple[TickerSnapshot, TickerScore]] = []
        errors: list[str] = []

        for ticker in scan:
            try:
                snap = self._snapshot(ticker)
            except Exception as exc:  # noqa: BLE001 — per-ticker isolation
                logger.warning(
                    "market_update_orchestrator: snapshot failed for %s: %s",
                    ticker,
                    exc,
                )
                errors.append(f"{ticker}: snapshot failed: {exc}")
                continue
            if snap is None:
                errors.append(f"{ticker}: no snapshot available")
                continue
            score = self._scorer(snap)
            gathered.append((snap, score))

        status = self._derive_status(gathered_count=len(gathered), error_count=len(errors))
        summary = self._build_summary(run_type=run_type, gathered=gathered, errors=errors)

        report_date = started_dt.date().isoformat()
        report_id = self._store.save_market_update_report(
            run_type=run_type,
            report_date=report_date,
            status=status,
            summary=summary,
        )

        queued = 0
        for snap, score in gathered:
            if score.significance >= self._followup_threshold:
                self._store.add_market_update_followup(
                    report_id=report_id,
                    ticker=snap.ticker,
                    action_type="review",
                    reason={
                        "score": score.significance,
                        "reasons": list(score.reasons),
                    },
                    priority_score=score.significance,
                )
                queued += 1

        finished = self._clock().isoformat()
        return RunResult(
            report_id=report_id,
            run_type=run_type,
            status=status,
            gathered_tickers=len(gathered),
            queued_followups=queued,
            errors=tuple(errors),
            started_at=started,
            finished_at=finished,
        )

    def _resolve_tickers(self, run_type: str, tickers: list[str] | None) -> list[str]:
        if tickers is not None:
            return self._normalize_tickers(tickers)
        rows = self._store.list_watch_tickers()
        watch_tickers = self._normalize_tickers(str(r["ticker"]) for r in rows)
        if watch_tickers:
            return watch_tickers
        # For end-of-day runs, default to a market-wide universe when available
        # so /market-update final reflects the broader market by default.
        if run_type == "final" and self._market_universe_loader is not None:
            try:
                return self._normalize_tickers(self._market_universe_loader())
            except Exception as exc:  # noqa: BLE001 -- fallback loader must be safe
                logger.warning(
                    "market_update_orchestrator: market universe load failed: %s",
                    exc,
                )
        return []

    @staticmethod
    def _normalize_tickers(tickers: list[str] | tuple[str, ...] | set[str] | Any) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw in tickers:
            ticker = str(raw or "").strip().upper()
            if not ticker or ticker in seen:
                continue
            seen.add(ticker)
            normalized.append(ticker)
        return normalized

    @staticmethod
    def _derive_status(*, gathered_count: int, error_count: int) -> str:
        if gathered_count == 0:
            return "failed"
        if error_count > 0:
            return "partial"
        return "complete"

    def _build_summary(
        self,
        *,
        run_type: str,
        gathered: list[tuple[TickerSnapshot, TickerScore]],
        errors: list[str],
    ) -> dict[str, Any]:
        movers = sum(
            1
            for _, score in gathered
            if score.significance >= self._followup_threshold
        )
        alerts = sum(1 for snap, _ in gathered if snap.has_alerts)
        headline = (
            f"Market update ({run_type}): {movers} mover(s), "
            f"{alerts} alert(s) across {len(gathered)} ticker(s)."
        )
        return {
            "run_type": run_type,
            "headline": headline,
            "tickers": [
                {
                    "ticker": snap.ticker,
                    "price": snap.price,
                    "pct_change": snap.pct_change,
                    "volume": snap.volume,
                    "news_count_24h": snap.news_count_24h,
                    "has_alerts": snap.has_alerts,
                    "stale_news": snap.stale_news,
                    "significance": score.significance,
                    "reasons": list(score.reasons),
                }
                for snap, score in gathered
            ],
            "errors": list(errors),
        }
