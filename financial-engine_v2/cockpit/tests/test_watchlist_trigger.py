"""Tests for WatchlistTrigger orchestrator."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from cockpit.core.research.alerts import AlertReader
from cockpit.core.watchlist_trigger import WatchlistTrigger


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeStateStore:
    """Minimal state store stub with a watchlist."""

    def __init__(self, tickers: list[str] | None = None) -> None:
        self._tickers = tickers or []

    def list_watch_tickers(self) -> list[dict[str, Any]]:
        return [{"ticker": t, "added_at": "2026-01-01T00:00:00+00:00"} for t in self._tickers]


class FakeStrategyService:
    """Stub that returns pre-configured decisions."""

    def __init__(self, decisions: dict[str, str] | None = None) -> None:
        self._decisions = decisions or {}

    def get_decision(self, ticker: str) -> dict[str, Any] | None:
        dec = self._decisions.get(ticker.upper())
        if dec:
            return {"ticker": ticker.upper(), "decision": dec, "decision_rationale": "test"}
        return None


class FakeBackendApiClient:
    """Stub that records analysis calls."""

    def __init__(self, *, fail: bool = False) -> None:
        self.base_url = "http://localhost:8000"
        self.api_key = ""
        self.calls: list[str] = []
        self._fail = fail

    def post_analysis(self, ticker: str) -> dict[str, Any]:
        self.calls.append(ticker)
        if self._fail:
            raise RuntimeError("backend unavailable")
        return {"modules_run": 7, "ticker": ticker}


def _write_artifact(reports_root: Path, ticker: str, module: str, data: dict) -> None:
    """Write a fake analysis artifact."""
    path = reports_root / "analysis" / ticker / f"{module}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestWatchlistTrigger(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.mkdtemp()
        self._alerts_path = Path(self._tmpdir) / "alerts" / "pending.jsonl"
        self._reports_root = Path(self._tmpdir) / "reports"

    def _make_trigger(
        self,
        tickers: list[str] | None = None,
        decisions: dict[str, str] | None = None,
        backend_fail: bool = False,
        dossier: Any = None,
    ) -> WatchlistTrigger:
        return WatchlistTrigger(
            state_store=FakeStateStore(tickers),
            strategy_service=FakeStrategyService(decisions),
            backend_api_client=FakeBackendApiClient(fail=backend_fail),
            alert_reader=AlertReader(path=self._alerts_path),
            dossier_service=dossier,
            reports_root=str(self._reports_root),
        )

    def test_empty_watchlist(self) -> None:
        trigger = self._make_trigger(tickers=[])
        summary = trigger.run()
        self.assertEqual(summary.tickers_scanned, 0)
        self.assertEqual(summary.total_alerts, 0)
        self.assertEqual(summary.total_errors, 0)

    def test_ticker_override(self) -> None:
        """Explicit tickers param overrides the watchlist table."""
        trigger = self._make_trigger(tickers=["AAA", "BBB"])
        # No artifacts exist → 0 alerts, but 2 tickers scanned
        with patch("cockpit.core.watchlist_trigger.WatchlistTrigger._call_analysis", return_value={"modules_run": 0}):
            summary = trigger.run(tickers=["CSL"])
        self.assertEqual(summary.tickers_scanned, 1)
        self.assertEqual(summary.results[0].ticker, "CSL")

    def test_scan_produces_alerts(self) -> None:
        """Artifacts with high leverage → alert generated and written to JSONL."""
        _write_artifact(self._reports_root, "BHP", "balance_sheet", {
            "leverage_risk": "high",
            "fcf_coverage_signal": "strong",
        })
        trigger = self._make_trigger(
            tickers=["BHP"],
            decisions={"BHP": "buy"},
        )
        with patch.object(trigger, "_call_analysis", return_value={"modules_run": 7}):
            summary = trigger.run()

        self.assertEqual(summary.tickers_scanned, 1)
        self.assertGreaterEqual(summary.total_alerts, 1)

        # Verify alert written to JSONL
        self.assertTrue(self._alerts_path.exists())
        alerts = [json.loads(line) for line in self._alerts_path.read_text().splitlines() if line.strip()]
        self.assertGreaterEqual(len(alerts), 1)
        self.assertEqual(alerts[0]["ticker"], "BHP")

    def test_scan_writes_dossier_finding(self) -> None:
        """When alerts are generated, a summary is saved to the dossier."""
        _write_artifact(self._reports_root, "CSL", "risk", {
            "risk_score": 80,
            "trajectory": "rising",
        })
        mock_dossier = MagicMock()
        trigger = self._make_trigger(
            tickers=["CSL"],
            dossier=mock_dossier,
        )
        with patch.object(trigger, "_call_analysis", return_value={"modules_run": 7}):
            summary = trigger.run()

        self.assertGreaterEqual(summary.total_alerts, 1)
        mock_dossier.save.assert_called_once()
        call_kwargs = mock_dossier.save.call_args
        self.assertEqual(call_kwargs.kwargs.get("ticker") or call_kwargs[1].get("ticker", call_kwargs[0][0] if call_kwargs[0] else ""), "CSL")

    def test_backend_failure_recorded_as_error(self) -> None:
        """Backend API failure is captured, scan still runs on existing artifacts."""
        trigger = self._make_trigger(tickers=["XYZ"])
        with patch.object(trigger, "_call_analysis", side_effect=RuntimeError("backend unavailable")):
            summary = trigger.run()
        self.assertEqual(summary.tickers_scanned, 1)
        result = summary.results[0]
        self.assertFalse(result.analysis_ok)
        self.assertGreater(len(result.errors), 0)

    def test_no_artifacts_no_alerts(self) -> None:
        """Ticker with no artifacts → 0 alerts, no crash."""
        trigger = self._make_trigger(tickers=["NAB"])
        with patch.object(trigger, "_call_analysis", return_value={"modules_run": 7}):
            summary = trigger.run()
        self.assertEqual(summary.tickers_scanned, 1)
        self.assertEqual(summary.total_alerts, 0)
        self.assertEqual(summary.total_errors, 0)

    def test_moat_check_respects_buy_decision(self) -> None:
        """Moat=none on buy-rated ticker → criteria_violated alert."""
        _write_artifact(self._reports_root, "WES", "moat", {
            "moat_classification": "none",
        })
        trigger = self._make_trigger(
            tickers=["WES"],
            decisions={"WES": "buy"},
        )
        with patch.object(trigger, "_call_analysis", return_value={"modules_run": 7}):
            summary = trigger.run()
        self.assertGreaterEqual(summary.total_alerts, 1)
        # Verify it's a criteria_violated alert
        alerts = [json.loads(line) for line in self._alerts_path.read_text().splitlines() if line.strip()]
        self.assertTrue(any(a.get("type") == "criteria_violated" for a in alerts))

    def test_moat_check_skips_non_buy(self) -> None:
        """Moat=none on watchlist-rated ticker → NO alert (only fires for buy)."""
        _write_artifact(self._reports_root, "WES", "moat", {
            "moat_classification": "none",
        })
        trigger = self._make_trigger(
            tickers=["WES"],
            decisions={"WES": "watchlist"},
        )
        with patch.object(trigger, "_call_analysis", return_value={"modules_run": 7}):
            summary = trigger.run()
        self.assertEqual(summary.total_alerts, 0)


class TestToolExecutorScanWatchlist(unittest.TestCase):
    """Test the scan_watchlist tool dispatch in ToolExecutor."""

    def test_dispatch_exists(self) -> None:
        from cockpit.core.tool_executor import ToolExecutor
        self.assertIn("scan_watchlist", ToolExecutor._READ_ONLY_DISPATCH)

    def test_no_trigger_returns_error(self) -> None:
        from cockpit.core.tool_executor import ToolExecutor
        executor = ToolExecutor(MagicMock(), MagicMock())
        result = executor.execute("scan_watchlist", {})
        self.assertFalse(result["ok"])
        self.assertIn("not configured", result["error"])


if __name__ == "__main__":
    unittest.main()
