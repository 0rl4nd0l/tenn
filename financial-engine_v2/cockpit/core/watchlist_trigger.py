"""watchlist_trigger.py — Automated watchlist monitoring using strategy criteria.

Orchestrates: load watchlist → run analysis → scan artifacts → generate alerts → save findings.
Stateless and idempotent — safe to run repeatedly.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from cockpit.core.research.alerts import AlertReader
from cockpit.core.strategy import StrategyService

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TriggerResult:
    """Summary of a single-ticker trigger run."""

    ticker: str
    analysis_ok: bool
    modules_run: int
    alerts_generated: int
    errors: tuple[str, ...]


@dataclass(frozen=True)
class TriggerSummary:
    """Summary of a full watchlist scan."""

    tickers_scanned: int
    total_alerts: int
    total_errors: int
    results: tuple[TriggerResult, ...]
    started_at: str
    finished_at: str


class WatchlistTrigger:
    """Orchestrate watchlist monitoring: analysis → scan → alerts → dossier.

    All dependencies are injected — no global state.
    """

    def __init__(
        self,
        *,
        state_store,
        strategy_service: StrategyService,
        backend_api_client,
        alert_reader: AlertReader,
        dossier_service=None,
        reports_root: str | None = None,
    ) -> None:
        self._store = state_store
        self._strategy = strategy_service
        self._backend = backend_api_client
        self._alerts = alert_reader
        self._alerts_path = getattr(alert_reader, "_path", None)
        self._dossier = dossier_service
        self._reports_root = reports_root

    def run(self, *, tickers: list[str] | None = None) -> TriggerSummary:
        """Run the full trigger cycle for watchlist tickers.

        Args:
            tickers: Override ticker list. If None, reads from watchlist table.

        Returns:
            TriggerSummary with per-ticker results.
        """
        started = datetime.now(timezone.utc).isoformat()

        # 1. Resolve tickers
        if tickers is not None:
            scan_tickers = [t.upper() for t in tickers]
        else:
            rows = self._store.list_watch_tickers()
            scan_tickers = [r["ticker"] for r in rows]

        if not scan_tickers:
            finished = datetime.now(timezone.utc).isoformat()
            return TriggerSummary(
                tickers_scanned=0,
                total_alerts=0,
                total_errors=0,
                results=(),
                started_at=started,
                finished_at=finished,
            )

        # 2. Load strategy decisions for all tickers
        decisions: dict[str, str] = {}
        for ticker in scan_tickers:
            dec = self._strategy.get_decision(ticker)
            if dec and dec.get("decision"):
                decisions[ticker] = dec["decision"]

        # 3. Run per-ticker cycle
        results: list[TriggerResult] = []
        for ticker in scan_tickers:
            result = self._run_ticker(ticker, decision=decisions.get(ticker, ""))
            results.append(result)

        finished = datetime.now(timezone.utc).isoformat()
        total_alerts = sum(r.alerts_generated for r in results)
        total_errors = sum(len(r.errors) for r in results)

        return TriggerSummary(
            tickers_scanned=len(scan_tickers),
            total_alerts=total_alerts,
            total_errors=total_errors,
            results=tuple(results),
            started_at=started,
            finished_at=finished,
        )

    def _run_ticker(self, ticker: str, *, decision: str) -> TriggerResult:
        """Run analysis + scan + alerts for a single ticker."""
        errors: list[str] = []

        # Step 1: Run analysis via backend API
        analysis_ok = False
        modules_run = 0
        if self._backend is not None:
            try:
                analysis_result = self._call_analysis(ticker)
                analysis_ok = bool(analysis_result.get("modules_run"))
                modules_run = int(analysis_result.get("modules_run", 0))
            except Exception as exc:
                errors.append(f"analysis failed: {exc}")
                logger.warning("watchlist_trigger: analysis failed for %s: %s", ticker, exc)
        else:
            errors.append("backend API client not configured")

        # Step 2: Scan artifacts (works even if analysis just failed — reads existing artifacts)
        alerts_generated = 0
        try:
            from app.modules.watchlist_scanner import WatchlistScanner

            scanner = WatchlistScanner()
            alerts = scanner.scan_ticker(
                ticker,
                reports_root=self._reports_root,
                decision=decision,
            )

            # Step 3: Write alerts to JSONL
            for alert in alerts:
                AlertReader.write_alert(
                    path=self._alerts_path,
                    ticker=alert.ticker,
                    alert_type=alert.alert_type,
                    message=alert.title,
                    data={
                        "detail": alert.detail,
                        "severity": alert.severity,
                        "source_module": alert.source_module,
                        **alert.evidence,
                    },
                )
            alerts_generated = len(alerts)

            # Step 4: Save summary finding to dossier
            if self._dossier is not None and alerts:
                summary_lines = [f"{a.severity.upper()}: {a.title}" for a in alerts]
                self._dossier.save(
                    ticker=ticker,
                    finding=f"Watchlist scan ({datetime.now(timezone.utc).strftime('%Y-%m-%d')}): "
                    + "; ".join(summary_lines),
                    source="watchlist_trigger",
                    confidence=0.7,
                    category="risk" if any(a.severity != "info" for a in alerts) else "general",
                )

        except Exception as exc:
            errors.append(f"scan failed: {exc}")
            logger.warning("watchlist_trigger: scan failed for %s: %s", ticker, exc)

        return TriggerResult(
            ticker=ticker,
            analysis_ok=analysis_ok,
            modules_run=modules_run,
            alerts_generated=alerts_generated,
            errors=tuple(errors),
        )

    def _call_analysis(self, ticker: str) -> dict[str, Any]:
        """Call POST /api/analysis/{ticker} via BackendApiClient."""
        import httpx

        url = f"{self._backend.base_url}/api/analysis/{ticker}"
        headers: dict[str, str] = {}
        if self._backend.api_key:
            headers["X-API-Key"] = self._backend.api_key

        with httpx.Client(timeout=180.0, follow_redirects=True) as client:
            response = client.post(url, headers=headers)
            response.raise_for_status()
            return response.json() if response.content else {}
