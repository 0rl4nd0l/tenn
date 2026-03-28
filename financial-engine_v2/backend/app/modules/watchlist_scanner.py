"""watchlist_scanner.py — Scan analysis artifacts and generate alerts.

Reads artifact JSON files for each watchlist ticker and compares signals
against alert rules. No DB dependency — works purely from on-disk artifacts.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.modules.artifacts import read_artifact

logger = logging.getLogger(__name__)

_MODULES = ("balance_sheet", "valuation", "risk", "roic", "moat", "catalysts")


@dataclass(frozen=True)
class WatchlistAlert:
    """A single alert produced by scanning a ticker's artifacts."""

    ticker: str
    alert_type: str  # criteria_met | criteria_violated | new_risk | catalyst_approaching
    severity: str  # info | warning | action_required
    title: str
    detail: str
    source_module: str
    evidence: dict[str, Any]


# ---------------------------------------------------------------------------
# Alert rules
# ---------------------------------------------------------------------------


def _check_balance_sheet(t: str, d: dict[str, Any]) -> list[WatchlistAlert]:
    alerts: list[WatchlistAlert] = []
    lev = d.get("leverage_risk", "")
    if lev in ("high", "critical"):
        alerts.append(WatchlistAlert(
            t, "new_risk", "warning" if lev == "high" else "action_required",
            f"Leverage risk is {lev}",
            f"Net-debt/EBIT ratio signals {lev} leverage risk.",
            "balance_sheet", {"leverage_risk": lev},
        ))
    fcf = d.get("fcf_coverage_signal", "")
    if fcf in ("none", "weak"):
        alerts.append(WatchlistAlert(
            t, "new_risk", "warning", f"FCF coverage is {fcf}",
            "Free-cash-flow coverage of debt is insufficient.",
            "balance_sheet", {"fcf_coverage_signal": fcf},
        ))
    return alerts


def _check_valuation(t: str, d: dict[str, Any]) -> list[WatchlistAlert]:
    signals: dict[str, str] = d.get("signals", {})
    composite = d.get("composite_signal", "")
    cheap = {k: v for k, v in signals.items() if v == "cheap"}
    if composite == "cheap" or cheap:
        label = composite if composite == "cheap" else ", ".join(cheap)
        return [WatchlistAlert(
            t, "criteria_met", "info",
            "Potential entry point — valuation signals cheap",
            f"Cheap signals: {label}.", "valuation",
            {"composite_signal": composite, "cheap_signals": cheap},
        )]
    return []


def _check_risk(t: str, d: dict[str, Any]) -> list[WatchlistAlert]:
    score = d.get("risk_score")
    if score is not None and score > 70:
        return [WatchlistAlert(
            t, "new_risk", "warning" if score <= 85 else "action_required",
            f"Aggregate risk score elevated ({score}/100)",
            "Risk module flags elevated aggregate risk.", "risk",
            {"risk_score": score, "trajectory": d.get("trajectory")},
        )]
    return []


def _check_catalysts(t: str, d: dict[str, Any]) -> list[WatchlistAlert]:
    alerts: list[WatchlistAlert] = []
    for cat in d.get("catalysts", []):
        if cat.get("timeframe") == "near_term" and cat.get("impact_direction") == "positive":
            alerts.append(WatchlistAlert(
                t, "catalyst_approaching", "info",
                f"Near-term positive catalyst: {cat.get('title', 'unnamed')}",
                cat.get("description", cat.get("title", "")),
                "catalysts", {"catalyst": cat},
            ))
    return alerts


def _check_moat(t: str, d: dict[str, Any], *, is_buy: bool) -> list[WatchlistAlert]:
    if is_buy and d.get("moat_classification") == "none":
        return [WatchlistAlert(
            t, "criteria_violated", "warning",
            "No moat detected on buy-rated ticker",
            "Moat module found no competitive advantage for a buy-rated ticker.",
            "moat", {"moat_classification": "none"},
        )]
    return []


def _check_roic(t: str, d: dict[str, Any], *, is_buy: bool) -> list[WatchlistAlert]:
    summary = d.get("summary", {})
    if is_buy and summary.get("roic_above_10pct") is False:
        latest = summary.get("latest_nopat_on_ic")
        return [WatchlistAlert(
            t, "criteria_violated", "warning",
            "ROIC below 10% on buy-rated ticker",
            f"Latest NOPAT-on-IC: {latest}. Below the 10% quality threshold.",
            "roic", {"roic_above_10pct": False, "latest_nopat_on_ic": latest},
        )]
    return []


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


class WatchlistScanner:
    """Scan analysis artifacts for watchlist tickers and generate alerts."""

    def scan(
        self,
        watchlist_tickers: list[str],
        *,
        reports_root: str | None = None,
        decisions: dict[str, str] | None = None,
    ) -> list[WatchlistAlert]:
        """Scan all watchlist tickers. Returns combined alert list.

        Args:
            watchlist_tickers: Ticker strings to scan.
            reports_root: Override for artifact directory root.
            decisions: Mapping of ticker -> decision string
                       (e.g. {"BHP": "buy", "NAB": "watchlist"}).
        """
        decisions = decisions or {}
        all_alerts: list[WatchlistAlert] = []
        for ticker in watchlist_tickers:
            all_alerts.extend(self.scan_ticker(
                ticker,
                reports_root=reports_root,
                decision=decisions.get(ticker.upper(), ""),
            ))
        return all_alerts

    def scan_ticker(
        self,
        ticker: str,
        *,
        reports_root: str | None = None,
        decision: str = "",
    ) -> list[WatchlistAlert]:
        """Scan a single ticker's artifacts for alerts."""
        upper = ticker.upper()
        is_buy = decision.lower() == "buy"

        artifacts: dict[str, dict[str, Any]] = {}
        for module in _MODULES:
            data = read_artifact(upper, module, reports_root)
            if data is not None:
                artifacts[module] = data

        if not artifacts:
            logger.info("watchlist_scanner: no artifacts for %s", upper)
            return []

        alerts: list[WatchlistAlert] = []
        if "balance_sheet" in artifacts:
            alerts.extend(_check_balance_sheet(upper, artifacts["balance_sheet"]))
        if "valuation" in artifacts:
            alerts.extend(_check_valuation(upper, artifacts["valuation"]))
        if "risk" in artifacts:
            alerts.extend(_check_risk(upper, artifacts["risk"]))
        if "catalysts" in artifacts:
            alerts.extend(_check_catalysts(upper, artifacts["catalysts"]))
        if "moat" in artifacts:
            alerts.extend(_check_moat(upper, artifacts["moat"], is_buy=is_buy))
        if "roic" in artifacts:
            alerts.extend(_check_roic(upper, artifacts["roic"], is_buy=is_buy))

        logger.info("watchlist_scanner: %s — %d alerts", upper, len(alerts))
        return alerts
